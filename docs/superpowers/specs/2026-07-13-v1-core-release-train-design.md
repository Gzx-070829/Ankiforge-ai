# AnkiForge AI v1-Core Release Train Design

## Goal

Turn the v0.11 card-generation flow into a safer v0.12 release candidate that helps users choose a generation style, review deterministic quality feedback, understand the exact write plan, and trace cards to a non-sensitive source label.

## Product boundary

The existing product path remains intact:

`CardMakerPanel -> BeginnerFlowSession -> duplicate check -> final confirmation -> MinimalAnkiWriter`

The release adds a pure-Python v1-core below the UI and connects it through small adapters. It does not add automatic provider calls, automatic writes, saved credentials, note-type mutation, existing-note edits, PDF parsing, OCR, accounts, telemetry, or cloud storage.

## Architecture

### Generation settings and prompt profile

`pipeline/generation_settings.py` owns the four card modes and validated in-memory settings. `pipeline/prompt_profile.py` converts settings into a short maintainable prompt profile. Both the current beginner AI draft generator and the legacy prompt builder accept omitted settings and preserve their old call shape.

Card mode is always visible in the UI. Card count, answer length, and output language live in a collapsed generation-settings region. The defaults are concept, balanced, short, and auto.

### Deterministic quality system

`pipeline/card_quality.py` evaluates card text without AI or network access. Results are immutable and contain a score, severity, warning identifiers, and suggestion identifiers. Empty front/back is blocking. Other simple, explainable heuristics are warnings. Batch evaluation adds duplicate-candidate warnings without changing the candidate objects.

The UI resolves warning identifiers through the existing bilingual product copy. Generated cards start unreviewed. Blocking cards cannot be marked for writing. Warning cards remain writable after the user explicitly keeps them. Editing a card rebuilds the quality snapshot and invalidates duplicate/write state.

### Traceability and write summaries

`pipeline/write_traceability.py` owns source types, safe source labels, tag normalization, default tags, pre-write summaries, post-write summaries, and in-memory last-write batch records. Source labels contain only generic text such as `Imported from DOCX` or `Pasted text`, never a full local path. Default tags are `ankiforge`, `ankiforge-ai`, `mode-{mode}`, and `source-{source_type}`.

The minimal writer receives already-normalized tags and adds them to newly created notes only. It does not create fields or mutate note types. Source field content is the short source label when the user maps a Source field.

### Undo decision

This release records only the last successful write batch in memory: snapshot id, created note ids, counts, target deck, tags, and source type. It exposes no delete or undo action. Full undo is deferred because deletion behavior and undo-stack integration cannot be proven safe across supported Anki versions without real-Anki acceptance testing.

### First-run and UI behavior

The existing two-column layout stays. The material empty state explains that this is an add-on, requires the user's own material and API key, keeps the key session-only, requires review and confirmation, and recommends a test deck. Quality status is embedded in each existing review card. Overall quality statistics appear above the card list. The right write section gains a compact summary rather than a new page or wizard.

## Data flow

1. Paste/import updates in-memory material and a safe source type.
2. The user chooses a mode and optionally expands generation settings.
3. Only the explicit Generate action builds a prompt and calls the configured provider.
4. Parsed drafts are evaluated locally and displayed as unreviewed candidates.
5. The user edits, keeps, or discards every candidate. Edits re-run quality checks.
6. The user reads Anki targets and selects existing deck, note type, and fields.
7. Duplicate check remains mandatory and possible duplicates remain skipped.
8. A pre-write summary shows target, mapping, source label, counts, tags, and blocking/warning totals.
9. A second explicit confirmation gates the writer.
10. The result creates a safe post-write summary and in-memory batch record.

## Error and safety handling

- Invalid settings raise clear validation errors before any provider call.
- Unknown card modes never reach prompt construction silently.
- Quality checks never mutate source cards.
- Blocking quality prevents write preparation.
- Any upstream change clears duplicate, confirmation, and write snapshots.
- Safe representations expose counts and enum identifiers, not material, credentials, local paths, or card text.
- Package validation remains the final boundary against config, backups, secrets, caches, tests, docs, and Anki data.

## Testing strategy

New pure-Python tests cover every mode, settings validation, prompt differences, bilingual copy, quality rules, batch duplicate detection, source labels, tag normalization, summaries, batch safety, session re-evaluation, blocking behavior, manual review, confirmation, and writer tags. Existing safety-contract tests remain unchanged unless their expected product behavior is deliberately strengthened. Full unittest, compileall, diff check, archive validation, secret audit, and two deterministic builds are required before commit and again after merge.

## Release boundary

One PR18 commit is preferred. If every release gate passes, the branch may be merged to main, public/main pushed, AnkiWeb updated only through an existing authenticated session without login or CAPTCHA, and release `v0.12.0-public-preview` created. Any listed fuse condition stops the release path.
