import json
import unittest
from pathlib import Path

import ankiforge_ai


class V1CoreDocumentationTests(unittest.TestCase):
    REQUIRED_DOCS = (
        "docs/card_quality_system.md",
        "docs/review_workbench.md",
        "docs/write_safety_and_traceability.md",
        "docs/v1_core_acceptance_checklist.md",
        "docs/ankiweb_description_v0_12.md",
        "docs/release_notes_v0_12_v1_core.md",
    )

    def test_required_v1_core_documents_exist(self):
        for relative_path in self.REQUIRED_DOCS:
            with self.subTest(path=relative_path):
                self.assertTrue((self.root() / relative_path).is_file())

    def test_runtime_and_manifest_versions_are_synchronized(self):
        manifest = json.loads(
            (self.root() / "ankiforge_ai" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(ankiforge_ai.__version__, "0.13.0")
        self.assertEqual(manifest["version"], "0.13.0")

    def test_readmes_describe_modes_quality_review_and_safety(self):
        combined = "\n".join(
            (self.root() / name).read_text(encoding="utf-8")
            for name in ("README.md", "README.en.md")
        ).casefold()

        for term in (
            "concept",
            "definition",
            "exam",
            "quick_review",
            "quality",
            "review",
            "session-only",
            "duplicate",
            "pdf",
            "ocr",
        ):
            self.assertIn(term, combined)

    def test_ankiweb_description_has_bilingual_product_boundaries(self):
        text = (self.root() / "docs" / "ankiweb_description_v0_12.md").read_text(
            encoding="utf-8"
        )
        lowered = text.casefold()

        for term in (
            "1227582295",
            "这是 anki 插件，不是共享牌组",
            "this is an anki add-on, not a shared deck",
            "api key",
            "session-only",
            "人工审核",
            "review",
            "pdf",
            "fallback",
            "ocr",
        ):
            self.assertIn(term, lowered)

    def test_release_notes_name_public_preview_and_deferred_undo(self):
        text = (
            self.root() / "docs" / "release_notes_v0_12_v1_core.md"
        ).read_text(encoding="utf-8").casefold()

        self.assertIn("v0.12.0-public-preview", text)
        self.assertIn("undo", text)
        self.assertIn("deferred", text)
        self.assertIn("manual review", text)
        self.assertIn("session-only", text)

    def test_docs_do_not_make_exaggerated_claims(self):
        combined = "\n".join(
            (self.root() / path).read_text(encoding="utf-8")
            for path in self.REQUIRED_DOCS
        ).casefold()
        for forbidden in (
            "perfect cards",
            "完美卡片",
            "no review required",
            "无需审核",
            "complete pdf parsing",
            "完整 pdf 解析",
            "absolute privacy",
            "绝对保护隐私",
        ):
            self.assertNotIn(forbidden, combined)

    @staticmethod
    def root():
        return Path(__file__).parents[1]


if __name__ == "__main__":
    unittest.main()
