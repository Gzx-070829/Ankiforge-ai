import hashlib
import json
import re
import struct
import unittest
from pathlib import Path


class ProductGradeReleaseAssetTests(unittest.TestCase):
    SCREENSHOTS = (
        "01_zh_default_empty.png",
        "02_ai_settings_dialog.png",
        "03_ai_configured_main.png",
        "04_generation_settings_expanded.png",
        "05_help_dialog.png",
        "06_en_default_empty.png",
        "07_example_loaded.png",
        "08_review_workbench.png",
        "09_warning_blocking_cards.png",
        "10_write_summary_ready.png",
        "11_final_confirmation.png",
    )

    STATES = (
        "zh-default",
        "ai-settings",
        "configured",
        "generation-expanded",
        "help",
        "en-default",
        "example-loaded",
        "review-workbench",
        "quality-alerts",
        "write-ready",
        "final-confirmation",
    )

    def test_preview_is_explicitly_offline_and_mocked(self):
        text = self.read_preview()
        lowered = text.casefold()

        self.assertIn("ui preview / mock", lowered)
        self.assertIn("not real anki acceptance", lowered)
        self.assertNotIn("http://", lowered)
        self.assertNotIn("https://", lowered)
        for forbidden in ("fetch(", "xmlhttprequest", "websocket", "sendbeacon"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, lowered)
        for state in self.STATES:
            with self.subTest(state=state):
                self.assertIn(state, text)

    def test_main_workbench_has_linear_flow_without_provider_fields(self):
        text = self.read_preview()
        match = re.search(
            r'<main id="main-workbench".*?</main>', text, flags=re.DOTALL
        )
        self.assertIsNotNone(match)
        workbench = match.group(0).casefold()

        self.assertIn("create-panel", workbench)
        self.assertIn("review-panel", workbench)
        self.assertIn("write-footer", workbench)
        self.assertNotIn("provider", workbench)
        self.assertNotIn("api key", workbench)
        self.assertNotIn("model", workbench)
        self.assertNotIn("卡片模板", workbench)
        self.assertNotIn(">template<", workbench)
        self.assertNotIn("保留 clean cards", workbench)
        self.assertIn("保留可用卡片", workbench)

    def test_ai_settings_has_one_key_hint_and_no_second_session_note(self):
        text = self.read_preview()
        match = re.search(
            r'<section class="dialog" aria-label="AI settings preview mock">'
            r'.*?</section>',
            text,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        dialog = match.group(0)
        self.assertEqual(dialog.count("仅本次使用，不会保存。"), 1)
        self.assertNotIn("session-note", dialog)

    def test_asset_manifest_binds_preview_and_screenshot_hashes(self):
        manifest_path = self.screenshot_dir / "manifest.json"
        self.assertTrue(manifest_path.is_file(), "Missing screenshot manifest")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertTrue(manifest["offline_ui_preview_mock"])
        self.assertEqual(
            manifest["preview_sha256"], self.sha256(self.preview)
        )
        self.assertEqual(set(manifest["screenshots"]), set(self.SCREENSHOTS))
        for filename, state in zip(self.SCREENSHOTS, self.STATES):
            with self.subTest(filename=filename):
                entry = manifest["screenshots"][filename]
                self.assertEqual(entry["state"], state)
                self.assertEqual(entry["width"], 1440)
                self.assertEqual(entry["height"], 900)
                self.assertEqual(
                    entry["sha256"], self.sha256(self.screenshot_dir / filename)
                )

    def test_all_release_screenshots_are_1440_by_900_pngs(self):
        for filename in self.SCREENSHOTS:
            path = self.screenshot_dir / filename
            with self.subTest(filename=filename):
                self.assertTrue(path.is_file(), f"Missing screenshot: {filename}")
                # Chrome's offline error page is a valid 1440x900 PNG but is
                # much smaller than the rendered product workbench.
                self.assertGreater(path.stat().st_size, 25_000)
                self.assertEqual(self.png_dimensions(path), (1440, 900))

    @property
    def root(self):
        return Path(__file__).parents[1]

    @property
    def preview(self):
        return self.root / "docs" / "assets" / "ui_preview_v0_13.html"

    @property
    def screenshot_dir(self):
        return self.root / "docs" / "assets" / "screenshots" / "v0_13"

    def read_preview(self):
        self.assertTrue(self.preview.is_file(), "Missing offline UI preview")
        return self.preview.read_text(encoding="utf-8")

    @staticmethod
    def png_dimensions(path):
        with path.open("rb") as handle:
            signature = handle.read(8)
            if signature != b"\x89PNG\r\n\x1a\n":
                raise AssertionError(f"Not a PNG: {path}")
            length = struct.unpack(">I", handle.read(4))[0]
            chunk_type = handle.read(4)
            if length != 13 or chunk_type != b"IHDR":
                raise AssertionError(f"Missing PNG IHDR: {path}")
            width, height = struct.unpack(">II", handle.read(8))
            return width, height

    @staticmethod
    def sha256(path):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65_536), b""):
                digest.update(chunk)
        return digest.hexdigest().upper()


if __name__ == "__main__":
    unittest.main()
