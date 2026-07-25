# Universal Document & Intelligence Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standard-library-first universal local document pipeline and
bounded intelligence engine that feeds the existing Create → Review → Write
workflow without weakening Provider, review, duplicate, confirmation, or Anki
write safety.

**Architecture:** Native importers normalize explicitly selected local files to
an immutable DocumentIR. Pure-Python analysis, structural chunking, planning,
template routing, call budgeting, quality, coverage, and deduplication operate
on safe snapshots. Optional backends are lazy local adapters only; Qt/Anki code
remains a thin presentation and operation boundary.

**Tech Stack:** Python standard library, frozen dataclasses, `unittest`,
`zipfile`, `xml.etree.ElementTree`, `html.parser`, deterministic fake Provider
tests, existing PyQt/Anki adapters, existing reproducible `.ankiaddon` builder.

## Global Constraints

- Branch: `v0.14.0-pr27-universal-document-intelligence-engine` from
  `858a908967a539e31ae6649d11aeb8b2acb528ae`; target version `0.14.0`.
- Do not merge or push `main`; do not update AnkiWeb; do not create a tag or
  GitHub Release.
- Do not start a real Provider or write a real Anki collection.
- API keys remain session-only and absent from files, config, IR, logs, repr,
  subprocesses, screenshots, package, and tests.
- No automatic AI call, automatic retry, automatic Anki write, external tool
  install, model download, directory scan, URL import, macro/script/notebook
  execution, external resource load, or include expansion.
- Core has no required third-party runtime. Docling, MarkItDown, Pandoc,
  Chonkie, OCR models, FFmpeg, and downloaded models are not bundled.
- Native PDF parsing/OCR is not implemented; PDF is fallback-only or handled by
  an explicitly selected optional backend.
- `MAX_AI_CALLS_PER_RUN = 12`; one repair per knowledge point and one coverage
  supplement per run; Cloze stays non-selectable.
- Preserve immutable snapshots, request-ID stale callback discard, human review,
  duplicate hard gate, final-confirmation hard gate, write replay protection,
  and non-mutation of existing notes/decks/note types.
- Every behavior change follows RED → GREEN → REFACTOR and uses safe,
  hand-derived assertions against real code.
- Before each commit run its focused tests and `git diff --check`; never commit
  credentials, user files, config, backups, Anki data, temp output, or optional
  dependencies.

---

### Task 1: Add DocumentIR, limits, detection, errors, and importer registry

**Files:**
- Create: `ankiforge_ai/document/__init__.py`
- Create: `ankiforge_ai/document/models.py`
- Create: `ankiforge_ai/document/serialization.py`
- Create: `ankiforge_ai/document/limits.py`
- Create: `ankiforge_ai/document/errors.py`
- Create: `ankiforge_ai/document/source_labels.py`
- Create: `ankiforge_ai/document/detection.py`
- Create: `ankiforge_ai/document/capabilities.py`
- Create: `ankiforge_ai/document/registry.py`
- Create: `ankiforge_ai/document/importers/__init__.py`
- Create: `ankiforge_ai/document/importers/base.py`
- Create: `ankiforge_ai/document/importers/registry.py`
- Test: `tests/test_document_ir.py`
- Test: `tests/test_document_detection.py`
- Test: `tests/test_document_registry.py`
- Test: `tests/test_document_errors_and_limits.py`

**Interfaces:**
- Produces `DocumentIR`, `DocumentSection`, `DocumentBlock`,
  `DocumentWarning`, `SourceLocation`, `BlockKind`, `SafeScalar`.
- Produces `validate_document_ir()`, `document_to_plain_text()`,
  `document_to_safe_markdown()`, `document_summary()`,
  `count_blocks_by_kind()`, `document_to_safe_json()`,
  `document_from_safe_json()`, and `get_safe_source_label()`.
- Produces `DocumentLimits`, `DEFAULT_DOCUMENT_LIMITS`, `DetectedFileType`,
  `detect_file_type()`, `DocumentImportError`, `ImporterCapability`,
  `SupportLevel`, `DocumentImporter`, and `DocumentImporterRegistry`.
