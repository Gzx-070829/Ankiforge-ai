# Getting Started / 新手指南

AnkiForge AI 是 Anki Desktop 插件，不是共享牌组，也不提供现成卡组。它把你自己的材料变成候选卡，并要求你在写入前完成审核、重复检查和最终确认。

## 1. 安装

推荐使用 AnkiWeb 插件代码 `1227582295`：在 Anki 中选择 **工具 → 插件 → 获取插件**，输入代码并重启。详细步骤见[安装说明](installation_ankiweb.md)。

重启后，牌组主页会显示紧凑的 **AnkiForge AI** 入口。也可以从
**工具 → AnkiForge AI** 打开，或按 `Ctrl+Alt+F`；重复调用只会唤回并置顶同一个工作台窗口。

开发候选包应使用独立测试 profile 或测试牌组手动安装，不要用未验收构建替换日常学习环境。

## 2. 配置本次 AI 会话

点击 Header 右侧 **AI 设置**：

1. 选择 DeepSeek 或 OpenAI-compatible Provider；
2. 确认 Model；
3. 输入 API key；
4. 点击“保存本次设置”。

Key 只留在当前窗口内存，不会保存。OpenAI-compatible 的 Base URL 和 Timeout 仅在选择该 Provider 时出现。详情见 [AI 设置与隐私](ai_settings_and_privacy.md)。

## 3. 添加学习材料

你可以粘贴文本、选择或拖入最多 20 个原生支持文件，或打开“使用示例”菜单。v0.14.1 原生支持文本、Markdown、DOCX/PPTX/XLSX、表格、HTML、JSON/XML、Notebook、EPUB、字幕和安全代码文本；PDF 当前只提供 Core fallback，不做内置 OCR。需要时可打开“支持能力”，为当前窗口明确选择已经安装并检测到的 Docling / MarkItDown，或选择本机 Pandoc 可执行文件；选择不保存，也不会自动安装。导入不会自动调用 Provider。粘贴材料仍走原有的一次生成路径；已导入文档才使用有界的本地分析、切块和计划。

第一次使用建议选择内置示例；示例会填入材料并推荐卡片模式，但不会自动生成。

## 4. 选择模式与生成

“卡片模式”始终可见；卡片数量、答案长度和输出语言位于默认收起的生成设置中。公开模式适合概念、定义、考试、快速回顾、对比、流程、公式或易错点。v0.14.1 当前不开放 Cloze 选择；内部兼容检查只负责 fail closed，不会创建或修改笔记类型与字段。已导入文档可选择 Fast、Standard 或 Deep：界面显示当前计划的具体调用数、12 次硬上限和最多 5 张 balanced 候选卡；历史范围不是每次运行的承诺。

检查材料与设置后主动点击生成。此时材料才会发送到你配置的 Provider。

## 5. 审核候选卡

每张卡默认 pending。阅读并编辑 Front/Back，然后明确保留或丢弃。warning 是提醒；blocking 必须修正或丢弃。编辑会重新检查质量，并使旧的 duplicate/write preview 失效。

质量提示不能保证事实正确。请对照材料，并对最终卡片负责。

## 6. 映射、查重和写入

选择已有牌组、笔记类型和 Front/Back 字段；Source 可选。运行重复检查，阅读写入摘要，再执行最终确认。没有保留卡、映射不完整、查重过期或存在 blocking 时不能写入。

第一次写入请使用独立测试牌组，并在 Anki Browser 中检查字段、Tags 和来源标签。

## 7. 获取帮助

Header 的帮助入口解释插件身份、隐私、安全和 PDF 限制。安装或运行异常见[排错指南](troubleshooting.md)。反馈前请删除 API key、私人材料、完整路径和 Anki collection 数据。

## English quick start

Install add-on code `1227582295`, configure session-only AI settings, paste/import your own material, choose a mode, and explicitly generate candidates. Review every card, select an existing Anki target and field mapping, run duplicate checking, inspect the write summary, and confirm the final write. Use a test deck first. PDF is fallback-only; AI output and local quality feedback do not guarantee correctness.
