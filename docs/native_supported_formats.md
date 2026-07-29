# Native supported formats (v0.14.1)

The packaged Core uses only local, bounded parsing. “Structured” means that the importer preserves the listed useful boundaries; it does not promise pixel-perfect rendering.

| Support level | Extensions | Preserved structure / limitation |
| --- | --- | --- |
| Native structured | `.txt`, `.md`, `.markdown` | Paragraphs; Markdown headings, lists, fenced code, and simple tables |
| Native structured | `.docx` | Paragraphs, heading styles, lists, and simple tables; no macros, external links, or OCR |
| Native structured | `.pptx` | Slide order, text, bullets, and simple tables; no embedded-object execution |
| Native structured | `.xlsx` | Visible sheets, bounded rows/cells, cached values and formula text; formulas never execute |
| Native structured | `.csv`, `.tsv` | Header and bounded row groups |
| Native structured | `.html`, `.htm`, `.xhtml` | Headings, paragraphs, lists, tables, code, quotes, and image alt text; scripts/resources never load |
| Native structured | `.json`, `.jsonl` | Bounded path/value blocks; JSONL streams within the shared document budget |
| Native structured | `.xml` | Safe bounded tag/path text; DTD and entities are rejected |
| Native structured | `.ipynb` | Markdown/code cells and short text outputs; cells never execute and binary output is skipped |
| Native structured | `.epub` | Spine/chapter order and safe XHTML structure; remote resources never load |
| Native structured | `.srt`, `.vtt` | Merged transcript blocks with timestamp ranges |
| Native safe text/code | `.yaml`, `.yml`, `.rst`, `.org`, `.tex`, `.latex`, `.log` | Text and basic headings only; includes and commands never execute |
| Native safe text/code | `.sql`, `.py`, `.js`, `.ts`, `.java`, `.c`, `.h`, `.cpp`, `.cc`, `.hpp`, `.rs`, `.go`, `.sh`, `.ps1` | Bounded code blocks and line locations; code never executes |
| Fallback only in Core | `.pdf` | Copy readable text or explicitly select a separately installed local Docling/MarkItDown backend for the current window |

PDF parsing and OCR are not native features. Optional backends are not bundled, downloaded, installed, persisted, or automatically enabled; see [Optional document backends](optional_document_backends.md).
