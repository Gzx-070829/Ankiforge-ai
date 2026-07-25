# AnkiForge AI v0.14 Universal Document & Intelligence Engine Design

**Status:** Approved B+ architecture, implementation specification
**Baseline:** `v0.13.2-pr26-release-metadata-lifecycle-polish` at
`858a908967a539e31ae6649d11aeb8b2acb528ae`
**Target branch:** `v0.14.0-pr27-universal-document-intelligence-engine`
**Target version:** `0.14.0`

## 1. Product outcome

v0.14 turns the existing Create → Review → Write workbench into a bounded local
document-intelligence pipeline:

```text
explicitly selected local files
  -> safe type detection and bounded import
  -> immutable DocumentIR
  -> deterministic analysis
  -> structure-aware chunks
  -> local or explicitly requested LLM knowledge plan
  -> bounded generation run
  -> deterministic quality, coverage, and cross-chunk deduplication
  -> human review
  -> existing duplicate hard gate
  -> existing final-confirmation hard gate
  -> existing safe Anki writer
```

The default `.ankiaddon` remains self-contained, starts without optional
software, does not download models, does not scan user directories, and does
not make a network request until the user explicitly starts generation.

## 2. Non-negotiable safety invariants

1. API keys remain memory-only for the active window. They never enter document
   objects, logs, `repr`, Anki configuration, files, subprocess arguments, or
   optional backend requests.
2. Importing or analyzing a document never calls an AI Provider.
3. Parsing handles only files explicitly selected or dropped by the user. No
   URL input, recursive directory scan, linked-resource fetch, include
   expansion, macro execution, script execution, notebook execution, or remote
   asset load is allowed.
4. Optional backends are lazy, absent-safe, default-off, and not bundled. They
   cannot prevent AnkiForge or the native Core from starting.
5. One click creates one bounded generation run. There is no automatic retry,
   recursive generation, or unbounded repair/supplement loop.
6. Every final candidate remains subject to deterministic local validation and
   user review. An LLM critic cannot waive a blocking local issue.
7. The existing duplicate check, final confirmation, target validation,
   snapshot/replay protection, and safe writer remain hard gates.
8. No real Anki collection write, Provider call, external installation, tag,
   Release, main merge, public/main push, or AnkiWeb update occurs during PR27.

## 3. B+ two-layer architecture

### 3.1 AnkiForge Core

Core is always packaged. It uses the Python standard library wherever
practical and contains:

- the immutable DocumentIR and safe JSON renderer;
- type detection, archive/XML guards, limits, importer registry, and native
  importers;
- deterministic analyzer, structural chunker, local planner, template router,
  coverage checker, quality bridge, and local deduplicator;
- immutable generation-run models and call-budget enforcement;
- pure UI presentation models and file-queue state;
- optional-backend protocols and safe capability detection, but no optional
  backend dependency.

Core has no Qt or Anki dependency below the UI adapters.

### 3.2 Optional Document Backends

MarkItDown, Docling, Pandoc, and a future companion process live behind narrow
adapters:

- lazy probe only;
- disabled until explicitly selected;
- local files only;
- no API key field and no remote URL field;
- fixed executable/module identity and argument allowlist;
- `shell=False`, bounded environment, timeout, output limits, controlled temp
  directory, and cleanup;
- output must pass DocumentIR validation;
- failure produces a structured error and never crashes plugin startup.

Docling OCR, model downloads, remote services, MarkItDown plugins/cloud paths,
Pandoc filters/PDF engines/includes, and Chonkie cloud/model integrations are
not enabled in v0.14.

## 4. Concrete resource limits

All limits are applied before or during parsing, not after a large allocation.
They balance the existing 5 MiB text limit with bounded Office/EPUB containers.

