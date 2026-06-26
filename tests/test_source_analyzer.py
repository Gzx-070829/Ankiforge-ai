import json
import os
import tempfile
import unittest

from ankiforge_ai.pipeline.source_analyzer import (
    analyze_markdown_file,
    build_chunk_id,
    build_source_chunks,
    build_source_display,
    build_source_document,
    compute_text_hash,
)


class SourceAnalyzerTests(unittest.TestCase):
    def test_text_hash_is_stable(self):
        text = "# Heading\nBody"

        self.assertEqual(compute_text_hash(text), compute_text_hash(text))

    def test_text_hash_changes_when_text_changes(self):
        self.assertNotEqual(compute_text_hash("Body A"), compute_text_hash("Body B"))

    def test_multilevel_markdown_generates_source_chunks(self):
        document = build_source_document(
            "C:/notes/ml.md",
            "# Model\nIntro\n## Overfitting\nDetails\n### Fix\nRegularization",
        )

        chunks = build_source_chunks(
            document,
            "# Model\nIntro\n## Overfitting\nDetails\n### Fix\nRegularization",
        )

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].heading_path, ["Model"])
        self.assertEqual(chunks[1].heading_path, ["Model", "Overfitting"])
        self.assertEqual(chunks[2].heading_path, ["Model", "Overfitting", "Fix"])
        self.assertEqual([chunk.ordinal for chunk in chunks], [0, 1, 2])

    def test_source_display(self):
        self.assertEqual(
            build_source_display("ml.md", ["Model", "Overfitting"]),
            "ml.md > Model > Overfitting",
        )

    def test_chunk_id_is_stable_for_same_input(self):
        chunk_id_a = build_chunk_id("doc1", ["A", "B"], 0, "hash")
        chunk_id_b = build_chunk_id("doc1", ["A", "B"], 0, "hash")

        self.assertEqual(chunk_id_a, chunk_id_b)

    def test_chunk_id_changes_when_chunk_content_hash_changes(self):
        self.assertNotEqual(
            build_chunk_id("doc1", ["A"], 0, compute_text_hash("Body A")),
            build_chunk_id("doc1", ["A"], 0, compute_text_hash("Body B")),
        )

    def test_no_heading_document_generates_untitled_chunk(self):
        document = build_source_document("note.md", "Only body text")

        chunks = build_source_chunks(document, "Only body text")

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].heading_path, ["Untitled"])
        self.assertEqual(chunks[0].heading_level, 0)
        self.assertEqual(chunks[0].source_display, "note.md > Untitled")

    def test_empty_document_generates_root_chunk(self):
        document = build_source_document("empty.md", "")

        chunks = build_source_chunks(document, "")

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].heading_path, ["Untitled"])
        self.assertEqual(chunks[0].text, "")

    def test_models_are_json_serializable(self):
        document = build_source_document("note.md", "# Heading\nBody")
        chunks = build_source_chunks(document, "# Heading\nBody")

        json.dumps(document.to_dict(), ensure_ascii=False)
        json.dumps(chunks[0].to_dict(), ensure_ascii=False)

    def test_analyze_markdown_file_reads_utf8(self):
        path = self._write_md("# Heading\nBody")

        document, chunks = analyze_markdown_file(path)

        self.assertEqual(document.file_name, os.path.basename(path))
        self.assertEqual(chunks[0].heading_path, ["Heading"])
        self.assertEqual(chunks[0].text, "Body")

    def _write_md(self, text):
        fd, path = tempfile.mkstemp(suffix=".md")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path


if __name__ == "__main__":
    unittest.main()