- Consumes no Qt, Anki, Provider, or legacy importer object.

- [ ] **Step 1: Write failing immutable-model and safe-serialization tests**

  Add tests that construct a two-section document with literal expected safe
  dictionaries, mutate caller-owned metadata/lists after construction, and
  assert the document remains unchanged. Assert that `repr(document)` excludes
  an absolute path, block body, and a fake API key; invalid IDs, duplicate block
  IDs, unsafe metadata, and absolute source labels are rejected.

- [ ] **Step 2: Verify RED for DocumentIR**

  Run:
  `python -m unittest tests.test_document_ir tests.test_document_errors_and_limits`

  Expected: import failure because `ankiforge_ai.document` does not exist.

- [ ] **Step 3: Implement frozen models, limits, labels, validation, and JSON**

  Use frozen dataclasses with tuple fields and immutable metadata proxies.
  `to_safe_dict()` returns new JSON-compatible dictionaries. Keep full source
  text out of `repr`; bound scalar key/value length; validate all counts against
  the exact values in the design specification.

- [ ] **Step 4: Write failing detection and registry tests**

  Cover UTF BOMs, text/binary heuristic, extension mismatch, Office ZIP member
  signatures, EPUB signatures, JSON/IPYNB hints, XML roots, malformed files,
  deterministic importer selection, absent optional importer, explicit-only
  fallback, and capability matrix ordering.

- [ ] **Step 5: Verify RED, implement detection/registry, and verify GREEN**

  Run the new detection/registry tests; confirm missing symbols fail. Implement
  prefix-only detection and ZIP member inspection without extraction. Registry
  stores lazy factories, never imports an optional dependency at registration,
  and raises structured safe errors.

  Run:
  `python -m unittest tests.test_document_ir tests.test_document_detection tests.test_document_registry tests.test_document_errors_and_limits`

  Expected: all Task 1 tests pass.

- [ ] **Step 6: Run baseline regression and safety check**

  Run:
  `python -m unittest tests.test_source_import tests.test_build_ankiaddon tests.test_pr26_release_metadata_and_lifecycle`

  Run: `git diff --check`

- [ ] **Step 7: Commit**

  Commit message:
  `Add DocumentIR and secure importer registry`

---

### Task 2: Add native structured and safe text importers

**Files:**
- Create: `ankiforge_ai/document/archive_safety.py`
- Create: `ankiforge_ai/document/xml_safety.py`
- Create: `ankiforge_ai/document/importers/text.py`
- Create: `ankiforge_ai/document/importers/markdown.py`
- Create: `ankiforge_ai/document/importers/html.py`
- Create: `ankiforge_ai/document/importers/tabular.py`
- Create: `ankiforge_ai/document/importers/json_data.py`
- Create: `ankiforge_ai/document/importers/xml_data.py`
- Create: `ankiforge_ai/document/importers/notebook.py`
- Create: `ankiforge_ai/document/importers/subtitles.py`
- Create: `ankiforge_ai/document/importers/office_open_xml.py`
- Create: `ankiforge_ai/document/importers/epub.py`
- Create: `ankiforge_ai/document/importers/code_text.py`
- Create: `scripts/generate_document_fixtures.py`
- Create: `tests/test_document_archive_xml_security.py`
- Create: `tests/test_document_importers_text_markup.py`
- Create: `tests/test_document_importers_data_notebook.py`
- Create: `tests/test_document_importers_office_epub.py`
- Create: `tests/test_document_importers_subtitles_code.py`
- Create: deterministic small files under `tests/fixtures/documents/` and
  `tests/fixtures/security/`
- Modify: `ankiforge_ai/importers/source_import.py`
- Modify: `tests/test_source_import.py`

**Interfaces:**
- Consumes Task 1 `DocumentIR`, limits, detection, safe archive/XML helpers,
  registry, and error contract.
- Produces registered native importers for every format listed in the design,
  plus `import_documents(paths, limits) -> tuple[DocumentIR, ...]`.
