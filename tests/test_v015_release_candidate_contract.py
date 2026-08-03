import json
from pathlib import Path
import unittest

import ankiforge_ai


VERSION = "0.15.0"


class V015ReleaseCandidateContractTests(unittest.TestCase):
    def test_runtime_manifest_and_candidate_documents_use_one_version(self):
        manifest = json.loads(
            self.read("ankiforge_ai/manifest.json")
        )

        self.assertEqual(ankiforge_ai.__version__, VERSION)
        self.assertEqual(manifest["version"], VERSION)
        self.assertEqual(manifest["human_version"], VERSION)
        for path in (
            "README.md",
            "README.en.md",
            "docs/release_notes_v0_15.md",
            "docs/ankiweb_description_v0_15.md",
            "docs/manual_anki_acceptance.md",
        ):
            with self.subTest(path=path):
                self.assertIn(VERSION, self.read(path))

    def test_release_notes_describe_the_completed_train_without_overclaiming(self):
        notes = self.read("docs/release_notes_v0_15.md").casefold()
        draft = self.read("docs/ankiweb_description_v0_15.md").casefold()

        for required in (
            "workbench application core",
            "ready / review / blocked",
            "source evidence",
            "near-duplicate",
            "non-sensitive preferences",
            "warm charcoal",
            "soft orange",
            "manual review",
            "final confirmation",
        ):
            self.assertIn(required, notes)
        for required in (
            "not a shared deck",
            "1227582295",
            "api key",
            "session-only",
            "pdf",
            "fallback",
            "human review",
        ):
            self.assertIn(required, draft)
        for forbidden in (
            "semantic deduplication",
            "factually correct",
            "automatic write",
            "full undo",
            "built-in ocr",
        ):
            self.assertNotIn(forbidden, notes + draft)

    @staticmethod
    def root():
        return Path(__file__).parents[1]

    def read(self, path):
        return (self.root() / path).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
