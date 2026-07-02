import ast
import unittest
from pathlib import Path

from ankiforge_ai.ui.beginner_flow_models import (
    COMPLETION_TITLE,
    BeginnerAICardDraft,
    BeginnerArtifactState,
    BeginnerFlowSession,
)
from ankiforge_ai.ui.read_only_anki_targets import (
    ANKI_MAPPING_PREVIEW_SAFETY_COPY,
    ANKI_TARGET_READ_ERROR_COPY,
    BeginnerAnkiDeckOption,
    BeginnerAnkiNoteTypeOption,
    BeginnerAnkiReadState,
    ReadOnlyAnkiTargetAdapter,
    build_beginner_field_mapping_preview,
)


class NamedItem:
    def __init__(self, item_id, name):
        self.id = item_id
        self.name = name


class FakeDeckManager:
    def __init__(self, items, fail=False):
        self.items = items
        self.fail = fail
        self.write_calls = 0

    def all_names_and_ids(self):
        if self.fail:
            raise RuntimeError("private collection detail")
        return self.items

    def id(self, name):
        self.write_calls += 1
        raise AssertionError("deck mutation must not be called")


class FakeModelManager:
    def __init__(self, items, models, fail=False):
        self.items = items
        self.models = models
        self.fail = fail
        self.write_calls = 0

    def all_names_and_ids(self):
        if self.fail:
            raise RuntimeError("private model detail")
        return self.items

    def get(self, note_type_id):
        if self.fail:
            raise RuntimeError("private field detail")
        return self.models.get(note_type_id)

    def add(self, model):
        self.write_calls += 1
        raise AssertionError("note type mutation must not be called")

    def add_field(self, model, field):
        self.write_calls += 1
        raise AssertionError("field mutation must not be called")


class FakeCollection:
    def __init__(self, fail=False):
        self.decks = FakeDeckManager(
            [NamedItem(2, "Learning"), NamedItem(1, "Default")],
            fail=fail,
        )
        self.models = FakeModelManager(
            [NamedItem(11, "Basic"), NamedItem(12, "Cloze")],
            {
                11: {
                    "id": 11,
                    "name": "Basic",
                    "flds": [
                        {"name": "Front"},
                        {"name": "Back"},
                        {"name": "Extra"},
                    ],
                },
                12: {
                    "id": 12,
                    "name": "Cloze",
                    "flds": [{"name": "Text"}, {"name": "Extra"}],
                },
            },
            fail=fail,
        )
        self.write_calls = 0

    def add_note(self, note):
        self.write_calls += 1
        raise AssertionError("note creation must not be called")


