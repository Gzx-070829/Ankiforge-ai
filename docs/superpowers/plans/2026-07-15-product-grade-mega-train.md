# Product-Grade Local AI Card Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first v0.13 product-grade candidate that upgrades AnkiForge AI's UI, templates, quality evaluation, review, field mapping, write reporting, onboarding, documentation, and open-source assets without weakening any safety boundary.

**Architecture:** Existing `BeginnerFlowSession`, generation, duplicate, confirmation, and minimal-writer paths remain authoritative. New capabilities are focused pure-Python registries and decision models integrated through thin PyQt adapters. The old mock quality gate stays as a compatibility adapter; Cloze stays non-selectable and write-blocked.

**Tech Stack:** Python standard library, `unittest`, Anki `aqt.qt`, Markdown/JSON fixtures, deterministic ZIP packaging.

## Global Constraints

- API keys remain session-only and never enter config, logs, docs, fixtures, snapshots, or packages.
- No automatic Provider calls, Anki writes, note/deck/note-type mutations, deletes, OCR, network PDF parsing, vault scanning, accounts, cloud storage, or background networking.
- `GenerationSettings` retains its four existing fields and defaults for compatibility.
- New heuristic quality rules are warnings; only structural impossibility can block.
- Cloze templates are registered but hidden and hard-blocked until a separately verified writer exists.
- Keep at most four aggregate commits and never merge or push `main` in this task.

---

### Task 1: Master architecture and version contract

**Files:**
- Create: `docs/product_grade_master_plan.md`
- Create: `docs/superpowers/plans/2026-07-15-product-grade-mega-train.md`
- Modify: `ankiforge_ai/__init__.py`
- Modify: `ankiforge_ai/manifest.json`
- Test: `tests/test_product_grade_contract.py`

**Interfaces:** Produces version `0.13.0`, the required-file contract, and the safety boundary checklist used by all later tasks.

- [ ] Write tests asserting synchronized version metadata, required master-plan sections, and absence of exaggerated claims.
- [ ] Run `python -m unittest tests.test_product_grade_contract` and confirm failure on version/docs gaps.
- [ ] Set runtime and manifest to `0.13.0`; finish master-plan sections without placeholders.
- [ ] Re-run the focused test and confirm pass.

### Task 2: Shared style tokens, user errors, and Help dialog

**Files:**
- Create: `ankiforge_ai/ui/style_tokens.py`
- Create: `ankiforge_ai/ui/widgets.py`
- Create: `ankiforge_ai/pipeline/user_errors.py`
- Create: `ankiforge_ai/ui/help_dialog.py`
- Modify: `ankiforge_ai/ui/product_styles.py`
- Modify: `ankiforge_ai/ui/product_i18n.py`
- Modify: `ankiforge_ai/ui/main_dialog.py`
- Test: `tests/test_product_grade_ui_foundations.py`
- Test: `tests/test_user_errors.py`

**Interfaces:** `UserErrorDefinition`, `get_user_error(code, language)`, style token constants, `HelpDialog`, and small styled-widget helpers.

- [ ] Add failing tests for every required error code, zh/en parity, safe messages, Help entry, no visible debug entry, and centralized tokens.
- [ ] Run focused tests and verify missing-module failures.
- [ ] Implement immutable error catalog, tokens/helpers, Help dialog, Header button, and remove legacy workbench construction/imports from the product window.
- [ ] Run focused plus existing UI tests; update source-contract tests only where product behavior intentionally changed.

### Task 3: Productized examples and input metadata

**Files:**
- Create: `ankiforge_ai/pipeline/example_materials.py`
- Modify: `ankiforge_ai/importers/source_import.py`
- Modify: `ankiforge_ai/ui/card_maker_panel.py`
- Modify: `ankiforge_ai/ui/product_i18n.py`
- Test: `tests/test_example_materials.py`
- Test: `tests/test_source_import_product_grade.py`

**Interfaces:** `ExampleMaterial`, `all_example_materials()`, `get_example_material()`, `parse_markdown_frontmatter()`, safe `ImportedSource` metadata.

- [ ] Write failing registry tests for stable IDs, bilingual copy, mode recommendations, 3–5 card ranges, no secrets/paths/network, and deterministic ordering.
- [ ] Write failing import tests for YAML-like title extraction/stripping, normal Markdown, unsafe title fallback, PDF fallback, and no directory traversal.
- [ ] Implement the pure registries/parser, then integrate a lightweight example menu that fills material and recommends mode without Provider calls.
- [ ] Run focused and existing import/UI tests.

