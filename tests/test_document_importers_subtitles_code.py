import unittest
from pathlib import Path

from ankiforge_ai.document import BlockKind
from ankiforge_ai.document.importers.code_text import CodeTextImporter
from ankiforge_ai.document.importers.subtitles import SubtitleImporter


FIXTURES = Path(__file__).parent / "fixtures" / "documents"


class DocumentSubtitleCodeImporterTests(unittest.TestCase):
    def test_srt_merges_adjacent_captions_with_bounded_timestamp_location(self):
        document = SubtitleImporter.for_path(FIXTURES / "captions.srt").import_document(
            FIXTURES / "captions.srt"
        )
        block = document.sections[0].blocks[0]
        self.assertEqual(block.kind, BlockKind.TRANSCRIPT)
        self.assertEqual(block.text, "First caption.\nSecond caption.")
        self.assertEqual(block.location.timestamp_start, 1.0)
        self.assertEqual(block.location.timestamp_end, 4.0)

    def test_vtt_produces_transcript_locations(self):
        document = SubtitleImporter.for_path(FIXTURES / "captions.vtt").import_document(
            FIXTURES / "captions.vtt"
        )
        self.assertTrue(document.sections[0].blocks)
        self.assertTrue(
            all(
                block.kind is BlockKind.TRANSCRIPT
                and block.location.timestamp_start is not None
                for block in document.sections[0].blocks
            )
        )

    def test_every_listed_code_extension_is_preserved_as_code_comment_groups(self):
        filenames = (
            "sample.py",
            "sample.js",
            "sample.ts",
            "Sample.java",
            "sample.c",
            "sample.h",
            "sample.cpp",
            "sample.cc",
            "sample.rs",
            "sample.go",
            "sample.sql",
            "sample.sh",
            "sample.ps1",
        )
        for filename in filenames:
            with self.subTest(filename=filename):
                document = CodeTextImporter.for_path(FIXTURES / filename).import_document(
                    FIXTURES / filename
                )
                blocks = document.sections[0].blocks
                self.assertTrue(blocks)
                self.assertTrue(all(block.kind is BlockKind.CODE for block in blocks))
                self.assertEqual(blocks[0].location.line_start, 1)
                self.assertLessEqual(
                    blocks[-1].location.line_end,
                    len((FIXTURES / filename).read_text(encoding="utf-8").splitlines()),
                )


if __name__ == "__main__":
    unittest.main()
