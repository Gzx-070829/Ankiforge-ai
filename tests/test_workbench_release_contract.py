from pathlib import Path
import unittest


class WorkbenchReleaseContractTests(unittest.TestCase):
    def test_architecture_document_describes_real_boundaries_without_overclaiming(self):
        architecture = Path("docs/workbench_architecture.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Create → Review → Write", architecture)
        self.assertIn("API key", architecture)
        self.assertIn("session-only", architecture)
        self.assertIn("ordinary background thread", architecture)
        self.assertIn("compatibility bridge", architecture)
        self.assertIn("compatibility alias", architecture)
        self.assertIn("concrete Anki adapters", architecture)
        self.assertNotIn("PDF OCR is supported", architecture)

    def test_docs_do_not_claim_later_quality_or_theme_phases_are_complete(self):
        architecture = Path("docs/workbench_architecture.md").read_text(
            encoding="utf-8"
        )
        normalized = " ".join(architecture.split())

        self.assertIn("not yet the warm-orange visual pass", normalized)
        self.assertIn("not a new semantic deduplication engine", normalized)


if __name__ == "__main__":
    unittest.main()
