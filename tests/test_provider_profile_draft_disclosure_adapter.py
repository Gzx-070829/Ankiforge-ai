import ast
import inspect
import json
import unittest
from dataclasses import fields, replace
from pathlib import Path

from ankiforge_ai.ui.provider_profile_draft_disclosure_adapter import (
    DISCLOSURE_SUMMARY_MESSAGE,
    ProviderProfileDraftSendDisclosure,
    build_provider_profile_draft_send_disclosure,
)
from ankiforge_ai.ui.provider_profile_draft_helpers import (
    PROVIDER_PROFILE_DRAFT_TARGET_STAGE,
    ProviderProfileDraftDisplayRow,
    ProviderProfileDraftInput,
    build_provider_profile_draft_view_data,
)
from ankiforge_ai.ui.provider_profile_draft_preview_adapter import (
    build_provider_profile_draft_read_only_preview,
)


class ProviderProfileDraftDisclosureAdapterTests(unittest.TestCase):
    def test_adapter_only_accepts_pr3_preview(self):
        for value in (None, object(), self.draft(), build_provider_profile_draft_view_data(None)):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(ValueError):
                    build_provider_profile_draft_send_disclosure(value)

    def test_empty_and_invalid_previews_do_not_generate_disclosure(self):
        for draft in (None, self.draft(base_url="ftp://example.com")):
            with self.subTest(draft=draft):
                self.assertIsNone(
                    build_provider_profile_draft_send_disclosure(
                        self.preview_for(draft)
                    )
                )

    def test_valid_preview_generates_current_and_future_disclosure(self):
        disclosure = self.disclosure_for(self.draft())

        self.assertIsInstance(disclosure, ProviderProfileDraftSendDisclosure)
        self.assertEqual(disclosure.summary_message, DISCLOSURE_SUMMARY_MESSAGE)
        self.assertEqual(
            self.row_mapping(disclosure.current_rows),
            {
                "当前操作": "仅本地预览",
                "当前保存设置": "否",
                "当前接收 API key": "否",
                "当前发送资料": "否",
                "当前调用 provider": "否",
                "当前读取源资料 / Anki 内容": "否",
                "当前创建 consent": "否（未请求、未记录）",
                "当前生成卡片": "否",
                "当前写入 Anki": "否",
            },
        )
        self.assertEqual(
            self.row_mapping(disclosure.future_rows),
            {
                "未来发送对象": "上方草稿中的 Provider / Base URL",
                "未来发送内容": "仅用户明确选择的短预览",
                "未来发送前": "必须再次明确同意",
                "Target stage": PROVIDER_PROFILE_DRAFT_TARGET_STAGE,
                "披露边界": "本披露不构成 consent 或执行授权",
                "Provider 状态": "本披露不代表 provider 已验证、激活或可运行",
            },
        )

    def test_disclosure_does_not_claim_consent_or_runtime_authority(self):
        disclosure = self.disclosure_for(self.draft())
        rendered = "\n".join(
            row.value for row in disclosure.current_rows + disclosure.future_rows
        )

        self.assertIn("必须再次明确同意", rendered)
        self.assertIn("不构成 consent 或执行授权", rendered)
        self.assertIn("不代表 provider 已验证、激活或可运行", rendered)
        self.assertIn("未请求、未记录", rendered)

    def test_forged_valid_preview_is_rejected(self):
        preview = self.preview_for(self.draft())
        forged_rows = tuple(
            ProviderProfileDraftDisplayRow(
                label=row.label,
                value=("是" if row.label == "Will call provider" else row.value),
            )
            for row in preview.status_rows
        )

        with self.assertRaises(ValueError):
            build_provider_profile_draft_send_disclosure(
                replace(preview, status_rows=forged_rows)
            )

    def test_public_shape_has_no_sensitive_or_runtime_fields(self):
        forbidden_markers = (
            "key",
            "secret",
            "token",
            "credential",
            "has_secret",
            "runtime_config",
        )
        public_names = {
            field.name.lower() for field in fields(ProviderProfileDraftSendDisclosure)
        }
        public_names.update(
            name.lower()
            for name in inspect.signature(
                build_provider_profile_draft_send_disclosure
            ).parameters
        )

        for public_name in public_names:
            with self.subTest(public_name=public_name):
                self.assertFalse(
                    any(marker in public_name for marker in forbidden_markers)
                )

    def test_repr_and_safe_dict_do_not_copy_complete_user_input(self):
        values = {
            "provider": "sk-" + "A" * 24,
            "model": "Bearer disclosure-model",
            "base_url": "https://private-disclosure.example.com/v1",
            "privacy_notice": "secret token disclosure notice",
        }
        disclosure = self.disclosure_for(self.draft(**values))
        rendered = (
            repr(disclosure)
            + json.dumps(disclosure.to_safe_dict(), ensure_ascii=False)
        ).lower()

        for forbidden in (
            *values.values(),
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
            "provider_profile_draft_disclosure_adapter.py"
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
            "user_provider_config",
            "provider_consent",
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
            "ProviderConsentRecord",
            "ProviderSelection",
            "ReadOnlyProviderPreview",
            "build_read_only_provider_preview",
            "create_openai_compatible_config_from_user_profile",
            "load_secret",
            "create_provider",
            "post_json",
            "urlopen",
            "write_to_anki",
            "add_note",
        ):
            self.assertNotIn(forbidden_name, imported_names)
            self.assertNotIn(forbidden_name, called_names)

    def test_dialog_calls_disclosure_after_pr3_preview_and_hides_none(self):
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
        render_draft = next(
            node
            for node in dialog_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "_render_draft"
        )
        render_disclosure = next(
            node
            for node in dialog_class.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_render_send_disclosure"
        )
        draft_source = ast.get_source_segment(source, render_draft) or ""
        disclosure_source = ast.get_source_segment(source, render_disclosure) or ""

        self.assertLess(
            draft_source.index("_adapt_draft_for_preview"),
            draft_source.index("build_provider_profile_draft_send_disclosure"),
        )
        self.assertIn("if disclosure is None", disclosure_source)
        self.assertIn("setVisible(False)", disclosure_source)
        self.assertIn("setVisible(True)", disclosure_source)

    def test_dialog_adds_no_entry_or_authorizing_button(self):
        dialog_path = self.repo_root() / "ankiforge_ai" / "ui" / (
            "provider_profile_draft_dialog.py"
        )
        dialog_source = dialog_path.read_text(encoding="utf-8")
        tree = ast.parse(dialog_source)
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

        self.assertIn('QGroupBox("未来发送披露（仅说明，不授权）")', dialog_source)
        self.assertEqual(button_labels, {"更新本地预览（仅本地）", "关闭"})

        main_source = (
            self.repo_root() / "ankiforge_ai" / "ui" / "main_dialog.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("provider_profile_draft_disclosure_adapter", main_source)
        self.assertNotIn("未来发送披露", main_source)

    @staticmethod
    def row_mapping(rows):
        return {row.label: row.value for row in rows}

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

    @classmethod
    def disclosure_for(cls, draft):
        return build_provider_profile_draft_send_disclosure(cls.preview_for(draft))


if __name__ == "__main__":
    unittest.main()
