import ast
import copy
import json
import socket
import unittest
import urllib.request
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.provider_consent import (
    ProviderConsentRecord,
    ProviderSelection,
)
from ankiforge_ai.pipeline.provider_dry_run_request import ProviderDryRunRequest
from ankiforge_ai.pipeline.provider_error_display import (
    ProviderErrorKind,
    create_provider_error_display,
)
from ankiforge_ai.pipeline.provider_preview import (
    ProviderDryRunRequestPreview,
    ReadOnlyProviderPreview,
    build_read_only_provider_preview,
)
from ankiforge_ai.pipeline.provider_secret_store import ProviderSecretRef
from ankiforge_ai.pipeline.user_provider_config import UserProviderProfile


class ProviderPreviewTests(unittest.TestCase):
    def test_matching_profile_and_selection_create_preview(self):
        preview = self.preview(has_secret=True)

        self.assertEqual(preview.profile_id, "profile-1")
        self.assertEqual(preview.provider_id, "provider-1")
        self.assertEqual(preview.provider_name, "Provider One")
        self.assertEqual(preview.model_name, "model-1")
        self.assertEqual(preview.base_url, "https://api.example.com/v1")

    def test_each_profile_selection_identity_mismatch_is_rejected(self):
        mismatches = {
            "profile_id": "different-profile",
            "provider_id": "different-provider",
            "provider_name": "Different Provider",
            "model_name": "different-model",
            "base_url": "https://other.example.com/v1",
        }
        profile = self.profile()
        for field_name, value in mismatches.items():
            with self.subTest(field_name=field_name):
                with self.assertRaises(ValueError):
                    build_read_only_provider_preview(
                        profile,
                        self.selection(**{field_name: value}),
                        False,
                    )

    def test_has_secret_accepts_only_strict_bool(self):
        for value in (True, False):
            with self.subTest(valid=value):
                self.assertIs(self.preview(has_secret=value).has_secret, value)
        for value in (1, 0, "true", None):
            with self.subTest(invalid=value):
                with self.assertRaises(ValueError):
                    self.preview(has_secret=value)

    def test_secret_status_is_only_a_boolean_projection(self):
        data = self.preview(has_secret=True).to_safe_dict()

        self.assertIs(data["has_secret"], True)
        rendered = json.dumps(data, ensure_ascii=False).lower()
        self.assertNotIn("test-api-key", rendered)
        self.assertNotIn("authorization", rendered)
        self.assertNotIn("credential_kind", rendered)

    def test_consent_absent_and_present_states(self):
        without_consent = self.preview(has_secret=False)
        consent = self.consent(self.selection())
        with_consent = self.preview(has_secret=False, consent=consent)

        self.assertFalse(without_consent.has_consent)
        self.assertEqual(without_consent.consented_at_iso, "")
        self.assertTrue(with_consent.has_consent)
        self.assertEqual(
            with_consent.consented_at_iso,
            "2026-06-29T12:00:00+00:00",
        )

    def test_consent_selection_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            self.preview(
                has_secret=True,
                consent=self.consent(
                    self.selection(provider_id="different-provider")
                ),
            )

    def test_request_requires_consent(self):
        selection = self.selection()
        consent = self.consent(selection)
        request = self.request(selection, consent)

        with self.assertRaises(ValueError):
            self.preview(
                has_secret=True,
                dry_run_request=request,
            )

    def test_local_endpoints_still_require_consent(self):
        for base_url in ("http://localhost:8000/v1", "https://127.0.0.1/v1"):
            with self.subTest(base_url=base_url):
                profile = self.profile(base_url=base_url)
                selection = self.selection(base_url=base_url)
                preview = build_read_only_provider_preview(
                    profile,
                    selection,
                    True,
                )
                self.assertFalse(preview.has_consent)
                self.assertTrue(preview.requires_explicit_consent)
                with self.assertRaises(ValueError):
                    build_read_only_provider_preview(
                        profile,
                        selection,
                        True,
                        dry_run_request=self.request(
                            selection,
                            self.consent(selection),
                        ),
                    )

    def test_matching_request_creates_safe_request_preview(self):
        selection = self.selection()
        consent = self.consent(selection)
        request = self.request(selection, consent)

        preview = self.preview(
            has_secret=True,
            consent=consent,
            dry_run_request=request,
        )
        request_preview = preview.dry_run_preview

        self.assertEqual(request_preview.source_chunk_id, "chunk-1")
        self.assertEqual(request_preview.source_title, "监督学习")
        self.assertEqual(
            request_preview.source_excerpt_preview_length,
            len("监督学习使用带标签的数据。"),
        )
        self.assertEqual(
            request_preview.target_stage,
            "knowledge_point_extraction",
        )

    def test_request_selection_mismatch_is_rejected(self):
        selection = self.selection()
        consent = self.consent(selection)
        other_selection = self.selection(provider_id="different-provider")
        other_consent = self.consent(other_selection)

        with self.assertRaises(ValueError):
            self.preview(
                has_secret=True,
                consent=consent,
                dry_run_request=self.request(other_selection, other_consent),
            )

    def test_request_consent_mismatch_is_rejected(self):
        selection = self.selection()
        consent = self.consent(selection)
        other_consent = self.consent(
            selection,
            consent_text="A different explicit consent statement.",
        )

        with self.assertRaises(ValueError):
            self.preview(
                has_secret=True,
                consent=consent,
                dry_run_request=self.request(selection, other_consent),
            )

    def test_safe_dict_omits_excerpt_but_user_visible_dict_includes_it(self):
        selection = self.selection()
        consent = self.consent(selection)
        request = self.request(selection, consent)
        preview = self.preview(
            has_secret=True,
            consent=consent,
            dry_run_request=request,
        )

        safe_data = preview.to_safe_dict()
        visible_data = preview.to_user_visible_dict()

        self.assertNotIn(
            "source_excerpt_preview",
            safe_data["dry_run_preview"],
        )
        self.assertEqual(
            visible_data["dry_run_preview"]["source_excerpt_preview"],
            request.source_excerpt_preview,
        )

    def test_preview_dtos_store_no_domain_or_secret_objects(self):
        main_fields = {field.name for field in fields(ReadOnlyProviderPreview)}
        request_fields = {
            field.name for field in fields(ProviderDryRunRequestPreview)
        }

        for forbidden in (
            "profile",
            "selection",
            "consent",
            "dry_run_request",
            "secret_ref",
        ):
            self.assertNotIn(forbidden, main_fields)
            self.assertNotIn(forbidden, request_fields)

    def test_repr_hides_excerpt_consent_and_credentials(self):
        selection = self.selection()
        consent = self.consent(selection)
        request = self.request(selection, consent)
        preview = self.preview(
            has_secret=True,
            consent=consent,
            dry_run_request=request,
        )
        rendered = f"{repr(preview)}\n{str(preview)}".lower()

        for forbidden in (
            request.source_excerpt_preview.lower(),
            consent.consent_text.lower(),
            "source_excerpt_preview",
            "has_secret",
            "providersecretref",
            "credential_kind",
            "test-api-key",
            "authorization",
            "bearer",
            "token",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_fixed_flags_are_read_only_and_false(self):
        request_preview = self.request_preview()
        preview = self.preview(has_secret=False)

        self.assertEqual(request_preview.target_stage, "knowledge_point_extraction")
        self.assertFalse(request_preview.will_send_full_source_text)
        self.assertFalse(request_preview.will_write_to_anki)
        self.assertFalse(request_preview.will_generate_cards)
        self.assertFalse(request_preview.will_create_anki_notes)
        self.assertEqual(preview.target_stage, "knowledge_point_extraction")
        self.assertFalse(preview.will_write_to_anki)
        self.assertFalse(preview.will_generate_cards)
        self.assertFalse(preview.will_create_anki_notes)

        with self.assertRaises(TypeError):
            self.request_preview(will_write_to_anki=True)
        with self.assertRaises(TypeError):
            self.preview(has_secret=False, will_write_to_anki=True)

    def test_safe_error_display_can_be_projected(self):
        error = create_provider_error_display(
            ProviderErrorKind.TIMEOUT,
            provider_name="Provider One",
        )
        preview = self.preview(has_secret=True, error_display=error)

        self.assertIs(preview.error_display, error)
        self.assertEqual(
            preview.to_safe_dict()["error_display"],
            error.to_safe_dict(),
        )

    def test_raw_error_objects_are_rejected(self):
        for value in (RuntimeError("raw exception"), {"raw": "response"}):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    self.preview(has_secret=False, error_display=value)

    def test_helper_does_not_modify_inputs(self):
        profile = self.profile()
        selection = self.selection()
        consent = self.consent(selection)
        request = self.request(selection, consent)
        before = copy.deepcopy((profile, selection, consent, request))

        build_read_only_provider_preview(
            profile,
            selection,
            True,
            consent,
            request,
        )

        self.assertEqual((profile, selection, consent, request), before)

    def test_preview_build_does_not_access_network(self):
        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Network access is forbidden."),
        ), patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Network access is forbidden."),
        ):
            preview = self.preview(has_secret=False)

        self.assertFalse(preview.will_write_to_anki)

    def test_module_has_strict_import_and_call_boundary(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "provider_preview.py"
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
                "provider_consent",
                "provider_dry_run_request",
                "provider_error_display",
                "user_provider_config",
            },
        )
        for forbidden_import in (
            "ProviderSecretStore",
            "ProviderSecretValue",
            "ProviderSecretRef",
            "OpenAICompatibleHTTPTransport",
        ):
            self.assertNotIn(forbidden_import, imported_names)
        for forbidden_call in (
            "asdict",
            "load_secret",
            "reveal",
            "urlopen",
            "create_connection",
            "extract",
            "post_json",
            "write",
        ):
            self.assertNotIn(forbidden_call, called_names)

    @staticmethod
    def profile(**overrides):
        values = {
            "profile_id": "profile-1",
            "provider_id": "provider-1",
            "provider_name": "Provider One",
            "model_name": "model-1",
            "base_url": "https://api.example.com/v1",
            "privacy_notice": "Material is sent to Provider One.",
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
            "base_url": "https://api.example.com/v1",
        }
        values.update(overrides)
        return ProviderSelection(**values)

    @staticmethod
    def consent(selection, **overrides):
        values = {
            "selection": selection,
            "consent_text": "I agree to send this material.",
            "privacy_notice": "Material is sent to Provider One.",
            "consented_at": datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc),
        }
        values.update(overrides)
        return ProviderConsentRecord(**values)

    @staticmethod
    def request(selection, consent):
        return ProviderDryRunRequest(
            selection=selection,
            consent=consent,
            secret_ref=ProviderSecretRef(profile_id=selection.profile_id),
            source_chunk_id="chunk-1",
            source_title="监督学习",
            source_excerpt_preview="监督学习使用带标签的数据。",
        )

    @staticmethod
    def request_preview(**overrides):
        values = {
            "profile_id": "profile-1",
            "source_chunk_id": "chunk-1",
            "source_title": "监督学习",
            "source_excerpt_preview": "监督学习使用带标签的数据。",
            "source_excerpt_preview_length": len("监督学习使用带标签的数据。"),
        }
        values.update(overrides)
        return ProviderDryRunRequestPreview(**values)

    @classmethod
    def preview(cls, has_secret, **overrides):
        values = {
            "profile": cls.profile(),
            "selection": cls.selection(),
            "has_secret": has_secret,
        }
        values.update(overrides)
        return build_read_only_provider_preview(**values)


if __name__ == "__main__":
    unittest.main()
