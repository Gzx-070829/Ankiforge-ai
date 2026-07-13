# AnkiForge AI v0.12.2 UI Rescue Design

Figma design pass: <https://www.figma.com/design/iSJHvLwQNnDh7kJjr3Vmkx>

## Goal

Restore a compact, trustworthy desktop-tool interface without changing the
v0.12 generation, review, duplicate-check, or Anki-write workflows. Layout
must remain stable when Chinese or English copy is shown.

## Information architecture

```text
+-----------------------------------------------------------------------+
| AnkiForge AI                                      [English / 简体中文] |
| Turn study materials into Anki cards                                  |
+----------------------------------+------------------------------------+
| LEFT 48%                         | RIGHT 52%                          |
|                                  |                                    |
| 学习材料 / Study Material        | 生成的卡片 / Generated Cards       |
| [short help]                     | [empty state or card list]         |
| [material drop area]             |                                    |
| [file] [example]        [count]  | 写入 Anki / Write to Anki          |
|                                  | [stable form rows]                 |
| 生成设置 / Generation Settings   | [duplicate check + short status]   |
| [card mode form row]             | [compact summary]                  |
| [one-line mode hint]             | [full-width write action]          |
| [more options disclosure]        |                                    |
|                                  |                                    |
| AI Provider                      |                                    |
| [Provider form row]              |                                    |
| [Model form row]                 |                                    |
| [API key form row]               |                                    |
|          [session-only hint]     |                                    |
| [full-width generate action]     |                                    |
+----------------------------------+------------------------------------+
```

The main column ratio is 48:52 with a 24 px gap. Each column stacks its
sections vertically with a 16 px gap. The legacy advanced entry remains
hidden by default and is not part of the normal task flow.

## Tokens

### Spacing

| Token | Value | Use |
| --- | ---: | --- |
| `xs` | 4 px | tight icon/text separation |
| `sm` | 8 px | title-to-card and compact control gaps |
| `md` | 12 px | form-row and help-text gaps |
| `lg` | 16 px | section vertical gap |
| `xl` | 24 px | main column gap |
| `section_padding` | 18 px | section-card inset |

### Typography

| Role | Size | Weight |
| --- | ---: | --- |
| page title | 18 px | bold |
| section title | 16 px | semibold |
| form label | 13 px | medium |
| body | 13 px | regular |
| hint/status | 12 px | regular or medium |
| button | 13 px | medium; primary semibold |

### Controls

- Form label column: fixed 96 px, single line, vertically centered.
- Form control column: stretch to the available width.
- Input and select minimum height: 40 px.
- Secondary button minimum height: 36 px.
- Primary button minimum height: 44 px.
- Border radius: 8 px.
- Hints sit below their control and align with the control column. They never
  share the control row or overlap the input.
- Provider, Model, and API key are three independent form rows.

## Section behavior

### Study Material

- Chinese help: `粘贴材料，或导入 Markdown / TXT / DOCX。`
- English help: `Paste material, or import Markdown / TXT / DOCX.`
- PDF guidance appears only in import feedback, not permanently on the main
  screen.
- Placeholder: `粘贴学习材料，或拖入文件` / `Paste study material, or drop a file`.
- Keep file, example, and character-count actions on one compact row.

### Generation Settings

- Card mode is always visible in a standard form row.
- Its description is one concise line below the row.
- `More options` is a quiet disclosure row at the end of the section.
- Card count, answer length, and output language are hidden by default and use
  the same 96 px form-label contract when expanded.

### AI Provider

- Provider, Model, and API key use separate reusable form rows.
- API key hint: `仅本次使用，不会保存。` / `Used only for this session. Not saved.`
- Generate Cards is the final full-width action inside this section.
- Disabled primary actions retain contrast and must not look broken.

### Generated Cards

- Empty state contains only a title and one action-oriented sentence.
- Review guidance and quality hints appear only after candidate cards exist.
- Card content is visually primary; quality feedback is a short status chip or
  compact warning. Numeric scores, warning identifiers, and engineering fields
  are not shown.

### Write to Anki

- Deck, note type, Front, Back, and Source use the shared form-row contract.
- Duplicate check uses one secondary button plus a short status.
- Empty summary is one short sentence.
- Ready summary uses separate lines for write count, duplicate skips, quality
  reminders, and tags. It does not show internal object names or full paths.
- Write to Anki is a full-width 44 px primary action.

## Copy rules

- Main-screen copy describes the next user action, not architecture or policy.
- Security policy remains enforced in code and documented outside the main
  screen; only the API-key session hint stays visible where it is relevant.
- Chinese copy is short and natural. English copy is concise rather than a
  literal translation.
- Do not show `调试工具`, `Debug Tools`, `quality_score`, warning IDs, or internal
  pipeline names on the normal surface.

## Implementation rules

- Keep the existing two-column workflow and existing signal handlers.
- Split the previous combined AI surface into independent Generation Settings
  and AI Provider sections without changing widget state or event behavior.
- Reuse helpers for section cards, form rows, hint labels, and button roles.
- Avoid fixed section heights. Use minimum control heights, stretch, and scroll
  behavior so content cannot cover adjacent widgets or primary actions.
- All layout and copy changes require static UI-contract tests in both languages.

## Visual acceptance

- Chinese and English default-state screenshots show complete primary buttons.
- Provider, Model, and API key never overlap at the target window width.
- No form label wraps into or covers its control.
- The default card area and write summary are short and visually quiet.
- The expanded generation-options state keeps the same alignment contract.

## Preview artifacts

- Latest executable static preview: [`ui_preview_v0_12_3.html`](ui_preview_v0_12_3.html)
- Chinese default state: [`screenshots/v0_12_2_ui_rescue_zh_default.png`](screenshots/v0_12_2_ui_rescue_zh_default.png)
- English default state: [`screenshots/v0_12_2_ui_rescue_en_default.png`](screenshots/v0_12_2_ui_rescue_en_default.png)

The screenshots use the same 48:52 layout, token values, copy, and component
states as this specification. They are static UI previews, not screenshots of
a running Anki process. Final acceptance must still check both languages in a
real Anki desktop window, including Windows display scaling and the installed
Qt font metrics.
