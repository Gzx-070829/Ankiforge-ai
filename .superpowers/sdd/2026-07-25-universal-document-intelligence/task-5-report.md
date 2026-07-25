# Task 5 Report: Bounded Intelligence Runs and Recovery

## Status and commit contract

Complete. Task 5 adds a pure, immutable bounded-generation state machine,
call-budget reservation, local-authoritative critic/revalidation, coverage,
deterministic cross-chunk deduplication, explicit failed-only recovery, a
taskman lifecycle controller driven only by injected callbacks, and an opt-in
aggregate-only deck-style foundation.

- Base commit: `365200fcf59a5165465f7acd131ae1b5987c7f30`
- Task commit count: exactly one
- Task commit message: `Add bounded intelligence runs and recovery`
- Push count: zero
- Real Provider/network executions: zero
- Qt/Anki collection executions: zero
- Automatic retry/write/review bypasses: zero

The final commit hash is reported in the task handoff. A commit cannot contain
its own final hash because adding that hash would change the commit hash.

## Changed files

New bounded intelligence runtime:

- `ankiforge_ai/intelligence/call_budget.py`
- `ankiforge_ai/intelligence/generation_run.py`
- `ankiforge_ai/intelligence/critic.py`
- `ankiforge_ai/intelligence/coverage.py`
- `ankiforge_ai/intelligence/deduplication.py`
- `ankiforge_ai/intelligence/recovery.py`
- `ankiforge_ai/intelligence/deck_style.py`

New asynchronous lifecycle adapter:

- `ankiforge_ai/ui/intelligent_generation_task_controller.py`

Updated public intelligence exports:

- `ankiforge_ai/intelligence/__init__.py`

New focused tests:

- `tests/test_generation_run_v014.py`
- `tests/test_intelligence_call_budget.py`
- `tests/test_critic_repair_v014.py`
- `tests/test_coverage_dedup_v014.py`
- `tests/test_partial_failure_recovery.py`
- `tests/test_deck_style_profile.py`
- `tests/test_intelligent_generation_task_controller.py`

Task record:

- `.superpowers/sdd/2026-07-25-universal-document-intelligence/task-5-report.md`

The existing `ankiforge_ai/ui/generation_task_controller.py` remains
unchanged; its public `submit()` behavior continues to pass its full regression
suite.

## Public interfaces

`ankiforge_ai.intelligence` now exports the required Task 5 models:

- `GenerationRun`, `GenerationStage`, `GenerationRunStatus`
- `ChunkGenerationState`, `ChunkGenerationSnapshot`
- `CallBudget`, `CallReservation`, `CallPurpose`, `CallBudgetError`
- `CriticDecision`, `CriticAction`, `RepairResult`
- `CoverageReport`
- `DeduplicationResult`
- `FailedChunkRetry`
- `DeckStyleProfile`, `DeckStyleQuery`

It also exports the pure constructors/transitions/checkers needed to use those
models: run creation/stage/chunk/call transitions, critic and repair
revalidation, coverage assessment, canonicalization/deduplication, failed-only
retry preparation/dispatch/completion, and deck-style query/summarization.

The UI package adds:

- `IntelligentGenerationRequestSnapshot`
- `IntelligentGenerationTaskCompletion`
- `IntelligentGenerationTaskController`

The controller accepts a frozen `GenerationRun` plus injected
planner/generator/critic callbacks. It contains no Provider construction,
network operation, Qt widget access, Anki collection access, persistence, or
write path.

## RED evidence

### Run and call budget

Before either production module existed:

```text
> python -m unittest tests.test_generation_run_v014 tests.test_intelligence_call_budget
EE
ModuleNotFoundError: No module named 'ankiforge_ai.intelligence.call_budget'
ModuleNotFoundError: No module named 'ankiforge_ai.intelligence.call_budget'
Ran 2 tests
FAILED (errors=2)
```

### Critic, coverage, and deduplication

Before those modules existed:

