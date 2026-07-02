# v0.10 PR6：duplicate check 只读预览契约

## 检查范围

用户完成候选卡、审核、目标 note type 与字段映射后，可以主动点击“检查是否可能重复”或“重新检查”。打开窗口、进入 Step 5 或修改普通 UI 状态都不会自动读取 notes。

本 PR 的保守检查范围是当前 collection 中所选 note type 的 notes，不保证限制到目标 deck。UI 必须明确显示：

> 当前只是只读检查；在当前 collection 可读范围内检查所选笔记类型。没有写入 Anki。

## 只读查询与匹配

`ReadOnlyDuplicateCheckAdapter` 只执行：

- `collection.db.list("select id from notes where mid = ?", note_type_id)`；
- `collection.get_note(note_id)`；
- 读取映射后的 front / back 字段文本。

匹配规则仅包含：

- 去掉首尾空白；
- 连续空白归一；
- 大小写归一；
- 规范化后的精确匹配。

不执行语义相似度。每张候选卡结果只能是“未发现明显重复”“可能重复”或“无法检查”。可能重复时可展示匹配字段、note id 和截断的字段预览。

## 失效与错误

开始新检查前必须清除旧 duplicate preview 与 final confirmation preview。候选卡、审核决定、deck、note type 或字段映射变化时，也必须清除这两类下游状态。

collection 读取失败只显示固定文案，不展示原始异常：

> 无法完成重复检查。没有写入 Anki。

## 不变边界

- 不写入 Anki；
- 不创建或修改 note；
- 不修改 card、deck、note type 或 collection；
- 不调用 writer；
- 不生成正式 `GeneratedCard` 或 `WriteReadyPreviewItem`；
- 不保存材料、AI 输出、API key 或 duplicate preview；
- 不修改 `config.json`。

终点文案保持：

> 演练完成，尚未写入 Anki

自动测试只使用 fake collection，不访问真实 Anki collection、不真实联网。Anki 手动验收通过前不得 merge。
