import json
import hashlib
import struct
import unittest
from pathlib import Path

import ankiforge_ai


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_VERSION = "0.14.1"
REQUIRED_DOCS = (
    "README.md", "README.en.md", "docs/getting_started.md", "docs/importing_materials.md", "docs/document_ir.md", "docs/native_supported_formats.md", "docs/optional_document_backends.md", "docs/docling_setup.md", "docs/markitdown_setup.md", "docs/pandoc_setup.md", "docs/document_security.md", "docs/intelligence_levels.md", "docs/knowledge_planning.md", "docs/chunking_and_source_traceability.md", "docs/ai_cost_and_call_budget.md", "docs/deck_style_profile.md", "docs/troubleshooting.md", "docs/manual_anki_acceptance.md", "docs/release_notes_v0_14.md", "docs/ankiweb_description_v0_14.md", "docs/future_document_engine_companion.md", "docs/third_party_notices.md",
)


class V014ReleaseContractTests(unittest.TestCase):
    def test_v014_required_docs_remain_available(self):
        for relative_path in REQUIRED_DOCS:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())
        for relative_path in (
            "docs/release_notes_v0_14.md",
            "docs/ankiweb_description_v0_14.md",
        ):
            self.assertIn(
                HISTORICAL_VERSION,
                (ROOT / relative_path).read_text(encoding="utf-8"),
            )

    def test_preview_and_manifest_are_offline_mock_release_assets(self):
        preview = ROOT / "docs" / "assets" / "ui_preview_v0_14.html"
        manifest_path = ROOT / "docs" / "assets" / "screenshots" / "v0_14" / "manifest.json"
        self.assertTrue(preview.is_file())
        self.assertTrue(manifest_path.is_file())
        text = preview.read_text(encoding="utf-8")
        self.assertIn("Mock UI preview — not a live Anki or Provider session", text)
        for forbidden in ("http://", "https://", "fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon"):
            self.assertNotIn(forbidden, text)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertTrue(manifest["offline_ui_preview_mock"])
        self.assertFalse(manifest["network_used"])
        self.assertFalse(manifest["anki_or_provider_called"])
        self.assertEqual(len(manifest["screenshots"]), 13)
        canonical = preview.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        self.assertEqual(hashlib.sha256(canonical).hexdigest().upper(), manifest["preview_sha256"])

    def test_each_mock_screenshot_has_the_recorded_viewport_and_hash(self):
        screenshot_dir = ROOT / "docs" / "assets" / "screenshots" / "v0_14"
        manifest = json.loads((screenshot_dir / "manifest.json").read_text(encoding="utf-8"))
        expected = (
            "01_zh_default_main.png", "02_multi_file_queue.png", "03_document_overview.png",
            "04_capabilities_dialog.png", "05_auto_mode_recommendation.png", "06_standard_plan_estimate.png",
            "07_deep_call_confirmation.png", "08_stage_progress.png", "09_review_source_chips.png",
            "10_partial_failure_retry.png", "11_en_default_main.png", "12_backend_missing.png",
            "13_backend_available.png",
        )
        self.assertEqual(tuple(manifest["screenshots"]), expected)
        for filename, entry in manifest["screenshots"].items():
            with self.subTest(filename=filename):
                image = screenshot_dir / filename
                self.assertTrue(image.is_file())
                with image.open("rb") as handle:
                    self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n")
                    handle.read(4)
                    self.assertEqual(handle.read(4), b"IHDR")
                    self.assertEqual(struct.unpack(">II", handle.read(8)), (1440, 900))
                self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest().upper(), entry["sha256"])


if __name__ == "__main__":
    unittest.main()
