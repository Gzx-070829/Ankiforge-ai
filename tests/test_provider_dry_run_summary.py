import ast
import copy
import json
import unittest
from pathlib import Path

from ankiforge_ai.pipeline.ai_extraction_service import (
    KnowledgePointExtractionOutcome,
    extract_knowledge_points,
)
from ankiforge_ai.pipeline.ai_provider_contracts import (
    AIProviderError,
    AIProviderResult,
    build_knowledge_point_extraction_request,
)
from ankiforge_ai.pipeline.fake_ai_provider import FakeAIProvider
from ankiforge_ai.pipeline.models import SourceChunk
from ankiforge_ai.pipeline.provider_dry_run_summary import (
    ProviderDryRunContext,
    ProviderDryRunSummary,
    create_provider_dry_run_summary,
)


class ProviderDryRunSummaryTests(unittest.TestCase):
    def test_success_outcome_preserves_mock_context_and_count(self):
        outcome = extract_knowledge_points(self.chunk(), FakeAIProvider())

        summary = create_provider_dry_run_summary(outcome, self.mock_context())

        self.assertTrue(summary.succeeded)
        self.assertEqual(summary.knowledge_point_count, 1)
        self.assertEqual(summary.provider_id, "fake")
        self.assertEqual(summary.provider_name, "Fake AI Provider")
        self.assertEqual(summary.model_name, "fake-knowledge-v0.5")
        self.assertTrue(summary.is_mock)
        self.assertFalse(summary.sends_user_content)
        self.assertTrue(summary.supports_json_output)
        self.assertTrue(summary.safety_wrapped)
        self.assertEqual(summary.error_type, "")
        self.assertEqual(summary.error_code, "")
        self.assertFalse(summary.retryable)
        self.assertFalse(summary.will_write_to_anki)

    def test_success_with_zero_points_is_still_successful(self):
        outcome = extract_knowledge_points(
            self.chunk(text="  \n\t "),
            FakeAIProvider(),
        )

        summary = create_provider_dry_run_summary(outcome, self.mock_context())

        self.assertTrue(summary.succeeded)
        self.assertEqual(summary.knowledge_point_count, 0)

    def test_openai_compatible_context_is_preserved(self):
        context = ProviderDryRunContext(
            provider_id="openai-compatible",
            provider_name="OpenAI-compatible",
            model_name="test-model",
            is_mock=False,
            sends_user_content=True,
            supports_json_output=True,
            safety_wrapped=True,
        )

        summary = create_provider_dry_run_summary(
            extract_knowledge_points(self.chunk(), FakeAIProvider()),
            context,
        )

        self.assertEqual(summary.provider_id, "openai-compatible")
        self.assertEqual(summary.provider_name, "OpenAI-compatible")
        self.assertEqual(summary.model_name, "test-model")
        self.assertFalse(summary.is_mock)
        self.assertTrue(summary.sends_user_content)

    def test_fixed_messages_cover_supported_error_types(self):
        cases = {
            "invalid_json": "AI 返回的 JSON 格式无效，需要重新生成或调整 provider 输出。",
            "malformed_response": "AI provider 返回格式异常，未能读取有效内容。",
            "network_error": "网络请求失败。",
            "auth_error": "API key 或认证配置可能有问题。",
            "rate_limit": "请求频率受限，请稍后重试。",
        }

        for error_type, expected_message in cases.items():
            with self.subTest(error_type=error_type):
                summary = create_provider_dry_run_summary(
                    self.failed_outcome(
                        code=error_type,
                        error_type=error_type,
                        retryable=error_type in {"network_error", "rate_limit"},
                    ),
                    self.mock_context(),
                )

                self.assertFalse(summary.succeeded)
                self.assertEqual(summary.knowledge_point_count, 0)
                self.assertEqual(summary.error_type, error_type)
                self.assertEqual(summary.error_code, error_type)
                self.assertEqual(summary.user_safe_message, expected_message)
                self.assertEqual(
                    summary.retryable,
                    error_type in {"network_error", "rate_limit"},
                )

    def test_provider_exception_uses_code_when_error_type_is_unknown(self):
        summary = create_provider_dry_run_summary(
            self.failed_outcome(
                code="provider_exception",
                error_type="unknown",
            ),
            self.mock_context(),
        )

        self.assertEqual(summary.error_type, "unknown")
        self.assertEqual(summary.error_code, "provider_exception")
        self.assertEqual(
            summary.user_safe_message,
            "AI provider 调用失败，已被安全拦截。",
        )

    def test_unknown_provider_failure_uses_generic_safe_message(self):
        summary = create_provider_dry_run_summary(
            self.failed_outcome(
                code="provider_failure",
                error_type="unexpected_failure",
                retryable=True,
            ),
            self.mock_context(),
        )

        self.assertEqual(summary.error_code, "provider_failure")
        self.assertEqual(summary.error_type, "unexpected_failure")
        self.assertTrue(summary.retryable)
        self.assertEqual(
            summary.user_safe_message,
            "AI provider 出现未知错误。",
        )

    def test_summary_never_accepts_or_reports_write_authorization(self):
        outcome = extract_knowledge_points(self.chunk(), FakeAIProvider())
        summary = create_provider_dry_run_summary(outcome, self.mock_context())

        self.assertFalse(summary.will_write_to_anki)
        self.assertFalse(summary.to_dict()["will_write_to_anki"])
        with self.assertRaises(TypeError):
            ProviderDryRunSummary(
                provider_id="fake",
                provider_name="Fake",
                model_name="fake-model",
                is_mock=True,
                sends_user_content=False,
                supports_json_output=True,
                safety_wrapped=True,
                succeeded=True,
                knowledge_point_count=0,
                error_type="",
                error_code="",
                retryable=False,
                user_safe_message="Safe",
                will_write_to_anki=True,
            )

    def test_summary_serialization_excludes_sensitive_input_data(self):
        secrets = (
            "test-api-key",
            "Authorization: Bearer secret-token",
            "PRIVATE SOURCE TEXT",
            "RAW RESPONSE BODY",
            "original exception detail",
        )
        outcome = self.failed_outcome(
            code="provider_exception",
            error_type="unknown",
            message=" | ".join(secrets),
            text="PRIVATE SOURCE TEXT",
        )

        summary = create_provider_dry_run_summary(outcome, self.mock_context())
        rendered = "\n".join(
            (
                repr(summary),
                str(summary),
                json.dumps(summary.to_dict(), ensure_ascii=False),
            )
        )

        for secret in secrets:
            with self.subTest(secret=secret):
                self.assertNotIn(secret, rendered)
        self.assertNotIn(outcome.request.text, rendered)

    def test_helper_does_not_modify_outcome_or_context(self):
        outcome = extract_knowledge_points(self.chunk(), FakeAIProvider())
        context = self.mock_context()
        outcome_before = copy.deepcopy(outcome)
        context_before = copy.deepcopy(context)

        create_provider_dry_run_summary(outcome, context)

        self.assertEqual(outcome, outcome_before)
        self.assertEqual(context, context_before)

    def test_context_and_summary_are_json_serializable(self):
        context = self.mock_context()
        summary = create_provider_dry_run_summary(
            extract_knowledge_points(self.chunk(), FakeAIProvider()),
            context,
        )

        json.dumps(context.to_dict(), ensure_ascii=False)
        json.dumps(summary.to_dict(), ensure_ascii=False)

    def test_module_has_no_forbidden_dependencies_or_calls(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "provider_dry_run_summary.py"
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
            "os",
            "pathlib",
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
        self.assertNotIn("GeneratedCard", source)
        self.assertNotIn("CardCandidate", source)
        self.assertNotIn("HumanReview", source)
        self.assertNotIn("self.cards", source)
        self.assertNotIn(".extract(", source)
        self.assertNotIn("post_json", source)

    @staticmethod
    def mock_context():
        return ProviderDryRunContext(
            provider_id="fake",
            provider_name="Fake AI Provider",
            model_name="fake-knowledge-v0.5",
            is_mock=True,
            sends_user_content=False,
            supports_json_output=True,
            safety_wrapped=True,
        )

    @classmethod
    def failed_outcome(
        cls,
        code,
        error_type,
        retryable=False,
        message="Sensitive provider error must not be copied.",
        text="测试内容",
    ):
        chunk = cls.chunk(text=text)
        request = build_knowledge_point_extraction_request(chunk)
        error = AIProviderError(
            code=code,
            message=message,
            error_type=error_type,
            retryable=retryable,
        )
        provider_result = AIProviderResult.from_error(request, error)
        return KnowledgePointExtractionOutcome(
            request=request,
            provider_result=provider_result,
            error=error,
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
