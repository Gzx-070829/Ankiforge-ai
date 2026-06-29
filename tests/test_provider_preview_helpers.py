import ast
import json
import unittest
from pathlib import Path

from ankiforge_ai.pipeline.provider_error_display import (
    ProviderErrorKind,
    create_provider_error_display,
)
from ankiforge_ai.pipeline.provider_preview import (
    ProviderDryRunRequestPreview,
    ReadOnlyProviderPreview,
)
from ankiforge_ai.ui.provider_preview_helpers import (
    EMPTY_PROVIDER_PREVIEW_MESSAGE,
    MAX_PROVIDER_EXCERPT_DISPLAY_CHARS,
    build_provider_preview_view_data,
    truncate_provider_preview_excerpt,
)


class ProviderPreviewHelperTests(unittest.TestCase):
    def test_empty_state_is_safe_and_non_writing(self):
        view = build_provider_preview_view_data(None)

        self.assertTrue(view.is_empty)
        self.assertEqual(view.empty_state_message, EMPTY_PROVIDER_PREVIEW_MESSAGE)
        self.assertEqual(view.provider_rows, ())
        self.assertEqual(self.row_value(view.safety_rows, "Will write to Anki"), "否")
        self.assertEqual(self.row_value(view.safety_rows, "Will generate cards"), "否")
        self.assertEqual(
            self.row_value(view.safety_rows, "Will create Anki notes"), "否"
        )

    def test_secret_status_is_display_only_and_unvalidated(self):
        configured = build_provider_preview_view_data(self.preview(has_secret=True))
        missing = build_provider_preview_view_data(self.preview(has_secret=False))

        self.assertEqual(
            self.row_value(configured.safety_rows, "Credential status"),
            "已配置，未验证",
        )
        self.assertEqual(
            self.row_value(missing.safety_rows, "Credential status"),
            "未配置，未验证",
        )

    def test_consent_present_and_absent_are_clear(self):
        absent = build_provider_preview_view_data(self.preview(consented_at_iso=""))
        present = build_provider_preview_view_data(
            self.preview(consented_at_iso="2026-06-30T09:00:00+08:00")
        )

        self.assertEqual(
            self.row_value(absent.safety_rows, "Consent status"), "未确认"
        )
        self.assertEqual(
            self.row_value(present.safety_rows, "Consent status"), "已确认"
        )

    def test_dry_run_absent_and_present_are_rendered(self):
        absent = build_provider_preview_view_data(self.preview())
        present = build_provider_preview_view_data(
            self.preview(
                consented_at_iso="2026-06-30T09:00:00+08:00",
                dry_run_preview=self.request_preview(),
            )
        )

        self.assertEqual(
            self.row_value(absent.dry_run_rows, "Dry-run request"), "尚未准备"
        )
        self.assertEqual(
            self.row_value(present.dry_run_rows, "Source title"), "监督学习"
        )
        self.assertEqual(present.source_excerpt_preview, "监督学习使用带标签的数据。")

    def test_safe_error_uses_only_provider_error_display_fields(self):
        error = create_provider_error_display(
            ProviderErrorKind.NETWORK_ERROR,
            "Provider One",
        )
        view = build_provider_preview_view_data(self.preview(error_display=error))

        self.assertEqual(
            self.row_value(view.error_rows, "Error type"), "network_error"
        )
        self.assertEqual(
            self.row_value(view.error_rows, "Diagnostic code"),
            "provider_error.network_error",
        )

    def test_excerpt_is_defensively_truncated(self):
        source = "A" * MAX_PROVIDER_EXCERPT_DISPLAY_CHARS + "FULL_SOURCE_SENTINEL"

        rendered = truncate_provider_preview_excerpt(source)

        self.assertLessEqual(len(rendered), MAX_PROVIDER_EXCERPT_DISPLAY_CHARS)
        self.assertTrue(rendered.endswith("..."))
        self.assertNotIn("FULL_SOURCE_SENTINEL", rendered)

    def test_no_write_flags_always_render_false(self):
        view = build_provider_preview_view_data(self.preview())

        self.assertEqual(
            self.row_value(view.safety_rows, "Target stage"),
            "knowledge_point_extraction",
        )
        for label in (
            "Will write to Anki",
            "Will generate cards",
            "Will create Anki notes",
        ):
            self.assertEqual(self.row_value(view.safety_rows, label), "否")

    def test_safe_output_and_repr_omit_excerpt_and_sensitive_values(self):
        view = build_provider_preview_view_data(
            self.preview(
                consented_at_iso="2026-06-30T09:00:00+08:00",
                dry_run_preview=self.request_preview(),
            )
        )

        rendered = (
            repr(view) + json.dumps(view.to_safe_dict(), ensure_ascii=False)
        ).lower()
        for forbidden in (
            "test-api-key",
            "secret_ref",
            "credential_kind",
            "raw consent",
            "raw exception",
            "监督学习使用带标签的数据。",
        ):
            self.assertNotIn(forbidden.lower(), rendered)

    def test_invalid_preview_type_is_rejected(self):
        with self.assertRaises(ValueError):
            build_provider_preview_view_data(object())

    def test_helper_has_strict_dependency_boundary(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "ui"
            / "provider_preview_helpers.py"
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
        called_names = {
            node.func.id
            if isinstance(node.func, ast.Name)
            else node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Name, ast.Attribute))
        }

        for forbidden_import in (
            "aqt",
            "PyQt",
            "config",
            "writer",
            "transport",
            "provider_factory",
            "executor",
            "secret_store",
            "orchestrator",
            "review_bridge",
            "socket",
            "urllib",
            "requests",
        ):
            self.assertFalse(
                any(forbidden_import in module for module in imported_modules),
                forbidden_import,
            )
        for forbidden_call in (
            "asdict",
            "load_secret",
            "reveal",
            "extract",
            "post_json",
            "urlopen",
            "write",
        ):
            self.assertNotIn(forbidden_call, called_names)

    @staticmethod
    def row_value(rows, label):
        return next(row.value for row in rows if row.label == label)

    @staticmethod
    def request_preview():
        excerpt = "监督学习使用带标签的数据。"
        return ProviderDryRunRequestPreview(
            profile_id="profile-1",
            source_chunk_id="chunk-1",
            source_title="监督学习",
            source_excerpt_preview=excerpt,
            source_excerpt_preview_length=len(excerpt),
        )

    @staticmethod
    def preview(**overrides):
        values = {
            "profile_id": "profile-1",
            "provider_id": "provider-1",
            "provider_name": "Provider One",
            "model_name": "model-1",
            "base_url": "https://api.example.com/v1",
            "sends_user_content": True,
            "requires_explicit_consent": True,
            "has_secret": False,
            "consented_at_iso": "",
            "privacy_notice": "Material is sent to Provider One.",
        }
        values.update(overrides)
        return ReadOnlyProviderPreview(**values)


if __name__ == "__main__":
    unittest.main()
