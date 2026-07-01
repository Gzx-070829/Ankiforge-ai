import ast
import json
import unittest
from dataclasses import fields, replace
from pathlib import Path

from ankiforge_ai.pipeline.card_candidate_preview_adapter import (
    CardCandidatePreviewItem,
)
from ankiforge_ai.ui.human_review_draft_helpers import (
    HumanReviewDecisionDraftInput,
    build_human_review_decision_draft_view_data,
)
from ankiforge_ai.ui.human_review_preview_adapter import (
    build_local_human_review_preview,
)
from ankiforge_ai.ui.write_eligibility_preview_adapter import (
    WriteEligibilityPreview,
    build_write_eligibility_preview,
)


class WriteEligibilityPreviewAdapterTests(unittest.TestCase):
    def test_missing_review_preview_is_safe_unknown_state(self):
        preview = build_write_eligibility_preview(None)

        self.assertTrue(preview.is_empty)
        self.assertEqual(preview.eligibility_status, "unknown")
        self.assertEqual(preview.blocking_reasons, ("review_preview_missing",))
        self.assert_fixed_safety(preview)

    def test_approved_passed_and_warning_are_eligible(self):
        for status in ("passed", "warning"):
            with self.subTest(status=status):
                preview = self.eligibility(status, "approved")
                self.assertEqual(preview.eligibility_status, "eligible")
                self.assertEqual(preview.blocking_reasons, ())
                self.assertTrue(preview.review_valid)

    def test_approved_failed_and_unchecked_are_blocked(self):
        for status, quality_reason in (
            ("failed", "quality_failed"),
            ("unchecked", "quality_unchecked"),
        ):
            with self.subTest(status=status):
                preview = self.eligibility(status, "approved")
                self.assertEqual(preview.eligibility_status, "blocked")
                self.assertIn(quality_reason, preview.blocking_reasons)
                self.assertIn("local_review_invalid", preview.blocking_reasons)
                self.assertFalse(preview.review_valid)

    def test_pending_needs_review_with_reason(self):
        preview = self.eligibility("passed", "pending")

        self.assertEqual(preview.eligibility_status, "needs_review")
        self.assertEqual(preview.blocking_reasons, ("review_pending",))

    def test_rejected_is_blocked_with_reason(self):
        preview = self.eligibility("passed", "rejected")

        self.assertEqual(preview.eligibility_status, "blocked")
        self.assertEqual(preview.blocking_reasons, ("review_rejected",))

    def test_needs_edit_is_blocked_with_reason(self):
        preview = self.eligibility("warning", "needs_edit")

        self.assertEqual(preview.eligibility_status, "blocked")
        self.assertEqual(preview.blocking_reasons, ("review_needs_edit",))

    def test_invalid_local_review_never_becomes_eligible(self):
        preview = self.eligibility("failed", "approved")

        self.assertFalse(preview.review_valid)
        self.assertNotEqual(preview.eligibility_status, "eligible")

    def test_forged_local_review_state_is_rejected(self):
        local = self.local_review("passed", "approved")

        with self.assertRaisesRegex(ValueError, "inconsistent quality"):
            build_write_eligibility_preview(
                replace(local, quality_status="failed")
            )

    def test_safe_output_preserves_id_shape_but_no_user_content(self):
        candidate_id = "candidate-private-123"
        preview = self.eligibility(
            "passed",
            "approved",
            candidate_id=candidate_id,
            front="sk-" + "F" * 30,
            back="Bearer private back",
            source="secret token source",
            note="private reviewer note",
        )
        rendered = (
            repr(preview) + json.dumps(preview.to_safe_dict(), ensure_ascii=False)
        ).lower()

        self.assertEqual(preview.candidate_id, candidate_id)
        self.assertNotIn(candidate_id.lower(), rendered)
        for marker in ("sk-", "bearer", "secret", "token", "private reviewer note"):
            self.assertNotIn(marker, rendered)

    def test_preview_has_no_write_object_fields(self):
        field_names = {field.name.lower() for field in fields(WriteEligibilityPreview)}
        for forbidden in (
            "generated_card",
            "write_ready",
            "write_plan_object",
            "writer_object",
            "collection",
            "provider",
            "api_key",
            "runtime_context",
        ):
            self.assertFalse(any(forbidden in name for name in field_names))

    def test_adapter_has_no_forbidden_runtime_dependencies(self):
        path = self.repo_root() / "ankiforge_ai" / "ui" / (
            "write_eligibility_preview_adapter.py"
        )
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        imported_modules.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        called_names = {
            node.func.id
            if isinstance(node.func, ast.Name)
            else node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Name, ast.Attribute))
        }

        for forbidden_module in (
            "controlled_write_bridge",
            "provider",
            "config",
            "secret_store",
            "transport",
            "executor",
            "requests",
            "httpx",
            "aiohttp",
            "urllib",
            "socket",
            "writer",
            "aqt",
            "anki",
            "PyQt",
            "PySide",
        ):
            self.assertFalse(
                any(forbidden_module in module for module in imported_modules),
                forbidden_module,
            )
        for forbidden_name in (
            "GeneratedCard",
            "WriteReadyPreviewItem",
            "build_pipeline_write_eligibility",
            "build_write_ready_preview_item",
            "add_cards_to_deck",
            "add_note",
        ):
            self.assertNotIn(forbidden_name, imported_names)
            self.assertNotIn(forbidden_name, called_names)

    def test_dialog_path_calls_local_review_then_eligibility_adapter(self):
        path = self.repo_root() / "ankiforge_ai" / "ui" / (
            "human_review_draft_dialog.py"
        )
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        dialog_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "HumanReviewDecisionDraftDialog"
        )
        method = next(
            node
            for node in dialog_class.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "generate_write_eligibility_preview"
        )
        method_source = ast.get_source_segment(source, method) or ""

        self.assertLess(
            method_source.index("build_local_human_review_preview"),
            method_source.index("build_write_eligibility_preview"),
        )
        for forbidden in (
            "self.cards",
            "add_to_anki",
            "writer",
            "GeneratedCard",
            "WriteReadyPreviewItem",
            "provider",
            "self.config",
            "mw.col",
        ):
            self.assertNotIn(forbidden, method_source)

    def test_dialog_clears_derived_summaries_on_widget_change(self):
        path = self.repo_root() / "ankiforge_ai" / "ui" / (
            "human_review_draft_dialog.py"
        )
        source = path.read_text(encoding="utf-8")

        self.assertIn("decision_combo.currentTextChanged.connect", source)
        self.assertIn("reviewer_note_input.textChanged.connect", source)
        self.assertIn("_render_write_eligibility_preview(None)", source)

    def assert_fixed_safety(self, preview):
        self.assertEqual(
            self.row_mapping(preview.safety_rows),
            {
                "Generated source": "本地 HumanReview 预览",
                "Summary meaning": "这是只读写入资格摘要",
                "Write authorization": "未授予",
                "Write Plan": "尚未生成 Write Plan",
                "GeneratedCard": "尚未生成 GeneratedCard",
                "WriteReadyPreviewItem": "尚未生成 WriteReadyPreviewItem",
                "Writer": "不调用 writer",
                "Anki write": "不写入 Anki",
                "Lifetime": "仅当前弹窗，关闭后丢弃",
            },
        )

    @staticmethod
    def row_mapping(rows):
        return {row.label: row.value for row in rows}

    @staticmethod
    def repo_root():
        return Path(__file__).parents[1]

    @staticmethod
    def candidate(status, **overrides):
        values = {
            "candidate_id": "candidate_1",
            "card_type": "basic",
            "front": "什么是过拟合？",
            "back": "模型过度拟合训练数据。",
            "extra": "",
            "tags": ("机器学习",),
            "source": "学习笔记.md > 过拟合",
            "source_display": "学习笔记.md > 过拟合",
            "quality_status": status,
            "quality_issues": (),
            "review_decision": "",
            "quality_allows_approval": status in {"passed", "warning"},
            "has_quality_errors": status == "failed",
            "has_quality_warnings": status == "warning",
            "review_status": "unreviewed",
            "review_allows_write": False,
        }
        values.update(overrides)
        if "source" in overrides and "source_display" not in overrides:
            values["source_display"] = overrides["source"]
        return CardCandidatePreviewItem(**values)

    @classmethod
    def local_review(cls, status, decision, **overrides):
        note = overrides.pop("note", "")
        candidate = cls.candidate(status, **overrides)
        draft = HumanReviewDecisionDraftInput(
            candidate_id=candidate.candidate_id,
            decision=decision,
            reviewer_note=note,
        )
        view = build_human_review_decision_draft_view_data(candidate, draft)
        return build_local_human_review_preview(view, draft)

    @classmethod
    def eligibility(cls, status, decision, **overrides):
        return build_write_eligibility_preview(
            cls.local_review(status, decision, **overrides)
        )


if __name__ == "__main__":
    unittest.main()
