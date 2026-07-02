import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.beginner_flow_models import (
    COMPLETION_TITLE,
    BeginnerAICardDraft,
    BeginnerArtifactState,
    BeginnerCandidateCardPreview,
    BeginnerFlowSession,
)
from ankiforge_ai.ui.read_only_anki_targets import (
    BeginnerAnkiDeckOption,
    BeginnerAnkiNoteTypeOption,
    build_beginner_field_mapping_preview,
)
from ankiforge_ai.ui.read_only_duplicate_check import (
    DUPLICATE_CHECK_ERROR_COPY,
    DUPLICATE_CHECK_SCOPE_COPY,
    BeginnerDuplicatePreviewState,
    BeginnerDuplicateStatus,
    ReadOnlyDuplicateCheckAdapter,
)


class FakeNote(dict):
    def __init__(self, note_id, front, back):
        super().__init__(Front=front, Back=back, Extra="")
        self.id = note_id


class FakeDB:
    def __init__(self, note_ids, fail=False):
        self.note_ids = note_ids
        self.fail = fail
        self.read_calls = []
        self.write_calls = 0

    def list(self, query, note_type_id):
        self.read_calls.append((query, note_type_id))
        if self.fail:
            raise RuntimeError("private database detail")
        return list(self.note_ids)

    def execute(self, query, *args):
        self.write_calls += 1
        raise AssertionError("database mutation must not be called")


class FakeCollection:
    def __init__(self, notes, fail=False):
        self.notes = {note.id: note for note in notes}
        self.db = FakeDB(self.notes, fail=fail)
        self.write_calls = 0

    def get_note(self, note_id):
        if self.db.fail:
            raise RuntimeError("private note detail")
        return self.notes[note_id]

    def add_note(self, note):
        self.write_calls += 1
        raise AssertionError("note creation must not be called")

    def update_note(self, note):
        self.write_calls += 1
        raise AssertionError("note mutation must not be called")

    def remove_notes(self, note_ids):
        self.write_calls += 1
        raise AssertionError("note removal must not be called")


