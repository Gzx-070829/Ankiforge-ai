# AnkiForge AI

把自己的学习材料变成可审核、可安全写入的 Anki 卡片。

[English](README.en.md)

> 这是 Anki 桌面端插件，不是共享牌组，也不是网页服务。它不提供现成卡组；请不要在 Shared Decks 中搜索。

AnkiForge AI 是一个本地优先、中文优先的 AI 制卡工作台。你提供材料、选择学习目标，AI 只生成候选卡；本地质量检查和人工审核完成后，插件才会进入重复检查、写入预览和最终确认。

当前候选版本：`v0.13.2-product-grade-preview`。

## 快速安装

### 通过 AnkiWeb

1. 打开 Anki Desktop。
2. 选择 **工具 → 插件 → 获取插件**。
3. 输入插件代码 `1227582295`。
4. 安装后重启 Anki，再打开 AnkiForge AI。

[打开 AnkiWeb 页面](https://ankiweb.net/shared/info/1227582295) · [完整安装说明](docs/installation_ankiweb.md)

### 从源码安装

```bash
git clone https://github.com/Gzx-070829/Ankiforge-ai.git
```

将 `ankiforge_ai` 文件夹复制到 Anki 的 `addons21` 目录，然后重启 Anki。

## 第一次制卡

1. 在右上角打开 **AI 设置**，选择 Provider 和 Model，输入自己的 API key。
2. 粘贴材料，或导入 Markdown / TXT / DOCX；也可以先使用内置示例。
3. 选择卡片模式和生成设置，主动点击生成。
4. 逐张编辑、保留或丢弃候选卡。blocking 卡必须先修正或丢弃。
5. 选择已有牌组、笔记类型和字段映射，执行重复检查。
6. 查看写入摘要，并在最终确认后写入。建议第一次使用独立的测试牌组。

[新手指南](docs/getting_started.md)

## 产品能力

- 粘贴文本，以及 Markdown / TXT / DOCX 选择和拖拽导入
- PDF 安全 fallback：当前不做 OCR，也不提取 PDF 正文
- DeepSeek 与 OpenAI-compatible Provider；AI 设置留在独立 Modal
- `concept`、`definition`、`exam`、`quick_review`、`compare_contrast`、`process_steps`、`formula_rule` 和 `mistake_trap` 八种公开模式；Cloze 仅保留内部 fail-closed 兼容检查，当前 UI 不开放
- 模板感知的生成提示，以及卡片数量、答案长度和输出语言控制
- 完全本地、确定性的 card-quality 检查与多学科 benchmark
- pending → 编辑/复制/还原 → 保留/丢弃的 Review 工作台
- Front / Back / Source 字段建议；不自动新增字段或修改笔记类型
- 重复检查、写入摘要、最终确认、来源标签、Tags 和最后写入批次摘要
- 中英文界面、可复现 `.ankiaddon` 打包和 forbidden-file 审计

## 安全与隐私

- API key 仅在本次会话使用，保持 session-only，不写入 config、日志、文档或安装包。
- 插件不会自动调用 AI；只有你点击生成后，当前材料才会发送给所选 Provider。
- AI 生成的只是候选卡，必须经过人工审核。
- 插件不会自动写入 Anki；写入前必须完成重复检查和最终确认。
- 可能重复的卡默认跳过；不会自动修改或删除已有 notes/cards、牌组、笔记类型或字段。
- 文件导入在本地完成；插件不上传文件，也不扫描 Obsidian vault。
- 质量提示不能保证事实正确或学习效果，你需要对最终卡片负责。
- 完整 Undo 仍未开放；当前只记录本次窗口的最后写入批次，不提供自动删除入口。

[AI 设置与隐私](docs/ai_settings_and_privacy.md) · [写入安全与追踪](docs/write_safety_and_traceability.md) · [隐私政策](PRIVACY.md) · [安全报告](SECURITY.md)

## 文档

- [安装与首次使用](docs/getting_started.md)
- [导入学习材料](docs/importing_materials.md)
- [卡片模式与模板](docs/card_modes_and_templates.md)
- [卡片质量系统](docs/card_quality_system.md)
- [审核工作台](docs/review_workbench.md)
- [字段映射](docs/field_mapping.md)
- [常见问题与排错](docs/troubleshooting.md)
- [人工 Anki 验收](docs/manual_anki_acceptance.md)
- [未来路线图](docs/future_roadmap.md)

## 开发与贡献

```bash
python -m unittest discover
python -m compileall .
python scripts/build_ankiaddon.py
git diff --check
```

欢迎提交 bug、文档改进和脱敏的 card-quality fixture。请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)，安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。

## 状态

这是面向真实用户验收的 product-grade preview，仍要求逐张审核，不能无人值守运行。公开发布前仍需真实 Anki 安装、重复检查、取消确认和测试牌组写入验收。
