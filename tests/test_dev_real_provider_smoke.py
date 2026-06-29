import ast
import copy
import io
import json
import socket
import unittest
import urllib.request
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleTransportResponse,
)
from ankiforge_ai.pipeline.provider_consent import (
    ProviderConsentRecord,
    ProviderSelection,
    create_provider_consent_record,
    create_provider_selection_from_profile,
)
from ankiforge_ai.pipeline.provider_dry_run_execution import (
    ProviderDryRunExecutionInput,
)
from ankiforge_ai.pipeline.provider_dry_run_request import ProviderDryRunRequest
from ankiforge_ai.pipeline.provider_real_dry_run import (
    OpenAICompatibleProviderDryRunExecutor,
    execute_openai_compatible_provider_dry_run_with_boundary,
)
from ankiforge_ai.pipeline.provider_secret_store import (
    ProviderSecretRef,
    ProviderSecretValue,
)
from ankiforge_ai.pipeline.user_provider_config import UserProviderProfile
from scripts import dev_real_provider_smoke as smoke
from scripts.dev_real_provider_smoke import (
    API_KEY_ENV_VAR,
    DevRealProviderSmokeResult,
    _OneShotDevSecretStore,
    build_argument_parser,
    format_dev_real_provider_smoke_output,
    main,
    run_dev_real_provider_smoke,
)


_FAKE_KEY = "test-api-key"
_PRIVATE_SOURCE = "PRIVATE SOURCE SHOULD NOT BE PRINTED"
_RAW_BODY = "RAW RESPONSE BODY SHOULD NOT BE PRINTED"
_RAW_EXCEPTION = "RAW EXCEPTION SHOULD NOT BE PRINTED"


