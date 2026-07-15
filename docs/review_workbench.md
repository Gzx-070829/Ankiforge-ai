# Review Workbench

AI 生成的是候选卡，不是已批准卡片。每张新候选卡从 `pending` 开始，必须由用户明确保留或丢弃。

## 单张卡操作

- 阅读并编辑 Front、Back 和安全来源摘要；
- 查看简短质量状态与建议，不显示 raw score 或内部 rule ID；
- **保留：** 仅允许非 blocking 卡进入写入候选；
- **丢弃：** 只改变当前窗口内存状态，不删除任何 Anki 数据；
- **复制：** 创建一个新的 pending 候选，随后重新评估；
- **还原：** 恢复 AI 最初候选内容，随后重新评估。

warning 卡可以在人工判断后保留。blocking 卡不能保留，必须编辑到解除 blocking，或直接丢弃。

## 批量操作与统计

工作台可汇总总数、待审核、已保留、已丢弃、有提醒和不能写入。批量操作保持保守：

- **丢弃不能写入：** 只丢弃当前候选中的 blocking 卡；
- **保留 clean cards：** 只保留没有 warning/blocking 的候选，不替用户批准有提醒的卡。

批量操作不会访问或删除已有 Anki notes/cards。

## 状态失效

编辑、复制或还原改变候选内容时：

1. 立即重新运行本地质量检查；
2. duplicate check 标记为 stale；
3. write preview 与 final confirmation 清除；
4. 用户必须重新检查并确认。

改变学习材料、模式、模板、生成设置或 AI 会话设置会清除不再可信的下游结果。

## 进入写入流程

没有明确保留的卡不能写入。blocking 卡不会进入写入列表。写入还需要已有 Anki 目标、完整字段映射、当前重复检查、写入摘要和用户最终确认。详情见[写入安全与追踪](write_safety_and_traceability.md)。

## English summary

Generated cards start pending. Users may edit, copy, restore, keep, or discard them. Blocking cards cannot be kept; warning cards may be kept only after explicit review. Any content change re-runs quality checks and invalidates duplicate and write previews. Bulk actions affect only in-memory candidates and never delete Anki notes or cards.
