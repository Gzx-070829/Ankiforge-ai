# AnkiForge AI v1-Core Release Train Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a v0.12 release candidate with generation modes, deterministic card-quality feedback, explicit review, safe traceability, and clearer write summaries while preserving the v0.11 safety chain.

**Architecture:** Add focused pure-Python modules for settings, prompt profiles, quality, and traceability. Keep the current CardMakerPanel and BeginnerFlowSession as thin integration layers, and extend MinimalAnkiWriter only to add normalized tags to newly created notes.

**Tech Stack:** Python standard library, dataclasses/enums, unittest, Qt through `aqt.qt`, deterministic ZIP packaging.

## Global Constraints

- API keys remain session-only and are never represented, persisted, logged, committed, or packaged.
- Provider calls occur only from the existing explicit Generate action.
- Writes require current review, duplicate check, final preview, and explicit confirmation.
- Existing notes, decks, note types, and fields are never modified.
- Full undo deletion is deferred; only an in-memory last-write batch record is added.
- The existing two-column layout remains; no new UI framework or complex wizard.
- Final release actions stop on any failed test, compile, diff, package, secret, safety, merge, login, or permission gate.

---

### Task 1: Generation settings and prompt profiles

**Files:**
- Create: `ankiforge_ai/pipeline/generation_settings.py`
- Create: `ankiforge_ai/pipeline/prompt_profile.py`
- Modify: `ankiforge_ai/ai/prompts.py`
- Modify: `ankiforge_ai/ui/beginner_ai_card_drafts.py`
- Test: `tests/test_generation_settings.py`
- Test: `tests/test_prompt_profile.py`

**Interfaces:**
- Produces: `GenerationSettings`, `CardModeProfile`, `all_card_mode_profiles()`, `coerce_generation_settings()`, `card_limit_for_settings()`, and `build_prompt_profile()`.
- Consumes: existing provider runtime settings and Markdown chunk prompt inputs.

- [ ] Write tests asserting four enumerable profiles, exact defaults, bilingual names/descriptions, non-empty guidance, explicit invalid-mode errors, safe repr, mode-specific prompt differences, language instructions, and omitted-settings compatibility.
- [ ] Run `python -m unittest tests.test_generation_settings tests.test_prompt_profile` and confirm failures are caused by missing modules/interfaces.
- [ ] Implement frozen settings/profile models and short profile builders. Example public shape:

  ```python
  settings = GenerationSettings()
  assert settings.card_mode == "concept"
  assert build_prompt_profile(settings).card_limit == 5
  ```

- [ ] Pass settings through both prompt paths without changing the old positional arguments.
- [ ] Re-run the targeted tests and confirm they pass.

### Task 2: Deterministic card-quality engine

**Files:**
- Create: `ankiforge_ai/pipeline/card_quality.py`
- Test: `tests/test_card_quality.py`

**Interfaces:**
- Consumes: front/back strings or card-like objects and optional `GenerationSettings`.
- Produces: immutable `CardQualityIssue`, `CardQualityResult`, `CardQualityBatch`, `evaluate_card_quality()`, and `evaluate_card_batch()`.

- [ ] Write failing tests for empty front/back blocking, short/generic front, long back, multiple questions, multiple points, boilerplate, markdown residue, duplicate candidates, good-card score, Chinese text, safe repr, and input immutability.
- [ ] Run `python -m unittest tests.test_card_quality` and confirm expected import/interface failures.
- [ ] Implement explainable regex/length/count heuristics with scores clamped to `0.0..1.0`; never delete or edit cards.
- [ ] Re-run the quality tests and confirm all pass.

### Task 3: Safe source, tags, summaries, and batch tracking

**Files:**
- Create: `ankiforge_ai/pipeline/write_traceability.py`
- Test: `tests/test_write_traceability.py`

**Interfaces:**
- Produces: `SourceType`, `safe_source_label()`, `normalize_tag()`, `build_default_tags()`, `WriteSummary`, `WriteResultSummary`, `LastWriteBatchRecord`, and summary builders.

- [ ] Write failing tests for every source type, Windows/POSIX path redaction, tag character/length rules, default mode/source tags, pre/post-write counts, batch note ids, safe repr, and rejection of secrets/full paths.
- [ ] Run `python -m unittest tests.test_write_traceability` and confirm expected failures.
- [ ] Implement pure immutable models and normalizers; never store full paths or card contents.
- [ ] Re-run targeted tests and confirm all pass.

### Task 4: Review/session integration

**Files:**
- Modify: `ankiforge_ai/ui/beginner_flow_models.py`
- Modify: `ankiforge_ai/ui/beginner_real_write.py`
- Modify: `ankiforge_ai/ui/beginner_final_confirmation.py`
- Test: `tests/test_v1_core_review_workflow.py`
- Modify: relevant existing beginner-flow/write tests.

**Interfaces:**
- Session stores generation settings, source type/label, quality results, and last batch record in memory.
- Write preparation consumes quality results and returns no command when a kept candidate is blocking.

