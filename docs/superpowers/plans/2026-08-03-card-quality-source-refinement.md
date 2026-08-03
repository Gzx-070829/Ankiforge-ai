# Card Quality, Source Traceability, and Preference Refinement Plan

> **Execution:** Implement task-by-task with `superpowers:executing-plans` and
> `superpowers:test-driven-development`. Every behavior change starts with a
> focused failing test.

**Goal:** Finish the v0.15 core-quality phase by turning the existing source,
quality, and duplicate services into one safe, explainable review contract while
keeping the public Create → Review → Write flow simple.

**Architecture:** Keep `document`, `intelligence`, and `pipeline` authoritative.
Add only narrow immutable values and adapters. The UI receives compact status and
evidence; it does not own quality rules or duplicate algorithms. Persist only a
strict allowlist of non-sensitive choices in Anki's preserved `user_files` area.

**Constraints:** No extra Provider call, embedding, telemetry, retry, automatic
write, collection-thread change, public Cloze control, API-key persistence, full
path exposure, or new public quality setting.

---

## Task 1: Normalize Safe Source Spans

**Files:**
- Create: `ankiforge_ai/document/source_spans.py`
- Modify: `ankiforge_ai/document/__init__.py`
- Modify: `ankiforge_ai/ui/universal_document_generation_adapter.py`
- Modify: `ankiforge_ai/ui/beginner_flow_models.py`
- Modify: `ankiforge_ai/ui/source_location_presenter.py`
- Test: `tests/test_source_spans.py`
- Test: `tests/test_universal_document_generation_adapter.py`

- [ ] Add a frozen `SourceSpan` containing a safe in-session document ID,
  basename-only source label, honest locator kind/value, optional block ID,
  optional trustworthy character offsets, and a bounded display label.
- [ ] Reject absolute/traversal paths, unsafe identifiers, inconsistent offsets,
  fabricated locator kinds, and unbounded values; keep repr content-free.
- [ ] Normalize a span from an imported `DocumentChunk` without claiming more
  precision than the chunk contains. Multiple blocks or locations degrade to a
  chunk/document-level label instead of inventing a page or paragraph.
- [ ] Carry the span through universal generation drafts and candidate previews.
  Editing, copying, and restoring a card preserve the source span.
- [ ] Let the existing source presenter consume either a `SourceSpan` or legacy
  `SourceLocation`, preserving current fallbacks and path redaction.

## Task 2: Publish One Three-state Quality Contract

**Files:**
- Modify: `ankiforge_ai/pipeline/card_quality.py`
- Modify: `ankiforge_ai/pipeline/review_workbench.py`
- Modify: `ankiforge_ai/ui/card_maker_panel.py`
- Modify: `ankiforge_ai/ui/product_i18n.py`
- Test: `tests/test_card_quality_status.py`
- Test: `tests/test_review_workbench_v4.py`
- Test: `tests/test_ui_copy_hotfix.py`

- [ ] Add the stable public statuses `ready`, `review`, and `blocked` while
  retaining the legacy `info`, `warning`, and `blocking` compatibility property.
- [ ] Add a compact localized summary selector and keep rule IDs/explanations in
  details. Do not expose score thresholds or add controls.
- [ ] Ensure empty/malformed cards are blocked; warnings remain advisory; human
  review remains mandatory even for `ready` cards.
- [ ] Use the public status in the current review UI and batch statistics without
  changing layout or write eligibility semantics.

## Task 3: Make Candidate Near-duplicates Advisory and Explainable

**Files:**
- Modify: `ankiforge_ai/intelligence/deduplication.py`
- Modify: `ankiforge_ai/workbench/generation_lifecycle.py`
- Modify: `ankiforge_ai/ui/beginner_flow_models.py`
- Modify: `ankiforge_ai/ui/card_maker_panel.py`
- Modify: `ankiforge_ai/ui/product_i18n.py`
- Test: `tests/test_coverage_dedup_v014.py`
- Test: `tests/test_generation_lifecycle.py`
- Test: `tests/test_intelligent_generation_task_controller.py`
- Test: `tests/test_candidate_near_duplicate_review.py`

- [ ] Add frozen, safe `DuplicateMatch` evidence with candidate ID, paired
  candidate ID, kind (`exact`, `canonical`, `similar`), reason code, and bounded
  deterministic similarity. Repr must contain no card text.
