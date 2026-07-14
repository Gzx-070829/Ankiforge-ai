# AnkiForge AI v0.12.5 Linear Flow + AI Settings Modal

## 1. Problem diagnosis

The current v0.12 main screen gives low-frequency AI configuration the same visual weight as the core card-making workflow. Users must scan between material input, provider fields, generated cards, and Anki write controls. Nested bordered cards reinforce the feeling of a configuration dashboard rather than a focused productivity tool.

PR23 must solve the structural problem rather than decorate the existing layout:

- Remove Provider, Model, API key, and the API key hint from the main screen.
- Make the main screen read as one linear flow: material → generation preferences → generate → review → write.
- Preserve every provider, card-quality, duplicate-check, write-confirmation, tag, source, and undo behavior.
- Keep the API key in memory for the current session only.

## 2. Selected approach

Use a modal `QDialog` for AI settings. A right drawer is rejected because it adds animation, resizing, focus, and overlay risks in Anki's PyQt environment. A header popover is rejected because it is too constrained for a credential form and future provider-specific validation.

The dialog is approximately 480 px wide and contains Provider, Model, and API key fields. OpenAI-compatible providers additionally reveal Base URL and Timeout controls so the existing provider capability is preserved without burdening the default form. Saving copies the values into the existing in-memory panel/session state and closes the dialog. It does not write configuration, logs, snapshots, or documentation.

The preferred presentation is a frameless dialog with a custom title bar, close button, Escape handling, Cancel action, Save action, and title-bar dragging. If the real Qt runtime proves frameless rendering unreliable, the implementation may retain the native title bar while preserving the form, hierarchy, spacing, and safety contract.

## 3. Information architecture

### Header

- Left: product name and short subtitle.
- Right: low-emphasis AI status chip, `AI 设置` / `AI Settings`, and language switch.
- Status states: not configured; configured with provider name where space allows.

### Create panel — left, 45%

1. Large study-material textarea.
2. File and example actions plus character count.
3. Always-visible card mode.
4. Collapsed-by-default generation options.
5. Full-width Generate button at the visual bottom.

This is one continuous panel. Material and generation preferences are separated by spacing and a subtle divider or background shift, not nested heavy cards.

### Review & Write panel — right, 55%

1. Generated-card list or lightweight empty state occupies the main area.
2. Compact write controls form a bottom action surface.
3. Duplicate check, field mapping, summary, and Write button retain the existing enablement and confirmation rules.

## 4. Layout wireframe

```text
┌─────────────────────────────────────────────────────────────────────┐
│ AnkiForge AI                         [AI 未配置] [AI 设置] [English] │
│ 把学习材料变成 Anki 卡片                                      │
├──────────────────────────────┬──────────────────────────────────────┤
│ 创建卡片                     │ 生成的卡片                           │
│                              │                                      │
│ 学习材料                     │        ◇                             │
│ ┌──────────────────────────┐ │       还没有卡片                     │
│ │ 粘贴学习材料，或拖入文件 │ │ 放入材料后点击“生成卡片”。          │
│ │                          │ │                                      │
│ └──────────────────────────┘ │                                      │
│ [选择文件] [使用示例] 0 字符 │                                      │
│                              │ ┌──────────────────────────────────┐ │
│ 生成偏好                     │ │ 写入 Anki                        │ │
│ 卡片模式 [概念理解       ▾] │ │ 目标牌组 [选择牌组             ▾] │ │
│ 理解概念、原因、区别。       │ │ 笔记类型 [Basic                ▾] │ │
│ 更多选项 ▾                   │ │ [检查重复] 未检查                 │ │
│                              │ │ [写入 Anki]                       │ │
│ [        生成卡片         ] │ └──────────────────────────────────┘ │
└──────────────────────────────┴──────────────────────────────────────┘

                 ┌─────────────────────────────────┐
                 │ AI 设置                      × │
                 │ Provider [DeepSeek           ▾] │
                 │ Model    [deepseek-v4-flash    ] │
                 │ API key  [输入 API key          ] │
                 │          仅本次使用，不会保存。 │
                 │                [取消] [保存本次设置] │
                 └─────────────────────────────────┘
```

## 5. Visual tokens

### Color palette

| Token | Value | Use |
| --- | --- | --- |
| `APP_BG` | `#0D1117` | Window background |
| `SURFACE` | `#111827` | Main left/right panels |
| `SURFACE_ELEVATED` | `#161B22` | Dialog and write footer |
| `INPUT_BG` | `#0F141B` | Text inputs and selects |
| `HOVER_BG` | `#1C2430` | Secondary hover states |
| `BORDER_SUBTLE` | `#263241` | Inputs and light separation |
| `BORDER_STRONG` | `#334155` | Focus-neutral strong edges |
| `TEXT_PRIMARY` | `#F8FAFC` | Titles and important values |
| `TEXT_SECONDARY` | `#CBD5E1` | Labels and body copy |
| `TEXT_MUTED` | `#7D8EA3` | Hints and inactive status |
| `ACCENT` | `#7C5CFF` | Primary actions and focus |
| `ACCENT_HOVER` | `#8B73FF` | Primary-action hover |
| `ACCENT_SOFT` | `rgba(124, 92, 255, 0.12)` | Configured status chip |

### Spacing

