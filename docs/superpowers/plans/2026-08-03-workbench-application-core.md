# Workbench Application Core Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a pure-Python workbench application layer, make session invalidation explicit, and move generation/review/write orchestration out of Qt-heavy modules without changing the public Create -> Review -> Write workflow.

**Architecture:** Add immutable workbench state plus pure transitions beside the existing `BeginnerFlowSession`, then integrate it through a temporary compatibility bridge. Move pure generation lifecycle code and Anki workflow orchestration into `ankiforge_ai.workbench`; keep Qt task scheduling, concrete Anki adapters, and widgets in `ankiforge_ai.ui`, with compatibility aliases preserving tests.

**Tech Stack:** Python 3.9-compatible dataclasses/enums/protocols, PyQt/Anki adapters at the boundary, `unittest`, AST architecture checks, GitHub Actions, deterministic `.ankiaddon` packaging.

## Global Constraints

- Keep the visible two-column `Create -> Review -> Write` workflow unchanged.
- Do not add visible controls, public Cloze selection, PDF/OCR, URL/media import, embeddings, telemetry, or cloud services.
- API keys remain memory-only and must not appear in workbench state, preferences, repr output, logs, tests, or packages.
- Do not add automatic Provider calls or automatic retries.
- Do not move Anki collection reads or writes to an ordinary background thread.
- Existing duplicate checking and final confirmation remain hard gates.
- Preserve arbitrary Anki add-on directory-name startup compatibility and Python 3.9 syntax compatibility.
- Use pure functions and focused modules; do not add a generic event bus or dependency-injection framework.
- Every task must leave focused tests passing before commit.
- This plan covers the application-core migration. Quality/source/near-duplicate refinement and the warm-charcoal/soft-orange visual pass receive separate plans after this phase is accepted.

---

## File Structure

### New application modules

- `ankiforge_ai/workbench/__init__.py`: stable public exports for the application layer.
- `ankiforge_ai/workbench/models.py`: immutable state/value objects only.
- `ankiforge_ai/workbench/transitions.py`: pure validated state transitions and readiness selectors.
- `ankiforge_ai/workbench/legacy_bridge.py`: temporary projection from `BeginnerFlowSession` into immutable workbench state.
- `ankiforge_ai/workbench/store.py`: small in-memory holder for the current immutable state; no persistence and no secrets.
- `ankiforge_ai/workbench/generation_lifecycle.py`: pure intelligence-generation lifecycle currently embedded in the Qt task controller.
- `ankiforge_ai/workbench/review_use_cases.py`: review operations over a narrow protocol.
- `ankiforge_ai/workbench/write_coordinator.py`: dependency-injected application
  entry point for target reads, duplicate preview, preparation, and confirmed
  write execution; it imports no UI or Anki adapter implementation.

### Existing modules changed

- `ankiforge_ai/ui/card_maker_panel.py`: construct/synchronize the workbench store and delegate review/write operations.
- `ankiforge_ai/ui/intelligent_generation_task_controller.py`: retain taskman scheduling, request identity, and main-thread delivery; import pure lifecycle functions.
- `ankiforge_ai/ui/workbench_factory.py`: composition root that injects the
  existing target, duplicate, preview, preparation, and writer implementations.
- `ankiforge_ai/ui/read_only_anki_targets.py`: remains the tested Anki target adapter.
- `ankiforge_ai/ui/read_only_duplicate_check.py`: remains the tested read-only duplicate adapter.
- `ankiforge_ai/ui/beginner_final_confirmation.py`: remains the tested final-preview implementation.
- `ankiforge_ai/ui/beginner_real_write.py`: remains the tested write-preparation gate.
- `.github/workflows/ci.yml`: supported-version tests, compilation, and package validation.

### Tests

- `tests/test_workbench_models.py`
- `tests/test_workbench_transitions.py`
- `tests/test_workbench_legacy_bridge.py`
- `tests/test_generation_lifecycle.py`
- `tests/test_workbench_review_use_cases.py`
- `tests/test_workbench_write_coordinator.py`
- `tests/test_workbench_architecture.py`
- existing generation, review, duplicate, write, package, and installed-runtime suites.

---

### Task 1: Immutable Workbench State Models

**Files:**
- Create: `ankiforge_ai/workbench/__init__.py`
- Create: `ankiforge_ai/workbench/models.py`
- Test: `tests/test_workbench_models.py`

**Interfaces:**
- Produces: `WorkbenchArtifactStatus`, `MaterialState`, `GenerationState`, `ReviewDecisionRecord`, `ReviewState`, `WriteState`, `WorkbenchSessionState`, and `initial_workbench_state()`.
- Consumes: `SourceType` from `ankiforge_ai.pipeline.write_traceability`.

- [ ] **Step 1: Write failing validation and secret-safety tests**

```python
import unittest

from ankiforge_ai.pipeline.write_traceability import SourceType
from ankiforge_ai.workbench.models import (
    GenerationState,
    MaterialState,
    ReviewDecisionRecord,
    WorkbenchArtifactStatus,
    WorkbenchSessionState,
    initial_workbench_state,
)


class WorkbenchModelsTests(unittest.TestCase):
    def test_initial_state_is_empty_closed_over_safe_values(self):
        state = initial_workbench_state()
        self.assertFalse(state.material.has_material)
        self.assertEqual(state.material.source_type, SourceType.PASTE)
        self.assertEqual(state.generation.status, WorkbenchArtifactStatus.EMPTY)
        self.assertEqual(state.review.decisions, ())
        self.assertFalse(state.closed)
        self.assertNotIn("api", repr(state).casefold())
        self.assertNotIn("key", repr(state).casefold())

    def test_material_state_rejects_inconsistent_presence(self):
        with self.assertRaises(ValueError):
            MaterialState(revision=0, has_material=True, char_count=0)

    def test_generation_state_rejects_duplicate_candidate_ids(self):
        with self.assertRaises(ValueError):
            GenerationState(
                request_id=1,
                status=WorkbenchArtifactStatus.COMPLETE,
                candidate_revision=1,
                candidate_ids=("card-1", "card-1"),
            )

    def test_review_decision_uses_bounded_safe_identifiers(self):
        with self.assertRaises(ValueError):
            ReviewDecisionRecord(candidate_id="../card", decision="keep")

    def test_state_repr_contains_counts_not_material_or_card_content(self):
        state = WorkbenchSessionState(
            material=MaterialState(
                revision=1,
                has_material=True,
                char_count=25,
                source_type=SourceType.PASTE,
            )
        )
        rendered = repr(state)
        self.assertIn("material_revision=1", rendered)
        self.assertNotIn("material_text", rendered)
```

