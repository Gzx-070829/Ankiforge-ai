import ast
import json
import socket
import unittest
import urllib.request
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.models import KnowledgePoint
from ankiforge_ai.pipeline.provider_consent import (
    ProviderConsentRecord,
    ProviderSelection,
)
from ankiforge_ai.pipeline.provider_dry_run_execution import (
    ProviderDryRunExecutionInput,
    ProviderDryRunExecutionResult,
    ProviderDryRunExecutor,
    ProviderDryRunExecutorOutcome,
    execute_provider_dry_run_with_boundary,
)
from ankiforge_ai.pipeline.provider_dry_run_request import ProviderDryRunRequest
from ankiforge_ai.pipeline.provider_error_display import ProviderErrorKind
from ankiforge_ai.pipeline.provider_secret_store import ProviderSecretRef


class FakeSuccessExecutor:
    def __init__(self, knowledge_points=()):
        self.knowledge_points = tuple(knowledge_points)
        self.call_count = 0

    def execute(self, execution_input):
        self.call_count += 1
        self.last_text = execution_input.extraction_text
        return ProviderDryRunExecutorOutcome(
            knowledge_points=self.knowledge_points
        )


class FakeErrorExecutor:
    def __init__(self, error_kind):
        self.error_kind = error_kind

    def execute(self, execution_input):
        return ProviderDryRunExecutorOutcome(error_kind=self.error_kind)


class RaisingExecutor:
    def execute(self, execution_input):
        raise RuntimeError(
            "RAW EXCEPTION test-api-key Authorization PRIVATE SOURCE"
        )


class WrongStageRequest(ProviderDryRunRequest):
    def to_safe_dict(self):
        data = super().to_safe_dict()
        data["target_stage"] = "card_generation"
        return data


class NonSendingSelection(ProviderSelection):
    @property
    def sends_user_content(self):
        return False


class ConsentOptionalSelection(ProviderSelection):
    @property
    def requires_explicit_consent(self):
        return False


class NonSendingConsent(ProviderConsentRecord):
    @property
    def sends_user_content(self):
        return False


class ConsentOptionalRecord(ProviderConsentRecord):
    @property
    def requires_explicit_consent(self):
        return False


class NonAffirmativeConsent(ProviderConsentRecord):
    @property
    def has_explicit_consent(self):
        return False


