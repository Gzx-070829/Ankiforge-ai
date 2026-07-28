# Task 6 report — universal document intelligence UI

## Outcome

Implemented the bounded multi-file document queue, async import controller,
capability dialog, bilingual intelligence/source presenters, intelligent
generation integration, explicit failed-generation-chunk retry, source chips,
and queue/material invalidation rules.

The panel now uses the intelligent controller only for parsed document runs.
Pasted/manual text is explicitly labeled as the legacy one-call path and the
Fast/Standard/Deep selector is disabled until a document has been imported.

## TDD evidence

RED was observed before each production slice:

- Queue/controller: missing `document_import_queue` and
  `document_import_task_controller` modules.
- Capability/intelligence/source presenters: three missing presenter modules.
- Panel integration: missing batch presenter and new queue/intelligence wiring.
- Task 5 integration blocker: four Standard/Deep failures caused by
  `minimum_call_policy_not_met`.
- Grouped adapter/controller contract: 34 tests produced 1 failure and 2
  errors (missing grouped protocol, missing injected Provider client, missing
  panel stage wiring).
- Repair/supplement lifecycle: 21 tests produced 2 failures because neither
  callback was dispatched.
- Adapter boundary audit: 19 tests produced 2 failures and 2 errors for hidden
  `__call__(None)` batches, retry quota lookup, missing critic evidence, and
  cross-document section collisions.
- Dynamic call display: 24 tests produced 2 failures while the UI still showed
  fixed policy-envelope lower bounds as per-run estimates.
- Panel thinness cleanup: 7 tests produced 1 failure while the obsolete
  synchronous importer remained.
- Paste/queue source-of-truth audit: 22 tests produced 1 failure and 1 error
  before the explicit paste path and centralized material sync existed.
- Deep empty-generation reservation audit: the focused regression test failed
  because the critic was still invoked after generation produced no cards.
- Independent review fix wave: 84 focused tests first exposed pending-import
  generation, dishonest card estimates/hidden batch overflow, omitted user
  settings and Auto routing, omitted file labels, missing complexity preflight,
  ineligible supplement billing, repeat-retry exceptions, excess repairs, and
  nonempty manual edits retaining the imported source type. The initial run
  produced 6 failures and 14 errors (subtest-expanded).
- Card-quota follow-up: a focused fake-Provider test showed output above the
  prompted batch quota was accepted; it failed before strict full-run quota
  enforcement was added.

GREEN after implementation:

- `python -m unittest tests.test_document_import_queue tests.test_document_import_task_controller`
  — 17 tests OK.
- `python -m unittest tests.test_document_capabilities_dialog tests.test_document_intelligence_presenter tests.test_source_location_presenter`
  — 18 tests OK.
- `python -m unittest tests.test_universal_document_ui_contract tests.test_file_drop_import tests.test_linear_flow_settings_modal tests.test_single_screen_card_maker`
  — 53 tests OK.
- Review-fix focused command covering queue, estimates, sources, controller,
  and universal UI contracts — 84 tests OK.
- `python -m unittest tests.test_generation_run_v014 tests.test_intelligence_call_budget tests.test_critic_repair_v014 tests.test_coverage_dedup_v014 tests.test_partial_failure_recovery tests.test_intelligent_generation_task_controller`
  — superseded by the broader exact Task 5 command below.
- Exact Task 5 regression command from the implementation plan — 132 tests
  OK.
- Required full UI/safety command — 133 tests OK.
- `python -m unittest discover -s tests` — 1,405 tests OK.

## Bounded lifecycle and Provider-call audit

- Every real planner, grouped-generation, critic, repair, supplement, and retry
  Provider callback is reserved before dispatch.
- Generation batches are preflighted against the remaining call budget before
  the first dispatch. Hostile iterables/mappings are consumed only to bounded
  limits.
- A failed generation batch becomes failed generation chunks while successful
  sibling cards survive. Retry is a separate explicit click and targets only
  those failed chunks.
