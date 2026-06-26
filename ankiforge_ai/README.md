# AnkiForge AI — v0.1.2 Polish

从 Markdown 笔记提取知识点 → 本地 mock 生成卡片 → 人工预览/编辑 → 写入 Anki → 自动套用美化模板。

v0.1.2 仍然不接真实 AI API，不发网络请求，也不要求 API key。这个版本在 v0.1.1 已验收通过的链路上做小范围 polish：显示更整洁、写入更稳、重复导入更安全。

## v0.1.2 做了什么

- 保留 mock AI generation 作为默认且唯一启用的生成方式。
- 保留轻量 provider abstraction：
  - `ai/providers/base.py`
  - `ai/providers/mock_provider.py`
  - `ai/providers/__init__.py`
- 预留 OpenAI、DeepSeek、SiliconFlow / 硅基流动、OpenRouter、其他 OpenAI-compatible API 的扩展位置，但本版本不实现真实调用。
- 加强 Markdown splitting：支持标题前内容，跳过空 chunk，避免把 fenced code block 里的 `#` 误判为标题。
- 写入前校验已勾选卡片的 Front / Back，空字段不会写入 Anki。
- 写入时同步 `Tags` 字段，同时继续写入 Anki 真实 tags。
- 新生成卡片的 Source 显示为 `filename.md > Heading`，避免完整本地路径过长。
- 重复导入时跳过同 note type、同 Front、同 Source 的卡片；不会删除、覆盖或修改已有 notes/cards。
- 增加「清空预览」按钮，只清空当前窗口候选卡片，不影响已写入 Anki 的内容。
- 加强错误提示，读文件、生成、写入失败时会弹出更明确的提示。
- 加强 note type 维护：`AnkiForge Basic` 已存在时也会补齐字段、模板并同步 `theme/style.css`。
- 添加不依赖 Anki、不依赖网络的纯 Python 测试。

## 怎么安装到 Anki 里测试

1. 找到 Anki 的插件目录：
   - macOS: `~/Library/Application Support/Anki2/addons21/`
   - Windows: `%APPDATA%\Anki2\addons21\`
   - Linux: `~/.local/share/Anki2/addons21/`
2. 把整个 `ankiforge_ai` 文件夹复制进去。
3. 确认文件夹名保持为 `ankiforge_ai`，和 `manifest.json` 里的 `package` 字段一致。
4. 重启 Anki。
5. 顶部菜单 **工具 (Tools) → AnkiForge AI** 打开窗口。

## 测试流程

1. 点击「选择 Markdown 文件...」，选择一个 `.md` 文件。
2. 点击「生成卡片」。
3. 在表格里编辑 Front / Back / Extra / Source。
4. 取消勾选不想写入的卡片。
5. 确认已勾选卡片的 Front 和 Back 都不为空。
6. 填好目标牌组，点击「添加到 Anki」。
7. 弹窗会提示新增数量，以及是否跳过重复卡片。
8. 去 Anki 浏览器里查看新牌组 `AnkiForge::Inbox` 或你自定义的牌组。

## 配置

`config.json` 当前示例：

```json
{
    "ai_provider": "mock",
    "model": "mock-v0.1.2",
    "api_base_url": "",
    "max_cards_per_chunk": 3,
    "default_deck": "AnkiForge::Inbox",
    "default_note_type": "AnkiForge Basic",
    "obsidian_vault_path": ""
}
```

说明：

- `ai_provider`：v0.1.2 只支持 `mock`。
- `model`：当前为 `mock-v0.1.2`，未来真实 provider 可使用模型名。
- `api_base_url`：当前留空，未来 OpenAI-compatible provider 可使用。
- `max_cards_per_chunk`：当前 mock provider 固定每个 chunk 生成 1 张卡，字段先为未来保留。
- 本版本没有 `api_key` 配置项。

## 目录结构

```text
ankiforge_ai/
├── __init__.py
├── manifest.json
├── config.json / config.md
├── config_loader.py
├── ui/
│   └── main_dialog.py
├── importers/
│   └── md_importer.py
├── ai/
│   ├── schemas.py
│   └── providers/
│       ├── __init__.py
│       ├── base.py
│       └── mock_provider.py
├── anki_writer/
│   ├── note_types.py
│   └── add_cards.py
└── theme/
    └── style.css
```

## 本地测试

这些测试不需要 Anki，也不会联网：

```bash
python -m unittest discover -s tests
```

## 后续方向

v0.2 可以在 `ai/providers/` 下新增真实 provider，例如 OpenAI-compatible provider。建议保持 provider 对外接口为：

```python
provider.generate_cards(chunk) -> List[GeneratedCard]
```

这样 UI、Markdown importer 和 Anki writer 都不需要知道底层 provider 是 mock、OpenAI、DeepSeek、SiliconFlow、OpenRouter，还是其他兼容接口。
