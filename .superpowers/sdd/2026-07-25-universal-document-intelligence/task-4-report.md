# Task 4 Report: Structure-Aware Chunking and Knowledge Planning

## Status and commit contract

Complete. Task 4 adds the deterministic, standard-library-only intelligence
foundation over reviewed immutable `DocumentIR`: bounded analysis, structural
chunking, local-first knowledge planning, strict caller-result LLM parsing,
coverage assessment, template routing, and call/card estimates.

- Base commit: `07209a609640175b8862b97ca52b6fb827fa9a5a`
- Task commit count: exactly one
- Task commit message: `Add structure-aware chunking and knowledge planning`
- Push count: zero
- Provider/backend/network executions: zero
- Qt/Anki imports below UI: zero

The final commit hash is reported in the task handoff. A commit cannot contain
its own final hash because adding that hash would change the commit hash.

## Changed files

New intelligence runtime:

- `ankiforge_ai/intelligence/__init__.py`
- `ankiforge_ai/intelligence/models.py`
- `ankiforge_ai/intelligence/analyzer.py`
- `ankiforge_ai/intelligence/mode_recommender.py`
- `ankiforge_ai/intelligence/estimates.py`
- `ankiforge_ai/intelligence/template_router.py`
- `ankiforge_ai/intelligence/chunking/__init__.py`
- `ankiforge_ai/intelligence/chunking/models.py`
- `ankiforge_ai/intelligence/chunking/structural.py`
- `ankiforge_ai/intelligence/chunking/token_budget.py`
- `ankiforge_ai/intelligence/chunking/table_chunker.py`
- `ankiforge_ai/intelligence/chunking/transcript_chunker.py`
- `ankiforge_ai/intelligence/planning/__init__.py`
- `ankiforge_ai/intelligence/planning/models.py`
- `ankiforge_ai/intelligence/planning/local_planner.py`
- `ankiforge_ai/intelligence/planning/llm_planner.py`
- `ankiforge_ai/intelligence/planning/coverage.py`

Modified generation compatibility:

- `ankiforge_ai/pipeline/generation_settings.py`
- `ankiforge_ai/pipeline/card_templates.py`
- `ankiforge_ai/pipeline/prompt_profile.py`

New focused tests:

- `tests/test_document_analyzer.py`
- `tests/test_structural_chunker.py`
- `tests/test_knowledge_planner_v014.py`
- `tests/test_template_router_v014.py`
- `tests/test_intelligence_estimates.py`

Updated v0.14 mode expectations:

- `tests/test_generation_settings.py`
- `tests/test_prompt_profile_v4.py`

Task record:

- `.superpowers/sdd/2026-07-25-universal-document-intelligence/task-4-report.md`

## Public interfaces

`ankiforge_ai.intelligence` exports:

- Models: `DocumentAnalysis`, `DocumentChunk`, `KnowledgePlan`,
  `KnowledgePointPlan`, `PlanCoverage`, `PlanEstimate`, `IntelligenceLevel`,
  and `TemplateRoute`.
- Functions: `analyze_document()`, `chunk_document()`,
  `build_local_knowledge_plan()`, `parse_llm_knowledge_plan()`,
  `assess_plan_coverage()`, `route_template()`, and
  `estimate_generation()`.

Important contracts:

- `DocumentAnalysis` reports safe IDs and bounded counts, language/kind,
  content density, semantic/structural signals, estimated points,
  deterministic recommendations, warnings, and confidence. Its `repr` never
  includes material.
- `DocumentChunk` stores safe deterministic IDs, section/heading provenance,
  exact chunk text, source block IDs/kinds, and immutable source locations.
  Its `repr` reports identity and counts only.
- `KnowledgePointPlan` stores a locally generated safe ID, evidence-derived
  title, point type/priority/section, 1–4 existing chunk references, derived
  source locations, a supported template, and bounded internal rationale.