- [ ] Write failing tests that AI drafts start unreviewed, quality attaches on apply, edits re-evaluate, blocking keep is rejected, warnings can be kept, upstream changes clear stale write state, and duplicate/manual confirmation gates remain required.
- [ ] Run `python -m unittest tests.test_v1_core_review_workflow` and confirm expected failures.
- [ ] Add session methods for settings/source changes, draft replacement, quality refresh, explicit review, and safe batch recording.
- [ ] Extend final/write summaries with quality counts, source label, and tags while keeping existing callers compatible.
- [ ] Re-run targeted plus existing beginner-flow/write tests and confirm all pass.

### Task 5: Writer tag integration and post-write record

**Files:**
- Modify: `ankiforge_ai/anki_writer/minimal_write.py`
- Modify: `ankiforge_ai/ui/beginner_real_write.py`
- Test: `tests/test_v1_core_writer_tags.py`
- Modify: `tests/test_beginner_minimal_real_anki_write.py`

**Interfaces:**
- `BeginnerWriteCommand.tags` is a validated tuple of normalized tags.
- MinimalAnkiWriter adds only those tags to each newly created note.

- [ ] Write failing tests for tag application, invalid tags, source label content, unchanged note-type schema, created-note ids, and safe command/result repr.
- [ ] Run the targeted tests and confirm expected failures.
- [ ] Implement the minimal writer extension and build/record `LastWriteBatchRecord` only after a write result.
- [ ] Re-run writer, duplicate, confirmation, and controlled-write tests.

### Task 6: Thin product UI and bilingual copy

**Files:**
- Modify: `ankiforge_ai/ui/card_maker_panel.py`
- Modify: `ankiforge_ai/ui/product_i18n.py`
- Modify: `ankiforge_ai/ui/product_styles.py`
- Test: `tests/test_v1_core_ui_contract.py`
- Modify: `tests/test_product_i18n.py`
- Modify: `tests/test_single_screen_card_maker.py`

**Interfaces:**
- Card mode combo is always visible.
- Generation settings toggle controls a collapsed region containing count, answer length, and language.
- Card render consumes current quality results and write render consumes current summary.

- [ ] Write failing AST/copy/model tests for controls, defaults, collapsed state, bilingual keys, first-run guidance, unreviewed defaults, quality badges, discard-blocking action, summary rows, and absence of automatic generate/write calls.
- [ ] Run targeted UI contract tests and confirm expected failures.
- [ ] Add compact controls to the current AI section, quality feedback to current card groups, and summary copy to the current write section without restructuring columns.
- [ ] Ensure settings/material/edit changes invalidate stale duplicate/write state and re-render current local quality.
- [ ] Re-run all UI and i18n tests.

### Task 7: Product and release documentation

**Files:**
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `ankiforge_ai/__init__.py`
- Modify: `ankiforge_ai/manifest.json`
- Create: `docs/card_quality_system.md`
- Create: `docs/review_workbench.md`
- Create: `docs/write_safety_and_traceability.md`
- Create: `docs/v1_core_acceptance_checklist.md`
- Create: `docs/ankiweb_description_v0_12.md`
- Create: `docs/release_notes_v0_12_v1_core.md`
- Test: `tests/test_v1_core_docs.py`

**Interfaces:** Documentation describes version `0.12.0`, add-on code `1227582295`, limitations, manual review, confirmation, session-only key, fallback PDF, and deferred undo.

- [ ] Write failing documentation tests for required files, exact safety statements, bilingual AnkiWeb sections, no exaggerated claims, and synchronized runtime/manifest versions.
- [ ] Run `python -m unittest tests.test_v1_core_docs` and confirm expected failures.
- [ ] Write concise Chinese/English product, acceptance, AnkiWeb, and release documents.
- [ ] Re-run documentation tests.

### Task 8: Full verification, package, commit, and gated release train

**Files:**
- Verify: all repository files and `dist/ankiforge_ai.ankiaddon`

- [ ] Run `python -m unittest discover`, `python -m compileall .`, and `git diff --check`; stop on any failure.
- [ ] Run `python scripts/build_ankiaddon.py` twice, hash each build, and require identical SHA-256.
- [ ] Inspect the archive for forbidden paths, secret patterns, config, backups, caches, tests/docs, and Anki collection data; require zero findings and source/package consistency.
- [ ] Audit tracked files and source for config, backups, `.anki2`, `.apkg`, real tokens, passwords, bearer values, and local paths; stop on any real finding.
- [ ] Stage all intended PR18 files, commit once as `Add v1 core card quality and review workflow`, and confirm clean status.
- [ ] Re-run full verification from the commit, merge with `--no-ff` only if all gates remain green, and repeat full tests/package/security checks on main.
- [ ] Push only after main is clean and validated. Attempt AnkiWeb only with an existing authenticated session and no login/CAPTCHA/file-picker block. Create the release only when its prerequisites and absent-tag check pass.
