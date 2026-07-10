# AnkiForge AI

AI-powered Anki card maker. Turn study materials into review-ready Anki cards.

[简体中文](README.md)

> This is an Anki Desktop add-on, not a shared deck or a web app. It does not include pre-made cards; it helps turn your own study material into cards. Do not look for it under Shared Decks.

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
- AnkiForge AI never writes cards automatically.
- Every write requires your confirmation.
- Possible duplicate cards are skipped by default.
- Existing notes, decks, and note types are not modified.

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
