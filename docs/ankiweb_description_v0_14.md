# AnkiWeb draft — AnkiForge AI v0.14.1

AnkiForge AI v0.14.1 is an Anki Desktop add-on, not a shared deck or cloud document service. This hotfix restores startup under Anki's installed add-on directory layout and preserves compatibility with supported older Anki Python runtimes; it does not change Provider, review, duplicate-check, or write behavior. It imports only files you explicitly select, builds a local structural view, and creates reviewable candidates only after you explicitly generate with your configured Provider.

Core supports common study documents locally. PDF/OCR are not built in; advanced local conversion requires a separately installed optional backend. The add-on does not auto-install tools, download models, upload files, scan directories, or write cards without duplicate checking and final confirmation. Review every card: source labels and local quality checks do not guarantee factual accuracy.