class TrackingEnvironment(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_calls = []

    def get(self, key, default=None):
        self.get_calls.append(key)
        return super().get(key, default)


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


class MissingSecretStore:
    def save_secret(self, ref, value):
        raise AssertionError("save_secret must not be called")

    def load_secret(self, ref):
        return None

    def has_secret(self, ref):
        return False

    def delete_secret(self, ref):
        return False


class DevRealProviderSmokeTests(unittest.TestCase):
    def test_parser_preserves_entry_and_marks_harness_dev_manual_only(self):
        help_text = build_argument_parser().format_help()

        self.assertIn("DEV ONLY", help_text)
        self.assertIn("MANUAL ONLY", help_text)
        self.assertIn("--confirm-send", help_text)
        self.assertEqual(API_KEY_ENV_VAR, "ANKIFORGE_DEV_API_KEY")

    def test_missing_confirmation_reads_no_key_and_builds_nothing(self):
        environment = TrackingEnvironment({API_KEY_ENV_VAR: _FAKE_KEY})
        output = io.StringIO()

        with patch.object(
            smoke,
            "_create_dev_http_transport",
            side_effect=AssertionError("transport must not be created"),
        ), patch.object(
            smoke,
            "OpenAICompatibleProviderDryRunExecutor",
            side_effect=AssertionError("executor must not be created"),
        ), self.block_real_network():
            exit_code = main(
                self.cli_args(confirm=False),
                environ=environment,
                output_stream=output,
            )

        self.assertEqual(exit_code, 2)
        self.assertEqual(environment.get_calls, [])
        self.assertIn("--confirm-send", output.getvalue())
        self.assertNotIn(_FAKE_KEY, output.getvalue())

    def test_missing_api_key_exits_before_transport_or_executor(self):
        environment = TrackingEnvironment()
        output = io.StringIO()

        with patch.object(
            smoke,
            "_create_dev_http_transport",
            side_effect=AssertionError("transport must not be created"),
        ), patch.object(
            smoke,
            "OpenAICompatibleProviderDryRunExecutor",
            side_effect=AssertionError("executor must not be created"),
        ):
            exit_code = main(
                self.cli_args(confirm=True),
                environ=environment,
                output_stream=output,
            )

        self.assertEqual(exit_code, 2)
        self.assertEqual(environment.get_calls, [API_KEY_ENV_VAR])
        self.assertIn(API_KEY_ENV_VAR, output.getvalue())

    def test_cli_api_key_argument_is_rejected_without_echoing_value(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            main(
                self.cli_args(confirm=True)
                + ["--api-key", "cli-secret-must-not-appear"],
                environ={API_KEY_ENV_VAR: _FAKE_KEY},
            )

        self.assertEqual(raised.exception.code, 2)
        self.assertNotIn("cli-secret-must-not-appear", stderr.getvalue())
        self.assertNotIn("--api-key", stderr.getvalue())

    def test_default_http_transport_is_created_only_after_gates(self):
        transport = RecordingTransport(self.valid_response())
        output = io.StringIO()

        with patch.object(
            smoke,
            "_create_dev_http_transport",
            return_value=transport,
        ) as factory, self.block_real_network():
            exit_code = main(
                self.cli_args(confirm=True),
                environ={API_KEY_ENV_VAR: _FAKE_KEY},
                output_stream=output,
            )

        self.assertEqual(exit_code, 0)
        factory.assert_called_once_with()
        self.assertEqual(len(transport.calls), 1)

    def test_fake_transport_completes_chinese_extraction_offline(self):
        transport = RecordingTransport(self.valid_response())

        with self.block_real_network():
            result = run_dev_real_provider_smoke(
                **self.run_args(),
                transport=transport,
            )

        self.assertTrue(result.execution_result.success)
        self.assertEqual(
            result.execution_result.target_stage,
            "knowledge_point_extraction",
        )
        self.assertEqual(result.knowledge_point_titles, ("验证集",))
        self.assertFalse(result.execution_result.will_write_to_anki)
        sent_text = transport.calls[0]["payload"]["messages"][1]["content"]
        self.assertEqual(sent_text, "中文测试内容")

    def test_harness_constructs_and_uses_every_v06_boundary_model(self):
        transport = RecordingTransport(self.valid_response())
        patches = (
            patch.object(smoke, "UserProviderProfile", wraps=UserProviderProfile),
            patch.object(
                smoke,
                "create_provider_selection_from_profile",
                wraps=create_provider_selection_from_profile,
            ),
            patch.object(
                smoke,
                "create_provider_consent_record",
                wraps=create_provider_consent_record,
            ),
            patch.object(smoke, "ProviderDryRunRequest", wraps=ProviderDryRunRequest),
            patch.object(
                smoke,
                "ProviderDryRunExecutionInput",
                wraps=ProviderDryRunExecutionInput,
            ),
            patch.object(
                smoke,
                "OpenAICompatibleProviderDryRunExecutor",
                wraps=OpenAICompatibleProviderDryRunExecutor,
            ),
            patch.object(
                smoke,
                "execute_openai_compatible_provider_dry_run_with_boundary",
                wraps=execute_openai_compatible_provider_dry_run_with_boundary,
            ),
        )

        entered = [item.start() for item in patches]
        try:
            result = run_dev_real_provider_smoke(
                **self.run_args(),
                transport=transport,
            )
        finally:
            for item in reversed(patches):
                item.stop()

        self.assertTrue(result.execution_result.success)
        self.assertTrue(all(mock.call_count == 1 for mock in entered))

    def test_one_shot_store_is_private_redacted_and_deletable(self):
        ref = ProviderSecretRef(profile_id="profile-1")
        secret = ProviderSecretValue(_FAKE_KEY)
        store = _OneShotDevSecretStore(ref, secret)

        self.assertFalse(hasattr(store, "__dict__"))
        self.assertNotIn(_FAKE_KEY, repr(store))
        self.assertIs(store.load_secret(ref), secret)
        self.assertTrue(store.delete_secret(ref))
        self.assertIsNone(store.load_secret(ref))

    def test_missing_secret_becomes_safe_provider_error(self):
        transport = RecordingTransport(self.valid_response())

        with patch.object(
            smoke,
            "_OneShotDevSecretStore",
            return_value=MissingSecretStore(),
        ):
            result = run_dev_real_provider_smoke(
                **self.run_args(),
                transport=transport,
            )

        self.assertFalse(result.execution_result.success)
        self.assertEqual(
            result.execution_result.error_display.kind.value,
            "auth_error",
        )
        self.assertEqual(transport.calls, [])

    def test_preview_over_500_characters_fails_without_sending_or_echoing(self):
        preview = "私" * 501
        transport = RecordingTransport(self.valid_response())
        output = io.StringIO()

        exit_code = main(
            self.cli_args(confirm=True, text=preview),
            environ={API_KEY_ENV_VAR: _FAKE_KEY},
            transport=transport,
            output_stream=output,
        )

        self.assertEqual(exit_code, 2)
        self.assertEqual(transport.calls, [])
        self.assertNotIn(preview, output.getvalue())

    def test_success_output_excludes_key_source_authorization_and_raw_response(self):
        preview = f"中文测试内容 {_PRIVATE_SOURCE}"
        transport = RecordingTransport(self.valid_response(evidence=_RAW_BODY))
        args = self.run_args()
        args["text"] = preview

        result = run_dev_real_provider_smoke(**args, transport=transport)
        rendered = format_dev_real_provider_smoke_output(result)

        for forbidden in (
            _FAKE_KEY,
            "Authorization",
            preview,
            _PRIVATE_SOURCE,
            _RAW_BODY,
            "knowledge_points",
        ):
            self.assertNotIn(forbidden, rendered)
        self.assertNotIn("验证集", rendered)
        self.assertIn("Will write to Anki: no", rendered)

    def test_invalid_json_outputs_only_safe_provider_display(self):
        response = OpenAICompatibleTransportResponse(
            status_code=200,
            json_body={"choices": [{"message": {"content": "not json"}}]},
        )

        exit_code, rendered = self.run_main_with_response(response)

        self.assertEqual(exit_code, 1)
        self.assertIn("provider_error.invalid_json", rendered)
        self.assertNotIn("not json", rendered)

    def test_malformed_response_outputs_only_safe_provider_display(self):
        response = OpenAICompatibleTransportResponse(
            status_code=200,
            json_body={"private": _RAW_BODY},
        )

        exit_code, rendered = self.run_main_with_response(response)

        self.assertEqual(exit_code, 1)
        self.assertIn("provider_error.malformed_response", rendered)
        self.assertNotIn(_RAW_BODY, rendered)

    def test_structured_failure_outputs_only_safe_provider_display(self):
        response = OpenAICompatibleTransportResponse(
            status_code=503,
            json_body={"private": _RAW_BODY},
        )

        exit_code, rendered = self.run_main_with_response(response)

        self.assertEqual(exit_code, 1)
        self.assertIn("provider_error.unknown_error", rendered)
        self.assertNotIn(_RAW_BODY, rendered)

    def test_transport_exception_never_reaches_stdout_or_stderr(self):
        transport = RecordingTransport(error=RuntimeError(_RAW_EXCEPTION))
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stderr(stderr), self.block_real_network():
            exit_code = main(
                self.cli_args(confirm=True, text=_PRIVATE_SOURCE),
                environ={API_KEY_ENV_VAR: _FAKE_KEY},
                transport=transport,
                output_stream=stdout,
            )

        rendered = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("provider_error.unknown_error", rendered)
        for forbidden in (
            _FAKE_KEY,
            "Authorization",
            _PRIVATE_SOURCE,
            _RAW_EXCEPTION,
            "RuntimeError",
            "Traceback",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_result_repr_and_safe_dict_hide_key_and_preview(self):
        preview = _PRIVATE_SOURCE
        result = run_dev_real_provider_smoke(
            **{**self.run_args(), "text": preview},
            transport=RecordingTransport(self.valid_response()),
        )
        rendered = (
            f"{result!r}\n{result.execution_result!r}\n"
            f"{result.execution_result.to_safe_dict()}"
        )

        self.assertNotIn(_FAKE_KEY, rendered)
        self.assertNotIn(preview, rendered)
        self.assertNotIn("Authorization", rendered)

    def test_script_has_strict_dev_only_dependency_and_call_boundary(self):
        source_path = (
            Path(__file__).parents[1]
            / "scripts"
            / "dev_real_provider_smoke.py"
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
        called_names = {
            node.func.id if isinstance(node.func, ast.Name) else node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Name, ast.Attribute))
        }

        for forbidden_module in (
            "aqt",
            "anki",
            "PyQt",
            "ankiforge_ai.ui",
            "ankiforge_ai.anki_writer",
            "orchestrator",
            "config_loader",
        ):
            self.assertFalse(
                any(
                    module == forbidden_module
                    or module.startswith(f"{forbidden_module}.")
                    for module in imported_modules
                )
            )
        for forbidden_name in (
            "GeneratedCard",
            "CardCandidate",
            "HumanReview",
        ):
            self.assertNotIn(forbidden_name, imported_names)
        for required_call in (
            "create_provider_selection_from_profile",
            "create_provider_consent_record",
            "ProviderSecretRef",
            "ProviderDryRunRequest",
            "ProviderDryRunExecutionInput",
            "OpenAICompatibleProviderDryRunExecutor",
            "execute_openai_compatible_provider_dry_run_with_boundary",
        ):
            self.assertIn(required_call, called_names)
        for forbidden_call in (
            "open",
            "urlopen",
            "create_connection",
            "run_full_mock_pipeline",
            "write",
        ):
            self.assertNotIn(forbidden_call, called_names)

    def test_all_automatic_paths_use_fake_transport_and_block_network(self):
        transport = RecordingTransport(self.valid_response())

        with patch.object(
            smoke,
            "_create_dev_http_transport",
            side_effect=AssertionError("real transport creation is forbidden"),
        ), self.block_real_network():
            result = run_dev_real_provider_smoke(
                **self.run_args(),
                transport=transport,
            )

        self.assertTrue(result.execution_result.success)

    def test_docs_describe_v06_boundaries_and_contain_no_fake_key(self):
        document = (
            Path(__file__).parents[1] / "docs" / "dev_real_provider_smoke.md"
        ).read_text(encoding="utf-8")

        self.assertNotIn(_FAKE_KEY, document)
        for phrase in (
            "developer-only manual verification tool",
            "not a formal key-storage solution",
            "500 characters",
            "ProviderDryRunExecutionResult",
            "does not write to Anki",
            "PR7c",
        ):
            self.assertIn(phrase, document)

    @staticmethod
    def cli_args(confirm, text="中文测试内容"):
        args = [
            "--provider-id",
            "manual-provider",
            "--provider-name",
            "Manual Provider",
            "--model-name",
            "manual-model",
            "--base-url",
            "https://provider.example.invalid/v1",
            "--text",
            text,
        ]
        if confirm:
            args.append("--confirm-send")
        return args

    @staticmethod
    def run_args():
        return {
            "provider_id": "manual-provider",
            "provider_name": "Manual Provider",
            "model_name": "manual-model",
            "base_url": "https://provider.example.invalid/v1",
            "secret_value": ProviderSecretValue(_FAKE_KEY),
            "confirmed": True,
            "text": "中文测试内容",
            "consented_at": datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc),
        }

    @staticmethod
    def valid_response(evidence="验证集用于评估模型的泛化表现。"):
        content = json.dumps(
            {
                "knowledge_points": [
                    {
                        "title": "验证集",
                        "explanation": "验证集用于模型选择。",
                        "evidence": evidence,
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

    @classmethod
    def run_main_with_response(cls, response):
        output = io.StringIO()
        exit_code = main(
            cls.cli_args(confirm=True, text=_PRIVATE_SOURCE),
            environ={API_KEY_ENV_VAR: _FAKE_KEY},
            transport=RecordingTransport(response),
            output_stream=output,
        )
        return exit_code, output.getvalue()

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
