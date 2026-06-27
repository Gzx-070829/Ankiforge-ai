import json
import unittest
from dataclasses import FrozenInstanceError

from ankiforge_ai.pipeline.ai_provider_contracts import (
    AIProviderError,
    AIProviderMetadata,
    AIProviderResult,
    KnowledgePointExtractionResponse,
    build_knowledge_point_extraction_request,
)
from ankiforge_ai.pipeline.models import SourceChunk


class AIProviderContractTests(unittest.TestCase):
    def test_metadata_is_frozen_and_json_serializable(self):
        metadata = AIProviderMetadata(provider_id="fake", model="fake-v0.5")

        self.assertEqual(
            metadata.to_dict(),
            {"provider_id": "fake", "model": "fake-v0.5"},
        )
        json.dumps(metadata.to_dict())
        with self.assertRaises(FrozenInstanceError):
            metadata.model = "changed"

    def test_metadata_requires_provider_and_model(self):
        with self.assertRaises(ValueError):
            AIProviderMetadata(provider_id="", model="model")
        with self.assertRaises(ValueError):
            AIProviderMetadata(provider_id="provider", model=" ")

    def test_request_copies_source_chunk_metadata(self):
        chunk = self.chunk()
        request = build_knowledge_point_extraction_request(chunk)

        self.assertEqual(request.request_id, "kp_extract_chunk_1")
        self.assertEqual(request.document_id, chunk.document_id)
        self.assertEqual(request.chunk_id, chunk.chunk_id)
        self.assertEqual(request.source_display, chunk.source_display)
        self.assertEqual(request.heading_path, ("机器学习", "过拟合"))
        self.assertEqual(request.text, chunk.text)

        chunk.heading_path.append("后来修改")
        self.assertEqual(request.heading_path, ("机器学习", "过拟合"))

    def test_request_accepts_explicit_request_id_and_serializes(self):
        request = build_knowledge_point_extraction_request(
            self.chunk(),
            request_id="request_123",
        )
        data = request.to_dict()

        self.assertEqual(data["request_id"], "request_123")
        self.assertEqual(data["heading_path"], ["机器学习", "过拟合"])
        json.dumps(data, ensure_ascii=False)

    def test_success_result_contains_response(self):
        response = self.response()
        result = AIProviderResult.from_response(response)

        self.assertTrue(result.success)
        self.assertIs(result.response, response)
        self.assertIsNone(result.error)
        self.assertTrue(result.to_dict()["success"])
        json.dumps(result.to_dict(), ensure_ascii=False)

    def test_failure_result_contains_structured_error(self):
        request = build_knowledge_point_extraction_request(self.chunk())
        error = AIProviderError(
            code="fake_failure",
            message="Injected failure.",
            error_type="FakeProviderError",
            retryable=False,
        )
        result = AIProviderResult.from_error(request, error)

        self.assertFalse(result.success)
        self.assertIsNone(result.response)
        self.assertIs(result.error, error)
        self.assertEqual(result.to_dict()["error"]["code"], "fake_failure")

    def test_result_requires_exactly_one_response_or_error(self):
        response = self.response()
        error = AIProviderError(code="failure", message="Failure")

        with self.assertRaises(ValueError):
            AIProviderResult(request_id="request_1", chunk_id="chunk_1")
        with self.assertRaises(ValueError):
            AIProviderResult(
                request_id="request_1",
                chunk_id="chunk_1",
                response=response,
                error=error,
            )

    def test_result_rejects_mismatched_response_ids(self):
        response = self.response()

        with self.assertRaises(ValueError):
            AIProviderResult(
                request_id="different_request",
                chunk_id=response.chunk_id,
                response=response,
            )
        with self.assertRaises(ValueError):
            AIProviderResult(
                request_id=response.request_id,
                chunk_id="different_chunk",
                response=response,
            )

    def test_result_rejects_wrong_response_or_error_types(self):
        with self.assertRaises(ValueError):
            AIProviderResult(
                request_id="request_1",
                chunk_id="chunk_1",
                response="not a response",
            )
        with self.assertRaises(ValueError):
            AIProviderResult(
                request_id="request_1",
                chunk_id="chunk_1",
                error="not an error",
            )

    def test_error_requires_code_message_and_bool_retryable(self):
        with self.assertRaises(ValueError):
            AIProviderError(code="", message="Failure")
        with self.assertRaises(ValueError):
            AIProviderError(code="failure", message=" ")
        with self.assertRaises(ValueError):
            AIProviderError(
                code="failure",
                message="Failure",
                retryable="no",
            )

    @staticmethod
    def response():
        return KnowledgePointExtractionResponse(
            request_id="request_1",
            chunk_id="chunk_1",
            metadata=AIProviderMetadata(provider_id="fake", model="fake-v0.5"),
            json_text='{"knowledge_points": []}',
        )

    @staticmethod
    def chunk():
        return SourceChunk(
            chunk_id="chunk_1",
            document_id="document_1",
            file_path="C:/notes/机器学习.md",
            file_name="机器学习.md",
            heading_path=["机器学习", "过拟合"],
            heading_level=2,
            ordinal=0,
            text="过拟合会降低模型在未见数据上的泛化能力。",
            chunk_hash="hash",
            source_display="机器学习.md > 机器学习 > 过拟合",
        )


if __name__ == "__main__":
    unittest.main()
