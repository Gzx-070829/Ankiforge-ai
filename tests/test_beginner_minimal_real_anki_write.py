import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

from ankiforge_ai.anki_writer.minimal_write import (
    WRITE_CARD_ERROR_COPY,
    BeginnerWriteCardCommand,
    BeginnerWriteCommand,
    BeginnerWriteResultState,
    BeginnerWrittenCardState,
    MinimalAnkiWriter,
)
from ankiforge_ai.ui.beginner_final_confirmation import (
    build_beginner_final_confirmation_preview,
)
from ankiforge_ai.ui.beginner_flow_models import (
    COMPLETION_TITLE,
    BeginnerAICardDraft,
    BeginnerArtifactState,
    BeginnerFlowSession,
    BeginnerWriteState,
)
from ankiforge_ai.ui.beginner_real_write import (
    WRITE_COMPLETION_TITLE,
    WRITE_CONFIRMATION_DISCLOSURE_COPY,
    execute_beginner_write_if_confirmed,
    prepare_beginner_write,
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


class FakeManager:
    def __init__(self, values):
        self.values = values
        self.mutation_calls = []

    def get(self, item_id):
        return self.values.get(item_id)

    def add(self, value):
        self.mutation_calls.append(("add", value))
        raise AssertionError("schema creation is forbidden")

    def save(self, value):
        self.mutation_calls.append(("save", value))
        raise AssertionError("schema mutation is forbidden")

    def update(self, value):
        self.mutation_calls.append(("update", value))
        raise AssertionError("schema mutation is forbidden")


class FakeNote(dict):
    def __init__(self, fields):
        super().__init__((name, "") for name in fields)
        self.id = 0


class FakeCollection:
    def __init__(self, fail_fronts=()):
        self.decks = FakeManager({7: {"id": 7, "name": "AnkiForge AI Test"}})
        self.models = FakeManager(
            {
                11: {
                    "id": 11,
                    "name": "Basic",
                    "flds": [
                        {"name": "Front"},
                        {"name": "Back"},
                        {"name": "Extra"},
                    ],
                }
            }
        )
        self.fail_fronts = set(fail_fronts)
        self.created_notes = []
        self.add_calls = []
        self.existing_notes = {500: {"Front": "existing", "Back": "unchanged"}}
        self.next_id = 1001

    def new_note(self, note_type):
        fields = tuple(item["name"] for item in note_type["flds"])
        return FakeNote(fields)

    def add_note(self, note, deck_id):
        self.add_calls.append((dict(note), deck_id))
        if note["Front"] in self.fail_fronts:
            raise RuntimeError("private collection failure")
        note.id = self.next_id
        self.next_id += 1
        self.created_notes.append((note, deck_id))
        return SimpleNamespace(id=note.id)


class FakeWriter:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def write(self, command):
        self.calls.append(command)
        return self.result


class BeginnerMinimalRealWriteTests(unittest.TestCase):
    def test_incomplete_conditions_do_not_create_command(self):
        session = BeginnerFlowSession()

        preparation = prepare_beginner_write(session, None, None, None)

        self.assertIsNone(preparation.command)
        self.assertFalse(preparation.can_write)
        self.assertIn("没有当前最终确认预览", preparation.missing_conditions)

    def test_missing_final_confirmation_blocks_otherwise_complete_context(self):
        session, mapping, duplicate_preview, _ = self.complete_context()
        session.final_confirmation_preview_state = BeginnerArtifactState.CLEARED

        preparation = prepare_beginner_write(
            session,
            None,
            mapping,
            duplicate_preview,
        )

        self.assertIsNone(preparation.command)
        self.assertIn("没有当前最终确认预览", preparation.missing_conditions)

    def test_missing_mapping_and_duplicate_check_block_command(self):
        session = self.ai_session()

        preparation = prepare_beginner_write(session, None, None, None)

        self.assertIsNone(preparation.command)
        self.assertIn("没有当前目标和字段映射", preparation.missing_conditions)
        self.assertIn("重复检查尚未完成", preparation.missing_conditions)

    def test_reusing_one_field_for_multiple_values_blocks_command(self):
        session, _, duplicate_preview, _ = self.complete_context()
        session.set_anki_field_mapping("Front", "Back", "Front")
        session.apply_duplicate_check_preview(3, 1)
        mapping = build_beginner_field_mapping_preview(
            deck=BeginnerAnkiDeckOption(7, "AnkiForge AI Test"),
            note_type=BeginnerAnkiNoteTypeOption(11, "Basic"),
            available_fields=("Front", "Back", "Extra"),
            front_field="Front",
            back_field="Back",
            source_field="Front",
        )
        final_preview = build_beginner_final_confirmation_preview(
            session,
            mapping,
            duplicate_preview,
        )
        session.apply_final_confirmation_preview(
            final_preview.candidate_count,
            len(final_preview.missing_conditions),
        )

        preparation = prepare_beginner_write(
            session,
            final_preview,
            mapping,
            duplicate_preview,
        )

        self.assertIsNone(preparation.command)
        self.assertIn("不能重复使用同一字段", preparation.missing_conditions[-1])

    def test_only_looks_good_non_duplicate_ai_card_enters_command(self):
        session, mapping, duplicate_preview, final_preview = self.complete_context()

        preparation = prepare_beginner_write(
            session,
            final_preview,
            mapping,
            duplicate_preview,
        )

        self.assertTrue(preparation.can_write)
        self.assertEqual(preparation.writable_count, 1)
        self.assertEqual(preparation.skipped_count, 2)
        command = preparation.command
        self.assertEqual(
            tuple(item.candidate_id for item in command.cards),
            (session.candidate_card_previews[0].id,),
        )
        self.assertEqual(command.deck_id, 7)
        self.assertEqual(command.deck_name, "AnkiForge AI Test")
        self.assertEqual(command.note_type_id, 11)
        self.assertEqual(command.note_type_name, "Basic")
        self.assertEqual(
            (command.front_field, command.back_field, command.source_field),
            ("Front", "Back", "Extra"),
        )

    def test_possible_duplicate_is_skipped_by_default(self):
        session, mapping, duplicate_preview, final_preview = self.complete_context()
        duplicate_candidate_id = session.candidate_card_previews[2].id

        preparation = prepare_beginner_write(
            session,
            final_preview,
            mapping,
            duplicate_preview,
        )

        self.assertIn(duplicate_candidate_id, preparation.skipped_candidate_ids)
        self.assertNotIn(
            duplicate_candidate_id,
            tuple(item.candidate_id for item in preparation.command.cards),
        )

    def test_writer_creates_new_note_with_selected_existing_structure(self):
        collection = FakeCollection()
        command = self.command()

        result = MinimalAnkiWriter(collection).write(command)

        self.assertEqual(result.state, BeginnerWriteResultState.SUCCESS)
        self.assertEqual(result.created_note_ids, (1001, 1002))
        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(collection.created_notes[0][1], 7)
        self.assertEqual(collection.created_notes[0][0]["Front"], "question one")
        self.assertEqual(collection.created_notes[0][0]["Back"], "answer one")
        self.assertEqual(collection.created_notes[0][0]["Extra"], "source one")
        self.assertEqual(collection.existing_notes[500]["Front"], "existing")
        self.assertEqual(collection.decks.mutation_calls, [])
        self.assertEqual(collection.models.mutation_calls, [])

    def test_writer_target_failure_is_safe_and_does_not_create_note(self):
        collection = FakeCollection()
        collection.decks.values.clear()

        result = MinimalAnkiWriter(collection).write(self.command())

        self.assertEqual(result.state, BeginnerWriteResultState.FAILED)
        self.assertEqual(result.success_count, 0)
        self.assertEqual(result.failed_count, 2)
        self.assertEqual(collection.add_calls, [])
        self.assertNotIn("private", result.user_message)

    def test_writer_rejects_target_renamed_after_confirmation(self):
        collection = FakeCollection()
        collection.decks.values[7]["name"] = "Renamed After Preview"

        result = MinimalAnkiWriter(collection).write(self.command())

        self.assertEqual(result.state, BeginnerWriteResultState.FAILED)
        self.assertEqual(collection.add_calls, [])

    def test_writer_reports_partial_success_without_false_total_success(self):
        collection = FakeCollection(fail_fronts=("FAIL",))
        command = self.command(second_front="FAIL")

        result = MinimalAnkiWriter(collection).write(command)

        self.assertEqual(result.state, BeginnerWriteResultState.PARTIAL)
        self.assertEqual(result.created_note_ids, (1001,))
        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failed_count, 1)
        failed = result.card_results[1]
        self.assertEqual(failed.state, BeginnerWrittenCardState.FAILED)
        self.assertEqual(failed.user_message, WRITE_CARD_ERROR_COPY)
        self.assertNotIn("private", str(result.to_safe_dict()) + result.user_message)

    def test_cancelled_confirmation_never_calls_writer(self):
        writer = FakeWriter()

        result = execute_beginner_write_if_confirmed(False, writer, self.command())

        self.assertIsNone(result)
        self.assertEqual(writer.calls, [])

    def test_successful_snapshot_cannot_be_prepared_twice(self):
        session, mapping, duplicate_preview, final_preview = self.complete_context()
        first = prepare_beginner_write(
            session,
            final_preview,
            mapping,
            duplicate_preview,
        )
        session.begin_write(
            first.command.snapshot_id,
            first.command.requested_count,
            first.command.skipped_count,
        )
        session.record_write_result(
            first.command.snapshot_id,
            (1001,),
            first.command.skipped_count,
            0,
        )

        second = prepare_beginner_write(
            session,
            final_preview,
            mapping,
            duplicate_preview,
        )

        self.assertIsNone(second.command)
        self.assertIn("不能重复写入", second.missing_conditions[0])
        self.assertEqual(session.write_state, BeginnerWriteState.SUCCESS)

    def test_upstream_changes_clear_write_result_but_keep_completed_guard(self):
        changes = (
            lambda session: session.update_material("changed material"),
            lambda session: session.set_candidate_review_decision(
                session.candidate_card_previews[0].id,
                "needs_revision",
            ),
            lambda session: session.set_anki_field_mapping("Front", "Back", None),
            lambda session: session.begin_duplicate_check(),
        )
        for change in changes:
            session, mapping, duplicate_preview, final_preview = self.complete_context()
            preparation = prepare_beginner_write(
                session,
                final_preview,
                mapping,
                duplicate_preview,
            )
            snapshot_id = preparation.command.snapshot_id
            session.begin_write(snapshot_id, 1, 2)
            session.record_write_result(snapshot_id, (1001,), 2, 0)

            change(session)

            with self.subTest(change=change):
                self.assertEqual(session.write_state, BeginnerWriteState.CLEARED)
                self.assertEqual(session.write_created_note_ids, ())
                self.assertTrue(session.has_completed_write_snapshot(snapshot_id))

    def test_api_key_cannot_enter_command_result_repr_or_safe_dict(self):
        secret = "sk-secret-never-store"
        command = self.command()
        result = MinimalAnkiWriter(FakeCollection()).write(command)

        rendered = (
            repr(command)
            + str(command)
            + str(command.to_safe_dict())
            + repr(result)
            + str(result.to_safe_dict())
            + result.user_message
        )

        self.assertNotIn(secret, rendered)
        self.assertNotIn("api_key", command.to_safe_dict())
        self.assertNotIn("api_key", result.to_safe_dict())

    def test_writer_source_never_creates_or_modifies_schema_or_existing_notes(self):
        source = self.writer_source()
        tree = ast.parse(source)
        called_attributes = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }

        self.assertIn("new_note", called_attributes)
        self.assertIn("add_note", called_attributes)
        for forbidden in (
            "add_field",
            "add_template",
            "update_note",
            "remove_notes",
            "remove_cards_and_orphaned_notes",
            "save",
            "flush",
        ):
            self.assertNotIn(forbidden, called_attributes)

    def test_ui_writer_call_is_only_after_secondary_confirmation(self):
        source = self.dialog_source()
        handler = self.function_source(source, "_confirm_and_write")

        self.assertIn('QPushButton("确认写入选中的卡片")', source)
        self.assertIn("QMessageBox.question", handler)
        self.assertIn("if not confirmed", handler)
        self.assertIn("execute_beginner_write_if_confirmed", handler)
        self.assertIn("WRITE_CONFIRMATION_DISCLOSURE_COPY", handler)
        self.assertIn(WRITE_CONFIRMATION_DISCLOSURE_COPY, self.real_write_source())
        self.assertNotIn("add_note", handler)
        self.assertNotIn("new_note", handler)

    def test_completion_copy_depends_on_real_success(self):
        self.assertEqual(COMPLETION_TITLE, "演练完成，尚未写入 Anki")
        self.assertEqual(WRITE_COMPLETION_TITLE, "写入完成，请在 Anki 中检查新卡片")

    def complete_context(self):
        session = self.ai_session()
        ids = tuple(item.id for item in session.candidate_card_previews)
        session.set_candidate_review_decision(ids[0], "looks_good")
        session.set_candidate_review_decision(ids[1], "needs_revision")
        session.set_candidate_review_decision(ids[2], "looks_good")
        session.select_anki_deck(7, "AnkiForge AI Test")
        session.select_anki_note_type(11, "Basic", ("Front", "Back", "Extra"))
        session.set_anki_field_mapping("Front", "Back", "Extra")
        mapping = self.mapping()
        duplicate_preview = BeginnerDuplicateCheckPreview(
            state=BeginnerDuplicatePreviewState.SUCCESS,
            results=(
                BeginnerDuplicateCandidateResult(
                    candidate_id=ids[0],
                    status=BeginnerDuplicateStatus.NO_OBVIOUS_DUPLICATE,
                ),
                BeginnerDuplicateCandidateResult(
                    candidate_id=ids[1],
                    status=BeginnerDuplicateStatus.NO_OBVIOUS_DUPLICATE,
                ),
                BeginnerDuplicateCandidateResult(
                    candidate_id=ids[2],
                    status=BeginnerDuplicateStatus.POSSIBLE_DUPLICATE,
                    matched_fields=("Front",),
                    matched_note_id=500,
                ),
            ),
            user_message="只读检查完成。",
        )
        session.apply_duplicate_check_preview(3, 1)
        final_preview = build_beginner_final_confirmation_preview(
            session,
            mapping,
            duplicate_preview,
        )
        session.apply_final_confirmation_preview(
            final_preview.candidate_count,
            len(final_preview.missing_conditions),
        )
        return session, mapping, duplicate_preview, final_preview

    @staticmethod
    def ai_session():
        session = BeginnerFlowSession()
        session.apply_ai_candidate_card_drafts(
            tuple(
                BeginnerAICardDraft(
                    id=str(index),
                    front=f"question {index}",
                    back=f"answer {index}",
                    source_excerpt=f"source {index}",
                )
                for index in range(1, 4)
            )
        )
        return session

    @staticmethod
    def mapping():
        return build_beginner_field_mapping_preview(
            deck=BeginnerAnkiDeckOption(7, "AnkiForge AI Test"),
            note_type=BeginnerAnkiNoteTypeOption(11, "Basic"),
            available_fields=("Front", "Back", "Extra"),
            front_field="Front",
            back_field="Back",
            source_field="Extra",
        )

    @staticmethod
    def command(second_front="question two"):
        return BeginnerWriteCommand(
            snapshot_id="snapshot-1",
            deck_id=7,
            deck_name="AnkiForge AI Test",
            note_type_id=11,
            note_type_name="Basic",
            front_field="Front",
            back_field="Back",
            source_field="Extra",
            cards=(
                BeginnerWriteCardCommand(
                    candidate_id="candidate-1",
                    front="question one",
                    back="answer one",
                    source="source one",
                ),
                BeginnerWriteCardCommand(
                    candidate_id="candidate-2",
                    front=second_front,
                    back="answer two",
                    source="source two",
                ),
            ),
            skipped_count=1,
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
    def root():
        return Path(__file__).parents[1]

    def writer_source(self):
        return (
            self.root() / "ankiforge_ai" / "anki_writer" / "minimal_write.py"
        ).read_text(encoding="utf-8")

    def dialog_source(self):
        return (
            self.root() / "ankiforge_ai" / "ui" / "beginner_mode_dialog.py"
        ).read_text(encoding="utf-8")

    def real_write_source(self):
        return (
            self.root() / "ankiforge_ai" / "ui" / "beginner_real_write.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
