"""Small in-memory product-copy catalog for the card maker surface."""


DEFAULT_PRODUCT_LANGUAGE = "zh"
PRODUCT_LANGUAGES = ("zh", "en")


PRODUCT_COPY = {
    "zh": {
        "title": "AnkiForge AI",
        "subtitle": "把学习材料变成 Anki 卡片",
        "language_toggle": "English",
        "advanced_debug": "高级",
        "advanced_debug_collapse": "收起高级",
        "advanced_debug_help": "旧版工具入口。普通制卡不需要使用。",
        "open_legacy_flow": "打开旧流程工具",
        "open_debug_panel": "打开旧版工具",
        "material_section": "学习材料",
        "material_help": "粘贴学习材料，或导入 .md / .txt / .docx 文件。PDF 请先复制文本或转换格式。",
        "first_run_guidance": "第一次使用？可以先试试示例材料，并写入测试牌组。",
        "material_placeholder": "粘贴材料，或拖入文件",
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
        "generation_preferences": "生成偏好",
        "provider_settings": "Provider 配置",
        "provider": "Provider",
        "model": "Model",
        "model_placeholder": "例如 deepseek-v4-flash",
        "api_key": "API key",
        "api_key_placeholder": "本次使用，不会保存",
        "api_key_help": "仅本次使用，不会保存。",
        "card_mode": "卡片模式",
        "mode_concept": "概念理解",
        "mode_concept_description": "理解概念、因果、区别和意义",
        "mode_definition": "术语定义",
        "mode_definition_description": "记忆术语、定义、关键特征和必要例子",
        "mode_exam": "考试复习",
        "mode_exam_description": "考题式正面，背面保留标准答题点",
        "mode_quick_review": "快速记忆",
        "mode_quick_review_description": "短问短答，一卡一事实",
        "generation_settings": "生成设置",
        "generation_settings_collapse": "收起生成设置",
        "generation_settings_help": "按需要调整；默认设置适合大多数材料。",
        "card_count": "卡片数量",
        "card_count_auto": "自动",
        "card_count_fewer": "更少",
        "card_count_balanced": "均衡",
        "card_count_more": "更多",
        "answer_length": "答案长度",
        "answer_length_short": "简短",
        "answer_length_medium": "适中",
        "output_language": "输出语言",
        "output_language_auto": "跟随材料",
        "output_language_zh": "简体中文",
        "output_language_en": "English",
        "advanced_settings": "更多设置",
        "advanced_settings_collapse": "收起更多设置",
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
        "generation_success": "已生成 {count} 张卡片，请检查后保留需要的卡片。",
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
        "review_required": "请检查卡片内容，保留需要写入 Anki 的卡片。",
        "quality_summary": "卡片检查：{good} 张可用 · {warnings} 张建议检查 · {blocking} 张不能写入",
        "quality_score": "质量 {score}% · {status}",
        "quality_status_info": "可用",
        "quality_status_warning": "请检查",
        "quality_status_blocking": "不能写入",
        "discard_blocking": "丢弃不能写入的卡",
        "quality_empty_front": "正面为空，不能写入",
        "quality_empty_front_suggestion": "补充一个具体问题，或丢弃这张卡。",
        "quality_empty_back": "背面为空，不能写入",
        "quality_empty_back_suggestion": "补充直接答案，或丢弃这张卡。",
        "quality_short_front": "问题可能过短",
        "quality_short_front_suggestion": "补充必要上下文，让问题可独立复习。",
        "quality_generic_front": "问题可能太泛",
        "quality_generic_front_suggestion": "把问题改得更具体。",
        "quality_long_back": "答案偏长",
        "quality_long_back_suggestion": "建议拆短，只保留直接答案。",
        "quality_multiple_questions": "可能包含多个问题",
        "quality_multiple_questions_suggestion": "拆成多张一卡一问的卡片。",
        "quality_multi_point_card": "可能包含多个知识点",
        "quality_multi_point_card_suggestion": "只保留一个可独立复习的知识点。",
        "quality_boilerplate_phrase": "包含无助于复习的套话",
        "quality_boilerplate_phrase_suggestion": "删除“根据材料可知”等套话。",
        "quality_markdown_residue": "可能残留 Markdown 标记",
        "quality_markdown_residue_suggestion": "清理标题、链接或强调标记。",
        "quality_duplicate_candidate": "与本批另一张卡内容相近",
        "quality_duplicate_candidate_suggestion": "比较两张卡，只保留更清楚的一张。",
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
        "duplicates_clear": "已检查",
        "duplicates_skipped": "可能重复，已跳过",
        "write_summary_empty": "完成审核和重复检查后，将显示写入摘要。",
        "write_summary": (
            "写入汇总｜牌组：{deck}｜笔记类型：{note_type}｜卡片：{cards}｜"
            "警告：{warnings}｜阻止：{blocking}\n来源：{source}\n标签：{tags}\n"
            "重复策略：可能重复的卡默认跳过"
        ),
        "write_result_summary": (
            "写入结果｜成功：{written}｜跳过重复：{skipped}｜失败：{failed}｜"
            "牌组：{deck}\n标签：{tags}"
        ),
        "write_to_anki": "写入 Anki",
        "write_running": "正在写入…",
        "write_completed_button": "已写入，请在 Anki 中查看",
        "write_failed": "写入失败，请检查牌组、笔记类型或字段映射后重试。",
        "write_cancelled": "已取消。",
        "write_success": "已写入 {count} 张卡片，可以到 Anki 中查看。",
        "write_partial": "已写入 {success} 张，{failed} 张失败。请检查失败项后重试。",
        "confirm_write_title": "确认写入 Anki？",
        "confirm_write_body": "将写入 {count} 张卡片到「{deck}」。",
        "confirm_write_body_v1": (
            "将写入 {count} 张卡片到「{deck}」。其中有 {warnings} 条质量警告；"
            "可能重复的卡已默认跳过。标签：{tags}。"
        ),
        "cancel": "取消",
        "confirm_write": "确认写入",
        "edit_card": "编辑卡片",
        "finish_edit": "完成修改",
    },
    "en": {
        "title": "AnkiForge AI",
        "subtitle": "Turn study materials into Anki cards",
        "language_toggle": "中文",
        "advanced_debug": "Advanced",
        "advanced_debug_collapse": "Hide Advanced",
        "advanced_debug_help": (
            "Legacy tools. You do not need these for normal card creation."
        ),
        "open_legacy_flow": "Open Legacy Workflow",
        "open_debug_panel": "Open Legacy Tools",
        "material_section": "Study Material",
        "material_help": (
            "Paste study material, or import a .md, .txt, or .docx file. "
            "For PDFs, copy the text or convert the file first."
        ),
        "first_run_guidance": "New here? Try the example material and write to a test deck first.",
        "material_placeholder": "Paste material, or drop a file",
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
        "generation_preferences": "Generation preferences",
        "provider_settings": "Provider settings",
        "provider": "Provider",
        "model": "Model",
        "model_placeholder": "For example, deepseek-v4-flash",
        "api_key": "API key",
        "api_key_placeholder": "Used this session only; not saved",
        "api_key_help": "API key is used only for this session and is not saved.",
        "card_mode": "Card mode",
        "mode_concept": "Concept",
        "mode_concept_description": "Understand concepts, causes, differences, and significance",
        "mode_definition": "Definition",
        "mode_definition_description": "Learn terms, definitions, key traits, and essential examples",
        "mode_exam": "Exam",
        "mode_exam_description": "Exam-style questions with concise answer points",
        "mode_quick_review": "Quick review",
        "mode_quick_review_description": "Short question, short answer, one fact per card",
        "generation_settings": "Generation Settings",
        "generation_settings_collapse": "Hide Generation Settings",
        "generation_settings_help": "Adjust when needed; the defaults suit most material.",
        "card_count": "Card count",
        "card_count_auto": "Auto",
        "card_count_fewer": "Fewer",
        "card_count_balanced": "Balanced",
        "card_count_more": "More",
        "answer_length": "Answer length",
        "answer_length_short": "Short",
        "answer_length_medium": "Medium",
        "output_language": "Output language",
        "output_language_auto": "Match material",
        "output_language_zh": "Simplified Chinese",
        "output_language_en": "English",
        "advanced_settings": "More Settings",
        "advanced_settings_collapse": "Hide More Settings",
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
        "generation_success": "Generated {count} cards. Check them and keep the ones you need.",
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
        "review_required": "Check each card and keep the ones you want to write to Anki.",
        "quality_summary": "Card check: {good} ready · {warnings} review · {blocking} cannot write",
        "quality_score": "Quality {score}% · {status}",
        "quality_status_info": "Ready",
        "quality_status_warning": "Review",
        "quality_status_blocking": "Cannot be written",
        "discard_blocking": "Discard blocked cards",
        "quality_empty_front": "Front is empty and cannot be written",
        "quality_empty_front_suggestion": "Add a specific question or discard this card.",
        "quality_empty_back": "Back is empty and cannot be written",
        "quality_empty_back_suggestion": "Add a direct answer or discard this card.",
        "quality_short_front": "Question may be too short",
        "quality_short_front_suggestion": "Add enough context for independent review.",
        "quality_generic_front": "Question may be too broad",
        "quality_generic_front_suggestion": "Make the question more specific.",
        "quality_long_back": "Answer may be too long",
        "quality_long_back_suggestion": "Shorten it to the direct answer.",
        "quality_multiple_questions": "May contain multiple questions",
        "quality_multiple_questions_suggestion": "Split it into one question per card.",
        "quality_multi_point_card": "May contain multiple points",
        "quality_multi_point_card_suggestion": "Keep one independently reviewable point.",
        "quality_boilerplate_phrase": "The card contains review-unhelpful filler",
        "quality_boilerplate_phrase_suggestion": "Remove phrases such as “according to the material”.",
        "quality_markdown_residue": "Markdown markup may remain",
        "quality_markdown_residue_suggestion": "Remove heading, link, or emphasis markup.",
        "quality_duplicate_candidate": "Similar to another card in this batch",
        "quality_duplicate_candidate_suggestion": "Compare both cards and keep the clearer one.",
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
        "duplicates_clear": "Checked",
        "duplicates_skipped": "Possible duplicate, skipped",
        "write_summary_empty": "Review cards and check duplicates to see the write summary.",
        "write_summary": (
            "Write summary | Deck: {deck} | Note type: {note_type} | Cards: {cards} | "
            "Warnings: {warnings} | Blocked: {blocking}\nSource: {source}\nTags: {tags}\n"
            "Duplicate behavior: possible duplicates are skipped"
        ),
        "write_result_summary": (
            "Write result | Written: {written} | Duplicate skips: {skipped} | "
            "Failed: {failed} | Deck: {deck}\nTags: {tags}"
        ),
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
        "confirm_write_body_v1": (
            "This will write {count} cards to “{deck}” with {warnings} quality "
            "warnings. Possible duplicates were skipped. Tags: {tags}."
        ),
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
