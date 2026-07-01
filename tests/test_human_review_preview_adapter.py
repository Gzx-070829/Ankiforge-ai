import ast
import json
import unittest
from dataclasses import fields, replace
from pathlib import Path

from ankiforge_ai.pipeline.card_candidate_preview_adapter import (
    CardCandidatePreviewItem,
    QualityIssuePreviewItem,
)
from ankiforge_ai.ui.human_review_draft_helpers import (
    HumanReviewDecisionDraftInput,
    HumanReviewDecisionDraftViewData,
    build_human_review_decision_draft_view_data,
)
from ankiforge_ai.ui.human_review_preview_adapter import (
    LocalHumanReviewPreview,
    build_local_human_review_preview,
)


class LocalHumanReviewPreviewAdapterTests(unittest.TestCase):
    def test_pending_rejected_and_needs_edit_build_local_previews(self):
        for decision in ("pending", "rejected", "needs_edit"):
            with self.subTest(decision=decision):
                preview = self.preview(self.candidate("failed"), decision=decision)
                self.assertTrue(preview.is_locally_valid)
                self.assertEqual(preview.review_decision, decision)

    def test_approved_passed_and_warning_build_valid_local_previews(self):
        for status in ("passed", "warning"):
            with self.subTest(status=status):
                preview = self.preview(self.candidate(status), decision="approved")
                self.assertTrue(preview.is_locally_valid)
                self.assertEqual(preview.quality_status, status)

    def test_approved_failed_and_unchecked_build_invalid_local_previews(self):
        for status in ("failed", "unchecked"):
            with self.subTest(status=status):
                preview = self.preview(self.candidate(status), decision="approved")
                self.assertFalse(preview.is_locally_valid)
                self.assertTrue(preview.validation_errors)

    def test_empty_view_has_no_local_preview(self):
        empty = build_human_review_decision_draft_view_data(None)
        draft = HumanReviewDecisionDraftInput(candidate_id="candidate_1")

        self.assertIsNone(build_local_human_review_preview(empty, draft))

    def test_candidate_id_and_decision_must_match_view(self):
        candidate = self.candidate("passed")
        draft = self.draft(candidate, decision="pending")
        view = build_human_review_decision_draft_view_data(candidate, draft)

        for forged in (
            replace(draft, candidate_id="other"),
            replace(draft, decision="rejected"),
        ):
            with self.subTest(forged=forged.to_safe_dict()):
                with self.assertRaisesRegex(ValueError, "must match"):
                    build_local_human_review_preview(view, forged)

    def test_forged_approval_state_is_rejected(self):
        candidate = self.candidate("passed")
        draft = self.draft(candidate)
        view = build_human_review_decision_draft_view_data(candidate, draft)

        with self.assertRaisesRegex(ValueError, "inconsistent approval"):
            build_local_human_review_preview(
                replace(view, approval_allowed=False),
                draft,
            )

    def test_reviewer_note_excerpt_is_short_and_safe_output_hides_it(self):
        note = "private reviewer note " + "N" * 120
        preview = self.preview(
            self.candidate("passed"),
            reviewer_note=note,
        )
        rendered = (
            repr(preview) + json.dumps(preview.to_safe_dict(), ensure_ascii=False)
        )

        self.assertLessEqual(len(preview.reviewer_note_excerpt), 80)
        self.assertEqual(preview.reviewer_note_length, len(note))
        self.assertNotIn(note, rendered)
        self.assertNotIn(preview.reviewer_note_excerpt, rendered)

    def test_front_back_and_source_never_enter_preview_safe_output(self):
        values = {
            "front": "sk-" + "F" * 30,
            "back": "Bearer private back",
            "source": "secret token source",
        }
        preview = self.preview(self.candidate("passed", **values))
        rendered = (
            repr(preview) + json.dumps(preview.to_safe_dict(), ensure_ascii=False)
        ).lower()

        for value in values.values():
            self.assertNotIn(value.lower(), rendered)
        for marker in ("sk-", "bearer", "secret", "token"):
            self.assertNotIn(marker, rendered)

    def test_preview_has_fixed_non_persistent_non_writing_status(self):
        preview = self.preview(self.candidate("passed"))

        self.assertEqual(
            self.row_mapping(preview.safety_rows),
            {
                "Created source": "本地审核草稿",
                "Preview meaning": "这是本地 HumanReview 预览",
                "Persistence": "尚未保存",
                "Write authorization": "尚未形成写入授权",
                "GeneratedCard": "尚未生成 GeneratedCard",
                "WriteReadyPreviewItem": "尚未生成 WriteReadyPreviewItem",
                "Writer": "不调用 writer",
                "Anki write": "不写入 Anki",
                "Lifetime": "仅当前弹窗，关闭后丢弃",
            },
        )

    def test_public_preview_shape_has_no_runtime_or_write_objects(self):
        field_names = {field.name.lower() for field in fields(LocalHumanReviewPreview)}
        for forbidden in (
            "generated_card",
            "write_ready",
            "writer_object",
            "collection",
            "provider",
            "api_key",
            "secret",
            "token",
            "runtime_context",
        ):
            self.assertFalse(any(forbidden in name for name in field_names))

    def test_adapter_has_no_forbidden_runtime_dependencies(self):
        path = self.repo_root() / "ankiforge_ai" / "ui" / (
            "human_review_preview_adapter.py"
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
            "HumanReview",
            "GeneratedCard",
            "WriteReadyPreviewItem",
            "build_pipeline_write_eligibility",
            "build_write_ready_preview_item",
            "add_cards_to_deck",
            "add_note",
        ):
            self.assertNotIn(forbidden_name, imported_names)
            self.assertNotIn(forbidden_name, called_names)

    def test_dialog_preview_path_calls_pr1_helper_then_pr2_adapter(self):
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
            and node.name == "generate_local_human_review_preview"
        )
        method_source = ast.get_source_segment(source, method) or ""

        self.assertLess(
            method_source.index("build_human_review_decision_draft_view_data"),
            method_source.index("build_local_human_review_preview"),
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

    def test_dialog_buttons_are_local_preview_only(self):
        path = self.repo_root() / "ankiforge_ai" / "ui" / (
            "human_review_draft_dialog.py"
        )
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        labels = {
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "QPushButton"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        }

        self.assertEqual(
            labels,
            {
                "更新审核草稿（仅本地）",
                "生成本地 HumanReview 预览（不写入）",
                "生成 Write Eligibility 只读摘要（不写入）",
                "生成只读 Write Plan 预览（不写入）",
                "生成最终确认契约预览（不写入）",
                "关闭",
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
        issue = QualityIssuePreviewItem(
            code="short_back",
            message="Back is short.",
            severity="warning",
        )
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
            "quality_issues": ((issue,) if status == "warning" else ()),
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

    @staticmethod
    def draft(candidate, decision="pending", reviewer_note=""):
        return HumanReviewDecisionDraftInput(
            candidate_id=candidate.candidate_id,
            decision=decision,
            reviewer_note=reviewer_note,
        )

    @classmethod
    def preview(cls, candidate, decision="pending", reviewer_note=""):
        draft = cls.draft(candidate, decision, reviewer_note)
        view = build_human_review_decision_draft_view_data(candidate, draft)
        return build_local_human_review_preview(view, draft)


if __name__ == "__main__":
    unittest.main()
