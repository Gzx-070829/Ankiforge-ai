import ast
import json
import socket
import unittest
import urllib.request
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from unittest.mock import patch

from ankiforge_ai.pipeline.provider_secret_store import (
    ProviderSecretRef,
    ProviderSecretStore,
    ProviderSecretValue,
)


class FakeProviderSecretStore:
    """Test-only fake; this is not a production credential backend."""

    def __init__(self):
        self._values = {}

    def save_secret(self, ref, value):
        self._values[ref] = value

    def load_secret(self, ref):
        return self._values.get(ref)

    def has_secret(self, ref):
        return ref in self._values

    def delete_secret(self, ref):
        if ref not in self._values:
            return False
        del self._values[ref]
        return True


class SensitiveObject:
    def __repr__(self):
        return "test-api-key"

    def __str__(self):
        return "test-api-key"


class ProviderSecretStoreTests(unittest.TestCase):
    def test_secret_ref_is_frozen_and_contains_only_profile_id_field(self):
        ref = ProviderSecretRef(profile_id="profile-1")

        self.assertEqual([field.name for field in fields(ref)], ["profile_id"])
        with self.assertRaises(FrozenInstanceError):
            ref.profile_id = "changed"

    def test_secret_ref_requires_non_empty_profile_id(self):
        for profile_id in ("", " ", "\n\t", None, SensitiveObject()):
            with self.subTest(profile_id=type(profile_id).__name__):
                with self.assertRaises(ValueError) as context:
                    ProviderSecretRef(profile_id=profile_id)
                self.assertNotIn("test-api-key", str(context.exception))

    def test_credential_kind_is_fixed_and_cannot_be_forged(self):
        ref = ProviderSecretRef(profile_id="profile-1")

        self.assertEqual(ref.credential_kind, "api_key")
        self.assertNotIn("credential_kind", {field.name for field in fields(ref)})
        with self.assertRaises(TypeError):
            ProviderSecretRef(profile_id="profile-1", credential_kind="password")

    def test_secret_ref_to_dict_has_only_safe_reference_fields(self):
        data = ProviderSecretRef(profile_id="profile-1").to_dict()

        self.assertEqual(
            data,
            {"profile_id": "profile-1", "credential_kind": "api_key"},
        )
        self.assertEqual(set(data), {"profile_id", "credential_kind"})
        for forbidden_field in (
            "api_key",
            "secret",
            "token",
            "authorization",
            "bearer",
            "password",
            "headers",
        ):
            self.assertNotIn(forbidden_field, data)

    def test_secret_value_rejects_empty_or_non_string_values(self):
        for value in ("", " ", "\n\t", None, SensitiveObject()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError) as context:
                    ProviderSecretValue(value)
                self.assertNotIn("test-api-key", str(context.exception))

    def test_secret_value_has_no_instance_dict(self):
        value = ProviderSecretValue("test-api-key")

        self.assertFalse(hasattr(value, "__dict__"))

    def test_secret_value_repr_and_str_are_always_redacted(self):
        value = ProviderSecretValue("test-api-key")

        self.assertEqual(repr(value), "<redacted>")
        self.assertEqual(str(value), "<redacted>")
        self.assertNotIn("test-api-key", repr(value))
        self.assertNotIn("test-api-key", str(value))

    def test_secret_value_is_not_directly_json_serializable(self):
        value = ProviderSecretValue("test-api-key")

        with self.assertRaises(TypeError) as context:
            json.dumps(value)
        self.assertNotIn("test-api-key", str(context.exception))

    def test_reveal_explicitly_returns_original_value(self):
        value = ProviderSecretValue("test-api-key")

        self.assertEqual(value.reveal(), "test-api-key")

    def test_test_fake_satisfies_runtime_protocol(self):
        self.assertIsInstance(FakeProviderSecretStore(), ProviderSecretStore)

    def test_test_fake_save_load_has_and_delete_semantics(self):
        store = FakeProviderSecretStore()
        ref = ProviderSecretRef(profile_id="profile-1")
        value = ProviderSecretValue("test-api-key")

        self.assertFalse(store.has_secret(ref))
        self.assertIsNone(store.load_secret(ref))
        store.save_secret(ref, value)
        self.assertTrue(store.has_secret(ref))
        self.assertIs(store.load_secret(ref), value)
        self.assertTrue(store.delete_secret(ref))
        self.assertFalse(store.has_secret(ref))
        self.assertIsNone(store.load_secret(ref))

    def test_deleting_missing_secret_returns_false(self):
        store = FakeProviderSecretStore()
        ref = ProviderSecretRef(profile_id="missing-profile")

        self.assertFalse(store.delete_secret(ref))

    def test_contract_usage_does_not_access_network(self):
        store = FakeProviderSecretStore()
        ref = ProviderSecretRef(profile_id="profile-1")
        value = ProviderSecretValue("test-api-key")

        with patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("Network access is forbidden."),
        ), patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("Network access is forbidden."),
        ):
            store.save_secret(ref, value)
            loaded = store.load_secret(ref)

        self.assertIs(loaded, value)

    def test_production_module_has_strict_dependency_boundary(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "provider_secret_store.py"
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
        forbidden_imports = (
            "aqt",
            "anki",
            "PyQt",
            "PySide",
            "writer",
            "orchestrator",
            "review",
            "provider_factory",
            "transport",
            "requests",
            "socket",
            "http.client",
            "urllib.request",
            "keyring",
            "os",
            "pathlib",
            "config",
        )

        self.assertFalse(
            any(
                module.startswith(prefix)
                for module in imported_modules
                for prefix in forbidden_imports
            )
        )
        for forbidden_text in (
            "config.json",
            "GeneratedCard",
            "KnowledgePoint",
            "CardCandidate",
            "HumanReview",
            "self.cards",
            "urlopen",
            "post_json",
            ".extract(",
        ):
            self.assertNotIn(forbidden_text, source)

    def test_production_module_has_no_store_implementation(self):
        source_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "provider_secret_store.py"
        )
        source = source_path.read_text(encoding="utf-8")

        self.assertNotIn("InMemoryProviderSecretStore", source)
        self.assertNotIn("FakeProviderSecretStore", source)


if __name__ == "__main__":
    unittest.main()
