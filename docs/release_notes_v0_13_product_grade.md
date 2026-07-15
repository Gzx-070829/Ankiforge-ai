# AnkiForge AI v0.13.0 Product-Grade Preview

Target tag: `v0.13.0-product-grade-preview`

Status: release draft only. The release-candidate build metadata is recorded below, but this document does not authorize a tag, GitHub Release, main push, or AnkiWeb update. Real-Anki acceptance and user sign-off remain required.

AnkiForge AI v0.13 turns the existing safe generation flow into a more complete local AI card workbench while preserving explicit control at every network and Anki boundary.

## Highlights

- Linear Create → Review → Write information architecture
- Session-only AI Settings dialog and clear configured state
- Local examples and first-run Help
- Template-aware concept, definition, exam, quick-review, compare, process, formula, mistake-trap, and restricted Cloze candidate modes
- Mode/template-aware structured prompts
- Deterministic quality rules with short bilingual guidance
- Offline multidisciplinary card-quality benchmark
- Pending review, edit/copy/restore, conservative bulk actions, and statistics
- Existing-field suggestions and Cloze compatibility checks
- Seven write gates, explainable pre/post summaries, safe tags/source labels, and in-memory last-write tracking
- Product-specific user errors, documentation, governance templates, and release/demo assets

## Import support

Pasted text, Markdown, TXT, drag-and-drop, and basic DOCX text extraction are local. A single Obsidian Markdown file is treated as ordinary Markdown without vault scanning. PDF remains fallback guidance: no OCR, network parser, or full PDF text extraction.

## Safety

- API key is session-only and is not saved or logged
- No automatic AI calls
- AI-generated cards require manual review
- No automatic Anki writes
- Duplicate checking and final confirmation remain hard gates
- Possible duplicates are skipped by default
- Existing notes/cards, decks, note types, and fields are not automatically modified or deleted
- No account, cloud database, telemetry, or background file upload
- Full Undo remains deferred

Quality feedback cannot guarantee factual correctness. Users are responsible for final cards and should complete acceptance in a separate test deck.

## Validation placeholders

- Unit tests: `996 passed`
- Compileall: `passed`
- Diff check: `passed`
- Package files / size: `90 files / 186,297 bytes`
- Package SHA-256: `EBB2263E11C531316D09DC15B092F8DEBEBA67A39D7ED6FA8F5D23492B3B0C52`
- Reproducible build: `passed; two consecutive builds matched byte-for-byte`
- Forbidden files: `0` required
- Real-Anki acceptance: `<pending user sign-off>`

## Install

- AnkiWeb add-on code: `1227582295`
- Anki Desktop: **Tools → Add-ons → Get Add-ons**
- This is an Anki add-on, not a shared deck or web app.

## 中文摘要

`v0.13.0-product-grade-preview` 将产品升级为 Create → Review → Write 本地制卡工作台，新增模板、示例、质量 benchmark、更完整审核、字段建议、写入 gate、帮助和开源治理材料。API key 仍只在会话内使用；AI 生成后必须人工审核，写入前必须查重和最终确认。PDF 仍是 fallback。建议先在测试牌组验收。
