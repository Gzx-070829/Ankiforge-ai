# v0.10 PR5：真实 Anki 目标与字段映射只读预览契约

## 授权范围

新手模式 Step 5 可以在用户点击“读取 Anki 结构”或“重新读取”后，只读访问当前 Anki collection：

- 读取 deck 名称与 ID；
- 读取 note type / model 名称与 ID；
- 读取所选 note type 的字段名称。

打开窗口、进入 Step 5 或修改普通 UI 状态都不会自动读取 collection。

## 只读 adapter

`ReadOnlyAnkiTargetAdapter` 只调用：

- `collection.decks.all_names_and_ids()`；
- `collection.models.all_names_and_ids()`；
- `collection.models.get(note_type_id)`。

adapter 不导入 writer，不调用任何 collection、deck 或 note type 写方法，不创建 note，也不执行 duplicate check。读取异常只返回固定文案：

> 无法读取 Anki 牌组或笔记类型。没有写入 Anki。

## 内存状态与映射预览

读取结果、目标选择和字段映射只保存在当前 dialog / `BeginnerFlowSession` 内存中。用户可以选择：

- 候选卡正面对应的 Anki 字段；
- 候选卡背面对应的 Anki 字段；
- 候选卡来源对应的可选 Anki 字段。

`BeginnerFieldMappingPreview` 只展示未来目标牌组、笔记类型和字段对应关系。它不是正式写入对象，`read_only` 固定为 true，`will_write_to_anki` 固定为 false。页面固定说明：

> 当前只是预览，尚未写入 Anki。

候选卡、审核结果、deck、note type 或字段映射发生变化时，final confirmation preview 必须被清除。重新读取会清除旧目标与旧映射；关闭窗口会丢弃全部选择。

## 不变边界

- 不写入 Anki；
- 不创建 note；
- 不修改 deck；
- 不修改 note type；
- 不修改 collection；
- 不执行 duplicate check；
- 不调用 writer；
- 不生成正式 `WriteReadyPreviewItem`；
- 不保存材料、AI 输出、API key 或目标映射；
- 不修改 `config.json`。

终点文案保持：

> 演练完成，尚未写入 Anki

自动测试仅使用 fake collection，不访问真实 Anki collection。Anki 手动验收通过前不得 merge。
