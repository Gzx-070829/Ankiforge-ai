# Warm Charcoal and Soft Orange UI Implementation Plan

> **Execution:** Use test-driven development and verify the final visual layer
> independently from the already-passing workbench/domain changes.

**Goal:** Apply the approved warm-charcoal and soft-orange product identity to
the current Qt workbench without changing controls, layout, workflow, or the
generated Anki card template CSS.

**Architecture:** Keep one palette in `ui/style_tokens.py`; render the scoped
Qt stylesheet from those tokens; retain `PRODUCT_DARK_STYLESHEET` as a
compatibility export. Synchronize one offline HTML mock with the same palette so
visual review never requires Anki, a Provider, or a collection.

## Task 1: Lock the palette and hierarchy contract

- Update style tests first to require warm-neutral background/surfaces/text,
  low-saturation orange accent/focus, dark primary-button text, muted semantic
  states, and removal of the former violet/cold-blue palette.
- Preserve typography sizes, two-column proportions, collapsed settings, and
  all current object/role selectors.
- Assert that `product_styles.py` may depend only on `style_tokens.py` and no
  business/runtime module.

## Task 2: Implement the scoped Qt visual system

- Update `style_tokens.py` with the approved palette while retaining existing
  spacing, dimensions, and public token names.
- Render `product_styles.py` from the shared token map.
- Reduce nested decorative borders, quiet secondary actions, clarify focus,
  and keep primary actions accessible without introducing new controls.
- Keep AI Settings, Help, source chips, queue rows, quality states, and scroll
  surfaces visually consistent.

## Task 3: Synchronize an offline mock and documentation

- Add `docs/assets/ui_preview_v0_15.html` as a static, offline, non-interactive
  mock of the unchanged Create → Review → Write layout.
- Label it clearly as a mock; include no real material, credentials, Provider
  calls, or Anki data.
- Document the visual scope and manual checks for normal/high-DPI, Chinese/
  English, empty/review/write, focus, hover, disabled, and semantic states.

## Task 4: Release-candidate verification

- Run focused style/UI contracts, then the full unit suite, compileall, and
  `git diff --check`.
- Build twice and compare SHA-256.
- Audit package contents for forbidden files, credentials, config, backup,
  Anki user data, runtime `user_files`, and absolute self-imports.
- Leave the candidate branch clean. Do not merge, push, tag, upload AnkiWeb, or
  create a GitHub Release without separate authorization.
