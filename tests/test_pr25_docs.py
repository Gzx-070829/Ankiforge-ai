import json
from pathlib import Path
import unittest


class PR25DocumentationContractTests(unittest.TestCase):
    def test_hardening_record_states_scope_and_non_claims(self):
        text = self.read("docs/pr25_runtime_safety_hardening.md")

        for required in (
            "does **not** claim complete SSRF prevention",
            "risk classification plus explicit confirmation",
            "not true cancellation",
            "plain-text",
            "Advanced trusted HTML or Markdown rendering",
            "No DNS lookup",
            "Automatic retry is not enabled",
            "ordinary Python worker thread",
        ):
            with self.subTest(required=required):
                self.assertIn(required.casefold(), text.casefold())

    def test_hardening_record_covers_all_ten_required_sections(self):
        text = self.read("docs/pr25_runtime_safety_hardening.md")

        for section_number in range(1, 11):
            self.assertIn(f"## {section_number}.", text)

    def test_manual_acceptance_has_all_pr25_runtime_checks(self):
        text = self.read("docs/manual_anki_acceptance.md")
        section = text.split("## PR25 运行时安全 hardening", 1)[1]

        for item_number in range(1, 14):
            self.assertIn(f"{item_number}. [ ]", section)
        for required in (
            "50,000",
            "metadata",
            "401",
            "429",
            "<script>",
            "<img onerror>",
            "duplicate check",
            "final confirmation",
        ):
            self.assertIn(required, section)

    def test_legacy_example_no_longer_invites_key_persistence(self):
        example = json.loads(self.read("ankiforge_ai/config.example.json"))
        config_doc = self.read("ankiforge_ai/config.md")

        self.assertNotIn("api_key", example)
        self.assertIn("does not read or save an API key", config_doc)

    @classmethod
    def root(cls):
        return Path(__file__).parents[1]

    @classmethod
    def read(cls, relative_path):
        return (cls.root() / relative_path).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
