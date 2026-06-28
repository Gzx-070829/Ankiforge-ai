import ast
import copy
import socket
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.ai_extraction_service import extract_knowledge_points
from ankiforge_ai.pipeline.ai_provider_contracts import (
    AIProviderError,
    AIProviderMetadata,
    AIProviderResult,
    KnowledgePointExtractionResponse,
    KnowledgePointJSONProvider,
    build_knowledge_point_extraction_request,
)
from ankiforge_ai.pipeline.fake_ai_provider import FakeAIProvider
from ankiforge_ai.pipeline.models import SourceChunk
from ankiforge_ai.pipeline.provider_safety_wrapper import (
    SafeKnowledgePointJSONProvider,
)


class FixedResultProvider:
    def __init__(self, result):
        self.metadata = AIProviderMetadata(provider_id="fixed", model="test")
        self.result = result

    def extract(self, request):
        return self.result


class RaisingProvider:
    def __init__(self, exception):
        self.metadata = AIProviderMetadata(provider_id="raising", model="test")
        self.exception = exception

    def extract(self, request):
        raise self.exception


class ProviderSafetyWrapperTests(unittest.TestCase):
    def test_metadata_is_proxied_from_inner_provider(self):
        inner = FakeAIProvider()
        wrapper = SafeKnowledgePointJSONProvider(inner)

        self.assertIs(wrapper.metadata, inner.metadata)
        self.assertIsInstance(wrapper, KnowledgePointJSONProvider)

    def test_success_result_is_returned_by_identity(self):
        request = build_knowledge_point_extraction_request(self.chunk())
        result = AIProviderResult.from_response(
            KnowledgePointExtractionResponse(
                request_id=request.request_id,
                chunk_id=request.chunk_id,
                metadata=AIProviderMetadata(provider_id="fixed", model="test"),
                json_text='{"knowledge_points": []}',
            )
        )
        wrapper = SafeKnowledgePointJSONProvider(FixedResultProvider(result))

        self.assertIs(wrapper.extract(request), result)

    def test_failure_result_and_error_are_returned_by_identity(self):
        request = build_knowledge_point_extraction_request(self.chunk())
        error = AIProviderError(
            code="provider_failure",
            message="Existing structured failure.",
            error_type="existing",
            retryable=True,
        )
        result = AIProviderResult.from_error(request, error)
        wrapper = SafeKnowledgePointJSONProvider(FixedResultProvider(result))

        returned = wrapper.extract(request)

        self.assertIs(returned, result)
        self.assertIs(returned.error, error)

    def test_direct_exception_becomes_structured_failure(self):
        request = build_knowledge_point_extraction_request(self.chunk())
        wrapper = SafeKnowledgePointJSONProvider(
            RaisingProvider(RuntimeError("private provider details"))
        )

        result = wrapper.extract(request)

        self.assertFalse(result.success)
        self.assertEqual(result.request_id, request.request_id)
        self.assertEqual(result.chunk_id, request.chunk_id)
        self.assertEqual(result.error.code, "provider_exception")
        self.assertEqual(result.error.error_type, "unknown")
        self.assertFalse(result.error.retryable)

    def test_exception_message_is_diagnostic_and_redacted(self):
        chunk = self.chunk(text="用户的私密学习资料")
        request = build_knowledge_point_extraction_request(chunk)
        secret = "secret-token-123"
        wrapper = SafeKnowledgePointJSONProvider(
            RaisingProvider(RuntimeError(f"credential={secret}; {chunk.text}"))
        )

        result = wrapper.extract(request)
        message = result.error.message

        self.assertIn("raising", message)
        self.assertIn("RuntimeError", message)
        self.assertIn(request.request_id, message)
        self.assertIn(request.chunk_id, message)
        self.assertNotIn(secret, message)
        self.assertNotIn(chunk.text, message)
        self.assertNotIn("credential=", message)

    def test_base_exception_is_not_caught(self):
        request = build_knowledge_point_extraction_request(self.chunk())
        wrapper = SafeKnowledgePointJSONProvider(RaisingProvider(KeyboardInterrupt()))

        with self.assertRaises(KeyboardInterrupt):
            wrapper.extract(request)

    def test_pr2_service_receives_failed_outcome_instead_of_exception(self):
        chunk = self.chunk()
        wrapper = SafeKnowledgePointJSONProvider(
            RaisingProvider(RuntimeError("provider crashed"))
        )

        outcome = extract_knowledge_points(chunk, wrapper)

        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.knowledge_points, ())
        self.assertEqual(outcome.error.code, "provider_exception")
        self.assertIs(outcome.error, outcome.provider_result.error)

    def test_successful_fake_provider_still_parses_through_pr2_service(self):
        outcome = extract_knowledge_points(
            self.chunk(),
            SafeKnowledgePointJSONProvider(FakeAIProvider()),
        )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(len(outcome.knowledge_points), 1)
        self.assertEqual(outcome.knowledge_points[0].title, "过拟合")

    def test_wrapper_does_not_modify_input(self):
        chunk = self.chunk()
        request = build_knowledge_point_extraction_request(chunk)
        before_chunk = copy.deepcopy(chunk)
        before_request = copy.deepcopy(request)

        SafeKnowledgePointJSONProvider(
            RaisingProvider(RuntimeError("failure"))
        ).extract(request)

        self.assertEqual(chunk, before_chunk)
        self.assertEqual(request, before_request)

    def test_wrapper_does_not_access_network(self):
        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Network access is not allowed."),
        ), patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Network access is not allowed."),
        ):
            outcome = extract_knowledge_points(
                self.chunk(),
                SafeKnowledgePointJSONProvider(FakeAIProvider()),
            )

        self.assertTrue(outcome.succeeded)

    def test_wrapper_module_has_no_forbidden_dependencies(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "provider_safety_wrapper.py"
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

    @staticmethod
    def chunk(text="过拟合会降低模型在未见数据上的泛化能力。"):
        return SourceChunk(
            chunk_id="chunk_1",
            document_id="document_1",
            file_path="C:/notes/机器学习.md",
            file_name="机器学习.md",
            heading_path=["机器学习", "过拟合"],
            heading_level=2,
            ordinal=0,
            text=text,
            chunk_hash="hash",
            source_display="机器学习.md > 机器学习 > 过拟合",
        )


if __name__ == "__main__":
    unittest.main()
