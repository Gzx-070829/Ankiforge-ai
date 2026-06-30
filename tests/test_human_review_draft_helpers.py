import ast
import inspect
import json
import unittest
from dataclasses import fields, replace
from pathlib import Path

from ankiforge_ai.pipeline.card_candidate_preview_adapter import (
    CardCandidatePreviewItem,
    QualityIssuePreviewItem,
)
from ankiforge_ai.ui.human_review_draft_helpers import (
    HUMAN_REVIEW_DRAFT_DECISIONS,
    HumanReviewDecisionDraftInput,
    HumanReviewDecisionDraftViewData,
    allowed_human_review_draft_decisions,
    build_human_review_decision_draft_view_data,
)


class HumanReviewDraftHelperTests(unittest.TestCase):
    def test_empty_candidate_is_a_safe_non_writing_state(self):
        view = build_human_review_decision_draft_view_data(None)

        self.assertTrue(view.is_empty)
        self.assertTrue(view.is_valid)
        self.assertEqual(view.candidate_rows, ())
        self.assertEqual(view.quality_rows, ())
        self.assertEqual(
            self.row_mapping(view.safety_rows),
            self.expected_safety_rows(),
        )
        self.assertNotIn(
            "approved",
            allowed_human_review_draft_decisions(view),
        )

    def test_all_supported_decisions_build_local_drafts(self):
        candidate = self.candidate("passed")

        for decision in HUMAN_REVIEW_DRAFT_DECISIONS:
            with self.subTest(decision=decision):
                view = self.view(candidate, decision=decision)
                self.assertTrue(view.is_valid)
                self.assertEqual(view.decision, decision)

    def test_quality_error_and_unchecked_forbid_approved(self):
        for quality_status in ("failed", "unchecked"):
            with self.subTest(quality_status=quality_status):
                candidate = self.candidate(quality_status)
                view = self.view(candidate, decision="approved")
                self.assertFalse(view.is_valid)
                self.assertFalse(view.approval_allowed)
                self.assertNotIn(
                    "approved",
                    allowed_human_review_draft_decisions(view),
                )

    def test_quality_warning_and_passed_allow_approved(self):
        for quality_status in ("warning", "passed"):
            with self.subTest(quality_status=quality_status):
                view = self.view(
                    self.candidate(quality_status),
                    decision="approved",
                )
                self.assertTrue(view.is_valid)
                self.assertTrue(view.approval_allowed)
                self.assertIn(
                    "approved",
                    allowed_human_review_draft_decisions(view),
                )

    def test_candidate_id_must_match(self):
        with self.assertRaisesRegex(ValueError, "IDs must match"):
            build_human_review_decision_draft_view_data(
                self.candidate("passed"),
                HumanReviewDecisionDraftInput(candidate_id="other"),
            )

    def test_forged_quality_state_is_rejected(self):
        candidate = self.candidate("failed")
        forged = replace(candidate, quality_allows_approval=True)

        with self.assertRaisesRegex(ValueError, "inconsistent approval"):
            build_human_review_decision_draft_view_data(forged)

    def test_candidate_and_quality_rows_are_safe_short_summaries(self):
        candidate = self.candidate(
            "warning",
            front="F" * 200,
            back="B" * 200,
            source="S" * 200,
        )
        view = self.view(candidate)
        rows = self.row_mapping(view.candidate_rows)

        self.assertEqual(rows["Candidate ID"], candidate.candidate_id)
        self.assertLessEqual(len(rows["Front preview"]), 120)
        self.assertLessEqual(len(rows["Back preview"]), 120)
        self.assertLessEqual(len(rows["Source preview"]), 120)
        self.assertIn("Issue short_back (warning)", self.row_mapping(view.quality_rows))

    def test_repr_and_safe_dict_do_not_copy_user_content_or_note(self):
        values = {
            "front": "sk-" + "F" * 40,
            "back": "Bearer private back",
            "source": "secret token source",
            "note": "private reviewer note " + "N" * 30,
        }
        view = self.view(
            self.candidate(
                "passed",
                front=values["front"],
                back=values["back"],
                source=values["source"],
            ),
            reviewer_note=values["note"],
        )
        rendered = (
            repr(view) + json.dumps(view.to_safe_dict(), ensure_ascii=False)
        ).lower()

        for value in values.values():
            self.assertNotIn(value.lower(), rendered)
        for marker in ("sk-", "bearer", "secret", "token"):
            self.assertNotIn(marker, rendered)
        self.assertEqual(view.reviewer_note_length, len(values["note"]))

    def test_public_shapes_have_no_formal_review_or_write_objects(self):
        names = {
            field.name.lower()
            for model in (
                HumanReviewDecisionDraftInput,
                HumanReviewDecisionDraftViewData,
            )
            for field in fields(model)
        }
        names.update(
            name.lower()
            for name in inspect.signature(
                build_human_review_decision_draft_view_data
            ).parameters
        )

        for forbidden in (
            "generated_card",
            "write_ready",
            "write_authorization",
            "provider",
            "api_key",
            "secret",
            "token",
        ):
            self.assertFalse(any(forbidden in name for name in names))

    def test_helper_has_no_forbidden_runtime_dependencies(self):
        path = self.repo_root() / "ankiforge_ai" / "ui" / (
            "human_review_draft_helpers.py"
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
            "create_human_review",
            "GeneratedCard",
            "WriteReadyPreviewItem",
            "build_write_ready_preview_item",
            "add_cards_to_deck",
            "add_note",
        ):
            self.assertNotIn(forbidden_name, imported_names)
            self.assertNotIn(forbidden_name, called_names)

    def test_dialog_has_only_local_draft_preview_and_close_buttons(self):
        path = self.repo_root() / "ankiforge_ai" / "ui" / (
            "human_review_draft_dialog.py"
        )
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        button_labels = {
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
            button_labels,
            {
                "更新审核草稿（仅本地）",
                "生成本地 HumanReview 预览（不写入）",
                "关闭",
            },
        )
        self.assertIn("self._drafts = {}", source)
        self.assertNotIn("self.cards", source)
        self.assertNotIn("add_to_anki", source)
        self.assertNotIn("add_note", source)

    def test_main_dialog_handler_is_isolated_from_legacy_and_provider_paths(self):
        path = self.repo_root() / "ankiforge_ai" / "ui" / "main_dialog.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        dialog_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "MainDialog"
        )
        handler = next(
            node
            for node in dialog_class.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "show_human_review_decision_draft"
        )
        handler_source = ast.get_source_segment(source, handler) or ""

        self.assertIn("run_full_mock_pipeline_with_status", handler_source)
        self.assertIn("build_card_candidate_preview_items", handler_source)
        self.assertIn("HumanReviewDecisionDraftDialog", handler_source)
        for forbidden in (
            "self.cards",
            "add_to_anki",
            "add_cards_to_deck",
            "provider_combo",
            "api_key_input",
            "self.config",
            "create_provider",
            "writer",
            "mw.col",
        ):
            self.assertNotIn(forbidden, handler_source)

    @staticmethod
    def expected_safety_rows():
        return {
            "Draft scope": "仅审核草稿",
            "Formal HumanReview": "尚未形成正式 HumanReview",
            "Write authorization": "尚未计算写入授权",
            "Will generate GeneratedCard": "否",
            "Will modify legacy candidates": "否（不修改 legacy 候选卡）",
            "Will call writer": "否（不调用 writer）",
            "Will write to Anki": "否（不写入 Anki）",
            "Draft lifetime": "仅当前弹窗，关闭后丢弃",
        }

    @staticmethod
    def row_mapping(rows):
        return {row.label: row.value for row in rows}

    @staticmethod
    def repo_root():
        return Path(__file__).parents[1]

    @staticmethod
    def candidate(quality_status, **overrides):
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
            "quality_status": quality_status,
            "quality_issues": ((issue,) if quality_status == "warning" else ()),
            "review_decision": "",
            "quality_allows_approval": quality_status in {"passed", "warning"},
            "has_quality_errors": quality_status == "failed",
            "has_quality_warnings": quality_status == "warning",
            "review_status": "unreviewed",
            "review_allows_write": False,
        }
        values.update(overrides)
        if "source" in overrides and "source_display" not in overrides:
            values["source_display"] = overrides["source"]
        return CardCandidatePreviewItem(**values)

    @staticmethod
    def view(candidate, decision="pending", reviewer_note=""):
        return build_human_review_decision_draft_view_data(
            candidate,
            HumanReviewDecisionDraftInput(
                candidate_id=candidate.candidate_id,
                decision=decision,
                reviewer_note=reviewer_note,
            ),
        )


if __name__ == "__main__":
    unittest.main()
