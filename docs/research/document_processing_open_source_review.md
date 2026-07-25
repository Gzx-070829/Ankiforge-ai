# Document-processing open-source review (v0.14)

**Research checked:** 2026-07-25. This is a design and adoption record, not an
implementation commitment or a guarantee of future upstream compatibility.

## Decision

AnkiForge will use a provider boundary around document conversion and retain a
small AnkiForge-owned, typed document intermediate representation (IR). The
default installation must start and remain usable with **no third-party
converter, model, plugin, external executable, or network connection**.

| Candidate | Checked version / revision | Role and adoption decision |
| --- | --- | --- |
| [MarkItDown](https://github.com/microsoft/markitdown/releases) | `0.1.6`, `v0.1.6`, `e144e0a` | Preferred first optional local conversion sidecar; prototype only after controlled local-file tests. |
| [Docling](https://github.com/docling-project/docling/releases) | `2.115.0`, `v2.115.0`, `b0a15d2` | Optional advanced/layout sidecar, not in the v0.14 default installer. |
| [Docling Core](https://github.com/docling-project/docling-core/releases) | `2.87.1`, `v2.87.1`, `0215808` | Borrow its design ideas; do not depend on it initially. |
| [Pandoc](https://github.com/jgm/pandoc/releases/tag/3.10.1) | `3.10.1`, `d6011e4465d4cb0d0a6fb872dab3ed089f404a75` | Optional separately installed executable, called only by a worker. |
| [Chonkie](https://github.com/feyninc/chonkie/releases/tag/v1.7.0) | `v1.7.0`, `0a6baea1a42c9afe9b3bc31ecb37739e744bb1ec` | Optional post-conversion text chunker; smallest local install only. |
| [Anki](https://github.com/ankitects/anki/releases/tag/26.05) | `26.05`, `e64c6b1aee3e8d668fb8bbe084beada8e070d985` | Runtime constraint: work is off the UI thread; collection writes are isolated and undoable. |

Versions must be pinned by version **and hash** in any release build. Moving
branch references are not an acceptable production lock.

## Comparison and provider boundaries

| Provider | Useful input/output scope | Dependencies, binaries, and models | Local/network boundary | v0.14 operating policy |
| --- | --- | --- | --- | --- |
| MarkItDown | Broad text-oriented conversion to Markdown: PDF, Office, HTML, text/data, EPUB, images, audio, archives and more. [Supported formats](https://github.com/microsoft/markitdown#readme) are broader than AnkiForge's initial allowlist. | Python `>=3.10`; base Python packages plus format extras such as `pdfplumber`, `mammoth`, `python-pptx`, `pandas`, and `openpyxl`. No normal Office/PDF executable. Audio may use user-managed ExifTool/FFmpeg. | Generic `convert()` accepts paths, streams, `file:`, `data:`, and HTTP(S) URIs. It can invoke web/YouTube/Azure/LLM paths. Use controlled streams or `convert_local()` only; reject URIs. [Security guidance](https://github.com/microsoft/markitdown#security-considerations). | Optional sidecar; selected local formats only (`pdf`, `docx`, `pptx`, `xlsx` initially); no `[all]`, network, LLM client, Azure, audio, YouTube, or auto-discovered plugins. |
| Docling | Structured document conversion with local layout/table/reading-order capabilities; exports Markdown/text/HTML and a rich document model. [Formats](https://docling-project.github.io/docling/usage/supported_formats/) include PDF, Office, HTML, images and many specialist types. | Python `>=3.10`; standard package adds PDF parsers, Torch/Torchvision, OCR/model packages and Hugging Face support. PDF models download to the cache by default. Legacy Office needs LibreOffice; video needs FFmpeg; particular OCR/HTML features can need Tesseract, Playwright, or other runtimes. | Public conversion accepts a path or URL. Remote vision is separately gated by `enable_remote_services=True`, but first-use model download is still outbound network activity. [Offline/model controls](https://docling-project.github.io/docling/usage/advanced_options/). | Separate advanced sidecar only, after explicit model-download, disk-use, cache-location, and offline-mode consent. Remote services and automatic enrichment remain off. |
| Pandoc | Universal markup/document conversion; use a narrow allowlist such as CommonMark/GFM, DOCX, ODT and controlled text output. It is not a general PDF-text extractor. [Manual](https://pandoc.org/MANUAL.html). | Standalone Windows executable for normal conversion; no Python dependency. PDF output needs a separately managed engine (e.g. TeX); filters may need runtimes such as Python. | Include directives, HTML iframe/resource handling, filters and custom writers may read files or access networks. Pandoc recommends `--sandbox`, with limits. [Security note](https://pandoc.org/MANUAL.html#A-note-on-security). | User/admin-installed executable only; call with absolute path, stdin/stdout, fixed arguments, `--sandbox`, timeout and memory/input/output caps. No filters, Lua, PDF engine, arbitrary resource/data paths or user switches. |
| Chonkie | In-process text chunking, not a general document parser. It accepts text/Chunk data after conversion. [Installation matrix](https://docs.chonkie.ai/oss/installation). | Python `>=3.10`; base packages include `chonkie-core` and `tokie`. Semantic/neural/code and provider extras add native wheels, models, Torch, or SDKs. No basic external executable. | Basic local chunking can be offline. Recipes/model loading can download from Hugging Face; provider embeddings and vector-store integrations can transmit content. [Hubbie](https://docs.chonkie.ai/oss/utils/hubbie). | Optional smallest local wheel set or helper runtime. No `chonkie[all]`, model/recipe download, provider embedding, vector DB, server, or silent cloud fallback. |

## Non-negotiable defaults

- **Nothing is bundled by default:** MarkItDown, Docling, Docling Core,
  Pandoc, and Chonkie are not bundled with the normal v0.14 add-on.
  Their absence is an unavailable capability with a clear remediation message,
  never a startup, import-basic-path, or UI failure.
- **Local-only is the default:** imported input originates from a user-selected
  file/approved stream. Reject URL and `file:` input strings from documents;
  canonicalize paths; validate type with extension plus magic bytes; constrain
  bytes, pages, archive expansion, duration, memory and worker lifetime.
- **Plugins, remote services, and OCR are default-off:** no entry-point
  discovery, web import, cloud OCR/vision/LLM, provider embeddings, remote
  models, or automatic weight download. Each future exception needs a named
  UI action with the destination, data type, executable/model, disk cost, and
  cancellation behavior disclosed first.
- **Least privilege and isolation:** parsers execute in a low-privilege worker
  with an allowlisted input root and controlled temp directory. Input cannot
  select an executable, model cache, resource path, LibreOffice behavior, or
  remote endpoint.

## Architecture to borrow, not code to copy

The useful common design is a conversion protocol rather than any project's
runtime:

`selected local file -> provider adapter -> normalized IR + diagnostics -> deterministic Markdown/text renderer -> structure-aware chunks -> candidate cards -> review -> undoable collection write`

The IR should preserve document metadata, ordered headings/paragraphs/lists/
tables/code/quotes, image placeholders, source page or character anchors,
provenance, and diagnostics. This borrows Docling Core's typed tree,
lossless-serialization, serializer, and structure-aware chunking ideas
([project overview](https://github.com/docling-project/docling-core#readme))
without coupling the product to its dependency graph or release cadence.

Each adapter declares its exact version, accepted MIME/extensions, output
features, required executable/models, local/network permission, and whether
OCR is available. The adapter returns output plus detected type, selected
pipeline, warnings, skipped capabilities, fallback, duration and safe error
code. Parsing, normalizing, rendering, chunking, AI generation and Anki
mutation are deliberately separate phases; parser quirks cannot silently turn
into cards.

## Anki AI/open-source interaction and evaluation references

These are first-party-source design references, not dependencies. None supplies
the source-citation traceability required for factual cards; AnkiForge retains
per-card evidence, source locator/hash, validator result, and reviewer
decision.

- **[raine/anki-llm](https://github.com/raine/anki-llm)** — checked `main`
  [`4e84390b0f0c3f1ff0f2fd87e241bb0acf2c97d4`](https://github.com/raine/anki-llm/tree/4e84390b0f0c3f1ff0f2fd87e241bb0acf2c97d4), latest observed release
  [`v2.0.18`](https://github.com/raine/anki-llm/releases/tag/v2.0.18),
  [MIT](https://github.com/raine/anki-llm/blob/4e84390b0f0c3f1ff0f2fd87e241bb0acf2c97d4/LICENSE).
  It is the primary interaction/evaluation reference: borrow staged candidate
  review, per-card accept/reject/regenerate, field-level duplicate diffs,
  preview samples, run IDs, snapshots and conflict-aware rollback. Reject an
  LLM `pass` or raw transcript as sufficient quality/provenance; require
  deterministic validators, source grounding and an explicit evidence panel.
- **[ankimcp/anki-mcp-server](https://github.com/ankimcp/anki-mcp-server)** —
  checked `main` [`3cd6ea82aff4237a15947f7e36207ee2730e82dd`](https://github.com/ankimcp/anki-mcp-server/tree/3cd6ea82aff4237a15947f7e36207ee2730e82dd), latest observed release
  [`v0.22.5`](https://github.com/ankimcp/anki-mcp-server/releases/tag/v0.22.5),
  [MIT](https://github.com/ankimcp/anki-mcp-server/blob/3cd6ea82aff4237a15947f7e36207ee2730e82dd/LICENSE).
  It is the safety/workflow-test reference: borrow explicit review-state
  transitions, read-only inspection, affirmative destructive-action parameters,
  deterministic sample decks, reviewer smoke tests, and transport/security
  tests. Reject a default write API, tunnel, or remote collection control.
- **[dhkim0124/anki-mcp-server](https://github.com/dhkim0124/anki-mcp-server)**
  — checked `main` [`ad978e4b2c818639391c3eff3ea4a6c30e722edb`](https://github.com/dhkim0124/anki-mcp-server/tree/ad978e4b2c818639391c3eff3ea4a6c30e722edb); no release was published when
  checked; [MIT](https://github.com/dhkim0124/anki-mcp-server/blob/ad978e4b2c818639391c3eff3ea4a6c30e722edb/LICENSE).
  Borrow impact preflight plus a separate `confirm=True`-style action,
  untrusted-template/style validation, and partial-batch result testing.
  Reject model instructions as a consent or safety control; encode policies in
  the action schema, add real-Anki integration coverage, and preserve evidence.
- **[anki-ai-dynamic-cards](https://github.com/AleksandrFurmenkovOfficial/anki-ai-dynamic-cards)**
  — checked `main` [`211a587724bfefa70e0e8dc74f3fb2aeee265f8a`](https://github.com/AleksandrFurmenkovOfficial/anki-ai-dynamic-cards/tree/211a587724bfefa70e0e8dc74f3fb2aeee265f8a), latest observed release
  [`v4`](https://github.com/AleksandrFurmenkovOfficial/anki-ai-dynamic-cards/releases/tag/v4),
  [MIT](https://github.com/AleksandrFurmenkovOfficial/anki-ai-dynamic-cards/blob/211a587724bfefa70e0e8dc74f3fb2aeee265f8a/LICENSE).
  Borrow only an opt-in, clearly separate “another example” interaction for
  transient practice. Reject its credential/provenance model: never put API
  secrets in card HTML/JavaScript or send them from rendered-card contexts, and
  never use unpersisted, uncitable generated text as stable knowledge-card
  content.

## Anki execution boundary

Capture UI and collection choices on the main thread. Run file reading,
subprocess conversion, chunking and any explicitly approved request in a
`QueryOp`; use `.without_collection()` only after all collection/UI data is
captured and the worker cannot touch `mw.col`. Update progress/UI on the main
thread. Only the confirmed final note/tag/media write uses a `CollectionOp` as
one undoable action. This follows Anki's [background-operation guidance](https://addon-docs.ankiweb.net/background-ops.html)
and protects collection bookkeeping described in its [collection API guidance](https://addon-docs.ankiweb.net/the-anki-module.html).

## References

- MarkItDown: [package metadata](https://raw.githubusercontent.com/microsoft/markitdown/main/packages/markitdown/pyproject.toml), [plugin behavior](https://github.com/microsoft/markitdown#plugins), [OCR plugin](https://raw.githubusercontent.com/microsoft/markitdown/main/packages/markitdown-ocr/README.md).
- Docling: [features](https://docling-project.github.io/docling/), [installation/OCR engines](https://docling-project.github.io/docling/getting_started/installation/), [package metadata](https://raw.githubusercontent.com/docling-project/docling/main/pyproject.toml).
- Pandoc: [installation](https://pandoc.org/installing.html) and [manual](https://pandoc.org/MANUAL.html).
- Chonkie: [OSS overview](https://docs.chonkie.ai/common/open-source) and [v1.7.0 metadata](https://github.com/feyninc/chonkie/blob/v1.7.0/pyproject.toml).
