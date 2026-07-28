# AnkiForge AI v0.14 UI Convergence Design

**Status:** Visual direction approved by the user on 2026-07-29.

## Goal

Restore the familiar, productive v0.13 workbench feel to the v0.14 main screen while retaining every v0.14 document-import and intelligence capability.

## Primary layout

The main dialog remains a two-column workbench. The left Create panel is the visual starting point and contains, in order:

1. A dominant **Study material** section with the existing editable Markdown/text area.
2. A restrained, inline file-import row below the editor. It states that users may drag or choose a TXT, MD, or DOCX file; the existing file chooser remains a secondary action. Import status, queued files, warnings, retry, and capability help remain available without turning the empty state into a file-only screen.
3. An always-visible **Card mode** selector and its short explanatory copy.
4. A collapsed **Generation settings (optional)** disclosure. Intelligence level, card count, answer length, output language, estimates, and plan details are subordinate to this disclosure by default.
5. The existing primary **Generate candidate cards** action.

The right Review and Write panel remains stable: review guidance and candidate cards occupy its main area, while deck, note type, duplicate checking, and the disabled write action stay anchored below. AI Provider, Model, and API key controls stay in the existing AI Settings dialog rather than returning to the main screen.

## Interaction and copy

Text paste is the default material path; drag-and-drop and file selection are equal supported paths but visually secondary. The initial screen must communicate the linear task flow—add own material, choose a card mode, generate, review, then manually confirm writing—without a heavy numbered-wizard treatment. Chinese copy is natural; English copy is compact and equivalent. PDF remains fallback guidance only, not OCR.

## Non-goals and safety boundaries

This pass changes layout, visibility defaults, spacing, styling hooks, and UI copy only. It must not alter document parsing, import queue behavior, generation settings values, provider requests, API-key session-only policy, quality/review workflow, duplicate detection, write confirmation, collection writes, or background-task behavior. No new network behavior, persistence, provider calls, or Anki writes are introduced.

## Expected implementation surface

- `ankiforge_ai/ui/card_maker_panel.py`: reorder or group existing widgets, default advanced settings closed, and preserve all existing signal connections.
- `ankiforge_ai/ui/product_styles.py`: small style-token/selectors adjustments for the clearer hierarchy.
- `ankiforge_ai/ui/product_i18n.py`: concise bilingual material/import/settings copy.
- Existing UI tests plus focused regression tests for the initial visibility and labels.

## Validation

Run the focused UI tests, the full unittest suite, `python -m compileall .`, `git diff --check`, and the existing `.ankiaddon` build/forbidden-file check. Perform manual Anki acceptance on the initial screen, file drag/drop, advanced-settings expansion, language switching, generation review, and write-confirmation flow.
