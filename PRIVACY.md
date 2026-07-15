# Privacy

AnkiForge AI runs locally as an Anki Desktop add-on. It does not proactively collect telemetry and does not include an AnkiForge account or cloud database.

## Material sent to an AI provider

File selection, drag-and-drop import, example loading, parsing, quality checks, and review state are local. When—and only when—you explicitly click Generate, the current study material and generation instructions are sent to the AI provider and endpoint you configured. The provider may process or retain that content under its own privacy policy and terms; review them before sending sensitive material.

The add-on's local controls do not extend to third-party providers, operating-system logs, Anki, or other software on the device.

## API key

The API key is session-only. It is held in memory for the current add-on window and is not intentionally written to config, logs, documentation, test snapshots, the `.ankiaddon` package, or Anki fields. Closing the window clears the runtime setting. If a key is ever exposed, revoke or rotate it with the provider immediately.

## Anki data

The add-on reads only the Anki metadata needed for the user-selected target and duplicate check. New notes are written only after card review, field mapping, duplicate checking, a write summary, and final confirmation. The normal workflow does not automatically edit or delete existing notes/cards, decks, note types, or fields.

Source labels are shortened and must not contain a complete local path. Internal note IDs used for the current last-write batch are not shown in the normal UI and are not uploaded by AnkiForge AI.

## Files and diagnostics

Markdown, TXT, and DOCX import is local. PDF receives fallback guidance; the add-on does not upload it for parsing, run OCR, or scan an Obsidian vault. User-facing errors should not expose stack traces, complete paths, API keys, or provider response bodies.

Before sharing an issue, screenshot, fixture, or log, remove personal material, complete paths, note IDs, collection data, credentials, and authorization headers.
