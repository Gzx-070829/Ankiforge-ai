import ast
import inspect
import json
import unittest
from dataclasses import fields, replace
from pathlib import Path

from ankiforge_ai.ui.provider_profile_draft_helpers import (
    PROVIDER_PROFILE_DRAFT_TARGET_STAGE,
    ProviderProfileDraftDisplayRow,
    ProviderProfileDraftInput,
    ProviderProfileDraftValidationError,
    build_provider_profile_draft_view_data,
)
from ankiforge_ai.ui.provider_profile_draft_preview_adapter import (
    INVALID_DRAFT_SUMMARY_MESSAGE,
    VALID_DRAFT_SUMMARY_MESSAGE,
    ProviderProfileDraftReadOnlyPreview,
    build_provider_profile_draft_read_only_preview,
)


class ProviderProfileDraftPreviewAdapterTests(unittest.TestCase):
    def test_adapter_only_accepts_processed_draft_view_data(self):
        for value in (None, object(), self.draft()):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(ValueError):
                    build_provider_profile_draft_read_only_preview(value)

    def test_empty_draft_has_no_provider_summary(self):
        preview = self.preview_for(None)

        self.assertTrue(preview.is_empty)
        self.assertFalse(preview.is_valid)
        self.assertEqual(preview.provider_rows, ())
        self.assertEqual(preview.validation_errors, ())
        self.assertEqual(preview.summary_message, "尚未填写本地 provider 草稿")
        self.assert_fixed_status_rows(preview)

    def test_invalid_draft_has_errors_but_no_provider_summary(self):
        preview = self.preview_for(self.draft(base_url="ftp://example.com"))

        self.assertFalse(preview.is_empty)
        self.assertFalse(preview.is_valid)
        self.assertEqual(preview.provider_rows, ())
        self.assertEqual(preview.summary_message, INVALID_DRAFT_SUMMARY_MESSAGE)
        self.assertEqual(
            {error.field_name for error in preview.validation_errors},
            {"base_url"},
        )
        self.assert_fixed_status_rows(preview)

    def test_valid_draft_builds_read_only_style_groups(self):
        preview = self.preview_for(self.draft())

        self.assertFalse(preview.is_empty)
        self.assertTrue(preview.is_valid)
        self.assertEqual(preview.summary_message, VALID_DRAFT_SUMMARY_MESSAGE)
        self.assertEqual(
            tuple(row.label for row in preview.provider_rows),
            (
                "Provider",
                "Model",
                "Base URL",
                "Privacy notice",
                "Target stage",
            ),
        )
        self.assertEqual(
            self.row_value(preview.provider_rows, "Target stage"),
            PROVIDER_PROFILE_DRAFT_TARGET_STAGE,
        )
        self.assert_fixed_status_rows(preview)

    def test_statuses_are_fixed_and_do_not_claim_runtime_readiness(self):
        preview = self.preview_for(self.draft())

        expected = {
            "Preview source": "仅本地草稿",
            "Activation status": "未激活",
            "Provider verification": "未执行",
            "Consent status": "不适用（未激活）",
            "Will save settings": "否",
            "Will send content": "否",
            "Will call provider": "否",
            "Will generate cards": "否",
            "Will write to Anki": "否",
        }
        self.assertEqual(self.row_mapping(preview.status_rows), expected)

    def test_forged_target_stage_is_rejected(self):
        view_data = build_provider_profile_draft_view_data(self.draft())
        forged_rows = tuple(
            ProviderProfileDraftDisplayRow(
                label=row.label,
                value=("card_generation" if row.label == "Target stage" else row.value),
            )
            for row in view_data.profile_rows
        )

        with self.assertRaises(ValueError):
            build_provider_profile_draft_read_only_preview(
                replace(view_data, profile_rows=forged_rows)
            )

    def test_forged_or_inconsistent_safety_state_is_rejected(self):
        valid = build_provider_profile_draft_view_data(self.draft())
        forged_safety = tuple(
            ProviderProfileDraftDisplayRow(
                label=row.label,
                value=("是" if row.label == "Will call provider" else row.value),
            )
            for row in valid.safety_rows
        )
        inconsistent_valid = replace(
            valid,
            validation_errors=(
                ProviderProfileDraftValidationError(
                    field_name="base_url",
                    message="Base URL 格式无效。",
                ),
            ),
        )

        for view_data in (
            replace(valid, safety_rows=forged_safety),
            inconsistent_valid,
        ):
            with self.subTest(view_data=view_data.to_safe_dict()):
                with self.assertRaises(ValueError):
                    build_provider_profile_draft_read_only_preview(view_data)

    def test_public_adapter_shape_has_no_sensitive_or_runtime_fields(self):
        forbidden_markers = (
            "key",
            "secret",
            "token",
            "credential",
            "has_secret",
            "runtime_config",
        )
        field_names = {
            field.name.lower() for field in fields(ProviderProfileDraftReadOnlyPreview)
        }
        parameter_names = {
            name.lower()
            for name in inspect.signature(
                build_provider_profile_draft_read_only_preview
            ).parameters
        }

        for public_name in field_names | parameter_names:
            with self.subTest(public_name=public_name):
                self.assertFalse(
                    any(marker in public_name for marker in forbidden_markers)
                )

    def test_repr_and_safe_dict_do_not_copy_complete_user_input(self):
        values = {
            "provider": "sk-" + "A" * 24,
            "model": "Bearer local-draft-model",
            "base_url": "https://private-preview.example.com/v1",
            "privacy_notice": "secret token local draft notice",
        }
        preview = self.preview_for(self.draft(**values))
        rendered = (
            repr(preview)
            + json.dumps(preview.to_safe_dict(), ensure_ascii=False)
        ).lower()

        for forbidden in (
            *values.values(),
            "api_key",
            "has_secret",
            "credential",
            "secret",
            "token",
            "bearer",
            "sk-",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden.lower(), rendered)

    def test_adapter_has_strict_dependency_and_call_boundary(self):
        source_path = self.repo_root() / "ankiforge_ai" / "ui" / (
            "provider_profile_draft_preview_adapter.py"
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
        called_names = {
            node.func.id
            if isinstance(node.func, ast.Name)
            else node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Name, ast.Attribute))
        }

        for forbidden_import in (
            "pipeline.provider_preview",
            "provider_preview_helpers",
            "user_provider_config",
            "config_loader",
            "provider_secret_store",
            "provider_factory",
            "transport",
            "executor",
            "requests",
            "httpx",
            "aiohttp",
            "urllib",
            "socket",
            "writer",
            "aqt",
            "anki",
            "PyQt",
            "PySide",
        ):
            self.assertFalse(
                any(forbidden_import in module for module in imported_modules),
                forbidden_import,
            )
        for forbidden_name in (
            "ReadOnlyProviderPreview",
            "build_read_only_provider_preview",
            "build_provider_preview_view_data",
            "create_openai_compatible_config_from_user_profile",
            "load_secret",
            "create_provider",
            "post_json",
            "urlopen",
            "write",
        ):
            self.assertNotIn(forbidden_name, imported_names)
            self.assertNotIn(forbidden_name, called_names)

    def test_dialog_update_path_uses_only_pr2_helper_and_pr3_adapter(self):
        source_path = self.repo_root() / "ankiforge_ai" / "ui" / (
            "provider_profile_draft_dialog.py"
        )
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        dialog_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "ProviderProfileDraftDialog"
        )
        adapter_method = next(
            node
            for node in dialog_class.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_adapt_draft_for_preview"
        )
        method_source = ast.get_source_segment(source, adapter_method) or ""

        self.assertIn("build_provider_profile_draft_view_data", method_source)
        self.assertIn(
            "build_provider_profile_draft_read_only_preview",
            method_source,
        )
        for forbidden in (
            "ReadOnlyProviderPreview",
            "build_read_only_provider_preview",
            "create_openai_compatible_config_from_user_profile",
            "self.config",
            "api_key_input",
            "self.cards",
            "secret_store",
            "provider_factory",
            "transport",
            "executor",
        ):
            self.assertNotIn(forbidden, method_source)

    def test_dialog_uses_read_only_style_group_titles_and_no_new_buttons(self):
        source_path = self.repo_root() / "ankiforge_ai" / "ui" / (
            "provider_profile_draft_dialog.py"
        )
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        button_labels = {
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "QPushButton"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        }

        self.assertIn('QGroupBox("Provider 安全信息")', source)
        self.assertIn('QGroupBox("草稿安全状态")', source)
        self.assertEqual(
            button_labels,
            {"更新本地预览（仅本地）", "关闭"},
        )

    def assert_fixed_status_rows(self, preview):
        self.assertEqual(
            self.row_mapping(preview.status_rows),
            {
                "Preview source": "仅本地草稿",
                "Activation status": "未激活",
                "Provider verification": "未执行",
                "Consent status": "不适用（未激活）",
                "Will save settings": "否",
                "Will send content": "否",
                "Will call provider": "否",
                "Will generate cards": "否",
                "Will write to Anki": "否",
            },
        )

    @staticmethod
    def row_mapping(rows):
        return {row.label: row.value for row in rows}

    @staticmethod
    def row_value(rows, label):
        return next(row.value for row in rows if row.label == label)

    @staticmethod
    def repo_root():
        return Path(__file__).parents[1]

    @staticmethod
    def draft(**overrides):
        values = {
            "provider": "Example Provider",
            "model": "example-model",
            "base_url": "https://api.example.com/v1",
            "privacy_notice": "Selected text stays in this local preview.",
        }
        values.update(overrides)
        return ProviderProfileDraftInput(**values)

    @staticmethod
    def preview_for(draft):
        view_data = build_provider_profile_draft_view_data(draft)
        return build_provider_profile_draft_read_only_preview(view_data)


if __name__ == "__main__":
    unittest.main()
