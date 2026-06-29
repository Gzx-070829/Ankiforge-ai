"""DEV ONLY manual smoke harness for an OpenAI-compatible provider.

DO NOT COMMIT REAL API KEYS.
DOES NOT WRITE TO ANKI.
SENDS PROVIDED TEXT TO THE CONFIGURED PROVIDER.
"""

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping, Optional, Sequence, TextIO, Tuple

from ankiforge_ai.pipeline.openai_compatible_http_transport import (
    OpenAICompatibleHTTPTransport,
)
from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleTransport,
)
from ankiforge_ai.pipeline.provider_consent import (
    create_provider_consent_record,
    create_provider_selection_from_profile,
)
from ankiforge_ai.pipeline.provider_dry_run_execution import (
    ProviderDryRunExecutionInput,
    ProviderDryRunExecutionResult,
)
from ankiforge_ai.pipeline.provider_dry_run_request import (
    ProviderDryRunRequest,
)
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


API_KEY_ENV_VAR = "ANKIFORGE_DEV_API_KEY"
DEFAULT_SAMPLE_TEXT = "监督学习使用带标签的数据训练模型。"
_PRIVACY_NOTICE = (
    "DEV ONLY: the source preview is sent to the configured provider."
)
_CONSENT_TEXT = (
    "I explicitly consent to send this source preview to the provider."
)
_SENSITIVE_OUTPUT_MARKERS = (
    "api_key",
    "api-key",
    "api key",
    "apikey",
    "authorization",
    "bearer",
    "password",
    "secret",
    "token",
    "raw response",
    "raw body",
    "stack trace",
)