```text
> python -m unittest tests.test_critic_repair_v014 tests.test_coverage_dedup_v014
EE
ModuleNotFoundError: No module named 'ankiforge_ai.intelligence.critic'
ModuleNotFoundError: No module named 'ankiforge_ai.intelligence.coverage'
Ran 2 tests
FAILED (errors=2)
```

The first implementation run then exposed three meaningful critic failures:

```text
> python -m unittest tests.test_critic_repair_v014 tests.test_coverage_dedup_v014
..F.FF........
Ran 14 tests
FAILED (failures=3)
```

Shared English stopwords let unsupported claims pass the pre-existing simple
grounding check. The Task 5 critic now independently requires substantive
source token/CJK-bigram coverage. The third failure corrected a hand-counted
test literal from 46 to 45 characters; it did not relax production behavior.

### Recovery and async controller

Before recovery/controller production modules existed, the seven existing
controller tests still passed and only the new imports failed:

```text
> python -m unittest tests.test_partial_failure_recovery tests.test_intelligent_generation_task_controller tests.test_generation_task_controller
EE.......
ModuleNotFoundError: No module named 'ankiforge_ai.intelligence.recovery'
ModuleNotFoundError: No module named 'ankiforge_ai.ui.intelligent_generation_task_controller'
Ran 9 tests
FAILED (errors=2)
```

The initial implementation run found one recovery error-precedence mismatch
and a test helper that accidentally shadowed `unittest.TestCase.run`. The
recovery identity check was moved ahead of stage validation; the helper was
renamed. The complete tranche then passed.

### Deck style

Before the deck-style module existed:

```text
> python -m unittest tests.test_deck_style_profile
E
ModuleNotFoundError: No module named 'ankiforge_ai.intelligence.deck_style'
Ran 1 test
FAILED (errors=1)
```

The first implementation run found one real aggregation failure: closing HTML
tags were not stripped before length calculation.

```text
...F....
Ran 8 tests
FAILED (failures=1)
```

The bounded tag matcher now handles opening and closing tags.

### Public exports

The required root export test failed all ten required Task 5 model subtests
before `ankiforge_ai.intelligence.__init__` was updated:

```text
FFFFFFFFFF
Ran 1 test
FAILED (failures=10)
```

### Adversarial self-review

Six narrow tests were added before their production corrections:

```text
> python -m unittest <six targeted review tests>
FFFEFF
Ran 6 tests
FAILED (failures=5, errors=1)
```

They proved:

- completed-partial runs were not terminal to ordinary transitions;
- direct model construction could exceed 96 cards across chunks;
- card-count overflow still recommended a supplement;
- explicit retry could not reopen a completed partial run;
- an HTML-only style sample was mislabeled `plain`;
- supersession during the planner callback did not stop the old generator and
  critic callbacks.

All six tests passed after the bounded corrections.

## GREEN and verification evidence

Tranche GREEN runs:

```text
> python -m unittest tests.test_generation_run_v014 tests.test_intelligence_call_budget
.................
Ran 17 tests
OK

> python -m unittest tests.test_critic_repair_v014 tests.test_coverage_dedup_v014
..............
Ran 14 tests
OK

> python -m unittest tests.test_partial_failure_recovery tests.test_intelligent_generation_task_controller tests.test_generation_task_controller
....................
Ran 20 tests
OK

> python -m unittest tests.test_deck_style_profile
........
Ran 8 tests
OK

> python -m unittest <six targeted review tests>
......
Ran 6 tests
OK
```

The combined Task 5/legacy-controller focused run before adversarial additions
was:

```text
............................................................
Ran 60 tests
OK
```

The exact required final regression command produced:

```text
> python -m unittest tests.test_card_quality_v4 tests.test_review_workbench_v4 tests.test_async_card_generation tests.test_generation_task_controller tests.test_generation_run_v014 tests.test_intelligence_call_budget tests.test_critic_repair_v014 tests.test_coverage_dedup_v014 tests.test_partial_failure_recovery tests.test_deck_style_profile tests.test_intelligent_generation_task_controller
.............................................................................................
Ran 93 tests in 0.075s
OK
```

