# AnkiWeb draft — AnkiForge AI v0.15.0

## English

AnkiForge AI is an Anki Desktop add-on, **not a shared deck** and not a web app.
Install it in Anki Desktop through **Tools → Add-ons → Get Add-ons** using code
**1227582295**. It does not include pre-made cards; it helps turn your own study
material into reviewable Anki card candidates.

v0.15.0 keeps the simple Create → Review → Write workflow while improving the
internal workbench, source evidence, ready/review/blocked quality feedback,
advisory local near-duplicate hints, and a warmer, quieter interface. Language,
Provider/model, and existing generation choices can be remembered as
non-sensitive preferences. The API key remains **session-only** and is never
saved. Human review, duplicate checking, and final confirmation are required
before cards are written.

Local import supports the documented text, Office, table, HTML/JSON/XML,
Notebook, EPUB, subtitle, and safe-code formats. PDF remains fallback-only in
Core; an advanced local backend must be separately installed and explicitly
selected. The add-on does not scan folders, upload files by itself, install
tools, or contact a Provider before you choose Generate.

## 简体中文

AnkiForge AI 是 **Anki 桌面端插件，不是共享牌组**，也不是网页应用。请在
Anki 桌面端打开 **工具 → 插件 → 获取插件**，输入插件代码 **1227582295**。
它不提供现成卡组，而是帮助你把自己的学习材料转换为可审核的 Anki 候选卡。

v0.15.0 保持简单的 Create → Review → Write 流程，同时完善内部工作台、来源
证据、ready/review/blocked 质量提示、本地近重复提示和更温和安静的界面。
语言、Provider/Model 与现有生成选项可以作为非敏感偏好记住；API key 仍然
只在本次窗口使用，关闭后清除。AI 生成后必须由用户审核，完成查重并最终确认
后才会写入。

本地导入支持文档中列出的文本、Office、表格、HTML/JSON/XML、Notebook、
EPUB、字幕与安全代码格式。PDF 在 Core 中仍是 fallback；高级本地 backend
需要用户另行安装并在当前会话明确选择。插件不会扫描目录、主动上传文件、
自动安装工具，也不会在你点击生成前联系 Provider。