- `KnowledgePlan` stores a safe plan ID, document ID, source (`local` or
  validated `llm`), existing chunk IDs, and at most 96 points.
- `PlanEstimate` uses `fast`, `standard`, or `deep`, always exposes the
  12-call ceiling, and defaults to Standard.

Selectable card modes now include `auto`, `code_understanding`,
`table_relationship`, and `transcript_summary_candidate`. Existing defaults
remain exactly `concept` / `balanced` / `short` / `auto` language. Cloze
remains registered but non-selectable. New modes reuse compatible existing
templates through explicit aliases, so no Provider or write-safety boundary
changes.

## RED evidence

### Analyzer and router

Before any intelligence production package existed:

```text
> python -m unittest tests.test_document_analyzer tests.test_template_router_v014
EE
ModuleNotFoundError: No module named 'ankiforge_ai.intelligence'
Ran 2 tests
FAILED (errors=2)
```

This was the expected Task 4 RED: imports failed solely because the new
package was absent.

### Structural chunker

After analyzer/router GREEN, before chunking production modules:

```text
> python -m unittest tests.test_structural_chunker
E
ModuleNotFoundError: No module named 'ankiforge_ai.intelligence.chunking'
Ran 1 test
FAILED (errors=1)
```

### Planner and estimates

After chunking GREEN, before planning/estimate production modules:

```text
> python -m unittest tests.test_knowledge_planner_v014 tests.test_intelligence_estimates
EE
ModuleNotFoundError: No module named 'ankiforge_ai.intelligence.planning'
ImportError: cannot import name 'estimate_generation'
Ran 2 tests
FAILED (errors=2)
```

### Mode-to-prompt compatibility

After the required mode expectations were expanded, the compatibility test
proved that validation alone was insufficient:

```text
> python -m unittest tests.test_generation_settings tests.test_card_templates_v4 tests.test_prompt_profile_v4
.............E...
ValueError: unsupported card mode: 'auto'
Ran 17 tests
FAILED (errors=1)
```

The correction added deterministic aliases to existing templates and an
explicit compatibility predicate; the existing template registry itself did
not expand.

### Adversarial review RED

The time-boxed self-review added narrow tests for independently derived edge
cases:

```text
> python -m unittest tests.test_document_analyzer tests.test_structural_chunker tests.test_knowledge_planner_v014
.F.......F.F.......
Ran 19 tests
FAILED (failures=3)
```

The three failures proved:

- an empty IR block was not included in the structural block count;
- a two-character separator straddling the hard split boundary could exceed
  `max_chars` by one;
- later pieces of oversized code lost their neighboring explanation.

Corrections separated structural/content counts, made separator searches
strictly end within the budget, and repeated a bounded neighboring
explanation for every oversized code/formula piece.

A separate safe-error RED proved Python's raw `BlockKind` error echoed
path-like caller data:

```text
> python -m unittest tests.test_template_router_v014.TemplateRouterV014Tests.test_invalid_block_kind_error_does_not_echo_path_like_input
F
ValueError: 'C:\\Users\\private\\source.txt' is not a valid BlockKind
Ran 1 test
FAILED (failures=1)
```

The router now replaces that diagnostic with a fixed safe message.

## GREEN evidence

Tranche GREEN runs:

```text
> python -m unittest tests.test_document_analyzer tests.test_template_router_v014
.........
Ran 9 tests
OK

> python -m unittest tests.test_structural_chunker
.......
Ran 7 tests
OK

> python -m unittest tests.test_knowledge_planner_v014 tests.test_intelligence_estimates
...........
Ran 11 tests
OK

> python -m unittest tests.test_generation_settings tests.test_card_templates_v4 tests.test_prompt_profile_v4
.................
Ran 17 tests
OK

> python -m unittest tests.test_document_analyzer tests.test_structural_chunker tests.test_knowledge_planner_v014
...................
Ran 19 tests
OK

> python -m unittest tests.test_template_router_v014.TemplateRouterV014Tests.test_invalid_block_kind_error_does_not_echo_path_like_input
.
Ran 1 test
OK
```

