import ast
import copy
import json
import socket
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch, sentinel

from ankiforge_ai.pipeline.ai_extraction_service import (
    KnowledgePointExtractionOutcome,
)
from ankiforge_ai.pipeline.ai_knowledge_extractor_adapter import (
    AIKnowledgePointExtractor,
)
from ankiforge_ai.pipeline.ai_provider_contracts import (
    AIProviderError,
    AIProviderMetadata,
    AIProviderResult,
    KnowledgePointExtractionResponse,
)
from ankiforge_ai.pipeline.fake_ai_provider import FakeAIProvider
from ankiforge_ai.pipeline.models import SourceChunk


class StaticJSONProvider:
    def __init__(self, json_text):
        self.metadata = AIProviderMetadata(provider_id="static", model="test")
        self.json_text = json_text

    def extract(self, request):
        return AIProviderResult.from_response(
            KnowledgePointExtractionResponse(
                request_id=request.request_id,
                chunk_id=request.chunk_id,
                metadata=self.metadata,
                json_text=self.json_text,
            )
        )


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
        return AIProviderResult.from_response(
            KnowledgePointExtractionResponse(
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
        )


class AIKnowledgePointExtractorTests(unittest.TestCase):
    def test_fake_provider_returns_valid_outcome(self):
        outcome = AIKnowledgePointExtractor(FakeAIProvider()).extract_from_chunk(
            self.chunk()
        )

        self.assertIsInstance(outcome, KnowledgePointExtractionOutcome)
        self.assertTrue(outcome.succeeded)
        self.assertEqual(len(outcome.knowledge_points), 1)
        self.assertEqual(outcome.knowledge_points[0].title, "过拟合")

    def test_chinese_content_is_preserved(self):
        chunk = self.chunk()

        outcome = AIKnowledgePointExtractor(FakeAIProvider()).extract_from_chunk(chunk)
        point = outcome.knowledge_points[0]

        self.assertEqual(point.explanation, chunk.text)
        self.assertEqual(point.evidence, chunk.text)
        self.assertEqual(point.source_display, "机器学习.md > 机器学习 > 过拟合")

    def test_whitespace_chunk_is_successful_with_no_points(self):
        for text in ("", "  \n\t "):
            with self.subTest(text=text):
                outcome = AIKnowledgePointExtractor(
                    FakeAIProvider()
                ).extract_from_chunk(self.chunk(text=text))

                self.assertTrue(outcome.succeeded)
                self.assertEqual(outcome.knowledge_points, ())
                self.assertIsNone(outcome.error)

    def test_invalid_json_preserves_structured_error(self):
        outcome = AIKnowledgePointExtractor(
            StaticJSONProvider("{invalid json")
        ).extract_from_chunk(self.chunk())

        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.knowledge_points, ())
        self.assertEqual(outcome.error.code, "invalid_json")
        self.assertEqual(outcome.error.error_type, "invalid_json")
        self.assertEqual(
            outcome.provider_result.response.json_text,
            "{invalid json",
        )

    def test_provider_failure_information_is_preserved(self):
        provider_error = AIProviderError(
            code="provider_failure",
            message="Provider failed.",
            error_type="FakeProviderError",
            retryable=True,
        )
        extractor = AIKnowledgePointExtractor(
            FakeAIProvider(failure=provider_error)
        )

        outcome = extractor.extract_from_chunk(self.chunk())

        self.assertFalse(outcome.succeeded)
        self.assertIs(outcome.error, provider_error)
        self.assertIs(outcome.provider_result.error, provider_error)

    def test_batch_preserves_order_and_partial_failures(self):
        chunks = [
            self.chunk(chunk_id="chunk_1", heading="过拟合"),
            self.chunk(chunk_id="chunk_2", heading="正则化"),
            self.chunk(chunk_id="chunk_3", heading="泛化"),
        ]
        extractor = AIKnowledgePointExtractor(
            MixedResultProvider(failed_chunk_id="chunk_2")
        )

        outcomes = extractor.extract_from_chunks(chunks)

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
        extractor = AIKnowledgePointExtractor(FakeAIProvider())

        self.assertEqual(extractor.extract_from_chunks([]), [])

    def test_input_chunks_are_not_modified(self):
        chunks = [self.chunk(), self.chunk(chunk_id="chunk_2", heading="泛化")]
        before = copy.deepcopy(chunks)

        AIKnowledgePointExtractor(FakeAIProvider()).extract_from_chunks(chunks)

        self.assertEqual(chunks, before)

    def test_single_chunk_delegates_to_pr2_service(self):
        provider = FakeAIProvider()
        chunk = self.chunk()
        extractor = AIKnowledgePointExtractor(provider)

        with patch(
            "ankiforge_ai.pipeline.ai_knowledge_extractor_adapter."
            "extract_knowledge_points",
            return_value=sentinel.outcome,
        ) as service:
            outcome = extractor.extract_from_chunk(chunk)

        self.assertIs(outcome, sentinel.outcome)
        service.assert_called_once_with(chunk, provider)

    def test_batch_delegates_to_pr2_service(self):
        provider = FakeAIProvider()
        chunks = [self.chunk()]
        extractor = AIKnowledgePointExtractor(provider)

        with patch(
            "ankiforge_ai.pipeline.ai_knowledge_extractor_adapter."
            "extract_knowledge_points_from_chunks",
            return_value=sentinel.outcomes,
        ) as service:
            outcomes = extractor.extract_from_chunks(chunks)

        self.assertIs(outcomes, sentinel.outcomes)
        service.assert_called_once_with(chunks, provider)

    def test_adapter_does_not_access_network(self):
        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Network access is not allowed."),
        ), patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Network access is not allowed."),
        ):
            outcome = AIKnowledgePointExtractor(
                FakeAIProvider()
            ).extract_from_chunk(self.chunk())

        self.assertTrue(outcome.succeeded)

    def test_adapter_module_has_no_forbidden_dependencies(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "ai_knowledge_extractor_adapter.py"
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
        self.assertNotIn("CardCandidate", source)
        self.assertNotIn("HumanReview", source)
        self.assertNotIn("self.cards", source)
        self.assertNotIn("parse_knowledge_points_json", source)

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
