# AnkiForge AI v0.3 Pipeline Contract

## Status and purpose

The v0.3 pipeline is an internal foundation for a future import workflow. It
defines stable data boundaries and a fully offline mock path so later releases
can connect product UI, real AI generation, and Anki writing without collapsing
those concerns into one module.

v0.3 is not a complete end-user product experience. It does not replace the
existing review workbench, call a real AI provider, or write notes to Anki.

## Canonical flow

```text
Source
  -> Chunks
  -> Knowledge Points
  -> Human Selection
  -> Card Candidates
  -> Quality Gate
  -> Human Review
  -> Full Mock Pipeline Orchestrator
  -> Pipeline Run Summary
  -> Pipeline Run Status / Errors
```

The data flow ends at `HumanReview`. No v0.3 pipeline function converts a
review into an Anki note or writes to an Anki collection.

## Stage contracts

### 1. Source analysis

**Public entry point:** `analyze_markdown_file(file_path)`

**Input:** A UTF-8 Markdown file path.

**Output:** One `SourceDocument` and an ordered list of `SourceChunk` objects.

`SourceDocument` records the document ID, file path, file name, content hash,
and creation timestamp. `SourceChunk` records document metadata, heading path,
heading level, ordinal, text, chunk hash, and a compact source display string.
Document and chunk IDs are deterministic for their identity inputs. Markdown
headings inside fenced code blocks are not treated as section headings. A
document with no usable heading content receives an `Untitled` root chunk.

This stage parses source structure only. It does not extract knowledge, call
AI, render UI, or write to Anki.

### 2. Knowledge point parsing and extraction

**Public APIs:**

- `parse_knowledge_points_json(text, source_chunk)`
- `parse_knowledge_points_payload(payload, source_chunk)`
- `MockKnowledgePointExtractor.extract_from_chunk(chunk)`
- `extract_knowledge_points_from_chunks(chunks, extractor)`

**Input:** A `SourceChunk` and either validated JSON-shaped data or the current
mock extractor.

**Output:** Ordered `KnowledgePoint` objects inheriting document, chunk,
heading, and source metadata.

The JSON parser accepts a list or an object containing a `knowledge_points`
list. It requires non-empty `title` and `explanation` values, validates tags as
a list, and applies simple defaults for evidence, tags, and importance.

`MockKnowledgePointExtractor` is deterministic and offline. For each non-empty
chunk it creates fake JSON for one knowledge point, then deliberately reuses
the same parser and validator. It is a test implementation, not NLP, semantic
analysis, or a production AI extractor.

### 3. Human selection

**Public APIs:**

- `create_human_selection(point, decision="selected", note="")`
- `create_human_selections(points, selected_point_ids)`

**Input:** `KnowledgePoint` objects and explicit point IDs.

**Output:** Ordered `HumanSelection` records.

Supported decisions are `selected`, `rejected`, and `deferred`. The bulk helper
creates records only for matching selected IDs and rejects unknown IDs. It
preserves the original knowledge-point order. The full mock orchestrator treats
`selected_point_ids=None` as selecting all extracted points; an explicit subset
only advances those points.

This model records a selection decision. It does not provide selection UI and
does not silently classify unselected points as rejected.

### 4. Card candidate generation

**Public APIs:**

- `create_card_candidate(selection)`
- `create_card_candidates(selections)`

**Input:** `HumanSelection` records.

**Output:** Ordered `CardCandidate` objects for selected records only.

PR5 supports exactly one `basic` candidate per selected knowledge point.
Rejected or deferred records cannot be converted by the single-item helper and
are skipped by the bulk helper. A `CardCandidate` is a pipeline object, not an
Anki note and not an Anki note-type binding.

The current deterministic mock content is:

```python
front = f"What is {title}?"
back = explanation
```

`extra` contains simple evidence and source text. This English question is a
temporary mock fixture, not the final product template or prompt strategy.

### 5. Quality Gate

**Public APIs:**

- `run_quality_gate(candidate)`
- `run_quality_gate_for_candidates(candidates)`

**Input:** `CardCandidate` objects.

**Output:** One ordered `QualityGateResult` per candidate, containing
`QualityIssue` records.

The gate performs deterministic structural checks only. Current errors cover
unsupported card types and empty front/back content. Current warnings cover
identical front/back content, a front longer than 200 characters, a back shorter
than 8 characters, and a missing source. `QualityGateResult.passed` is a
read-only property derived from whether any current issue has severity `error`.
Warnings do not block passage.

This stage does not perform semantic scoring, AI evaluation, fuzzy matching,
or duplicate detection.

### 6. Human review

**Public APIs:**

- `create_human_review(candidate, quality_result, decision="pending",
  reviewer_note="")`
- `create_human_reviews(candidates, quality_results)`

**Input:** Positionally matched `CardCandidate` and `QualityGateResult` objects.

