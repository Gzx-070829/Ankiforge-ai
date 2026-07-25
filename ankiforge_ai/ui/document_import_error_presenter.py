"""Stable bilingual, path-free document import issue presentation."""

from __future__ import annotations

import re
from dataclasses import dataclass


_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,119}$")

_GROUPS = {
    "file_unavailable": "file_unavailable",
    "empty_file": "empty",
    "document_empty": "empty",
    "file_too_large": "too_large",
    "batch_too_large": "too_large",
    "too_many_files": "too_large",
    "document_too_complex": "too_complex",
    "table_too_large": "too_complex",
    "archive_too_many_members": "unsafe_archive",
    "encrypted_archive_member": "unsafe_archive",
    "unsafe_archive_member": "unsafe_archive",
    "archive_member_too_large": "unsafe_archive",
    "archive_too_large": "unsafe_archive",
    "suspicious_archive_compression": "unsafe_archive",
    "duplicate_archive_member": "unsafe_archive",
    "invalid_archive": "unsafe_archive",
    "office_macros_not_allowed": "unsafe_archive",
    "invalid_office_archive": "malformed",
    "malformed_file": "malformed",
    "binary_file": "unsupported",
    "binary_extension_mismatch": "unsupported",
    "risky_extension_mismatch": "unsupported",
    "unsupported_binary": "unsupported",
    "unsupported_type": "unsupported",
    "unknown_importer": "unsupported",
    "importer_does_not_support_type": "unsupported",
    "optional_importer_unavailable": "optional_backend",
    "optional_backend_missing": "optional_backend",
    "backend_disabled": "optional_backend",
    "backend_unavailable": "optional_backend",
    "backend_timeout": "backend_failed",
    "backend_cancelled": "backend_failed",
    "backend_failed": "backend_failed",
    "external_backend_failed": "backend_failed",
    "backend_output_too_large": "backend_failed",
    "backend_invalid_output": "backend_failed",
    "backend_containment_failed": "backend_failed",
    "unsafe_xml": "unsafe_xml",
    "xml_not_safe": "unsafe_xml",
    "extension_mismatch": "extension_warning",
    "hidden_sheet_skipped": "hidden_sheet",
    "notebook_output_too_large": "notebook_output",
    "notebook_binary_output_skipped": "notebook_output",
    "material_preview_truncated": "preview_truncated",
}

_COPY = {
    "zh": {
        "file_unavailable": (
            "无法读取这个文件。",
            "请重新选择文件，并确认它未被移动或占用。",
        ),
        "empty": ("文件没有可导入的文本。", "请选择包含学习内容的文件。"),
        "too_large": (
            "文件或本次选择超过安全大小限制。",
            "请减少文件数量，或拆分材料后重试。",
        ),
        "too_complex": (
            "文档结构超过本地解析安全限制。",
            "请拆分文档或转换为较简单的 Markdown / TXT。",
        ),
        "unsafe_archive": (
            "压缩包或 Office 容器未通过安全检查。",
            "请使用可信软件重新导出文件，不要移除安全限制。",
        ),
        "malformed": (
            "文件结构不完整或格式不正确。",
            "请重新导出，或转换为 Markdown / TXT。",
        ),
        "unsupported": (
            "当前解析器不支持这个文件。",
            "PDF 请配置本地可选后端，或复制可读文本；其他格式可转为 Markdown / TXT。",
        ),
        "optional_backend": (
            "所选本地可选后端尚未就绪。",
            "打开“支持能力”，为本次会话选择已安装的后端；PDF 也可复制文本。",
        ),
        "backend_failed": (
            "本地可选后端未完成转换。",
            "检查本机后端设置后重试，或改用原生格式。",
        ),
        "unsafe_xml": (
            "XML / HTML 内容未通过安全检查。",
            "请移除 DOCTYPE、ENTITY 或外部引用后重新导出。",
        ),
        "extension_warning": (
            "文件内容与扩展名不完全一致。",
            "请确认文件来源和实际格式。",
        ),
        "hidden_sheet": (
            "隐藏工作表已跳过。",
            "如需使用其中内容，请先在表格软件中取消隐藏。",
        ),
        "notebook_output": (
            "部分 Notebook 输出因大小或二进制类型被跳过。",
            "源代码和可读文本仍可审核。",
        ),
        "preview_truncated": (
            "编辑框只显示前 50,000 个字符的本地预览。",
            "智能生成使用已解析的完整文档，并仍受分块与调用上限约束。",
        ),
        "generic": (
            "文档导入未完成。",
            "请查看支持能力，转换为 Markdown / TXT 后重试。",
        ),
    },
    "en": {
        "file_unavailable": (
            "The file could not be read.",
            "Select it again and make sure it was not moved or locked.",
        ),
        "empty": (
            "The file has no importable text.",
            "Choose a file that contains study material.",
        ),
        "too_large": (
            "The file or selection exceeds the safety limit.",
            "Choose fewer files or split the material, then retry.",
        ),
        "too_complex": (
            "The document exceeds the local structure safety limit.",
            "Split it or convert it to simpler Markdown / TXT.",
        ),
        "unsafe_archive": (
            "The archive or Office container failed a safety check.",
            "Re-export it with trusted software; do not bypass the limit.",
        ),
        "malformed": (
            "The file structure is incomplete or malformed.",
            "Re-export it or convert it to Markdown / TXT.",
        ),
        "unsupported": (
            "No current parser supports this file.",
            "For PDF, configure an optional local backend or copy readable text; otherwise convert to Markdown / TXT.",
        ),
        "optional_backend": (
            "The selected optional local backend is not ready.",
            "Open Document capabilities and select an installed backend for this session, or copy PDF text.",
        ),
        "backend_failed": (
            "The optional local backend did not complete conversion.",
            "Check its local setup and retry, or use a native format.",
        ),
        "unsafe_xml": (
            "The XML / HTML content failed a safety check.",
            "Remove DOCTYPE, ENTITY, or external references and re-export.",
        ),
        "extension_warning": (
            "The file content does not fully match its extension.",
            "Confirm the source and actual format.",
        ),
        "hidden_sheet": (
            "A hidden worksheet was skipped.",
            "Unhide it in your spreadsheet app if you need that content.",
        ),
        "notebook_output": (
            "Some Notebook output was skipped because it was large or binary.",
            "Source code and readable text remain available for review.",
        ),
        "preview_truncated": (
            "The editor shows only the first 50,000 characters as a local preview.",
            "Intelligent generation uses the full parsed documents within chunk and call limits.",
        ),
        "generic": (
            "Document import did not complete.",
            "Check Document capabilities or convert the file to Markdown / TXT.",
        ),
    },
}


@dataclass(frozen=True)
class DocumentImportIssueView:
    message: str
    action: str

    @property
    def display_text(self) -> str:
        return f"{self.message} {self.action}"


def present_document_import_issue(
    code: str,
    *,
    language: str,
) -> DocumentImportIssueView:
    if not isinstance(code, str) or not _SAFE_CODE.fullmatch(code):
        raise ValueError("code must be a safe stable identifier")
    if language not in _COPY:
        raise ValueError("language must be zh or en")
    key = _GROUPS.get(code, "generic")
    message, action = _COPY[language][key]
    return DocumentImportIssueView(message=message, action=action)


__all__ = [
    "DocumentImportIssueView",
    "present_document_import_issue",
]