| Constant | Value | Rationale |
| --- | ---: | --- |
| `MAX_SOURCE_FILE_BYTES` | 10 MiB | Allows ordinary Office files while rejecting large media-heavy inputs. |
| `MAX_TEXT_FILE_BYTES` | 5 MiB | Preserves the existing plain-text safety envelope. |
| `MAX_TOTAL_BATCH_BYTES` | 25 MiB | Bounds one explicit multi-file import. |
| `MAX_FILES_PER_BATCH` | 20 | Keeps queue, UI, and parsing work understandable. |
| `MAX_ARCHIVE_MEMBERS` | 2,048 | Retains the proven DOCX guard across OOXML/EPUB. |
| `MAX_ARCHIVE_UNCOMPRESSED_BYTES` | 64 MiB | Prevents large aggregate archive expansion. |
| `MAX_ARCHIVE_COMPRESSION_RATIO` | 100.0 | Rejects suspicious highly compressed members. |
| `MAX_MEMBER_BYTES` | 20 MiB | Bounds a single XML/shared-string/chapter member. |
| `MAX_DOCUMENT_BLOCKS` | 20,000 | Prevents pathological IR growth. |
| `MAX_TABLE_ROWS` | 10,000 | Allows useful datasets without importing whole workbooks. |
| `MAX_TABLE_COLUMNS` | 256 | Bounds wide-sheet memory and UI output. |
| `MAX_CELL_CHARS` | 32,000 | Near the practical spreadsheet cell ceiling. |
| `MAX_JSON_DEPTH` | 64 | Prevents recursive-depth abuse. |
| `MAX_XML_DEPTH` | 64 | Rejects pathologically nested XML. |
| `MAX_XML_ELEMENTS` | 100,000 | Retains the proven DOCX element bound. |
| `MAX_TEXT_CHARS` | 5,000,000 | Bounds normalized text and serialization. |
| `MAX_NOTEBOOK_OUTPUT_CHARS` | 100,000 | Keeps optional short text outputs bounded. |
| `MAX_CHUNK_CHARS` | 12,000 | Leaves margin below the 50,000-character Provider limit. |
| `TARGET_CHUNK_CHARS` | 6,000 | Keeps related structure together without oversized calls. |
| `MAX_DOCUMENT_CHUNKS` | 48 | Bounds planning and UI state before AI budgeting. |
| `MAX_AI_CALLS_PER_RUN` | 12 | Hard ceiling shared by planner, generation, critic, repair, and supplement. |

Files or documents beyond these limits fail with an actionable safe error;
the UI never silently truncates a file without a warning.

## 5. DocumentIR

`ankiforge_ai/document/models.py` owns dependency-free frozen dataclasses:

```text
DocumentIR
  schema_version
  document_id
  title
  language_hint
  source_type
  source_label
  metadata
  sections
  warnings
  original_char_count
  extracted_char_count

DocumentSection
  section_id
  heading
  heading_path
  location
  blocks

DocumentBlock
  block_id
  kind
  text
  location
  metadata

SourceLocation
  file_label, page, slide, sheet, row_start, row_end, cell_range,
  section, timestamp_start, timestamp_end, notebook_cell,
  line_start, line_end

DocumentWarning
  code, severity, message_key, action_key, location
```

`BlockKind` contains `heading`, `paragraph`, `list`, `list_item`, `table`,
`code`, `formula`, `quote`, `caption`, `transcript`, and `metadata`.
Metadata accepts only `str`, `int`, `float`, `bool`, or `None`, with bounded
keys and values. Constructors freeze mappings with immutable proxies and
normalize all sequences to tuples.

Safety rules:

- IDs are stable SHA-256-derived identifiers, not paths.
- `source_label` is a sanitized basename or user-facing label, maximum 120
  characters.
- no model stores an absolute path;
- `repr` reports IDs, labels, counts, and kinds, never full block text;
- `to_safe_dict()` is JSON-compatible and bounded;
- full content is included only by explicit serialization functions, not
  diagnostic representations;
- validation rejects unknown kinds, duplicate IDs, invalid parent references,
  over-limit counts, unsafe metadata, and leaked absolute paths.

Public functions:

- `document_to_plain_text(document)`;
- `document_to_safe_markdown(document)`;
- `document_summary(document)`;
- `count_blocks_by_kind(document)`;
- `get_safe_source_label(value)`;
- `validate_document_ir(document)`;
- `document_to_safe_json(document)` and `document_from_safe_json(payload)`.

## 6. Detection, registry, fallback, and errors

Detection combines extension, prefix bytes, BOM, ZIP member names, Office
content types, EPUB `mimetype`/container, text/binary heuristic, XML root, and
JSON/IPYNB schema hints. Extension mismatch becomes a warning or rejection
according to risk; binary data renamed `.txt` is rejected.

`DocumentImporter` exposes:

```text
importer_id
supported_extensions
availability()
inspect(path, limits) -> ImportInspection
import_document(path, limits) -> DocumentIR
```

`ImporterCapability` reports bilingual display names, support level,
structure/table/image/formula support, external dependencies, unavailability,
and security notes. `SupportLevel` is exactly:

