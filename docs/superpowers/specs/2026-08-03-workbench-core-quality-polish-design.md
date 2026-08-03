# AnkiForge AI Workbench Core and Quality Polish Design

**Date:** 2026-08-03
**Target branch:** `codex/v0.15.0-workbench-core-quality-polish`
**Status:** Approved design awaiting implementation plan

## 1. Goal

Strengthen AnkiForge AI's internal architecture, reliability, and card-quality
tooling without making the product harder to use. The visible workflow remains:

`Create -> Review -> Write`

Internal capability may become more sophisticated, but the default interface
must become simpler, quieter, and easier to understand. After the core migration
is stable, the product UI adopts the approved warm-charcoal and soft-orange
visual direction.

## 2. Product Principles

1. **Complex inside, simple outside.** Internal analysis must not create a new
   settings burden.
2. **Human control remains a hard gate.** Provider calls, review decisions,
   duplicate checks, final confirmation, and Anki writes keep their existing
   explicit boundaries.
3. **No big-bang rewrite.** Every migration step leaves the add-on runnable and
   preserves compatibility facades until callers are moved safely.
4. **Local-first quality.** New quality and near-duplicate checks are
   deterministic, bounded, and do not add Provider calls, embeddings, downloads,
   telemetry, or cloud services.
5. **Anki owns the collection.** Collection reads and writes remain on
   Anki-supported execution paths. They must never be moved to an ordinary
   background thread.
6. **Secrets stay ephemeral.** API keys remain memory-only for the current main
   window and never enter preferences, files, logs, exceptions, snapshots,
   tests, packages, or Anki fields.

## 3. Scope

### 3.1 Architecture and reliability

- Introduce a small `ankiforge_ai.workbench` application layer.
- Establish one explicit immutable session state and narrow state transitions.
- Move orchestration out of large Qt widgets into testable coordinators and use
  cases.
- Split the current create, review, generation, and write responsibilities by
  bounded context.
- Preserve public entry points and temporary re-export facades during migration.
- Add CI for supported Python syntax, unit tests, compilation, packaging, and
  forbidden-file validation.
- Archive or clearly label historical internal documentation so current user and
  contributor guidance remains easy to find.
- Persist a strict allowlist of non-sensitive preferences only.

### 3.2 Card quality

- Normalize precise source locations when the importer can provide them.
- Add deterministic card-quality assessments with a small public severity model.
- Add bounded local near-duplicate detection for candidates in the current run.
- Keep the existing collection duplicate check as the authoritative pre-write
  check.
- Add a versioned offline benchmark with sanitized Chinese and English fixtures
  from multiple study domains.
- Record only aggregate in-memory review outcomes for the active session so the
  workbench can summarize accepted, edited, rejected, and blocked candidates.

### 3.3 Final visual pass

- Apply the approved warm-charcoal and soft-orange palette after the
  architecture and quality work passes verification.
- Reduce decorative borders, normalize radii and spacing, and simplify visual
  hierarchy without changing layout or workflow.
- Keep product QSS, style tokens, dialogs, and mock previews synchronized.

## 4. Non-goals

This train does not add:

- native PDF parsing or OCR;
- image, audio, video, ASR, web, or URL import;
- bundled third-party tools, models, or automatic installation;
- automatic Provider calls, background retries, or unattended generation;
- persisted API keys, custom endpoint credentials, or full request payload logs;
- public Cloze selection;
- embeddings, vector databases, or claims of true semantic deduplication;
- a new Anki scheduler, mobile application, cloud account, or shared-deck service;
- full undo or deletion by tag/deck;
- a replacement UI framework or a redesigned overall layout.

## 5. Target Architecture

### 5.1 UI layer

The Qt UI renders state and emits user intent. It does not implement Provider
requests, document analysis, quality rules, duplicate algorithms, or Anki write
decisions.

The main workbench remains the only public surface and composes three bounded
sections:

- `CreateSection`: material/import state, card mode, generation settings, and
  explicit Generate intent;
- `ReviewSection`: progress, candidate cards, source evidence, quality summary,
  and review decisions;
- `WriteSection`: Anki target, field mapping, duplicate status, write summary,
  and explicit final confirmation.

These section names describe boundaries, not three new pages. The current
two-column workbench layout remains.

### 5.2 Workbench application layer

`ankiforge_ai.workbench` owns orchestration and exposes small testable units:

- `models.py`: immutable session state and value objects;
- `transitions.py`: validated state transitions;
- `create_use_cases.py`: import selection, active material, and generation
  preparation;
- `generation_coordinator.py`: request identity, progress reduction, cancellation
  intent, terminal outcomes, and stale-result rejection;
- `review_use_cases.py`: candidate edits, keep/discard decisions, quality and
  source summaries;
- `write_use_cases.py`: mapping readiness, duplicate readiness, and creation of an
  immutable write preparation object;
- `preferences.py`: allowlisted non-sensitive preference projection.

