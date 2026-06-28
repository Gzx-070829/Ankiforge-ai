"""DEV ONLY manual smoke harness for an OpenAI-compatible provider.

DO NOT COMMIT REAL API KEYS.
DOES NOT WRITE TO ANKI.
SENDS PROVIDED TEXT TO THE CONFIGURED PROVIDER.
"""

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, TextIO, Tuple

from ankiforge_ai.pipeline.models import SourceChunk
from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleProviderConfig,
    OpenAICompatibleTransport,
)
from ankiforge_ai.pipeline.provider_dry_run_summary import (
    ProviderDryRunContext,
    ProviderDryRunSummary,
    create_provider_dry_run_summary,
)
from ankiforge_ai.pipeline.provider_factory import (
    create_openai_compatible_knowledge_point_extractor,
)


API_KEY_ENV_VAR = "ANKIFORGE_DEV_API_KEY"
DEFAULT_SAMPLE_TEXT = "监督学习使用带标签的数据训练模型。"


class SafeArgumentParser(argparse.ArgumentParser):
    """Avoid echoing unknown argument values that may contain a secret."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: invalid arguments.\n")


class DevSmokeConfigurationError(ValueError):
    """A safe configuration error that never includes credential values."""


@dataclass(frozen=True)
class DevRealProviderSmokeResult:
    summary: ProviderDryRunSummary
    knowledge_point_titles: Tuple[str, ...]


def build_argument_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(
        description=(
            "DEV ONLY: send short text to an explicitly configured "
            "OpenAI-compatible provider. This never writes to Anki."
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
        help="Confirm that the supplied text may be sent to the provider.",
    )
    return parser


def build_dev_provider_config(
    *,
    provider_id: str,
    provider_name: str,
    model_name: str,
    base_url: str,
    api_key: str,
    timeout_seconds: float = 60.0,
) -> OpenAICompatibleProviderConfig:
    _require_api_key(api_key)
    return OpenAICompatibleProviderConfig(
        provider_id=provider_id,
        provider_name=provider_name,
        model_name=model_name,
        base_url=base_url,
        api_key=api_key.strip(),
        privacy_notice=(
            "DEV ONLY: supplied text is sent to the configured provider."
        ),
        timeout_seconds=timeout_seconds,
    )


def run_dev_real_provider_smoke(
    *,
    provider_id: str,
    provider_name: str,
    model_name: str,
    base_url: str,
    api_key: str,
    confirmed: bool,
    text: str = DEFAULT_SAMPLE_TEXT,
    timeout_seconds: float = 60.0,
    transport: Optional[OpenAICompatibleTransport] = None,
) -> DevRealProviderSmokeResult:
    """Run one explicitly confirmed extraction and return safe diagnostics."""
    if confirmed is not True:
        raise DevSmokeConfigurationError(
            "Explicit --confirm-send acknowledgement is required."
        )
    _require_api_key(api_key)
    if not isinstance(text, str) or not text.strip():
        raise DevSmokeConfigurationError("Smoke input text must not be empty.")

    config = build_dev_provider_config(
        provider_id=provider_id,
        provider_name=provider_name,
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
    extractor = create_openai_compatible_knowledge_point_extractor(
        config,
        transport=transport,
        wrap_safe=True,
    )
    outcome = extractor.extract_from_chunk(_build_source_chunk(text))
    summary = create_provider_dry_run_summary(
        outcome,
        ProviderDryRunContext(
            provider_id=provider_id,
            provider_name=provider_name,
            model_name=model_name,
            is_mock=False,
            sends_user_content=True,
            supports_json_output=True,
            safety_wrapped=True,
        ),
    )
    return DevRealProviderSmokeResult(
        summary=summary,
        knowledge_point_titles=tuple(
            point.title for point in outcome.knowledge_points
        ),
    )


def format_dev_real_provider_smoke_output(
    result: DevRealProviderSmokeResult,
) -> str:
    """Render only credential-free summary fields and knowledge-point titles."""
    summary = result.summary
    lines = [
        f"Provider: {_safe_display_text(summary.provider_name)}",
        f"Model: {_safe_display_text(summary.model_name)}",
        f"Sends user content: {_yes_no(summary.sends_user_content)}",
        f"Succeeded: {_yes_no(summary.succeeded)}",
        f"Knowledge points: {summary.knowledge_point_count}",
        f"Error type: {_safe_display_text(summary.error_type or 'none')}",
        f"Message: {_safe_display_text(summary.user_safe_message)}",
        f"Will write to Anki: {_yes_no(summary.will_write_to_anki)}",
    ]
    if result.knowledge_point_titles:
        lines.append("Knowledge point titles:")
        lines.extend(
            f"- {_safe_display_text(title)}"
            for title in result.knowledge_point_titles
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
    environment = os.environ if environ is None else environ

    if not args.confirm_send:
        print(
            "Smoke cancelled: explicit --confirm-send acknowledgement is required.",
            file=output,
        )
        return 2

    api_key = environment.get(API_KEY_ENV_VAR, "")
    if not isinstance(api_key, str) or not api_key.strip():
        print(
            f"Smoke cancelled: {API_KEY_ENV_VAR} is not set.",
            file=output,
        )
        return 2

    try:
        result = run_dev_real_provider_smoke(
            provider_id=args.provider_id,
            provider_name=args.provider_name,
            model_name=args.model_name,
            base_url=args.base_url,
            api_key=api_key,
            confirmed=True,
            text=args.text,
            timeout_seconds=args.timeout_seconds,
            transport=transport,
        )
    except DevSmokeConfigurationError as exc:
        print(f"Smoke cancelled: {exc}", file=output)
        return 2
    except ValueError:
        print(
            "Smoke cancelled: check provider, model, URL, timeout, and text values.",
            file=output,
        )
        return 2
    except Exception:
        print(
            "Smoke failed before a safe provider summary could be created.",
            file=output,
        )
        return 2

    print(format_dev_real_provider_smoke_output(result), file=output)
    return 0 if result.summary.succeeded else 1


def _build_source_chunk(text: str) -> SourceChunk:
    normalized_text = text.strip()
    text_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    return SourceChunk(
        chunk_id=f"dev_smoke_{text_hash[:16]}",
        document_id="dev_real_provider_smoke",
        file_path="",
        file_name="dev_manual_input",
        heading_path=["Developer smoke input"],
        heading_level=1,
        ordinal=0,
        text=normalized_text,
        chunk_hash=text_hash,
        source_display="Developer smoke input",
    )


def _require_api_key(api_key: str) -> None:
    if not isinstance(api_key, str) or not api_key.strip():
        raise DevSmokeConfigurationError(
            f"{API_KEY_ENV_VAR} must be provided through the environment."
        )


def _safe_display_text(value: object, max_length: int = 120) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3]}..."


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


if __name__ == "__main__":
    raise SystemExit(main())