Changed Python files compile with `python -m py_compile`. Final whitespace
validation is run after this report is written and recorded in the handoff.

## Implementation mapping

### Immutable run and legal transitions

- A run owns safe run/request/document/hash identity, recursively frozen
  document/settings snapshots, level/stage/status, up to 48 unique chunks, up
  to 96 total cards, one matching immutable call budget, safe error codes,
  repaired-point IDs, one supplement flag, and explicit retry scheduling IDs.
- Material, card bodies, plans, and settings are excluded from diagnostic
  representations. Representations contain only safe IDs, enum values, counts,
  and reason codes.
- The ordinary graph moves forward from analyze through plan, generation,
  review/optional repair, coverage, deduplication, and terminal completion.
  Failed and superseded states are terminal.
- A completed partial run is terminal to ordinary transitions. The only reopen
  operation is the explicit failed-only recovery function; it retains
  successful siblings and marks only previously failed, never-before-scheduled
  chunks pending.
- Chunk completion is idempotent by rejection: only `pending -> running ->
  succeeded|failed` is accepted. Duplicate/late success and failure callbacks
  cannot overwrite prior results.

### Atomic bounded call accounting

- `CallBudget` defaults to Standard and embeds exact Fast `1..3`, Standard
  `3..8`, and Deep `4..12` policy metadata.
- The active ceiling is level-specific and the global ceiling is always 12.
- Reservations are immutable, contiguous, purpose-labeled, and created before
  callback dispatch. A failed callback remains billed in the returned failed
  run.
- Fast permits generation only. Standard permits planner/generation and one
  caller-enabled repair. Deep additionally permits critic and one supplement.
- Repair reservation and repaired-point insertion occur in one immutable
  transition. Duplicate point repair is rejected before billing.
- Supplement reservation and the run-level supplement flag also occur in one
  transition. A second supplement is rejected before billing.
- There is no recursive or automatic retry API.

### Local critic and repair authority

- The existing deterministic card-quality bridge is reused for local rules.
- Empty fields, unsupported Cloze, invalid Cloze, and failed source grounding
  are treated as critic-blocking. A model `pass` cannot waive them.
- First local failure requests one repair; post-repair local failure rejects.
- `repair_and_revalidate()` invokes one injected callback exactly once, checks
  stable candidate identity, and locally revalidates source support.
- Raw model reasoning and repair exceptions are never retained or rendered.
  Only bounded allowlisted reason codes cross the boundary.

### Coverage and deterministic deduplication

- Coverage accepts at most 96 point/card records and validates every point,
  section, and card reference.
- It reports missing high-priority points, uncovered and overcovered sections,
  duplicate point coverage, card count, and overflow.
- Only missing high-priority points can recommend supplementation, and overflow
  suppresses that recommendation.
- Deduplication preserves caller order and keeps the first card.
- Exact equality runs first, followed by Unicode NFKC/case/punctuation/
  whitespace canonicalization.
- Similar matching uses deterministic Latin-token/CJK-bigram Jaccard overlap,
  a validated finite threshold, and required source/point overlap.
- At 96 cards the worst-case pair comparison count is 4,560.
- A semantic matcher may be supplied as a protocol placeholder but is never
  called; enabling semantic/embedding dedup fails closed.

### Explicit partial recovery

- `FailedChunkRetry` contains only safe retry/run/request/chunk identity and the
  source call count.
- Retry creation includes failed, not-yet-scheduled chunks only.
- Preparation retains every successful sibling card and does not bill.
- Dispatch validates pending state first, then atomically reserves one
  generation call and moves exactly that failed chunk to running.
- Duplicate dispatch/completion is rejected without mutating or double-billing
  the returned snapshot.
- A new explicit click may reopen a completed partial run, but scheduled chunks
  cannot be scheduled again and the API never calls itself.

### Async taskman lifecycle

- Submission requires an immutable `GenerationRun`, strictly increasing
  request ID, a generator callback, and a UI completion callback.
