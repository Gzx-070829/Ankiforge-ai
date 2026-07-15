import ast
import copy
import io
import json
import socket
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.ai_extraction_service import extract_knowledge_points
from ankiforge_ai.pipeline.ai_provider_contracts import (
    build_knowledge_point_extraction_request,
)
from ankiforge_ai.pipeline.models import SourceChunk
from ankiforge_ai.pipeline.openai_compatible_http_transport import (
    OpenAICompatibleHTTPTransport,
    _NoRedirectHandler,
)
from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleKnowledgePointProvider,
    OpenAICompatibleProviderConfig,
    OpenAICompatibleTransport,
)


class FakeHTTPResponse:
    def __init__(self, status_code=200, body=b"{}"):
        self.status_code = status_code
        self.body = body
        self.read_count = 0
        self.closed = False

    def getcode(self):
        return self.status_code

    def read(self, size=-1):
        self.read_count += 1
        return self.body if size < 0 else self.body[:size]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.closed = True


class FakeOpener:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def __call__(self, request, timeout=None):
        self.calls.append({"request": request, "timeout": timeout})
        if self.error is not None:
            raise self.error
        return self.response


class TrackingErrorBody(io.BytesIO):
    def __init__(self, value):
        super().__init__(value)
        self.read_count = 0
        self.read_sizes = []

    def read(self, *args, **kwargs):
        self.read_count += 1
        self.read_sizes.append(args[0] if args else -1)
        return super().read(*args, **kwargs)


