import ast
import copy
import json
import unittest
from pathlib import Path

from ankiforge_ai.pipeline.ai_extraction_service import (
    KnowledgePointExtractionOutcome,
    extract_knowledge_points,
    extract_knowledge_points_from_chunks,
)
from ankiforge_ai.pipeline.ai_provider_contracts import (
    AIProviderError,
    AIProviderMetadata,
    AIProviderResult,
    KnowledgePointExtractionResponse,
)
from ankiforge_ai.pipeline.fake_ai_provider import FakeAIProvider
from ankiforge_ai.pipeline.models import KnowledgePoint, SourceChunk


class StaticJSONProvider:
    def __init__(self, json_by_chunk):
        self.metadata = AIProviderMetadata(provider_id="static", model="test")
        self.json_by_chunk = dict(json_by_chunk)

    def extract(self, request):
        response = KnowledgePointExtractionResponse(
            request_id=request.request_id,
            chunk_id=request.chunk_id,
            metadata=self.metadata,
            json_text=self.json_by_chunk[request.chunk_id],
        )
        return AIProviderResult.from_response(response)


class MixedResultProvider:
    def __init__(self, failed_chunk_id):
        self.metadata = AIProviderMetadata(provider_id="mixed", model="test")
        self.failed_chunk_id = failed_chunk_id

    def extract(self, request):
        if request.chunk_id == self.failed_chunk_id:
            return AIProviderResult.from_error(
                request,
                AIProviderError(
                    code="provider_failure",
                    message="Injected provider failure.",
                    error_type="FakeProviderError",
                    retryable=True,
                ),
            )
        response = KnowledgePointExtractionResponse(
            request_id=request.request_id,
            chunk_id=request.chunk_id,
            metadata=self.metadata,
            json_text=json.dumps(
                {
                    "knowledge_points": [
                        {
                            "title": request.heading_path[-1],
                            "explanation": request.text,
                        }
                    ]
                },
                ensure_ascii=False,
            ),
        )
        return AIProviderResult.from_response(response)


