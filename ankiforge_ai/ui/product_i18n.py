"""Small in-memory product-copy catalog for the card maker surface."""


DEFAULT_PRODUCT_LANGUAGE = "zh"
PRODUCT_LANGUAGES = ("zh", "en")


PRODUCT_COPY = {
    "zh": {
        "title": "AnkiForge AI",
        "subtitle": "把学习材料变成 Anki 卡片",
        "language_toggle": "English",
        "help": "帮助",
        "help_title": "第一次使用 AnkiForge AI？",
        "help_close": "知道了",
        "help_use_example": "使用示例",
        "help_addon_identity": "这是 Anki 桌面端插件，不是共享牌组，也不是网页服务。",
        "help_own_material": "它把你自己的学习材料整理成候选卡，不提供现成卡组。",
        "help_provider": "生成卡片需要你自行选择 AI Provider。",
        "help_session_key": "API key 只在当前窗口使用，关闭后即清除。",
        "help_review": "AI 生成的是候选卡，请逐张审核并修改。",
        "help_confirmation": "只有你最终确认后，卡片才会写入 Anki。",
        "help_test_deck": "第一次使用建议选择单独的测试牌组。",
        "help_pdf": "PDF 暂不解析，请复制文本或转换为 Markdown、TXT 或 DOCX。",
        "example_picker_title": "选择示例材料",
        "ai_settings": "AI 设置",
        "ai_not_configured": "AI 未配置",
        "ai_configured": "{provider} · 已配置",
        "save_session_settings": "保存本次设置",
        "close": "关闭",
        "ai_settings_session_note": (
            "API key 仅在本次 Anki 窗口中使用，不会写入配置文件。"
        ),
        "ai_settings_invalid": "请填写有效的 Provider、Model 和 API key。",
        "create_cards_section": "创建卡片",
        "advanced_debug": "高级",
        "advanced_debug_collapse": "收起高级",
        "advanced_debug_help": "旧版工具入口。普通制卡不需要使用。",
        "open_legacy_flow": "打开旧流程工具",
        "open_debug_panel": "打开旧版工具",
        "material_section": "学习材料",
        "material_help": "粘贴材料，或导入 Markdown / TXT / DOCX。",
        "first_run_guidance": "第一次使用？可以先试试示例材料，并写入测试牌组。",
        "material_placeholder": "粘贴学习材料，或拖入文件",
        "material_import_hint": "也可拖入 TXT、MD 或 DOCX 文件",
        "choose_file": "选择文件",
        "source_file_filter": (
            "支持的文档 (*.txt *.log *.md *.markdown *.html *.htm *.xhtml "
            "*.csv *.tsv *.json *.jsonl *.xml *.ipynb *.srt *.vtt *.docx "
            "*.pptx *.xlsx *.epub *.yaml *.yml *.rst *.org *.tex *.latex "
            "*.py *.js *.ts *.java *.c *.h *.cpp *.cc *.hpp *.rs *.go *.sql *.sh "
            "*.ps1 *.pdf);;所有文件 (*)"
        ),
        "document_capabilities": "支持能力",
        "document_queue_empty": "尚未选择文档",
        "document_queue_status_queued": "等待导入",
        "document_queue_status_importing": "正在导入",
        "document_queue_status_success": "已导入",
        "document_queue_status_warning": "已导入，有提醒",
        "document_queue_status_failure": "导入失败",
        "document_queue_row": (
            "{filename} · {status} · {type} · {importer} · "
            "{sections} 节 / {blocks} 块 / {chars} 字符"
        ),
        "remove_document": "移除",
        "move_document_up": "上移",
        "move_document_down": "下移",
        "retry_failed_imports": "仅重试失败文件",
        "retry_failed_generation": "仅重试失败分块",
        "retry_generation_confirmation_title": "确认重试失败分块",
        "retry_generation_confirmation_body": (
            "本次最多再调用 AI {calls} 次，并且最多补充 {cards} 张卡片。"
            "只会重试失败分块，继续吗？"
        ),
        "document_imported_batch": "已解析 {count} 个文档；不会自动调用 AI。",
        "document_queue_error_too_many_files": "一次最多选择 20 个文件。",
        "document_queue_error_batch_too_large": "所选文件总大小超过 25 MiB。",
        "document_queue_error_file_unavailable": "无法读取所选文件，请重新选择。",
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
        "ai_provider": "AI Provider",
        "generation_preferences": "生成偏好",
        "provider_settings": "Provider 配置",
        "provider": "Provider",
        "model": "Model",
        "model_placeholder": "例如 deepseek-v4-flash",
        "api_key": "API key",
        "api_key_placeholder": "输入 API key",
        "api_key_help": "仅本次使用，不会保存。",
        "card_mode": "卡片模式",
        "mode_concept": "概念理解",
        "mode_concept_description": "理解概念、原因、区别和意义。",
        "mode_definition": "术语定义",
        "mode_definition_description": "记忆术语、定义、关键特征和必要例子",
        "mode_exam": "考试复习",
        "mode_exam_description": "考题式正面，背面保留标准答题点",
        "mode_quick_review": "快速回顾",
        "mode_quick_review_description": "短问短答，一卡一事实",
        "generation_settings": "生成设置",
        "intelligence_level": "智能级别",
        "intelligence_fast": "快速",
        "intelligence_standard": "标准",
        "intelligence_deep": "深度",
        "intelligence_estimate_pending": "解析文档后显示分块、调用与卡片估算。",
        "paste_generation_behavior": (
            "粘贴文本使用 1 次有界卡片生成调用；"
            "Fast / Standard / Deep 仅在导入文档后启用。"
        ),
        "plan_details": "查看计划详情",
        "plan_details_collapse": "收起计划详情",
        "intelligence_confirmation_title": "确认开始有界 AI 生成",
        "intelligence_confirmation_body": (
            "{level} 模式预计 {estimate}。确认后才会开始首次 AI 调用；"
            "不会自动重试。"
        ),
        "generation_settings_collapse": "收起生成设置",
        "more_options": "生成设置（可选）",
        "more_options_collapse": "收起生成设置",
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
        "document_run_in_progress": (
            "文档有界运行进行中；这里会显示规划、生成与本地检查阶段。"
        ),
        "generation_group_progress": "生成分组 {completed}/{total}",
        "document_import_in_progress": (
            "请等待队列中的全部文档完成导入，再生成卡片。"
        ),
        "document_batch_too_complex": (
            "合并后的文档超过单次运行上限（最多 48 个分块、96 个知识点）。"
            "请移除部分文档或拆成多批生成。"
        ),
        "generation_requirements": "请先添加材料并配置 AI。",
        "material_too_long": "材料过长，请拆分后再生成。",
        "generation_failed": "生成失败，请检查 API key、模型或网络后重试。",
        "generation_endpoint_not_authorized": "请重新检查并确认 Provider 地址。",
        "generation_http_auth": "API key 可能无效或无权限。",
        "generation_http_not_found": "模型或 Provider 地址可能不存在。",
        "generation_http_timeout": "请求超时，请稍后重试。",
        "generation_http_rate_limit": "请求过于频繁或额度不足。",
        "generation_http_unavailable": "Provider 服务暂时不可用。",
        "model_failure_help": (
            "模型名称可能不正确。DeepSeek 可尝试 deepseek-v4-flash "
            "或 deepseek-v4-pro。"
        ),
        "generation_success": "已生成 {count} 张卡片，请检查后保留需要的卡片。",
        "cards_section": "生成的卡片",
        "no_cards": "还没有卡片",
        "no_cards_help": "放入材料后点击“生成卡片”。",
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
        "quality_status_ready": "可用",
        "quality_status_review": "请检查",
        "quality_status_blocked": "不能写入",
        "discard_blocking": "丢弃不能写入的卡",
        "keep_clean": "保留可用卡片",
        "copy": "复制",
        "restore": "还原",
        "review_stats": (
            "共 {total} · 待审核 {pending} · 已保留 {kept} · 已丢弃 {discarded} · "
            "有提醒 {warnings} · 不能写入 {blocking}"
        ),
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
        "front_mapping": "正面",
        "back_mapping": "背面",
        "source_mapping": "来源",
        "select": "请选择",
        "no_source": "不使用",
        "target_read_failed": "无法读取 Anki 牌组或笔记类型。",
        "field_read_failed": "无法读取笔记类型字段。",
        "mapping_incomplete": "字段映射不完整或不兼容，请重新选择。",
        "check_duplicates": "检查重复",
        "duplicates_unchecked": "未检查",
        "duplicates_clear": "已检查",
        "duplicates_skipped": "可能重复，已跳过",
        "write_summary_empty": "完成审核和重复检查后，将显示写入摘要。",
        "write_summary": (
            "目标：{deck} · {note_type}\n"
            "将写入：{cards} 张\n"
            "跳过重复：{skipped} 张\n"
            "质量提醒：{warnings} 张\n"
            "不能写入：{blocking} 张\n"
            "来源：{source}\n"
            "Tags：{tags}"
        ),
        "write_result_summary": (
            "已写入：{written} 张\n"
            "跳过重复：{skipped} 张\n"
            "失败：{failed} 张\n"
            "目标：{deck} · {note_type}\n"
            "来源：{source}\n"
            "时间：{timestamp}\n"
            "批次：{batch}\n"
            "Tags：{tags}"
        ),
        "last_write": "上次写入：{count} 张到 {deck} · {timestamp}",
        "write_to_anki": "写入 Anki",
        "write_running": "正在写入…",
        "write_completed_button": "已写入，请在 Anki 中查看",
        "write_failed": "写入失败，请检查牌组、笔记类型或字段映射后重试。",
        "write_cancelled": "已取消。",
        "duplicate_state_changed": "重复检查结果已变化，请查看更新后的摘要并再次确认。",
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
        "help": "Help",
        "help_title": "New to AnkiForge AI?",
        "help_close": "Got it",
        "help_use_example": "Use an example",
        "help_addon_identity": "This is an Anki Desktop add-on, not a shared deck or web app.",
        "help_own_material": "It turns your own study material into candidate cards; no pre-made decks are included.",
        "help_provider": "Card generation requires an AI provider you choose.",
        "help_session_key": "Your API key stays in this window and is cleared when it closes.",
        "help_review": "AI output is a set of candidate cards. Review and edit every card.",
        "help_confirmation": "Cards are written to Anki only after your final confirmation.",
        "help_test_deck": "Start with a separate test deck the first time.",
        "help_pdf": "PDF import is unavailable. Copy the text or convert it to Markdown, TXT, or DOCX.",
        "example_picker_title": "Choose example material",
        "ai_settings": "AI Settings",
        "ai_not_configured": "AI not configured",
        "ai_configured": "{provider} · Configured",
        "save_session_settings": "Save for this session",
        "close": "Close",
        "ai_settings_session_note": (
            "The API key is used only in this Anki window and is not written "
            "to a configuration file."
        ),
        "ai_settings_invalid": "Enter a valid Provider, Model, and API key.",
        "create_cards_section": "Create Cards",
        "advanced_debug": "Advanced",
        "advanced_debug_collapse": "Hide Advanced",
        "advanced_debug_help": (
            "Legacy tools. You do not need these for normal card creation."
        ),
        "open_legacy_flow": "Open Legacy Workflow",
        "open_debug_panel": "Open Legacy Tools",
        "material_section": "Study Material",
        "material_help": "Paste material, or import Markdown / TXT / DOCX.",
        "first_run_guidance": "New here? Try the example material and write to a test deck first.",
        "material_placeholder": "Paste study material, or drop a file",
        "material_import_hint": "You can also drop a TXT, MD, or DOCX file",
        "choose_file": "Choose file",
        "source_file_filter": (
            "Supported documents (*.txt *.log *.md *.markdown *.html *.htm "
            "*.xhtml *.csv *.tsv *.json *.jsonl *.xml *.ipynb *.srt *.vtt "
            "*.docx *.pptx *.xlsx *.epub *.yaml *.yml *.rst *.org *.tex "
            "*.latex *.py *.js *.ts *.java *.c *.h *.cpp *.cc *.hpp *.rs *.go "
            "*.sql *.sh *.ps1 *.pdf);;All files (*)"
        ),
        "document_capabilities": "Capabilities",
        "document_queue_empty": "No documents selected",
        "document_queue_status_queued": "Queued",
        "document_queue_status_importing": "Importing",
        "document_queue_status_success": "Imported",
        "document_queue_status_warning": "Imported with warnings",
        "document_queue_status_failure": "Import failed",
        "document_queue_row": (
            "{filename} · {status} · {type} · {importer} · "
            "{sections} sections / {blocks} blocks / {chars} characters"
        ),
        "remove_document": "Remove",
        "move_document_up": "Move up",
        "move_document_down": "Move down",
        "retry_failed_imports": "Retry failed files only",
        "retry_failed_generation": "Retry failed generation chunks only",
        "retry_generation_confirmation_title": "Confirm failed-chunk retry",
        "retry_generation_confirmation_body": (
            "This can make up to {calls} more AI calls and add at most "
            "{cards} cards. Only failed chunks are retried. Continue?"
        ),
        "document_imported_batch": (
            "Parsed {count} documents; AI will not start automatically."
        ),
        "document_queue_error_too_many_files": "Select no more than 20 files at once.",
        "document_queue_error_batch_too_large": (
            "The selected files exceed the 25 MiB batch limit."
        ),
        "document_queue_error_file_unavailable": (
            "A selected file could not be read. Select it again."
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
        "ai_provider": "AI Provider",
        "generation_preferences": "Generation preferences",
        "provider_settings": "Provider settings",
        "provider": "Provider",
        "model": "Model",
        "model_placeholder": "For example, deepseek-v4-flash",
        "api_key": "API key",
        "api_key_placeholder": "Enter API key",
        "api_key_help": "Used only for this session. Not saved.",
        "card_mode": "Card mode",
        "mode_concept": "Concept",
        "mode_concept_description": "Understand concepts, causes, differences, and significance",
        "mode_definition": "Definition",
        "mode_definition_description": "Learn terms, definitions, key traits, and essential examples",
        "mode_exam": "Exam",
        "mode_exam_description": "Exam-style questions with concise answer points",
        "mode_quick_review": "Quick Review",
        "mode_quick_review_description": "Short question, short answer, one fact per card",
        "generation_settings": "Generation Settings",
        "intelligence_level": "Intelligence",
        "intelligence_fast": "Fast",
        "intelligence_standard": "Standard",
        "intelligence_deep": "Deep",
        "intelligence_estimate_pending": (
            "Parse documents to see chunk, call, and card estimates."
        ),
        "paste_generation_behavior": (
            "Pasted text uses one bounded card-generation call; "
            "Fast / Standard / Deep apply after document import."
        ),
        "plan_details": "View plan details",
        "plan_details_collapse": "Hide plan details",
        "intelligence_confirmation_title": "Confirm bounded AI generation",
        "intelligence_confirmation_body": (
            "{level} is estimated at {estimate}. The first AI call starts only "
            "after confirmation; there is no automatic retry."
        ),
        "generation_settings_collapse": "Hide Generation Settings",
        "more_options": "Generation settings (optional)",
        "more_options_collapse": "Hide generation settings",
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
        "document_run_in_progress": (
            "Bounded document run in progress; planning, generation, and "
            "local quality stages appear here."
        ),
        "generation_group_progress": "Generation group {completed}/{total}",
        "document_import_in_progress": (
            "Wait for every queued document to finish importing before "
            "generating cards."
        ),
        "document_batch_too_complex": (
            "The combined documents exceed one run (48 chunks or 96 knowledge "
            "points). Remove documents or generate them in smaller batches."
        ),
        "generation_requirements": "Add material and configure AI first.",
        "material_too_long": (
            "The material is too long. Please split it before generating cards."
        ),
        "generation_failed": (
            "Generation failed. Check your API key, model, or network, "
            "then try again."
        ),
        "generation_endpoint_not_authorized": (
            "Review and confirm the provider endpoint before generating."
        ),
        "generation_http_auth": "The API key may be invalid or lack permission.",
        "generation_http_not_found": "The model or provider endpoint may not exist.",
        "generation_http_timeout": "The request timed out. Try again later.",
        "generation_http_rate_limit": (
            "Requests may be too frequent, or the account may lack quota."
        ),
        "generation_http_unavailable": (
            "The provider service is temporarily unavailable."
        ),
        "model_failure_help": (
            "The model name may be incorrect. For DeepSeek, try "
            "deepseek-v4-flash or deepseek-v4-pro."
        ),
        "generation_success": "Generated {count} cards. Check them and keep the ones you need.",
        "cards_section": "Generated Cards",
        "no_cards": "No cards yet",
        "no_cards_help": "Add material, then click “Generate cards”.",
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
        "quality_status_ready": "Ready",
        "quality_status_review": "Review",
        "quality_status_blocked": "Cannot be written",
        "discard_blocking": "Discard blocked cards",
        "keep_clean": "Keep clean cards",
        "copy": "Copy",
        "restore": "Restore",
        "review_stats": (
            "Total {total} · Pending {pending} · Kept {kept} · Discarded {discarded} · "
            "Reminders {warnings} · Blocked {blocking}"
        ),
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
        "front_mapping": "Front",
        "back_mapping": "Back",
        "source_mapping": "Source",
        "select": "Select",
        "no_source": "Do not use",
        "target_read_failed": "Could not read Anki decks or note types.",
        "field_read_failed": "Could not read note type fields.",
        "mapping_incomplete": "Field mapping is incomplete or incompatible. Choose again.",
        "check_duplicates": "Check Duplicates",
        "duplicates_unchecked": "Not checked",
        "duplicates_clear": "Checked",
        "duplicates_skipped": "Possible duplicate, skipped",
        "write_summary_empty": "Review cards and check duplicates to see the write summary.",
        "write_summary": (
            "Target: {deck} · {note_type}\n"
            "Cards to write: {cards}\n"
            "Duplicate skips: {skipped}\n"
            "Quality reminders: {warnings}\n"
            "Blocked: {blocking}\n"
            "Source: {source}\n"
            "Tags: {tags}"
        ),
        "write_result_summary": (
            "Written: {written}\n"
            "Duplicate skips: {skipped}\n"
            "Failed: {failed}\n"
            "Target: {deck} · {note_type}\n"
            "Source: {source}\n"
            "Time: {timestamp}\n"
            "Batch: {batch}\n"
            "Tags: {tags}"
        ),
        "last_write": "Last write: {count} cards to {deck} · {timestamp}",
        "write_to_anki": "Write to Anki",
        "write_running": "Writing…",
        "write_completed_button": "Written — check Anki",
        "write_failed": (
            "Write failed. Check your deck, note type, or field mapping, "
            "then try again."
        ),
        "write_cancelled": "Cancelled.",
        "duplicate_state_changed": (
            "Duplicate results changed. Review the updated summary and confirm again."
        ),
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
