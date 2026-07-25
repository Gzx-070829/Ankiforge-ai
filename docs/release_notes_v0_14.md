# AnkiForge AI v0.14.0 release notes

v0.14.0 adds the Universal Document & Intelligence Engine: immutable DocumentIR, secure native importers, local analysis/chunking/planning, bounded Fast/Standard/Deep estimates, live request-safe stage progress, document summaries/Auto recommendations, coverage/dedup foundations, and document-oriented review handoff.

Implemented: native local formats (including `.hpp`) and deterministic local safeguards. Limited: source locations are hints; PDF is fallback-only in Core. Optional when separately installed and explicitly selected for the current window: local Docling, MarkItDown, and Pandoc adapters. Foundation-only: companion protocol, semantic dedup, and real deck-style sampling. Deferred: native PDF/OCR, web/URL import, cloud parsing, model downloads, audio/video/ASR, and bundled third-party tools/models.

No automatic installation, upload, Provider call, retry, or Anki write is introduced. Generate remains explicit; manual review, duplicate checking, and final confirmation remain hard gates.