class BeginnerReadOnlyDuplicateCheckTests(unittest.TestCase):
    def test_adapter_detects_exact_front_duplicate(self):
        collection = FakeCollection(
            [FakeNote(101, "什么是过拟合？", "旧答案")]
        )

        preview = ReadOnlyDuplicateCheckAdapter(collection).check(
            (self.candidate(front="什么是过拟合？"),),
            self.mapping(),
        )

        result = preview.results[0]
        self.assertEqual(preview.state, BeginnerDuplicatePreviewState.SUCCESS)
        self.assertEqual(result.status, BeginnerDuplicateStatus.POSSIBLE_DUPLICATE)
        self.assertEqual(result.matched_fields, ("Front",))
        self.assertEqual(result.matched_note_id, 101)
        self.assertEqual(result.matched_field_preview, "什么是过拟合？")

    def test_adapter_normalizes_case_and_consecutive_whitespace(self):
        collection = FakeCollection(
            [FakeNote(102, "  WHAT   is\nOverfitting?  ", "旧答案")]
        )

        preview = ReadOnlyDuplicateCheckAdapter(collection).check(
            (self.candidate(front="what is overfitting?"),),
            self.mapping(),
        )

        self.assertEqual(
            preview.results[0].status,
            BeginnerDuplicateStatus.POSSIBLE_DUPLICATE,
        )

    def test_no_match_returns_no_obvious_duplicate(self):
        collection = FakeCollection([FakeNote(103, "不同问题", "不同答案")])

        preview = ReadOnlyDuplicateCheckAdapter(collection).check(
            (self.candidate(),),
            self.mapping(),
        )

        result = preview.results[0]
        self.assertEqual(
            result.status,
            BeginnerDuplicateStatus.NO_OBVIOUS_DUPLICATE,
        )
        self.assertEqual(result.status_copy, "未发现明显重复")
        self.assertEqual(result.matched_fields, ())

    def test_collection_failure_returns_safe_unable_results(self):
        collection = FakeCollection([], fail=True)

        preview = ReadOnlyDuplicateCheckAdapter(collection).check(
            (self.candidate(),),
            self.mapping(),
        )

        self.assertEqual(preview.state, BeginnerDuplicatePreviewState.ERROR)
        self.assertEqual(preview.user_message, DUPLICATE_CHECK_ERROR_COPY)
        self.assertIn("没有写入 Anki", preview.user_message)
        self.assertEqual(
            preview.results[0].status,
            BeginnerDuplicateStatus.UNABLE_TO_CHECK,
        )
        self.assertNotIn("private", preview.user_message)

    def test_adapter_only_calls_read_methods(self):
        collection = FakeCollection([FakeNote(104, "问题", "答案")])

        ReadOnlyDuplicateCheckAdapter(collection).check(
            (self.candidate(),),
            self.mapping(),
        )

        self.assertEqual(collection.write_calls, 0)
        self.assertEqual(collection.db.write_calls, 0)
        self.assertEqual(
            collection.db.read_calls,
            [("select id from notes where mid = ?", 11)],
        )

    def test_missing_mapping_returns_blocked_without_collection_read(self):
        collection = FakeCollection([])

        preview = ReadOnlyDuplicateCheckAdapter(collection).check(
            (self.candidate(),),
            None,
        )

        self.assertEqual(preview.state, BeginnerDuplicatePreviewState.BLOCKED)
        self.assertEqual(collection.db.read_calls, [])

    def test_candidate_change_clears_duplicate_and_final_previews(self):
        session = self.session_with_duplicate_preview()
        replacement = BeginnerAICardDraft(
            id="replacement",
            front="新的问题",
            back="新的答案",
            source_excerpt="新的来源",
        )

        session.apply_ai_candidate_card_drafts((replacement,))

        self.assert_duplicate_and_final_cleared(session)

    def test_review_change_clears_duplicate_and_final_previews(self):
        session = self.session_with_duplicate_preview()
        candidate_id = session.candidate_card_previews[0].id

        session.set_candidate_review_decision(candidate_id, "needs_revision")

        self.assert_duplicate_and_final_cleared(session)

    def test_target_and_mapping_changes_clear_duplicate_and_final_previews(self):
        changes = (
            lambda session: session.select_anki_deck(2, "Learning"),
            lambda session: session.select_anki_note_type(
                12,
                "Cloze",
                ("Text", "Extra"),
            ),
            lambda session: session.set_anki_field_mapping(
                "Front",
                "Back",
                None,
            ),
        )
        for change in changes:
            session = self.session_with_duplicate_preview()
            change(session)
            with self.subTest(change=change):
                self.assert_duplicate_and_final_cleared(session)

    def test_ui_uses_read_only_adapter_and_shows_allowed_copy(self):
        source = self.dialog_source()
        handler = self.function_source(source, "_run_duplicate_check")

        self.assertIn('QPushButton("检查是否可能重复")', source)
        self.assertIn('QPushButton("重新检查")', source)
        self.assertIn("self.duplicate_check_adapter.check", handler)
        self.assertIn("未发现明显重复", self.adapter_source())
        self.assertIn("可能重复", self.adapter_source())
        self.assertIn("无法检查", self.adapter_source())
        self.assertIn("当前只是只读检查", self.adapter_source())
        self.assertIn("没有写入 Anki", DUPLICATE_CHECK_SCOPE_COPY)
        for forbidden in (
            "add_note(",
            "update_note(",
            "remove_notes(",
            "add_to_anki(",
        ):
            self.assertNotIn(forbidden, self.adapter_source())
            self.assertNotIn(forbidden, handler)

    def test_preview_is_not_formal_write_output_and_completion_is_unchanged(self):
        tree = ast.parse(self.adapter_source())
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }

        self.assertNotIn("GeneratedCard", imported_names)
        self.assertNotIn("WriteReadyPreviewItem", imported_names)
        self.assertFalse(any("writer" in name.lower() for name in imported_names))
        self.assertEqual(COMPLETION_TITLE, "演练完成，尚未写入 Anki")

    @staticmethod
    def candidate(front="什么是过拟合？", back="模型过度贴合训练数据。"):
        return BeginnerCandidateCardPreview(
            id="candidate-1",
            knowledge_point_id="ai-1",
            front_preview=front,
            back_preview=back,
            source_excerpt="过拟合会降低泛化表现",
        )

    @staticmethod
    def mapping():
        return build_beginner_field_mapping_preview(
            deck=BeginnerAnkiDeckOption(1, "Default"),
            note_type=BeginnerAnkiNoteTypeOption(11, "Basic"),
            available_fields=("Front", "Back", "Extra"),
            front_field="Front",
            back_field="Back",
            source_field="Extra",
        )

    def session_with_duplicate_preview(self):
        session = BeginnerFlowSession()
        draft = BeginnerAICardDraft(
            id="draft-1",
            front="什么是过拟合？",
            back="模型过度贴合训练数据。",
            source_excerpt="过拟合会降低泛化表现",
        )
        session.apply_ai_candidate_card_drafts((draft,))
        session.select_anki_deck(1, "Default")
        session.select_anki_note_type(11, "Basic", ("Front", "Back", "Extra"))
        session.set_anki_field_mapping("Front", "Back", "Extra")
        session.apply_duplicate_check_preview(1, 1)
        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT
        return session

    def assert_duplicate_and_final_cleared(self, session):
        self.assertEqual(
            session.duplicate_check_preview_state,
            BeginnerArtifactState.CLEARED,
        )
        self.assertEqual(session.duplicate_check_result_count, 0)
        self.assertEqual(session.possible_duplicate_count, 0)
        self.assertEqual(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.CLEARED,
        )

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

    def adapter_source(self):
        return (
            self.repo_root() / "ankiforge_ai" / "ui" / "read_only_duplicate_check.py"
        ).read_text(encoding="utf-8")

    def dialog_source(self):
        return (
            self.repo_root() / "ankiforge_ai" / "ui" / "beginner_mode_dialog.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
