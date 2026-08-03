import unittest

from ankiforge_ai.workbench.write_coordinator import WorkbenchWriteCoordinator


class WorkbenchWriteCoordinatorTests(unittest.TestCase):
    def make_coordinator(self, calls, *, writer=None):
        class TargetAdapter:
            def read_targets(self):
                calls.append(("read_targets",))
                return "targets"

            def read_fields(self, note_type_id):
                calls.append(("read_fields", note_type_id))
                return "fields"

        class DuplicateAdapter:
            def check(self, candidates, mapping):
                calls.append(("duplicates", candidates, mapping))
                return "duplicates"

        resolved_writer = object() if writer is None else writer
        return WorkbenchWriteCoordinator(
            target_adapter=TargetAdapter(),
            duplicate_adapter=DuplicateAdapter(),
            writer=resolved_writer,
            final_preview_builder=lambda session, mapping, duplicates: (
                "final",
                session,
                mapping,
                duplicates,
            ),
            write_preparer=lambda session, final, mapping, duplicates: (
                "prepared",
                session,
                final,
                mapping,
                duplicates,
            ),
            confirmed_executor=lambda confirmed, injected_writer, command: (
                confirmed,
                injected_writer,
                command,
            ),
        )

    def test_target_and_duplicate_reads_delegate_to_injected_adapters(self):
        calls = []
        coordinator = self.make_coordinator(calls)

        self.assertEqual(coordinator.read_targets(), "targets")
        self.assertEqual(coordinator.read_fields(42), "fields")
        self.assertEqual(
            coordinator.check_duplicates(("card",), "mapping"),
            "duplicates",
        )
        self.assertEqual(calls[-1], ("duplicates", ("card",), "mapping"))

    def test_prepare_builds_final_preview_before_write_preparation(self):
        coordinator = self.make_coordinator([])

        prepared = coordinator.prepare("session", "mapping", "duplicates")

        self.assertEqual(
            prepared.final_preview,
            ("final", "session", "mapping", "duplicates"),
        )
        self.assertEqual(prepared.preparation[0], "prepared")
        self.assertIs(prepared.preparation[2], prepared.final_preview)

    def test_confirmation_execution_uses_the_injected_existing_gate(self):
        writer = object()
        coordinator = self.make_coordinator([], writer=writer)

        confirmed, injected_writer, command = coordinator.execute_if_confirmed(
            False,
            "command",
        )

        self.assertFalse(confirmed)
        self.assertIs(injected_writer, writer)
        self.assertEqual(command, "command")

    def test_repr_does_not_render_injected_dependencies(self):
        class PrivateWriter:
            def __repr__(self):
                return "private card content and collection"

        coordinator = self.make_coordinator([], writer=PrivateWriter())

        self.assertNotIn("private card content", repr(coordinator))

    def test_constructor_rejects_incomplete_adapters(self):
        with self.assertRaises(TypeError):
            WorkbenchWriteCoordinator(
                target_adapter=object(),
                duplicate_adapter=object(),
                writer=object(),
                final_preview_builder=lambda *args: None,
                write_preparer=lambda *args: None,
                confirmed_executor=lambda *args: None,
            )


if __name__ == "__main__":
    unittest.main()