- Keeps `import_source_file(path) -> ImportedSource` and
  `merge_imported_source_text()` backward-compatible by rendering one IR.

- [ ] **Step 1: Generate reviewable fixtures and write failing text/markup tests**

  The fixture script creates deterministic OOXML/EPUB ZIPs with fixed member
  timestamps. Text fixtures cover TXT, Markdown/frontmatter, HTML scripts and
  remote resources, YAML/RST/Org/TeX/log, and all listed code extensions.
  Assert exact block kinds, heading paths, line locations, safe labels, and
  absence of executed/fetched content.

- [ ] **Step 2: Verify RED and implement text/markup importers**

  Run:
  `python -m unittest tests.test_document_importers_text_markup tests.test_document_importers_subtitles_code`

  Expected: missing importer modules. Implement bounded decoders, Markdown
  structure, a non-fetching `HTMLParser`, subtitle grouping, and code/comment
  grouping. Do not parse includes.

- [ ] **Step 3: Write failing data/XML/notebook security tests**

  Cover CSV/TSV headers and row groups, JSON/JSONL bounded recursion, safe XML,
  XXE/DOCTYPE/ENTITY, element/depth limits, notebook cell locations, skipped
  image/base64 output, and output-size warnings.

- [ ] **Step 4: Verify RED and implement data/XML/notebook importers**

  Run:
  `python -m unittest tests.test_document_importers_data_notebook tests.test_document_archive_xml_security`

  Expected: missing behavior. Implement iterative bounded traversal and explicit
  structured errors; never evaluate spreadsheet/notebook formulas or code.

- [ ] **Step 5: Write failing Office/EPUB/archive tests**

  Cover valid DOCX/PPTX/XLSX/EPUB order and source locations, list/table
  preservation, hidden XLSX sheet skip, formula text, macro/external relation
  ignore, ZIP traversal, symlink, duplicate normalized path, encrypted member,
  member/aggregate/ratio limits, fake Office archive, and malformed EPUB.

- [ ] **Step 6: Verify RED and implement Office/EPUB importers**

  Run:
  `python -m unittest tests.test_document_importers_office_epub tests.test_document_archive_xml_security`

  Expected: missing behavior. Parse only validated in-archive members with
  standard-library ZIP/XML; resolve relationships within the same archive;
  never extract members to user paths.

- [ ] **Step 7: Register all native importers and preserve legacy adapter**

  Add registry construction in `document/importers/registry.py`. Adapt
  `source_import.import_source_file()` to render DocumentIR while retaining its
  stable errors, fields, append behavior, and PDF fallback.

  Run:
  `python -m unittest tests.test_document_importers_text_markup tests.test_document_importers_data_notebook tests.test_document_importers_office_epub tests.test_document_importers_subtitles_code tests.test_document_archive_xml_security tests.test_source_import tests.test_source_import_product_grade`

- [ ] **Step 8: Diff/safety check and commit**

  Run: `git diff --check`

  Confirm fixtures contain no user path, credential, collection, backup, or
  network-fetched data.

  Commit message:
  `Add native structured document importers`

---

### Task 3: Add optional local backend adapters and companion protocol

**Files:**
- Create: `ankiforge_ai/document/backends/__init__.py`
- Create: `ankiforge_ai/document/backends/base.py`
- Create: `ankiforge_ai/document/backends/detection.py`
- Create: `ankiforge_ai/document/backends/command_runner.py`
- Create: `ankiforge_ai/document/backends/docling_adapter.py`
- Create: `ankiforge_ai/document/backends/markitdown_adapter.py`
- Create: `ankiforge_ai/document/backends/pandoc_adapter.py`
- Create: `ankiforge_ai/document/backends/companion_protocol.py`
- Create: `ankiforge_ai/document/importers/optional_backends.py`
- Test: `tests/test_document_backend_capabilities.py`
- Test: `tests/test_document_backend_command_runner.py`
- Test: `tests/test_document_backend_adapters.py`
- Test: `tests/test_document_companion_protocol.py`

