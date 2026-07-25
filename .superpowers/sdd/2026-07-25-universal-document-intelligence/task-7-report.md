# Task 7 final release-candidate evidence

## Scope and safety

No Provider, Anki process/collection, external tool installation, main merge/push, tag, Release, or AnkiWeb update was used. The benchmark patches `socket.create_connection` to fail if a network connection is attempted. Screenshot capture used only the already-installed local Chrome against a checked-in `file:///` preview with background networking disabled.

## TDD evidence

Initial RED, run with `python -m unittest discover -s tests -p 'test_document_intelligence_benchmark.py'` and `test_v014_release_contract.py`:

- missing `ankiforge_ai.eval.document_intelligence_benchmark` (two benchmark errors);
- runtime was `0.13.2` rather than `0.14.0`;
- v0.14 preview/manifest were absent.

Benchmark GREEN:

```text
python -m unittest tests.test_document_intelligence_benchmark
Ran 3 tests
OK
```

It runs 14 local scenarios: Python, SQL, BCI/EEGNet, math, vocabulary, biology, history, process, comparison, table, transcript, bilingual, PPT, and XLSX. The independent test table asserts each literal route, chunk/point count, structure/source preservation, plan grounding, and warning/blocking/duplicate counts. Aggregate metrics assert `{1: 3, 2: 11}` chunk counts, real chunk-size buckets `{0-32: 14, 33-64: 4, 65-128: 7, 129+: 0}`, 25/25 planning coverage, 14/14 route accuracy, synthetic local-rule warning/blocking/duplicate rates `5/28`, `1/28`, and `3/28`, and no failure reasons. These are deterministic smoke metrics, not an AI-quality or factual-accuracy score.

## Focused verification

The final focused regression group covered importer budgets, optional backends, capabilities UI, request-safe generation/retry progress, screenshots/manifest, benchmark, docs, and packaging: 99 tests passed. Separate final reviewers reran 74 key tests and found no Critical or Core automation blockers.

## Package evidence

Two consecutive `python scripts/build_ankiaddon.py` runs produced:

```text
Files: 162
Size: 352660 bytes
SHA-256: C025400A15B280A5EEA4A07A694DCDA240E231A2AB28A4A6B44BBED95EAAC573
identical: True
archive forbidden members: []
archive sensitive/secret matches: []
archive duplicate members: 0
archive dangerous paths: 0
package version / human_version: 0.14.0 / 0.14.0
```

The builder blocks eval, tests, fixtures, screenshots/docs, models, cache, temp/tmp, tools, config/credentials/secrets, backups, logs, Anki data, and common private-key suffixes/patterns.

## Test module count

Baseline `858a908967a539e31ae6649d11aeb8b2acb528ae`: 109
`test*.py` modules. Final working-tree count: 144, delta +35.

## Offline screenshots

Capture used the supplied local Chrome executable in `--headless=new` mode with a fixed 1440×900 window/device scale, local `file:///` state URLs, a temporary user profile outside the repository, and disabled background networking/component update flags. No browser was downloaded or installed. All 13 PNGs are valid 1440×900, have manifest SHA-256 values, and the canonical preview SHA-256 is `3B271ED62A9C958E9DA6BCE537AE4E86CE0D23D056F9239427FF19C0DA75A476`.

Representative visual inspection covered the Chinese empty default, capabilities dialog, localized Auto recommendation, Mock stage labels, and backend available state. The capability Mock includes the explicit native-Core-only opt-out. The stage frame illustrates labels emitted by the implemented live reporter and does not draw an unimplemented progress bar. Every frame remains explicitly marked as a Mock and not a live Anki/Provider session.

Temporary Chrome capture profiles remain outside the repository, are not tracked or packaged, and contain no project credential.

## Final review disposition

- Security review: no Critical or Important blocker. Remaining items are defense-in-depth limits on JSON container-node counting, bounded intermediate OOXML/EPUB lists, and a narrow user-selected Pandoc executable TOCTOU window.
- Product review Important item (ambiguous Pandoc selection feedback) was fixed. Copy, session-only opt-out, retry progress, and Mock/UI alignment were also corrected.
- Specification review: no Critical or Core automation blocker. Real Anki acceptance and real embedded-runtime checks for Docling/MarkItDown/Pandoc remain mandatory before main merge/public preview.

## Complete verification

```text
python -m unittest discover
Ran 1422 tests in 47.141s
OK

python -m compileall .
passed

git diff --check
passed
```

Two consecutive package builds were identical. Independent archive inspection
found 0 forbidden members, 0 duplicate members, 0 dangerous paths, 0
high-confidence secret matches, no config, no backups, and no Anki user data.
Real Anki, real Provider, optional-backend end-to-end execution, duplicate/write
gates, and collection behavior are intentionally left to the documented manual
acceptance step before merge or public release.