### Task 4: Template-aware modes and Prompt Profile v3

**Files:**
- Create: `ankiforge_ai/pipeline/card_templates.py`
- Modify: `ankiforge_ai/pipeline/generation_settings.py`
- Modify: `ankiforge_ai/pipeline/prompt_profile.py`
- Modify: `ankiforge_ai/ui/card_maker_panel.py`
- Modify: `ankiforge_ai/ui/product_i18n.py`
- Test: `tests/test_card_templates.py`
- Test: `tests/test_prompt_profile_v3.py`

**Interfaces:** `CardTemplate`, `all_card_templates()`, `get_card_template()`, `default_template_for_mode()`, `build_prompt_profile(settings, template_id=None)`.

- [ ] Add failing enumeration/safe-repr/bilingual/default/Cloze tests and prompt-difference/no-secret/no-path tests.
- [ ] Verify failures, implement immutable template registry and eight selectable non-Cloze modes plus hidden Cloze candidate.
- [ ] Extend prompt profile with template guidance while retaining its old call signature and output parser schema.
- [ ] Generate UI mode items from the profile registry; run prompt/generation/UI compatibility tests.

### Task 5: Card Quality v4 registry and deterministic rules

**Files:**
- Modify: `ankiforge_ai/pipeline/card_quality.py`
- Modify: `ankiforge_ai/pipeline/quality_gate.py`
- Modify: `ankiforge_ai/ui/product_i18n.py`
- Test: `tests/test_card_quality_v4.py`

**Interfaces:** `QualityRuleDefinition`, `all_quality_rules()`, backward-compatible `CardQualityIssue`, optional `CardQualityContext`, canonical evaluator and legacy adapter.

- [ ] Parameterize failing tests for every specified rule, bilingual messages/suggestions, score deltas, no mutation, safe repr, high/low scores, and missing-context non-triggering.
- [ ] Verify expected failures before production edits.
- [ ] Implement registry-driven rules; preserve `warning_id`, `suggestion_id`, existing score range, and old caller defaults.
- [ ] Convert legacy quality gate to a compatibility adapter without changing its public result types; run all quality/orchestrator tests.

### Task 6: Offline benchmark and multidisciplinary fixtures

**Files:**
- Create: `ankiforge_ai/eval/__init__.py`
- Create: `ankiforge_ai/eval/card_quality_benchmark.py`
- Create: `tests/fixtures/card_quality/*.json`
- Create: `tests/test_card_quality_benchmark.py`

**Interfaces:** `BenchmarkFixture`, `BenchmarkSummary`, `load_benchmark_fixture()`, `run_card_quality_benchmark()`.

- [ ] Add failing tests for ten subject fixtures, schema, deterministic summary, score distribution, no external calls, and unsafe-content rejection.
- [ ] Implement standard-library JSON loader/evaluator with stable ordering and structural safe repr.
- [ ] Confirm two runs produce identical summaries and all fixture expectations pass.

### Task 7: Review Workbench v4 pure state operations

**Files:**
- Create: `ankiforge_ai/pipeline/review_workbench.py`
- Modify: `ankiforge_ai/ui/beginner_flow_models.py`
- Modify: `ankiforge_ai/ui/card_maker_panel.py`
- Modify: `ankiforge_ai/ui/product_i18n.py`
- Test: `tests/test_review_workbench_v4.py`

**Interfaces:** `ReviewStats`, candidate original/current snapshots, copy/restore/bulk-keep-clean operations, and session methods that invalidate downstream state.

- [ ] Add failing tests for pending defaults, six statistics, copy, restore, edit revalidation, unique IDs, bulk clean keep, blocking rejection, warning keep, and invalidation.
- [ ] Implement pure statistics/helpers, then extend session state while preserving existing decision enum and public candidates.
- [ ] Integrate compact toolbar/stat labels and user-facing quality messages without rule IDs or scores.
- [ ] Run Review, duplicate, confirmation, and UI suites.

### Task 8: Field Mapping v3 and Cloze compatibility

**Files:**
- Create: `ankiforge_ai/pipeline/field_mapping.py`
- Modify: `ankiforge_ai/ui/read_only_anki_targets.py`
- Modify: `ankiforge_ai/ui/card_maker_panel.py`
- Test: `tests/test_field_mapping_v3.py`

**Interfaces:** `FieldMappingSuggestion`, `MappingAssessment`, `suggest_field_mapping(fields, mode_id, note_type_name)` and `assess_field_mapping(...)`.

