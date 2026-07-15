"""Stable bilingual user-facing errors with no raw exception disclosure."""

from dataclasses import dataclass


@dataclass(frozen=True, repr=False)
class UserErrorDefinition:
    code: str
    severity: str
    message: str
    suggested_action: str

    def __post_init__(self) -> None:
        if self.severity not in {"info", "warning", "error"}:
            raise ValueError("invalid user error severity")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (self.code, self.message, self.suggested_action)
        ):
            raise ValueError("user error fields must be non-empty")

    def __repr__(self) -> str:
        return f"UserErrorDefinition(code={self.code!r}, severity={self.severity!r})"


_COPY = {
    "no_material": ("warning", "还没有学习材料。", "请粘贴材料、导入文件或选择示例。", "No study material yet.", "Paste material, import a file, or choose an example."),
    "ai_not_configured": ("warning", "AI 尚未配置。", "请先打开 AI 设置。", "AI is not configured.", "Open AI Settings first."),
    "api_key_empty": ("warning", "API key 为空。", "请输入本次会话使用的 API key。", "The API key is empty.", "Enter the API key for this session."),
    "provider_call_failed": ("error", "AI 请求失败。", "请检查 Provider、模型和网络后重试。", "The AI request failed.", "Check the provider, model, and network, then retry."),
    "pdf_not_parsed": ("info", "PDF 暂不解析。", "请复制文本或转换为 Markdown、TXT 或 DOCX。", "PDF import is not available.", "Copy the text or convert it to Markdown, TXT, or DOCX."),
    "no_kept_cards": ("warning", "还没有保留的卡片。", "请先审核并保留至少一张卡。", "No cards are kept.", "Review and keep at least one card first."),
    "duplicate_not_checked": ("warning", "尚未检查重复。", "请先运行重复检查。", "Duplicates have not been checked.", "Run the duplicate check first."),
    "mapping_incomplete": ("warning", "字段映射不完整。", "请选择不同的正面和背面字段。", "Field mapping is incomplete.", "Select distinct front and back fields."),
    "blocking_cards_exist": ("warning", "仍有不能写入的卡片。", "请修改或丢弃这些卡片。", "Some cards cannot be written.", "Edit or discard the blocked cards."),
    "write_failed": ("error", "写入失败。", "请检查目标和字段；没有自动重试。", "Writing failed.", "Check the target and fields; no automatic retry was made."),
    "unsupported_note_type": ("warning", "当前笔记类型不受支持。", "请选择兼容的笔记类型。", "This note type is not supported.", "Choose a compatible note type."),
    "import_failed": ("error", "无法导入该文件。", "请检查文件格式、大小和编码。", "The file could not be imported.", "Check its format, size, and encoding."),
    "docx_partial_extraction": ("info", "DOCX 只提取了基础文本。", "请检查公式、图片和复杂排版内容。", "Only basic DOCX text was extracted.", "Review formulas, images, and complex layout manually."),
    "model_empty": ("warning", "模型名称为空。", "请在 AI 设置中填写模型。", "The model name is empty.", "Enter a model in AI Settings."),
    "provider_empty": ("warning", "Provider 为空。", "请在 AI 设置中选择 Provider。", "The provider is empty.", "Choose a provider in AI Settings."),
}

USER_ERROR_CODES = tuple(_COPY)


def get_user_error(code: str, language: str = "zh") -> UserErrorDefinition:
    if language not in {"zh", "en"}:
        raise ValueError("language must be zh or en")
    try:
        severity, zh_message, zh_action, en_message, en_action = _COPY[code]
    except (KeyError, TypeError):
        raise ValueError(f"unknown user error code: {code!r}") from None
    message, action = (
        (zh_message, zh_action) if language == "zh" else (en_message, en_action)
    )
    return UserErrorDefinition(code, severity, message, action)