- [ ] **Step 2: Run the focused test and verify the missing-module failure**

Run: `python -m unittest tests.test_workbench_models -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'ankiforge_ai.workbench'`.

- [ ] **Step 3: Implement the immutable model contract**

Create enums and frozen dataclasses with these exact fields:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Optional

from ..pipeline.write_traceability import SourceType


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class WorkbenchArtifactStatus(str, Enum):
    EMPTY = "empty"
    CURRENT = "current"
    RUNNING = "running"
    FAILED = "failed"
    STALE = "stale"
    COMPLETE = "complete"


@dataclass(frozen=True, repr=False)
class MaterialState:
    revision: int = 0
    has_material: bool = False
    char_count: int = 0
    source_type: SourceType = SourceType.PASTE


@dataclass(frozen=True, repr=False)
class GenerationState:
    request_id: Optional[int] = None
    status: WorkbenchArtifactStatus = WorkbenchArtifactStatus.EMPTY
    candidate_revision: int = 0
    candidate_ids: tuple[str, ...] = field(default_factory=tuple)
    error_code: Optional[str] = None


@dataclass(frozen=True)
class ReviewDecisionRecord:
    candidate_id: str
    decision: str


@dataclass(frozen=True, repr=False)
class ReviewState:
    candidate_revision: int = 0
    revision: int = 0
    status: WorkbenchArtifactStatus = WorkbenchArtifactStatus.EMPTY
    decisions: tuple[ReviewDecisionRecord, ...] = field(default_factory=tuple)


@dataclass(frozen=True, repr=False)
class WriteState:
    target_revision: int = 0
    mapping_revision: int = 0
    duplicate_candidate_revision: Optional[int] = None
    duplicate_target_revision: Optional[int] = None
    duplicate_mapping_revision: Optional[int] = None
    status: WorkbenchArtifactStatus = WorkbenchArtifactStatus.EMPTY


@dataclass(frozen=True, repr=False)
class WorkbenchSessionState:
    material: MaterialState = field(default_factory=MaterialState)
    generation: GenerationState = field(default_factory=GenerationState)
    review: ReviewState = field(default_factory=ReviewState)
    write: WriteState = field(default_factory=WriteState)
    closed: bool = False


def initial_workbench_state() -> WorkbenchSessionState:
    return WorkbenchSessionState()
```

Implement `__post_init__` validation for non-negative integer revisions/counts,
safe unique candidate IDs, safe bounded error codes, valid decision values
`keep`, `discard`, and `needs_edit`, and cross-state candidate-revision
consistency. Implement redacted `__repr__` methods that expose only status,
revisions, and counts.

- [ ] **Step 4: Export stable names and run focused tests**

`ankiforge_ai/workbench/__init__.py` explicitly imports and lists the model names
in `__all__`; it must not import Qt, `aqt`, Provider transports, or Anki writer
modules.

Run: `python -m unittest tests.test_workbench_models -v`

Expected: PASS.

- [ ] **Step 5: Run syntax compatibility and commit**

Run: `python -m compileall -q ankiforge_ai/workbench tests/test_workbench_models.py`

Expected: exit 0.

```powershell
git add ankiforge_ai/workbench tests/test_workbench_models.py
git commit -m "Add immutable workbench state models"
```

---

### Task 2: Pure State Transitions and Invalidation Rules

**Files:**
- Create: `ankiforge_ai/workbench/transitions.py`
- Modify: `ankiforge_ai/workbench/__init__.py`
- Test: `tests/test_workbench_transitions.py`

**Interfaces:**
- Consumes: Task 1 state dataclasses.
- Produces: `update_material`, `start_generation`, `complete_generation`, `fail_generation`, `record_review_decision`, `change_target`, `change_mapping`, `mark_duplicate_check_current`, `write_is_ready`, and `close_session`.

- [ ] **Step 1: Write failing transition tests**

```python
import unittest

from ankiforge_ai.pipeline.write_traceability import SourceType
from ankiforge_ai.workbench import initial_workbench_state
from ankiforge_ai.workbench.transitions import (
    complete_generation,
    mark_duplicate_check_current,
    record_review_decision,
    start_generation,
    update_material,
    write_is_ready,
)


class WorkbenchTransitionTests(unittest.TestCase):
    def test_material_change_invalidates_all_downstream_state(self):
        state = update_material(
            initial_workbench_state(),
            char_count=20,
            source_type=SourceType.PASTE,
        )
        state = start_generation(state, request_id=1)
        state = complete_generation(state, request_id=1, candidate_ids=("c1",))
        state = record_review_decision(state, "c1", "keep")
        state = mark_duplicate_check_current(state)

        changed = update_material(
            state,
            char_count=25,
            source_type=SourceType.MARKDOWN,
        )

        self.assertEqual(changed.material.revision, 2)
        self.assertEqual(changed.generation.candidate_ids, ())
        self.assertEqual(changed.review.decisions, ())
        self.assertFalse(write_is_ready(changed))

    def test_stale_generation_completion_is_ignored(self):
        state = update_material(
            initial_workbench_state(),
            char_count=10,
            source_type=SourceType.PASTE,
        )
        running = start_generation(state, request_id=2)
        self.assertIs(
            complete_generation(running, request_id=1, candidate_ids=("old",)),
            running,
        )

    def test_duplicate_check_must_match_candidate_and_mapping_revisions(self):
        state = update_material(
            initial_workbench_state(),
            char_count=10,
            source_type=SourceType.PASTE,
        )
        state = complete_generation(
            start_generation(state, request_id=1),
            request_id=1,
            candidate_ids=("c1",),
        )
        state = record_review_decision(state, "c1", "keep")
        current = mark_duplicate_check_current(state)
        self.assertTrue(write_is_ready(current))
        self.assertFalse(write_is_ready(update_material(
            current,
            char_count=11,
            source_type=SourceType.PASTE,
        )))
