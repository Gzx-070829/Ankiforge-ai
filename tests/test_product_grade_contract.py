import json
import unittest
from pathlib import Path

import ankiforge_ai


class ProductGradeContractTests(unittest.TestCase):
    def test_runtime_manifest_and_target_version_are_synchronized(self):
        manifest = json.loads(
            (self.root / "ankiforge_ai" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(ankiforge_ai.__version__, "0.13.0")
        self.assertEqual(manifest["version"], "0.13.0")

    def test_master_plan_covers_every_product_boundary(self):
        text = (
            self.root / "docs" / "product_grade_master_plan.md"
        ).read_text(encoding="utf-8").casefold()

        for term in (
            "终局定位",
            "ai 设置 modal",
            "card quality v4",
            "review workbench v4",
            "field mapping v3",
            "write safety v3",
            "local benchmark",
            "open source governance",
            "manual acceptance",
            "future roadmap",
            "full undo",
            "deferred",
        ):
            self.assertIn(term, text)

    def test_master_plan_has_no_placeholders_or_exaggerated_claims(self):
        text = (
            self.root / "docs" / "product_grade_master_plan.md"
        ).read_text(encoding="utf-8").casefold()

        for forbidden in (
            "tbd",
            "todo",
            "完美卡片",
            "无需审核",
            "保证绝对隐私",
            "完整 pdf 解析",
        ):
            self.assertNotIn(forbidden, text)

    @property
    def root(self):
        return Path(__file__).parents[1]


if __name__ == "__main__":
    unittest.main()