- `native_structured`;
- `native_text`;
- `optional_advanced`;
- `fallback_only`;
- `unsupported`.

Registry selection is deterministic. A failure may fall back only when the
capability record explicitly names that fallback. Binary or malformed content
is never decoded as generic text. Optional importers are registered as lazy
factories and cannot import third-party modules during startup.

Errors use stable codes, bilingual copy keys, severity, and one suggested
action. `repr` and UI text contain no absolute path, source body, traceback,
credential, subprocess environment, or raw backend output.

## 7. Native format contract

| Format | Level | Native behavior and limitations |
| --- | --- | --- |
| TXT | native text | BOM/encoding detection, paragraphs and line locations; no execution. |
| MD/Markdown | native structured | headings, lists, fenced code, simple tables, safe scalar frontmatter title/tags; no includes. |
| DOCX | native structured | paragraphs, heading styles, lists, simple tables, image placeholders; no macros, embedded objects, external relationships, or OCR. |
| PPTX | native structured | slide order/title/text/bullets/simple tables and safe notes when present; no embedded objects or external links. |
| XLSX | native structured | visible sheets, bounded cells/rows, headers, merged-cell metadata, formula text/cached value only; hidden sheets skipped with warning. |
| CSV/TSV | native structured | safe delimiter/header detection, row groups, repeated header context. |
| HTML/HTM | native structured | headings, paragraphs, lists, tables, pre/code, quotes, image alt; script/style/iframe removed and no resources fetched. |
| JSON/JSONL | native structured | bounded path/value and record blocks; no single giant block. |
| XML | native structured | DTD/entity rejected, bounded element/depth walk, tag-path sections. |
| IPYNB | native structured | markdown/code cells, bounded short text output, image/base64/large output skipped; code never executed. |
| EPUB | native structured | validated container, OPF spine order, local XHTML chapters; remote resources ignored. |
| SRT/VTT | native structured | timestamps and merged adjacent captions; no per-caption card explosion. |
| YAML/YML/RST/Org/TeX/LaTeX/log | native text | headings/comments/code-like blocks only; includes and commands never executed. |
| SQL/Python/JS/TS/Java/C/C++/Rust/Go/shell/PowerShell | native text | preserve code/comment groups and line ranges; never execute. |
| PDF | fallback only / optional advanced | Core performs no PDF parsing or OCR. It gives copy-text guidance or routes to an explicitly selected installed backend. |

The legacy `import_source_file()` remains compatible by rendering one
DocumentIR to an `ImportedSource`. The new queue and intelligence pipeline use
DocumentIR directly.

## 8. Archive and XML policy

ZIP inspection rejects:

- absolute member paths, `..` traversal, drive-prefixed paths, encrypted
  members, symlink-like Unix mode entries, duplicate normalized paths,
  excessive members, oversized members/aggregate expansion, suspicious
  compression ratio, and missing/invalid format-required members.

XML parsing rejects `DOCTYPE` and `ENTITY` in normalized bytes, never resolves
external entities, bounds element count/depth/text, and ignores external
relationships. Office macros, OLE objects, scripts, and linked resources are
never opened. EPUB paths are resolved within the archive only.

## 9. Optional backend protocol

`DocumentBackend` exposes `probe()`, `capabilities()`,
`convert_local_file()`, `version_info()`, and `health_check()`.

The command runner:

- accepts no URL and validates an explicitly selected regular local file;
- resolves a configured executable to one absolute path;
- uses an argument tuple, `shell=False`, a minimal environment, controlled
  working/temp directory, and no credential variables;
- applies a 60-second default timeout, 5 MiB stdout limit, and 64 KiB
  sanitized stderr limit;
- terminates the process tree on timeout/cancel where supported;
- cleans temp files in `finally`;
- rejects invalid UTF-8/JSON, oversized output, absolute paths in output, and
  invalid DocumentIR.

Adapter status:

- MarkItDown: optional adapter to narrow local conversion/Markdown output;
  plugins and remote features disabled.
- Docling: optional CLI/companion adapter; OCR is off; no model download is
  initiated by AnkiForge.
- Pandoc: optional external executable only, fixed input allowlist,
  `--sandbox`, no filters/includes/templates/PDF engine/user arguments.
- Companion: protocol foundation only in v0.14.

