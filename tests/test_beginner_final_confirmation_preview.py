import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.beginner_final_confirmation import (
    FINAL_CONFIRMATION_FUTURE_COPY,
    FINAL_CONFIRMATION_SAFETY_COPY,
    BeginnerFinalConfirmationPreview,
    build_beginner_final_confirmation_preview,
)
from ankiforge_ai.ui.beginner_flow_models import (
    COMPLETION_TITLE,
    BeginnerAICardDraft,
    BeginnerArtifactState,
    BeginnerFlowSession,
)
from ankiforge_ai.ui.read_only_anki_targets import (
    BeginnerAnkiDeckOption,
    BeginnerAnkiNoteTypeOption,
    build_beginner_field_mapping_preview,
)
from ankiforge_ai.ui.read_only_duplicate_check import (
    BeginnerDuplicateCandidateResult,
    BeginnerDuplicateCheckPreview,
    BeginnerDuplicatePreviewState,
    BeginnerDuplicateStatus,
)


class BeginnerFinalConfirmationPreviewTests(unittest.TestCase):
    def test_preview_summarizes_cards_reviews_target_mapping_and_duplicates(self):
        session, mapping, duplicate_preview = self.complete_context()

        preview = build_beginner_final_confirmation_preview(
            session,
            mapping,
            duplicate_preview,
        )
        session.apply_final_confirmation_preview(
            preview.candidate_count,
            len(preview.missing_conditions),
        )

        self.assertIsInstance(preview, BeginnerFinalConfirmationPreview)
        self.assertEqual(preview.candidate_count, 2)
        self.assertEqual(preview.deck_name, "Learning")
        self.assertEqual(preview.note_type_name, "Basic")
        self.assertEqual(
            (preview.front_field, preview.back_field, preview.source_field),
            ("Front", "Back", "Extra"),
        )
        self.assertEqual(preview.cards[0].review_copy, "看起来可以")
        self.assertEqual(preview.cards[0].duplicate_copy, "未发现明显重复")
        self.assertEqual(preview.cards[1].review_copy, "暂时不要")
        self.assertEqual(preview.cards[1].duplicate_copy, "可能重复")
        self.assertIn("应跳过", preview.cards[1].attention_copy)
        self.assertIn("可能重复", preview.cards[1].attention_copy)
        self.assertEqual(preview.missing_conditions, ())
        self.assertTrue(preview.requirements_complete)
        self.assertTrue(preview.read_only)
        self.assertFalse(preview.real_write_available)
        self.assertFalse(preview.will_write_to_anki)
        self.assertEqual(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.CURRENT,
        )

    def test_missing_candidates_are_reported(self):
        preview = build_beginner_final_confirmation_preview(
            BeginnerFlowSession(),
            None,
            None,
        )

        self.assertIn("没有候选卡", preview.missing_conditions)
        self.assertFalse(preview.requirements_complete)
        self.assertFalse(preview.real_write_available)

    def test_missing_review_is_reported(self):
        session, mapping, duplicate_preview = self.complete_context()
        session.set_candidate_review_decision(
            session.candidate_card_previews[0].id,
            None,
        )

        preview = build_beginner_final_confirmation_preview(
            session,
            mapping,
            duplicate_preview,
        )

        self.assertIn("候选卡还没有全部审核", preview.missing_conditions)
        self.assertIn("尚未审核", preview.cards[0].attention_copy)
        self.assertIn("重复检查尚未完成", preview.missing_conditions)

    def test_missing_target_note_type_and_front_back_mapping_are_reported(self):
        session = self.session_with_candidates()

        preview = build_beginner_final_confirmation_preview(session, None, None)

        self.assertIn("没有选择目标牌组", preview.missing_conditions)
        self.assertIn("没有选择笔记类型", preview.missing_conditions)
        self.assertIn(
            "没有完成正面和背面的字段映射",
            preview.missing_conditions,
        )

    def test_duplicate_check_must_be_current_and_cover_every_candidate(self):
        session, mapping, duplicate_preview = self.complete_context()
        session.clear_duplicate_check_preview()

        preview = build_beginner_final_confirmation_preview(
            session,
            mapping,
            duplicate_preview,
        )

        self.assertIn("重复检查尚未完成", preview.missing_conditions)

    def test_candidate_review_mapping_and_duplicate_changes_clear_final_preview(self):
        changes = (
            self.change_candidate,
            self.change_review,
            self.change_mapping,
            self.restart_duplicate_check,
        )
        for change in changes:
            session, _, _ = self.complete_context()
            session.apply_final_confirmation_preview(2, 0)

            change(session)

            with self.subTest(change=change.__name__):
                self.assertEqual(
                    session.final_confirmation_preview_state,
                    BeginnerArtifactState.CLEARED,
                )
                self.assertEqual(session.final_confirmation_card_count, 0)
                self.assertEqual(
                    session.final_confirmation_missing_condition_count,
                    0,
                )

    def test_close_and_new_session_do_not_retain_final_preview(self):
        session, _, _ = self.complete_context()
        session.apply_final_confirmation_preview(2, 0)

        session.close()
        replacement = BeginnerFlowSession()

        self.assertEqual(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.EMPTY,
        )
        self.assertEqual(session.final_confirmation_card_count, 0)
        self.assertEqual(
            replacement.final_confirmation_preview_state,
            BeginnerArtifactState.EMPTY,
        )

    def test_repr_and_safe_dict_do_not_expose_card_content(self):
        session, mapping, duplicate_preview = self.complete_context()
        preview = build_beginner_final_confirmation_preview(
            session,
            mapping,
            duplicate_preview,
        )

        rendered = repr(preview) + repr(preview.cards[0]) + str(
            preview.to_safe_dict()
        )

        self.assertNotIn("private front one", rendered)
        self.assertNotIn("private back one", rendered)
        self.assertNotIn("private source one", rendered)

    def test_ui_has_preview_only_entry_and_no_write_handler(self):
        source = self.dialog_source()
        handler = self.function_source(source, "_show_final_confirmation_preview")

        self.assertIn('QGroupBox("最终确认预览")', source)
        self.assertIn('QPushButton("查看汇总预览")', source)
        self.assertIn("build_beginner_final_confirmation_preview", handler)
        self.assertIn("apply_final_confirmation_preview", handler)
        self.assertIn("FINAL_CONFIRMATION_SAFETY_COPY", source)
        self.assertIn("FINAL_CONFIRMATION_FUTURE_COPY", source)
        self.assertIn(FINAL_CONFIRMATION_SAFETY_COPY, self.preview_source())
        self.assertIn(FINAL_CONFIRMATION_FUTURE_COPY, self.preview_source())
        for forbidden in (
            "add_note(",
            "update_note(",
            "add_to_anki(",
            "write_to_anki(",
            "writer",
        ):
            self.assertNotIn(forbidden, handler)

    def test_preview_module_has_no_formal_write_models_or_writer(self):
        source = self.preview_source()
        tree = ast.parse(source)
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }

        self.assertNotIn("GeneratedCard", imported_names)
        self.assertNotIn("WriteReadyPreviewItem", imported_names)
        self.assertFalse(any("writer" in name.lower() for name in imported_names))
        self.assertNotIn("collection", source.casefold())

    def test_copy_is_non_misleading_and_completion_is_unchanged(self):
        combined = "\n".join(
            (
                FINAL_CONFIRMATION_SAFETY_COPY,
                FINAL_CONFIRMATION_FUTURE_COPY,
                self.preview_source(),
            )
        )
        self.assertIn("尚未写入 Anki", FINAL_CONFIRMATION_SAFETY_COPY)
        for forbidden in ("写入成功", "已写入", "已准备好写入", "可以直接写入"):
            self.assertNotIn(forbidden, combined)
        self.assertEqual(COMPLETION_TITLE, "演练完成，尚未写入 Anki")

    def complete_context(self):
        session = self.session_with_candidates()
        candidate_ids = [item.id for item in session.candidate_card_previews]
        session.set_candidate_review_decision(candidate_ids[0], "looks_good")
        session.set_candidate_review_decision(candidate_ids[1], "skip_for_now")
        session.select_anki_deck(7, "Learning")
        session.select_anki_note_type(
            11,
            "Basic",
            ("Front", "Back", "Extra"),
        )
        session.set_anki_field_mapping("Front", "Back", "Extra")
        duplicate_preview = BeginnerDuplicateCheckPreview(
            state=BeginnerDuplicatePreviewState.SUCCESS,
            results=(
                BeginnerDuplicateCandidateResult(
                    candidate_id=candidate_ids[0],
                    status=BeginnerDuplicateStatus.NO_OBVIOUS_DUPLICATE,
                ),
                BeginnerDuplicateCandidateResult(
                    candidate_id=candidate_ids[1],
                    status=BeginnerDuplicateStatus.POSSIBLE_DUPLICATE,
                    matched_fields=("Front",),
                    matched_note_id=99,
                    matched_field_preview="existing value",
                ),
            ),
            user_message="只读检查完成。没有写入 Anki。",
        )
        session.apply_duplicate_check_preview(2, 1)
        return session, self.mapping(), duplicate_preview

    @staticmethod
    def session_with_candidates():
        session = BeginnerFlowSession()
        session.apply_ai_candidate_card_drafts(
            (
                BeginnerAICardDraft(
                    id="one",
                    front="private front one",
                    back="private back one",
                    source_excerpt="private source one",
                ),
                BeginnerAICardDraft(
                    id="two",
                    front="private front two",
                    back="private back two",
                    source_excerpt="private source two",
                ),
            )
        )
        return session

    @staticmethod
    def mapping():
        return build_beginner_field_mapping_preview(
            deck=BeginnerAnkiDeckOption(7, "Learning"),
            note_type=BeginnerAnkiNoteTypeOption(11, "Basic"),
            available_fields=("Front", "Back", "Extra"),
            front_field="Front",
            back_field="Back",
            source_field="Extra",
        )

    @staticmethod
    def change_candidate(session):
        session.apply_ai_candidate_card_drafts(
            (
                BeginnerAICardDraft(
                    id="replacement",
                    front="replacement front",
                    back="replacement back",
                    source_excerpt="replacement source",
                ),
            )
        )

    @staticmethod
    def change_review(session):
        session.set_candidate_review_decision(
            session.candidate_card_previews[0].id,
            "needs_revision",
        )

    @staticmethod
    def change_mapping(session):
        session.set_anki_field_mapping("Front", "Back", None)

    @staticmethod
    def restart_duplicate_check(session):
        session.begin_duplicate_check()

    @staticmethod
    def function_source(source, name):
        tree = ast.parse(source)
        node = next(
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.FunctionDef) and item.name == name
        )
        return ast.unparse(node)

    @staticmethod
    def repo_root():
        return Path(__file__).parents[1]

    def preview_source(self):
        return (
            self.repo_root()
            / "ankiforge_ai"
            / "ui"
            / "beginner_final_confirmation.py"
        ).read_text(encoding="utf-8")

    def dialog_source(self):
        return (
            self.repo_root() / "ankiforge_ai" / "ui" / "beginner_mode_dialog.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
