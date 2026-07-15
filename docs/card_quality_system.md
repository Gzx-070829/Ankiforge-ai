# Card Quality System

AnkiForge AI evaluates candidate cards locally before they enter the write flow. The engine is deterministic Python: it does not call AI, access the network, read the Anki collection, or modify the candidate.

质量提示是辅助检查，不是事实验证器，也不能保证学习效果。用户必须阅读材料和卡片，并对最终卡片负责。

## 用户看到什么

主界面只显示短状态和可执行建议：

- **可用：** 没有发现当前规则能够识别的问题。
- **建议检查：** 可以继续审核和保留，但应检查提示。
- **不能写入：** 正面/背面为空、Cloze 不兼容等硬问题必须先修正或丢弃。

内部 `rule_id`、raw score、debug severity 和对象名不在普通 UI 中展示。内部标识用于确定性测试和 benchmark，而不是给卡片贴“正确率”标签。

## 检查范围

规则覆盖以下常见问题：

- 正面或背面为空；
- 问题过泛、不像问题，或定义卡缺少明确术语；
- 答案过长、引言冗余、项目符号过多，或与当前模式不匹配；
- 一张卡含多个问题或多个知识点；
- “根据材料可知”等套话、Prompt 残留或 Markdown 残留；
- 问题泄露答案；
- 同一批候选卡可能重复；
- 短材料生成过多卡；
- 对比卡缺少双方、流程卡缺少顺序、公式卡缺少条件、考试卡过于空泛；
- Cloze 语法无效，或当前笔记类型不支持 Cloze。

每条规则拥有稳定内部 ID、severity、blocking 标记、score delta、双语短消息和建议。评估结果使用不可变数据；safe representation 不包含学习材料或卡片正文。

## 编辑后的行为

编辑、复制或还原候选卡后会重新评估。因为卡片内容已变化，旧的 duplicate preview、写入摘要和最终确认都会失效，必须重新检查。blocking 卡不能保留或写入；warning 卡可以由用户明确保留。

## Local benchmark

本地 benchmark 对多学科合成 fixtures 和 mock cards 运行同一套引擎，汇总 pass、warning、blocking 和 score distribution。它不调用 Provider，也不宣称测量事实正确率；用途是发现 prompt、parser 或质量规则的回归。

Fixtures 不得包含真实 API key、用户 Anki 数据、私人材料或本地路径。贡献方法见 [CONTRIBUTING.md](../CONTRIBUTING.md)。

## English summary

The quality engine is local, deterministic, and assistive. Normal UI shows short actions rather than rule IDs or raw scores. Blocking findings prevent a card from being kept or written; warnings remain reviewable. Editing re-runs evaluation and invalidates stale duplicate/write previews. Quality feedback cannot guarantee correctness—the user remains responsible for every final card.
