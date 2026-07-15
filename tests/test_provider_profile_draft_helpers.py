import ast
import inspect
import json
import unittest
from dataclasses import fields
from pathlib import Path

from ankiforge_ai.ui.provider_profile_draft_helpers import (
    EMPTY_PROVIDER_PROFILE_DRAFT_MESSAGE,
    PROVIDER_PROFILE_DRAFT_TARGET_STAGE,
    ProviderProfileDraftDisplayRow,
    ProviderProfileDraftInput,
    ProviderProfileDraftValidationError,
    ProviderProfileDraftViewData,
    build_provider_profile_draft_view_data,
)


class ProviderProfileDraftHelperTests(unittest.TestCase):
    def test_empty_draft_is_safe_and_non_executing(self):
        view = build_provider_profile_draft_view_data(None)

        self.assertTrue(view.is_empty)
        self.assertFalse(view.is_valid)
        self.assertEqual(
            view.empty_state_message,
            EMPTY_PROVIDER_PROFILE_DRAFT_MESSAGE,
        )
        self.assertEqual(view.profile_rows, ())
        self.assertEqual(view.validation_errors, ())
        self.assert_fixed_safety_rows(view)

    def test_valid_draft_is_normalized_and_previewed(self):
        view = build_provider_profile_draft_view_data(
            self.draft(
                provider="  Example Provider  ",
                model="  example-model  ",
                base_url="  https://api.example.com/v1  ",
                privacy_notice="  Selected text stays in this local preview.  ",
            )
        )

        self.assertFalse(view.is_empty)
        self.assertTrue(view.is_valid)
        self.assertEqual(
            self.row_value(view.profile_rows, "Provider"),
            "Example Provider",
        )
        self.assertEqual(
            self.row_value(view.profile_rows, "Model"),
            "example-model",
        )
        self.assertEqual(
            self.row_value(view.profile_rows, "Base URL"),
            "https://api.example.com/v1",
        )
        self.assertEqual(
            self.row_value(view.profile_rows, "Target stage"),
            PROVIDER_PROFILE_DRAFT_TARGET_STAGE,
        )

    def test_required_fields_report_local_errors_without_values(self):
        for field_name in (
            "provider",
            "model",
            "base_url",
            "privacy_notice",
        ):
            with self.subTest(field_name=field_name):
                view = build_provider_profile_draft_view_data(
                    self.draft(**{field_name: " "})
                )

                self.assertFalse(view.is_empty)
                self.assertFalse(view.is_valid)
                self.assertEqual(view.profile_rows, ())
                self.assertIn(
                    field_name,
                    {error.field_name for error in view.validation_errors},
                )

    def test_non_http_urls_are_rejected(self):
        for base_url in (
            "api.example.com/v1",
            "file:///tmp/provider",
            "data://text/plain,value",
            "/relative/path",
            "https://",
        ):
            with self.subTest(base_url=base_url):
                view = build_provider_profile_draft_view_data(
                    self.draft(base_url=base_url)
                )

                self.assertFalse(view.is_valid)
                self.assertEqual(
                    {error.field_name for error in view.validation_errors},
                    {"base_url"},
                )

    def test_url_embedded_credentials_are_rejected(self):
        for base_url in (
            "https://user:pass@example.com/v1",
            "https://user@example.com/v1",
            "https://@example.com/v1",
        ):
            with self.subTest(base_url=base_url):
                view = build_provider_profile_draft_view_data(
                    self.draft(base_url=base_url)
                )

                self.assertFalse(view.is_valid)
                self.assertEqual(
                    view.validation_errors[0].message,
                    "Base URL 不能包含用户名或密码。",
                )

    def test_target_stage_is_fixed(self):
        self.assertEqual(
            ProviderProfileDraftInput().target_stage,
            "knowledge_point_extraction",
        )
        with self.assertRaises(ValueError):
            self.draft(target_stage="card_generation")

    def test_fixed_safety_rows_forbid_persistence_execution_and_writes(self):
        view = build_provider_profile_draft_view_data(self.draft())

        self.assert_fixed_safety_rows(view)

    def test_public_shapes_have_no_sensitive_or_runtime_fields(self):
        forbidden_markers = (
            "key",
            "secret",
            "token",
            "has_secret",
            "credential",
        )
        for data_type in (
            ProviderProfileDraftInput,
            ProviderProfileDraftDisplayRow,
            ProviderProfileDraftValidationError,
            ProviderProfileDraftViewData,
        ):
            with self.subTest(data_type=data_type.__name__):
                field_names = {field.name.lower() for field in fields(data_type)}
                self.assertFalse(
                    any(
                        marker in field_name
                        for field_name in field_names
                        for marker in forbidden_markers
                    )
                )

        parameter_names = {
            name.lower()
            for name in inspect.signature(
                build_provider_profile_draft_view_data
            ).parameters
        }
        self.assertFalse(
            any(
                marker in parameter_name
                for parameter_name in parameter_names
                for marker in forbidden_markers
            )
        )

    def test_safe_summaries_and_repr_do_not_copy_user_values(self):
        draft = self.draft(
            provider="sk-" + "A" * 24,
            model="Bearer example-value",
            privacy_notice="secret token example",
        )
        view = build_provider_profile_draft_view_data(draft)
        rendered = "\n".join(
            (
                repr(draft),
                repr(view),
                json.dumps(draft.to_safe_dict(), ensure_ascii=False),
                json.dumps(view.to_safe_dict(), ensure_ascii=False),
            )
        ).lower()

        for forbidden in (
            "api_key",
            "api key",
            "secret",
            "token",
            "bearer",
            "sk-",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, rendered)

    def test_helper_has_strict_dependency_and_call_boundary(self):
        source_path = self.repo_root() / "ankiforge_ai" / "ui" / (
            "provider_profile_draft_helpers.py"
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
            "anki",
            "PyQt",
            "PySide",
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
        ):
            self.assertFalse(
                any(forbidden_import in module for module in imported_modules),
                forbidden_import,
            )
        for forbidden_call in (
            "create_openai_compatible_config_from_user_profile",
            "build_read_only_provider_preview",
            "load_config",
            "save_config",
            "load_secret",
            "create_provider",
            "post_json",
            "urlopen",
            "write",
        ):
            self.assertNotIn(forbidden_call, called_names)

    def test_legacy_provider_profile_draft_is_not_mounted_on_main_dialog(self):
        source_path = self.repo_root() / "ankiforge_ai" / "ui" / "main_dialog.py"
        source = source_path.read_text(encoding="utf-8")

        self.assertNotIn("show_provider_profile_draft_preview", source)
        self.assertNotIn("ProviderProfileDraftDialog", source)
        self.assertNotIn("save_config", source)
        self.assertNotIn("api_key_input", source)

    def test_dialog_source_has_only_allowed_inputs_and_buttons(self):
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
        editable_names = {
            target.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id in {"QLineEdit", "QTextEdit"}
            for target in node.targets
            if isinstance(target, ast.Attribute)
        }

        self.assertEqual(
            button_labels,
            {"更新本地预览（仅本地）", "关闭"},
        )
        self.assertEqual(
            editable_names,
            {
                "provider_input",
                "model_input",
                "base_url_input",
                "privacy_notice_input",
            },
        )
        self.assertNotIn("api_key_input", source)
        for required_notice in (
            "仅本地草稿",
            "不保存设置",
            "不接收 API key",
            "不发送资料",
            "不调用 provider",
            "不生成卡片",
            "不写入 Anki",
            "关闭后丢弃",
        ):
            self.assertIn(required_notice, source)

    def assert_fixed_safety_rows(self, view):
        for label in (
            "Will save settings",
            "Will send user content",
            "Will call provider",
            "Will generate cards",
            "Will write to Anki",
        ):
            self.assertEqual(self.row_value(view.safety_rows, label), "否")
        self.assertEqual(
            self.row_value(view.safety_rows, "Draft lifetime"),
            "仅当前弹窗，关闭后丢弃",
        )

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
            "privacy_notice": "Selected text would be sent to this provider.",
        }
        values.update(overrides)
        return ProviderProfileDraftInput(**values)


if __name__ == "__main__":
    unittest.main()