Final required regression:

```text
> python -m unittest tests.test_generation_settings tests.test_card_templates_v4 tests.test_prompt_profile_v4 tests.test_document_analyzer tests.test_structural_chunker tests.test_knowledge_planner_v014 tests.test_template_router_v014 tests.test_intelligence_estimates
................................................
----------------------------------------------------------------------
Ran 48 tests in 0.011s

OK
```

Changed Python files compiled:

```text
> python -m py_compile <17 intelligence modules> <3 pipeline modules> <7 test modules>
[no output; exit 0]
```

Whitespace validation:

```text
> git diff --check
[no errors; exit 0]
```

## Implementation mapping

### Deterministic analysis and routing

- Analyzer scans every block in stable document order with compiled
  standard-library regular expressions and block-kind counters.
- Literal definition, comparison, ordered-process, formula, code, table,
  transcript, and bilingual fixtures assert hand-derived values.
- Recommendations use one stable priority order, then conservative `concept`
  fallback.
- Point-local type/kind evidence outranks document-wide signals in Auto.
- Every Auto route returns a template, confidence, stable reason code, and
  source constraint tuple.
- Any selectable explicit mode overrides Auto with confidence `1.0`.
- Unknown and Cloze requests fail closed; raw invalid block-kind input is not
  echoed.

### Structure-aware bounded chunking

- Default target: 6,000 characters.
- Hard chunk maximum: 12,000 characters.
- Hard document maximum: 48 chunks.
- Sections and safe heading paths are processed before secondary text
  splitting.
- Adjacent peer blocks merge only within the target, hard maximum, section,
  and source boundary.
- List blocks and consecutive list items remain units when possible.
- Tables split by rows and repeat the first serialized header in every piece.
- Code/formulas pair with a neighboring leading explanation; oversized pairs
  repeat bounded explanation context.
- Transcript and generic text split without tokenizer/model dependencies,
  preferring paragraph, line, sentence, punctuation, and whitespace
  boundaries before an exact character boundary.
- The splitter neither overlaps nor omits long unbroken Unicode text and
  cannot overrun the hard maximum when a multi-character separator lies on
  the boundary.
- Page, slide, sheet, section/chapter, cell/notebook, row/timestamp location
  objects are preserved in deterministic order.
- Absolute/traversal-looking heading paths are not rendered into chunk
  headings. Source text remains available only in the explicit chunk `text`
  field, never in IDs, errors, or representations.
- Chunk IDs hash only safe document/section/block IDs and sequence, never
  source bodies or paths.

### Local-first grounded planning

- The local planner is the primary implementation and the fallback when
  supplied LLM output is missing, malformed, over-limit, wrong-typed,
  extra-field-bearing, unknown-chunk, or ungrounded.
- Sections are visited round-robin in document order. The first unique point
  in each section is high priority; later points are medium priority.
- Candidate titles are literal bounded substrings of existing chunk evidence.
- Unicode NFKC/case/punctuation-insensitive normalization removes duplicate
  candidates deterministically.
- Every point references 1–4 existing chunk IDs; section and location
  provenance are derived from those chunks.
- IDs hash only safe document/chunk IDs and local ordinal state, not titles,
  rationale, source bodies, paths, or credentials.
- The caller-supplied LLM parser performs no call. JSON input is capped at
  256,000 characters, nesting recursion falls back safely, root/point fields
  are exact, points are capped at 96, and types/priorities/templates/source
  references are allowlisted.
- LLM titles must normalize to a substring of at least one referenced chunk;
  duplicate titles are removed in caller order.
- Coverage reports deterministic covered/uncovered chunks and sections,
  duplicate point IDs, invalid/ungrounded point IDs, and grounded status.

