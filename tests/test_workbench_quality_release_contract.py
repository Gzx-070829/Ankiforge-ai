from pathlib import Path
import unittest


class WorkbenchQualityReleaseContractTests(unittest.TestCase):
    def test_bilingual_readmes_link_the_quality_and_source_contract(self):
        for name in ("README.md", "README.en.md"):
            with self.subTest(name=name):
                text = self.read(name).casefold()
                self.assertIn("docs/card_quality_and_source_evidence.md", text)
                self.assertIn("ready", text)
                self.assertIn("review", text)
                self.assertIn("blocked", text)
                self.assertIn("preferences", text)

    def test_evidence_document_states_the_honest_boundaries(self):
        text = self.read("docs/card_quality_and_source_evidence.md").casefold()

        for required in (
            "bounded review context",
            "not factual proof",
            "not semantic deduplication",
            "collection duplicate check remains authoritative",
            "human review is always required",
            "user_files/preferences.json",
            "provider name",
            "model name",
            "card mode",
            "card count",
            "answer length",
            "output language",
            "intelligence level",
            "api key",
            "base url",
            "study material",
            "review state",
            "write history",
        ):
            self.assertIn(required, text)

    def test_architecture_and_manual_acceptance_cover_new_safety_contracts(self):
        architecture = self.read("docs/workbench_architecture.md").casefold()
        acceptance = self.read("docs/manual_anki_acceptance.md").casefold()

        for required in (
            "sourcespan",
            "ready / review / blocked",
            "near-duplicate",
            "preferences",
        ):
            self.assertIn(required, architecture)
        for required in (
            "source evidence",
            "exact / canonical / similar",
            "user_files/preferences.json",
            "api key",
        ):
            self.assertIn(required, acceptance)

    @staticmethod
    def root():
        return Path(__file__).parents[1]

    def read(self, relative_path):
        return (self.root() / relative_path).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
