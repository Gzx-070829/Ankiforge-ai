"""Small in-memory product-copy catalog for the card maker surface."""


DEFAULT_PRODUCT_LANGUAGE = "zh"
PRODUCT_LANGUAGES = ("zh", "en")


PRODUCT_COPY = {
    "zh": {
        "title": "AnkiForge AI",
        "subtitle": "把学习材料变成 Anki 卡片",
        "language_toggle": "中文 / EN",
        "advanced_debug": "高级 / 调试工具",
        "advanced_debug_collapse": "收起高级 / 调试工具",
        "advanced_debug_help": "旧流程与开发调试入口。普通制卡不需要使用这里。",
        "open_legacy_flow": "打开旧流程工具",
        "open_debug_panel": "打开旧调试面板",
        "material_section": "学习材料",
        "material_help": "粘贴笔记、教材段落或复习资料。",
        "material_placeholder": "在这里粘贴学习材料",
        "choose_markdown": "选择 Markdown 文件",
        "markdown_filter": "Markdown 文件 (*.md)",
        "use_example": "使用示例",
        "character_count": "{count} 字符",
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
        "markdown_read_failed": "无法读取该 Markdown 文件。",
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
        "deck": "目标牌组 Deck",
        "note_type": "笔记类型 Note type",
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
        "language_toggle": "中文 / EN",
        "advanced_debug": "Advanced / Debug Tools",
        "advanced_debug_collapse": "Hide Advanced / Debug Tools",
        "advanced_debug_help": (
            "Legacy workflow and developer tools. You do not need these "
            "for normal card creation."
        ),
        "open_legacy_flow": "Open Legacy Workflow",
        "open_debug_panel": "Open Debug Panel",
        "material_section": "Study Material",
        "material_help": "Paste notes, textbook passages, or review material.",
        "material_placeholder": "Paste study material here",
        "choose_markdown": "Choose Markdown File",
        "markdown_filter": "Markdown Files (*.md)",
        "use_example": "Use Example",
        "character_count": "{count} characters",
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
        "markdown_read_failed": "Could not read that Markdown file.",
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