**Interfaces:**
- Produces `DocumentBackend`, `BackendCapability`, `BackendProbe`,
  `BackendCommand`, `BackendResult`, `SafeCommandRunner`,
  `CompanionRequest`, `CompanionResponse`, and `CompanionProgress`.
- Adapters accept only a validated local path plus limits and return validated
  DocumentIR or a stable error.
- Optional modules remain unimported until `probe()`/explicit conversion.

- [ ] **Step 1: Write failing capability and absence-safe tests**

  Assert Core imports with deliberately blocked `docling`, `markitdown`, and
  subprocess executables; probes report unavailable without traceback; no
  adapter is enabled by default; no URL or credential field exists.

- [ ] **Step 2: Verify RED and implement protocols/probes**

  Run:
  `python -m unittest tests.test_document_backend_capabilities tests.test_document_companion_protocol`

  Expected: missing backend modules. Implement immutable capability/version/
  health models and strict versioned companion JSON validation.

- [ ] **Step 3: Write failing command-runner security tests**

  Use a tiny local fake executable/script fixture. Assert argument vector,
  `shell=False`, fixed executable, sanitized environment, controlled cwd/temp,
  timeout, stdout/stderr limits, nonzero exit, cancellation, cleanup, and
  rejection of URL/user switches/invalid output.

- [ ] **Step 4: Verify RED and implement SafeCommandRunner**

  Run:
  `python -m unittest tests.test_document_backend_command_runner`

  Expected: missing runner. Implement bounded `subprocess.Popen` handling
  without a shell; never include source text or credentials in error repr.

- [ ] **Step 5: Write and satisfy adapter mapping tests**

  Mock only the command boundary and feed literal MarkItDown Markdown, Docling
  JSON/Markdown, and Pandoc Markdown. Verify DocumentIR mapping, PDF optional
  status, OCR/plugins/remote/downloads off, Pandoc fixed `--sandbox --from ...
  --to gfm` arguments, output validation, and safe failure fallback.

  Run:
  `python -m unittest tests.test_document_backend_adapters tests.test_document_backend_command_runner tests.test_document_backend_capabilities tests.test_document_companion_protocol`

- [ ] **Step 6: Diff/package-boundary check and commit**

  Run: `git diff --check`

  Run:
  `python -m unittest tests.test_build_ankiaddon`

  Confirm no third-party package, executable, model, downloaded file, or temp
  output is present under `ankiforge_ai/`.

  Commit message:
  `Add optional local document backend adapters`

---

### Task 4: Add analysis, structural chunking, planning, routing, and estimates

**Files:**
- Create: `ankiforge_ai/intelligence/__init__.py`
- Create: `ankiforge_ai/intelligence/models.py`
- Create: `ankiforge_ai/intelligence/analyzer.py`
- Create: `ankiforge_ai/intelligence/mode_recommender.py`
- Create: `ankiforge_ai/intelligence/estimates.py`
- Create: `ankiforge_ai/intelligence/template_router.py`
- Create: `ankiforge_ai/intelligence/chunking/__init__.py`
- Create: `ankiforge_ai/intelligence/chunking/models.py`
- Create: `ankiforge_ai/intelligence/chunking/structural.py`
- Create: `ankiforge_ai/intelligence/chunking/token_budget.py`
- Create: `ankiforge_ai/intelligence/chunking/table_chunker.py`
- Create: `ankiforge_ai/intelligence/chunking/transcript_chunker.py`
- Create: `ankiforge_ai/intelligence/planning/__init__.py`
- Create: `ankiforge_ai/intelligence/planning/models.py`
- Create: `ankiforge_ai/intelligence/planning/local_planner.py`
- Create: `ankiforge_ai/intelligence/planning/llm_planner.py`
- Create: `ankiforge_ai/intelligence/planning/coverage.py`
- Modify: `ankiforge_ai/pipeline/generation_settings.py`
- Test: `tests/test_document_analyzer.py`
- Test: `tests/test_structural_chunker.py`
- Test: `tests/test_knowledge_planner_v014.py`
- Test: `tests/test_template_router_v014.py`
- Test: `tests/test_intelligence_estimates.py`

