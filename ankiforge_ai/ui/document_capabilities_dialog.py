"""Bilingual document-capability presentation and its thin Qt dialog."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Optional

from ..document import (
    ImporterCapability,
    SupportLevel,
    create_native_importer_registry,
)

try:
    from aqt.qt import (
        QDialog,
        QButtonGroup,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QRadioButton,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # Pure presentation tests run without Anki/Qt.
    QDialog = object
    QButtonGroup = QFileDialog = QHBoxLayout = QLabel = QPushButton = None
    QRadioButton = QScrollArea = QVBoxLayout = QWidget = None


_COPY = {
    "zh": {
        "title": "文档支持能力",
        "intro": "仅处理你明确选择的本地文件；导入与分析不会调用 AI。",
        "native": "原生支持",
        "optional_ready": "可选后端已检测到",
        "optional_missing": "可选后端未配置",
        "fallback": "回退方式",
        "unsupported": "暂不支持",
        "native_detail": "本地解析，无需额外组件。",
        "optional_ready_detail": "检测到本机组件；需为本次会话选择，实际转换仍会经过安全校验。",
        "optional_missing_detail": "此格式需要你另行配置可选后端。",
        "optional_missing_guidance": "打开设置指南，完成本地后端设置后再重试。",
        "fallback_detail": "请复制可读文本或转换为原生支持的格式。",
        "unsupported_detail": "请改用原生支持的本地文件格式。",
        "native_only": "仅使用原生 Core",
        "use_session": "本次会话使用",
        "choose_pandoc": "选择 Pandoc 可执行文件",
        "pandoc_ready": "Pandoc 已为本次会话启用。",
        "pandoc_invalid": "未选择有效的 pandoc.exe；请重新选择或继续使用原生 Core。",
        "close": "关闭",
    },
    "en": {
        "title": "Document capabilities",
        "intro": (
            "Only explicitly selected local files are processed; importing and "
            "analysis do not call AI."
        ),
        "native": "Native",
        "optional_ready": "Optional backend detected",
        "optional_missing": "Optional backend not configured",
        "fallback": "Fallback",
        "unsupported": "Unsupported",
        "native_detail": "Parsed locally with no extra component.",
        "optional_ready_detail": (
            "Detected locally; select it for this session. Conversion output "
            "still passes safety validation."
        ),
        "optional_missing_detail": (
            "This format needs an optional backend configured by you."
        ),
        "optional_missing_guidance": (
            "Open the setup guide, configure the local backend, then retry."
        ),
        "fallback_detail": (
            "Copy readable text or convert the file to a natively supported format."
        ),
        "unsupported_detail": "Choose a natively supported local file format.",
        "native_only": "Use native Core only",
        "use_session": "Use for this session",
        "choose_pandoc": "Choose Pandoc executable",
        "pandoc_ready": "Pandoc is enabled for this session.",
        "pandoc_invalid": (
            "No valid pandoc executable was selected; choose it again or "
            "continue with native Core."
        ),
        "close": "Close",
    },
}


@dataclass(frozen=True)
class DocumentCapabilityRowView:
    format_name: str
    extensions: str
    status: str
    detail: str
    guidance: str = ""
    backend_id: Optional[str] = field(default=None, repr=False)

    def to_safe_dict(self) -> dict[str, str]:
        return {
            "format_name": self.format_name,
            "extensions": self.extensions,
            "status": self.status,
            "detail": self.detail,
            "guidance": self.guidance,
        }


@dataclass(frozen=True)
class DocumentCapabilitiesView:
    title: str
    intro: str
    rows: tuple[DocumentCapabilityRowView, ...]
    close_label: str

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "intro": self.intro,
            "rows": [row.to_safe_dict() for row in self.rows],
            "close_label": self.close_label,
        }


def build_document_capabilities_view(
    capabilities: Iterable[ImporterCapability],
    *,
    language: str,
    backend_availability: Optional[Mapping[str, bool]] = None,
) -> DocumentCapabilitiesView:
    copy = _copy_for(language)
    availability = {} if backend_availability is None else dict(backend_availability)
    rows = []
    for capability in tuple(capabilities):
        if not isinstance(capability, ImporterCapability):
            raise TypeError("capabilities must contain ImporterCapability values")
        name = (
            capability.display_name_zh
            if language == "zh"
            else capability.display_name_en
        )
        status_key, detail_key, guidance_key = _capability_copy_keys(
            capability,
            availability.get(capability.importer_id),
        )
        rows.append(
            DocumentCapabilityRowView(
                format_name=name,
                extensions=", ".join(capability.supported_extensions),
                status=copy[status_key],
                detail=copy[detail_key],
                guidance="" if guidance_key is None else copy[guidance_key],
                backend_id=(
                    capability.importer_id
                    if capability.support_level
                    is SupportLevel.OPTIONAL_ADVANCED
                    else None
                ),
            )
        )
    return DocumentCapabilitiesView(
        title=copy["title"],
        intro=copy["intro"],
        rows=tuple(rows),
        close_label=copy["close"],
    )


def default_document_capabilities() -> tuple[ImporterCapability, ...]:
    """Return native capabilities plus honest optional/fallback PDF rows."""

    native = create_native_importer_registry().capabilities()
    return native + (
        ImporterCapability(
            importer_id="docling",
            display_name_en="Docling (advanced local parsing)",
            display_name_zh="Docling（高级本地解析）",
            support_level=SupportLevel.OPTIONAL_ADVANCED,
            supported_extensions=(".pdf", ".docx", ".pptx", ".xlsx", ".html"),
            supports_structure=True,
            supports_tables=True,
            supports_images=False,
            supports_formulas=True,
            external_dependencies=("docling",),
            unavailable_reason_key="optional_backend_missing",
            security_notes=("explicit_local_files_only", "no_network"),
            fallback_importer_ids=(),
        ),
        ImporterCapability(
            importer_id="markitdown",
            display_name_en="MarkItDown (local conversion)",
            display_name_zh="MarkItDown（本地转换）",
            support_level=SupportLevel.OPTIONAL_ADVANCED,
            supported_extensions=(".pdf", ".docx", ".pptx", ".xlsx"),
            supports_structure=False,
            supports_tables=True,
            supports_images=False,
            supports_formulas=False,
            external_dependencies=("markitdown",),
            unavailable_reason_key="optional_backend_missing",
            security_notes=("explicit_local_files_only", "no_network"),
            fallback_importer_ids=(),
        ),
        ImporterCapability(
            importer_id="pandoc",
            display_name_en="Pandoc (local executable)",
            display_name_zh="Pandoc（本地可执行文件）",
            support_level=SupportLevel.OPTIONAL_ADVANCED,
            supported_extensions=(
                ".docx",
                ".odt",
                ".md",
                ".markdown",
                ".rst",
                ".org",
                ".tex",
            ),
            supports_structure=False,
            supports_tables=True,
            supports_images=False,
            supports_formulas=False,
            external_dependencies=("pandoc",),
            unavailable_reason_key="optional_backend_missing",
            security_notes=("explicit_local_files_only", "no_network"),
            fallback_importer_ids=(),
        ),
        ImporterCapability(
            importer_id="pdf_copy_text",
            display_name_en="PDF copy-text fallback",
            display_name_zh="PDF 复制文本回退",
            support_level=SupportLevel.FALLBACK_ONLY,
            supported_extensions=(".pdf",),
            supports_structure=False,
            supports_tables=False,
            supports_images=False,
            supports_formulas=False,
            external_dependencies=(),
            unavailable_reason_key=None,
            security_notes=("explicit_local_files_only",),
            fallback_importer_ids=(),
        ),
    )


def probe_optional_backend_availability(
    *,
    pandoc_executable=None,
) -> dict[str, bool]:
    """Probe local capabilities without importing or installing backends."""

    from ..document.backends.detection import (
        probe_absolute_executable,
        probe_python_module,
    )

    return {
        "docling": probe_python_module("docling", "docling").available,
        "markitdown": probe_python_module(
            "markitdown",
            "markitdown",
        ).available,
        "pandoc": probe_absolute_executable(
            "pandoc",
            pandoc_executable,
        ).available,
    }


def _capability_copy_keys(
    capability: ImporterCapability,
    available: Optional[bool],
) -> tuple[str, str, Optional[str]]:
    if capability.support_level in {
        SupportLevel.NATIVE_STRUCTURED,
        SupportLevel.NATIVE_TEXT,
    }:
        return "native", "native_detail", None
    if capability.support_level is SupportLevel.OPTIONAL_ADVANCED:
        if available is True:
            return "optional_ready", "optional_ready_detail", None
        return (
            "optional_missing",
            "optional_missing_detail",
            "optional_missing_guidance",
        )
    if capability.support_level is SupportLevel.FALLBACK_ONLY:
        return "fallback", "fallback_detail", None
    return "unsupported", "unsupported_detail", None


def _copy_for(language: str) -> dict[str, str]:
    if language not in _COPY:
        raise ValueError("language must be zh or en")
    return _COPY[language]


class DocumentCapabilitiesDialog(QDialog):
    """Render a precomputed capability view without probing or importing."""

    def __init__(
        self,
        capabilities,
        *,
        language,
        backend_availability=None,
        enabled_backend_ids=(),
        pandoc_executable=None,
        parent=None,
    ):
        if QVBoxLayout is None:
            raise RuntimeError("DocumentCapabilitiesDialog requires Anki Qt")
        super().__init__(parent)
        view = build_document_capabilities_view(
            capabilities,
            language=language,
            backend_availability=backend_availability,
        )
        self.setWindowTitle(view.title)
        self._language = language
        self._pandoc_executable = pandoc_executable
        self._backend_availability = dict(backend_availability or {})
        self._backend_buttons = {}
        self._backend_status_labels = {}
        self._backend_detail_labels = {}
        self._backend_button_group = QButtonGroup(self)
        self._backend_button_group.setExclusive(True)
        enabled = set(enabled_backend_ids)
        self.setMinimumWidth(640)
        root = QVBoxLayout(self)
        intro = QLabel(view.intro)
        intro.setWordWrap(True)
        root.addWidget(intro)
        self._native_only_button = QRadioButton(
            _copy_for(language)["native_only"]
        )
        self._backend_button_group.addButton(self._native_only_button)
        self._native_only_button.setChecked(not enabled)
        root.addWidget(self._native_only_button)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        rows_layout = QVBoxLayout(body)
        for row in view.rows:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            format_label = QLabel(f"{row.format_name}  {row.extensions}")
            format_label.setProperty("role", "fieldLabel")
            status_label = QLabel(row.status)
            status_label.setProperty("role", "status")
            detail_label = QLabel(
                row.detail if not row.guidance else f"{row.detail} {row.guidance}"
            )
            detail_label.setWordWrap(True)
            row_layout.addWidget(format_label)
            row_layout.addWidget(status_label)
            row_layout.addWidget(detail_label, 1)
            if row.backend_id is not None:
                self._backend_status_labels[row.backend_id] = status_label
                self._backend_detail_labels[row.backend_id] = detail_label
                selector = QRadioButton(_copy_for(language)["use_session"])
                selector.setEnabled(
                    self._backend_availability.get(row.backend_id) is True
                )
                selector.setChecked(
                    row.backend_id in enabled and selector.isEnabled()
                )
                self._backend_button_group.addButton(selector)
                self._backend_buttons[row.backend_id] = selector
                row_layout.addWidget(selector)
                if row.backend_id == "pandoc":
                    choose = QPushButton(_copy_for(language)["choose_pandoc"])
                    choose.clicked.connect(self._choose_pandoc_executable)
                    row_layout.addWidget(choose)
            rows_layout.addWidget(row_widget)
        if not any(button.isChecked() for button in self._backend_buttons.values()):
            self._native_only_button.setChecked(True)
        rows_layout.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        close_button = QPushButton(view.close_label)
        close_button.clicked.connect(self.accept)
        root.addWidget(close_button)

    def selected_backend_ids(self) -> tuple[str, ...]:
        return tuple(
            backend_id
            for backend_id, button in self._backend_buttons.items()
            if button.isEnabled() and button.isChecked()
        )

    def pandoc_executable(self):
        return self._pandoc_executable

    def _choose_pandoc_executable(self):
        selected, _filter = QFileDialog.getOpenFileName(
            self,
            _copy_for(self._language)["choose_pandoc"],
            "",
            "Pandoc executable (pandoc.exe pandoc)",
        )
        if not selected:
            return
        available = probe_optional_backend_availability(
            pandoc_executable=selected,
        )["pandoc"]
        self._backend_availability["pandoc"] = available
        button = self._backend_buttons.get("pandoc")
        if button is not None:
            if available:
                button.setEnabled(True)
                button.setChecked(True)
                button.setToolTip(_copy_for(self._language)["pandoc_ready"])
            else:
                self._native_only_button.setChecked(True)
                button.setEnabled(False)
                button.setToolTip(_copy_for(self._language)["pandoc_invalid"])
        status_label = self._backend_status_labels.get("pandoc")
        detail_label = self._backend_detail_labels.get("pandoc")
        if status_label is not None:
            status_label.setText(
                _copy_for(self._language)[
                    "optional_ready" if available else "optional_missing"
                ]
            )
        if detail_label is not None:
            detail_label.setText(
                _copy_for(self._language)[
                    "optional_ready_detail" if available else "pandoc_invalid"
                ]
            )
        self._pandoc_executable = selected if available else None


__all__ = [
    "DocumentCapabilitiesDialog",
    "DocumentCapabilitiesView",
    "DocumentCapabilityRowView",
    "build_document_capabilities_view",
    "default_document_capabilities",
    "probe_optional_backend_availability",
]
