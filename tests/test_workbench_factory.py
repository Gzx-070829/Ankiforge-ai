import unittest

from ankiforge_ai.anki_writer.minimal_write import MinimalAnkiWriter
from ankiforge_ai.ui.read_only_anki_targets import ReadOnlyAnkiTargetAdapter
from ankiforge_ai.ui.read_only_duplicate_check import (
    ReadOnlyDuplicateCheckAdapter,
)
from ankiforge_ai.ui.workbench_factory import (
    create_workbench_write_coordinator,
)
from ankiforge_ai.workbench.write_coordinator import WorkbenchWriteCoordinator


class WorkbenchFactoryTests(unittest.TestCase):
    def test_factory_injects_existing_tested_anki_boundaries(self):
        collection = object()

        coordinator = create_workbench_write_coordinator(collection)

        self.assertIsInstance(coordinator, WorkbenchWriteCoordinator)
        self.assertIsInstance(coordinator.target_adapter, ReadOnlyAnkiTargetAdapter)
        self.assertIsInstance(
            coordinator.duplicate_adapter,
            ReadOnlyDuplicateCheckAdapter,
        )
        self.assertIsInstance(coordinator.writer, MinimalAnkiWriter)
        self.assertIs(coordinator.target_adapter._collection, collection)
        self.assertIs(coordinator.duplicate_adapter._collection, collection)
        self.assertIs(coordinator.writer._collection, collection)


if __name__ == "__main__":
    unittest.main()