- Worker execution is deferred with `uses_collection=False`.
- Planner/generator/critic callbacks receive only immutable run snapshots after
  their call reservation has been recorded.
- The worker imports no Qt, Anki, Provider, collection, or write component.
- A new request supersedes the current request. The controller checks freshness
  before work and after each injected callback so later old callbacks stop at
  the next boundary.
- Stale and closed-window completions are no-ops.
- Callback, future, and taskman-submission exceptions become safe reason-coded
  completions; raw exception/provider output is discarded.
- UI completion exceptions are isolated after controller state is released.
- The legacy `GenerationTaskController.submit()` remains unchanged and all
  compatibility tests pass.

### Deck-style foundation

- `DeckStyleQuery` is opt-in and requires one explicit positive selected-deck
  ID plus a safe bounded label.
- Query policy is fixed to no descendants, no full scan, no mutation,
  aggregate-only, and at most 20 notes.
- `summarize_deck_style()` is pure and consumes no more than the specified
  1–20 already-supplied notes; disabled mode does not touch the iterable.
- It stores only field names, front/back length ranges, bullet/HTML ratios,
  common layout categories, common tags, and template hints.
- Note dictionaries/lists are never mutated or retained in the profile.
- Provider payload excludes deck ID/label and all example/note bodies.
- `REAL_DECK_STYLE_SAMPLING_ENABLED` is `False`; requesting real sampling or
  examples fails closed.
- No Anki query exists in this task.

## Complexity, privacy, and boundary self-review

- All public collections are capped before materialization where the boundary
  accepts arbitrary iterables.
- Run/chunk traversal is bounded by 48/96; budget traversal by 12.
- Deduplication is the intentional bounded quadratic operation: at most 4,560
  deterministic comparisons, each over card text capped at 12,000 characters.
- Coverage and retry are bounded by 96 points/cards and 48 chunks.
- Deck style consumes at most 20 notes, 32 fields per note, 16 tags per note,
  and 12,000 characters per field.
- Numeric counts reject booleans/non-integers; ratios and similarity thresholds
  reject non-finite or out-of-range values.
- Mutable mappings/sequences captured by runs, cards, repairs, and results are
  copied into immutable aggregate structures.
- Safe `repr`/errors contain only IDs, counts, stages/statuses, purpose/action
  enums, and reason codes. Tests pressure private material, card bodies,
  filesystem-looking values, model reasoning, callback exceptions, and deck
  note bodies.
- No new code imports a Provider, HTTP/network client, Qt, Anki collection,
  writer, config loader, secret store, or persistence layer.
- No code auto-approves review, bypasses duplicate/final-confirmation gates, or
  writes a card.

## Meaningful assertion and mutation review

Tests fail for these realistic regressions:

- an illegal skipped/terminal stage edge, mutable snapshot, unsafe ID/hash/
  reason, wrong chunk transition, or total-card overflow;
- wrong level default/range/ceiling, bool/float call count, purpose outside a
  level, thirteenth Deep call, lost failed-call charge, repeated repair, or
  repeated supplement;
- model pass overriding a local block, unsupported repaired claim, second
  repair, persisted reasoning, changed candidate identity, or raw callback
  exception;
- missing/overcovered section loss, duplicate-point loss, supplement during
  overflow, canonical punctuation/whitespace regression, unstable first-wins
  order, source-free fuzzy match, semantic matcher invocation, or comparison
  bound overflow;
- sibling card loss, retry of a successful/foreign chunk, preparation billing,
  duplicate retry billing/completion, or inability to explicitly recover a
  completed partial run;
- collection use, mutable callback snapshots, pre-reservation callback,
  stale-result delivery, mid-worker old callback continuation, closed-window
  delivery, taskman/future/UI exception escape, or legacy controller breakage;
- disabled-mode note consumption, descendant/full-scan/mutation permission,
  21st note consumption, unsafe deck label, note mutation/body leakage, wrong
  aggregate literal, HTML misclassification, or real-sampling enablement.

