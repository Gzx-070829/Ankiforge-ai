import unittest

from ankiforge_ai.pipeline.knowledge_extractor import (
    MockKnowledgePointExtractor,
    extract_knowledge_points_from_chunks,
)
from ankiforge_ai.pipeline.models import KnowledgePoint, SourceChunk


class MockKnowledgePointExtractorTests(unittest.TestCase):
    def setUp(self):
        self.extractor = MockKnowledgePointExtractor()

    def test_returns_knowledge_point_objects(self):
        points = self.extractor.extract_from_chunk(self.chunk())

        self.assertEqual(len(points), 1)
        self.assertIsInstance(points[0], KnowledgePoint)
        self.assertEqual(points[0].title, "Overfitting")
        self.assertEqual(points[0].tags, ["mock"])

    def test_metadata_is_inherited_from_source_chunk(self):
        chunk = self.chunk()

        point = self.extractor.extract_from_chunk(chunk)[0]

        self.assertEqual(point.document_id, chunk.document_id)
        self.assertEqual(point.chunk_id, chunk.chunk_id)
        self.assertEqual(point.source_display, chunk.source_display)
        self.assertEqual(point.heading_path, chunk.heading_path)

    def test_service_processes_multiple_chunks_in_order(self):
        first = self.chunk(chunk_id="chunk-1", heading="First", ordinal=0)
        second = self.chunk(chunk_id="chunk-2", heading="Second", ordinal=1)

        points = extract_knowledge_points_from_chunks(
            [first, second],
            self.extractor,
        )

        self.assertEqual(len(points), 2)
        self.assertEqual([point.chunk_id for point in points], ["chunk-1", "chunk-2"])
        self.assertEqual([point.title for point in points], ["First", "Second"])

    def test_empty_chunk_list_returns_empty_list(self):
        points = extract_knowledge_points_from_chunks([], self.extractor)

        self.assertEqual(points, [])

    def test_extraction_is_deterministic(self):
        chunk = self.chunk()

        first = self.extractor.extract_from_chunk(chunk)
        second = self.extractor.extract_from_chunk(chunk)

        self.assertEqual(first, second)
        self.assertEqual(first[0].point_id, second[0].point_id)

    def test_empty_or_whitespace_chunk_returns_empty_list(self):
        self.assertEqual(self.extractor.extract_from_chunk(self.chunk(text="")), [])
        self.assertEqual(self.extractor.extract_from_chunk(self.chunk(text="  \n\t")), [])

    def test_missing_heading_uses_untitled_title(self):
        chunk = self.chunk()
        chunk.heading_path = []

        points = self.extractor.extract_from_chunk(chunk)

        self.assertEqual(points[0].title, "Untitled")

    def chunk(
        self,
        chunk_id="chunk-1",
        heading="Overfitting",
        ordinal=0,
        text="Overfitting memorizes training noise.",
    ):
        return SourceChunk(
            chunk_id=chunk_id,
            document_id="doc-1",
            file_path="C:/notes/ml.md",
            file_name="ml.md",
            heading_path=["Models", heading],
            heading_level=2,
            ordinal=ordinal,
            text=text,
            chunk_hash="hash",
            source_display=f"ml.md > Models > {heading}",
        )


if __name__ == "__main__":
    unittest.main()
