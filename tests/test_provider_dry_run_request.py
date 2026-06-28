import ast
import copy
import inspect
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
from ankiforge_ai.pipeline.provider_dry_run_request import (
    MAX_SOURCE_EXCERPT_PREVIEW_CHARS,
    ProviderDryRunRequest,
    create_provider_dry_run_request,
)
from ankiforge_ai.pipeline.provider_secret_store import (
    ProviderSecretRef,
    ProviderSecretValue,
)


_UNSET = object()


class SensitiveObject:
    def __repr__(self):
        return "test-api-key PRIVATE SOURCE TITLE"

    def __str__(self):
        return "test-api-key PRIVATE SOURCE TITLE"


class NonSendingSelection(ProviderSelection):
    @property
    def sends_user_content(self):
        return False


class ConsentOptionalSelection(ProviderSelection):
    @property
    def requires_explicit_consent(self):
        return False


class NonSendingConsent(ProviderConsentRecord):
    @property
    def sends_user_content(self):
        return False


class ConsentOptionalRecord(ProviderConsentRecord):
    @property
    def requires_explicit_consent(self):
        return False


class NonAffirmativeConsent(ProviderConsentRecord):
    @property
    def has_explicit_consent(self):
        return False


class ProviderDryRunRequestTests(unittest.TestCase):
    def test_request_fields_are_correct(self):
        request = self.request()

        self.assertEqual(
            [field.name for field in fields(request)],
            [
                "selection",
                "consent",
                "secret_ref",
                "source_chunk_id",
                "source_title",
                "source_excerpt_preview",
            ],
        )
        self.assertEqual(request.source_chunk_id, "chunk-1")
        self.assertEqual(request.source_title, "监督学习")
        self.assertEqual(request.source_excerpt_preview, "监督学习使用带标签的数据。")

    def test_request_is_frozen(self):
        request = self.request()

        with self.assertRaises(FrozenInstanceError):
            request.source_title = "changed"

    def test_matching_selection_consent_and_secret_ref_are_accepted(self):
        selection = self.selection()
        consent = self.consent(selection)
        secret_ref = ProviderSecretRef(profile_id=selection.profile_id)

        request = self.request(
            selection=selection,
            consent=consent,
            secret_ref=secret_ref,
        )

        self.assertIs(request.selection, selection)
        self.assertIs(request.consent, consent)
        self.assertIs(request.secret_ref, secret_ref)

    def test_required_gate_objects_must_have_correct_types(self):
        cases = (
            ("selection", None),
            ("selection", SensitiveObject()),
            ("consent", None),
            ("consent", SensitiveObject()),
            ("secret_ref", None),
            ("secret_ref", SensitiveObject()),
        )
        for field_name, value in cases:
            with self.subTest(field_name=field_name, value=type(value).__name__):
                with self.assertRaises(ValueError) as context:
                    self.request(**{field_name: value})
                self.assert_safe_error(context.exception)

    def test_provider_secret_value_is_rejected_as_secret_ref(self):
        value = ProviderSecretValue("test-api-key")

        with self.assertRaises(ValueError) as context:
            self.request(secret_ref=value)

        self.assert_safe_error(context.exception)

    def test_each_selection_identity_mismatch_is_rejected(self):
        mismatches = {
            "profile_id": "different-profile",
            "provider_id": "different-provider",
            "provider_name": "Different Provider",
            "model_name": "different-model",
            "base_url": "https://other.example.com/v1",
        }
        request_selection = self.selection()
        for field_name, value in mismatches.items():
            with self.subTest(field_name=field_name):
                consent_selection = self.selection(**{field_name: value})
                with self.assertRaises(ValueError) as context:
                    self.request(
                        selection=request_selection,
                        consent=self.consent(consent_selection),
                    )
                self.assert_safe_error(context.exception)

    def test_secret_ref_profile_must_match_selection(self):
        with self.assertRaises(ValueError) as context:
            self.request(secret_ref=ProviderSecretRef(profile_id="other-profile"))

        self.assert_safe_error(context.exception)

    def test_selection_safety_flags_are_enforced(self):
        for selection_type in (NonSendingSelection, ConsentOptionalSelection):
            with self.subTest(selection_type=selection_type.__name__):
                selection = self.selection(selection_type=selection_type)
                with self.assertRaises(ValueError) as context:
                    self.request(
                        selection=selection,
                        consent=self.consent(selection),
                    )
                self.assert_safe_error(context.exception)

    def test_consent_safety_flags_are_enforced(self):
        for consent_type in (
            NonSendingConsent,
            ConsentOptionalRecord,
            NonAffirmativeConsent,
        ):
            with self.subTest(consent_type=consent_type.__name__):
                selection = self.selection()
                with self.assertRaises(ValueError) as context:
                    self.request(
                        selection=selection,
                        consent=self.consent(selection, consent_type=consent_type),
                    )
                self.assert_safe_error(context.exception)

    def test_local_endpoints_still_require_explicit_consent(self):
        for base_url in ("http://localhost:8000/v1", "https://127.0.0.1/v1"):
            with self.subTest(base_url=base_url):
                selection = self.selection(base_url=base_url)
                request = self.request(
                    selection=selection,
                    consent=self.consent(selection),
                )
                self.assertTrue(request.selection.sends_user_content)
                self.assertTrue(request.selection.requires_explicit_consent)
                self.assertTrue(request.consent.has_explicit_consent)

    def test_preview_length_boundary(self):
        accepted = "中" * MAX_SOURCE_EXCERPT_PREVIEW_CHARS
        rejected = "中" * (MAX_SOURCE_EXCERPT_PREVIEW_CHARS + 1)

        self.assertEqual(self.request(source_excerpt_preview=accepted).source_excerpt_preview, accepted)
        with self.assertRaises(ValueError) as context:
            self.request(source_excerpt_preview=rejected)
        self.assertNotIn(rejected, str(context.exception))

    def test_source_fields_are_required_without_echoing_input(self):
        cases = (
            ("source_chunk_id", ""),
            ("source_chunk_id", " "),
            ("source_title", ""),
            ("source_title", "PRIVATE SOURCE TITLE test-api-key"),
            ("source_excerpt_preview", ""),
            ("source_excerpt_preview", " "),
            ("source_excerpt_preview", SensitiveObject()),
        )
        for field_name, value in cases:
            if field_name == "source_title" and value:
                continue
            with self.subTest(field_name=field_name, value=type(value).__name__):
                with self.assertRaises(ValueError) as context:
                    self.request(**{field_name: value})
                self.assert_safe_error(context.exception)

    def test_errors_do_not_echo_title_preview_or_key(self):
        title = "PRIVATE SOURCE TITLE test-api-key"
        preview = "PRIVATE PREVIEW Authorization " * 30

        with self.assertRaises(ValueError) as context:
            self.request(source_title=title, source_excerpt_preview=preview)

        message = str(context.exception)
        self.assertNotIn(title, message)
        self.assertNotIn(preview, message)
        self.assertNotIn("test-api-key", message)
        self.assertNotIn("Authorization", message)

    def test_repr_and_str_hide_preview_and_secret_ref(self):
        preview = "PRIVATE PREVIEW"
        request = self.request(source_excerpt_preview=preview)
        rendered = f"{repr(request)}\n{str(request)}"

        self.assertNotIn(preview, rendered)
        self.assertNotIn("secret_ref=", rendered)
        self.assertNotIn("ProviderSecretRef", rendered)
        self.assertNotIn("test-api-key", rendered)

    def test_safe_dict_contains_only_allowed_request_data(self):
        request = self.request()
        data = request.to_safe_dict()

        self.assertEqual(data["selection"], request.selection.to_safe_dict())
        self.assertEqual(data["consent"], request.consent.to_safe_dict())
        self.assertEqual(data["source_chunk_id"], "chunk-1")
        self.assertEqual(data["source_title"], "监督学习")
        self.assertEqual(data["source_excerpt_preview"], "监督学习使用带标签的数据。")
        self.assertEqual(data["target_stage"], "knowledge_point_extraction")
        self.assertNotIn("secret_ref", data)

        rendered = json.dumps(data, ensure_ascii=False).lower()
        for forbidden in (
            "test-api-key",
            "full_source_text",
            "chunk_text",
            "authorization",
            "bearer",
            "headers",
            "card text",
            "generatedcard",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_helper_requires_every_argument_and_has_no_defaults(self):
        signature = inspect.signature(create_provider_dry_run_request)

        self.assertTrue(
            all(
                parameter.default is inspect.Parameter.empty
                for parameter in signature.parameters.values()
            )
        )
        with self.assertRaises(TypeError):
            create_provider_dry_run_request(self.selection())

    def test_helper_does_not_modify_inputs(self):
        selection = self.selection()
        consent = self.consent(selection)
        secret_ref = ProviderSecretRef(profile_id=selection.profile_id)
        before = copy.deepcopy((selection, consent, secret_ref))

        create_provider_dry_run_request(
            selection,
            consent,
            secret_ref,
            "chunk-1",
            "监督学习",
            "监督学习使用带标签的数据。",
        )

        self.assertEqual((selection, consent, secret_ref), before)

    def test_helper_does_not_access_network(self):
        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Network access is forbidden."),
        ), patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Network access is forbidden."),
        ):
            request = self.request()

        self.assertEqual(request.to_safe_dict()["target_stage"], "knowledge_point_extraction")

    def test_module_has_strict_dependency_and_execution_boundary(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "provider_dry_run_request.py"
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
        function_names = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        }

        self.assertEqual(
            imported_modules,
            {"dataclasses", "provider_consent", "provider_secret_store"},
        )
        self.assertNotIn("ProviderSecretValue", imported_names)
        self.assertNotIn("ProviderSecretStore", imported_names)
        for forbidden_function in (
            "execute",
            "send",
            "run",
            "call_provider",
            "resolve_secret",
            "create_provider",
            "extract",
        ):
            self.assertNotIn(forbidden_function, function_names)
        for forbidden_text in (
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
    def selection(selection_type=ProviderSelection, **overrides):
        values = {
            "profile_id": "profile-1",
            "provider_id": "provider-1",
            "provider_name": "Provider One",
            "model_name": "model-1",
            "base_url": "https://api.example.com/v1",
        }
        values.update(overrides)
        return selection_type(**values)

    @staticmethod
    def consent(selection, consent_type=ProviderConsentRecord):
        return consent_type(
            selection=selection,
            consent_text="I agree to send this material.",
            privacy_notice="Material is sent to Provider One.",
            consented_at=datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc),
        )

    @classmethod
    def request(cls, **overrides):
        selection = overrides.pop("selection", _UNSET)
        if selection is _UNSET:
            selection = cls.selection()
        consent = overrides.pop("consent", _UNSET)
        if consent is _UNSET:
            consent = cls.consent(selection)
        default_profile_id = (
            selection.profile_id
            if isinstance(selection, ProviderSelection)
            else "profile-1"
        )
        values = {
            "selection": selection,
            "consent": consent,
            "secret_ref": ProviderSecretRef(profile_id=default_profile_id),
            "source_chunk_id": "chunk-1",
            "source_title": "监督学习",
            "source_excerpt_preview": "监督学习使用带标签的数据。",
        }
        values.update(overrides)
        return ProviderDryRunRequest(**values)

    def assert_safe_error(self, error):
        message = str(error)
        for forbidden in (
            "test-api-key",
            "PRIVATE SOURCE TITLE",
            "PRIVATE PREVIEW",
            "Authorization",
        ):
            self.assertNotIn(forbidden, message)


if __name__ == "__main__":
    unittest.main()