Expected values are hand-derived literals. Tests exercise real pure models and
transitions; fake callbacks stand in only for the explicitly external
planner/generator/critic boundary.

## Concerns

None blocking.

The intelligent controller is intentionally a Task 5 foundation: it processes
only injected callbacks and safe in-memory outcomes. Task 6 owns product UI
wiring. Deck-style real Anki sampling remains deliberately disabled pending the
separate manual acceptance boundary. Similar deduplication is conservative and
source-overlap-gated; semantic/embedding deduplication remains protocol-only.

## Review fix round 1

The first review round identified two critical lifecycle/accounting gaps and
nine important boundedness/coherence gaps. All findings were reproduced with
focused tests before their production fixes.

### RED evidence

The public repair boundary initially did not accept or bill a run:

```text
> python -m unittest tests.test_critic_repair_v014
EEE....
Ran 7 tests
FAILED (errors=3)
```

The controller tests then demonstrated that local critic decisions and model
rejections were discarded, minimum calls were not enforced, generator
materialization failures lost their billed run, supersession during iteration
did not stop the critic, and deduplication/coverage were skipped:

```text
> python -m unittest tests.test_intelligent_generation_task_controller
...F.FFFFFF...
Ran 14 tests
FAILED (failures=8)
```

The consolidated validation RED run covered direct run coherence, bounded
snapshot traversal, deck-field access, exact recovery accounting, symbol-safe
deduplication, coverage-at-capacity, and safe exception/completion models:

```text
> python -m unittest tests.test_generation_run_v014 tests.test_coverage_dedup_v014 tests.test_partial_failure_recovery tests.test_deck_style_profile tests.test_intelligence_call_budget tests.test_intelligent_generation_task_controller
Ran 55 tests
FAILED (failures=16, errors=2)
```

After the main fixes, a 77-test run exposed 15 transition-order errors caused
by constructing an intermediate failed chunk with a still-running status.
Making the failed-chunk/status replacement atomic reduced this to four fixture
errors; those fixtures were updated to satisfy the now-enforced minimum-call
and post-generation coherence rules.

### Corrective implementation

- Every generated card is now locally criticized against its owning source
  text. The optional callback decision is combined through `decide_card()`,
  so local blocks cannot be waived and callback `REJECT`/`REPAIR` outcomes
  cannot enter the accepted set.
- Critic calls are reserved before callback dispatch. Accepted cards are
  deterministically deduplicated and assessed for coverage before completion.
- `repair_and_revalidate()` now requires a run and point ID, atomically
  reserves the single repair before invoking the callback, and returns the
  billed run on success and all safe rejection/error paths.
- Completion enforces the actual Fast/Standard/Deep minimums of 1/3/4 calls.
  The controller returns a safe structured failure when real lifecycle calls
  do not meet that policy; it never fabricates dummy calls.
- Freshness is checked before every reservation/callback and after callback
  output materialization. Iterator failures and supersession preserve the
  latest billed run and prevent later critic work.
- `CoverageReport` and the assessor only recommend supplementation when
  `card_count < max_cards`.
- Direct `GenerationRun` construction now validates stage/status/level,
  chunk-state, call-purpose, completion-minimum, retry-dispatch, and error-code
  coherence. Failed chunk/state changes are atomic.
- Snapshot freezing now has explicit depth, node, mapping-key, sequence-item,
  text, and byte limits; it rejects cycles and hostile/unsupported values.
  Deck-style field iteration consumes at most 33 keys to prove the 32-field
  cap without trusting hostile `len()`/`items()`.
- Recovery validates exact source call counts in `0..12`, records the call
  count used for each dispatch, and rejects stale lower or higher counts at
  preparation, dispatch, and completion boundaries.
- Canonical deduplication removes punctuation and whitespace while retaining
  Unicode symbols used by mathematics and code.
- `CallBudgetError` and `IntelligentGenerationTaskCompletion` now validate
  bounded safe codes, numeric counts, purpose types, and request/run identity.