- [ ] Keep existing bounded local comparison and add inexpensive character
  n-gram evidence beside token overlap. Similar matches still require shared
  source identity.
- [ ] Stop removing duplicate candidates from the user-facing generation run.
  Keep every candidate for review and attach advisory evidence instead.
- [ ] Recalculate candidate duplicate warnings after local edits. Never delete,
  auto-discard, or call an external semantic matcher.
- [ ] Show the paired card number and a short reason in the existing quality
  details. Keep the collection duplicate check unchanged and authoritative.

## Task 4: Turn the Offline Benchmark into a Regression Contract

**Files:**
- Modify: `ankiforge_ai/eval/card_quality_benchmark.py`
- Modify: `tests/fixtures/card_quality/*.json`
- Modify: `tests/test_card_quality_benchmark.py`
- Create: `tests/test_card_quality_benchmark_contract.py`

- [ ] Version the checked-in fixture schema and record expected per-card public
  status and rule IDs for sanitized Chinese and English cases.
- [ ] Add safe immutable candidate/fixture reports containing IDs, status, score
  bucket/rank, rule IDs, and expected card-range coverage—never source/card text.
- [ ] Cover conceptual, definition, process, comparison, formula/rule,
  exam-trap, ambiguous, overlong, multi-part, exact duplicate, near-duplicate,
  and unrelated cases.
- [ ] Make CI fail deterministically when status, rule outcome, coverage range, or
  duplicate classification regresses. Do not present the result as truth or an
  academic accuracy score.

## Task 5: Persist Only Allowlisted Non-sensitive Preferences

**Files:**
- Create: `ankiforge_ai/workbench/preferences.py`
- Create: `ankiforge_ai/ui/workbench_preferences_adapter.py`
- Modify: `ankiforge_ai/ui/main_dialog.py`
- Modify: `ankiforge_ai/ui/card_maker_panel.py`
- Modify: `ankiforge_ai/ui/ai_settings_dialog.py`
- Modify: `scripts/build_ankiaddon.py`
- Test: `tests/test_workbench_preferences.py`
- Test: `tests/test_workbench_preferences_adapter.py`
- Test: `tests/test_build_ankiaddon.py`

- [ ] Define a schema-versioned frozen preference value for UI language,
  Provider name, model name, public card mode, card-count preset, answer-length
  preset, output language, and intelligence level.
- [ ] Strictly allowlist-decode, size-bound, and atomically write
  `user_files/preferences.json`; invalid data falls back to stable defaults.
- [ ] Explicitly reject API key, token, password, Authorization/Bearer, cookie,
  custom Base URL, imported material, paths, candidate content, review state, and
  write history at every storage boundary.
- [ ] Load preferences before UI construction and update them only after the user
  changes an existing choice. The API key remains session-only and the current
  dialog teardown still clears it.
- [ ] Ensure runtime `user_files` contents are excluded from `.ankiaddon` and the
  package forbidden-file audit covers preference payloads.

## Task 6: Phase-two Documentation and Verification

**Files:**
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `docs/workbench_architecture.md`
- Modify: `docs/future_roadmap.md`
- Modify: `docs/manual_anki_acceptance.md`
- Create: `docs/card_quality_and_source_evidence.md`
- Test: `tests/test_workbench_quality_release_contract.py`

- [ ] Document that source evidence is bounded review context, not factual proof;
  local near-duplicate detection is not semantic dedup; the collection check is
  still authoritative; and human review is always required.
- [ ] Document exactly which non-sensitive preferences persist and which values
  never persist.
- [ ] Run focused suites after every task, then the full unit suite,
  `compileall`, and `git diff --check`.
- [ ] Build twice, compare SHA-256, and confirm forbidden files, config, secrets,
  backup, Anki user data, runtime `user_files`, and absolute self-imports are all
  zero.
- [ ] Commit Phase 2 on
  `codex/v0.15.0-workbench-core-quality-polish`. Do not merge, public-push, tag,
  upload AnkiWeb, or create a GitHub Release.

## Acceptance

- Existing visible controls do not increase.
- Every candidate remains visible until the user decides.
- Quality uses `ready / review / blocked` and never claims truth verification.
- Source precision is honest and paths stay private.
- Near-duplicate results identify the pair/reason and remain local/advisory.
- Preferences reduce repeated setup without retaining any credential or content.
- Provider, collection duplicate, final confirmation, and Anki write boundaries
  remain unchanged.
