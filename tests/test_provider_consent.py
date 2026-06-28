import ast
import copy
import json
import socket
import unittest
import urllib.request
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.provider_consent import (
    ProviderConsentRecord,
    ProviderSelection,
    create_provider_consent_record,
    create_provider_selection_from_profile,
)
from ankiforge_ai.pipeline.user_provider_config import UserProviderProfile


class SensitiveObject:
    def __repr__(self):
        return "test-api-key PRIVATE SOURCE Authorization"

    def __str__(self):
        return "test-api-key PRIVATE SOURCE Authorization"


class ProviderConsentTests(unittest.TestCase):
    def test_selection_fields_and_safe_dict_are_correct(self):
        selection = self.selection()

        self.assertEqual(
            [field.name for field in fields(selection)],
            ["profile_id", "provider_id", "provider_name", "model_name", "base_url"],
        )
        self.assertEqual(
            selection.to_safe_dict(),
            {
                "profile_id": "profile-1",
                "provider_id": "provider-1",
                "provider_name": "Provider One",
                "model_name": "model-1",
                "base_url": "https://api.example.com/v1",
                "sends_user_content": True,
                "requires_explicit_consent": True,
            },
        )

    def test_selection_is_frozen(self):
        selection = self.selection()

        with self.assertRaises(FrozenInstanceError):
            selection.model_name = "changed"

    def test_selection_requires_non_empty_fields_without_echoing_input(self):
        for field_name in (
            "profile_id",
            "provider_id",
            "provider_name",
            "model_name",
        ):
            for value in ("", " ", "\n\t", None, SensitiveObject()):
                with self.subTest(field_name=field_name, value=type(value).__name__):
                    with self.assertRaises(ValueError) as context:
                        self.selection(**{field_name: value})
                    self.assertNotIn("test-api-key", str(context.exception))
                    self.assertNotIn("PRIVATE SOURCE", str(context.exception))

    def test_selection_validates_base_url(self):
        valid_urls = (
            "http://api.example.com/v1",
            "https://api.example.com/v1",
            "http://localhost:8000/v1",
            "https://127.0.0.1/v1",
        )
        invalid_urls = (
            "",
            " ",
            "api.example.com/v1",
            "/relative/path",
            "file:///tmp/provider",
            "data://text/plain,value",
            "https://",
            "http:///v1",
            "https://user@example.com/v1",
            "https://user:password@example.com/v1",
        )
        for base_url in valid_urls:
            with self.subTest(valid=base_url):
                self.assertEqual(self.selection(base_url=base_url).base_url, base_url)
        for base_url in invalid_urls:
            with self.subTest(invalid=base_url):
                with self.assertRaises(ValueError):
                    self.selection(base_url=base_url)

    def test_local_endpoints_do_not_bypass_consent(self):
        for base_url in ("http://localhost:8000/v1", "https://127.0.0.1/v1"):
            with self.subTest(base_url=base_url):
                selection = self.selection(base_url=base_url)
                self.assertTrue(selection.sends_user_content)
                self.assertTrue(selection.requires_explicit_consent)

    def test_selection_flags_are_properties_and_cannot_be_forged(self):
        selection = self.selection()
        field_names = {field.name for field in fields(selection)}

        self.assertNotIn("sends_user_content", field_names)
        self.assertNotIn("requires_explicit_consent", field_names)
        with self.assertRaises(TypeError):
            self.selection(sends_user_content=False)
        with self.assertRaises(TypeError):
            self.selection(requires_explicit_consent=False)

    def test_selection_from_profile_copies_only_safe_fields(self):
        profile = self.profile()
        before = copy.deepcopy(profile)

        selection = create_provider_selection_from_profile(profile)

        self.assertEqual(selection.profile_id, profile.profile_id)
        self.assertEqual(selection.provider_id, profile.provider_id)
        self.assertEqual(selection.provider_name, profile.provider_name)
        self.assertEqual(selection.model_name, profile.model_name)
        self.assertEqual(selection.base_url, profile.base_url)
        self.assertEqual(profile, before)

    def test_selection_safe_outputs_do_not_contain_sensitive_data(self):
        selection = create_provider_selection_from_profile(self.profile())
        rendered = "\n".join(
            (
                repr(selection),
                str(selection),
                json.dumps(selection.to_safe_dict(), ensure_ascii=False),
            )
        ).lower()

        for forbidden in (
            "test-api-key",
            "authorization",
            "bearer",
            "private source",
            "chunk text",
            "headers",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_consent_record_fields_and_flags_are_correct(self):
        selection = self.selection()
        consented_at = datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc)

        record = self.record(selection=selection, consented_at=consented_at)

        self.assertIs(record.selection, selection)
        self.assertEqual(record.consent_text, "I agree to send this material.")
        self.assertEqual(record.privacy_notice, "Material is sent to Provider One.")
        self.assertEqual(record.consented_at, consented_at)
        self.assertTrue(record.sends_user_content)
        self.assertTrue(record.requires_explicit_consent)
        self.assertTrue(record.has_explicit_consent)

    def test_consent_record_is_frozen(self):
        record = self.record()

        with self.assertRaises(FrozenInstanceError):
            record.consented_at = datetime.now(timezone.utc)

    def test_consent_flags_are_properties_and_cannot_be_forged(self):
        record = self.record()
        field_names = {field.name for field in fields(record)}

        self.assertNotIn("sends_user_content", field_names)
        self.assertNotIn("requires_explicit_consent", field_names)
        self.assertNotIn("has_explicit_consent", field_names)
        with self.assertRaises(TypeError):
            self.record(sends_user_content=False)
        with self.assertRaises(TypeError):
            self.record(requires_explicit_consent=False)
        with self.assertRaises(TypeError):
            self.record(has_explicit_consent=False)

    def test_consent_record_requires_selection(self):
        with self.assertRaises(ValueError) as context:
            self.record(selection=SensitiveObject())

        self.assertNotIn("test-api-key", str(context.exception))
        self.assertNotIn("PRIVATE SOURCE", str(context.exception))

    def test_consent_text_and_privacy_notice_are_required(self):
        for field_name in ("consent_text", "privacy_notice"):
            for value in ("", " ", "\n\t", None, SensitiveObject()):
                with self.subTest(field_name=field_name, value=type(value).__name__):
                    with self.assertRaises(ValueError) as context:
                        self.record(**{field_name: value})
                    self.assertNotIn("test-api-key", str(context.exception))
                    self.assertNotIn("PRIVATE SOURCE", str(context.exception))

    def test_naive_or_invalid_datetime_is_rejected(self):
        for consented_at in (
            datetime(2026, 6, 29, 12, 0),
            "2026-06-29T12:00:00Z",
            None,
        ):
            with self.subTest(value=type(consented_at).__name__):
                with self.assertRaises(ValueError):
                    self.record(consented_at=consented_at)

    def test_utc_and_non_utc_aware_datetimes_are_accepted(self):
        values = (
            datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc),
            datetime(
                2026,
                6,
                29,
                20,
                0,
                tzinfo=timezone(timedelta(hours=8)),
            ),
        )
        for consented_at in values:
            with self.subTest(consented_at=consented_at):
                self.assertEqual(
                    self.record(consented_at=consented_at).consented_at,
                    consented_at,
                )

    def test_consent_safe_dict_uses_nested_selection_and_iso_time(self):
        record = self.record(
            consented_at=datetime(
                2026,
                6,
                29,
                20,
                30,
                tzinfo=timezone(timedelta(hours=8)),
            )
        )

        data = record.to_safe_dict()

        self.assertEqual(data["selection"], record.selection.to_safe_dict())
        self.assertEqual(data["consented_at"], "2026-06-29T20:30:00+08:00")
        self.assertTrue(data["sends_user_content"])
        self.assertTrue(data["requires_explicit_consent"])
        self.assertTrue(data["has_explicit_consent"])

    def test_consent_safe_outputs_do_not_contain_sensitive_data(self):
        record = self.record()
        rendered = "\n".join(
            (
                repr(record),
                str(record),
                json.dumps(record.to_safe_dict(), ensure_ascii=False),
            )
        ).lower()

        for forbidden in (
            "test-api-key",
            "authorization",
            "bearer",
            "private source",
            "chunk text",
            "card text",
            "headers",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_consent_helper_requires_all_explicit_arguments(self):
        selection = self.selection()

        with self.assertRaises(TypeError):
            create_provider_consent_record(selection)
        with self.assertRaises(TypeError):
            create_provider_consent_record(
                selection,
                "I agree.",
                "Material is sent.",
            )

    def test_helpers_do_not_modify_inputs(self):
        profile = self.profile()
        profile_before = copy.deepcopy(profile)
        selection = create_provider_selection_from_profile(profile)
        selection_before = copy.deepcopy(selection)

        create_provider_consent_record(
            selection,
            "I agree to send this material.",
            "Material is sent to Provider One.",
            datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(profile, profile_before)
        self.assertEqual(selection, selection_before)

    def test_helpers_do_not_access_network(self):
        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Network access is forbidden."),
        ), patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Network access is forbidden."),
        ):
            selection = create_provider_selection_from_profile(self.profile())
            record = self.record(selection=selection)

        self.assertTrue(record.has_explicit_consent)

    def test_module_has_strict_dependency_boundary(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "provider_consent.py"
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
        allowed_imports = {
            "dataclasses",
            "datetime",
            "urllib.parse",
            "user_provider_config",
        }

        self.assertEqual(imported_modules, allowed_imports)
        for forbidden_text in (
            "ProviderSecretRef",
            "ProviderSecretValue",
            "ProviderSecretStore",
            "config.json",
            "GeneratedCard",
            "KnowledgePoint",
            "CardCandidate",
            "HumanReview",
            "WriteReady",
            "self.cards",
            "urlopen",
            "post_json",
            ".extract(",
        ):
            self.assertNotIn(forbidden_text, source)

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

    @classmethod
    def record(cls, **overrides):
        values = {
            "selection": cls.selection(),
            "consent_text": "I agree to send this material.",
            "privacy_notice": "Material is sent to Provider One.",
            "consented_at": datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc),
        }
        values.update(overrides)
        return ProviderConsentRecord(**values)


if __name__ == "__main__":
    unittest.main()