- Standard performs planner + dynamic grouped generation, plus at most one
  locally triggered source-grounded repair for the whole run. Deep can repair
  at most once per point while budget remains.
- Deep adds the critic and at most one coverage supplement; supplement cards
  pass the deterministic local grounding gate. Missing points backed only by
  failed chunks, or runs already at their card limit, skip supplement
  reservation and dispatch.
- Failed generation retry is offered only when unscheduled failed chunks and
  enough remaining budget exist. A failed explicit retry cannot be scheduled
  a second time and never raises synchronously from the UI handler.
- Small runs are allowed to finish below historical policy-envelope lower
  bounds. The UI now shows the plan-specific mandatory count and policy
  ceiling (one-chunk Standard = 2 planned calls; Deep = 3). No dummy call is
  made or billed.
- Deep runs that produce no cards skip critic reservation and dispatch,
  preventing an empty adapter call from being presented as Provider usage.
- Every Provider prompt carries validated card mode, answer length, output
  language, and per-point recommended/effective template. The same immutable
  settings snapshot drives deterministic review and repair revalidation.
- Provider output is rejected above the prompted batch quota; empty successful
  chunk outcomes remain explicit rather than becoming false partial failures.
- Maximum 48-chunk/96-point planner, generation, and critic prompts are tested
  under the existing 50,000-character input limit. Critic prompts include
  bounded source evidence.
- Stale post-repair/post-supplement snapshots become superseded while retaining
  already charged reservations. Closing/discarding clears the adapter holding
  runtime credentials and makes late callbacks no-ops.

## Queue and source-of-truth audit

- Picker/drop preserve every selected local file in order.
- Queue rows expose safe filename/type/importer/status/counts/warnings only;
  private paths remain out of repr/safe dicts.
- All parsing, detection, analysis, chunking, and estimate work runs in the
  non-Qt import worker with `uses_collection=False`.
- One `_sync_material_from_document_queue()` path re-renders visible material
  after completion, reorder, remove, and retry success. Generation therefore
  uses the same ordered document snapshots represented in the editor.
- Manual editing clears the parsed queue and switches to the explicitly
  labeled pasted-text path, preventing stale original chunks from being sent.
- Queued/importing rows, pending serial requests, or a running import worker
  hard-disable generation in both button readiness and the handler.
- Combined batches are locally preflighted before confirmation or Provider
  setup. More than 48 chunks or 96 planned points receives an actionable
  bilingual error with zero Provider reservations or dispatch.
- Multi-document section identities are namespaced before coverage assessment.
- Source locations propagate through generated drafts and review previews, so
  safe file labels plus Page/Slide/Sheet/Cell/line/timestamp can be shown
  without a path.

## Panel thinness and progress disclosure

`card_maker_panel.py` is +776/-52 lines relative to Task 5. The delta is large,
but it is Qt construction, rendering, signal wiring, confirmation, and
request-safe completion routing. An audit found none of the forbidden parsing,
importer, analysis, chunking, local-planning, estimate, or Provider transport
calls in the panel. Those responsibilities remain in the queue/controller,
presenter, and bounded Provider adapter modules.

The controller does not expose a proven request-ID-checked main-thread
`on_progress` channel. The UI therefore uses honest coarse “bounded document
run in progress” copy and displays the terminal stage on completion. It does
not pretend to stream live analyzing/planning/critic/coverage events. Live
per-stage Qt delivery is documented as deferred.

## Static verification

- `python -m py_compile` succeeded for every changed/new Python production and
  test module.
- `git diff --check` succeeded. Git printed only the existing Windows
  LF-to-CRLF conversion notices.
- No real Provider/network call was used by tests; all Provider behavior used
  injected fakes.
- Review fixes remain deliberately unstaged and uncommitted while concurrent
  Task 7 release/evaluation changes are present in the shared worktree.
