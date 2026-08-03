# Workbench Application Architecture

This document describes the internal application boundary on the current
development branch. It preserves the visible `Create → Review → Write` flow;
it is not a new user-facing workflow.

## Layers

### UI

`ankiforge_ai/ui/` owns Qt widgets, translated copy, dialog lifetime, taskman
scheduling, and the composition roots that assemble concrete dependencies. The
main card panel renders state and sends explicit user actions to application
use cases. It no longer constructs the Anki writer or read adapters directly.

### Workbench application layer

`ankiforge_ai/workbench/` is pure Python. It owns:

- immutable, content-free session state;
- explicit material, generation, review, target, mapping, and duplicate
  invalidation rules;
- the pure bounded generation lifecycle;
- validated review commands;
- dependency-injected Anki workflow orchestration.

These modules do not import Qt, `aqt`, the UI package, or concrete Anki
adapters. Architecture tests enforce that direction.

### Domain and adapters

Existing `document/`, `intelligence/`, and `pipeline/` modules remain the domain
layer. Concrete Anki adapters, Provider transports, file importers, and Qt
taskman remain at the outside boundary. The workbench coordinator receives the
concrete Anki adapters from `ui/workbench_factory.py`; it never stores or opens
an Anki collection itself.

## Migration strategy

`BeginnerFlowSession` remains the behavior-compatible mutable session while the
new state model is adopted incrementally. A temporary compatibility bridge
projects only revisions, counts, safe IDs, statuses, and source type into an
immutable snapshot. It never copies material, card bodies, source excerpts,
paths, runtime Provider settings, or credentials.

The Qt generation controller retains scheduling, request locking, main-thread
delivery, and stale callback suppression. Its former pure lifecycle functions
now live in `workbench/generation_lifecycle.py`. A compatibility alias keeps
the older private test/import names available during migration.

Review actions use a narrow port. A small UI-side adapter maps application
decisions to the legacy session's values. Target reads, duplicate checks, final
preview, write preparation, and confirmed execution similarly pass through one
injected coordinator while their existing audited implementations remain in
place.

Compatibility bridge and compatibility alias removal requires a later,
separately reviewed migration after no product code relies on the legacy
session surface.

## Safety invariants

- The API key remains session-only and outside every workbench model, repr,
  store, document, package, and preference path.
- Importing material never starts a Provider call; generation still requires an
  explicit user click.
- A new generation invalidates older candidates. Request identity prevents a
  stale completion from replacing current state.
- Review edits and decisions invalidate duplicate and write readiness.
- Duplicate readiness is tied to candidate, target, and mapping revisions.
- Final confirmation and the existing write-safety snapshot remain hard gates.
- Collection reads and writes are not moved into an ordinary background thread.
  Any future async collection work must use Anki-supported operation APIs and
  receive separate acceptance testing.
- Existing notes, decks, note types, and fields are not modified.

## Current scope

This phase makes orchestration and invalidation easier to test. It is not yet
the warm-orange visual pass, and it is not a new semantic deduplication engine.
The existing deterministic local quality, source-location, and duplicate
behavior remains active. Quality refinement and the warm charcoal / soft orange
theme are subsequent phases on the same candidate branch.

PDF remains fallback-only unless the user separately installs and explicitly
enables a local backend. OCR, cloud storage, telemetry, automatic retries,
automatic Provider calls, automatic Anki writes, and public Cloze selection are
outside this phase.
