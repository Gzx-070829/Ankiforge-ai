# AnkiForge AI — v0.2 AI Providers

从 Markdown 笔记提取知识点 → AI provider 生成候选卡片 → 人工预览/编辑 → 写入 Anki → 自动套用美化模板。

v0.2 保留 `mock` 作为默认安全 provider，并新增一个通用 `OpenAICompatibleProvider`。DeepSeek 是第一个真实 API 测试目标，但只是 preset，本质仍复用同一套 OpenAI-compatible 请求逻辑。

## v0.2 做了什么

- 默认仍使用 `mock`，不需要 API key，不联网。
- 新增 provider 选项：
  - `mock`
  - `deepseek`
  - `openai_compatible`
- `deepseek` 自动填入默认 API Base URL：`https://api.deepseek.com`，推荐模型：`deepseek-chat`。
- `openai_compatible` 可用于未来 OpenRouter、SiliconFlow、OpenAI 或其他兼容 Chat Completions 的 API。
- 真实 API 调用走后台任务，避免 Anki UI 长时间假死。
- AI 必须返回结构化 JSON：`{"cards":[...]}`。
- 本地 validator 校验 JSON、字段、`basic` card 类型、Front/Back 非空。
- Source 字段仍由本地代码生成，模型不能控制 Source。
- AI 只生成候选卡片；必须人工预览、编辑、勾选，再点击写入。
- 写入层继续保留 Tags 字段同步、Anki tags、Front/Back 校验和重复导入跳过。

## 安装到 Anki 测试

1. 找到 Anki 的插件目录：
   - macOS: `~/Library/Application Support/Anki2/addons21/`
   - Windows: `%APPDATA%\Anki2\addons21\`
   - Linux: `~/.local/share/Anki2/addons21/`
2. 把整个 `ankiforge_ai` 文件夹复制进去。
3. 确认文件夹名保持为 `ankiforge_ai`。
4. 重启 Anki。
5. 顶部菜单 **工具 (Tools) → AnkiForge AI** 打开窗口。

## 测试 mock provider

1. Provider 选择 `mock`。
2. 选择 Markdown 文件。
3. 点击「生成卡片」。
4. 候选卡片进入预览表后，编辑、勾选，再点击「添加到 Anki」。

mock provider 不需要 API key，不会发网络请求。

## 测试 DeepSeek / OpenAI-compatible provider

1. Provider 选择 `deepseek`。
2. 确认 API Base URL 为 `https://api.deepseek.com`。
3. 确认 Model 为 `deepseek-chat`，也可以手动修改。
4. 填入你自己的 API Key。
5. 选择 Markdown 文件，点击「生成卡片」。
6. 等待后台任务完成，候选卡片会进入预览表。
7. 人工编辑、勾选后，再点击「添加到 Anki」。

如果要测试其他 OpenAI-compatible API，选择 `openai_compatible`，手动填写 API Base URL、Model 和 API Key。仓库里的 `config.json` 必须保持 `api_key` 为空字符串，不要提交真实 key。

## 配置

`config.json` 默认示例：

```json
{
    "ai_provider": "mock",
    "model": "mock-v0.2",
    "api_base_url": "",
    "api_key": "",
    "max_cards_per_chunk": 3,
    "timeout_seconds": 60,
    "temperature": 0.2,
    "default_deck": "AnkiForge::Inbox",
    "default_note_type": "AnkiForge Basic",
    "obsidian_vault_path": ""
}
```

## 目录结构

```text
ankiforge_ai/
├── ai/
│   ├── prompts.py
│   ├── schemas.py
│   ├── validators.py
│   └── providers/
│       ├── __init__.py
│       ├── base.py
│       ├── mock_provider.py
│       └── openai_compatible.py
├── anki_writer/
├── importers/
├── theme/
├── ui/
├── config.json
├── config_loader.py
└── manifest.json
```

## 本地测试

这些测试不需要 Anki，也不会联网：

```bash
python -m unittest discover -s tests
```

编译检查：

```bash
python -m compileall ankiforge_ai tests
```

## 不在 v0.2 范围内

- PDF importer
- Obsidian vault 扫描
- cloze note type
- 批量导入
- 为 DeepSeek/OpenRouter/SiliconFlow/OpenAI 分别写重复 provider
