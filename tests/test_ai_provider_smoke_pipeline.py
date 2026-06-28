import ast
import json
import socket
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.ai_extraction_service import (
    KnowledgePointExtractionOutcome,
)
from ankiforge_ai.pipeline.models import KnowledgePoint
from ankiforge_ai.pipeline.openai_compatible_http_transport import (
    OpenAICompatibleHTTPTransport,
)
from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleProviderConfig,
)
from ankiforge_ai.pipeline.provider_factory import (
    create_openai_compatible_knowledge_point_extractor,
)
from ankiforge_ai.pipeline.source_analyzer import analyze_markdown_file


class MemoryHTTPResponse:
    def __init__(self, body):
        self._body = body

    def getcode(self):
        return 200

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None


class KnowledgePointFakeOpener:
    def __init__(self):
        self.calls = []

    def __call__(self, request, timeout=None):
        request_payload = json.loads(request.data.decode("utf-8"))
        self.calls.append(
            {
                "url": request.full_url,
                "payload": request_payload,
                "timeout": timeout,
            }
        )
        knowledge_point_json = json.dumps(
            {
                "knowledge_points": [
                    {
                        "title": "监督学习中的泛化",
                        "explanation": "模型应在未参与训练的新样本上保持预测能力。",
                        "evidence": "验证集可用于观察模型的泛化表现。",
                        "tags": ["监督学习", "模型评估"],
                        "importance": "high",
                    }
                ]
            },
            ensure_ascii=False,
        )
        provider_body = json.dumps(
            {
                "choices": [
                    {"message": {"content": knowledge_point_json}}
                ]
            },
            ensure_ascii=False,
        ).encode("utf-8")
        return MemoryHTTPResponse(provider_body)


class AIProviderSmokePipelineTests(unittest.TestCase):
    def test_chinese_source_reaches_validated_knowledge_points_offline(self):
        fixture_path = (
            Path(__file__).parent
            / "fixtures"
            / "pipeline"
            / "ai_provider_smoke_source_zh.md"
        )
        document, chunks = analyze_markdown_file(str(fixture_path))
        fake_opener = KnowledgePointFakeOpener()
        extractor = create_openai_compatible_knowledge_point_extractor(
            OpenAICompatibleProviderConfig(
                provider_id="smoke-provider",
                provider_name="Smoke Provider",
                model_name="smoke-model",
                base_url="https://api.example.invalid/v1",
                api_key="test-api-key",
                timeout_seconds=5.0,
            ),
            transport=OpenAICompatibleHTTPTransport(fake_opener),
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
            outcomes = extractor.extract_from_chunks(chunks)

        self.assertEqual(document.file_name, "ai_provider_smoke_source_zh.md")
        self.assertGreaterEqual(len(chunks), 3)
        self.assertEqual(len(outcomes), len(chunks))
        self.assertTrue(all(outcome.succeeded for outcome in outcomes))
        self.assertTrue(
            all(
                isinstance(outcome, KnowledgePointExtractionOutcome)
                for outcome in outcomes
            )
        )

        points = [
            point
            for outcome in outcomes
            for point in outcome.knowledge_points
        ]
        self.assertTrue(points)
        self.assertTrue(all(isinstance(point, KnowledgePoint) for point in points))
        self.assertTrue(all(point.title == "监督学习中的泛化" for point in points))
        self.assertTrue(
            all("未参与训练的新样本" in point.explanation for point in points)
        )
        self.assertTrue(all("监督学习" in point.tags for point in points))

        sent_text = "\n".join(
            call["payload"]["messages"][1]["content"]
            for call in fake_opener.calls
        )
        self.assertIn("过拟合", sent_text)
        self.assertIn("验证集", sent_text)
        self.assertTrue(
            all(call["url"].startswith("https://api.example.invalid/") for call in fake_opener.calls)
        )
        self.assertTrue(all(call["timeout"] == 5.0 for call in fake_opener.calls))

        for outcome in outcomes:
            self.assertEqual(
                type(outcome).__name__,
                "KnowledgePointExtractionOutcome",
            )
            self.assertFalse(hasattr(outcome, "card_candidates"))
            self.assertFalse(hasattr(outcome, "human_reviews"))
            self.assertFalse(hasattr(outcome, "write"))

    def test_smoke_module_has_no_anki_ui_or_writer_dependencies(self):
        source = Path(__file__).read_text(encoding="utf-8")
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
            "ankiforge_ai.anki_writer",
            "ankiforge_ai.ui.main_dialog",
        )

        self.assertFalse(
            any(
                module == prefix or module.startswith(f"{prefix}.")
                for module in imported_modules
                for prefix in forbidden
            )
        )


if __name__ == "__main__":
    unittest.main()
