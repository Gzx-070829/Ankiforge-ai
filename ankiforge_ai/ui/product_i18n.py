"""Small in-memory product-copy catalog for the card maker surface."""


DEFAULT_PRODUCT_LANGUAGE = "zh"
PRODUCT_LANGUAGES = ("zh", "en")


PRODUCT_COPY = {
    "zh": {
        "title": "AnkiForge AI",
        "subtitle": "把学习材料变成 Anki 卡片",
        "language_toggle": "English",
        "advanced_debug": "高级 / 调试工具",
        "advanced_debug_collapse": "收起高级 / 调试工具",
        "advanced_debug_help": "旧流程与开发调试入口。普通制卡不需要使用这里。",
        "open_legacy_flow": "打开旧流程工具",
        "open_debug_panel": "打开旧调试面板",
        "material_section": "学习材料",
        "material_help": "粘贴学习材料，或导入本地文件；导入后仍可继续编辑。",
        "material_placeholder": "粘贴材料，或拖入 .md / .txt / .docx / .pdf 文件",
        "choose_file": "选择文件",
        "source_file_filter": (
            "支持的文件 (*.md *.markdown *.txt *.docx *.pdf);;"
            "Markdown (*.md *.markdown);;文本 (*.txt);;"
            "Word 文档 (*.docx);;PDF (*.pdf)"
        ),
        "use_example": "使用示例",
        "character_count": "{count} 字符",
        "source_imported": "已导入 {filename} · {kind} · {count} 字符",
        "source_import_first_only": "一次仅支持一个文件，本次已导入第一个。",
        "source_import_appended": "原有材料已保留，新文件已追加到末尾。",
        "system_encoding_fallback": "文件不是 UTF-8，已使用本机默认编码读取。",
        "docx_text_only": "DOCX 仅提取文本，图片、公式和复杂排版不会保留。",
        "pdf_text_only": (
            "PDF 仅提取可复制文本，不支持扫描版 OCR，复杂排版可能不完整。"
        ),
        "pdf_little_text": "提取到的 PDF 文本很少，该文件可能是扫描版。",
        "source_import_error_generic": "无法导入该文件，请检查文件后重试。",
        "source_import_error_file_not_found": "找不到该文件，请重新选择。",
        "source_import_error_unsupported_type": "暂不支持该文件类型。",
        "source_import_error_legacy_doc": (
            "暂不支持旧版 .doc，请另存为 .docx 后再导入。"
        ),
        "source_import_error_file_too_large": "文件过大，请先截取需要制卡的部分。",
        "source_import_error_empty_file": "文件中没有可导入的文本。",
        "source_import_error_read_failed": "无法读取该文件，请检查格式或编码。",
        "source_import_error_docx_invalid": "无法读取该 DOCX，文件可能已损坏或加密。",
        "source_import_error_docx_missing_document": (
            "无法读取该 DOCX，文件内容不完整。"
        ),
        "source_import_error_pdf_unavailable": (
            "当前环境无法解析 PDF，请先复制 PDF 文本或转换为 TXT/Markdown。"
        ),
        "source_import_error_pdf_invalid": "无法读取该 PDF，文件可能已损坏。",
        "source_import_error_pdf_encrypted": "暂不支持加密 PDF。",
        "source_import_error_pdf_too_many_pages": (
            "PDF 超过 50 页，请先截取需要制卡的部分。"
        ),
        "source_import_error_pdf_no_text": (
            "未提取到可复制文本，该 PDF 可能是扫描版；当前不支持 OCR。"
        ),
        "ai_section": "AI",
        "provider": "Provider",
        "model": "Model",
        "model_placeholder": "例如 deepseek-v4-flash",
        "api_key": "API key",
        "api_key_placeholder": "本次使用，不会保存",
        "api_key_help": "API key 仅本次使用，不会保存。",
        "advanced_settings": "高级设置",
        "advanced_settings_collapse": "收起高级设置",
        "base_url": "Base URL",
        "timeout": "Timeout",
        "generate_cards": "生成卡片",
        "regenerate_cards": "重新生成",
        "generation_running": "正在生成…",
        "generation_requirements": "请先填写学习材料、Model 和 API key。",
        "generation_failed": "生成失败，请检查 API key、模型或网络后重试。",
        "model_failure_help": (
            "模型名称可能不正确。DeepSeek 可尝试 deepseek-v4-flash "
            "或 deepseek-v4-pro。"
        ),
        "generation_success": "已生成 {count} 张卡片。",
        "cards_section": "生成的卡片",
        "no_cards": "还没有卡片",
        "no_cards_help": "放入材料后点击“生成卡片”",
        "card_number": "卡片 {number}",
        "front": "正面",
        "back": "背面",
        "source": "来源",
        "keep": "保留",
        "edit": "编辑",
        "discard": "丢弃",
        "write_section": "写入 Anki",
        "deck": "目标牌组",
        "note_type": "笔记类型",
        "front_mapping": "正面 →",
        "back_mapping": "背面 →",
        "source_mapping": "来源 →",
        "select": "请选择",
        "no_source": "不使用",
        "target_read_failed": "无法读取 Anki 牌组或笔记类型。",
        "field_read_failed": "无法读取笔记类型字段。",
        "check_duplicates": "检查重复",
        "duplicates_unchecked": "未检查",
        "duplicates_clear": "未发现重复",
        "duplicates_skipped": "可能重复，已跳过",
        "write_to_anki": "写入 Anki",
        "write_running": "正在写入…",
        "write_completed_button": "已写入，请在 Anki 中查看",
        "write_failed": "写入失败，请检查牌组、笔记类型或字段映射后重试。",
        "write_cancelled": "已取消。",
        "write_success": "已写入 {count} 张卡片，可以到 Anki 中查看。",
        "write_partial": "已写入 {success} 张，{failed} 张失败。请检查失败项后重试。",
        "confirm_write_title": "确认写入 Anki？",
        "confirm_write_body": "将写入 {count} 张卡片到「{deck}」。",
        "cancel": "取消",
        "confirm_write": "确认写入",
        "edit_card": "编辑卡片",
        "finish_edit": "完成修改",
    },
    "en": {
        "title": "AnkiForge AI",
        "subtitle": "Turn study materials into Anki cards",
        "language_toggle": "中文",
        "advanced_debug": "Advanced / Debug Tools",
        "advanced_debug_collapse": "Hide Advanced / Debug Tools",
        "advanced_debug_help": (
            "Legacy workflow and developer tools. You do not need these "
            "for normal card creation."
        ),
        "open_legacy_flow": "Open Legacy Workflow",
        "open_debug_panel": "Open Debug Panel",
        "material_section": "Study Material",
        "material_help": (
            "Paste study material or import a local file, then edit it before "
            "generating cards."
        ),
        "material_placeholder": (
            "Paste material, or drop a .md / .txt / .docx / .pdf file"
        ),
        "choose_file": "Choose file",
        "source_file_filter": (
            "Supported files (*.md *.markdown *.txt *.docx *.pdf);;"
            "Markdown (*.md *.markdown);;Text (*.txt);;"
            "Word documents (*.docx);;PDF (*.pdf)"
        ),
        "use_example": "Use Example",
        "character_count": "{count} characters",
        "source_imported": "Imported {filename} · {kind} · {count} characters",
        "source_import_first_only": (
            "One file can be imported at a time; the first file was imported."
        ),
        "source_import_appended": (
            "The existing material was kept and the file was appended."
        ),
        "system_encoding_fallback": (
            "The file was not UTF-8 and was read using the system encoding."
        ),
        "docx_text_only": (
            "DOCX import extracts text only; images, formulas, and complex "
            "layout are not preserved."
        ),
        "pdf_text_only": (
            "PDF import extracts selectable text only. Scanned PDFs/OCR and "
            "complex layout are not supported."
        ),
        "pdf_little_text": (
            "Very little PDF text was extracted; the file may be scanned."
        ),
        "source_import_error_generic": (
            "Could not import that file. Check it and try again."
        ),
        "source_import_error_file_not_found": (
            "That file could not be found. Please choose it again."
        ),
        "source_import_error_unsupported_type": (
            "This file type is not supported yet."
        ),
        "source_import_error_legacy_doc": (
            "Legacy .doc files are not supported. Please save as .docx first."
        ),
        "source_import_error_file_too_large": (
            "The file is too large. Please import a smaller excerpt."
        ),
        "source_import_error_empty_file": "The file contains no importable text.",
        "source_import_error_read_failed": (
            "Could not read that file. Check its format or encoding."
        ),
        "source_import_error_docx_invalid": (
            "Could not read that DOCX. It may be damaged or encrypted."
        ),
        "source_import_error_docx_missing_document": (
            "Could not read that DOCX because its contents are incomplete."
        ),
        "source_import_error_pdf_unavailable": (
            "PDF parsing is unavailable in this environment. Copy the PDF "
            "text or convert it to TXT/Markdown first."
        ),
        "source_import_error_pdf_invalid": (
            "Could not read that PDF. It may be damaged."
        ),
        "source_import_error_pdf_encrypted": "Encrypted PDFs are not supported.",
        "source_import_error_pdf_too_many_pages": (
            "The PDF exceeds 50 pages. Please import a smaller excerpt."
        ),
        "source_import_error_pdf_no_text": (
            "No selectable text was found. This PDF may be scanned; OCR is "
            "not supported."
        ),
        "ai_section": "AI",
        "provider": "Provider",
        "model": "Model",
        "model_placeholder": "For example, deepseek-v4-flash",
        "api_key": "API key",
        "api_key_placeholder": "Used this session only; not saved",
        "api_key_help": (
            "API key is used only for this session and will not be saved."
        ),
        "advanced_settings": "Advanced Settings",
        "advanced_settings_collapse": "Hide Advanced Settings",
        "base_url": "Base URL",
        "timeout": "Timeout",
        "generate_cards": "Generate Cards",
        "regenerate_cards": "Regenerate",
        "generation_running": "Generating…",
        "generation_requirements": (
            "Add study material, a model, and an API key first."
        ),
        "generation_failed": (
            "Generation failed. Check your API key, model, or network, "
            "then try again."
        ),
        "model_failure_help": (
            "The model name may be incorrect. For DeepSeek, try "
            "deepseek-v4-flash or deepseek-v4-pro."
        ),
        "generation_success": "Generated {count} cards.",
        "cards_section": "Generated Cards",
        "no_cards": "No cards yet",
        "no_cards_help": "Add material, then click “Generate Cards”",
        "card_number": "Card {number}",
        "front": "Front",
        "back": "Back",
        "source": "Source",
        "keep": "Keep",
        "edit": "Edit",
        "discard": "Discard",
        "write_section": "Write to Anki",
        "deck": "Deck",
        "note_type": "Note type",
        "front_mapping": "Front →",
        "back_mapping": "Back →",
        "source_mapping": "Source →",
        "select": "Select",
        "no_source": "Do not use",
        "target_read_failed": "Could not read Anki decks or note types.",
        "field_read_failed": "Could not read note type fields.",
        "check_duplicates": "Check Duplicates",
        "duplicates_unchecked": "Not checked",
        "duplicates_clear": "No duplicates found",
        "duplicates_skipped": "Possible duplicate, skipped",
        "write_to_anki": "Write to Anki",
        "write_running": "Writing…",
        "write_completed_button": "Written — check Anki",
        "write_failed": (
            "Write failed. Check your deck, note type, or field mapping, "
            "then try again."
        ),
        "write_cancelled": "Cancelled.",
        "write_success": "Wrote {count} cards. You can now check them in Anki.",
        "write_partial": (
            "Wrote {success} cards; {failed} failed. Check the failed items "
            "and try again."
        ),
        "confirm_write_title": "Write to Anki?",
        "confirm_write_body": "This will write {count} cards to “{deck}”.",
        "cancel": "Cancel",
        "confirm_write": "Confirm Write",
        "edit_card": "Edit Card",
        "finish_edit": "Apply Changes",
    },
}


def product_text(language: str, key: str, **values) -> str:
    """Return one formatted product string for a supported language."""

    if language not in PRODUCT_LANGUAGES:
        raise ValueError("unsupported product language")
    try:
        template = PRODUCT_COPY[language][key]
    except KeyError as error:
        raise KeyError(f"unknown product copy key: {key}") from error
    return template.format(**values)
