import ast
import copy
import inspect
import json
import socket
import unittest
import urllib.request
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleTransportResponse,
)
from ankiforge_ai.pipeline.provider_consent import (
    ProviderConsentRecord,
    ProviderSelection,
)
from ankiforge_ai.pipeline.provider_dry_run_execution import (
    ProviderDryRunExecutionInput,
    ProviderDryRunExecutor,
)
from ankiforge_ai.pipeline.provider_dry_run_request import ProviderDryRunRequest
from ankiforge_ai.pipeline.provider_error_display import ProviderErrorKind
from ankiforge_ai.pipeline.provider_real_dry_run import (
    OpenAICompatibleProviderDryRunExecutor,
    execute_openai_compatible_provider_dry_run_with_boundary,
)
from ankiforge_ai.pipeline.provider_secret_store import (
    ProviderSecretRef,
    ProviderSecretStore,
    ProviderSecretValue,
)
from ankiforge_ai.pipeline.user_provider_config import UserProviderProfile


_FAKE_KEY = "unit-test-credential-marker"
_RAW_BODY = "RAW PROVIDER BODY PRIVATE"
_RAW_EXCEPTION = "RAW EXCEPTION PRIVATE"


class CountingSecretValue(ProviderSecretValue):
    __slots__ = ("reveal_count",)

    def __init__(self, value):
        super().__init__(value)
        self.reveal_count = 0

    def reveal(self):
        self.reveal_count += 1
        return super().reveal()


class FakeSecretStore:
    def __init__(self, value=None):
        self.value = value
        self.loaded_refs = []

    def save_secret(self, ref, value):
        self.value = value

    def load_secret(self, ref):
        self.loaded_refs.append(ref)
        return self.value

    def has_secret(self, ref):
        return self.value is not None

    def delete_secret(self, ref):
        existed = self.value is not None
        self.value = None
        return existed


