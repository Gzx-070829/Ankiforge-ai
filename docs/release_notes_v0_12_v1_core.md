# AnkiForge AI v0.12.0 Public Preview - Card Quality & Review Workflow

Tag: `v0.12.0-public-preview`

AnkiForge AI v0.12 moves the product closer to its v1 core: better generation choices, explainable local quality feedback, explicit review, and clearer safe writing.

## Highlights

- concept, definition, exam, and quick_review card modes
- card count, answer length, and language settings
- mode-aware, maintainable prompts
- deterministic local card quality warnings
- generated cards start unreviewed
- editing immediately re-runs quality checks
- blocking cards cannot be written
- warning cards remain available after manual review
- clearer pre-write and post-write summaries
- normalized mode/source tags and short source labels
- in-memory last-write batch tracking
- Chinese and English product copy

## Safety

- API key is session-only and is not saved
- no automatic AI calls
- no automatic Anki writes
- manual review and final confirmation remain required
- duplicate checking remains mandatory
- possible duplicates are skipped by default
- existing notes/cards, decks, note types, and fields are not modified
- complete local paths are not written to tags or Source fields
- no automatic note/card deletion

## Deferred

Full Undo is deferred. This release records only the last write batch in memory and exposes no delete action. PDF remains fallback guidance and OCR is not included.

## Install

- AnkiWeb add-on code: `1227582295`
- Anki Desktop: Tools → Add-ons → Get Add-ons
- This is an Anki add-on, not a shared deck or web app.

Quality checks help identify common issues but cannot guarantee factual or pedagogical correctness. Manual review remains essential; test with a separate deck first.
