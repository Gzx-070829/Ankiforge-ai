# AnkiForge AI v0.14 — Universal Document & Intelligence Engine

This document is the product-facing architecture summary for PR27. The
implementation contract is
[`docs/superpowers/specs/2026-07-25-universal-document-intelligence-design.md`](superpowers/specs/2026-07-25-universal-document-intelligence-design.md).

## Why v0.14 exists

v0.13 accepts pasted or lightly imported text and safely converts it into
reviewable card candidates. v0.14 adds a document layer that understands
structure before generation:

```text
files -> DocumentIR -> analysis -> structural chunks -> knowledge plan
      -> bounded generation -> quality/coverage/dedup -> Review -> Write
```

The Create → Review → Write workflow and its safety gates do not change.

## Core and optional backends

The packaged **AnkiForge Core** is standard-library-first and supports common
study files without external software. It owns the safe data model, native
parsers, deterministic intelligence, call budget, and review handoff.

**Optional Document Backends** are detected lazily and remain disabled until
the user chooses one:

- MarkItDown: broad local text conversion;
- Docling: advanced local document/PDF layout conversion;
- Pandoc: user-installed markup/office bridge;
- future local Companion protocol.

They are not bundled, imported at startup, downloaded, or installed by the
add-on. Their absence does not affect native importing. PDF is not parsed by
Core and OCR is not included.

## Native support

### Structured native import

- TXT, Markdown;
- DOCX, PPTX, XLSX;
- CSV, TSV;
- HTML;
- JSON, JSONL, safe XML;
- Jupyter Notebook (`.ipynb`, never executed);
- EPUB;
- SRT and WebVTT.

### Safe text/code import

- YAML, reStructuredText, Org, TeX/LaTeX, logs;
- SQL;
- Python, JavaScript, TypeScript, Java, C/C++, Rust, Go;
- shell and PowerShell.

These formats never execute scripts, macros, formulas, includes, notebook
cells, external relationships, or remote resources.

### PDF

Core provides a clear fallback: copy selectable text or enable a separately
installed local advanced backend. v0.14 does not ship a PDF parser, OCR model,
Docling, MarkItDown, or a cloud document service.

## Safe DocumentIR

Every importer produces the same immutable structure:

- safe document ID, title, type, and label;
- ordered sections and heading paths;
- paragraphs, lists, tables, code, formulas, quotes, captions, transcript
  blocks, and metadata;
- source locations such as page, slide, sheet/row, chapter, cell, line, or
  timestamp;
- structured warnings and bounded counts.

DocumentIR contains no full local path or API key. Diagnostic representations
contain counts and IDs, not source text. Explicit safe JSON serialization is
versioned and validated.

## Security model

v0.14 applies bounded file, batch, archive, XML/JSON depth, table, cell, block,
text, chunk, and AI-call limits. Archive traversal, symlinks, suspicious
compression, XXE/DOCTYPE/ENTITY, Office macros, external HTML resources,
LaTeX/Org/RST includes, and renamed binary files are rejected or skipped with
clear bilingual errors.

Optional subprocess adapters use:

- a known executable and fixed argument allowlist;
- `shell=False`;
- no URLs or credentials;
- a controlled environment/temp directory;
- timeout and output limits;
- cleanup and DocumentIR validation.

## Local intelligence

Before any Provider call, the deterministic analyzer reports document kind,
structure, language, density, definitions/comparisons/processes/formulas/code/
tables/transcript signals, estimated knowledge points, recommended card modes,
and warnings.

The chunker respects headings, lists, tables, code, formulas, slides, sheets,
chapters, pages, cells, and timestamps. Oversized content is split only after
structural grouping. Table chunks repeat their header.

The local planner balances coverage across sections, avoids repeated points,
and ties every knowledge point to source chunks. Auto mode routes points to a
supported card template; an explicit user-selected mode always wins. Cloze
remains unavailable in the public UI.

## Fast, Standard, and Deep

- **Fast:** local analysis/planning, grouped generation, deterministic quality
  and deduplication; normally 1–3 calls.
- **Standard (default):** one planner call, grouped generation, coverage and
  deduplication; the UI shows the plan-specific mandatory count and the
  8-call policy ceiling. A one-chunk run plans 2 calls.
- **Deep:** planner, generation, critic, at most one repair per point, and at
  most one missing-point supplement; the UI shows the plan-specific mandatory
  count (3 calls for one chunk) and never exceeds the 12-call policy ceiling.

The historical 1–3 / 3–8 / 4–12 values are policy envelopes, not mandatory
paid-call minimums. Small runs may complete below an envelope's lower bound;
no dummy call is dispatched or billed. Repair and supplement calls occur only
when deterministic source-grounding or coverage checks require them.

Standard and Deep show estimated blocks, calls, and candidates and require
confirmation. No mode automatically retries a failed request.

## Recovery and review

A run stores immutable safe snapshots, stage and per-chunk states, call count,
successful cards, and failures. One failed chunk does not discard siblings.
Retrying failures requires another click. New runs supersede old callbacks, and
closed windows ignore late results.

The critic can flag, request one repair, or reject, but it cannot override a
deterministic blocking issue. Coverage and cross-chunk deduplication are local
and explainable. All cards still enter Review, and the existing duplicate and
final-confirmation hard gates remain required before writing.

## Deck style adaptation

The model and bounded statistic summarizer are included. The feature is
off by default and limited to an explicitly chosen deck and at most 20 notes.
Only aggregate style statistics are eligible for generation context by
default. Full note examples require a separate future preview/confirmation.
Real collection sampling may remain a disabled preview until manual Anki
acceptance proves the operation safe.

## UI shape

Create gains a compact file queue, document summary, capability dialog, Auto
recommendation, intelligence selector, plan estimate, and bounded-run status.
Optional backends are detected but remain disabled until the user selects one
for the current window. Qt progress is delivered through Anki's main-thread
dispatcher and rechecks request ID/window lifetime before showing planning,
generation-group, review/repair, coverage, deduplication, or terminal stages.
Advanced details remain progressively disclosed. Queue rows show safe labels,
parser/status/counts/warnings and remove/reorder/retry actions, never absolute
paths.

Review gains short source chips and an optional view of the already extracted
source snippet. It never rereads arbitrary files from the review surface.

## Research and third-party boundaries

The source-backed decisions are recorded in:

- [`docs/research/document_processing_open_source_review.md`](research/document_processing_open_source_review.md);
- [`docs/research/third_party_license_and_security_matrix.md`](research/third_party_license_and_security_matrix.md).

MarkItDown, Docling and Docling Core are MIT; Chonkie is MIT; Pandoc is
GPL-2.0-or-later and remains an external executable. Models, binaries and
transitive dependencies have their own licenses. No third-party code is copied
into Core.

## PR27 release boundary

PR27 may build and push only
`v0.14.0-pr27-universal-document-intelligence-engine`. It does not merge main,
push public/main, update AnkiWeb, create a tag/Release, start a real Provider,
write a real Anki collection, install external tools, or upload a user file.
