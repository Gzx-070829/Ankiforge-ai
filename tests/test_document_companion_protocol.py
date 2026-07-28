import dataclasses
import json
import math
import unittest


class CompanionProtocolTests(unittest.TestCase):
    def test_all_messages_reject_non_integer_or_out_of_range_versions(self):
        from ankiforge_ai.document.backends import (
            CompanionProgress,
            CompanionRequest,
            CompanionResponse,
        )

        constructors = (
            lambda version: CompanionRequest(
                protocol_version=version,
                request_id="request-123",
                operation="health",
            ),
            lambda version: CompanionProgress(
                protocol_version=version,
                request_id="request-123",
                stage="converting",
                completed=0,
                total=1,
            ),
            lambda version: CompanionResponse(
                protocol_version=version,
                request_id="request-123",
                status="ok",
            ),
        )
        invalid_versions = (
            1.0,
            "1",
            True,
            math.nan,
            math.inf,
            -math.inf,
            10**100,
        )
        for constructor in constructors:
            for version in invalid_versions:
                with self.subTest(
                    message=constructor,
                    version_type=type(version).__name__,
                ):
                    with self.assertRaisesRegex(
                        ValueError,
                        "^unsupported companion protocol version$",
                    ) as caught:
                        constructor(version)
                    diagnostic = repr(caught.exception)
                    self.assertNotIn(repr(version), diagnostic)

    def test_request_round_trip_is_strict_versioned_and_immutable(self):
        from ankiforge_ai.document.backends import CompanionRequest

        request = CompanionRequest(
            protocol_version=1,
            request_id="request-123",
            operation="convert",
            capability="document.convert",
            local_file_token="file-456",
        )
        decoded = CompanionRequest.from_json(request.to_json())

        self.assertEqual(decoded, request)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            decoded.operation = "cancel"
        with self.assertRaisesRegex(ValueError, "unexpected"):
            CompanionRequest.from_json(
                json.dumps(
                    {
                        **json.loads(request.to_json()),
                        "url": "https://example.invalid/document",
                    }
                )
            )
        with self.assertRaisesRegex(ValueError, "protocol"):
            CompanionRequest.from_json(
                request.to_json().replace(
                    '"protocol_version":1',
                    '"protocol_version":2',
                )
            )

    def test_progress_and_response_are_bounded_and_do_not_leak_payloads(self):
        from ankiforge_ai.document.backends import (
            CompanionProgress,
            CompanionResponse,
        )

        progress = CompanionProgress(
            protocol_version=1,
            request_id="request-123",
            stage="converting",
            completed=1,
            total=2,
        )
        self.assertEqual(
            CompanionProgress.from_json(progress.to_json()),
            progress,
        )
        response = CompanionResponse(
            protocol_version=1,
            request_id="request-123",
            status="error",
            error_code="backend_unavailable",
            message_key="document.error.backend_unavailable",
            action_key="document.action.enable_backend",
        )
        self.assertEqual(
            CompanionResponse.from_json(response.to_json()),
            response,
        )
        self.assertNotIn("C:\\private\\source.pdf", repr(response))
        with self.assertRaisesRegex(ValueError, "bounded"):
            CompanionProgress(
                protocol_version=1,
                request_id="request-123",
                stage="x" * 129,
                completed=0,
                total=1,
            )

    def test_protocol_models_expose_no_remote_or_secret_fields(self):
        from ankiforge_ai.document.backends import (
            CompanionProgress,
            CompanionRequest,
            CompanionResponse,
        )

        forbidden = ("url", "credential", "secret", "api_key", "cookie")
        for model in (CompanionRequest, CompanionProgress, CompanionResponse):
            names = {field.name.casefold() for field in dataclasses.fields(model)}
            self.assertFalse(
                any(token in name for token in forbidden for name in names),
                (model.__name__, names),
            )


if __name__ == "__main__":
    unittest.main()