### Estimates and compatibility

- Fast returns the exact 1–3 call policy and no estimate-confirmation flag.
- Standard is the default and returns the exact 3–8 call policy.
- Deep returns the exact 4–12 call policy.
- All levels expose `max_calls=12`; 49 or more chunks fail before arithmetic.
- Card ranges are conservative transformations of the validated plan size or
  analysis estimate, are ordered, and are capped at 96.
- Empty documents estimate zero cards without changing the bounded level
  policy.
- Existing generation defaults, profiles, old templates, note compatibility,
  Provider code, quality gates, duplicate gate, confirmation gate, and writer
  are untouched except for the narrow new mode/template compatibility aliases.

## Complexity and safety self-review

- Analyzer: linear in document blocks/text; no model/tokenizer/import backend.
- Chunk grouping: linear in block/unit count. Table-presence state and source
  location dedup use constant-time flags/sets rather than repeated scans.
- Secondary splitting: forward-only bounded slices; no backtracking regex and
  no overlapping windows.
- Planning: at most 48 chunks and 96 points. Source/document references are
  validated once before selection.
- LLM validation: bounded input, bounded points, bounded references per point,
  exact field sets, and deterministic caller order.
- Coverage/estimate arithmetic is bounded by the same 48/96/12 limits.
- All runtime dataclasses are frozen; mutable mappings are frozen where used.
- Diagnostic representations contain IDs, counts, enum-like values, and safe
  reason codes only.
- No Qt, Anki, Provider, backend, network, subprocess, filesystem read/write,
  external package, model, tokenizer, or credential dependency exists in the
  new intelligence runtime.

## Meaningful assertion/mutation review

Tests would fail for these realistic regressions:

- a signal counter, language classification, mode ordering, confidence, or
  estimated-point formula returning a wrong literal;
- Auto ignoring point evidence or explicit mode precedence;
- Cloze becoming selectable;
- heading/list ownership loss, peer non-merge, table header omission, code or
  formula context loss, boundary/provenance loss, chunk overflow, chunk
  nondeterminism, Unicode overlap/omission, or unsafe diagnostic output;
- section-order flooding, wrong priority, unknown chunk references,
  out-of-source LLM titles, duplicate normalization failure, extra fields,
  wrong types, 97-point acceptance, or failed-parser non-fallback;
- wrong Fast/Standard/Deep ranges, wrong default level, 12-call overflow,
  invalid 49-chunk acceptance, or incompatible card-range arithmetic;
- new card modes failing generation validation or prompt construction, or
  old defaults changing.

Expected values are literal and hand-derived. Tests exercise real immutable
models and functions; no mocks are used.

## Concerns

None blocking. The analyzer and local planner are deliberately conservative
heuristics, not semantic truth claims. Standard/Deep may consume a
caller-supplied structured planner result, but this task intentionally
contains no Provider call or retry path.

## Review fix round 1

### Status

Complete. The original Task 4 commit was amended in place; no second commit or
push was created.

### RED evidence

The review tests were added before production corrections. The initial
combined review run produced failures in every reported category:

```text
> python -m unittest tests.test_document_analyzer tests.test_structural_chunker tests.test_knowledge_planner_v014 tests.test_intelligence_estimates
.F.....FFFFFFFFFFFFFF......FF..FF.FF.F.FF..F...F..
----------------------------------------------------------------------
Ran 38 tests in 6.233s

FAILED (failures=26)
```

The failures covered:

- false definition/process positives;
- unsafe or under-validated exported chunk/plan/coverage models;
- omitted file/timestamp/row/line structural boundary fields;
- unbounded huge-text slicing and arbitrary iterable consumption;
- table headers falling into generic splitting;
- duplicate LLM evidence being silently accepted;
- invalid caller fallback plans being returned;
- cross-section points being marked grounded;
- quadratic source-location deduplication;
- hostile mappings being copied before schema rejection.