```

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_workbench_transitions -v`

Expected: FAIL because `ankiforge_ai.workbench.transitions` does not exist.

- [ ] **Step 3: Implement transitions with `dataclasses.replace`**

Use this exact transition implementation, with validation delegated to the
frozen dataclasses from Task 1:

```python
from dataclasses import replace


def _require_open(state: WorkbenchSessionState) -> None:
    if state.closed:
        raise RuntimeError("closed workbench sessions cannot be reused")


def update_material(
    state: WorkbenchSessionState,
    *,
    char_count: int,
    source_type: SourceType,
) -> WorkbenchSessionState:
    _require_open(state)
    material = MaterialState(
        revision=state.material.revision + 1,
        has_material=char_count > 0,
        char_count=char_count,
        source_type=source_type,
    )
    return replace(
        state,
        material=material,
        generation=GenerationState(),
        review=ReviewState(),
        write=WriteState(),
    )

def start_generation(
    state: WorkbenchSessionState,
    *,
    request_id: int,
) -> WorkbenchSessionState:
    _require_open(state)
    if not state.material.has_material:
        raise ValueError("material is required before generation")
    generation = GenerationState(
        request_id=request_id,
        status=WorkbenchArtifactStatus.RUNNING,
        candidate_revision=state.generation.candidate_revision,
    )
    return replace(
        state,
        generation=generation,
        review=ReviewState(),
        write=WriteState(
            target_revision=state.write.target_revision,
            mapping_revision=state.write.mapping_revision,
        ),
    )

def complete_generation(
    state: WorkbenchSessionState,
    *,
    request_id: int,
    candidate_ids: tuple[str, ...],
) -> WorkbenchSessionState:
    _require_open(state)
    if request_id != state.generation.request_id:
        return state
    candidate_revision = state.generation.candidate_revision + 1
    generation = GenerationState(
        request_id=request_id,
        status=WorkbenchArtifactStatus.COMPLETE,
        candidate_revision=candidate_revision,
        candidate_ids=candidate_ids,
    )
    return replace(
        state,
        generation=generation,
        review=ReviewState(
            candidate_revision=candidate_revision,
            status=WorkbenchArtifactStatus.CURRENT,
        ),
        write=WriteState(
            target_revision=state.write.target_revision,
            mapping_revision=state.write.mapping_revision,
        ),
    )

def fail_generation(
    state: WorkbenchSessionState,
    *,
    request_id: int,
    error_code: str,
) -> WorkbenchSessionState:
    _require_open(state)
    if request_id != state.generation.request_id:
        return state
    return replace(
        state,
        generation=replace(
            state.generation,
            status=WorkbenchArtifactStatus.FAILED,
            candidate_ids=(),
            error_code=error_code,
        ),
        review=ReviewState(),
        write=WriteState(
            target_revision=state.write.target_revision,
            mapping_revision=state.write.mapping_revision,
        ),
    )

def record_review_decision(
    state: WorkbenchSessionState,
    candidate_id: str,
    decision: str,
) -> WorkbenchSessionState:
    _require_open(state)
    if candidate_id not in state.generation.candidate_ids:
        raise ValueError("candidate_id is not part of the current generation")
    decisions = {
        item.candidate_id: item for item in state.review.decisions
    }
    decisions[candidate_id] = ReviewDecisionRecord(candidate_id, decision)
    ordered = tuple(
        decisions[item]
        for item in state.generation.candidate_ids
        if item in decisions
    )
    review_status = (
        WorkbenchArtifactStatus.COMPLETE
        if len(ordered) == len(state.generation.candidate_ids)
        else WorkbenchArtifactStatus.CURRENT
    )
    return replace(
        state,
        review=ReviewState(
            candidate_revision=state.generation.candidate_revision,
            revision=state.review.revision + 1,
            status=review_status,
            decisions=ordered,
        ),
        write=replace(
            state.write,
            duplicate_candidate_revision=None,
            duplicate_target_revision=None,
            duplicate_mapping_revision=None,
            status=WorkbenchArtifactStatus.STALE,
        ),
    )

def change_target(state: WorkbenchSessionState) -> WorkbenchSessionState:
    _require_open(state)
    return replace(
        state,
        write=WriteState(
            target_revision=state.write.target_revision + 1,
            mapping_revision=state.write.mapping_revision,
            status=WorkbenchArtifactStatus.STALE,
        ),
    )


def change_mapping(state: WorkbenchSessionState) -> WorkbenchSessionState:
    _require_open(state)
    return replace(
        state,
        write=WriteState(
            target_revision=state.write.target_revision,
            mapping_revision=state.write.mapping_revision + 1,
            status=WorkbenchArtifactStatus.STALE,
        ),
    )


def mark_duplicate_check_current(
    state: WorkbenchSessionState,
) -> WorkbenchSessionState:
    _require_open(state)
    if state.review.status is not WorkbenchArtifactStatus.COMPLETE:
        raise ValueError("review must be complete before duplicate checking")
    return replace(
        state,
        write=replace(
            state.write,
            duplicate_candidate_revision=state.generation.candidate_revision,
            duplicate_target_revision=state.write.target_revision,
            duplicate_mapping_revision=state.write.mapping_revision,
            status=WorkbenchArtifactStatus.CURRENT,
        ),
    )


def write_is_ready(state: WorkbenchSessionState) -> bool:
    decisions = {item.decision for item in state.review.decisions}
    return (
        not state.closed
        and state.generation.status is WorkbenchArtifactStatus.COMPLETE
        and state.review.status is WorkbenchArtifactStatus.COMPLETE
        and "keep" in decisions
        and state.write.status is WorkbenchArtifactStatus.CURRENT
        and state.write.duplicate_candidate_revision
        == state.generation.candidate_revision
        and state.write.duplicate_target_revision == state.write.target_revision
        and state.write.duplicate_mapping_revision == state.write.mapping_revision
    )


def close_session(state: WorkbenchSessionState) -> WorkbenchSessionState:
    _require_open(state)
    return WorkbenchSessionState(closed=True)
```