class BeginnerReadOnlyAnkiTargetTests(unittest.TestCase):
    def test_adapter_reads_deck_list_from_fake_collection(self):
        snapshot = ReadOnlyAnkiTargetAdapter(FakeCollection()).read_targets()

        self.assertEqual(snapshot.state, BeginnerAnkiReadState.SUCCESS)
        self.assertEqual(
            tuple((item.id, item.name) for item in snapshot.decks),
            ((1, "Default"), (2, "Learning")),
        )
        self.assertFalse(snapshot.to_safe_dict()["will_write_to_anki"])

    def test_adapter_reads_note_type_list_from_fake_collection(self):
        snapshot = ReadOnlyAnkiTargetAdapter(FakeCollection()).read_targets()

        self.assertEqual(
            tuple((item.id, item.name) for item in snapshot.note_types),
            ((11, "Basic"), (12, "Cloze")),
        )

    def test_adapter_reads_selected_note_type_fields(self):
        field_snapshot = ReadOnlyAnkiTargetAdapter(
            FakeCollection()
        ).read_fields(11)

        self.assertEqual(field_snapshot.state, BeginnerAnkiReadState.SUCCESS)
        self.assertEqual(field_snapshot.fields, ("Front", "Back", "Extra"))
        self.assertFalse(field_snapshot.to_safe_dict()["will_write_to_anki"])

    def test_adapter_never_calls_fake_write_methods(self):
        collection = FakeCollection()
        adapter = ReadOnlyAnkiTargetAdapter(collection)

        adapter.read_targets()
        adapter.read_fields(11)

        self.assertEqual(collection.write_calls, 0)
        self.assertEqual(collection.decks.write_calls, 0)
        self.assertEqual(collection.models.write_calls, 0)

    def test_collection_failure_returns_fixed_safe_error(self):
        snapshot = ReadOnlyAnkiTargetAdapter(
            FakeCollection(fail=True)
        ).read_targets()

        self.assertEqual(snapshot.state, BeginnerAnkiReadState.ERROR)
        self.assertEqual(snapshot.user_message, ANKI_TARGET_READ_ERROR_COPY)
        self.assertIn("没有写入 Anki", snapshot.user_message)
        self.assertNotIn("private", snapshot.user_message)

    def test_field_mapping_preview_maps_front_back_and_optional_source(self):
        preview = build_beginner_field_mapping_preview(
            deck=BeginnerAnkiDeckOption(1, "Default"),
            note_type=BeginnerAnkiNoteTypeOption(11, "Basic"),
            available_fields=("Front", "Back", "Extra"),
            front_field="Front",
            back_field="Back",
            source_field="Extra",
        )

        self.assertEqual(preview.front_field, "Front")
        self.assertEqual(preview.back_field, "Back")
        self.assertEqual(preview.source_field, "Extra")
        self.assertIn("未来写入目标牌组：Default", preview.summary_lines)
        self.assertIn("未来使用笔记类型：Basic", preview.summary_lines)
        self.assertIn(ANKI_MAPPING_PREVIEW_SAFETY_COPY, preview.summary_lines)
        self.assertTrue(preview.read_only)
        self.assertFalse(preview.will_write_to_anki)

    def test_deck_note_type_and_mapping_changes_clear_final_confirmation(self):
        session = BeginnerFlowSession()
        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT

        session.select_anki_deck(1, "Default")
        self.assertEqual(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.CLEARED,
        )
        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT

        session.select_anki_note_type(
            11,
            "Basic",
            ("Front", "Back", "Extra"),
        )
        self.assertEqual(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.CLEARED,
        )
        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT

        session.set_anki_field_mapping("Front", "Back", "Extra")
        self.assertEqual(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.CLEARED,
        )
        self.assertEqual(
            session.anki_mapping_preview_state,
            BeginnerArtifactState.CURRENT,
        )

        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT
        session.clear_anki_field_mapping()
        self.assertEqual(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.CLEARED,
        )
        self.assertEqual(
            session.anki_mapping_preview_state,
            BeginnerArtifactState.CLEARED,
        )

        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT
        session.select_anki_deck(2, "Learning")
        self.assertEqual(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.CLEARED,
        )
        self.assertEqual(
            session.anki_mapping_preview_state,
            BeginnerArtifactState.CLEARED,
        )

    def test_candidate_and_review_changes_clear_final_confirmation(self):
        session = BeginnerFlowSession()
        session.update_material("早停会观察验证集表现。")
        first = BeginnerAICardDraft(
            id="one",
            front="什么是早停？",
            back="验证表现不再改善时停止训练。",
            source_excerpt="早停会观察验证集表现",
        )
        session.apply_ai_candidate_card_drafts((first,))
        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT
        second = BeginnerAICardDraft(
            id="two",
            front="早停何时触发？",
            back="验证表现不再改善时。",
            source_excerpt="验证表现不再改善",
        )

        session.apply_ai_candidate_card_drafts((second,))
        self.assertEqual(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.CLEARED,
        )
        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT
        candidate_id = session.candidate_card_previews[0].id

        session.set_candidate_review_decision(candidate_id, "looks_good")
        self.assertEqual(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.CLEARED,
        )

    def test_close_and_new_session_do_not_retain_target_mapping(self):
        session = BeginnerFlowSession()
        session.select_anki_deck(1, "Default")
        session.select_anki_note_type(11, "Basic", ("Front", "Back", "Extra"))
        session.set_anki_field_mapping("Front", "Back", "Extra")

        session.close()
        new_session = BeginnerFlowSession()

        for item in (session, new_session):
            self.assertIsNone(item.selected_anki_deck_id)
            self.assertIsNone(item.selected_anki_note_type_id)
            self.assertEqual(item.selected_anki_note_type_fields, ())
            self.assertEqual(item.mapped_front_field, "")
            self.assertEqual(item.mapped_back_field, "")
            self.assertIsNone(item.mapped_source_field)

    def test_ui_reads_only_through_adapter_and_has_preview_copy(self):
        source = self.dialog_source()
        read_handler = self.function_source(source, "_read_anki_targets")

        self.assertIn("self.anki_target_adapter.read_targets()", read_handler)
        self.assertIn('QPushButton("读取 Anki 结构")', source)
        self.assertIn('QPushButton("重新读取")', source)
        self.assertIn("build_beginner_field_mapping_preview", source)
        self.assertIn("当前只是预览，尚未写入 Anki", self.adapter_source())
        for forbidden in (
            "add_note(",
            "addNote(",
            "add_to_anki(",
            "duplicate_check(",
        ):
            self.assertNotIn(forbidden, self.adapter_source())
            self.assertNotIn(forbidden, read_handler)

    def test_adapter_has_no_formal_write_output_or_writer_import(self):
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
            self.repo_root() / "ankiforge_ai" / "ui" / "read_only_anki_targets.py"
        ).read_text(encoding="utf-8")

    def dialog_source(self):
        return (
            self.repo_root() / "ankiforge_ai" / "ui" / "beginner_mode_dialog.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
