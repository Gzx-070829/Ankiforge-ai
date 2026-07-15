import tempfile
import unittest
from pathlib import Path

from ankiforge_ai.importers.source_import import (
    import_markdown_file,
    parse_markdown_frontmatter,
)


class SourceImportProductGradeTests(unittest.TestCase):
    def test_frontmatter_title_becomes_label_and_is_removed_from_body(self):
        text = "---\ntitle: SQL JOIN 复习\ntags: [sql]\n---\n# JOIN\nINNER JOIN 只保留匹配行。"

        parsed = parse_markdown_frontmatter(text)

        self.assertEqual(parsed.title, "SQL JOIN 复习")
        self.assertEqual(parsed.body, "# JOIN\nINNER JOIN 只保留匹配行。")

    def test_normal_markdown_is_unchanged(self):
        text = "# 标题\n正文"
        parsed = parse_markdown_frontmatter(text)
        self.assertIsNone(parsed.title)
        self.assertEqual(parsed.body, text)

    def test_unsafe_or_multiline_title_is_ignored(self):
        parsed = parse_markdown_frontmatter(
            "---\ntitle: C:\\Users\\person\\private.md\n---\n正文"
        )
        self.assertIsNone(parsed.title)
        self.assertEqual(parsed.body, "正文")

    def test_markdown_import_uses_safe_title_without_full_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.md"
            path.write_text("---\ntitle: 数据库连接\n---\n连接用于组合表。", encoding="utf-8")

            imported = import_markdown_file(path)

        self.assertEqual(imported.source_label, "数据库连接")
        self.assertEqual(imported.text, "连接用于组合表。")
        self.assertNotIn(directory, repr(imported))


if __name__ == "__main__":
    unittest.main()