Material changes reset generation/review/write to defaults. Generation completion
increments candidate revision and resets review/write. Review changes clear the
duplicate snapshot. Target or mapping changes invalidate duplicate readiness.
Stale completion/failure request IDs return the identical input object. Closed
state rejects every mutating transition.

- [ ] **Step 4: Run focused models and transition tests**

Run: `python -m unittest tests.test_workbench_models tests.test_workbench_transitions -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add ankiforge_ai/workbench tests/test_workbench_transitions.py
git commit -m "Add workbench state transitions"
```

---

### Task 3: Legacy Session Projection and Panel Store

**Files:**
- Create: `ankiforge_ai/workbench/legacy_bridge.py`
- Create: `ankiforge_ai/workbench/store.py`
- Modify: `ankiforge_ai/workbench/__init__.py`
- Modify: `ankiforge_ai/ui/card_maker_panel.py:144-198,2619-2760`
- Test: `tests/test_workbench_legacy_bridge.py`
- Modify: `tests/test_single_screen_card_maker.py`

**Interfaces:**
- Consumes: `BeginnerFlowSession` through attribute access only; Task 1 models.
- Produces: `project_legacy_session(session, active_request_id=None,
  target_revision=0, mapping_revision=0)`,
  `WorkbenchSessionStore.from_legacy(session)`,
  `WorkbenchSessionStore.synchronize(session, active_request_id=None)`,
  `WorkbenchSessionStore.state`, and `WorkbenchSessionStore.close()`.

- [ ] **Step 1: Write failing bridge tests**

```python
import unittest

from ankiforge_ai.ui.beginner_flow_models import BeginnerFlowSession
from ankiforge_ai.workbench.legacy_bridge import project_legacy_session
from ankiforge_ai.workbench.store import WorkbenchSessionStore


class WorkbenchLegacyBridgeTests(unittest.TestCase):
    def test_projection_tracks_material_candidates_reviews_and_write_revisions(self):
        session = BeginnerFlowSession()
        session.update_material("alpha beta gamma")
        projected = project_legacy_session(session)
        self.assertTrue(projected.material.has_material)
        self.assertEqual(projected.material.char_count, 16)
        self.assertEqual(projected.material.revision, session.material_revision)

    def test_store_synchronization_replaces_an_immutable_snapshot(self):
        session = BeginnerFlowSession()
        store = WorkbenchSessionStore.from_legacy(session)
        first = store.state
        session.update_material("new material")
        second = store.synchronize(session)
        self.assertIsNot(first, second)
        self.assertIs(second, store.state)

    def test_store_repr_never_contains_material(self):
        session = BeginnerFlowSession(material_text="private study material")
        store = WorkbenchSessionStore.from_legacy(session)
        self.assertNotIn("private study material", repr(store))
```

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_workbench_legacy_bridge -v`

Expected: FAIL because bridge/store modules do not exist.

- [ ] **Step 3: Implement the explicit projection table**

`project_legacy_session()` uses this fixed mapping:

- `material_revision`, `material_text`, and `source_type` -> `MaterialState`;
- `IDLE` -> `EMPTY`, `RUNNING` -> `RUNNING`, `SUCCESS` -> `COMPLETE`, and
  every Provider/timeout/parse/material error enum -> `FAILED` with the enum
  value copied as the bounded `error_code`;
- the supplied active request ID is copied only while generation is running;
- ordered candidate IDs from AI drafts, falling back to candidate previews;
- review values map `LOOKS_GOOD` -> `keep`, `NEEDS_CHANGES` -> `needs_edit`,
  and `SKIP_FOR_NOW` -> `discard`; decisions are ordered by candidate order;
- review status is `EMPTY` without candidates, `COMPLETE` when every current
  candidate has a decision, and `CURRENT` otherwise;
- `WorkbenchSessionStore` compares a private target fingerprint
  `(deck_id, note_type_id)` and mapping fingerprint
  `(front_field, back_field, source_field)` on every synchronization. A changed
  fingerprint increments the matching revision and clears the duplicate
  snapshot. These fingerprints are excluded from repr and never leave memory;
- a current legacy duplicate preview records the current candidate, target, and
  mapping revisions; an empty/cleared preview records no snapshot;
- `closed` -> `WorkbenchSessionState.closed`.

It copies counts, IDs, statuses, and revisions only. It must never copy material
text, card content, source excerpts, paths, runtime settings, or credentials.

On `from_legacy`, a non-empty target or mapping fingerprint starts at revision
1 and an empty fingerprint starts at 0. On each `synchronize`, compare the new
fingerprints with the private prior values, increment only changed revisions,
then call `project_legacy_session` with those revisions. Never derive a revision
from a Python hash because hash randomization would make state nondeterministic.

- [ ] **Step 4: Implement the store and wire it read-only into the panel**

Add in `CardMakerPanel.__init__` immediately after `self.session`:

```python
self.workbench_store = WorkbenchSessionStore.from_legacy(self.session)
```

Add:

```python
def _sync_workbench_state(self):
    active_request_id = self._intelligent_generation_controller.current_request_id
    return self.workbench_store.synchronize(
        self.session,
        active_request_id=active_request_id,
    )