class RecordingTransport:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post_json(self, url, headers, payload, timeout_seconds):
        self.calls.append(
            {
                "url": url,
                "headers": copy.deepcopy(headers),
                "payload": copy.deepcopy(payload),
                "timeout_seconds": timeout_seconds,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


class ProviderRealDryRunTests(unittest.TestCase):
    def test_executor_implements_protocol_and_requires_explicit_dependencies(self):
        executor = self.executor()

        self.assertIsInstance(executor, ProviderDryRunExecutor)
        signature = inspect.signature(OpenAICompatibleProviderDryRunExecutor)
        self.assertTrue(
            all(
                parameter.default is inspect.Parameter.empty
                for parameter in signature.parameters.values()
            )
        )

    def test_successful_offline_extraction_returns_chinese_knowledge_point(self):
        secret = CountingSecretValue(_FAKE_KEY)
        store = FakeSecretStore(secret)
        transport = RecordingTransport(self.valid_response())

        with self.block_real_network():
            result = self.execute(store=store, transport=transport)

        self.assertTrue(result.success)
        self.assertEqual(len(result.knowledge_points), 1)
        self.assertEqual(result.knowledge_points[0].title, "验证集")
        self.assertEqual(result.knowledge_points[0].explanation, "验证集用于模型选择。")
        self.assertEqual(secret.reveal_count, 1)
        self.assertEqual(len(store.loaded_refs), 1)
        self.assertEqual(len(transport.calls), 1)

    def test_success_stops_at_knowledge_point_extraction(self):
        result = self.execute()

        self.assertEqual(result.target_stage, "knowledge_point_extraction")
        self.assertFalse(result.will_write_to_anki)
        self.assertFalse(result.will_generate_cards)
        self.assertFalse(result.will_create_anki_notes)
        self.assertFalse(result.will_modify_self_cards)
        result_fields = {item.name for item in fields(result)}
        for forbidden in (
            "card_candidates",
            "human_reviews",
            "anki_notes",
            "self_cards",
        ):
            self.assertNotIn(forbidden, result_fields)

    def test_only_preview_text_is_sent_to_transport(self):
        preview = "只发送这段中文预览。"
        transport = RecordingTransport(self.valid_response())

        self.execute(transport=transport, preview=preview)

        user_message = transport.calls[0]["payload"]["messages"][1]["content"]
        self.assertEqual(user_message, preview)
        self.assertNotIn("监督学习", user_message)

    def test_consent_mismatch_is_rejected_before_secret_load(self):
        request = self.request()
        other_selection = self.selection(provider_id="other-provider")
        object.__setattr__(request, "consent", self.consent(other_selection))
        store = FakeSecretStore(CountingSecretValue(_FAKE_KEY))

        with self.assertRaises(ValueError):
            self.execute(request=request, store=store)

        self.assertEqual(store.loaded_refs, [])

    def test_selection_mismatch_is_rejected_before_secret_load(self):
        selection = self.selection(provider_id="other-provider")
        request = self.request(selection=selection)
        store = FakeSecretStore(CountingSecretValue(_FAKE_KEY))

        with self.assertRaises(ValueError):
            self.execute(request=request, store=store)

        self.assertEqual(store.loaded_refs, [])

    def test_profile_mismatch_is_rejected_before_secret_load(self):
        store = FakeSecretStore(CountingSecretValue(_FAKE_KEY))

        with self.assertRaises(ValueError):
            self.execute(
                store=store,
                profile=self.profile(model_name="other-model"),
            )

        self.assertEqual(store.loaded_refs, [])

    def test_secret_ref_mismatch_is_rejected_before_secret_load(self):
        request = self.request()
        object.__setattr__(
            request,
            "secret_ref",
            ProviderSecretRef(profile_id="other-profile"),
        )
        store = FakeSecretStore(CountingSecretValue(_FAKE_KEY))

        with self.assertRaises(ValueError):
            self.execute(request=request, store=store)

        self.assertEqual(store.loaded_refs, [])

    def test_missing_secret_returns_safe_auth_error(self):
        store = FakeSecretStore()
        transport = RecordingTransport(self.valid_response())

        result = self.execute(store=store, transport=transport)

        self.assertFalse(result.success)
        self.assertEqual(result.error_display.kind, ProviderErrorKind.AUTH_ERROR)
        self.assertEqual(transport.calls, [])

    def test_local_endpoints_still_require_consent(self):
        for base_url in ("http://localhost:8000/v1", "https://127.0.0.1/v1"):
            with self.subTest(base_url=base_url):
                profile = self.profile(base_url=base_url)
                request = self.request(base_url=base_url)
                object.__setattr__(request, "consent", None)
                store = FakeSecretStore(CountingSecretValue(_FAKE_KEY))
                with self.assertRaises(ValueError):
                    self.execute(
                        profile=profile,
                        request=request,
                        store=store,
                    )
                self.assertEqual(store.loaded_refs, [])

    def test_public_helper_delegates_to_pr7a_boundary(self):
        execution_input = ProviderDryRunExecutionInput(self.request())
        executor = self.executor()
        sentinel = object()

        with patch(
            "ankiforge_ai.pipeline.provider_real_dry_run."
            "execute_provider_dry_run_with_boundary",
            return_value=sentinel,
        ) as boundary:
            result = execute_openai_compatible_provider_dry_run_with_boundary(
                execution_input,
                executor,
            )

        self.assertIs(result, sentinel)
        boundary.assert_called_once_with(execution_input, executor)

    def test_invalid_json_maps_to_safe_error(self):
        response = OpenAICompatibleTransportResponse(
            status_code=200,
            json_body={"choices": [{"message": {"content": "not json"}}]},
        )

        result = self.execute(transport=RecordingTransport(response))

        self.assertFalse(result.success)
        self.assertEqual(result.error_display.kind, ProviderErrorKind.INVALID_JSON)

    def test_malformed_response_maps_to_safe_error(self):
        response = OpenAICompatibleTransportResponse(
            status_code=200,
            json_body={"unexpected": "shape"},
        )

        result = self.execute(transport=RecordingTransport(response))

        self.assertFalse(result.success)
        self.assertEqual(
            result.error_display.kind,
            ProviderErrorKind.MALFORMED_RESPONSE,
        )

    def test_other_structured_failure_maps_to_unknown_error(self):
        response = OpenAICompatibleTransportResponse(
            status_code=503,
            json_body={"private": _RAW_BODY},
        )

        result = self.execute(transport=RecordingTransport(response))

        self.assertFalse(result.success)
        self.assertEqual(
            result.error_display.kind,
            ProviderErrorKind.UNKNOWN_ERROR,
        )
        self.assert_safe_rendering(result)

    def test_transport_exception_is_safely_wrapped_before_mapping(self):
        transport = RecordingTransport(error=RuntimeError(_RAW_EXCEPTION))

        result = self.execute(transport=transport, preview="PRIVATE PREVIEW")

        self.assertFalse(result.success)
        self.assertEqual(
            result.error_display.kind,
            ProviderErrorKind.UNKNOWN_ERROR,
        )
        self.assert_safe_rendering(result)

    def test_secret_is_not_stored_or_rendered_by_executor_or_results(self):
        secret = CountingSecretValue(_FAKE_KEY)
        store = FakeSecretStore(secret)
        executor = self.executor(store=store)
        execution_input = ProviderDryRunExecutionInput(self.request())

        outcome = executor.execute(execution_input)
        result = execute_openai_compatible_provider_dry_run_with_boundary(
            execution_input,
            executor,
        )
        rendered = f"{executor!r}\n{outcome!r}\n{result!r}\n{result.to_safe_dict()}"

        self.assertNotIn(_FAKE_KEY, rendered)
        self.assertNotIn("Authorization", rendered)
        executor_fields = {item.name for item in fields(executor)}
        for forbidden in (
            "secret_value",
            "api_key",
            "config",
            "provider",
            "extractor",
        ):
            self.assertNotIn(forbidden, executor_fields)

    def test_source_preview_is_not_in_result_safe_dict(self):
        preview = "PRIVATE PREVIEW SHOULD NOT BE RENDERED"
        result = self.execute(preview=preview)

        rendered = json.dumps(result.to_safe_dict(), ensure_ascii=False)
        self.assertNotIn(preview, rendered)
        self.assertNotIn(_FAKE_KEY, rendered)

    def test_inputs_are_not_modified(self):
        profile = self.profile()
        request = self.request()
        before = copy.deepcopy((profile, request))

        self.execute(profile=profile, request=request)

        self.assertEqual((profile, request), before)

    def test_execution_is_offline_with_fake_transport(self):
        with self.block_real_network():
            result = self.execute()

        self.assertTrue(result.success)

    def test_module_has_strict_import_call_and_reveal_boundary(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "provider_real_dry_run.py"
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
        calls_by_name = {}
        for function in (
            node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ):
            calls_by_name[function.name] = {
                node.func.id if isinstance(node.func, ast.Name) else node.func.attr
                for node in ast.walk(function)
                if isinstance(node, ast.Call)
                and isinstance(node.func, (ast.Name, ast.Attribute))
            }

        for forbidden_module in (
            "aqt",
            "anki",
            "urllib",
            "requests",
            "http.client",
            "socket",
            "writer",
            "orchestrator",
        ):
            self.assertNotIn(forbidden_module, imported_modules)
        for forbidden_name in (
            "OpenAICompatibleHTTPTransport",
            "CardCandidate",
            "HumanReview",
            "GeneratedCard",
        ):
            self.assertNotIn(forbidden_name, imported_names)
        reveal_functions = [
            name for name, calls in calls_by_name.items() if "reveal" in calls
        ]
        self.assertEqual(
            reveal_functions,
            ["_extract_inside_secret_reveal_boundary"],
        )
        all_calls = set().union(*calls_by_name.values())
        for forbidden_call in (
            "getenv",
            "open",
            "urlopen",
            "create_connection",
            "run_full_mock_pipeline",
            "write",
        ):
            self.assertNotIn(forbidden_call, all_calls)

    def test_docs_contain_no_fake_credential_and_state_non_goals(self):
        document = (
            Path(__file__).parents[1]
            / "docs"
            / "pipeline_v0_6_real_provider_dry_run_executor.md"
        ).read_text(encoding="utf-8")

        self.assertNotIn(_FAKE_KEY, document)
        for phrase in (
            "does not provide a CLI",
            "does not create a default HTTP transport",
            "does not write to Anki",
            "KnowledgePoint extraction",
            "PR7b-2",
            "PR7c",
        ):
            self.assertIn(phrase, document)

    def assert_safe_rendering(self, result):
        rendered = f"{result!r}\n{result.to_safe_dict()}"
        for forbidden in (
            _FAKE_KEY,
            _RAW_BODY,
            _RAW_EXCEPTION,
            "Authorization",
            "PRIVATE PREVIEW",
        ):
            self.assertNotIn(forbidden, rendered)

    @staticmethod
    def profile(**overrides):
        values = {
            "profile_id": "profile-1",
            "provider_id": "provider-1",
            "provider_name": "Provider One",
            "model_name": "model-1",
            "base_url": "https://api.example.invalid/v1",
            "privacy_notice": "The preview is sent to Provider One.",
            "timeout_seconds": 30.0,
        }
        values.update(overrides)
        return UserProviderProfile(**values)

    @staticmethod
    def selection(**overrides):
        values = {
            "profile_id": "profile-1",
            "provider_id": "provider-1",
            "provider_name": "Provider One",
            "model_name": "model-1",
            "base_url": "https://api.example.invalid/v1",
        }
        values.update(overrides)
        return ProviderSelection(**values)

    @staticmethod
    def consent(selection):
        return ProviderConsentRecord(
            selection=selection,
            consent_text="I explicitly consent to send this preview.",
            privacy_notice="The preview is sent to Provider One.",
            consented_at=datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc),
        )

    @classmethod
    def request(cls, selection=None, base_url=None, preview=None):
        if selection is None:
            selection = cls.selection(
                **({"base_url": base_url} if base_url is not None else {})
            )
        return ProviderDryRunRequest(
            selection=selection,
            consent=cls.consent(selection),
            secret_ref=ProviderSecretRef(profile_id=selection.profile_id),
            source_chunk_id="chunk-1",
            source_title="监督学习",
            source_excerpt_preview=(
                "监督学习使用带标签的数据。" if preview is None else preview
            ),
        )

    @classmethod
    def executor(cls, profile=None, store=None, transport=None):
        return OpenAICompatibleProviderDryRunExecutor(
            profile=profile or cls.profile(),
            secret_store=(
                store
                if store is not None
                else FakeSecretStore(CountingSecretValue(_FAKE_KEY))
            ),
            transport=transport or RecordingTransport(cls.valid_response()),
        )

    @classmethod
    def execute(
        cls,
        profile=None,
        request=None,
        store=None,
        transport=None,
        preview=None,
    ):
        resolved_request = request or cls.request(preview=preview)
        executor = cls.executor(
            profile=profile,
            store=store,
            transport=transport,
        )
        return execute_openai_compatible_provider_dry_run_with_boundary(
            ProviderDryRunExecutionInput(resolved_request),
            executor,
        )

    @staticmethod
    def valid_response():
        content = json.dumps(
            {
                "knowledge_points": [
                    {
                        "title": "验证集",
                        "explanation": "验证集用于模型选择。",
                        "evidence": "验证集用于评估模型的泛化表现。",
                        "tags": ["机器学习"],
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
    def block_real_network():
        class NetworkBlock:
            def __enter__(self):
                self.urlopen = patch.object(
                    urllib.request,
                    "urlopen",
                    side_effect=AssertionError("Real urlopen is forbidden."),
                )
                self.socket = patch.object(
                    socket,
                    "create_connection",
                    side_effect=AssertionError("Real network is forbidden."),
                )
                self.urlopen.start()
                self.socket.start()
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                self.socket.stop()
                self.urlopen.stop()

        return NetworkBlock()


if __name__ == "__main__":
    unittest.main()