### GREEN and final verification

```text
> python -m unittest tests.test_generation_run_v014 tests.test_coverage_dedup_v014 tests.test_partial_failure_recovery tests.test_deck_style_profile tests.test_intelligence_call_budget tests.test_intelligent_generation_task_controller tests.test_critic_repair_v014
.............................................................................
Ran 77 tests in 0.032s
OK

> python -m unittest tests.test_card_quality_v4 tests.test_review_workbench_v4 tests.test_async_card_generation tests.test_generation_task_controller tests.test_generation_run_v014 tests.test_intelligence_call_budget tests.test_critic_repair_v014 tests.test_coverage_dedup_v014 tests.test_partial_failure_recovery tests.test_deck_style_profile tests.test_intelligent_generation_task_controller
...............................................................................................................
Ran 111 tests in 0.092s
OK

> python -m py_compile <all changed Python files>
OK

> git diff --check
OK
```

No blocking concerns remain. This round preserves the original Task 5
boundaries: no provider/network execution, no collection/write access, no
automatic retry, no review bypass, no push, and exactly one amended Task 5
commit.

## Review fix round 2

The second review round found one critical hostile-output escape and two
important source-snapshot/coverage gaps. Each was reproduced before production
changes.

### RED evidence

```text
> python -m unittest tests.test_critic_repair_v014 tests.test_generation_run_v014 tests.test_intelligent_generation_task_controller
.E...................F.........F....F.....
Ran 42 tests in 0.024s
FAILED (failures=3, errors=1)
```

The error was the raw `RuntimeError` from a repaired mapping whose `items()`
method failed after the repair reservation. The three failures showed that a
frozen dataclass retained its mutable list alias, missing high-priority points
were invisible because expected coverage was derived from accepted cards, and
a run without any coverage source completed successfully.

### Corrective implementation

- Post-dispatch repair processing now catches every ordinary exception and
  returns `repair_output_invalid` with the already-frozen input and billed run.
  Callback/output exception text never crosses the boundary.
- Snapshot freezing recursively captures every dataclass field under the same
  depth, node, sequence, mapping, text, and byte limits. Frozen dataclass
  instances are copied as the same safe model type with deeply immutable field
  values, so later mutation of an input alias cannot change a run snapshot.
- Controller coverage now requires the validated `KnowledgePlan` stored on the
  run, validates its document/chunk universe, preserves point priority,
  section, and source-chunk identity, and assesses accepted/deduplicated cards
  against the full plan. Missing source data fails safely with
  `coverage_source_unavailable`; invalid card/plan assessment fails with a
  separate safe coverage code.
- Focused coverage assertions prove a missing high-priority point, its
  uncovered section, and the resulting supplement recommendation.

### GREEN and final verification

```text
> python -m unittest tests.test_generation_run_v014 tests.test_coverage_dedup_v014 tests.test_partial_failure_recovery tests.test_deck_style_profile tests.test_intelligence_call_budget tests.test_intelligent_generation_task_controller tests.test_critic_repair_v014
.................................................................................
Ran 81 tests in 0.042s
OK

> python -m unittest tests.test_card_quality_v4 tests.test_review_workbench_v4 tests.test_async_card_generation tests.test_generation_task_controller tests.test_generation_run_v014 tests.test_intelligence_call_budget tests.test_critic_repair_v014 tests.test_coverage_dedup_v014 tests.test_partial_failure_recovery tests.test_deck_style_profile tests.test_intelligent_generation_task_controller
...................................................................................................................
Ran 115 tests in 0.101s
OK

> python -m unittest tests.test_document_ir tests.test_document_analyzer tests.test_knowledge_planner_v014 tests.test_generation_task_controller tests.test_intelligent_generation_task_controller
...............................................................
Ran 63 tests in 0.063s
OK

> python -m py_compile <all changed Python files>
OK

> git diff --check
OK
```

No blocking concerns remain. This round changes only Task 5 critic/run/controller
foundations and their focused tests/report; Task 6/UI code remains untouched.