**Interfaces:**
- Produces `DocumentAnalysis`, `DocumentChunk`, `KnowledgePlan`,
  `KnowledgePointPlan`, `PlanEstimate`, `IntelligenceLevel`, and
  `TemplateRoute`.
- Produces `analyze_document()`, `chunk_document()`,
  `build_local_knowledge_plan()`, `parse_llm_knowledge_plan()`,
  `assess_plan_coverage()`, `route_template()`, and `estimate_generation()`.
- Extends selectable modes with `auto`, `code_understanding`,
  `table_relationship`, and `transcript_summary_candidate`; Cloze stays false.

- [ ] **Step 1: Write failing analyzer/routing tests**

  Use literal definition, comparison, process, formula, code, table,
  transcript, and bilingual IR fixtures. Assert hand-derived signals,
  confidence, recommended modes, explicit-mode precedence, Auto reason codes,
  and non-selectable Cloze.

- [ ] **Step 2: Verify RED and implement analyzer/router**

  Run:
  `python -m unittest tests.test_document_analyzer tests.test_template_router_v014`

  Expected: missing intelligence package. Implement deterministic bounded
  heuristics and extend generation profiles without changing default
  `concept/balanced/short/auto`.

- [ ] **Step 3: Write failing structural chunk tests**

  Assert heading/list integrity, repeated table headers, code/formula context,
  slide/sheet/chapter/timestamp boundaries, adjacent peer merge, source
  locations, target/max character budgets, and no path leakage.

- [ ] **Step 4: Verify RED and implement chunker**

  Run:
  `python -m unittest tests.test_structural_chunker`

  Expected: missing chunking modules. Implement structure-first grouping and
  bounded secondary splitting without external tokenizers.

- [ ] **Step 5: Write failing planner/estimate tests**

  Cover section balance, priority, source references, duplicate point removal,
  no out-of-source points, structured LLM JSON validation, failed planner local
  fallback, Fast/Standard/Deep call/card ranges, and 12-call hard ceiling.

- [ ] **Step 6: Verify RED and implement planner/estimates**

  Run:
  `python -m unittest tests.test_knowledge_planner_v014 tests.test_intelligence_estimates`

  Expected: missing planning behavior. Implement local planning first; LLM
  parsing accepts a caller result but performs no Provider call itself.

- [ ] **Step 7: Regression, diff check, and commit**

  Run:
  `python -m unittest tests.test_generation_settings tests.test_card_templates_v4 tests.test_prompt_profile_v4 tests.test_document_analyzer tests.test_structural_chunker tests.test_knowledge_planner_v014 tests.test_template_router_v014 tests.test_intelligence_estimates`

  Run: `git diff --check`

  Commit message:
  `Add structure-aware chunking and knowledge planning`

---

### Task 5: Add bounded generation runs, quality recovery, and deck-style foundation

**Files:**
- Create: `ankiforge_ai/intelligence/generation_run.py`
- Create: `ankiforge_ai/intelligence/call_budget.py`
- Create: `ankiforge_ai/intelligence/critic.py`
- Create: `ankiforge_ai/intelligence/coverage.py`
- Create: `ankiforge_ai/intelligence/deduplication.py`
- Create: `ankiforge_ai/intelligence/recovery.py`
- Create: `ankiforge_ai/intelligence/deck_style.py`
- Create: `ankiforge_ai/ui/intelligent_generation_task_controller.py`
- Modify: `ankiforge_ai/ui/generation_task_controller.py` only for reusable
  lifecycle helpers when backward-compatible
- Test: `tests/test_generation_run_v014.py`
- Test: `tests/test_intelligence_call_budget.py`
- Test: `tests/test_critic_repair_v014.py`
- Test: `tests/test_coverage_dedup_v014.py`
- Test: `tests/test_partial_failure_recovery.py`
- Test: `tests/test_deck_style_profile.py`
- Test: `tests/test_intelligent_generation_task_controller.py`

**Interfaces:**
- Produces `GenerationRun`, `GenerationStage`, `GenerationRunStatus`,
  `ChunkGenerationState`, `CallBudget`, `CriticDecision`, `CoverageReport`,
  `DeduplicationResult`, `FailedChunkRetry`, and `DeckStyleProfile`.
