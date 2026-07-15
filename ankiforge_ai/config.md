# Legacy configuration reference

The current product does not read or save an API key here. Enter credentials only in the AI Settings Modal for the active window; any legacy `api_key` field on disk is ignored and removed on save.

```json
{
    "ai_provider": "支持 mock、deepseek、openai_compatible。deepseek 是 OpenAI-compatible preset",
    "model": "mock 默认 mock-v0.2；deepseek 默认 deepseek-chat；openai_compatible 由用户填写",
    "api_base_url": "deepseek 默认 https://api.deepseek.com；openai_compatible 由用户填写",
    "max_cards_per_chunk": "每个 Markdown chunk 最多生成多少张候选卡",
    "timeout_seconds": "真实 API 请求超时时间，单位秒",
    "temperature": "真实 API 采样温度，建议 0.0 到 1.0",
    "default_deck": "卡片默认写入的牌组名，支持 :: 表示子牌组",
    "default_note_type": "插件自动创建/使用的笔记类型名称，不建议手动修改",
    "obsidian_vault_path": "未来 Obsidian 整库扫描使用，留空表示暂不使用"
}
```
