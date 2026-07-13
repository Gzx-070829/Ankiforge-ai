# AnkiForge AI

AI-powered Anki card maker. Turn study materials into review-ready Anki cards.

[简体中文](README.md)

> This is an Anki Desktop add-on, not a shared deck or a web app. It does not include pre-made cards; it helps turn your own study material into cards. Do not look for it under Shared Decks.

## v0.12 core workflow

- Four card modes: `concept`, `definition`, `exam`, and `quick_review`
- Card count, answer length, and output-language settings
- A local deterministic card quality assistant for empty content, generic questions, long answers, multiple points, and Markdown residue
- Generated cards start unreviewed; explicitly keep or discard every card
- Blocking cards cannot be written; warning cards remain writable after review
- A pre-write summary for deck, note type, field mapping, source, quality counts, duplicate behavior, and tags
- Default tags for AnkiForge, card mode, and safe source type
- Short source labels that never include a full local path

Quality checks are explainable local heuristics, not a guarantee that AI-generated content is correct. Review every card and start with a test deck.

## Install

### Option 1: Install from AnkiWeb

Add-on code:

```text
1227582295
```

In Anki, open:

**Tools → Add-ons → Get Add-ons**

Paste the add-on code `1227582295`. After installation, restart Anki and open AnkiForge AI.

AnkiWeb page: [https://ankiweb.net/shared/info/1227582295](https://ankiweb.net/shared/info/1227582295)

### Option 2: Install from source

1. Clone the repository:

   ```bash
   git clone https://github.com/Gzx-070829/Ankiforge-ai.git
   ```

2. Copy the `ankiforge_ai` folder into Anki's `addons21` folder.
3. Restart Anki.

## Features

- Paste Markdown or text study material
- Drop or choose `.md`, `.markdown`, `.txt`, and `.docx` files
- DOCX text import (images, formulas, and complex layout are not preserved)
- Recognize `.pdf` files and fail safely; this build does not bundle a PDF parser
- Generate cards with OpenAI-compatible providers
- DeepSeek support by default
- Review generated cards
- Re-run local quality checks after editing a card
- Choose the deck, note type, and field mapping
- Check for duplicates
- Confirm before writing to Anki
- Chinese and English UI

## File import notes

- Markdown / TXT: preserves the original text structure, up to 5 MB per file.
- DOCX: uses a built-in pure-Python text extractor for paragraphs and simple tables. Images, formulas, comments, and complex styling are not imported.
- PDF: fallback-only in this build. You can choose or drop a `.pdf`, but the plugin will ask you to copy selectable text or convert it to TXT / Markdown first. OCR, scanned PDFs, and complex PDF layout are not supported.
- When multiple files are dropped, only the first is imported and a notice is shown.
- If material already exists, the imported file is appended with a filename separator; existing input is never silently overwritten.

File import only updates the study-material text box. It never calls AI or writes to Anki automatically. See the [file import guide](docs/file_import.md).

## Safety

- Your API key is used only for the current session and is not saved.
- The API key remains session-only and is never written to config, logs, or the package.
- AI is called only when you click Generate Cards.
- AnkiForge AI never writes cards automatically.
- Every write requires your confirmation.
- Possible duplicate cards are skipped by default.
- Existing notes, decks, and note types are not modified.
- Full Undo is not exposed in v0.12. The current window only tracks the last write batch and provides no automatic delete action.

Details: [Card quality system](docs/card_quality_system.md) · [Review workbench](docs/review_workbench.md) · [Write safety and traceability](docs/write_safety_and_traceability.md)

## Development

Run the unit tests:

```bash
python -m unittest discover -s tests
```

Compile all Python sources:

```bash
python -m compileall .
```

## Status

AnkiForge AI is an early local/self-use version. Public feedback is welcome.