- Produces pure transition functions and an async controller that consumes an
  immutable run snapshot plus injected planner/generator/critic callbacks.
- Existing `GenerationTaskController.submit()` behavior remains valid.

- [ ] **Step 1: Write failing run/budget transition tests**

  Assert legal stages, immutable snapshots, budget reservation before each
  call, Fast/Standard/Deep stage/call policy, 12-call rejection, one repair per
  point, one supplement per run, safe repr, and no recursive retry.

- [ ] **Step 2: Verify RED and implement run/budget models**

  Run:
  `python -m unittest tests.test_generation_run_v014 tests.test_intelligence_call_budget`

  Expected: missing run modules. Implement pure transitions that return new
  frozen runs and structured errors.

- [ ] **Step 3: Write failing critic/coverage/dedup tests**

  Assert local blocking authority, one repair then revalidation, no unsupported
  source claims, missed/overcovered section detection, exact/canonical/similar
  duplicates across chunks, punctuation/whitespace normalization, and no
  embedding dependency.

- [ ] **Step 4: Verify RED and implement critic/coverage/dedup**

  Run:
  `python -m unittest tests.test_critic_repair_v014 tests.test_coverage_dedup_v014`

  Expected: missing behavior. Reuse canonical card-quality normalization where
  compatible and return user-facing reason codes rather than raw reasoning.

- [ ] **Step 5: Write failing partial recovery and async lifecycle tests**

  Cover one failed chunk retaining sibling cards, explicit failed-only retry,
  no duplicate retry/billing, immutable settings/document snapshots, request-ID
  stale discard, new-run supersession, closed-window no-op, and callback
  exception safety.

- [ ] **Step 6: Verify RED and implement recovery/controller**

  Run:
  `python -m unittest tests.test_partial_failure_recovery tests.test_intelligent_generation_task_controller tests.test_generation_task_controller`

  Expected: missing controller/recovery. Worker callbacks never touch Qt or
  collection; UI adapters receive safe completion snapshots only.

- [ ] **Step 7: Write and satisfy DeckStyleProfile tests**

  Assert opt-in, selected-deck-only query specification, maximum 20 notes,
  aggregate-only default payload, no mutation/full scan, safe deck label, and
  no note content in repr/log. Implement pure profile summarization and a
  disabled real-sampling capability flag.

  Run:
  `python -m unittest tests.test_deck_style_profile`

- [ ] **Step 8: Regression, diff check, and commit**

  Run:
  `python -m unittest tests.test_card_quality_v4 tests.test_review_workbench_v4 tests.test_async_card_generation tests.test_generation_task_controller tests.test_generation_run_v014 tests.test_intelligence_call_budget tests.test_critic_repair_v014 tests.test_coverage_dedup_v014 tests.test_partial_failure_recovery tests.test_deck_style_profile tests.test_intelligent_generation_task_controller`

  Run: `git diff --check`

  Commit message:
  `Add bounded intelligence runs and recovery`

---

### Task 6: Integrate queue, capabilities, intelligence controls, progress, and sources

**Files:**
- Create: `ankiforge_ai/ui/document_import_queue.py`
- Create: `ankiforge_ai/ui/document_import_task_controller.py`
- Create: `ankiforge_ai/ui/document_capabilities_dialog.py`
- Create: `ankiforge_ai/ui/document_intelligence_presenter.py`
- Create: `ankiforge_ai/ui/source_location_presenter.py`
- Modify: `ankiforge_ai/ui/file_drop_text_edit.py`
- Modify: `ankiforge_ai/ui/card_maker_panel.py`
- Modify: `ankiforge_ai/ui/beginner_flow_models.py`
- Modify: `ankiforge_ai/ui/product_i18n.py`
- Modify: `ankiforge_ai/ui/product_styles.py`
- Modify: `ankiforge_ai/ui/style_tokens.py`
- Test: `tests/test_document_import_queue.py`
- Test: `tests/test_document_import_task_controller.py`
- Test: `tests/test_document_capabilities_dialog.py`
- Test: `tests/test_document_intelligence_presenter.py`
- Test: `tests/test_source_location_presenter.py`
- Test: `tests/test_universal_document_ui_contract.py`