class ProviderDryRunExecutionTests(unittest.TestCase):
    def test_success_returns_knowledge_points_and_uses_preview_text(self):
        point = self.point()
        execution_input = self.execution_input()
        executor = FakeSuccessExecutor((point,))

        result = execute_provider_dry_run_with_boundary(
            execution_input,
            executor,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.knowledge_points, (point,))
        self.assertEqual(executor.last_text, execution_input.request.source_excerpt_preview)
        self.assertEqual(executor.call_count, 1)

    def test_success_with_zero_knowledge_points_is_valid(self):
        result = execute_provider_dry_run_with_boundary(
            self.execution_input(),
            FakeSuccessExecutor(),
        )

        self.assertTrue(result.success)
        self.assertEqual(result.knowledge_points, ())
        self.assertEqual(result.to_safe_dict()["knowledge_point_count"], 0)

    def test_result_stops_at_knowledge_point_extraction(self):
        result = self.execute_success()

        self.assertEqual(result.target_stage, "knowledge_point_extraction")
        self.assertFalse(result.will_write_to_anki)
        self.assertFalse(result.will_generate_cards)
        self.assertFalse(result.will_create_anki_notes)
        self.assertFalse(result.will_modify_self_cards)
        field_names = {item.name for item in fields(result)}
        for forbidden in (
            "card_candidates",
            "human_reviews",
            "anki_notes",
            "self_cards",
        ):
            self.assertNotIn(forbidden, field_names)

    def test_result_is_frozen_and_fixed_flags_cannot_be_forged(self):
        result = self.execute_success()

        with self.assertRaises(FrozenInstanceError):
            result.profile_id = "changed"
        for flag in (
            "will_write_to_anki",
            "will_generate_cards",
            "will_create_anki_notes",
            "will_modify_self_cards",
        ):
            with self.subTest(flag=flag):
                with self.assertRaises(TypeError):
                    self.result(**{flag: True})

    def test_execution_input_is_frozen_and_hides_request(self):
        execution_input = self.execution_input()

        with self.assertRaises(FrozenInstanceError):
            execution_input.request = self.request()
        rendered = f"{repr(execution_input)}\n{str(execution_input)}"
        self.assertNotIn(execution_input.extraction_text, rendered)
        self.assertNotIn("secret_ref", rendered)

    def test_input_safe_dict_contains_only_preview_length(self):
        execution_input = self.execution_input()
        data = execution_input.to_safe_dict()

        self.assertEqual(
            data,
            {
                "profile_id": "profile-1",
                "source_chunk_id": "chunk-1",
                "source_excerpt_preview_length": len("监督学习使用带标签的数据。"),
                "target_stage": "knowledge_point_extraction",
            },
        )
        self.assertNotIn(execution_input.extraction_text, json.dumps(data))

    def test_input_safe_projection_rejects_sensitive_identifiers(self):
        for field_name, value in (
            ("profile_id", "test-api-key"),
            ("source_chunk_id", "Authorization Bearer token"),
        ):
            with self.subTest(field_name=field_name):
                if field_name == "profile_id":
                    selection = self.selection(profile_id=value)
                    request = ProviderDryRunRequest(
                        selection=selection,
                        consent=self.consent(selection),
                        secret_ref=ProviderSecretRef(profile_id=value),
                        source_chunk_id="chunk-1",
                        source_title="监督学习",
                        source_excerpt_preview="监督学习使用带标签的数据。",
                    )
                else:
                    request = self.request()
                    object.__setattr__(request, field_name, value)
                with self.assertRaises(ValueError) as context:
                    ProviderDryRunExecutionInput(request)
                self.assertNotIn(value, str(context.exception))

    def test_missing_consent_is_rejected_before_executor_call(self):
        request = self.request()
        object.__setattr__(request, "consent", None)
        executor = FakeSuccessExecutor()

        with self.assertRaises(ValueError):
            execute_provider_dry_run_with_boundary(
                ProviderDryRunExecutionInput(request),
                executor,
            )

        self.assertEqual(executor.call_count, 0)

    def test_consent_selection_mismatch_is_rejected(self):
        request = self.request()
        other_selection = self.selection(provider_id="other-provider")
        object.__setattr__(request, "consent", self.consent(other_selection))

        with self.assertRaises(ValueError):
            self.execute_request(request)

    def test_request_selection_mismatch_is_rejected(self):
        request = self.request()
        object.__setattr__(
            request,
            "selection",
            self.selection(model_name="other-model"),
        )

        with self.assertRaises(ValueError):
            self.execute_request(request)

    def test_secret_ref_mismatch_is_rejected(self):
        request = self.request()
        object.__setattr__(
            request,
            "secret_ref",
            ProviderSecretRef(profile_id="other-profile"),
        )

        with self.assertRaises(ValueError):
            self.execute_request(request)

    def test_target_stage_mismatch_is_rejected(self):
        request = self.request(request_type=WrongStageRequest)

        with self.assertRaises(ValueError):
            self.execute_request(request)

    def test_selection_safety_flags_are_revalidated(self):
        for selection_type in (NonSendingSelection, ConsentOptionalSelection):
            with self.subTest(selection_type=selection_type.__name__):
                request = self.request()
                selection = self.selection(selection_type=selection_type)
                object.__setattr__(request, "selection", selection)
                object.__setattr__(request, "consent", self.consent(selection))
                with self.assertRaises(ValueError):
                    self.execute_request(request)

    def test_consent_safety_flags_are_revalidated(self):
        for consent_type in (
            NonSendingConsent,
            ConsentOptionalRecord,
            NonAffirmativeConsent,
        ):
            with self.subTest(consent_type=consent_type.__name__):
                request = self.request()
                object.__setattr__(
                    request,
                    "consent",
                    self.consent(request.selection, consent_type=consent_type),
                )
                with self.assertRaises(ValueError):
                    self.execute_request(request)

    def test_local_endpoints_do_not_bypass_consent(self):
        for base_url in ("http://localhost:8000/v1", "https://127.0.0.1/v1"):
            with self.subTest(base_url=base_url):
                request = self.request(base_url=base_url)
                result = self.execute_request(request)
                self.assertTrue(result.success)
                object.__setattr__(request, "consent", None)
                with self.assertRaises(ValueError):
                    self.execute_request(request)

    def test_executor_must_be_explicit_and_protocol_compatible(self):
        self.assertIsInstance(FakeSuccessExecutor(), ProviderDryRunExecutor)
        with self.assertRaises(ValueError):
            execute_provider_dry_run_with_boundary(
                self.execution_input(),
                None,
            )
        with self.assertRaises(ValueError):
            execute_provider_dry_run_with_boundary(
                self.execution_input(),
                object(),
            )

    def test_executor_must_return_normalized_outcome(self):
        class InvalidExecutor:
            def execute(self, execution_input):
                return {"raw": "response"}

        with self.assertRaises(ValueError):
            execute_provider_dry_run_with_boundary(
                self.execution_input(),
                InvalidExecutor(),
            )

    def test_error_kinds_map_to_safe_display(self):
        kinds = (
            ProviderErrorKind.AUTH_ERROR,
            ProviderErrorKind.NETWORK_ERROR,
            ProviderErrorKind.TIMEOUT,
            ProviderErrorKind.RATE_LIMIT,
            ProviderErrorKind.PROVIDER_UNAVAILABLE,
            ProviderErrorKind.INVALID_JSON,
            ProviderErrorKind.MALFORMED_RESPONSE,
            ProviderErrorKind.CONTENT_POLICY,
            ProviderErrorKind.UNKNOWN_ERROR,
        )
        for kind in kinds:
            with self.subTest(kind=kind.value):
                result = execute_provider_dry_run_with_boundary(
                    self.execution_input(),
                    FakeErrorExecutor(kind),
                )
                self.assertFalse(result.success)
                self.assertEqual(result.knowledge_points, ())
                self.assertEqual(result.error_display.kind, kind)
                self.assertEqual(
                    result.to_safe_dict()["error_display"]["kind"],
                    kind.value,
                )

    def test_outcome_rejects_raw_diagnostic_fields(self):
        for field_name in (
            "raw_exception",
            "raw_response_body",
            "payload",
            "authorization",
            "api_key",
            "source_text",
        ):
            with self.subTest(field_name=field_name):
                with self.assertRaises(TypeError):
                    ProviderDryRunExecutorOutcome(**{field_name: "sensitive"})

    def test_raised_exception_is_not_wrapped_into_result(self):
        execution_input = self.execution_input(
            source_excerpt_preview="PRIVATE SOURCE"
        )

        with self.assertRaises(RuntimeError):
            execute_provider_dry_run_with_boundary(
                execution_input,
                RaisingExecutor(),
            )

        rendered = f"{repr(execution_input)}\n{execution_input.to_safe_dict()}"
        for forbidden in (
            "PRIVATE SOURCE",
            "test-api-key",
            "Authorization",
            "RAW EXCEPTION",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_result_repr_and_safe_dict_do_not_leak_sensitive_content(self):
        execution_input = self.execution_input(
            source_excerpt_preview="PRIVATE SOURCE Authorization test-api-key"
        )
        result = execute_provider_dry_run_with_boundary(
            execution_input,
            FakeErrorExecutor(ProviderErrorKind.UNKNOWN_ERROR),
        )
        rendered = f"{repr(result)}\n{str(result)}\n{result.to_safe_dict()}"

        for forbidden in (
            execution_input.extraction_text,
            "test-api-key",
            "Authorization",
            "secret_ref",
            "credential_kind",
            "raw response",
            "stack trace",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_success_result_hides_knowledge_point_content(self):
        point = self.point()
        result = execute_provider_dry_run_with_boundary(
            self.execution_input(),
            FakeSuccessExecutor((point,)),
        )
        rendered = f"{repr(result)}\n{str(result)}\n{result.to_safe_dict()}"

        for forbidden in (
            point.title,
            point.explanation,
            point.evidence,
            point.source_display,
        ):
            self.assertNotIn(forbidden, rendered)

    def test_boundary_does_not_access_network(self):
        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Network access is forbidden."),
        ), patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Network access is forbidden."),
        ):
            result = self.execute_success()

        self.assertTrue(result.success)

    def test_module_has_strict_import_and_call_boundary(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "provider_dry_run_execution.py"
        )
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
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
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        called_names = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr)

        self.assertEqual(
            imported_modules,
            {
                "dataclasses",
                "typing",
                "models",
                "provider_consent",
                "provider_dry_run_request",
                "provider_error_display",
                "provider_secret_store",
            },
        )
        for forbidden_import in (
            "ProviderSecretStore",
            "ProviderSecretValue",
            "OpenAICompatibleHTTPTransport",
        ):
            self.assertNotIn(forbidden_import, imported_names)
        for forbidden_call in (
            "reveal",
            "load_secret",
            "urlopen",
            "create_connection",
            "post_json",
            "create_openai_compatible_knowledge_point_provider",
            "run_full_mock_pipeline",
            "write",
        ):
            self.assertNotIn(forbidden_call, called_names)
        self.assertFalse(
            any(isinstance(node, ast.ExceptHandler) for node in ast.walk(tree))
        )

    @staticmethod
    def selection(selection_type=ProviderSelection, **overrides):
        values = {
            "profile_id": "profile-1",
            "provider_id": "provider-1",
            "provider_name": "Provider One",
            "model_name": "model-1",
            "base_url": "https://api.example.com/v1",
        }
        values.update(overrides)
        return selection_type(**values)

    @staticmethod
    def consent(selection, consent_type=ProviderConsentRecord):
        return consent_type(
            selection=selection,
            consent_text="I explicitly consent to send the preview.",
            privacy_notice="The preview is sent to Provider One.",
            consented_at=datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc),
        )

    @staticmethod
    def point():
        return KnowledgePoint(
            point_id="point-1",
            document_id="document-1",
            chunk_id="chunk-1",
            source_display="监督学习 > 定义",
            heading_path=["监督学习", "定义"],
            ordinal=0,
            title="监督学习",
            explanation="监督学习使用带标签的数据。",
            evidence="输入与标签共同用于训练。",
            tags=["机器学习"],
            importance="high",
        )

    @classmethod
    def request(cls, request_type=ProviderDryRunRequest, base_url=None):
        selection = cls.selection(
            **({"base_url": base_url} if base_url is not None else {})
        )
        return request_type(
            selection=selection,
            consent=cls.consent(selection),
            secret_ref=ProviderSecretRef(profile_id=selection.profile_id),
            source_chunk_id="chunk-1",
            source_title="监督学习",
            source_excerpt_preview="监督学习使用带标签的数据。",
        )

    @classmethod
    def execution_input(cls, **request_overrides):
        request = cls.request()
        for field_name, value in request_overrides.items():
            object.__setattr__(request, field_name, value)
        return ProviderDryRunExecutionInput(request)

    @classmethod
    def execute_request(cls, request):
        return execute_provider_dry_run_with_boundary(
            ProviderDryRunExecutionInput(request),
            FakeSuccessExecutor(),
        )

    @classmethod
    def execute_success(cls):
        return execute_provider_dry_run_with_boundary(
            cls.execution_input(),
            FakeSuccessExecutor((cls.point(),)),
        )

    @staticmethod
    def result(**overrides):
        values = {
            "profile_id": "profile-1",
            "source_chunk_id": "chunk-1",
            "source_excerpt_preview_length": 12,
            "knowledge_points": (),
        }
        values.update(overrides)
        return ProviderDryRunExecutionResult(**values)


if __name__ == "__main__":
    unittest.main()
