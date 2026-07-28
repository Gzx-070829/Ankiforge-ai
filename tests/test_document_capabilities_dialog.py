import ast
import unittest
from pathlib import Path
from unittest import mock

from ankiforge_ai.document import ImporterCapability, SupportLevel
from ankiforge_ai.ui.document_capabilities_dialog import (
    build_document_capabilities_view,
    default_document_capabilities,
    probe_optional_backend_availability,
)


def _capability(importer_id, name_en, name_zh, level, extensions, **kwargs):
    return ImporterCapability(
        importer_id=importer_id,
        display_name_en=name_en,
        display_name_zh=name_zh,
        support_level=level,
        supported_extensions=extensions,
        supports_structure=kwargs.get("structure", False),
        supports_tables=kwargs.get("tables", False),
        supports_images=False,
        supports_formulas=kwargs.get("formulas", False),
        external_dependencies=kwargs.get("dependencies", ()),
        unavailable_reason_key=kwargs.get("reason"),
        security_notes=("explicit_local_files_only",),
        fallback_importer_ids=kwargs.get("fallbacks", ()),
    )


class DocumentCapabilitiesDialogTests(unittest.TestCase):
    def setUp(self):
        self.capabilities = (
            _capability(
                "docx_native",
                "Word document",
                "Word 文档",
                SupportLevel.NATIVE_STRUCTURED,
                (".docx",),
                structure=True,
                tables=True,
            ),
            _capability(
                "pdf_advanced_internal",
                "Advanced PDF",
                "高级 PDF",
                SupportLevel.OPTIONAL_ADVANCED,
                (".pdf",),
                structure=True,
                dependencies=("docling",),
                reason="optional_backend_missing",
            ),
            _capability(
                "pdf_copy_text",
                "PDF copy-text fallback",
                "PDF 复制文本回退",
                SupportLevel.FALLBACK_ONLY,
                (".pdf",),
            ),
        )

    def test_bilingual_rows_present_native_optional_and_fallback_status(self):
        zh = build_document_capabilities_view(
            self.capabilities,
            language="zh",
            backend_availability={"pdf_advanced_internal": False},
        )
        en = build_document_capabilities_view(
            self.capabilities,
            language="en",
            backend_availability={"pdf_advanced_internal": False},
        )

        self.assertEqual(zh.title, "文档支持能力")
        self.assertEqual(en.title, "Document capabilities")
        self.assertEqual(
            tuple(row.status for row in zh.rows),
            ("原生支持", "可选后端未配置", "回退方式"),
        )
        self.assertEqual(
            tuple(row.status for row in en.rows),
            ("Native", "Optional backend not configured", "Fallback"),
        )
        self.assertEqual(zh.rows[0].format_name, "Word 文档")
        self.assertEqual(en.rows[0].format_name, "Word document")

    def test_missing_optional_backend_has_actionable_manual_guidance_without_auto_install(self):
        for language in ("zh", "en"):
            view = build_document_capabilities_view(
                self.capabilities,
                language=language,
                backend_availability={"pdf_advanced_internal": False},
            )
            optional = view.rows[1]
            rendered = (optional.detail + " " + optional.guidance).casefold()

            self.assertTrue(optional.guidance)
            self.assertIn(
                "设置" if language == "zh" else "setup",
                rendered,
            )
            for forbidden in (
                "自动安装",
                "一键安装",
                "auto-install",
                "automatically install",
                "pip install",
                "pdf_advanced_internal",
                "optional_backend_missing",
            ):
                self.assertNotIn(forbidden, rendered)

    def test_available_optional_backend_is_distinct_from_missing_backend(self):
        view = build_document_capabilities_view(
            self.capabilities,
            language="en",
            backend_availability={"pdf_advanced_internal": True},
        )

        self.assertEqual(view.rows[1].status, "Optional backend detected")
        self.assertEqual(view.rows[1].guidance, "")

    def test_view_models_do_not_expose_internal_ids_dependencies_or_rules(self):
        view = build_document_capabilities_view(
            self.capabilities,
            language="en",
            backend_availability={"pdf_advanced_internal": False},
        )
        rendered = repr(view) + str(view.to_safe_dict())

        for forbidden in (
            "pdf_advanced_internal",
            "docx_native",
            "optional_backend_missing",
            "explicit_local_files_only",
            "ImporterCapability",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_dialog_is_a_thin_renderer_of_the_pure_view_model(self):
        source = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "ui"
            / "document_capabilities_dialog.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        dialog = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "DocumentCapabilitiesDialog"
        )
        rendered = ast.get_source_segment(source, dialog) or ""

        self.assertIn("QDialog", rendered)
        self.assertIn("build_document_capabilities_view", rendered)
        self.assertIn("view.rows", rendered)
        self.assertIn("_native_only_button", rendered)
        self.assertIn("_backend_status_labels", rendered)
        self.assertIn("_backend_detail_labels", rendered)
        self.assertIn("pandoc_invalid", rendered)
        for forbidden in (
            "detect_file_type",
            "import_document",
            "subprocess",
            "pip install",
            "planner",
            "Provider",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_default_view_lists_each_optional_backend_and_pdf_fallback(self):
        capabilities = default_document_capabilities()
        view = build_document_capabilities_view(
            capabilities,
            language="en",
            backend_availability={
                "docling": True,
                "markitdown": False,
                "pandoc": False,
            },
        )
        rendered = "\n".join(
            f"{row.format_name} {row.extensions} {row.status}"
            for row in view.rows
        )

        self.assertIn("Docling", rendered)
        self.assertIn("MarkItDown", rendered)
        self.assertIn("Pandoc", rendered)
        self.assertIn("PDF copy-text fallback", rendered)
        self.assertIn("Optional backend detected", rendered)

    def test_optional_probe_is_detection_only_and_default_off(self):
        with mock.patch(
            "ankiforge_ai.document.backends.detection.importlib.util.find_spec",
            return_value=None,
        ):
            availability = probe_optional_backend_availability()

        self.assertEqual(
            availability,
            {"docling": False, "markitdown": False, "pandoc": False},
        )


if __name__ == "__main__":
    unittest.main()