**Interfaces:**
- Queue models consume selected path tokens privately and expose safe row
  snapshots with filename/type/importer/status/counts/warnings only.
- Presenter consumes DocumentIR/analysis/estimate/run and returns localized
  view models; Qt widgets do not implement intelligence logic.
- Panel converts successful queue documents to bounded material/chunks only
  after parsing and never starts AI automatically.

- [ ] **Step 1: Write failing queue/controller tests**

  Assert up to 20 ordered files, add/remove/reorder, independent success/warning/
  failure, failed-only retry after explicit action, batch byte limit, private
  paths excluded from repr/safe dict, immutable request IDs, stale completion,
  close no-op, and `uses_collection=False`.

- [ ] **Step 2: Verify RED and implement queue/controller**

  Run:
  `python -m unittest tests.test_document_import_queue tests.test_document_import_task_controller`

  Expected: missing UI models/controllers. Implement pure queue transitions and
  a taskman adapter; keep all Qt updates in completion callbacks.

- [ ] **Step 3: Write failing presenter/capability/source tests**

  Assert bilingual capabilities, native/optional/fallback status, missing
  backend guidance, no auto-install wording, document summary, Auto
  recommendation, Fast/Standard/Deep estimates, all stage labels, short source
  chips, bounded source snippet, and no internal IDs/classes/rules/prompts.

- [ ] **Step 4: Verify RED and implement presenters/dialog**

  Run:
  `python -m unittest tests.test_document_capabilities_dialog tests.test_document_intelligence_presenter tests.test_source_location_presenter`

  Expected: missing modules/copy. Implement presentation models first, then the
  thin dialog.

- [ ] **Step 5: Write failing panel/UI contract tests**

  Assert file picker accepts all native extensions and multi-select, drop keeps
  every file, Create remains compact, capabilities entry exists, Auto mode and
  intelligence selector exist, settings default to Standard and collapsed
  detail, estimates and explicit Standard/Deep confirmation appear, stage
  progress and partial retry appear, Review source chips appear, API settings
  remain outside the main form, and existing Write controls/gates remain.

- [ ] **Step 6: Verify RED and integrate panel/state/i18n/styles**

  Run:
  `python -m unittest tests.test_universal_document_ui_contract tests.test_file_drop_import tests.test_linear_flow_settings_modal tests.test_single_screen_card_maker`

  Expected: new UI contract failures. Integrate presenters and controllers
  without parsing/planning logic in `card_maker_panel.py`. Invalidate parsed,
  planned, candidate, duplicate, and final artifacts when queue/settings change.

- [ ] **Step 7: Full UI/safety regression, diff check, and commit**

  Run:
  `python -m unittest tests.test_product_i18n tests.test_product_styles tests.test_ui_rescue_v0_12_2 tests.test_provider_form_layout_hotfix tests.test_async_card_generation tests.test_beginner_minimal_real_anki_write tests.test_write_safety_v3 tests.test_document_import_queue tests.test_document_import_task_controller tests.test_document_capabilities_dialog tests.test_document_intelligence_presenter tests.test_source_location_presenter tests.test_universal_document_ui_contract`

  Run: `git diff --check`

  Commit message:
  `Integrate universal document intelligence UI`

---

### Task 7: Add benchmark, documentation, version, package, and Mock screenshots

**Files:**
- Create: `ankiforge_ai/eval/document_intelligence_benchmark.py`
- Create: `tests/test_document_intelligence_benchmark.py`
- Create: `tests/test_v014_release_contract.py`
- Modify: `ankiforge_ai/__init__.py`
- Modify: `ankiforge_ai/manifest.json`
- Modify: `scripts/build_ankiaddon.py`
- Modify: `tests/test_build_ankiaddon.py`
- Modify: `README.md`
- Modify: `README.en.md`
- Create/update all v0.14 docs required by the design, including
  `docs/getting_started.md`, `docs/importing_materials.md`,
  `docs/document_ir.md`, `docs/native_supported_formats.md`,
  `docs/optional_document_backends.md`, backend setup guides,
  `docs/document_security.md`, intelligence/planning/chunking/call-budget/
  deck-style/troubleshooting/manual-acceptance docs,
  `docs/release_notes_v0_14.md`, `docs/ankiweb_description_v0_14.md`,
  `docs/future_document_engine_companion.md`, and
  `docs/third_party_notices.md`
