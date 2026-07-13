# Write Safety and Traceability

The v0.12 write path keeps the existing hard gates:

1. The user explicitly generates cards.
2. Every candidate is reviewed.
3. An existing deck, note type, and fields are selected.
4. Duplicate checking completes; possible duplicates are skipped by default.
5. A write summary is shown.
6. The user confirms a second time.
7. Only then may new notes be created.

AnkiForge AI does not edit existing notes/cards, create or modify note types, add fields, or change decks.

## Source labels and tags

If a Source field is mapped, the plugin writes a short generic label such as `Pasted text`, `Markdown import`, `TXT import`, or `Imported from DOCX`. It never writes a complete local path.

New notes receive normalized tags:

- `ankiforge`
- `ankiforge-ai`
- `mode-{card_mode}`
- `source-{source_type}`

Tag generation is local, length-limited, and restricted to safe characters. Tags apply only to notes created by the current confirmed write.

## Last write batch and Undo

The current window records the last successful write batch in memory: snapshot id, created note ids, counts, deck, tags, and source type. Safe views expose only structural counts.

Full Undo is deferred. v0.12 exposes no delete button and performs no automatic note/card deletion. Cross-version Anki undo integration and partial failure behavior require real-Anki acceptance work before deletion can be proven safe.