class SafeArgumentParser(argparse.ArgumentParser):
    """Avoid echoing unknown argument values that may contain a secret."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: invalid arguments.\n")


class DevSmokeConfigurationError(ValueError):
    """A safe configuration error that never includes credential values."""


class _OneShotDevSecretStore:
    """DEV ONLY one-secret adapter; this is not a storage backend."""

    __slots__ = ("_ref", "_value")

    def __init__(
        self,
        ref: ProviderSecretRef,
        value: ProviderSecretValue,
    ) -> None:
        if not isinstance(ref, ProviderSecretRef):
            raise DevSmokeConfigurationError("A valid secret reference is required.")
        if not isinstance(value, ProviderSecretValue):
            raise DevSmokeConfigurationError("A runtime secret value is required.")
        self._ref = ref
        self._value = value

    def save_secret(
        self,
        ref: ProviderSecretRef,
        value: ProviderSecretValue,
    ) -> None:
        raise DevSmokeConfigurationError(
            "The dev one-shot store does not save replacement secrets."
        )

    def load_secret(
        self,
        ref: ProviderSecretRef,
    ) -> ProviderSecretValue | None:
        if ref != self._ref:
            return None
        return self._value

    def has_secret(self, ref: ProviderSecretRef) -> bool:
        return ref == self._ref and self._value is not None

    def delete_secret(self, ref: ProviderSecretRef) -> bool:
        if ref != self._ref or self._value is None:
            return False
        self._value = None
        return True

    def __repr__(self) -> str:
        return "<dev-one-shot-secret-store>"

    __str__ = __repr__


@dataclass(frozen=True)
class DevRealProviderSmokeResult:
    provider_name: str = field(repr=False)
    model_name: str = field(repr=False)
    execution_result: ProviderDryRunExecutionResult = field(repr=False)
    knowledge_point_titles: Tuple[str, ...] = field(repr=False)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(
        description=(
            "DEV ONLY / MANUAL ONLY: send a short consented preview to an "
            "explicitly configured OpenAI-compatible provider. This never "
            "writes to Anki."
        )
    )
    parser.add_argument("--provider-id", required=True)
    parser.add_argument("--provider-name", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--text", default=DEFAULT_SAMPLE_TEXT)
    parser.add_argument(
        "--confirm-send",
        action="store_true",
        help="Confirm that the supplied preview may be sent to the provider.",
    )
    return parser


def run_dev_real_provider_smoke(
    *,
    provider_id: str,
    provider_name: str,
    model_name: str,
    base_url: str,
    secret_value: ProviderSecretValue,
    confirmed: bool,
    text: str = DEFAULT_SAMPLE_TEXT,
    timeout_seconds: float = 60.0,
    transport: Optional[OpenAICompatibleTransport] = None,
    consented_at: Optional[datetime] = None,
) -> DevRealProviderSmokeResult:
    """Run one consent-gated dry run through the v0.6 execution boundary."""
    if confirmed is not True:
        raise DevSmokeConfigurationError(
            "Explicit --confirm-send acknowledgement is required."
        )
    if not isinstance(secret_value, ProviderSecretValue):
        raise DevSmokeConfigurationError(
            f"{API_KEY_ENV_VAR} must provide a runtime secret."
        )

    profile = UserProviderProfile(
        profile_id="dev-manual-provider-profile",
        provider_id=provider_id,
        provider_name=provider_name,
        model_name=model_name,
        base_url=base_url,
        privacy_notice=_PRIVACY_NOTICE,
        timeout_seconds=timeout_seconds,
    )
    selection = create_provider_selection_from_profile(profile)
    consent = create_provider_consent_record(
        selection=selection,
        consent_text=_CONSENT_TEXT,
        privacy_notice=_PRIVACY_NOTICE,
        consented_at=(consented_at or datetime.now(timezone.utc)),
    )
    secret_ref = ProviderSecretRef(profile_id=profile.profile_id)
    request = ProviderDryRunRequest(
        selection=selection,
        consent=consent,
        secret_ref=secret_ref,
        source_chunk_id=_build_source_chunk_id(text),
        source_title="Developer smoke preview",
        source_excerpt_preview=text,
    )
    execution_input = ProviderDryRunExecutionInput(request)
    secret_store: ProviderSecretStore = _OneShotDevSecretStore(
        secret_ref,
        secret_value,
    )
    executor = None

    try:
        resolved_transport = (
            transport if transport is not None else _create_dev_http_transport()
        )
        executor = OpenAICompatibleProviderDryRunExecutor(
            profile=profile,
            secret_store=secret_store,
            transport=resolved_transport,
        )
        execution_result = (
            execute_openai_compatible_provider_dry_run_with_boundary(
                execution_input,
                executor,
            )
        )
        return DevRealProviderSmokeResult(
            provider_name=profile.provider_name,
            model_name=profile.model_name,
            execution_result=execution_result,
            knowledge_point_titles=tuple(
                point.title for point in execution_result.knowledge_points
            ),
        )
    finally:
        secret_store.delete_secret(secret_ref)
        executor = None
        secret_store = None
        secret_value = None


def format_dev_real_provider_smoke_output(
    result: DevRealProviderSmokeResult,
) -> str:
    """Render only safe execution fields and knowledge-point titles."""
    execution_result = result.execution_result
    error_display = execution_result.error_display
    lines = [
        f"Provider: {_safe_display_text(result.provider_name)}",
        f"Model: {_safe_display_text(result.model_name)}",
        "Sends user content: yes",
        f"Succeeded: {_yes_no(execution_result.success)}",
        f"Knowledge points: {len(execution_result.knowledge_points)}",
        f"Will write to Anki: {_yes_no(execution_result.will_write_to_anki)}",
    ]
    if error_display is not None:
        lines.extend(
            (
                f"Error title: {_safe_display_text(error_display.user_title)}",
                f"Message: {_safe_display_text(error_display.user_message)}",
                f"Suggested action: {_safe_display_text(error_display.suggested_action)}",
                f"Diagnostic code: {_safe_display_text(error_display.safe_diagnostic_code)}",
                f"Retryable: {_yes_no(error_display.retryable)}",
            )
        )
    return "\n".join(lines)


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    environ: Optional[Mapping[str, str]] = None,
    transport: Optional[OpenAICompatibleTransport] = None,
    output_stream: Optional[TextIO] = None,
) -> int:
    args = build_argument_parser().parse_args(argv)
    output = output_stream or sys.stdout

    if not args.confirm_send:
        print(
            "Smoke cancelled: explicit --confirm-send acknowledgement is required.",
            file=output,
        )
        return 2

    environment = os.environ if environ is None else environ
    raw_api_key = environment.get(API_KEY_ENV_VAR, "")
    if not isinstance(raw_api_key, str) or not raw_api_key.strip():
        print(
            f"Smoke cancelled: {API_KEY_ENV_VAR} is not set.",
            file=output,
        )
        return 2

    secret_value = ProviderSecretValue(raw_api_key)
    raw_api_key = None
    try:
        result = run_dev_real_provider_smoke(
            provider_id=args.provider_id,
            provider_name=args.provider_name,
            model_name=args.model_name,
            base_url=args.base_url,
            secret_value=secret_value,
            confirmed=True,
            text=args.text,
            timeout_seconds=args.timeout_seconds,
            transport=transport,
        )
    except DevSmokeConfigurationError as error:
        print(f"Smoke cancelled: {error}", file=output)
        return 2
    except ValueError:
        print(
            "Smoke cancelled: check provider, model, URL, timeout, and preview length.",
            file=output,
        )
        return 2
    except Exception:
        print(
            "Smoke failed before a safe provider result could be created.",
            file=output,
        )
        return 2
    finally:
        secret_value = None

    print(format_dev_real_provider_smoke_output(result), file=output)
    return 0 if result.execution_result.success else 1


def _create_dev_http_transport() -> OpenAICompatibleTransport:
    """Create a real transport only for an explicitly confirmed manual run."""
    return OpenAICompatibleHTTPTransport()


def _build_source_chunk_id(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise DevSmokeConfigurationError("Smoke preview text must not be empty.")
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"dev_smoke_{text_hash[:16]}"


def _safe_display_text(value: object, max_length: int = 120) -> str:
    text = " ".join(str(value or "").split())
    lowered = text.lower()
    if any(marker in lowered for marker in _SENSITIVE_OUTPUT_MARKERS):
        return "[redacted]"
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3]}..."


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


if __name__ == "__main__":
    raise SystemExit(main())