After the streaming implementation, two direct critical-path assertions were
added. They proved that the legacy tuple helper and a rowless overlong header
still needed the same protections:

```text
> python -m unittest tests.test_structural_chunker.StructuralChunkerTests.test_tuple_split_helper_is_also_capped_before_materialization tests.test_structural_chunker.StructuralChunkerTests.test_table_header_at_or_over_hard_budget_fails_before_generic_split
FF
----------------------------------------------------------------------
Ran 2 tests in 0.002s

FAILED (failures=2)
```

The tuple helper attempted a 50th slice and the rowless header did not raise.
Both were corrected before final verification.

### Corrections and finding mapping

1. **Cap before materialization:** `iter_text_to_budget()`,
   `iter_table_text()`, and `iter_transcript_text()` now yield pieces lazily.
   `chunk_document()` constructs at most 48 chunks and reads only the 49th
   piece needed to reject overflow. Tuple compatibility helpers also consume
   only 49 pieces before returning or failing. A 4,999,000-character
   slice-counting string with one-character budgets records exactly 49
   slices, not millions.
2. **Complete structural boundaries:** the deterministic boundary key now
   includes `file_label`, page, slide, sheet, row start/end, cell range,
   section, timestamp start/end, notebook cell, and line start/end. Literal
   same-section subtests prove that changing any one field prevents merging.
3. **Fallback validation:** supplied fallback plans must be local, match the
   exact current chunk ordering, reference current chunks, remain within one
   point section, be grounded in referenced text, preserve derived locations,
   and contain no normalized duplicates. Any failure rebuilds the local plan.
4. **Duplicate LLM evidence:** a repeated normalized title now invalidates the
   whole caller-supplied plan and selects the local fallback. It is no longer
   silently dropped from a result labelled `llm`.
5. **Coverage grounding:** point references must exist in both current chunks
   and `plan.chunk_ids`; every referenced chunk must belong exactly to
   `point.section_id`; derived locations and normalized evidence must match.
   Cross-section multi-chunk points are invalid and cover no chunks.
6. **Exported model invariants:** `DocumentChunk`, `KnowledgePointPlan`,
   `KnowledgePlan`, and `PlanCoverage` now cap arbitrary sequence inputs while
   freezing them to tuples; validate safe bounded IDs, Unicode, approved
   12,000/48/96/20,000 limits, aligned block IDs/kinds, unique locations and
   IDs, plan reference membership, coverage disjointness, and grounded/invalid
   consistency. Representations remain material/path safe.
7. **Hostile iterable/mapping bounds:** local planning and estimates consume
   at most 49 chunks from arbitrary iterables. LLM root and point mappings
   check length and bounded exact keys before reading fields and never copy an
   arbitrary mapping. Instrumented infinite iterables stop at exactly 49; a
   wrong-sized mapping is rejected without iteration.
8. **Linear location dedup:** LLM source locations now use an ordered list plus
   a membership set. The 120-location instrumented test records fewer than
   300 equality comparisons rather than the former 7,140.
9. **Conservative heuristics:** English definitions require `defined as`,
   `refers to`, `means`, or `is/are a|an|type`; Chinese uses explicit
   definition forms. Process detection requires at least two stage markers.
   “The meeting is Tuesday”, a single “Next”, and the Chinese calendar
   sentence produce only the conservative `concept` recommendation. True
   bilingual definitions and multi-stage processes remain detected.
10. **Table header safety:** a repeated header that leaves no room for a row,
    including exact-boundary, one-over, and rowless overlong cases, fails with
    a fixed source-free error before generic splitting.

The adjacent minor `findall()` allocation was also removed: analyzer language
counts now use streaming `finditer()` sums.

### GREEN evidence

Focused review set:

```text
> python -m unittest tests.test_document_analyzer tests.test_structural_chunker tests.test_knowledge_planner_v014 tests.test_intelligence_estimates
......................................
----------------------------------------------------------------------
Ran 38 tests in 0.314s

OK
```