class OpenAICompatibleHTTPTransportTests(unittest.TestCase):
    def test_transport_is_protocol_compatible(self):
        transport = OpenAICompatibleHTTPTransport(
            FakeOpener(response=FakeHTTPResponse())
        )

        self.assertIsInstance(transport, OpenAICompatibleTransport)

    def test_successful_response_is_decoded_as_json(self):
        response = FakeHTTPResponse(
            status_code=201,
            body=json.dumps({"result": "成功"}, ensure_ascii=False).encode("utf-8"),
        )
        transport = OpenAICompatibleHTTPTransport(FakeOpener(response=response))

        result = transport.post_json(
            "https://api.example.invalid/v1/chat/completions",
            {"Content-Type": "application/json"},
            {"input": "中文"},
            8.5,
        )

        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json_body, {"result": "成功"})
        self.assertEqual(response.read_count, 1)
        self.assertTrue(response.closed)

    def test_http_error_returns_status_with_bounded_sanitized_detail(self):
        body = TrackingErrorBody(b'{"error":{"message":"quota reached"}}')
        error = urllib.error.HTTPError(
            url="https://api.example.invalid/v1/chat/completions",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=body,
        )
        transport = OpenAICompatibleHTTPTransport(FakeOpener(error=error))

        result = transport.post_json(
            "https://api.example.invalid/v1/chat/completions",
            {"Authorization": "Bearer test-api-key"},
            {"private": "用户资料"},
            3.0,
        )

        self.assertEqual(result.status_code, 429)
        self.assertIsNone(result.json_body)
        self.assertEqual(body.read_count, 1)
        self.assertEqual(body.read_sizes, [8192])
        self.assertEqual(result.error_detail, "quota reached")
        self.assertTrue(body.closed)

    def test_non_raising_http_failure_is_also_bounded_and_sanitized(self):
        secret = "response-secret-value"
        response = FakeHTTPResponse(
            status_code=500,
            body=(
                '{"error":{"message":"Authorization=Bearer '
                + secret
                + " "
                + "private material " * 1000
                + '"}}'
            ).encode("utf-8"),
        )
        transport = OpenAICompatibleHTTPTransport(
            FakeOpener(response=response)
        )

        result = transport.post_json(
            "https://api.example.invalid/v1/chat/completions",
            {"Authorization": f"Bearer {secret}"},
            {},
            3.0,
        )

        self.assertEqual(result.status_code, 500)
        self.assertIsNone(result.json_body)
        self.assertNotIn(secret, result.error_detail)
        self.assertLessEqual(len(result.error_detail), 300)
        self.assertTrue(response.closed)

    def test_transport_blocks_denied_endpoint_before_opener(self):
        opener = FakeOpener(response=FakeHTTPResponse())

        with self.assertRaisesRegex(ValueError, "provider endpoint is denied"):
            OpenAICompatibleHTTPTransport(opener).post_json(
                "http://169.254.169.254/latest/meta-data",
                {"Authorization": "Bearer fake-key"},
                {},
                1.0,
            )

        self.assertEqual(opener.calls, [])

    def test_malformed_json_returns_none_body_with_original_status(self):
        transport = OpenAICompatibleHTTPTransport(
            FakeOpener(response=FakeHTTPResponse(200, b"{not json"))
        )

        result = transport.post_json(
            "https://api.example.invalid",
            {},
            {},
            None,
        )

        self.assertEqual(result.status_code, 200)
        self.assertIsNone(result.json_body)

    def test_utf8_decode_failure_returns_none_body_with_original_status(self):
        transport = OpenAICompatibleHTTPTransport(
            FakeOpener(response=FakeHTTPResponse(202, b"\xff\xfe"))
        )

        result = transport.post_json(
            "https://api.example.invalid",
            {},
            {},
            None,
        )

        self.assertEqual(result.status_code, 202)
        self.assertIsNone(result.json_body)

    def test_request_passes_headers_timeout_and_utf8_json_payload(self):
        opener = FakeOpener(response=FakeHTTPResponse(200, b"{}"))
        transport = OpenAICompatibleHTTPTransport(opener)
        payload = {"model": "test-model", "text": "中文内容"}

        transport.post_json(
            "https://api.example.invalid/v1/chat/completions",
            {
                "Authorization": "Bearer test-api-key",
                "Content-Type": "application/json",
            },
            payload,
            12.5,
        )

        call = opener.calls[0]
        request = call["request"]
        self.assertEqual(call["timeout"], 12.5)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-api-key")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(json.loads(request.data.decode("utf-8")), payload)

    def test_injected_opener_never_touches_real_urlopen_or_socket(self):
        opener = FakeOpener(response=FakeHTTPResponse(200, b"{}"))
        transport = OpenAICompatibleHTTPTransport(opener)

        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Real urlopen must not be called."),
        ), patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Real network must not be accessed."),
        ):
            result = transport.post_json(
                "https://api.example.invalid",
                {},
                {},
                1.0,
            )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(opener.calls), 1)

    def test_default_opener_is_resolved_without_real_network(self):
        opener = FakeOpener(response=FakeHTTPResponse(200, b"{}"))
        built_opener = type("BuiltOpener", (), {"open": staticmethod(opener)})()
        with patch.object(
            urllib.request,
            "build_opener",
            return_value=built_opener,
        ) as build_opener:
            transport = OpenAICompatibleHTTPTransport()
            result = transport.post_json(
                "https://api.example.invalid",
                {},
                {},
                2.0,
            )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(build_opener.call_count, 1)
        handler = build_opener.call_args.args[0]
        self.assertIsInstance(handler, _NoRedirectHandler)

    def test_redirect_handler_never_forwards_the_authorized_request(self):
        request = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": "Bearer fake-session-key"},
        )

        redirected = _NoRedirectHandler().redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://unconfirmed.example/v1/chat/completions",
        )

        self.assertIsNone(redirected)

    def test_network_and_timeout_exceptions_are_not_caught(self):
        errors = (
            urllib.error.URLError("offline"),
            TimeoutError("timed out"),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                transport = OpenAICompatibleHTTPTransport(FakeOpener(error=error))
                with self.assertRaises(type(error)):
                    transport.post_json(
                        "https://api.example.invalid",
                        {},
                        {},
                        1.0,
                    )

    def test_provider_and_extraction_service_integrate_offline_with_chinese(self):
        knowledge_point_json = json.dumps(
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
        provider_body = json.dumps(
            {
                "choices": [
                    {"message": {"content": knowledge_point_json}}
                ]
            },
            ensure_ascii=False,
        ).encode("utf-8")
        opener = FakeOpener(response=FakeHTTPResponse(200, provider_body))
        provider = OpenAICompatibleKnowledgePointProvider(
            self.config(),
            OpenAICompatibleHTTPTransport(opener),
        )
        chunk = self.chunk()

        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Real urlopen must not be called."),
        ), patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Real network must not be accessed."),
        ):
            outcome = extract_knowledge_points(chunk, provider)

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.knowledge_points[0].title, "特征值")
        self.assertEqual(outcome.knowledge_points[0].tags, ["线性代数"])
        sent_payload = json.loads(opener.calls[0]["request"].data.decode("utf-8"))
        self.assertEqual(sent_payload["messages"][1]["content"], chunk.text)

    def test_transport_does_not_modify_inputs(self):
        headers = {"Authorization": "Bearer test-api-key"}
        payload = {"messages": [{"content": "中文资料"}]}
        before_headers = copy.deepcopy(headers)
        before_payload = copy.deepcopy(payload)
        transport = OpenAICompatibleHTTPTransport(
            FakeOpener(response=FakeHTTPResponse(200, b"{}"))
        )

        transport.post_json(
            "https://api.example.invalid",
            headers,
            payload,
            1.0,
        )

        self.assertEqual(headers, before_headers)
        self.assertEqual(payload, before_payload)

    def test_module_has_only_expected_standard_library_dependencies(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "openai_compatible_http_transport.py"
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
            "config",
            "anki_writer",
            "logging",
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
        self.assertNotIn("print(", source)

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