This is not a generic event bus, dependency-injection framework, or Redux clone.
Functions and small coordinators are preferred over abstract base classes unless
an existing external boundary already requires an interface.

### 5.3 Domain layer

Existing pure-Python packages remain authoritative:

- `document`: safe local parsing and DocumentIR;
- `intelligence`: analysis, chunking, planning, source-aware generation plans;
- `pipeline`: Provider contracts, card models, quality, mapping, and safety gates;
- `anki_writer`: duplicate comparison and bounded write execution.

The workbench layer composes these modules but does not duplicate their rules.

### 5.4 Adapter layer

Side effects remain behind narrow adapters:

- local file selection and import;
- Provider HTTP execution;
- Anki collection read/write operations;
- non-sensitive preference storage;
- Qt scheduling and presentation.

The Provider adapter receives explicit runtime settings and material only after
Generate. The Anki adapter receives an immutable write preparation only after
review, mapping, duplicate checking, and final confirmation.

## 6. Session State

`WorkbenchSessionState` is an immutable dataclass composed of bounded child
states:

- `MaterialState`
- `GenerationState`
- `ReviewState`
- `WriteState`
- `SessionPreferenceState`

Each child state has explicit status values rather than loosely related booleans.
Transitions reject impossible combinations, including:

- generated candidates without active material;
- write readiness before review completion;
- a successful duplicate check for a stale mapping or candidate set;
- write authorization after candidates, target, note type, or fields change;
- a terminal callback whose request ID is no longer current.

Sensitive runtime settings are held separately from serializable session state.
The state representation and debug output must never include API-key text.

## 7. End-to-end Data Flow

1. The user pastes or explicitly selects local material.
2. Import adapters produce DocumentIR and normalized source metadata.
3. The create use case validates limits and creates an immutable generation
   preparation.
4. The generation coordinator starts an explicit request with a unique request
   ID and reduces progress events into session state.
5. Provider output is parsed into candidate cards and passed through local
   quality, source, coverage, and near-duplicate checks.
6. The review section shows a compact result. The user edits, keeps, or discards
   every candidate.
7. The write use case creates a write preparation only when target and field
   mapping are valid.
8. The existing collection duplicate check runs on the appropriate Anki path.
9. The UI presents the final write summary and asks for confirmation.
10. The writer executes the bounded batch and returns a per-card result summary.

Any material, candidate, mapping, or target change invalidates downstream state
through a transition instead of scattered widget callbacks.

## 8. Source Traceability

Introduce or normalize a pure `SourceSpan` value with:

- stable in-session document ID;
- display-safe source name (basename only);
- locator kind, such as section, page, slide, sheet, row, line, cell, or block;
- normalized locator value;
- DocumentIR block ID;
- optional character start/end offsets when trustworthy;
- short display label.

Rules:

- Full local paths are not shown in cards, Provider payloads, tags, logs, or
  diagnostics.
- Importers only claim precision they actually possess.
- Source locations remain review evidence, not proof of factual correctness.
- A candidate without a reliable location may use a document-level source label;
  it must not fabricate a page or paragraph.
- Editing a card preserves its source metadata unless the source itself changes.

## 9. Quality Model

The public result model has only three severities:

- `ready`: no blocking local issue found;
- `review`: the user should inspect one or more warnings;
- `blocked`: the candidate cannot enter the write-ready set.

Internal rules may detect:

- empty or malformed fields;
- overly broad or multi-part questions;
- excessively long answers;
- missing context or ambiguous pronouns;
- answer leakage in the front;
- unsupported or malformed Cloze syntax;
- weak or missing source evidence;
- exact and near duplicate candidates;
- coverage imbalance and repeated knowledge points.

The UI shows one concise summary by default. Rule IDs and explanations live in an
expandable detail area. There are no new quality toggles or threshold controls in
the public UI.

Quality checks do not claim to verify truth. Human review remains mandatory.

## 10. Local Near-duplicate Detection

Candidate near-duplicate detection is local, deterministic, and bounded to the
active generation result. It uses normalized text and inexpensive signals such
as token overlap and character n-gram similarity. Thresholds are internal and
covered by fixtures.

It must:

- avoid external embeddings and additional Provider calls;
- run within a bounded candidate limit;
- distinguish exact duplicate, likely near duplicate, and unrelated;
- identify the paired candidate and reason for review;
- never delete or silently discard a candidate;
- remain advisory until the user decides;
- leave the existing collection duplicate check unchanged and authoritative.

Documentation must call this "near-duplicate detection," not semantic dedup.

## 11. Offline Quality Benchmark

Add sanitized, versioned fixtures representing at least:

- Chinese conceptual material;
- English conceptual material;
- definitions and terminology;
- process/sequence material;
- compare-and-contrast material;
- formulas or rules represented as text;
- exam-style traps;
- deliberately ambiguous, overlong, multi-part, and duplicate candidates.

The benchmark reports deterministic rule outcomes, severity, score/rank when
applicable, and coverage expectations. It contains no real user data, API keys,
copyrighted document dumps, or live Provider dependency.