```

Call it once at the beginning of `_refresh_product_state()` and close it from
`discard_session()`. This task does not change button enablement yet; it proves
the bridge can observe the current product without behavior changes.

- [ ] **Step 5: Add a UI contract assertion and run focused tests**

Extend `tests/test_single_screen_card_maker.py` to assert that
`WorkbenchSessionStore` is constructed and synchronized, while `_ai_runtime_settings`
is not passed into it.

Run:

`python -m unittest tests.test_workbench_models tests.test_workbench_transitions tests.test_workbench_legacy_bridge tests.test_single_screen_card_maker -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add ankiforge_ai/workbench ankiforge_ai/ui/card_maker_panel.py tests/test_workbench_legacy_bridge.py tests/test_single_screen_card_maker.py
git commit -m "Bridge the current UI into workbench state"
```

---

### Task 4: Extract the Pure Generation Lifecycle

**Files:**
- Create: `ankiforge_ai/workbench/generation_lifecycle.py`
- Modify: `ankiforge_ai/workbench/__init__.py`
- Modify: `ankiforge_ai/ui/intelligent_generation_task_controller.py:1-1538`
- Create: `tests/test_generation_lifecycle.py`
- Modify: `tests/test_intelligent_generation_task_controller.py`

**Interfaces:**
- Produces: `GenerationLifecycleResult`, `IntelligentGenerationProgress`,
  `execute_generation_lifecycle`, `execute_failed_retry_lifecycle`,
  `apply_coverage_supplement`, and `failed_generation_retry_is_available`.
- Consumes: existing immutable `GenerationRun`, planning, critic, recovery, coverage, deduplication, and generation settings APIs.
- The Qt controller retains `IntelligentGenerationRequestSnapshot`,
  `IntelligentGenerationTaskCompletion`, request locking, taskman scheduling,
  stale-delivery suppression, and close/invalidate behavior. It re-exports the
  moved progress type for compatibility.

- [ ] **Step 1: Write an architecture-focused failing test**

```python
import ast
from pathlib import Path
import unittest


