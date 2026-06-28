import ast
import copy
import json
import socket
import unittest
import urllib.request
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.ai_extraction_service import extract_knowledge_points
from ankiforge_ai.pipeline.ai_provider_contracts import (
    AIProviderMetadata,
    KnowledgePointJSONProvider,
    build_knowledge_point_extraction_request,
)
from ankiforge_ai.pipeline.models import SourceChunk
from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleKnowledgePointProvider,
    OpenAICompatibleProviderConfig,
    OpenAICompatibleTransport,
    OpenAICompatibleTransportResponse,
    build_chat_completions_payload,
    build_chat_completions_url,
)


class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post_json(self, url, headers, payload, timeout_seconds):
        self.calls.append(
            {
                "url": url,
                "headers": dict(headers),
                "payload": copy.deepcopy(payload),
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.response


class RaisingTransport:
    def post_json(self, url, headers, payload, timeout_seconds):
        raise RuntimeError("transport failure")


class OpenAICompatibleProviderTests(unittest.TestCase):
    def test_config_is_frozen_and_does_not_expose_api_key(self):
        config = self.config()

        self.assertNotIn("test-api-key", repr(config))
        self.assertNotIn("test-api-key", str(config))
        self.assertNotIn("api_key", config.to_dict())
        with self.assertRaises(FrozenInstanceError):
            config.model_name = "changed"

    def test_config_validates_required_fields_and_timeout(self):
        with self.assertRaises(ValueError):
            self.config(provider_id="")
        with self.assertRaises(ValueError):
            self.config(api_key=" ")
        with self.assertRaises(ValueError):
            self.config(timeout_seconds=0)
        with self.assertRaises(ValueError):
            self.config(timeout_seconds=True)

    def test_metadata_and_protocols_are_correct(self):
        transport = FakeTransport(self.success_response())
        provider = OpenAICompatibleKnowledgePointProvider(self.config(), transport)

        self.assertEqual(
            provider.metadata,
            AIProviderMetadata(provider_id="test-provider", model="test-model"),
        )
        self.assertIsInstance(provider, KnowledgePointJSONProvider)
        self.assertIsInstance(transport, OpenAICompatibleTransport)

    def test_chat_completions_url_is_normalized(self):
        cases = {
            "https://api.example.com/v1": (
                "https://api.example.com/v1/chat/completions"
            ),
            "https://api.example.com/v1/": (
                "https://api.example.com/v1/chat/completions"
            ),
            "https://api.example.com/v1/chat/completions": (
                "https://api.example.com/v1/chat/completions"
            ),
            "https://api.example.com/custom/path/": (
                "https://api.example.com/custom/path/chat/completions"
            ),
        }
        for base_url, expected in cases.items():
            with self.subTest(base_url=base_url):
                self.assertEqual(build_chat_completions_url(base_url), expected)

    def test_payload_is_minimal_and_uses_only_current_request_text(self):
        request = build_knowledge_point_extraction_request(self.chunk())

        payload = build_chat_completions_payload(request, self.config())

        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(len(payload["messages"]), 2)
        self.assertIn("knowledge_points", payload["messages"][0]["content"])
        self.assertEqual(payload["messages"][1], {"role": "user", "content": request.text})
        self.assertNotIn("其他 chunk", json.dumps(payload, ensure_ascii=False))

    def test_fake_transport_receives_url_headers_payload_and_timeout(self):
        transport = FakeTransport(self.success_response())
        config = self.config()
        request = build_knowledge_point_extraction_request(self.chunk())
        provider = OpenAICompatibleKnowledgePointProvider(config, transport)

        result = provider.extract(request)
        call = transport.calls[0]

        self.assertTrue(result.success)
        self.assertEqual(call["url"], "https://api.example.com/v1/chat/completions")
        self.assertEqual(call["headers"]["Authorization"], "Bearer test-api-key")
        self.assertEqual(call["headers"]["Content-Type"], "application/json")
        self.assertEqual(call["payload"]["model"], config.model_name)
        self.assertEqual(call["timeout_seconds"], 12.5)

    def test_success_extracts_assistant_content(self):
        response = self.success_response(
            content='  {"knowledge_points": []}  '
        )
        provider = OpenAICompatibleKnowledgePointProvider(
            self.config(),
            FakeTransport(response),
        )
        request = build_knowledge_point_extraction_request(self.chunk())

        result = provider.extract(request)

        self.assertTrue(result.success)
        self.assertEqual(result.response.json_text, '{"knowledge_points": []}')
        self.assertEqual(result.response.request_id, request.request_id)
        self.assertEqual(result.response.chunk_id, request.chunk_id)

    def test_success_integrates_with_pr2_and_preserves_chinese(self):
        content = json.dumps(
            {
                "knowledge_points": [
                    {
                        "title": "过拟合",
                        "explanation": "模型过度拟合训练数据。",
                        "evidence": "验证误差上升",
                        "tags": ["机器学习"],
                    }
                ]
            },
            ensure_ascii=False,
        )
        transport = FakeTransport(self.success_response(content=content))
        provider = OpenAICompatibleKnowledgePointProvider(self.config(), transport)
        chunk = self.chunk()

        outcome = extract_knowledge_points(chunk, provider)

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.knowledge_points[0].title, "过拟合")
        self.assertEqual(outcome.knowledge_points[0].tags, ["机器学习"])
        self.assertEqual(transport.calls[0]["payload"]["messages"][1]["content"], chunk.text)

    def test_http_failure_is_structured_and_redacted(self):
        secret_body = {"error": "test-api-key 用户的私密学习资料 Authorization"}
        transport = FakeTransport(
            OpenAICompatibleTransportResponse(status_code=401, json_body=secret_body)
        )
        provider = OpenAICompatibleKnowledgePointProvider(self.config(), transport)
        request = build_knowledge_point_extraction_request(
            self.chunk(text="用户的私密学习资料")
        )

        result = provider.extract(request)
        message = result.error.message

        self.assertFalse(result.success)
        self.assertEqual(result.error.code, "http_error")
        self.assertEqual(result.error.error_type, "http_error")
        self.assertFalse(result.error.retryable)
        self.assertIn("test-provider", message)
        self.assertIn("401", message)
        self.assertNotIn("test-api-key", message)
        self.assertNotIn("Authorization", message)
        self.assertNotIn(request.text, message)
        self.assertNotIn(secret_body["error"], message)

    def test_malformed_response_is_structured_and_redacted(self):
        malformed_bodies = (
            {},
            {"choices": []},
            {"choices": [{}]},
            {"choices": [{"message": {"content": "  "}}]},
            {"choices": [{"message": {"content": 123}}]},
        )
        for body in malformed_bodies:
            with self.subTest(body=body):
                provider = OpenAICompatibleKnowledgePointProvider(
                    self.config(),
                    FakeTransport(
                        OpenAICompatibleTransportResponse(
                            status_code=200,
                            json_body=body,
                        )
                    ),
                )

                result = provider.extract(
                    build_knowledge_point_extraction_request(self.chunk())
                )

                self.assertFalse(result.success)
                self.assertEqual(result.error.code, "malformed_response")
                self.assertEqual(result.error.error_type, "malformed_response")
                self.assertNotIn("test-api-key", result.error.message)
                self.assertNotIn(self.chunk().text, result.error.message)

    def test_invalid_content_json_is_left_for_pr2_validation(self):
        provider = OpenAICompatibleKnowledgePointProvider(
            self.config(),
            FakeTransport(self.success_response(content="{invalid json")),
        )
        chunk = self.chunk()
        request = build_knowledge_point_extraction_request(chunk)

        provider_result = provider.extract(request)
        outcome = extract_knowledge_points(chunk, provider)

        self.assertTrue(provider_result.success)
        self.assertEqual(provider_result.response.json_text, "{invalid json")
        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.error.error_type, "invalid_json")

    def test_transport_exception_is_not_caught_by_provider(self):
        provider = OpenAICompatibleKnowledgePointProvider(
            self.config(),
            RaisingTransport(),
        )

        with self.assertRaises(RuntimeError):
            provider.extract(build_knowledge_point_extraction_request(self.chunk()))

    def test_provider_does_not_modify_input(self):
        chunk = self.chunk()
        request = build_knowledge_point_extraction_request(chunk)
        before_chunk = copy.deepcopy(chunk)
        before_request = copy.deepcopy(request)
        provider = OpenAICompatibleKnowledgePointProvider(
            self.config(),
            FakeTransport(self.success_response()),
        )

        provider.extract(request)

        self.assertEqual(chunk, before_chunk)
        self.assertEqual(request, before_request)

    def test_provider_does_not_access_network(self):
        provider = OpenAICompatibleKnowledgePointProvider(
            self.config(),
            FakeTransport(self.success_response()),
        )
        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Network access is not allowed."),
        ), patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Network access is not allowed."),
        ):
            result = provider.extract(
                build_knowledge_point_extraction_request(self.chunk())
            )

        self.assertTrue(result.success)

    def test_module_has_no_forbidden_or_legacy_dependencies(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "openai_compatible_provider.py"
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
            "ankiforge_ai.ai.providers",
        )

        self.assertFalse(
            any(
                module.startswith(prefix)
                for module in imported_modules
                for prefix in forbidden
            )
        )
        self.assertNotIn("GeneratedCard", source)
        self.assertNotIn("CardCandidate", source)
        self.assertNotIn("HumanReview", source)
        self.assertNotIn("self.cards", source)

    @staticmethod
    def config(**overrides):
        values = {
            "provider_id": "test-provider",
            "provider_name": "Test Provider",
            "model_name": "test-model",
            "base_url": "https://api.example.com/v1/",
            "api_key": "test-api-key",
            "privacy_notice": "Test data stays inside the fake transport.",
            "timeout_seconds": 12.5,
        }
        values.update(overrides)
        return OpenAICompatibleProviderConfig(**values)

    @staticmethod
    def success_response(content='{"knowledge_points": []}'):
        return OpenAICompatibleTransportResponse(
            status_code=200,
            json_body={"choices": [{"message": {"content": content}}]},
        )

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