- Create: `docs/assets/ui_preview_v0_14.html`
- Create: `docs/assets/screenshots/v0_14/manifest.json`
- Create: at least 13 Mock screenshots in
  `docs/assets/screenshots/v0_14/`

**Interfaces:**
- Benchmark consumes deterministic fixtures, native importers, analyzer,
  chunker, local planner/router, fake cards, quality, coverage, and dedup.
- Version contract requires runtime/manifest/human version/public docs to be
  `0.14.0`.
- Package remains runtime-only and excludes eval, fixtures, screenshots,
  optional tools, models, config, secrets, backup, logs, and Anki data.

- [ ] **Step 1: Write failing benchmark and release-contract tests**

  Assert literal expected routing/coverage for Python, SQL, BCI/EEGNet, math,
  vocabulary, biology, history, process, comparison, table, transcript,
  bilingual, PPT, and XLSX fixtures. Assert benchmark metrics/failure reasons
  are deterministic and make no network call. Assert version and required docs
  are exactly `0.14.0`.

- [ ] **Step 2: Verify RED and implement benchmark/version**

  Run:
  `python -m unittest tests.test_document_intelligence_benchmark tests.test_v014_release_contract`

  Expected: missing benchmark/docs and old version. Implement benchmark output
  and update version metadata; do not use a real Provider.

- [ ] **Step 3: Write/update user and release documentation**

  Document exact native levels, PDF fallback, optional backend installation and
  licenses, no auto-install/upload, Provider egress, intelligence call
  differences, no retry, review requirement, source-location limitations,
  manual acceptance, and precise implemented/limited/foundation/deferred status.

- [ ] **Step 4: Build offline Mock UI preview and screenshots**

  The HTML preview uses static fake documents/cards only and labels every frame
  `Mock UI preview — not a live Anki or Provider session`. Capture the 13
  required Chinese/English, queue, capability, estimate, progress, source, and
  backend states. Record filenames, viewport, scenario, and mock status in the
  screenshot manifest.

- [ ] **Step 5: Run focused benchmark/docs/package tests**

  Run:
  `python -m unittest tests.test_document_intelligence_benchmark tests.test_v014_release_contract tests.test_build_ankiaddon tests.test_product_grade_docs tests.test_pr26_release_metadata_and_lifecycle`

  Run: `python -m compileall .`

  Run: `git diff --check`

- [ ] **Step 6: Run complete suite**

  Run: `python -m unittest discover`

  Record the exact total, failures, errors, skips, elapsed time, and number of
  new `test*.py` modules compared with baseline.

- [ ] **Step 7: Build twice and prove reproducibility**

  Run `python scripts/build_ankiaddon.py`, record path/file count/size/SHA-256,
  copy only the hash value, run the same build again, and compare hashes.
  Inspect archive names/content for forbidden files, high-confidence secrets,
  config, backup, optional dependencies/models, test fixtures/screenshots, temp
  output, and Anki user data.

- [ ] **Step 8: Commit**

  Commit message:
  `Add evaluations docs packaging and v0.14 release assets`

- [ ] **Step 9: Final review and branch-only push**

  Use `superpowers:requesting-code-review` for a whole-branch review against
  `858a908967a539e31ae6649d11aeb8b2acb528ae`. Resolve Critical/Important
  findings through one reviewed fix wave, rerun the complete verification, then
  push only:

  `git push public v0.14.0-pr27-universal-document-intelligence-engine`

  Confirm `public/main` is unchanged. Do not create a PR, tag, Release, or
  AnkiWeb update.
