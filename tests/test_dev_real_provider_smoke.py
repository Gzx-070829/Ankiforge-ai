import ast
import copy
import io
import json
import socket
import unittest
import urllib.request
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleTransportResponse,
)
from ankiforge_ai.pipeline.provider_factory import (
    create_openai_compatible_knowledge_point_extractor,
    create_openai_compatible_knowledge_point_provider,
)
from scripts.dev_real_provider_smoke import (
    API_KEY_ENV_VAR,
    build_dev_provider_config,
    format_dev_real_provider_smoke_output,
    main,
    run_dev_real_provider_smoke,
)


class RecordingTransport:
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
        raise RuntimeError(
            "test-api-key Authorization PRIVATE SOURCE RAW RESPONSE"
        )


class DevRealProviderSmokeTests(unittest.TestCase):
    def test_missing_api_key_exits_before_transport_call(self):
        transport = RecordingTransport(self.valid_response())
        output = io.StringIO()

        exit_code = main(
            self.cli_args(confirm=True),
            environ={},
            transport=transport,
            output_stream=output,
        )

        self.assertEqual(exit_code, 2)
        self.assertEqual(transport.calls, [])
        self.assertIn(API_KEY_ENV_VAR, output.getvalue())

    def test_missing_confirmation_exits_before_transport_call(self):
        transport = RecordingTransport(self.valid_response())
        output = io.StringIO()

        exit_code = main(
            self.cli_args(confirm=False),
            environ={API_KEY_ENV_VAR: "test-api-key"},
            transport=transport,
            output_stream=output,
        )

        self.assertEqual(exit_code, 2)
        self.assertEqual(transport.calls, [])
        self.assertIn("--confirm-send", output.getvalue())
        self.assertNotIn("test-api-key", output.getvalue())

    def test_cli_api_key_argument_is_rejected_without_echoing_value(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            main(
                self.cli_args(confirm=True)
                + ["--api-key", "cli-secret-must-not-appear"],
                environ={API_KEY_ENV_VAR: "test-api-key"},
            )

        self.assertEqual(raised.exception.code, 2)
        self.assertNotIn("cli-secret-must-not-appear", stderr.getvalue())
        self.assertNotIn("--api-key", stderr.getvalue())

    def test_fake_transport_completes_chinese_extraction_offline(self):
        transport = RecordingTransport(self.valid_response())

        with self.block_real_network():
            result = run_dev_real_provider_smoke(
                **self.run_args(),
                transport=transport,
            )

        self.assertTrue(result.summary.succeeded)
        self.assertEqual(result.summary.knowledge_point_count, 1)
        self.assertEqual(result.knowledge_point_titles, ("验证集",))
        self.assertFalse(result.summary.will_write_to_anki)
        self.assertEqual(len(transport.calls), 1)
        self.assertIn("中文测试内容", transport.calls[0]["payload"]["messages"][1]["content"])

    def test_success_output_excludes_key_source_authorization_and_raw_response(self):
        source = "中文测试内容 PRIVATE SOURCE SHOULD NOT BE PRINTED"
        raw_marker = "RAW RESPONSE BODY SHOULD NOT BE PRINTED"
        transport = RecordingTransport(self.valid_response(evidence=raw_marker))
        args = self.run_args()
        args["text"] = source

        result = run_dev_real_provider_smoke(**args, transport=transport)
        rendered = format_dev_real_provider_smoke_output(result)

        self.assertNotIn("test-api-key", rendered)
        self.assertNotIn("Authorization", rendered)
        self.assertNotIn(source, rendered)
        self.assertNotIn(raw_marker, rendered)
        self.assertNotIn("knowledge_points", rendered)
        self.assertIn("验证集", rendered)
        self.assertIn("Will write to Anki: no", rendered)

    def test_transport_exception_becomes_safe_summary_and_nonzero_exit(self):
        transport = RaisingTransport()
        output = io.StringIO()

        with self.block_real_network():
            exit_code = main(
                self.cli_args(confirm=True, text="PRIVATE SOURCE"),
                environ={API_KEY_ENV_VAR: "test-api-key"},
                transport=transport,
                output_stream=output,
            )

        rendered = output.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertEqual(transport.calls, 1)
        self.assertIn("AI provider 调用失败，已被安全拦截。", rendered)
        for secret in (
            "test-api-key",
            "Authorization",
            "PRIVATE SOURCE",
            "RAW RESPONSE",
            "RuntimeError",
        ):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, rendered)

    def test_config_provider_and_extractor_repr_do_not_expose_key(self):
        transport = RecordingTransport(self.valid_response())
        config = build_dev_provider_config(
            provider_id="manual-provider",
            provider_name="Manual Provider",
            model_name="manual-model",
            base_url="https://provider.example.invalid/v1",
            api_key="test-api-key",
        )
        provider = create_openai_compatible_knowledge_point_provider(
            config,
            transport=transport,
        )
        extractor = create_openai_compatible_knowledge_point_extractor(
            config,
            transport=transport,
        )

        for value in (config, provider, extractor):
            with self.subTest(value=type(value).__name__):
                self.assertNotIn("test-api-key", repr(value))
                self.assertNotIn("test-api-key", str(value))

    def test_main_success_returns_zero_and_only_uses_fake_transport(self):
        transport = RecordingTransport(self.valid_response())
        output = io.StringIO()

        with self.block_real_network():
            exit_code = main(
                self.cli_args(confirm=True),
                environ={API_KEY_ENV_VAR: "test-api-key"},
                transport=transport,
                output_stream=output,
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(transport.calls), 1)
        self.assertIn("Succeeded: yes", output.getvalue())
        self.assertIn("Will write to Anki: no", output.getvalue())

    def test_script_has_no_plugin_ui_anki_or_write_dependencies(self):
        source_path = (
            Path(__file__).parents[1]
            / "scripts"
            / "dev_real_provider_smoke.py"
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
            "ankiforge_ai.ui",
            "ankiforge_ai.anki_writer",
            "config_loader",
        )

        self.assertFalse(
            any(
                module == prefix or module.startswith(f"{prefix}.")
                for module in imported_modules
                for prefix in forbidden
            )
        )
        self.assertNotIn("GeneratedCard", source)
        self.assertNotIn("CardCandidate", source)
        self.assertNotIn("HumanReview", source)
        self.assertNotIn("self.cards", source)
        self.assertNotIn("urlopen", source)
        self.assertNotIn("socket", source)

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
            "api_key": "test-api-key",
            "confirmed": True,
            "text": "中文测试内容",
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