- Outer margin: 24 px.
- Column gap: 24 px.
- Vertical section gap: 16 px.
- Panel padding: 18 px.
- Form row gap: 12 px.
- Small/medium/large tokens: 8 / 12 / 16 px.

### Typography

- Page title: 18 px bold.
- Section title: 16 px semibold.
- Label/button: 13 px medium/semibold.
- Body: 13 px.
- Hint: 12 px.

## 6. Component rules

### Main panels

- Only the top-level Create and Review & Write regions use full surfaces.
- Internal regions rely on spacing and subtle dividers.
- Textarea and generated-card list may retain borders because they are direct content containers.
- The write footer uses a soft elevated surface without another heavy outer card.

### Controls

- Inputs and selects: 40 px minimum height, 10 px radius, accent focus border.
- Primary buttons: 44 px on the main screen, 36–38 px in the dialog, accent fill, distinct disabled styling that remains readable.
- Secondary buttons: transparent/elevated background, subtle border, lower visual weight.
- The Generate button stays at the bottom of the Create panel; the Write button stays at the bottom of the write footer.

### AI Settings dialog

- Fixed label column of 88–96 px; control column stretches.
- Three stable rows: Provider, Model, API key.
- API key hint is nested under the input in the same field container and appears exactly once.
- Custom close button, Escape, Cancel, and Save all provide obvious exit paths.
- Save is visually primary; Cancel is secondary.
- Optional drop shadow may use 24–32 px blur, 0/8 offset, and translucent black. It is omitted if it harms rendering stability.

### Empty state and cards

- Empty state uses a text glyph such as `◇`, a short title, and one short action sentence.
- Generated cards prioritize front, back, review state, and short quality chips.
- Internal quality scores, warning IDs, blocking IDs, raw field names, and debug data never appear.

## 7. Copy rules

Main-screen copy is short and task-oriented. The main screen must not contain plugin explanations, provider safety essays, PDF fallback instructions, review-policy essays, debug labels, or internal quality terminology.

Required Chinese copy includes:

- `粘贴材料，或导入 Markdown / TXT / DOCX。`
- `粘贴学习材料，或拖入文件`
- `更多选项` / `收起选项`
- `请先添加材料并配置 AI。`
- `还没有卡片`
- `放入材料后点击“生成卡片”。`

The API key safety message appears only in the AI Settings dialog: `仅本次使用，不会保存。` / `Used only for this session. Not saved.`

## 8. PyQt implementation strategy

### Boundaries

- Keep `CardMakerPanel` as the owner of the existing generation and write workflow.
- Add a focused `AiSettingsDialog` that only edits a temporary draft and returns accepted values.
- Keep provider controls available as in-memory widgets/state if existing generation code depends on them, but do not insert them into the main-screen layout.
- Move layout composition into small helpers where doing so reduces nesting: header, create panel, review panel, write footer, form row, primary/secondary button, and empty state.
- Centralize visual constants and QSS selectors without introducing a new UI framework.

### Settings data flow

1. Header button opens the dialog with the current in-memory provider, model, and current-session API key. The key field always uses password echo mode, so the key is never rendered as plain text.
2. Dialog edits a local draft; Cancel and close discard draft changes.
3. Save validates the UI-level required values and returns them to `CardMakerPanel`.
4. `CardMakerPanel` updates its current session provider/model/API-key state through the existing boundary.
5. Header status and Generate enablement refresh.
6. No persistence or logging call is introduced.

### Error handling

- Missing settings keep Generate disabled and show only a short status hint.
- Dialog validation stays adjacent to the affected field or in one compact status label.
- Provider/network errors continue through the existing generation error path.
- PDF guidance remains event-driven and only appears after an attempted PDF import.

## 9. Test strategy

Add or update UI/source-contract tests to prove:

1. The main layout does not insert Provider, Model, API key, or the key hint.
2. The header exposes the AI Settings action and configured/unconfigured status.
3. The dialog contains the three required fields and a single key hint.
4. Saving updates only current-session state and refreshes status/Generate enablement.
5. Cancel and close do not change current settings.
6. No config write, unsafe representation, or key logging path is introduced.
7. A fresh session does not retain the key; this is covered through the existing pure-Python session boundary rather than a real Anki collection.
8. Card mode remains visible; additional generation settings remain collapsed by default.
9. Debug tools and forbidden long copy are absent from the main screen.
10. Chinese and English key sets stay complete.

Full validation remains `python -m unittest discover`, `python -m compileall .`, `git diff --check`, two package builds, archive inspection, secret scanning, and screenshot review.

## 10. Acceptance criteria

- The first screen communicates a left-to-right, top-to-bottom create/review/write flow.
- Provider, Model, API key, and key hint are absent from the main screen.
- The AI Settings action is in the header and the status chip reflects current-session configuration.
- The selected Modal Dialog is polished, stable, closable, draggable when frameless, and free of overlap.
- API key remains session-only and never enters config, logs, docs, snapshots, package data, or unsafe string representations.
- Generate and Write buttons retain existing business enablement and safety gates.
- No provider, prompt, validator, duplicate, writer, tag, source, or undo logic changes.
- Required Chinese/English empty, expanded-settings, dialog, and configured-status screenshots demonstrate the final hierarchy.
- PR23 remains isolated on `v0.12.5-pr23-linear-flow-settings-modal` until manual screenshot and Anki acceptance.
