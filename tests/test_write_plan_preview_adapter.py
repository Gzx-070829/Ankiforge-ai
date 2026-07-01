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
    build_write_eligibility_preview,
)
from ankiforge_ai.ui.write_plan_preview_adapter import (
    ReadOnlyWritePlanPreview,
    build_read_only_write_plan_preview,
)


class ReadOnlyWritePlanPreviewAdapterTests(unittest.TestCase):
    def test_missing_eligibility_is_safe_unknown_preview(self):
        plan = build_read_only_write_plan_preview(None)

        self.assertTrue(plan.is_empty)
        self.assertEqual(plan.plan_status, "unknown")
        self.assertEqual(plan.blocking_reasons, ("eligibility_preview_missing",))
        self.assert_fixed_safety(plan)

    def test_eligible_becomes_ready_preview(self):
        plan = self.plan("passed", "approved")

        self.assertEqual(plan.eligibility_status, "eligible")
        self.assertEqual(plan.plan_status, "ready_preview")
        self.assertEqual(plan.blocking_reasons, ())

    def test_blocked_remains_blocked_with_reasons(self):
        plan = self.plan("failed", "approved")

        self.assertEqual(plan.plan_status, "blocked")
        self.assertIn("quality_failed", plan.blocking_reasons)
        self.assertIn("local_review_invalid", plan.blocking_reasons)

    def test_needs_review_remains_needs_review_with_reason(self):
        plan = self.plan("passed", "pending")

        self.assertEqual(plan.plan_status, "needs_review")
        self.assertEqual(plan.blocking_reasons, ("review_pending",))

    def test_unknown_eligibility_remains_unknown(self):
        eligibility = build_write_eligibility_preview(None)
        plan = build_read_only_write_plan_preview(eligibility)

        self.assertTrue(plan.is_empty)
        self.assertEqual(plan.plan_status, "unknown")

    def test_target_bindings_are_preview_only_and_mappings_are_fixed(self):
        plan = self.plan("warning", "approved")

        self.assertEqual(
            plan.target_note_type_preview,
            "未绑定真实 Anki note type，仅预览",
        )
        self.assertEqual(plan.target_deck_preview, "未绑定真实 Anki deck，仅预览")
        self.assertEqual(
            tuple(
                (mapping.source_field, mapping.target_field)
                for mapping in plan.field_mappings
            ),
            (("Front", "Front"), ("Back", "Back"), ("Source", "Source")),
        )
        self.assertEqual(
            plan.tag_preview,
            ("AnkiForgeAI", "pipeline-preview", "human-reviewed"),
        )

    def test_safe_output_excludes_candidate_and_user_content(self):
        candidate_id = "private-candidate-123"
        plan = self.plan(
            "passed",
            "approved",
            candidate_id=candidate_id,
            front="sk-" + "F" * 30,
            back="Bearer private back",
            source="secret token source",
            note="private reviewer note",
        )
        rendered = (
            repr(plan) + json.dumps(plan.to_safe_dict(), ensure_ascii=False)
        ).lower()

        self.assertEqual(plan.candidate_id, candidate_id)
        self.assertNotIn(candidate_id.lower(), rendered)
        for marker in ("sk-", "bearer", "secret", "token", "private reviewer note"):
            self.assertNotIn(marker, rendered)

    def test_fixed_safety_states_no_authorization_or_execution(self):
        self.assert_fixed_safety(self.plan("passed", "approved"))

    def test_forged_eligibility_is_rejected(self):
        eligibility = self.eligibility("passed", "approved")

        with self.assertRaisesRegex(ValueError, "eligible state is inconsistent"):
            build_read_only_write_plan_preview(
                replace(eligibility, blocking_reasons=("forged",))
            )

    def test_public_plan_shape_has_no_runtime_write_objects(self):
        field_names = {field.name.lower() for field in fields(ReadOnlyWritePlanPreview)}
        for forbidden in (
            "generated_card",
            "write_ready",
            "writer_object",
            "collection_object",
            "provider",
            "api_key",
            "runtime_context",
        ):
            self.assertFalse(any(forbidden in name for name in field_names))

    def test_adapter_has_no_forbidden_runtime_dependencies(self):
        path = self.repo_root() / "ankiforge_ai" / "ui" / (
            "write_plan_preview_adapter.py"
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
            "build_write_ready_preview_item",
            "add_cards_to_deck",
            "add_note",
        ):
            self.assertNotIn(forbidden_name, imported_names)
            self.assertNotIn(forbidden_name, called_names)

    def test_dialog_path_builds_eligibility_before_write_plan(self):
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
            and node.name == "generate_read_only_write_plan_preview"
        )
        method_source = ast.get_source_segment(source, method) or ""

        self.assertLess(
            method_source.index("build_write_eligibility_preview"),
            method_source.index("build_read_only_write_plan_preview"),
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

    def test_dialog_clears_stale_write_plan_and_has_safe_buttons(self):
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

        self.assertIn("_render_write_plan_preview(None)", source)
        self.assertEqual(
            labels,
            {
                "更新审核草稿（仅本地）",
                "生成本地 HumanReview 预览（不写入）",
                "生成 Write Eligibility 只读摘要（不写入）",
                "生成只读 Write Plan 预览（不写入）",
                "关闭",
            },
        )

    def assert_fixed_safety(self, plan):
        self.assertEqual(
            self.row_mapping(plan.safety_rows),
            {
                "Source": "本地 Write Eligibility 只读摘要",
                "Preview meaning": "这是只读 Write Plan 预览",
                "Duplicate check": "未执行",
                "Anki collection": "尚未绑定真实 Anki collection",
                "Write authorization": "未授予",
                "Write execution": "不会执行",
                "Persistence": "未保存",
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
    def eligibility(cls, status, decision, **overrides):
        note = overrides.pop("note", "")
        candidate = cls.candidate(status, **overrides)
        draft = HumanReviewDecisionDraftInput(
            candidate_id=candidate.candidate_id,
            decision=decision,
            reviewer_note=note,
        )
        view = build_human_review_decision_draft_view_data(candidate, draft)
        local_review = build_local_human_review_preview(view, draft)
        return build_write_eligibility_preview(local_review)

    @classmethod
    def plan(cls, status, decision, **overrides):
        return build_read_only_write_plan_preview(
            cls.eligibility(status, decision, **overrides)
        )


if __name__ == "__main__":
    unittest.main()