- [ ] Add failing tests for Basic, Question/Answer, Chinese aliases, source optional, conflict/incomplete states, no mutation, uncertain fields, and Cloze incompatibility.
- [ ] Implement normalized deterministic scoring and compatibility assessment using only passed metadata.
- [ ] Integrate suggestions after field read while retaining user override and hard-block incomplete/conflicting mappings.
- [ ] Run mapping and write-preparation tests.

### Task 9: Write Safety v3, duplicate recheck, and trustworthy reports

**Files:**
- Create: `ankiforge_ai/pipeline/write_safety.py`
- Modify: `ankiforge_ai/ui/beginner_real_write.py`
- Modify: `ankiforge_ai/anki_writer/minimal_write.py`
- Modify: `ankiforge_ai/pipeline/write_traceability.py`
- Modify: `ankiforge_ai/ui/beginner_flow_models.py`
- Modify: `ankiforge_ai/ui/card_maker_panel.py`
- Test: `tests/test_write_safety_v3.py`
- Test: `tests/test_write_traceability_v3.py`

**Interfaces:** `WriteGateInput`, `WriteGateDecision`, distinct skipped-reason counts, final duplicate recheck hook, internal `LastWriteBatchRecord`, safe user summary.

- [ ] Add failing tests for all seven gates, truthful reason counts, explicit generation completion, TOCTOU duplicate prevention, post-add ID uncertainty handling, timestamp/batch/note-type/source, and note-ID redaction.
- [ ] Implement pure gate decision and extend summaries compatibly.
- [ ] Recheck duplicates immediately before each add using the already selected note type/fields; treat a created note with unavailable ID as written-but-untracked, never as safe-to-retry failure.
- [ ] Update UI summary/last-write text; keep Undo deferred and expose no delete action.
- [ ] Run every writer, duplicate, confirmation, traceability, and session test.

### Task 10: Documentation, governance, and release assets

**Files:**
- Modify: `README.md`, `README.en.md`, `SECURITY.md`, `CONTRIBUTING.md`, `PRIVACY.md`
- Create: `CODE_OF_CONDUCT.md`
- Create/modify all user guides listed in `docs/product_grade_master_plan.md`
- Create: `.github/ISSUE_TEMPLATE/*.md`, `.github/pull_request_template.md`
- Create: `tests/test_product_grade_docs.py`

**Interfaces:** Canonical user-facing docs structure, v0.13 AnkiWeb/Release drafts, issue/PR intake safety contracts.

- [ ] Add failing required-file, required-boundary, no-exaggeration, bilingual release, template-safety, and Markdown-link tests.
- [ ] Rewrite README as concise product entry points; create canonical guides and mark old install/import docs historical redirects.
- [ ] Expand policies and community templates with explicit no-key/no-user-data language.
- [ ] Add demo/growth assets and future roadmap; run documentation tests.

### Task 11: Static product acceptance previews

**Files:**
- Create: `docs/ui_preview_v0_13.html`
- Create: `docs/screenshots/v0_13/*.png`
- Test: `tests/test_v0_13_screenshot_assets.py`

**Interfaces:** Eleven synthetic, credential-free static states matching PyQt/QSS hierarchy.

- [ ] Add failing asset-name/dimension/no-secret tests.
- [ ] Create one query-driven static preview for zh/en, Modal, Help, examples, Review warning/blocking, write-ready, and pre-confirm states.
- [ ] Render eleven 1280×960 screenshots with headless Chrome and inspect each image manually.
- [ ] State clearly that these are static acceptance previews and real Anki rendering remains a manual gate.

### Task 12: Final verification, packaging, audit, commits, and branch push

**Files:**
- Modify: `dist/ankiforge_ai.ankiaddon`

**Interfaces:** Reproducible v0.13 package and auditable PR24 branch only.

- [ ] Run `python -m unittest discover`, `python -m compileall .`, and `git diff --check`.
- [ ] Build twice with `python scripts/build_ankiaddon.py`; compare SHA-256, file count, and byte size.
- [ ] Independently inspect ZIP names/content for config, backup, tests, docs, pycache, secrets, logs, Anki data, and source/package version consistency.
- [ ] Scan tracked files for real secrets and user data; manually classify only explicit fake fixtures.
- [ ] Create no more than four aggregate commits using the user-approved messages.
- [ ] Push only `public/v0.13.0-pr24-product-grade-mega-train`; verify `public/main` is unchanged.
