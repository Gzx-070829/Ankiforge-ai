import ast
import copy
import json
import socket
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.ai_knowledge_extractor_adapter import (
    AIKnowledgePointExtractor,
)
from ankiforge_ai.pipeline.ai_provider_contracts import KnowledgePointJSONProvider
from ankiforge_ai.pipeline.fake_ai_provider import FakeAIProvider
from ankiforge_ai.pipeline.models import SourceChunk
from ankiforge_ai.pipeline.openai_compatible_http_transport import (
    OpenAICompatibleHTTPTransport,
)
from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleKnowledgePointProvider,
    OpenAICompatibleProviderConfig,
    OpenAICompatibleTransportResponse,
)
from ankiforge_ai.pipeline.provider_factory import (
    create_openai_compatible_knowledge_point_extractor,
    create_openai_compatible_knowledge_point_provider,
)
from ankiforge_ai.pipeline.provider_safety_wrapper import (
    SafeKnowledgePointJSONProvider,
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
    def __init__(self):
        self.calls = 0

    def post_json(self, url, headers, payload, timeout_seconds):
        self.calls += 1
        raise RuntimeError("test-api-key and private source must stay hidden")


class ProviderFactoryTests(unittest.TestCase):
    def test_provider_factory_wraps_safely_by_default(self):
        provider = create_openai_compatible_knowledge_point_provider(
            self.config(),
            transport=FakeTransport(self.provider_response()),
        )

        self.assertIsInstance(provider, SafeKnowledgePointJSONProvider)
        self.assertIsInstance(provider, KnowledgePointJSONProvider)
        self.assertEqual(provider.metadata.provider_id, "test-provider")

    def test_provider_factory_can_return_raw_provider(self):
        provider = create_openai_compatible_knowledge_point_provider(
            self.config(),
            transport=FakeTransport(self.provider_response()),
            wrap_safe=False,
        )

        self.assertIsInstance(provider, OpenAICompatibleKnowledgePointProvider)
        self.assertNotIsInstance(provider, SafeKnowledgePointJSONProvider)

    def test_injected_transport_is_used_but_not_called_during_wiring(self):
        transport = FakeTransport(self.provider_response())

        provider = create_openai_compatible_knowledge_point_provider(
            self.config(),
            transport=transport,
            wrap_safe=False,
        )
        extractor = create_openai_compatible_knowledge_point_extractor(
            self.config(),
            transport=transport,
        )

        self.assertIs(provider._transport, transport)
        self.assertIsInstance(extractor, AIKnowledgePointExtractor)
        self.assertEqual(transport.calls, [])

    def test_default_transport_is_created_without_network_access(self):
        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Factory must not call urlopen."),
        ) as urlopen, patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Factory must not access the network."),
        ) as create_connection:
            provider = create_openai_compatible_knowledge_point_provider(
                self.config(),
                wrap_safe=False,
            )

        self.assertIsInstance(provider._transport, OpenAICompatibleHTTPTransport)
        urlopen.assert_not_called()
        create_connection.assert_not_called()

    def test_extractor_factory_reuses_provider_factory(self):
        config = self.config()
        transport = FakeTransport(self.provider_response())
        stub_provider = FakeAIProvider()

        with patch(
            "ankiforge_ai.pipeline.provider_factory."
            "create_openai_compatible_knowledge_point_provider",
            return_value=stub_provider,
        ) as provider_factory:
            extractor = create_openai_compatible_knowledge_point_extractor(
                config,
                transport=transport,
                wrap_safe=False,
            )

        self.assertIsInstance(extractor, AIKnowledgePointExtractor)
        provider_factory.assert_called_once_with(
            config,
            transport=transport,
            wrap_safe=False,
        )

    def test_extractor_completes_chinese_extraction_offline(self):
        transport = FakeTransport(self.provider_response())
        extractor = create_openai_compatible_knowledge_point_extractor(
            self.config(),
            transport=transport,
        )

        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Real urlopen must not be called."),
        ), patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Real network must not be accessed."),
        ):
            outcome = extractor.extract_from_chunk(self.chunk())

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.knowledge_points[0].title, "特征值")
        self.assertEqual(outcome.knowledge_points[0].tags, ["线性代数"])
        self.assertEqual(len(transport.calls), 1)

    def test_invalid_json_remains_a_pr2_validation_error(self):
        transport = FakeTransport(self.provider_response(content="{invalid json"))
        extractor = create_openai_compatible_knowledge_point_extractor(
            self.config(),
            transport=transport,
        )

        outcome = extractor.extract_from_chunk(self.chunk())

        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.error.code, "invalid_json")
        self.assertEqual(outcome.error.error_type, "invalid_json")

    def test_raising_transport_is_structured_by_default_safety_wrapper(self):
        transport = RaisingTransport()
        extractor = create_openai_compatible_knowledge_point_extractor(
            self.config(),
            transport=transport,
        )

        outcome = extractor.extract_from_chunk(self.chunk())

        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.error.code, "provider_exception")
        self.assertEqual(outcome.error.error_type, "unknown")
        self.assertFalse(outcome.error.retryable)
        self.assertEqual(transport.calls, 1)
        self.assertNotIn("test-api-key", outcome.error.message)
        self.assertNotIn("private source", outcome.error.message)

    def test_api_key_is_not_exposed_by_wired_object_representations(self):
        config = self.config()
        transport = RaisingTransport()
        raw_provider = create_openai_compatible_knowledge_point_provider(
            config,
            transport=transport,
            wrap_safe=False,
        )
        safe_provider = create_openai_compatible_knowledge_point_provider(
            config,
            transport=transport,
        )
        extractor = create_openai_compatible_knowledge_point_extractor(
            config,
            transport=transport,
        )

        for value in (config, raw_provider, safe_provider, extractor):
            with self.subTest(value=type(value).__name__):
                self.assertNotIn("test-api-key", repr(value))
                self.assertNotIn("test-api-key", str(value))

    def test_factory_does_not_modify_config_or_chunk(self):
        config = self.config()
        chunk = self.chunk()
        config_before = copy.deepcopy(config)
        chunk_before = copy.deepcopy(chunk)
        extractor = create_openai_compatible_knowledge_point_extractor(
            config,
            transport=FakeTransport(self.provider_response()),
        )

        extractor.extract_from_chunk(chunk)

        self.assertEqual(config, config_before)
        self.assertEqual(chunk, chunk_before)

    def test_factory_module_has_no_forbidden_dependencies_or_side_effects(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "provider_factory.py"
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
            "ankiforge_ai.ai.providers",
            "anki_writer",
            "config_loader",
            "urllib",
            "socket",
            "os",
            "pathlib",
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
        self.assertNotIn(".extract(", source)

    @staticmethod
    def config():
        return OpenAICompatibleProviderConfig(
            provider_id="test-provider",
            provider_name="Test Provider",
            model_name="test-model",
            base_url="https://api.example.invalid/v1",
            api_key="test-api-key",
            timeout_seconds=10.0,
        )

    @staticmethod
    def provider_response(content=None):
        if content is None:
            content = json.dumps(
                {
                    "knowledge_points": [
                        {
                            "title": "特征值",
                            "explanation": "特征向量在线性变换后只改变尺度。",
                            "evidence": "Av = lambda v",
                            "tags": ["线性代数"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        return OpenAICompatibleTransportResponse(
            status_code=200,
            json_body={"choices": [{"message": {"content": content}}]},
        )

    @staticmethod
    def chunk():
        return SourceChunk(
            chunk_id="chunk_1",
            document_id="document_1",
            file_path="C:/notes/线性代数.md",
            file_name="线性代数.md",
            heading_path=["线性代数", "特征值"],
            heading_level=2,
            ordinal=0,
            text="特征向量在线性变换后只改变尺度。",
            chunk_hash="hash",
            source_display="线性代数.md > 线性代数 > 特征值",
        )


if __name__ == "__main__":
    unittest.main()
