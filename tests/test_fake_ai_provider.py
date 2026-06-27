import ast
import copy
import json
import socket
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.ai_provider_contracts import (
    AIProviderError,
    KnowledgePointJSONProvider,
)
from ankiforge_ai.pipeline.fake_ai_provider import FakeAIProvider
from ankiforge_ai.pipeline.knowledge_points import parse_knowledge_points_json
from ankiforge_ai.pipeline.models import KnowledgePoint, SourceChunk


class FakeAIProviderTests(unittest.TestCase):
    def test_provider_matches_contract_and_returns_metadata(self):
        provider = FakeAIProvider()
        result = provider.extract_from_chunk(self.chunk())

        self.assertIsInstance(provider, KnowledgePointJSONProvider)
        self.assertTrue(result.success)
        self.assertEqual(result.response.metadata.provider_id, "fake")
        self.assertEqual(result.response.metadata.model, "fake-knowledge-v0.5")

    def test_output_parses_into_knowledge_point(self):
        chunk = self.chunk()
        result = FakeAIProvider().extract_from_chunk(chunk)
        points = parse_knowledge_points_json(result.response.json_text, chunk)

        self.assertEqual(len(points), 1)
        self.assertIsInstance(points[0], KnowledgePoint)
        self.assertEqual(points[0].title, "过拟合")
        self.assertEqual(points[0].explanation, chunk.text)
        self.assertEqual(points[0].evidence, chunk.text)
        self.assertEqual(points[0].tags, ["fake"])
        self.assertEqual(points[0].importance, "medium")

    def test_empty_or_whitespace_chunk_returns_empty_success_payload(self):
        for text in ("", "   \n\t"):
            with self.subTest(text=text):
                chunk = self.chunk(text=text)
                result = FakeAIProvider().extract_from_chunk(chunk)

                self.assertTrue(result.success)
                self.assertEqual(
                    json.loads(result.response.json_text),
                    {"knowledge_points": []},
                )
                self.assertEqual(
                    parse_knowledge_points_json(result.response.json_text, chunk),
                    [],
                )

    def test_output_is_deterministic(self):
        provider = FakeAIProvider()
        chunk = self.chunk()

        first = provider.extract_from_chunk(chunk)
        second = provider.extract_from_chunk(chunk)

        self.assertEqual(first, second)
        self.assertEqual(first.response.json_text, second.response.json_text)

    def test_chinese_content_is_preserved(self):
        result = FakeAIProvider().extract_from_chunk(self.chunk())

        self.assertIn("过拟合", result.response.json_text)
        self.assertIn("泛化能力", result.response.json_text)

    def test_injected_failure_is_structured_and_has_no_response(self):
        provider = FakeAIProvider(
            failure=AIProviderError(
                code="fake_failure",
                message="Injected failure.",
                error_type="FakeProviderError",
            )
        )
        result = provider.extract_from_chunk(self.chunk())

        self.assertFalse(result.success)
        self.assertIsNone(result.response)
        self.assertEqual(result.error.code, "fake_failure")

    def test_provider_does_not_modify_source_chunk(self):
        chunk = self.chunk()
        before = copy.deepcopy(chunk)

        FakeAIProvider().extract_from_chunk(chunk)

        self.assertEqual(chunk, before)

    def test_provider_does_not_access_network(self):
        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Network access is not allowed."),
        ), patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Network access is not allowed."),
        ):
            result = FakeAIProvider().extract_from_chunk(self.chunk())

        self.assertTrue(result.success)

    def test_modules_have_no_forbidden_imports_or_secrets(self):
        forbidden = (
            "aqt",
            "PyQt",
            "PyQt6",
            "urllib",
            "socket",
            "config",
            "anki_writer",
        )
        pipeline_dir = Path(__file__).parents[1] / "ankiforge_ai" / "pipeline"
        for file_name in ("ai_provider_contracts.py", "fake_ai_provider.py"):
            with self.subTest(file_name=file_name):
                source = (pipeline_dir / file_name).read_text(encoding="utf-8")
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

                self.assertFalse(
                    any(
                        module.startswith(prefix)
                        for module in imported_modules
                        for prefix in forbidden
                    )
                )
                self.assertNotIn("api_key", source.lower())
                self.assertNotIn("GeneratedCard", source)

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
