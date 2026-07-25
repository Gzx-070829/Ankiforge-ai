# Third-party license and security matrix (v0.14)

**Research checked:** 2026-07-25. This matrix records reviewed upstream
licensing and integration conditions. It is an engineering record, not legal
advice; release packaging requires a pinned SBOM, third-party notices and
legal review of every shipped artifact.

## Release posture

The v0.14 default add-on contains no MarkItDown, Docling/Docling Core, Pandoc,
or Chonkie runtime. **Third-party absence must not break startup.** An optional
provider is capability-detected and may fail locally with actionable install,
version, or model diagnostics. It must never be imported eagerly at Anki
startup.

All optional processing is local-file-only by default. Plugins, remote
services, OCR, model downloads, provider embeddings, vector stores, URL
conversion and web/YouTube import are **off by default**. A user must opt in
to each egress or installation action after seeing what data leaves the device
and what executable, model, cache, disk space or credentials are involved.

## License, packaging, and security matrix

| Component (checked ref) | License and redistribution implication | Dependencies / binaries / models | Security and data boundary | v0.14 decision |
| --- | --- | --- | --- | --- |
| [MarkItDown 0.1.6](https://github.com/microsoft/markitdown/releases), `v0.1.6` / `e144e0a` | [MIT](https://raw.githubusercontent.com/microsoft/markitdown/main/LICENSE): retain notices for copied/redistributed portions. Microsoft trademark guidance still applies. Transitive wheels and cloud services have independent terms. | Python `>=3.10`; base plus per-format extras. Optional ExifTool and FFmpeg for parts of audio. Avoid `[all]`. | `convert()` can process local paths, streams and URI schemes including HTTP(S); it runs with worker privileges. Plugins can import installed code. OCR plugin may send images/pages to an OpenAI-compatible service. | Do not bundle. Optional isolated sidecar with selected local extras only; controlled stream/`convert_local()`, no URIs, no plugin discovery, no Azure/LLM/OCR/audio/YouTube. |
| [Docling 2.115.0](https://github.com/docling-project/docling/releases), `v2.115.0` / `b0a15d2` | MIT package metadata ([source](https://raw.githubusercontent.com/docling-project/docling/main/packages/docling/pyproject.toml)); retain notices. Its model graph and every wheel/system component need separate review. | `docling` installs `docling-slim[standard]`; PDF/layout/OCR stack includes Torch and model dependencies. Legacy Office: LibreOffice; video: FFmpeg; OCR variants can use Tesseract/others; HTML may use Playwright. | Inputs may be paths or URLs. Remote vision requires explicit enablement, but default first use can download model weights. A worker still has its filesystem permissions. | Do not bundle or install in the default profile. Advanced sidecar only after explicit model-download/cache/offline consent. No remote services, automatic download, plugin activation, VLM/ASR/OCR by default. |
| [Docling Core 2.87.1](https://github.com/docling-project/docling-core/releases), `v2.87.1` / `0215808` | [MIT](https://raw.githubusercontent.com/docling-project/docling-core/main/LICENSE); retain notice if adopted. | Python `>=3.10`; types, export/serialization and chunking, not parsers/PDF models. | No adoption means no runtime surface in v0.14. | Do not bundle or depend on it now; borrow IR/serializer/chunker concepts only. |
| [Docling model artifacts](https://huggingface.co/docling-project/docling-models) | Repository labels include **CDLA-Permissive-2.0** and **Apache-2.0**; model weights are distinct redistributable artifacts, not automatically covered by Docling's MIT license. | Layout, TableFormer, picture classifier, code/formula and RapidOCR artifacts can be cached/downloaded; hardware/Torch compatibility varies. | First-use downloads are outbound network activity even when user documents stay local. | Do not ship or auto-download. If later enabled, pin artifact hashes, show license/notices/size/cache location, support local pre-provisioned artifacts and cancellation. |
| [Pandoc 3.10.1](https://github.com/jgm/pandoc/releases/tag/3.10.1), `3.10.1` / `d6011e4465d4cb0d0a6fb872dab3ed089f404a75` | [GPL-2.0-or-later](https://github.com/jgm/pandoc/blob/3.10.1/COPYRIGHT). If redistributed, ship appropriate GPL notices and source/offer obligations for the exact platform artifact; obtain packaging review. | Separate executable; normal Windows package is self-contained. PDF path needs a separate engine; filters may require additional runtimes. | Filters/custom writers can access filesystem; includes and HTML resources can expose paths/URLs. `--sandbox` helps but does not secure filters/PDF engines. | **GPL-2.0-or-later external executable only.** Not bundled, linked, embedded or invoked with filters/PDF engines. Call through fixed stdin/stdout arguments with `--sandbox`, hard caps, timeout and absolute executable path. |
| [Chonkie v1.7.0](https://github.com/feyninc/chonkie/releases/tag/v1.7.0), `v1.7.0` / `0a6baea1a42c9afe9b3bc31ecb37739e744bb1ec` | [MIT](https://github.com/feyninc/chonkie/blob/v1.7.0/LICENSE); retain notice plus resolved transitive notices. | Python `>=3.10`; base is `chonkie-core`/`tokie` etc. Extras may add Torch, Transformers, SentenceTransformers, tree-sitter, provider SDKs or native wheels. | Local chunking can remain in-process. Recipes/models can download; cloud embedding/LLM and vector-store paths transmit/store chunks; `FileFetcher` and JSON export touch local files. | Do not bundle by default; optional minimal hash-locked helper/runtime for local text chunking only. No `[all]`, recipes/models, cloud, vector DB/API server or auto-export. |
| [Anki 26.05](https://github.com/ankitects/anki/releases/tag/26.05), `26.05` / `e64c6b1aee3e8d668fb8bbe084beada8e070d985` | [AGPL-3.0-or-later with listed exceptions](https://github.com/ankitects/anki/blob/26.05/LICENSE). The add-on remains independently packaged, but redistribution questions require review. | Add-on Python dependencies must be bundled if used; do not assume system Python visibility. [Official guidance](https://addon-docs.ankiweb.net/python-modules.html). | Worker operations must not access Qt or mutate the collection. Collection APIs preserve sync/validity bookkeeping. | Preserve default startup without optional providers. Use `QueryOp` for conversion/chunking; final confirmed mutation only in undoable `CollectionOp`. |

## Required security controls

1. **Input containment:** use the file picker/controlled streams; canonicalize
   approved paths; reject document-supplied URI strings; validate magic bytes
   and extension; apply size/page/archive/time/memory limits.
2. **Process containment:** use a least-privilege worker, a controlled temp
   directory, fixed executable paths and argument vectors (never a shell).
   Do not let input set resource paths, model cache paths, macros, filters,
   remote endpoints or command-line options.
3. **No silent egress:** model downloads are network activity; so are cloud
   OCR, LLMs, URL conversion, YouTube, remote vision, embeddings and vector
   stores. Defaults prohibit them. Consent is granular, recorded and
   cancellable.
4. **No arbitrary extensions:** MarkItDown entry points and Docling
   integrations are not discovered from the environment. Named, reviewed
   components can be added only through explicit capability configuration.
5. **Review before mutation:** conversion returns immutable text/IR plus
   provenance and diagnostics. Card candidates undergo validation and human
   review; only selected results reach one undoable collection operation.

## Provenance and operational record

For every completed import, record provider name/version/revision, detected
format, selected pipeline, source hash and locator, output/IR version, model
or executable version, enabled OCR/network action, fallback/skipped feature,
diagnostics and duration. For generated cards also record source chunk IDs,
prompt/model version, validator outcome and reviewer decision. This provides
reproducibility without treating raw LLM transcripts as citations.

## Upstream sources

- MarkItDown: [security](https://github.com/microsoft/markitdown#security-considerations), [plugins](https://github.com/microsoft/markitdown#plugins), [package metadata](https://raw.githubusercontent.com/microsoft/markitdown/main/packages/markitdown/pyproject.toml).
- Docling: [installation and OCR engines](https://docling-project.github.io/docling/getting_started/installation/), [advanced/offline options](https://docling-project.github.io/docling/usage/advanced_options/), [IBM models repository](https://github.com/docling-project/docling-ibm-models).
- Pandoc: [installation](https://pandoc.org/installing.html), [manual security note](https://pandoc.org/MANUAL.html#A-note-on-security).
- Chonkie: [installation](https://docs.chonkie.ai/oss/installation), [FileFetcher](https://docs.chonkie.ai/oss/fetchers/file-fetcher), [JSONPorter](https://docs.chonkie.ai/oss/porters/json-porter).
