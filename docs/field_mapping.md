# Field Mapping / 字段映射

字段映射决定候选卡写入已有笔记类型的哪个字段。AnkiForge AI 只读取用户选择的笔记类型字段并提供建议，不自动创建、重命名或删除字段，也不修改 note type。

## 自动建议

规范化匹配顺序包括：

- Front：`Front`、`Question`、`正面`、`问题`
- Back：`Back`、`Answer`、`背面`、`答案`
- Source（可选）：`Source`、`来源`

Front 和 Back 必须存在且不能映射到同一字段。Source 是可选项；没有 Source 字段不会阻止普通 Basic 写入。无法可靠判断时，插件应让用户选择，而不是猜测。

## Cloze compatibility

Cloze 候选必须匹配兼容的笔记类型和正文目标字段。普通 Basic note type 不能因为候选卡使用 Cloze 就被自动修改。不兼容时写入 gate 必须阻止该卡，并显示短提示。

## Mapping completeness

每次更换牌组、笔记类型、字段、候选内容或模式后都应重新检查 mapping。映射不完整时不能创建 write preview；旧 duplicate preview 和 final confirmation 也不能沿用。

## 人工验收

至少测试 Basic 的 Front/Back、中文“正面/背面/来源”、没有 Source 的笔记类型、不完整 mapping，以及 Cloze 与非 Cloze 目标。验收前后确认字段列表和 note type 结构没有变化。

## English summary

Field mapping suggests existing Front/Question/正面/问题, Back/Answer/背面/答案, and optional Source/来源 fields. Front and Back are required and distinct. The add-on never adds fields or mutates a note type. Cloze candidates remain blocked unless the selected target is compatible.