Critical tuple/header correction:

```text
> python -m unittest tests.test_structural_chunker.StructuralChunkerTests.test_tuple_split_helper_is_also_capped_before_materialization tests.test_structural_chunker.StructuralChunkerTests.test_table_header_at_or_over_hard_budget_fails_before_generic_split
..
----------------------------------------------------------------------
Ran 2 tests in 0.001s

OK
```

Final Task 4 and compatibility regression:

```text
> python -m unittest tests.test_generation_settings tests.test_card_templates_v4 tests.test_prompt_profile_v4 tests.test_document_analyzer tests.test_structural_chunker tests.test_knowledge_planner_v014 tests.test_template_router_v014 tests.test_intelligence_estimates
...............................................................
----------------------------------------------------------------------
Ran 63 tests in 0.328s

OK
```

All changed Python files compiled with `python -m py_compile`; no output,
exit 0. `git diff --check` produced no errors. Only Git's configured
LF-to-CRLF informational warnings were emitted.

### Review fix round 1 concerns

None.

## Review fix round 2

### Status

Complete. The existing Task 4 commit is amended in place; no additional
commit or push is created.

### RED evidence

The round-two constructor, allowlist, reference-limit, and streaming-table
tests were added before production changes:

```text
> python -m unittest tests.test_structural_chunker tests.test_document_analyzer tests.test_knowledge_planner_v014 tests.test_intelligence_estimates
........F.......FFFF...........F......FF.....FFFFF...
----------------------------------------------------------------------
Ran 46 tests in 0.606s

FAILED (failures=13)
```

The failures proved that:

- the table path still called eager `str.splitlines()` on a near-5-million
  character table;
- `DocumentAnalysis` accepted unsafe IDs, a 97-point estimate, impossible
  signal counts, and non-finite density;
- `KnowledgePointPlan` accepted arbitrary point/template strings and five
  source references, while the LLM parser accepted five same-section
  references;
- `PlanEstimate` accepted a 13-call ceiling, 49 chunks, 97 cards, incorrect
  call ranges, and an incorrect Fast confirmation policy.

### Corrections

1. **Forward-only table scanning:** table splitting now uses a lazy line
   iterator that recognizes LF, CRLF, and CR without constructing a full line
   list. A 4,998,002-character instrumented table raises at the document chunk
   ceiling after exactly 49 row slices and records zero `splitlines()` calls.
   Rows that exactly reach the target are yielded immediately, so no extra row
   is read merely to discover the next boundary.
2. **Exact planning schema:** shared immutable allowlists define the supported
   point types and recommended templates. Direct point construction, supplied
   fallback validation, and LLM parsing all use the same sets.
3. **One-to-four evidence references:** `KnowledgePointPlan` consumes at most
   five items from an arbitrary source-ID iterable, accepts exactly one
   through four unique safe references, and rejects the fifth before further
   materialization. `KnowledgePlan` membership validation and LLM membership,
   uniqueness, and same-section checks remain enforced. Four-reference LLM
   plans are accepted; five-reference plans fall back locally.
4. **Bounded public analysis:** `DocumentAnalysis` validates its safe bounded
   document ID, known language/kind, finite density and confidence, bounded
   document/signal counts, the 96-point maximum, bounded immutable modes and
   warning codes, and coherent immutable block-kind counts.
5. **Bounded public estimates:** `PlanEstimate` rejects booleans and non-
   integers in count fields, caps chunks/cards/calls at 48/96/12, preserves
   ordered card/call ranges, and enforces the exact Fast 1–3, Standard 3–8,
   and Deep 4–12 call and confirmation policies. Its representation remains
   numeric and source-free.

### GREEN evidence

Focused round-two review set:

```text
> python -m unittest tests.test_document_analyzer tests.test_structural_chunker tests.test_knowledge_planner_v014 tests.test_intelligence_estimates
..............................................
----------------------------------------------------------------------
Ran 46 tests in 0.626s

OK
```

Final Task 4 and compatibility regression:

```text
> python -m unittest tests.test_generation_settings tests.test_card_templates_v4 tests.test_prompt_profile_v4 tests.test_document_analyzer tests.test_structural_chunker tests.test_knowledge_planner_v014 tests.test_template_router_v014 tests.test_intelligence_estimates
......................................................................
----------------------------------------------------------------------
Ran 70 tests in 0.598s

OK
```

All changed Python files compiled with `python -m py_compile`; no output,
exit 0. `git diff --check` produced no errors. Only Git's configured
LF-to-CRLF informational warnings were emitted.

### Review fix round 2 concerns

None.

## Review fix round 3

### Status

Complete. The complexity correction is amended into the existing Task 4
commit; no additional commit or push is created.

### RED evidence

The regression test uses default 6,000/12,000 budgets and 8,000 short table
rows. Its instrumented string records the remaining-suffix span of every
separator search plus every direct character-index visit. It contains no
timer or environment-dependent threshold.

Before the scanner correction:

```text
> python -m unittest tests.test_structural_chunker.StructuralChunkerTests.test_default_budget_many_short_rows_use_linear_separator_work tests.test_structural_chunker.StructuralChunkerTests.test_lazy_line_scanner_matches_splitlines_terminal_behavior
F.
======================================================================
FAIL: test_default_budget_many_short_rows_use_linear_separator_work
----------------------------------------------------------------------
AssertionError: 128056005 not less than or equal to 32004

----------------------------------------------------------------------
Ran 2 tests in 0.015s

FAILED (failures=1)
```

The terminal-newline characterization already passed. The complexity test
failed because each row performed both LF and CR `find()` calls; the absent
separator search repeatedly traversed the remaining suffix.

### Correction

`_iter_lines()` now owns one monotonically increasing index. It visits the
input forward, yields a slice at LF or CR, and advances by two only for a CRLF
pair. It performs no suffix search or line-list materialization. The iterator
remains lazy: stopping the consumer after the 49th table piece stops line
scanning at the same point. A trailing LF, CR, or CRLF does not create an
extra terminal empty line, matching `str.splitlines()`; interior empty lines
remain preserved.

### GREEN evidence

Direct complexity and terminal-behavior tests:

```text
> python -m unittest tests.test_structural_chunker.StructuralChunkerTests.test_default_budget_many_short_rows_use_linear_separator_work tests.test_structural_chunker.StructuralChunkerTests.test_lazy_line_scanner_matches_splitlines_terminal_behavior
..
----------------------------------------------------------------------
Ran 2 tests in 0.009s

OK
```

Structural suite, including the exact 49-row near-5M lazy cap:

```text
> python -m unittest tests.test_structural_chunker
..................
----------------------------------------------------------------------
Ran 18 tests in 0.630s

OK
```

Focused round-three review set:

```text
> python -m unittest tests.test_document_analyzer tests.test_structural_chunker tests.test_knowledge_planner_v014 tests.test_intelligence_estimates
................................................
----------------------------------------------------------------------
Ran 48 tests in 0.645s

OK
```

Final Task 4 and compatibility regression:

```text
> python -m unittest tests.test_generation_settings tests.test_card_templates_v4 tests.test_prompt_profile_v4 tests.test_document_analyzer tests.test_structural_chunker tests.test_knowledge_planner_v014 tests.test_template_router_v014 tests.test_intelligence_estimates
........................................................................
----------------------------------------------------------------------
Ran 72 tests in 0.649s

OK
```

All changed Python files compiled with `python -m py_compile`; no output,
exit 0. `git diff --check` produced no errors. Only Git's configured
LF-to-CRLF informational warnings were emitted.

### Review fix round 3 concerns

None.