**Output:** Ordered `HumanReview` records containing candidate content and a
copied quality snapshot.

Supported decisions are `pending`, `approved`, `rejected`, and `needs_edit`.
The default is always `pending`; no orchestrator path automatically approves a
review. A candidate whose quality result contains an error cannot be created
with decision `approved`. Candidate IDs must match, and bulk inputs must have
equal lengths and matching IDs at each position.

`HumanReview` is the terminal v0.3 pipeline record. It is not an Anki note and
does not trigger an Anki write.

## Orchestration contract

### `PipelineRunResult`

`PipelineRunResult` aggregates the source document and every ordered stage
list: chunks, knowledge points, human selections, card candidates, quality
results, and human reviews. It is an in-memory return value, not persisted run
state.

### `run_full_mock_pipeline()`

This is the original strict entry point. It executes the following order:

1. `source_analysis`
2. `knowledge_extraction`
3. `human_selection`
4. `card_generation`
5. `quality_gate`
6. `human_review`

On success it returns `PipelineRunResult`. On failure it propagates the
original exception. It does not convert errors into status objects.

### `PipelineRunSummary`

`summarize_pipeline_run(result)` reads a `PipelineRunResult` without modifying
it. The returned `PipelineRunSummary` contains source identity and counts for
each stage, quality pass/fail outcomes, selection decisions, and review
decisions. Counts describe records that actually exist. For example, a point
omitted from an explicit selected-ID subset is not counted as rejected.

Summary generation does not render UI text, write logs, or persist JSON files.

### `PipelineRunStatus` and `PipelineRunWithStatus`

`run_full_mock_pipeline_with_status()` is the safe entry point. It returns a
`PipelineRunWithStatus` containing an optional result and a
`PipelineRunStatus`:

- `success`: every pipeline stage and summary generation completed.
- `failed`: source analysis failed before a usable pipeline result existed.
- `partial`: at least one earlier stage completed before a later stage failed.

Fixed failure stage names are `source_analysis`, `knowledge_extraction`,
`human_selection`, `card_generation`, `quality_gate`, `human_review`, and
`summary`. Status records contain only the failed stage, error message, error
type, and an optional summary. They do not implement logging, retry, telemetry,
or user-facing error localization.

Middle-stage failures currently return no aggregate `PipelineRunResult` because
the full aggregate is not complete. A summary-stage failure may retain the
already completed result. The safe entry point does not change review decisions
and never auto-approves cards.

## Safety boundaries

These rules are part of the v0.3 contract:

- AI output must never bypass `HumanReview` and write directly to Anki.
- A quality result containing an error cannot be approved.
- Every review produced by the mock orchestrator starts as `pending`.
- The orchestrator and all pipeline helpers must not write to Anki.
- The v0.3 pipeline does not connect to real OpenAI, DeepSeek, or compatible
  providers, even though provider support exists elsewhere in the application.
- The v0.3 pipeline does not change the existing UI or review workbench.
- The v0.3 pipeline does not change Anki note types or field definitions.
- Pure pipeline tests must not require Anki and must not access the network.
- Real API keys must never be committed. Repository defaults must remain free
  of credentials.

Any future Anki write adapter must remain downstream of an explicit approved
human review and must preserve the quality and duplicate-safety requirements of
that future release. Such an adapter is not part of v0.3.

## Current mock limitations

- `MockKnowledgePointExtractor` produces deterministic fake data and one point
  per non-empty chunk. It is not a real extraction model.
- Card generation supports only one basic card per selected knowledge point.
- `front = "What is {title}?"` is a temporary English mock template.
- The mock generator does not choose question style based on language or
  content.
- Chinese templates, English templates, user-selectable language, question
  styles, and configurable templates remain backlog items. They are not v0.3
  capabilities.

## Explicit non-goals for v0.3

The following are intentionally outside this foundation:

- UI integration or review-workbench changes
- Real AI provider calls or provider retry behavior
- Anki note creation, collection writes, or note-type changes
- Duplicate detection or duplicate-resolution policy
- Cloze, reverse, multiple-choice, image-occlusion, or other card types
- PDF, Word, Obsidian vault, or batch import
- Semantic quality scoring or AI-based quality judgment
- Template configuration, localization, or prompt editing
- Pipeline persistence, run history, telemetry, or a logging system
- API-key storage changes

## Planned direction after v0.3

The following items are roadmap directions only. They are not implemented by
v0.3 and are not promises of exact scope or release timing.

- **v0.4:** Connect the new pipeline contracts to the existing human review
  workbench while preserving explicit user control.
- **v0.5:** Route real AI generation through the pipeline boundaries and local
  validators instead of bypassing them.
- **v0.6:** Focus on user experience, safety, stability, duplicate handling,
  and secure API-key practices.
- **v0.7:** Prepare documentation, packaging, compatibility, and release quality
  for public distribution and possible AnkiWeb submission.

