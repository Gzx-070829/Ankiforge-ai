import ast
import inspect
import json
import socket
import unittest
import urllib.request
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.provider_error_display import (
    ProviderErrorDisplay,
    ProviderErrorKind,
    create_provider_error_display,
)


class SensitiveObject:
    def __repr__(self):
        return "test-api-key PRIVATE SOURCE TEXT raw payload"

    def __str__(self):
        return "test-api-key PRIVATE SOURCE TEXT raw payload"


class ProviderErrorDisplayTests(unittest.TestCase):
    def test_every_error_kind_maps_to_a_display(self):
        self.assertEqual(len(ProviderErrorKind), 11)

        for kind in ProviderErrorKind:
            with self.subTest(kind=kind):
                display = create_provider_error_display(kind)
                self.assertIsInstance(display, ProviderErrorDisplay)
                self.assertIs(display.kind, kind)
                self.assertTrue(display.user_title.strip())
                self.assertTrue(display.user_message.strip())
                self.assertTrue(display.suggested_action.strip())
                self.assertTrue(display.safe_diagnostic_code.strip())
                self.assertIs(type(display.retryable), bool)

    def test_display_is_frozen(self):
        display = create_provider_error_display(ProviderErrorKind.NETWORK_ERROR)

        with self.assertRaises(FrozenInstanceError):
            display.retryable = False

    def test_kind_must_be_provider_error_kind(self):
        with self.assertRaises(ValueError):
            create_provider_error_display("network_error")
        with self.assertRaises(ValueError):
            self.display(kind="network_error")

    def test_display_requires_safe_non_empty_text_fields(self):
        for field_name in (
            "user_title",
            "user_message",
            "suggested_action",
            "safe_diagnostic_code",
        ):
            for value in ("", " ", "\n", SensitiveObject()):
                with self.subTest(field_name=field_name, value=type(value).__name__):
                    with self.assertRaises(ValueError) as context:
                        self.display(**{field_name: value})
                    self.assert_safe_error(context.exception)

    def test_retryable_must_be_bool(self):
        for value in (0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.display(retryable=value)

    def test_safe_dict_has_exact_fields_and_string_kind(self):
        display = create_provider_error_display(ProviderErrorKind.INVALID_JSON)

        data = display.to_safe_dict()

        self.assertEqual(
            set(data),
            {
                "kind",
                "user_title",
                "user_message",
                "suggested_action",
                "retryable",
                "safe_diagnostic_code",
            },
        )
        self.assertEqual(data["kind"], "invalid_json")
        self.assertIsInstance(data["kind"], str)

    def test_retryable_policy_is_conservative_and_fixed(self):
        retryable_kinds = {
            ProviderErrorKind.NETWORK_ERROR,
            ProviderErrorKind.TIMEOUT,
            ProviderErrorKind.RATE_LIMIT,
            ProviderErrorKind.PROVIDER_UNAVAILABLE,
        }

        for kind in ProviderErrorKind:
            with self.subTest(kind=kind):
                self.assertEqual(
                    create_provider_error_display(kind).retryable,
                    kind in retryable_kinds,
                )

    def test_unknown_error_uses_generic_safe_copy(self):
        display = create_provider_error_display(ProviderErrorKind.UNKNOWN_ERROR)

        self.assertIn("出现问题", display.user_title)
        self.assertIn("未能完成", display.user_message)
        self.assertEqual(display.safe_diagnostic_code, "provider_error.unknown_error")

    def test_valid_provider_name_is_used_as_display_label(self):
        display = create_provider_error_display(
            ProviderErrorKind.TIMEOUT,
            provider_name="示例 Provider",
        )

        self.assertTrue(display.user_title.startswith("示例 Provider："))

    def test_none_provider_name_uses_generic_label(self):
        display = create_provider_error_display(ProviderErrorKind.TIMEOUT)

        self.assertTrue(display.user_title.startswith("AI provider："))

    def test_unsafe_provider_names_are_rejected_without_echo(self):
        unsafe_names = (
            "",
            " ",
            "Provider\nInjected",
            "P" * 81,
            "test-api-key",
            "Authorization Bearer value",
            "raw payload",
            "PRIVATE SOURCE TEXT",
        )
        for provider_name in unsafe_names:
            with self.subTest(provider_name=provider_name[:20]):
                with self.assertRaises(ValueError) as context:
                    create_provider_error_display(
                        ProviderErrorKind.UNKNOWN_ERROR,
                        provider_name=provider_name,
                    )
                self.assert_safe_error(context.exception)

    def test_fixed_mappings_do_not_expose_sensitive_details(self):
        forbidden_values = (
            "test-api-key",
            "Authorization: Bearer private-value",
            "PRIVATE SOURCE TEXT",
            "PRIVATE CHUNK TEXT",
            "RAW RESPONSE BODY",
            "raw payload",
            "headers",
            "stack trace",
        )
        kinds = (
            ProviderErrorKind.AUTH_ERROR,
            ProviderErrorKind.INVALID_JSON,
            ProviderErrorKind.MALFORMED_RESPONSE,
            ProviderErrorKind.CONTENT_POLICY,
        )
        for kind in kinds:
            with self.subTest(kind=kind):
                display = create_provider_error_display(kind)
                rendered = "\n".join(
                    (
                        repr(display),
                        str(display),
                        json.dumps(display.to_safe_dict(), ensure_ascii=False),
                    )
                ).lower()
                for forbidden in forbidden_values:
                    self.assertNotIn(forbidden.lower(), rendered)

    def test_dto_itself_rejects_sensitive_display_content(self):
        for field_name, value in (
            ("user_title", "Authorization failed"),
            ("user_message", "PRIVATE SOURCE TEXT"),
            ("suggested_action", "Inspect raw response"),
            ("safe_diagnostic_code", "headers.exposed"),
        ):
            with self.subTest(field_name=field_name):
                with self.assertRaises(ValueError) as context:
                    self.display(**{field_name: value})
                self.assert_safe_error(context.exception)

    def test_helper_signature_accepts_no_raw_error_inputs(self):
        signature = inspect.signature(create_provider_error_display)

        self.assertEqual(list(signature.parameters), ["kind", "provider_name"])
        for forbidden in (
            "exception",
            "error_message",
            "raw_response",
            "payload",
            "source_text",
        ):
            self.assertNotIn(forbidden, signature.parameters)

    def test_mapping_does_not_access_network(self):
        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Network access is forbidden."),
        ), patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Network access is forbidden."),
        ):
            display = create_provider_error_display(
                ProviderErrorKind.NETWORK_ERROR
            )

        self.assertTrue(display.retryable)

    def test_module_has_strict_dependency_and_side_effect_boundary(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "provider_error_display.py"
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
        function_names = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        }

        self.assertEqual(imported_modules, {"dataclasses", "enum"})
        for forbidden_function in (
            "classify_exception",
            "capture_exception",
            "retry",
            "backoff",
            "execute",
            "send",
            "run",
            "notify",
            "log",
        ):
            self.assertNotIn(forbidden_function, function_names)
        for forbidden_text in (
            "ProviderDryRunRequest",
            "ProviderSecretRef",
            "ProviderSecretValue",
            "ProviderSecretStore",
            "config.json",
            "SourceChunk",
            "KnowledgePoint",
            "CardCandidate",
            "HumanReview",
            "GeneratedCard",
            "WriteReady",
            "self.cards",
            "urlopen",
            "post_json",
            ".reveal(",
        ):
            self.assertNotIn(forbidden_text, source)

    @staticmethod
    def display(**overrides):
        values = {
            "kind": ProviderErrorKind.UNKNOWN_ERROR,
            "user_title": "AI provider 出现问题",
            "user_message": "AI provider 未能完成本次请求。",
            "suggested_action": "请检查设置或稍后再试。",
            "retryable": False,
            "safe_diagnostic_code": "provider_error.unknown_error",
        }
        values.update(overrides)
        return ProviderErrorDisplay(**values)

    def assert_safe_error(self, error):
        message = str(error).lower()
        for forbidden in (
            "test-api-key",
            "authorization bearer",
            "private source text",
            "raw payload",
        ):
            self.assertNotIn(forbidden, message)


if __name__ == "__main__":
    unittest.main()
