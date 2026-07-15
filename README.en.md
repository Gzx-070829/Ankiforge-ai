# AnkiForge AI

Turn your own study material into reviewable, safely writable Anki cards.

[简体中文](README.md)

> This is an Anki Desktop add-on, not a shared deck or web app. It does not include pre-made decks; do not search for it under Shared Decks.

AnkiForge AI is a local-first AI card workbench. You provide the source and learning goal; AI produces candidates only. Local quality checks and manual review come before duplicate checking, a write preview, and final confirmation.

Current candidate: `v0.13.0-product-grade-preview`.

## Quick install

### Install from AnkiWeb

1. Open Anki Desktop.
2. Choose **Tools → Add-ons → Get Add-ons**.
3. Enter add-on code `1227582295`.
4. Restart Anki, then open AnkiForge AI.

[Open the AnkiWeb page](https://ankiweb.net/shared/info/1227582295) · [Full installation guide](docs/installation_ankiweb.md)

### Install from source

```bash
git clone https://github.com/Gzx-070829/Ankiforge-ai.git
```

Copy the `ankiforge_ai` folder into Anki's `addons21` directory and restart Anki.

## Make your first cards

1. Open **AI Settings** in the header, choose a provider and model, and enter your own API key.
2. Paste material, import Markdown / TXT / DOCX, or start with a built-in example.
3. Choose a card mode and generation settings, then explicitly click Generate.
4. Edit, keep, or discard every candidate. A blocking card must be fixed or discarded.
5. Select an existing deck, note type, and field mapping, then run duplicate checking.
6. Inspect the write summary and confirm the final write. Start with a separate test deck.

[Getting started](docs/getting_started.md)

## Product capabilities

- Paste text or choose/drop Markdown, TXT, and DOCX files
- Safe PDF fallback guidance; no OCR or full PDF text extraction
- DeepSeek and OpenAI-compatible providers in a dedicated AI Settings dialog
- `concept`, `definition`, `exam`, `quick_review`, `compare_contrast`, `process_steps`, `formula_rule`, `mistake_trap`, and restricted `cloze_candidate` modes
- Template-aware prompts plus card-count, answer-length, and output-language controls
- Fully local deterministic card-quality checks and a multidisciplinary benchmark
- A pending → edit/copy/restore → keep/discard Review workbench
- Front / Back / Source field suggestions without adding fields or mutating note types
- Duplicate checking, write summaries, final confirmation, safe source labels, tags, and last-write summaries
- Chinese and English UI, reproducible `.ankiaddon` builds, and forbidden-file auditing

## Safety and privacy

- The API key is session-only and used only for the current session. It is never written to config, logs, documentation, or the package.
- There are no automatic AI calls. Material reaches the selected provider only after you click Generate.
- AI output is a set of candidates and always requires manual review.
- There are no automatic Anki writes. Duplicate checking and final confirmation are required before writing.
- Possible duplicates are skipped by default. Existing notes/cards, decks, note types, and fields are not automatically modified or deleted.
- File import is local. The add-on does not upload files or scan an Obsidian vault.
- Quality feedback cannot guarantee factual correctness or learning effectiveness. You are responsible for the final cards.
- Full Undo is deferred. The current window tracks only the last write batch and exposes no automatic delete action.

[AI settings and privacy](docs/ai_settings_and_privacy.md) · [Write safety and traceability](docs/write_safety_and_traceability.md) · [Privacy policy](PRIVACY.md) · [Security reporting](SECURITY.md)

## Documentation

- [Installation and first run](docs/getting_started.md)
- [Importing study material](docs/importing_materials.md)
- [Card modes and templates](docs/card_modes_and_templates.md)
- [Card quality system](docs/card_quality_system.md)
- [Review workbench](docs/review_workbench.md)
- [Field mapping](docs/field_mapping.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Manual Anki acceptance](docs/manual_anki_acceptance.md)
- [Future roadmap](docs/future_roadmap.md)

## Development and contribution

```bash
python -m unittest discover
python -m compileall .
python scripts/build_ankiaddon.py
git diff --check
```

Bug fixes, documentation improvements, and sanitized card-quality fixtures are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md); report security issues privately as described in [SECURITY.md](SECURITY.md).

## Status

This is a product-grade preview for real-user acceptance. It still requires per-card review and is not an unattended workflow. A public release also requires real-Anki installation, duplicate, cancel-confirmation, and test-deck write acceptance.
