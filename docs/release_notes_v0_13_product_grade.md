# AnkiForge AI v0.13.2 Product-Grade Preview

Target tag: `v0.13.2-product-grade-preview`

Status: release draft only. The PR26 branch candidate validation metadata is recorded below. This document does not authorize a tag, GitHub Release, main push, or AnkiWeb update. Real-Anki acceptance and user sign-off remain required.

AnkiForge AI v0.13 turns the existing safe generation flow into a more complete local AI card workbench while preserving explicit control at every network and Anki boundary.

## Highlights

- Linear Create → Review → Write information architecture
- Session-only AI Settings dialog and clear configured state
- Local examples and first-run Help
- Template-aware concept, definition, exam, quick-review, compare, process, formula, and mistake-trap modes
- Mode/template-aware structured prompts
- Deterministic quality rules with short bilingual guidance
- Offline multidisciplinary card-quality benchmark
- Pending review, edit/copy/restore, conservative bulk actions, and statistics
- Existing-field suggestions and Cloze compatibility checks
- Seven write gates, explainable pre/post summaries, safe tags/source labels, and in-memory last-write tracking
- Product-specific user errors, documentation, governance templates, and release/demo assets

Cloze templates and compatibility checks remain internal and fail closed. Cloze is not publicly selectable in the v0.13.2 UI, and the add-on does not create or modify note types or fields to enable it.

## v0.13 release train

- **PR24 — product-grade workflow:** introduced the Create → Review → Write workbench, templates, deterministic quality feedback, richer review, mapping suggestions, write gates, and product documentation.
- **PR25 — runtime safety hardening:** moved Provider generation onto Anki's background task mechanism with stale-result protection, added a 50,000-character material limit, classified endpoints as allow/confirm/deny, disabled authenticated redirects, bounded Provider error bodies, and hardened plain-text write/duplicate normalization.
- **PR26 — metadata and lifecycle polish:** aligns runtime, internal `version`, Anki-recognized `human_version`, package, README, release, and AnkiWeb draft metadata at 0.13.2; releases MainDialog session state after normal or exceptional exit; prevents duplicate menu registration; and makes the legacy preference loader refuse credential-shaped fields.

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
- Endpoint safety is risk classification plus explicit per-session confirmation, not complete SSRF protection
- Failed requests are not retried automatically, and an already-started network request is not claimed to be cancelled
- Collection writes remain on the existing guarded Anki path; PR26 does not move them into an ordinary worker thread

Quality feedback cannot guarantee factual correctness. Users are responsible for final cards and should complete acceptance in a separate test deck.

## PR26 branch candidate validation

- Unit tests: `1,062 passed`
- Compileall: `passed`
- Diff check: `passed`
- Package files / size: `95 files / 198,058 bytes`
- Package SHA-256: `1499C162147B189C7A1BAAC07822AACFB184FD01DB7B683102523D940D55EB1C`
- Reproducible build: `passed; two consecutive builds matched byte-for-byte`
- Forbidden files: `0`
- Real-Anki acceptance: `<pending user sign-off>`

## Install

- AnkiWeb add-on code: `1227582295`
- Anki Desktop: **Tools → Add-ons → Get Add-ons**
- This is an Anki add-on, not a shared deck or web app.

## 中文摘要

`v0.13.2-product-grade-preview` 汇总 PR24 的 product-grade workflow、PR25 的运行时安全加固和 PR26 的版本/窗口生命周期收口。API key 仍只在会话内使用；AI 生成后必须人工审核，写入前必须查重和最终确认。当前 UI 不开放 Cloze，不自动 retry；Endpoint 防护是风险分类与逐会话确认，不是完整 SSRF 证明。PDF 仍是 fallback。建议先在测试牌组验收。
