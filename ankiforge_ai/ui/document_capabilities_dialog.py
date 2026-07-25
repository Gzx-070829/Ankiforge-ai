"""Bilingual document-capability presentation and its thin Qt dialog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

from ..document import (
    ImporterCapability,
    SupportLevel,
    create_native_importer_registry,
)

try:
    from aqt.qt import (
        QDialog,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # Pure presentation tests run without Anki/Qt.
    QDialog = object
    QHBoxLayout = QLabel = QPushButton = QScrollArea = QVBoxLayout = QWidget = None


_COPY = {
    "zh": {
        "title": "文档支持能力",
        "intro": "仅处理你明确选择的本地文件；导入与分析不会调用 AI。",
        "native": "原生支持",
        "optional_ready": "可选后端已就绪",
        "optional_missing": "可选后端未配置",
        "fallback": "回退方式",
        "unsupported": "暂不支持",
        "native_detail": "本地解析，无需额外组件。",
        "optional_ready_detail": "使用已配置的本地可选后端。",
        "optional_missing_detail": "此格式需要你另行配置可选后端。",
        "optional_missing_guidance": "打开设置指南，完成本地后端设置后再重试。",
        "fallback_detail": "请复制可读文本或转换为原生支持的格式。",
        "unsupported_detail": "请改用原生支持的本地文件格式。",
        "close": "关闭",
    },
    "en": {
        "title": "Document capabilities",
        "intro": (
            "Only explicitly selected local files are processed; importing and "
            "analysis do not call AI."
        ),
        "native": "Native",
        "optional_ready": "Optional backend ready",
        "optional_missing": "Optional backend not configured",
        "fallback": "Fallback",
        "unsupported": "Unsupported",
        "native_detail": "Parsed locally with no extra component.",
        "optional_ready_detail": "Uses a configured optional local backend.",
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
            importer_id="pdf_optional",
            display_name_en="Advanced PDF",
            display_name_zh="高级 PDF",
            support_level=SupportLevel.OPTIONAL_ADVANCED,
            supported_extensions=(".pdf",),
            supports_structure=True,
            supports_tables=True,
            supports_images=False,
            supports_formulas=True,
            external_dependencies=("optional_local_backend",),
            unavailable_reason_key="optional_backend_missing",
            security_notes=("explicit_local_files_only", "no_network"),
            fallback_importer_ids=("pdf_copy_text",),
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
        self.setMinimumWidth(640)
        root = QVBoxLayout(self)
        intro = QLabel(view.intro)
        intro.setWordWrap(True)
        root.addWidget(intro)

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
            rows_layout.addWidget(row_widget)
        rows_layout.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        close_button = QPushButton(view.close_label)
        close_button.clicked.connect(self.accept)
        root.addWidget(close_button)


__all__ = [
    "DocumentCapabilitiesDialog",
    "DocumentCapabilitiesView",
    "DocumentCapabilityRowView",
    "build_document_capabilities_view",
    "default_document_capabilities",
]