class GenerationLifecycleArchitectureTests(unittest.TestCase):
    def test_pure_lifecycle_module_has_no_qt_or_aqt_import(self):
        path = Path("ankiforge_ai/workbench/generation_lifecycle.py")
        self.assertTrue(path.exists())
        tree = ast.parse(path.read_text(encoding="utf-8"))
        roots = {
            node.names[0].name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
        }
        roots.update(
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        self.assertNotIn("aqt", roots)
        self.assertNotIn("PyQt6", roots)
```

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_generation_lifecycle -v`

Expected: FAIL because the lifecycle module does not exist.

- [ ] **Step 3: Move pure lifecycle code without semantic edits**

Move `failed_generation_retry_is_available`, `_WorkerResult`,
`IntelligentGenerationProgress`, `_execute_lifecycle`, and every helper from
`_execute_lifecycle` through the end of
`ui/intelligent_generation_task_controller.py` into the new module. Rename the
definitions, not just local call sites:

| Existing definition | New definition |
| --- | --- |
| `_WorkerResult` | `GenerationLifecycleResult` |
| `_execute_lifecycle` | `execute_generation_lifecycle` |
| `_execute_failed_retry_lifecycle` | `execute_failed_retry_lifecycle` |
| `_apply_coverage_supplement` | `apply_coverage_supplement` |

Keep each complete function signature and body unchanged except for calls to
the renamed symbols. Private helpers remain private. Preserve all bounds,
failure codes, budget accounting, deduplication, repair, coverage, progress,
and retry behavior byte-for-byte.

- [ ] **Step 4: Reduce the Qt controller to scheduling and compatibility aliases**

Import the public lifecycle functions. Keep temporary aliases because existing
tests import private names:

```python
_WorkerResult = GenerationLifecycleResult
_execute_lifecycle = execute_generation_lifecycle
_execute_failed_retry_lifecycle = execute_failed_retry_lifecycle
_apply_coverage_supplement = apply_coverage_supplement
```

Change background task calls to public names. Do not alter `uses_collection=False`,
request locking, `run_on_main`, stale callback handling, or callback exception
containment.

- [ ] **Step 5: Move pure lifecycle assertions to the new test module**

Import public names from `ankiforge_ai.workbench.generation_lifecycle` in the new
test. Keep controller scheduling/stale-delivery tests in the existing controller
test. Add one compatibility assertion that old private aliases reference the new
functions.

Run:

`python -m unittest tests.test_generation_lifecycle tests.test_intelligent_generation_task_controller -v`

Expected: PASS with the same generation outcomes and call budgets as the baseline.

- [ ] **Step 6: Run dependent v0.14 intelligence tests and commit**

Run:

`python -m unittest tests.test_generation_run_v014 tests.test_critic_repair_v014 tests.test_coverage_dedup_v014 tests.test_universal_document_ui_contract -v`

Expected: PASS.

```powershell
git add ankiforge_ai/workbench ankiforge_ai/ui/intelligent_generation_task_controller.py tests/test_generation_lifecycle.py tests/test_intelligent_generation_task_controller.py
git commit -m "Extract the pure generation lifecycle"
```

---

### Task 5: Extract Review Use Cases Behind a Narrow Port

**Files:**
- Create: `ankiforge_ai/workbench/review_use_cases.py`
- Modify: `ankiforge_ai/workbench/__init__.py`
- Modify: `ankiforge_ai/ui/card_maker_panel.py:1978-2198`
- Test: `tests/test_workbench_review_use_cases.py`
- Modify: `tests/test_review_workbench_v4.py`

**Interfaces:**
- Produces: `ReviewSessionPort`, `ReviewCounts`, and `ReviewUseCases` methods `snapshot()`, `set_decision()`, `replace_content()`, `restore_content()`, `keep_clean()`, and `discard_blocking()`.
- Consumes: the existing `BeginnerFlowSession` through the protocol only.

- [ ] **Step 1: Write failing use-case tests with a fake port**

```python
import unittest

from ankiforge_ai.workbench.review_use_cases import ReviewUseCases


class FakeReviewSession:
    def __init__(self):
        self.calls = []

    def review_workbench_snapshot(self):
        self.calls.append(("snapshot",))
        return "snapshot"

    def set_candidate_review_decision(self, candidate_id, decision):
        self.calls.append(("decision", candidate_id, decision))

    def replace_candidate_content(self, candidate_id, front, back):
        self.calls.append(("replace", candidate_id, front, back))

    def restore_candidate_content(self, candidate_id):
        self.calls.append(("restore", candidate_id))

    def keep_clean_candidates(self):
        self.calls.append(("keep_clean",))
        return 2

    def discard_blocking_candidates(self):
        self.calls.append(("discard_blocking",))
        return 1


class WorkbenchReviewUseCasesTests(unittest.TestCase):
    def test_use_cases_delegate_only_declared_review_operations(self):
        session = FakeReviewSession()
        use_cases = ReviewUseCases(session)
        use_cases.set_decision("c1", "keep")
        use_cases.replace_content("c1", "front", "back")
        use_cases.restore_content("c1")
        self.assertEqual(use_cases.keep_clean(), 2)
        self.assertEqual(use_cases.discard_blocking(), 1)
        self.assertEqual(session.calls[0], ("decision", "c1", "keep"))
```

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_workbench_review_use_cases -v`

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement the runtime-checkable protocol and use cases**

The module imports only `typing` and pure model types. It validates safe candidate
IDs and allowed decisions before delegation. `replace_content` requires strings
and enforces the existing material/card length limits before calling the port.
`ReviewCounts` contains only non-negative `ready`, `review`, `blocked`, `kept`,
and `discarded` counts and has a redacted repr.

- [ ] **Step 4: Wire panel review actions through one use-case object**

Construct:

```python
self.review_use_cases = ReviewUseCases(self.session)
```

Update `_discard_blocking_cards`, `_keep_clean_cards`, `_restore_card`,
`_set_card_decision`, and `_edit_card` to call the use-case object. Keep existing
rendering, copy-card behavior, dialogs, translated messages, downstream
invalidation, and final-confirmation behavior unchanged.

- [ ] **Step 5: Run review and UI contract tests**

Run:

`python -m unittest tests.test_workbench_review_use_cases tests.test_review_workbench_v4 tests.test_single_screen_card_maker tests.test_v1_core_ui_contract -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add ankiforge_ai/workbench ankiforge_ai/ui/card_maker_panel.py tests/test_workbench_review_use_cases.py tests/test_review_workbench_v4.py
git commit -m "Move review actions behind workbench use cases"
```

---

### Task 6: Put Anki Workflow Orchestration Behind an Injected Boundary

**Files:**
- Create: `ankiforge_ai/workbench/write_coordinator.py`
- Modify: `ankiforge_ai/workbench/__init__.py`
- Create: `ankiforge_ai/ui/workbench_factory.py`
- Modify: `ankiforge_ai/ui/card_maker_panel.py:40-125,953-1043,2199-2618`
- Test: `tests/test_workbench_write_coordinator.py`
- Test: `tests/test_workbench_factory.py`
- Modify: existing static Anki target, duplicate, final-confirmation, and
  minimal-write contract tests.

**Interfaces:**
- Produces `PreparedWrite(final_preview, preparation)` and an injected
  `WorkbenchWriteCoordinator` with `read_targets()`, `read_fields(note_type_id)`,
  `check_duplicates(candidates, mapping)`, `prepare(session, mapping,
  duplicate_preview)`, and `execute_if_confirmed(confirmed, command)`.
- Keeps all existing concrete adapters and write-safety functions in their
  current tested modules during this phase.
- Keeps `MinimalAnkiWriter` as the collection adapter and preserves synchronous
  execution on Anki's safe collection thread.

- [ ] **Step 1: Write failing coordinator boundary tests**

```python
import unittest

from ankiforge_ai.workbench.write_coordinator import WorkbenchWriteCoordinator


class WorkbenchWriteCoordinatorTests(unittest.TestCase):
    def make_coordinator(self, calls):
        class TargetAdapter:
            def read_targets(self):
                calls.append(("read_targets",))
                return "targets"

            def read_fields(self, note_type_id):
                calls.append(("read_fields", note_type_id))
                return "fields"

        class DuplicateAdapter:
            def check(self, candidates, mapping):
                calls.append(("duplicates", candidates, mapping))
                return "duplicates"

        return WorkbenchWriteCoordinator(
            target_adapter=TargetAdapter(),
            duplicate_adapter=DuplicateAdapter(),
            writer=object(),
            final_preview_builder=lambda session, mapping, duplicates: "final",
            write_preparer=lambda session, final, mapping, duplicates: "prepared",
            confirmed_executor=lambda confirmed, writer, command: (
                confirmed,
                writer,
                command,
            ),
        )

    def test_target_and_duplicate_reads_delegate_to_injected_adapters(self):
        calls = []
        coordinator = self.make_coordinator(calls)
        self.assertEqual(coordinator.read_targets(), "targets")
        self.assertEqual(coordinator.read_fields(42), "fields")
        self.assertEqual(coordinator.check_duplicates(("card",), "mapping"), "duplicates")
        self.assertEqual(calls[-1], ("duplicates", ("card",), "mapping"))

    def test_prepare_builds_final_preview_before_write_preparation(self):
        coordinator = self.make_coordinator([])
        prepared = coordinator.prepare("session", "mapping", "duplicates")
        self.assertEqual(prepared.final_preview, "final")
        self.assertEqual(prepared.preparation, "prepared")

    def test_unconfirmed_execution_is_delegated_to_the_existing_hard_gate(self):
        coordinator = self.make_coordinator([])
        confirmed, _writer, command = coordinator.execute_if_confirmed(
            False,
            "command",
        )
        self.assertFalse(confirmed)
        self.assertEqual(command, "command")
```

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_workbench_write_coordinator -v`

Expected: FAIL because the coordinator module does not exist.

- [ ] **Step 3: Implement the pure injected coordinator**

`write_coordinator.py` imports only `dataclasses` and `typing`. Its constructor
requires adapter methods and three callables, validates them once, and stores no
collection object itself. Implement methods exactly as follows:

```python
@dataclass(frozen=True, repr=False)
class PreparedWrite:
    final_preview: object
    preparation: object

    def __repr__(self) -> str:
        return "PreparedWrite(final_preview=True, preparation=True)"


class WorkbenchWriteCoordinator:
    def __init__(
        self,
        *,
        target_adapter,
        duplicate_adapter,
        writer,
        final_preview_builder,
        write_preparer,
        confirmed_executor,
    ):
        for adapter, method_names, label in (
            (target_adapter, ("read_targets", "read_fields"), "target_adapter"),
            (duplicate_adapter, ("check",), "duplicate_adapter"),
        ):
            if any(not callable(getattr(adapter, name, None)) for name in method_names):
                raise TypeError(f"{label} does not satisfy its required interface")
        for callback, label in (
            (final_preview_builder, "final_preview_builder"),
            (write_preparer, "write_preparer"),
            (confirmed_executor, "confirmed_executor"),
        ):
            if not callable(callback):
                raise TypeError(f"{label} must be callable")
        self.target_adapter = target_adapter
        self.duplicate_adapter = duplicate_adapter
        self.writer = writer
        self._final_preview_builder = final_preview_builder
        self._write_preparer = write_preparer
        self._confirmed_executor = confirmed_executor

    def read_targets(self):
        return self.target_adapter.read_targets()

    def read_fields(self, note_type_id: int):
        return self.target_adapter.read_fields(note_type_id)

    def check_duplicates(self, candidates, mapping):
        return self.duplicate_adapter.check(candidates, mapping)

    def prepare(self, session, mapping, duplicate_preview):
        final_preview = self._final_preview_builder(
            session,
            mapping,
            duplicate_preview,
        )
        preparation = self._write_preparer(
            session,
            final_preview,
            mapping,
            duplicate_preview,
        )
        return PreparedWrite(final_preview, preparation)

    def execute_if_confirmed(self, confirmed: bool, command):
        return self._confirmed_executor(confirmed, self.writer, command)

    def __repr__(self) -> str:
        return (
            "WorkbenchWriteCoordinator("
            "target_adapter=True, duplicate_adapter=True, writer=True)"
        )
```

The constructor and repr test must prove that collection content, commands,
card content, and credentials cannot appear in repr. Do not add taskman,
threads, retries, or exception swallowing.

- [ ] **Step 4: Add the UI composition root**

`ui/workbench_factory.py` is the only new file that imports all concrete
implementations. Implement:

```python
def create_workbench_write_coordinator(collection):
    return WorkbenchWriteCoordinator(
        target_adapter=ReadOnlyAnkiTargetAdapter(collection),
        duplicate_adapter=ReadOnlyDuplicateCheckAdapter(collection),
        writer=MinimalAnkiWriter(collection),
        final_preview_builder=build_beginner_final_confirmation_preview,
        write_preparer=prepare_beginner_write,
        confirmed_executor=execute_beginner_write_if_confirmed,
    )
```

Add a factory test that patches each constructor/function and asserts identity,
without creating Anki or touching a collection.

- [ ] **Step 5: Wire the panel to one coordinator**

Construct only:

```python
self.write_coordinator = create_workbench_write_coordinator(collection)
```

Replace direct `read_targets`, `read_fields`, duplicate check, final-preview,
preparation, and confirmed-execution calls with coordinator methods. Preserve
the panel's confirmation dialog, `QApplication.processEvents()` behavior,
target combos, message copy, summary rendering, session mutation order, and
result tracking exactly.

- [ ] **Step 6: Run all focused write-boundary tests**

Run:

`python -m unittest tests.test_workbench_write_coordinator tests.test_workbench_factory tests.test_beginner_read_only_anki_targets tests.test_beginner_read_only_duplicate_check tests.test_beginner_final_confirmation_preview tests.test_beginner_minimal_real_anki_write tests.test_write_safety_v3 tests.test_anki_field_content tests.test_v1_core_writer_tags -v`

Expected: PASS.

- [ ] **Step 7: Run static UI safety contracts and commit**

Run:

`python -m unittest tests.test_single_screen_card_maker tests.test_file_drop_import tests.test_universal_document_ui_contract tests.test_v1_core_ui_contract -v`

Expected: PASS after source assertions require the coordinator instead of direct
adapter/writer construction while preserving the same confirmation ordering.

```powershell
git add ankiforge_ai/workbench ankiforge_ai/ui/workbench_factory.py ankiforge_ai/ui/card_maker_panel.py tests/test_workbench_write_coordinator.py tests/test_workbench_factory.py tests/test_beginner_read_only_anki_targets.py tests/test_beginner_read_only_duplicate_check.py tests/test_beginner_final_confirmation_preview.py tests/test_beginner_minimal_real_anki_write.py tests/test_single_screen_card_maker.py tests/test_file_drop_import.py tests/test_universal_document_ui_contract.py tests/test_v1_core_ui_contract.py
git commit -m "Move Anki orchestration behind the workbench boundary"
```

---

### Task 7: Architecture Guards and Continuous Integration

**Files:**
- Create: `tests/test_workbench_architecture.py`
- Create: `.github/workflows/ci.yml`
- Modify: `tests/test_installed_package_runtime.py`
- Modify: `tests/test_build_ankiaddon.py`

**Interfaces:**
- Consumes: all workbench modules from Tasks 1-6.
- Produces: enforceable dependency and packaging rules; no runtime API.

- [ ] **Step 1: Write failing AST architecture tests**

```python
import ast
from pathlib import Path
import unittest


class WorkbenchArchitectureTests(unittest.TestCase):
    def test_workbench_modules_do_not_import_ui_qt_aqt_or_anki_adapters(self):
        forbidden = {"aqt", "PyQt5", "PyQt6", "ui", "anki_writer"}
        for path in Path("ankiforge_ai/workbench").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            roots = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots.update(item.name.split(".")[0] for item in node.names)
                elif isinstance(node, ast.ImportFrom):
                    roots.add((node.module or "").split(".")[0])
            self.assertFalse(forbidden & roots, path.as_posix())

    def test_card_maker_panel_has_no_direct_anki_writer_import(self):
        source = Path("ankiforge_ai/ui/card_maker_panel.py").read_text(encoding="utf-8")
        self.assertNotIn("from ..anki_writer", source)
        self.assertNotIn("MinimalAnkiWriter", source)
        self.assertNotIn("ReadOnlyAnkiTargetAdapter", source)
        self.assertNotIn("ReadOnlyDuplicateCheckAdapter", source)
        self.assertIn("create_workbench_write_coordinator", source)
```

- [ ] **Step 2: Verify RED against any remaining boundary violations**

Run: `python -m unittest tests.test_workbench_architecture -v`

Expected: FAIL until all new modules and panel imports follow the intended
boundary.

- [ ] **Step 3: Fix imports and extend installed-layout coverage**

Add `workbench/__init__.py`, `workbench/models.py`,
`workbench/generation_lifecycle.py`, and `workbench/write_coordinator.py` to the
critical installed-runtime import set. Add workbench files to the build script's
required runtime members. Preserve the existing rejection of absolute
`ankiforge_ai` self-imports and eager Python 3.10-only annotations.

- [ ] **Step 4: Add CI matrix**

Create `.github/workflows/ci.yml` with:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  verify:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: ["3.9", "3.13"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: python -m unittest discover
      - run: python -m compileall -q .
      - run: python scripts/build_ankiaddon.py
```

No CI step receives secrets, calls a Provider, launches Anki, or writes a
collection. Package validation remains inside the existing build script.

- [ ] **Step 5: Run architecture/package tests locally**

Run:

`python -m unittest tests.test_workbench_architecture tests.test_installed_package_runtime tests.test_build_ankiaddon -v`

Expected: PASS.

- [ ] **Step 6: Build once and commit**

Run: `python scripts/build_ankiaddon.py`

Expected: package validation passes and forbidden files remain 0.

```powershell
git add .github/workflows/ci.yml ankiforge_ai/workbench scripts/build_ankiaddon.py tests/test_workbench_architecture.py tests/test_installed_package_runtime.py tests/test_build_ankiaddon.py dist/ankiforge_ai.ankiaddon
git commit -m "Enforce workbench architecture in CI"
```

---

### Task 8: Phase-one Documentation and Full Verification

**Files:**
- Modify: `docs/future_roadmap.md`
- Create: `docs/workbench_architecture.md`
- Modify: `docs/manual_anki_acceptance.md`
- Modify: `README.md`
- Modify: `README.en.md`
- Test: `tests/test_workbench_release_contract.py`

**Interfaces:**
- Documents the actual Task 1-7 implementation only.
- Does not claim quality/source/theme phase completion.

- [ ] **Step 1: Write a failing release-contract test**

```python
from pathlib import Path
import unittest


class WorkbenchReleaseContractTests(unittest.TestCase):
    def test_current_docs_describe_the_workbench_boundary_without_overclaiming(self):
        architecture = Path("docs/workbench_architecture.md").read_text(encoding="utf-8")
        self.assertIn("Create → Review → Write", architecture)
        self.assertIn("API key", architecture)
        self.assertIn("session-only", architecture)
        self.assertIn("ordinary background thread", architecture)
        self.assertIn("compatibility bridge", architecture)
        self.assertIn("compatibility alias", architecture)
        self.assertNotIn("PDF OCR is supported", architecture)
```

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_workbench_release_contract -v`

Expected: FAIL because the architecture document does not exist.

- [ ] **Step 3: Document current boundaries and manual checks**

`docs/workbench_architecture.md` explains:

- UI, application, domain, and adapter responsibilities;
- immutable projection and temporary legacy bridge;
- pure generation lifecycle versus Qt scheduling;
- review and Anki write coordinators;
- API-key exclusion;
- collection-thread restriction;
- compatibility bridge/aliases and their removal criteria;
- remaining Phase 2 quality and Phase 3 visual work.

Update `future_roadmap.md` current baseline from v0.13.2 to the actual v0.14.1
baseline plus this workbench candidate. Add manual acceptance checks for startup,
settings, import, cancel/stale callback, review/edit/discard, duplicate check,
cancelled confirmation, test-deck write, and dialog teardown. README changes are
limited to accurate architecture/release-candidate status and must not market
unfinished quality or visual work as shipped.

- [ ] **Step 4: Run the full automatic suite**

Run: `python -m unittest discover`

Expected: all tests pass.

- [ ] **Step 5: Run compilation and diff checks**

Run: `python -m compileall -q .`

Expected: exit 0.

Run: `git diff --check`

Expected: no output and exit 0.

- [ ] **Step 6: Verify reproducible package build**

Run `python scripts/build_ankiaddon.py`, record file count, byte size, and SHA-256,
copy the artifact hash value, run the same command a second time, and assert the
second file count, size, and SHA-256 are identical. Inspect the archive and record:

- forbidden files = 0;
- config/user_files content = 0;
- backup/Anki collection data = 0;
- high-confidence real secrets = 0;
- absolute self-imports = 0.

- [ ] **Step 7: Commit phase-one docs and verification contracts**

```powershell
git add README.md README.en.md docs/future_roadmap.md docs/workbench_architecture.md docs/manual_anki_acceptance.md tests/test_workbench_release_contract.py dist/ankiforge_ai.ankiaddon
git commit -m "Document the workbench application boundary"
```

- [ ] **Step 8: Confirm phase-one branch state**

Run:

```powershell
git status --short
git log --oneline -10
```

Expected: clean worktree with all Phase 1 commits on
`codex/v0.15.0-workbench-core-quality-polish`. Do not merge, push, tag, upload
AnkiWeb, or create a GitHub Release without a separate explicit decision.