Companion request/response JSON includes protocol version, request ID,
capability query, local file token/path supplied by the user action, progress,
cancel, structured errors, and DocumentIR JSON. It contains no API key, Provider
configuration, remote URL, arbitrary command, or collection identifier.

## 10. Analysis, chunking, and planning

`DocumentAnalysis` is deterministic and reports dominant language, document
kind, section/block counts, density, definitions/comparisons/processes/formulas/
code/tables/transcript flags, estimated knowledge points, recommended modes,
warnings, and confidence. It does not call AI.

The chunker is structure-first:

- headings stay with owned blocks;
- lists stay intact when possible;
- tables repeat a serialized header in row chunks;
- code/formulas stay with neighboring explanations;
- slide, sheet/table, chapter, page, cell, and timestamp boundaries are
  retained;
- adjacent small blocks under one heading may merge;
- only over-budget blocks receive bounded secondary splitting;
- chunks never contain absolute paths.

`KnowledgePlan` and `KnowledgePointPlan` use immutable IDs, source chunk IDs,
source locations, priorities, recommended template, and internal rationale.
The local planner balances sections, deduplicates candidate points, prevents
one-detail floods, and ensures every point references source chunks.

Fast uses only the local planner. Standard and Deep may make one bounded
planner call over outline/chunk summaries; malformed, ungrounded, or failed
planner output falls back to the local plan without automatic retry.

## 11. Template routing and intelligence levels

Public modes include `auto`, existing selectable modes, plus
`code_understanding`, `table_relationship`, and
`transcript_summary_candidate`. Cloze remains internal and non-selectable.

Auto routing returns template ID, confidence, reason code, and source
constraints from analysis, block kinds, and point type. A user-selected mode
always overrides Auto.

| Level | Default behavior | Call policy envelope |
| --- | --- | --- |
| Fast | local analysis/chunking/planning, grouped generation, deterministic quality/dedup | 1–3 calls, no critic/repair |
| Standard (default) | one planner call, bounded grouped generation, quality, coverage, dedup | 3–8 calls; at most one blocking-card repair if enabled |
| Deep | planner, generation, critic, at most one repair per point, coverage, at most one supplement | 4–12 calls |

Standard/Deep show chunk count, call range, and card-count estimate and require
confirmation before the first call. No currency estimate is shown.

The table ranges are policy envelopes, not hard paid-call minimums. The UI
also shows the plan-specific mandatory count: grouped generation batches plus
planner for Standard, and plus planner and critic for Deep. Small inputs may
complete below the envelope's lower bound, and the runtime never makes dummy
calls merely to satisfy that lower bound.

## 12. Generation lifecycle, partial failure, and budget

`GenerationRun` stores only safe immutable snapshots and bounded results:
run/request IDs, DocumentIR snapshot/hash, settings snapshot, level, stage,
chunk states, plan, cards, failed chunks, call count/limit, and status. Material
and credentials are `repr=False`; API keys are absent.

Stages are `analyzing`, `planning`, `generating`, `reviewing`, `repairing`,
`checking_coverage`, `deduplicating`, `completed`, `failed`, and `superseded`.
Chunk states are `pending`, `running`, `succeeded`, `failed`, and `skipped`.

Every Provider call reserves budget before dispatch. The run cannot exceed 12
calls. A point receives at most one repair; a run receives at most one coverage
supplement; failed chunks are retained and retried only after a new explicit
click. Successful candidates survive sibling failure. A newer run invalidates
all older callbacks, and closing the window makes late callbacks no-ops.

## 13. Critic, coverage, and deduplication

Critic decisions are `pass`, `flag`, `repair`, or `reject`. Raw reasoning is
not displayed or persisted. A repair must remain source-grounded and is
revalidated locally. Deterministic blocking issues remain authoritative.

Coverage reports missing high-priority points, uncovered sections, section
imbalance, over-generation, duplicate point coverage, and card-count overflow.
Only missing high-priority points may be supplemented, once, within budget.

Cross-chunk dedup first uses deterministic front/back canonicalization,
Unicode/punctuation/whitespace normalization, token/bigram overlap, safe
similarity thresholds, and source overlap. No embedding model is required.
Semantic dedup is protocol-only and default-off.

## 14. DeckStyleProfile

The pure-Python profile model and bounded summarizer are implemented, but real
collection sampling remains an opt-in UI preview unless manual Anki acceptance
proves the Anki operation safe.

