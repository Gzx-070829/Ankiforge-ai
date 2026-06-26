import os
import tempfile
import unittest

from ankiforge_ai.importers.md_importer import split_markdown_by_headings


class MarkdownImporterTests(unittest.TestCase):
    def test_splits_intro_and_headings(self):
        path = self._write_md(
            "\n".join(
                [
                    "Intro paragraph",
                    "# First",
                    "First body",
                    "```python",
                    "# not a heading",
                    "```",
                    "## Second ###",
                    "Second body",
                ]
            )
        )

        chunks = split_markdown_by_headings(path)

        self.assertEqual([chunk.heading for chunk in chunks], ["Untitled", "First", "Second"])
        self.assertEqual([chunk.level for chunk in chunks], [0, 1, 2])
        self.assertIn("# not a heading", chunks[1].content)
        self.assertEqual(chunks[2].content, "Second body")

    def test_no_heading_file_becomes_untitled(self):
        path = self._write_md("Only body text\nwithout a heading")

        chunks = split_markdown_by_headings(path)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].heading, "Untitled")
        self.assertEqual(chunks[0].content, "Only body text\nwithout a heading")

    def test_empty_heading_chunks_are_skipped(self):
        path = self._write_md("# Empty\n## Full\nBody")

        chunks = split_markdown_by_headings(path)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].heading, "Full")

    def _write_md(self, text):
        fd, path = tempfile.mkstemp(suffix=".md")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path


if __name__ == "__main__":
    unittest.main()
