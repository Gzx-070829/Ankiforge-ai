# AnkiForge AI v0.14.1 release notes

v0.14.1 fixes a release-blocking startup error in the packaged add-on. Internal imports now resolve relative to Anki's assigned add-on directory name, the build rejects source-layout-only absolute self-imports before producing an `.ankiaddon`, and runtime annotations remain deferred for the Python 3.9 environment used by supported older Anki releases. Provider behavior, review gates, duplicate checking, and Anki write safety are unchanged.

v0.14.0 introduced the Universal Document & Intelligence Engine: immutable DocumentIR, secure native importers, local analysis/chunking/planning, bounded Fast/Standard/Deep estimates, live request-safe stage progress, document summaries/Auto recommendations, coverage/dedup foundations, and document-oriented review handoff.

Implemented: native local formats (including `.hpp`) and deterministic local safeguards. Limited: source locations are hints; PDF is fallback-only in Core. Optional when separately installed and explicitly selected for the current window: local Docling, MarkItDown, and Pandoc adapters. Foundation-only: companion protocol, semantic dedup, and real deck-style sampling. Deferred: native PDF/OCR, web/URL import, cloud parsing, model downloads, audio/video/ASR, and bundled third-party tools/models.

No automatic installation, upload, Provider call, retry, or Anki write is introduced. Generate remains explicit; manual review, duplicate checking, and final confirmation remain hard gates.
