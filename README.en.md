# AnkiForge AI

AI-powered Anki card maker. Turn study materials into review-ready Anki cards.

[简体中文](README.md)

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
- Generate cards with OpenAI-compatible providers
- DeepSeek support by default
- Review generated cards
- Choose the deck, note type, and field mapping
- Check for duplicates
- Confirm before writing to Anki
- Chinese and English UI

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
