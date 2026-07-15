# Card Modes and Templates / 卡片模式与模板

模式表达学习目标，模板表达卡片应如何组织。默认模式是 `concept`；模板系统是纯 Python，不创建字段、笔记类型或牌组。

| Mode | Default template | 适合内容 | 重点 |
| --- | --- | --- | --- |
| `concept` | `concept` | 原理、原因、意义 | 一个概念，解释清楚 |
| `definition` | `definition` | 术语、定义、特征 | 明确术语与边界 |
| `exam` | `exam_answer` | 考点、标准答案点 | 分点但简洁 |
| `quick_review` | `quick_review` | 快速事实回顾 | 短问短答 |
| `compare_contrast` | `compare_contrast` | 两个概念的区别 | 双方都必须出现 |
| `process_steps` | `process_steps` | 流程、顺序 | 顺序与条件清楚 |
| `formula_rule` | `formula_rule` | 公式、规则 | 变量与适用条件 |
| `mistake_trap` | `mistake_trap` | 常见误区、易混点 | 指出错误与纠正 |
| `cloze_candidate` | `cloze_candidate` | 简单填空候选 | 仅在兼容时启用 |

`basic_qa` 是通用基础模板，可用于兼容或内部映射；它不会改变选定 mode 的安全要求。

## 模板包含的信息

每个模板定义稳定 ID、双语名称/说明、适用场景、Front/Back 指引、理想形态、常见坏模式、质量优先级、Cloze 能力和兼容笔记类型提示。Prompt builder 只读取这些静态定义和用户设置，不接收 API key 或本地路径。

## Cloze 边界

`cloze_candidate` 不是“自动修改为 Cloze”。只有语法有效、当前笔记类型和字段兼容，并且用户完成审核时才能进入写入准备。插件不会自动创建 Cloze 笔记类型、字段或模板；不兼容时应阻止写入并提示选择合适目标。

## 选择建议

- 不确定时用 `concept`。
- 一段材料包含很多名词时用 `definition`。
- 需要评分点时用 `exam`，只做快速回忆时用 `quick_review`。
- 对比、流程、公式和误区使用对应专用模式，避免一张卡承担多个目标。

无论模式如何，AI 都只生成候选卡。模式或模板变化会清除旧生成结果，用户仍需人工审核。

## English summary

Modes express the learning goal; templates define front/back shape and quality priorities. The registry is deterministic Python and never mutates Anki schemas. `cloze_candidate` is restricted to compatible note types and valid syntax. Changing a mode or template invalidates stale candidates, and every result still requires review.