CI uses the benchmark as a regression contract. It is not presented as an
academic accuracy score or a substitute for human evaluation.

## 12. Non-sensitive Preferences

Persist only a strict allowlist in Anki's preserved add-on `user_files` area:

- UI language;
- Provider name;
- model name;
- last public card mode;
- card count preset;
- answer length preset;
- output language choice;
- intelligence level.

Do not persist:

- API key, token, password, Authorization/Bearer value, cookie, or secret;
- custom Base URL or local/private endpoint;
- pasted/imported material or file paths;
- candidate card content, source spans, review decisions, or write history;
- raw Provider request/response data.

The preference file is schema-versioned, allowlist-decoded, size-bounded, and
written atomically. Invalid data falls back to stable defaults without blocking
startup. Runtime `user_files` content remains excluded from the `.ankiaddon`.

## 13. Error Handling and Recovery

- Every failure maps to a stable internal error kind and a short safe user
  message.
- Errors never include keys, headers, full payloads, full file paths, complete
  imported documents, or provider response dumps.
- Import or generation failure preserves already imported material and completed
  review decisions when they are still valid.
- A failed chunk may be retried only through an explicit bounded user action.
- There is no automatic retry.
- Cancellation intent invalidates the request ID. If a transport cannot cancel an
  in-flight request, its later callback is ignored.
- Collection mutation never runs in an ordinary worker thread.
- A write result reports per-card success/failure and never implies rollback when
  no safe rollback occurred.

## 14. Migration Strategy

The migration proceeds in independently verifiable slices:

1. Freeze current behavior with architecture and state-contract tests.
2. Introduce `WorkbenchSessionState` and selectors without changing widgets.
3. Route material/import state through create use cases.
4. Extract generation request lifecycle and progress reduction.
5. Route candidate edits and review decisions through review use cases.
6. Add normalized source spans and deterministic quality/near-duplicate services.
7. Route mapping, duplicate readiness, and write preparation through write use
   cases while preserving the current writer.
8. Add allowlisted non-sensitive preferences.
9. Split Qt sections and leave compatibility facades for migrated imports.
10. Add CI, package checks, current docs, and archive labels for historical docs.
11. Apply the approved warm-charcoal and soft-orange visual system.
12. Run full automatic and real-Anki acceptance.

No slice may combine a major behavior change with a large visual rewrite.

## 15. CI and Verification

Add GitHub Actions jobs that run without real credentials or collections:

- Python 3.9 compatibility tests;
- Python 3.13 tests;
- `python -m unittest discover`;
- `python -m compileall .`;
- `python scripts/build_ankiaddon.py`;
- installed-package arbitrary-directory-name startup smoke;
- version consistency checks;
- package forbidden-file and absolute-self-import checks;
- secret-pattern audit against tracked/package content using approved fake-fixture
  exceptions.

At least Windows and one non-Windows CI runner exercise the pure-Python suite and
packager. CI does not call a real Provider or open a real Anki collection.

Local release-candidate verification additionally requires:

- full unit suite;
- compileall;
- `git diff --check`;
- two reproducible package builds and SHA-256 comparison;
- forbidden files = 0;
- no config, backup, collection, credentials, logs, or user files in the package;
- clean worktree after commit.

## 16. Visual System After Core Stabilization

The selected visual direction is **Warm Charcoal + Soft Orange**:

- warm charcoal application background;
- quiet warm-black surfaces;
- low-saturation orange for primary actions and focus only;
- warm neutral text instead of cold blue-white;
- muted success/warning/error tones;
- fewer decorative borders;
- consistent radii and spacing;
- hierarchy based on whitespace and typography rather than nested boxes.

The pass updates product QSS, style tokens, dialogs, and mock UI previews. It does
not change the generated Anki card template CSS or any product behavior.

## 17. Acceptance Criteria

The work is accepted only when:

1. The default visible workflow has no more controls than the current UI.
2. Create, Review, and Write remain understandable without reading developer
   terminology.
3. API keys remain session-only and absent from all persistence and artifacts.
4. No new automatic Provider call, retry, file scan, download, or Anki write is
   introduced.
5. Session state invalidates stale downstream decisions correctly.
6. Source labels never invent precision or expose full local paths.
7. Near-duplicate detection is bounded, local, advisory, and clearly named.
8. Existing collection duplicate checking and final confirmation remain hard
   gates.
9. Historical public imports remain compatible or have explicit temporary
   facades.
10. The full automatic suite, build validation, security audit, and reproducible
    package checks pass.
11. Real Anki acceptance covers startup, close/reopen, file import, generation,
    cancellation, review/edit/discard, duplicate checking, cancelled write,
    confirmed write to a test deck, and session teardown.
12. The final visual pass matches the approved warm-charcoal and soft-orange
    direction without introducing layout regressions.

## 18. Release Boundary

Completing this branch does not by itself authorize merge, public push, AnkiWeb
upload, tag creation, or GitHub Release creation. Those actions require a
separate explicit release decision after automatic and real-Anki acceptance.
