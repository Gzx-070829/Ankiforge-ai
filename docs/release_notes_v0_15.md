# AnkiForge AI v0.15.0 Release Candidate

v0.15.0 strengthens the internals and review feedback while keeping the public
Create → Review → Write flow compact.

## Highlights

- A pure-Python **workbench application core** now owns immutable session state,
  invalidation rules, generation lifecycle, review use cases, and guarded write
  coordination behind the existing Qt surface.
- One public card-quality contract: **ready / review / blocked**. It is local,
  deterministic guidance and never claims factual correctness.
- Bounded **source evidence** preserves only honest, display-safe location hints
  through edit, copy, and restore.
- Advisory local **near-duplicate** evidence identifies the paired candidate and
  reason while keeping every card visible for the user to decide.
- A versioned offline Chinese/English quality benchmark now records deterministic
  per-card expectations and duplicate classifications.
- Strictly allowlisted **non-sensitive preferences** remember language,
  Provider/model, and existing generation choices under `user_files`.
- The UI now uses **Warm Charcoal + Soft Orange** with quieter surfaces, fewer
  decorative borders, clear focus, and no new controls.

## Safety preserved

- API keys and custom endpoints remain session-only; neither enters preferences.
- Generation starts only after an explicit user action.
- Manual review, the collection duplicate check, and final confirmation remain
  required.
- Candidate similarity is local advisory evidence; the collection check remains
  the pre-write authority.
- Collection operations were not moved to an ordinary background thread.
- Existing notes, decks, note types, and fields are not changed by this train.

## Boundaries

PDF remains fallback-only in Core unless the user separately installs and
explicitly selects a local backend. Cloze is not publicly selectable. There is
no new Provider retry, OCR, cloud service, telemetry, or unattended workflow.
Source and quality feedback are review aids, not proof.

This is a release candidate. Real-Anki startup, high-DPI UI, import, Provider,
review, duplicate, cancelled-write, and test-deck write acceptance remain
required before a public release decision.
