from pathlib import Path

from ..capabilities import ImporterCapability, SupportLevel
from ..errors import DocumentImportError
from ..limits import DEFAULT_DOCUMENT_LIMITS, DocumentLimits
from ..registry import DocumentImporterRegistry
from .code_text import CodeTextImporter
from .epub import EpubImporter
from .html import HtmlImporter
from .json_data import JsonDataImporter
from .markdown import MarkdownImporter
from .notebook import NotebookImporter
from .office_open_xml import DocxImporter, PptxImporter, XlsxImporter
from .subtitles import SubtitleImporter
from .tabular import TabularImporter
from .text import TextImporter, TextMarkupImporter
from .xml_data import XmlDataImporter


def _capability(
    importer_id,
    extensions,
    *,
    structured,
    tables=False,
    formulas=False,
):
    return ImporterCapability(
        importer_id=importer_id,
        display_name_en=importer_id.upper(),
        display_name_zh=importer_id.upper(),
        support_level=(
            SupportLevel.NATIVE_STRUCTURED
            if structured
            else SupportLevel.NATIVE_TEXT
        ),
        supported_extensions=tuple(extensions),
        supports_structure=structured,
        supports_tables=tables,
        supports_images=False,
        supports_formulas=formulas,
        external_dependencies=(),
        unavailable_reason_key=None,
        security_notes=("explicit_local_files_only", "no_network", "no_execution"),
        fallback_importer_ids=(),
    )


def create_native_importer_registry() -> DocumentImporterRegistry:
    registry = DocumentImporterRegistry()
    registrations = (
        (_capability("text", (".txt", ".log"), structured=False), TextImporter),
        (
            _capability(
                "markdown",
                (".md", ".markdown"),
                structured=True,
                tables=True,
            ),
            MarkdownImporter,
        ),
        (
            _capability(
                "html",
                (".html", ".htm", ".xhtml"),
                structured=True,
                tables=True,
            ),
            HtmlImporter,
        ),
        (
            _capability("csv", (".csv",), structured=True, tables=True),
            lambda: TabularImporter("csv", ","),
        ),
        (
            _capability("tsv", (".tsv",), structured=True, tables=True),
            lambda: TabularImporter("tsv", "\t"),
        ),
        (
            _capability("json", (".json",), structured=True),
            lambda: JsonDataImporter("json"),
        ),
        (
            _capability("jsonl", (".jsonl",), structured=True),
            lambda: JsonDataImporter("jsonl"),
        ),
        (_capability("xml", (".xml",), structured=True), XmlDataImporter),
        (_capability("ipynb", (".ipynb",), structured=True), NotebookImporter),
        (
            _capability("srt", (".srt",), structured=True),
            lambda: SubtitleImporter("srt"),
        ),
        (
            _capability("vtt", (".vtt",), structured=True),
            lambda: SubtitleImporter("vtt"),
        ),
        (
            _capability("docx", (".docx",), structured=True, tables=True),
            DocxImporter,
        ),
        (
            _capability("pptx", (".pptx",), structured=True, tables=True),
            PptxImporter,
        ),
        (
            _capability(
                "xlsx",
                (".xlsx",),
                structured=True,
                tables=True,
                formulas=True,
            ),
            XlsxImporter,
        ),
        (_capability("epub", (".epub",), structured=True), EpubImporter),
        (
            _capability("yaml", (".yaml", ".yml"), structured=False),
            lambda: TextMarkupImporter("yaml"),
        ),
        (
            _capability("rst", (".rst",), structured=False),
            lambda: TextMarkupImporter("rst"),
        ),
        (
            _capability("org", (".org",), structured=False),
            lambda: TextMarkupImporter("org"),
        ),
        (
            _capability("latex", (".tex", ".latex"), structured=False),
            lambda: TextMarkupImporter("latex"),
        ),
        (
            _capability("python", (".py",), structured=False),
            lambda: CodeTextImporter("python"),
        ),
        (
            _capability("javascript", (".js",), structured=False),
            lambda: CodeTextImporter("javascript"),
        ),
        (
            _capability("typescript", (".ts",), structured=False),
            lambda: CodeTextImporter("typescript"),
        ),
        (
            _capability("java", (".java",), structured=False),
            lambda: CodeTextImporter("java"),
        ),
        (
            _capability("c", (".c", ".h"), structured=False),
            lambda: CodeTextImporter("c"),
        ),
        (
            _capability("cpp", (".cpp", ".cc"), structured=False),
            lambda: CodeTextImporter("cpp"),
        ),
        (
            _capability("rust", (".rs",), structured=False),
            lambda: CodeTextImporter("rust"),
        ),
        (
            _capability("go", (".go",), structured=False),
            lambda: CodeTextImporter("go"),
        ),
        (
            _capability("sql", (".sql",), structured=False),
            lambda: CodeTextImporter("sql"),
        ),
        (
            _capability("shell", (".sh",), structured=False),
            lambda: CodeTextImporter("shell"),
        ),
        (
            _capability("powershell", (".ps1",), structured=False),
            lambda: CodeTextImporter("powershell"),
        ),
    )
    for capability, factory in registrations:
        registry.register(capability, factory)
    return registry


def _batch_error(code):
    return DocumentImportError(
        code=code,
        message_key=f"document.error.{code}",
        action_key="document.action.reduce_selection",
    )


def import_documents(paths, limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS):
    selected = tuple(Path(path) for path in paths)
    if len(selected) > limits.max_files_per_batch:
        raise _batch_error("too_many_files")
    total = 0
    for path in selected:
        try:
            if not path.is_file():
                raise OSError
            total += path.stat().st_size
        except OSError:
            raise DocumentImportError(
                code="file_unavailable",
                message_key="document.error.file_unavailable",
                action_key="document.action.reselect_file",
            ) from None
        if total > limits.max_total_batch_bytes:
            raise _batch_error("batch_too_large")
    registry = create_native_importer_registry()
    return tuple(registry.import_document(path, limits) for path in selected)


__all__ = [
    "DocumentImporterRegistry",
    "create_native_importer_registry",
    "import_documents",
]
