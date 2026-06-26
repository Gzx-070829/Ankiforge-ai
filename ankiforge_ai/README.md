# AnkiForge AI — v0.1 (MVP 骨架)

从 Markdown 笔记提取知识点 → AI 生成卡片 → 人工预览/编辑 → 写入 Anki → 自动套用美化模板。

当前版本 v0.1：AI 制卡部分是 **mock（模拟）数据**，还没有接入真实的 AI API；
目的是先把"选文件 → 解析 → 预览编辑 → 写入 → 美化"这条完整链路跑通、跑稳，
再在这个骨架上接入真实 AI 调用、Obsidian 整库扫描、PDF 导入。

## 怎么安装到 Anki 里测试

1. 找到 Anki 的插件目录：
   - macOS: `~/Library/Application Support/Anki2/addons21/`
   - Windows: `%APPDATA%\Anki2\addons21\`
   - Linux: `~/.local/share/Anki2/addons21/`
2. 把整个 `ankiforge_ai` 文件夹复制进去（文件夹名必须保持 `ankiforge_ai`，
   和 `manifest.json` 里的 `package` 字段一致）。
3. 重启 Anki。
4. 顶部菜单 **工具 (Tools) → AnkiForge AI**，应该能看到弹出的窗口。

## 测试流程

1. 点击「选择 Markdown 文件...」，选一个 `.md` 文件（按 `#`/`##` 标题切分）。
2. 点击「生成卡片」——目前会用模拟逻辑给每个标题生成一张卡（不联网）。
3. 在表格里直接编辑 Front / Back / Extra 文字（可选）。
4. 取消勾选你不想要的卡片。
5. 填好牌组名，点击「添加到 Anki」。
6. 去 Anki 浏览器里查看新牌组 `AnkiForge::Inbox`（或你自定义的名字），
   笔记类型应该是 `AnkiForge Basic`，卡片外观应用了 `theme/style.css` 里的样式
   （正反面配色、暗色模式都已经适配）。

## 目录结构

```
ankiforge_ai/
├── __init__.py              # 插件入口，注册 Tools 菜单
├── manifest.json             # Anki 插件元数据
├── config.json / config.md   # 插件配置（API key、默认牌组等，v0.1 暂未使用 API key）
├── ui/
│   └── main_dialog.py        # 主窗口：选文件、生成、可编辑预览表、写入
├── importers/
│   └── md_importer.py        # 按标题切分 Markdown（无 Anki 依赖，可单独单测）
├── ai/
│   └── schemas.py             # GeneratedCard 数据结构 + mock_generate_cards()
├── anki_writer/
│   ├── note_types.py          # 创建/确保 "AnkiForge Basic" 笔记类型 + 模板
│   └── add_cards.py           # 把已审核的卡片写入指定牌组
└── theme/
    └── style.css               # 卡片外观样式（独立文件，改样式不用碰 Python）
```

设计上特意把 `importers/md_importer.py` 和 `ai/schemas.py` 的核心逻辑做成
**不依赖 `aqt`**，所以可以直接用 `python3` 跑单测，不用每次开 Anki 验证逻辑。

## 下一步（建议顺序）

1. **v0.2 - 接入真实 AI API**：把 `ai/schemas.py` 里的 `mock_generate_cards()`
   换成对 AI API 的真实调用，用 structured output / JSON Schema 约束返回格式，
   函数签名 `(chunk) -> List[GeneratedCard]` 保持不变，UI 不用改。
2. **v0.2 - Obsidian 整库扫描**：在 `importers/` 下新增一个模块，递归扫描
   vault 目录下所有 `.md`，按文件夹/标签生成 Anki tag。
3. **v0.3 - PDF 支持**：新增 `importers/pdf_importer.py`，提取文本+页码，
   `source` 字段带上页码信息。
4. **v0.4 - 界面美化深化**：在 `theme/style.css` 基础上做更多排版/配色细化，
   如果要做 Anki 编辑器/复习界面的局部增强，再考虑 webview hook。

## 如果你想继续用 Codex CLI 迭代

可以在这个项目目录下运行 `codex`，然后描述你要加的功能，例如：

> 在 ai/schemas.py 里新增一个 generate_cards_via_api() 函数，
> 调用 OpenAI 的 chat completions API，用 structured outputs
> 强制返回 JSON，schema 对应 GeneratedCard 的字段。
> 函数签名保持 (chunk) -> List[GeneratedCard] 不变，
> 在 ui/main_dialog.py 里加一个开关，让用户选择用 mock 还是真实 API。

骨架已经按这种"替换单个函数、不改其他模块"的方式设计，方便后续逐步替换。
