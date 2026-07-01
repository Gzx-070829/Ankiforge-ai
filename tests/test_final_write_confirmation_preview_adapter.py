import ast
import json
import unittest
from dataclasses import fields, replace
from pathlib import Path

from ankiforge_ai.pipeline.card_candidate_preview_adapter import (
    CardCandidatePreviewItem,
)
from ankiforge_ai.ui.final_write_confirmation_preview_adapter import (
    FinalWriteConfirmationPreview,
    build_final_write_confirmation_preview,
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
    build_read_only_write_plan_preview,
)


class FinalWriteConfirmationPreviewAdapterTests(unittest.TestCase):
    def test_missing_write_plan_is_safe_unknown_state(self):
        preview = build_final_write_confirmation_preview(None)

        self.assertTrue(preview.is_empty)
        self.assertEqual(preview.final_status, "unknown")
        self.assertEqual(
            preview.blocking_reasons,
            ("write_plan_preview_missing",),
        )
        self.assert_fixed_contract(preview)

    def test_ready_plan_is_ready_for_future_confirmation_without_authority(self):
        preview = self.preview("passed", "approved")

        self.assertEqual(preview.write_plan_status, "ready_preview")
        self.assertEqual(preview.final_status, "ready_for_future_confirmation")
        self.assertEqual(preview.write_authorization, "not_granted")
        self.assertEqual(preview.final_confirmation_status, "not_requested")

    def test_blocked_plan_remains_blocked(self):
        preview = self.preview("failed", "approved")

        self.assertEqual(preview.final_status, "blocked")
        self.assertIn("quality_failed", preview.blocking_reasons)
        self.assertIn("local_review_invalid", preview.blocking_reasons)

    def test_needs_review_plan_remains_needs_review(self):
        preview = self.preview("passed", "pending")

        self.assertEqual(preview.final_status, "needs_review")
        self.assertEqual(preview.blocking_reasons, ("review_pending",))

    def test_unknown_write_plan_remains_unknown(self):
        write_plan = build_read_only_write_plan_preview(None)
        preview = build_final_write_confirmation_preview(write_plan)

        self.assertTrue(preview.is_empty)
        self.assertEqual(preview.final_status, "unknown")
        self.assert_fixed_contract(preview)

    def test_duplicate_and_confirmation_states_are_fixed(self):
        preview = self.preview("warning", "approved")

        self.assertEqual(preview.duplicate_check_status, "not_run")
        self.assertEqual(
            preview.duplicate_check_requirement,
            "required_before_write",
        )
        self.assertEqual(preview.duplicate_result, "unknown")
        self.assertEqual(preview.final_confirmation_status, "not_requested")
        self.assertEqual(preview.write_authorization, "not_granted")
        self.assertEqual(preview.write_execution, "will_not_execute")

    def test_required_future_steps_are_stable_and_non_executing(self):
        preview = self.preview("passed", "approved")

        self.assertEqual(
            preview.required_future_steps,
            (
                "重新展示并确认候选内容",
                "绑定真实 Anki note type 与 deck",
                "在独立授权流程中执行 duplicate check",
                "展示 duplicate check 结果",
                "请求独立的最终用户确认",
                "仅在确认后重新计算写入授权",
            ),
        )

    def test_safe_output_excludes_candidate_and_user_content(self):
        candidate_id = "private-candidate-456"
        preview = self.preview(
            "passed",
            "approved",
            candidate_id=candidate_id,
            front="sk-" + "F" * 30,
            back="Bearer private back",
            source="secret token source",
            note="private reviewer note",
        )
        rendered = (
            repr(preview)
            + json.dumps(preview.to_safe_dict(), ensure_ascii=False)
        ).lower()

        self.assertEqual(preview.candidate_id, candidate_id)
        self.assertNotIn(candidate_id.lower(), rendered)
        for marker in (
            "sk-",
            "bearer private back",
            "secret token source",
            "private reviewer note",
        ):
            self.assertNotIn(marker, rendered)

    def test_forged_write_plan_is_rejected(self):
        plan = self.plan("passed", "approved")

        with self.assertRaisesRegex(ValueError, "unsupported blocking reason"):
            build_final_write_confirmation_preview(
                replace(plan, blocking_reasons=("private user content",))
            )

    def test_public_shape_has_no_runtime_write_objects(self):
        field_names = {
            field.name.lower() for field in fields(FinalWriteConfirmationPreview)
        }
        for forbidden in (
            "generated_card",
            "write_ready",
            "writer_object",
            "collection_object",
            "provider",
            "api_key",
            "runtime_context",
            "confirmation_token",
        ):
            self.assertFalse(any(forbidden in name for name in field_names))

    def test_adapter_has_no_forbidden_runtime_dependencies(self):
        path = self.repo_root() / "ankiforge_ai" / "ui" / (
            "final_write_confirmation_preview_adapter.py"
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
            "run_duplicate_check",
        ):
            self.assertNotIn(forbidden_name, imported_names)
            self.assertNotIn(forbidden_name, called_names)

    def test_dialog_builds_write_plan_before_final_contract(self):
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
            and node.name == "generate_final_write_confirmation_preview"
        )
        method_source = ast.get_source_segment(source, method) or ""

        self.assertLess(
            method_source.index("build_read_only_write_plan_preview"),
            method_source.index("build_final_write_confirmation_preview"),
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
            "run_duplicate_check",
        ):
            self.assertNotIn(forbidden, method_source)

    def test_dialog_clears_stale_final_contract_and_has_safe_buttons(self):
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

        self.assertGreaterEqual(
            source.count("_render_final_write_confirmation_preview(None)"),
            7,
        )
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

    def assert_fixed_contract(self, preview):
        self.assertEqual(preview.duplicate_check_status, "not_run")
        self.assertEqual(
            preview.duplicate_check_requirement,
            "required_before_write",
        )
        self.assertEqual(preview.duplicate_result, "unknown")
        self.assertEqual(preview.final_confirmation_status, "not_requested")
        self.assertEqual(preview.write_authorization, "not_granted")
        self.assertEqual(preview.write_execution, "will_not_execute")
        self.assertEqual(
            self.row_mapping(preview.safety_rows),
            {
                "Source": "只读 Write Plan 预览",
                "Preview meaning": "这是最终确认契约预览",
                "User confirmation": "这不是用户确认",
                "Duplicate check": "尚未执行",
                "Anki collection": "尚未绑定真实 Anki collection",
                "Write authorization": "不是写入授权；未授予",
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
    def plan(cls, status, decision, **overrides):
        note = overrides.pop("note", "")
        candidate = cls.candidate(status, **overrides)
        draft = HumanReviewDecisionDraftInput(
            candidate_id=candidate.candidate_id,
            decision=decision,
            reviewer_note=note,
        )
        view = build_human_review_decision_draft_view_data(candidate, draft)
        local_review = build_local_human_review_preview(view, draft)
        eligibility = build_write_eligibility_preview(local_review)
        return build_read_only_write_plan_preview(eligibility)

    @classmethod
    def preview(cls, status, decision, **overrides):
        return build_final_write_confirmation_preview(
            cls.plan(status, decision, **overrides)
        )


if __name__ == "__main__":
    unittest.main()
