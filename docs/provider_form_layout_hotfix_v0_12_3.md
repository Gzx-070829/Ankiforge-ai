# AnkiForge AI v0.12.3 Provider Form Layout Hotfix

## Root cause

The v0.12.2 Provider card used a `QFormLayout` for three controls and inserted
the API-key hint as a separate fourth form row. In a vertically constrained
real Anki window, Qt could compress that group in a way that made the Model and
API-key rows appear to overlap. The API-key placeholder also repeated the same
session-only policy already shown by the hint.

## Layout contract

- The Provider card root uses a vertical layout with 12 px row gaps.
- Provider, Model, and API key are three explicit horizontal rows.
- Every row uses a fixed 96 px, non-wrapping label column and a stretching
  control column separated by 16 px.
- Provider, Model, and API-key inputs have a minimum height of 40 px.
- The API-key input and its one hint label share a nested vertical field with a
  4 px gap, so the hint cannot become a competing form row.
- The Generate Cards button follows the form with at least 16 px separation
  and retains its 44 px primary-action height.
- The default card has no `More Settings` disclosure. Base URL and timeout are
  preserved for `OpenAI-compatible` and appear only when that Provider is
  selected.
- The Provider data flow, API-key lifetime, generation action, and all Anki
  write behavior remain unchanged.

## Preview artifacts

- [Chinese default state](screenshots/v0_12_3_provider_form_zh_default.png)
- [Provider detail](screenshots/v0_12_3_provider_form_detail.png)
- [English default state](screenshots/v0_12_3_provider_form_en_default.png)
- [Executable static preview](ui_preview_v0_12_3.html)

These are static previews because the development environment does not include
Anki or its Qt runtime. Final acceptance must verify the installed add-on in
Anki at the user's Windows display scaling before merge or publication.