When enabled, only the explicitly selected deck is read, with at most 20 notes.
The default Provider payload contains statistics only: field names,
front/back length ranges, bullet/HTML ratios, common layout patterns, common
tags, and preferred template hints. Full collection scans and note mutation are
forbidden. Sending examples requires a separate preview and confirmation and is
not enabled by default.

## 15. UI and Anki operation boundaries

Create remains progressively disclosed:

- compact file queue and drag area;
- capability/help entry;
- parse status and document summary;
- Auto recommendation;
- Fast/Standard/Deep selector;
- plan/call/card estimate;
- one explicit Generate action and bounded-run progress.

The immutable run records every internal stage. The v0.14 Qt integration shows
coarse in-progress copy and the terminal stage; live per-stage delivery is
deferred rather than sending worker-thread callbacks directly to widgets.

Each queue row shows safe filename, detected type, importer, status, structural
counts, extracted characters, warning, remove, reorder, and retry. It never
shows an absolute path. One failure does not clear successful rows.

Pure file parsing/conversion uses an immutable snapshot in a
`QueryOp(...).without_collection()` or equivalent `taskman` worker because it
does not touch `mw.col`. UI values are captured first and UI changes occur only
on the main thread. Collection reads for an opted-in deck profile use a
serialized `QueryOp`. Final write remains on the established safe path; a
future migration to `CollectionOp` requires separate Anki acceptance and is not
silently introduced here.

Review shows short source chips such as `Page 6`, `Slide 4`,
`Sheet "Results", Row 2`, `Chapter 3`, `Cell 7`, or a timestamp. “View source
snippet” shows only the already extracted bounded block text.

## 16. Errors and i18n

The required stable error codes are implemented with complete Chinese and
English text:

`unsupported_file_type`, `importer_unavailable`,
`optional_backend_missing`, `file_too_large`, `batch_too_large`,
`too_many_files`, `archive_too_large`, `suspicious_archive`,
`invalid_office_archive`, `xml_not_safe`, `document_empty`,
`document_too_complex`, `table_too_large`, `notebook_output_too_large`,
`external_backend_timeout`, `external_backend_failed`,
`backend_output_invalid`, `planning_failed`,
`generation_budget_exceeded`, `chunk_generation_failed`,
`coverage_incomplete`, `stale_generation_result`, and
`deck_style_unavailable`.

User copy names actions and remediation, never internal class names, rule IDs,
raw prompts, tracebacks, or arbitrary backend stderr.

## 17. Tests, fixtures, and benchmark

All production behavior follows red-green-refactor TDD. Tests remain runnable
without Anki, network, Provider, optional backend, Pandoc, or user files.

Fixtures cover every native format, archive/XML attacks, renamed binary input,
hidden sheets, formula cells, external HTML resources, includes, notebook
output, and multidisciplinary content. Binary fixtures are generated
deterministically by a committed fixture builder so their contents are
reviewable and reproducible.

The offline benchmark reports parse pass rate, structure preservation, source
location coverage, chunk distribution, planning coverage, duplicate/warning/
blocking rates, template-routing accuracy, and per-fixture failure reasons. It
uses deterministic planning and fake Provider outputs only.

## 18. Version, package, docs, and screenshots

Runtime, manifest, `human_version`, README, release notes, AnkiWeb draft, and
version-consistency tests use `0.14.0`.

The package excludes optional tools, models, temp output, source documents,
tests/fixtures, screenshots, config, credentials, logs, backups, and Anki user
data. Two final builds must have identical SHA-256 and pass source/package
consistency plus forbidden-file and secret scans.

Offline screenshots are explicitly labeled **Mock UI preview**. No screenshot
is labeled as real Anki unless captured in a genuine Anki session. PR27 does not
start Anki, call a real Provider, or write a real collection.

## 19. Explicit limitations and deferred work

- Native PDF parsing and OCR are not implemented. PDF remains fallback-only or
  optional-backend processing.
- Docling/MarkItDown/Pandoc/Chonkie are not bundled or auto-installed.
- Companion is a protocol foundation, not a separately shipped application.
- Semantic/embedding dedup is protocol-only.
- Real DeckStyleProfile sampling may remain disabled preview pending manual
  Anki acceptance.
- Full Undo exposure and a CollectionOp write migration are not silently added.
- Audio/video, ASR, images, remote URLs, web import, model downloads, and cloud
  document parsing are outside v0.14.
- Cloze remains non-selectable.

These limitations must be reported precisely; protocol foundations and absent
optional dependencies are not described as complete end-user features.
