import json
import unittest

from ankiforge_ai.pipeline.knowledge_points import (
    build_knowledge_point_id,
    parse_knowledge_points_json,
    parse_knowledge_points_payload,
)
from ankiforge_ai.pipeline.models import SourceChunk


class KnowledgePointTests(unittest.TestCase):
    def test_parse_list_payload(self):
        points = parse_knowledge_points_payload(
            [
                {
                    "title": "Overfitting",
                    "explanation": "The model memorizes training noise.",
                    "evidence": "training noise",
                    "tags": ["ml", "generalization"],
                    "importance": "high",
                }
            ],
            self.chunk(),
        )

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].title, "Overfitting")
        self.assertEqual(points[0].importance, "high")

    def test_parse_object_payload(self):
        text = json.dumps(
            {
                "knowledge_points": [
                    {
                        "title": "Regularization",
                        "explanation": "A method to reduce overfitting.",
                    }
                ]
            }
        )

        points = parse_knowledge_points_json(text, self.chunk())

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].title, "Regularization")

    def test_metadata_inherited_from_source_chunk(self):
        chunk = self.chunk()

        points = parse_knowledge_points_payload(
            [{"title": "T", "explanation": "E"}],
            chunk,
        )

        point = points[0]
        self.assertEqual(point.document_id, chunk.document_id)
        self.assertEqual(point.chunk_id, chunk.chunk_id)
        self.assertEqual(point.source_display, chunk.source_display)
        self.assertEqual(point.heading_path, chunk.heading_path)
        self.assertEqual(point.ordinal, 0)

    def test_defaults(self):
        points = parse_knowledge_points_payload(
            [{"title": "T", "explanation": "E"}],
            self.chunk(),
        )

        point = points[0]
        self.assertEqual(point.tags, [])
        self.assertEqual(point.importance, "medium")
        self.assertEqual(point.evidence, "")

    def test_invalid_json(self):
        with self.assertRaises(ValueError):
            parse_knowledge_points_json("{not json", self.chunk())

    def test_invalid_payload_shape(self):
        with self.assertRaises(ValueError):
            parse_knowledge_points_payload({"knowledge_points": "bad"}, self.chunk())

        with self.assertRaises(ValueError):
            parse_knowledge_points_payload("bad", self.chunk())

    def test_missing_title(self):
        with self.assertRaises(ValueError):
            parse_knowledge_points_payload(
                [{"title": "", "explanation": "E"}],
                self.chunk(),
            )

    def test_missing_explanation(self):
        with self.assertRaises(ValueError):
            parse_knowledge_points_payload(
                [{"title": "T", "explanation": ""}],
                self.chunk(),
            )

    def test_tags_must_be_list(self):
        with self.assertRaises(ValueError):
            parse_knowledge_points_payload(
                [{"title": "T", "explanation": "E", "tags": "ml"}],
                self.chunk(),
            )

    def test_to_dict_is_json_serializable(self):
        points = parse_knowledge_points_payload(
            [{"title": "T", "explanation": "E", "tags": ["ml"]}],
            self.chunk(),
        )

        data = points[0].to_dict()

        self.assertEqual(data["title"], "T")
        json.dumps(data, ensure_ascii=False)

    def test_point_id_is_deterministic_and_changes_with_content(self):
        same_a = build_knowledge_point_id("chunk1", 0, "T", "E")
        same_b = build_knowledge_point_id("chunk1", 0, "T", "E")
        changed = build_knowledge_point_id("chunk1", 0, "T", "Different")

        self.assertEqual(same_a, same_b)
        self.assertTrue(same_a.startswith("kp_chunk1_0_"))
        self.assertNotEqual(same_a, changed)

    def chunk(self):
        return SourceChunk(
            chunk_id="chunk1",
            document_id="doc1",
            file_path="C:/notes/ml.md",
            file_name="ml.md",
            heading_path=["Model", "Overfitting"],
            heading_level=2,
            ordinal=0,
            text="Chunk text",
            chunk_hash="hash",
            source_display="ml.md > Model > Overfitting",
        )


if __name__ == "__main__":
    unittest.main()