class AIExtractionServiceTests(unittest.TestCase):
    def test_valid_json_parses_into_knowledge_points(self):
        chunk = self.chunk()
        outcome = extract_knowledge_points(chunk, FakeAIProvider())

        self.assertIsInstance(outcome, KnowledgePointExtractionOutcome)
        self.assertTrue(outcome.succeeded)
        self.assertIsNone(outcome.error)
        self.assertEqual(len(outcome.knowledge_points), 1)
        self.assertIsInstance(outcome.knowledge_points[0], KnowledgePoint)
        self.assertEqual(outcome.knowledge_points[0].chunk_id, chunk.chunk_id)

    def test_chinese_content_is_preserved_by_validator(self):
        chunk = self.chunk()
        outcome = extract_knowledge_points(chunk, FakeAIProvider())
        point = outcome.knowledge_points[0]

        self.assertEqual(point.title, "过拟合")
        self.assertEqual(point.explanation, chunk.text)
        self.assertEqual(point.evidence, chunk.text)
        self.assertEqual(point.source_display, chunk.source_display)

    def test_whitespace_chunk_succeeds_with_no_knowledge_points(self):
        for text in ("", "  \n\t "):
            with self.subTest(text=text):
                outcome = extract_knowledge_points(
                    self.chunk(text=text),
                    FakeAIProvider(),
                )

                self.assertTrue(outcome.succeeded)
                self.assertEqual(outcome.knowledge_points, ())
                self.assertIsNone(outcome.error)

    def test_invalid_json_returns_structured_error_and_preserves_response(self):
        chunk = self.chunk()
        provider = StaticJSONProvider({chunk.chunk_id: "{not valid json"})

        outcome = extract_knowledge_points(chunk, provider)

        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.knowledge_points, ())
        self.assertEqual(outcome.error.code, "invalid_json")
        self.assertEqual(outcome.error.error_type, "invalid_json")
        self.assertFalse(outcome.error.retryable)
        self.assertTrue(outcome.provider_result.success)
        self.assertEqual(
            outcome.provider_result.response.json_text,
            "{not valid json",
        )

    def test_validator_failure_does_not_return_partial_results(self):
        chunk = self.chunk()
        provider = StaticJSONProvider(
            {
                chunk.chunk_id: json.dumps(
                    {
                        "knowledge_points": [
                            {"title": "Valid", "explanation": "Valid explanation"},
                            {"title": "Missing explanation"},
                        ]
                    }
                )
            }
        )

        outcome = extract_knowledge_points(chunk, provider)

        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.error.code, "invalid_json")
        self.assertEqual(outcome.knowledge_points, ())

    def test_provider_failure_is_preserved_without_parsing(self):
        chunk = self.chunk()
        provider_error = AIProviderError(
            code="fake_failure",
            message="Injected failure.",
            error_type="FakeProviderError",
            retryable=True,
        )
        provider = FakeAIProvider(failure=provider_error)

        outcome = extract_knowledge_points(chunk, provider)

        self.assertFalse(outcome.succeeded)
        self.assertIs(outcome.error, provider_error)
        self.assertIs(outcome.provider_result.error, provider_error)
        self.assertIsNone(outcome.provider_result.response)
        self.assertEqual(outcome.knowledge_points, ())

    def test_batch_preserves_order_and_individual_failures(self):
        chunks = [
            self.chunk(chunk_id="chunk_1", heading="过拟合"),
            self.chunk(chunk_id="chunk_2", heading="正则化"),
            self.chunk(chunk_id="chunk_3", heading="泛化"),
        ]
        outcomes = extract_knowledge_points_from_chunks(
            chunks,
            MixedResultProvider(failed_chunk_id="chunk_2"),
        )

        self.assertEqual(
            [outcome.request.chunk_id for outcome in outcomes],
            ["chunk_1", "chunk_2", "chunk_3"],
        )
        self.assertEqual(
            [outcome.succeeded for outcome in outcomes],
            [True, False, True],
        )
        self.assertEqual(outcomes[1].error.code, "provider_failure")
        self.assertEqual(outcomes[2].knowledge_points[0].title, "泛化")

    def test_empty_batch_returns_empty_list(self):
        self.assertEqual(
            extract_knowledge_points_from_chunks([], FakeAIProvider()),
            [],
        )

    def test_service_does_not_modify_source_chunk(self):
        chunk = self.chunk()
        before = copy.deepcopy(chunk)

        outcome = extract_knowledge_points(chunk, FakeAIProvider())

        self.assertEqual(chunk, before)
        self.assertEqual(outcome.request.heading_path, tuple(before.heading_path))

    def test_outcome_is_json_serializable(self):
        outcome = extract_knowledge_points(self.chunk(), FakeAIProvider())

        data = outcome.to_dict()

        self.assertTrue(data["succeeded"])
        self.assertEqual(len(data["knowledge_points"]), 1)
        json.dumps(data, ensure_ascii=False)

    def test_service_module_has_no_forbidden_imports(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "ai_extraction_service.py"
        )
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        imported_modules.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        forbidden = (
            "aqt",
            "anki",
            "PyQt",
            "urllib",
            "socket",
            "config",
            "anki_writer",
        )

        self.assertFalse(
            any(
                module.startswith(prefix)
                for module in imported_modules
                for prefix in forbidden
            )
        )
        self.assertNotIn("api_key", source.lower())
        self.assertNotIn("GeneratedCard", source)
        self.assertNotIn("self.cards", source)

    @staticmethod
    def chunk(
        text="过拟合会降低模型在未见数据上的泛化能力。",
        chunk_id="chunk_1",
        heading="过拟合",
    ):
        return SourceChunk(
            chunk_id=chunk_id,
            document_id="document_1",
            file_path="C:/notes/机器学习.md",
            file_name="机器学习.md",
            heading_path=["机器学习", heading],
            heading_level=2,
            ordinal=0,
            text=text,
            chunk_hash="hash",
            source_display=f"机器学习.md > 机器学习 > {heading}",
        )


if __name__ == "__main__":
    unittest.main()
