# v0.10 PR8 真实写入最小闭环契约

## 唯一写入入口

新手模式默认仍从只读流程开始。打开窗口、生成 AI 草稿、人工审核、读取 Anki 结构、重复检查和生成最终确认预览都不会自动写入。

真实写入只允许从最终确认区域的“确认写入选中的卡片”按钮触发。点击后必须出现二次确认，明确展示写入数量、目标牌组、笔记类型、字段映射，并说明会真正修改 Anki collection。取消二次确认时 writer 调用次数必须为零。

## 不可变命令快照

写入命令只包含：

- 当前 session 的真实 AI 候选卡草稿；
- 人工审核为“看起来可以”的卡；
- 已完成只读重复检查且未发现明显重复的卡；
- 当前已选择的现有 deck、note type 和 front/back/source 字段映射。

“需要修改”“暂时不要”“可能重复”的卡默认跳过。命令不包含 API key、Provider 设置或 config 数据。snapshot id 由当前内容、审核修订和目标映射确定；已经至少成功创建一张 note 的 snapshot 会被 session 记住，不能再次写入。

## Writer 边界

`MinimalAnkiWriter` 只允许：

1. 读取并验证指定 deck 已存在；
2. 读取并验证指定 note type 与字段已存在；
3. 为命令中的每张卡创建新 note；
4. 调用 collection 的 `add_note` 将新 note 放入已存在的 deck；
5. 返回逐卡 created/failed 状态和 created note ids。

Writer 不创建或修改 deck，不创建或修改 note type/field/template，不修改或删除已有 note/card，不覆盖已有内容。某张卡失败时继续处理其余卡，并明确报告成功、跳过和失败数量；不会把部分成功误报为全部成功。

## 生命周期与清除

材料、AI 输出、审核、deck、note type、field mapping 或 duplicate preview 变化时，旧 final confirmation preview 和旧 write result 会被清除。已经成功写过的 snapshot id 防重记录保留到当前窗口关闭。

关闭窗口后不会保存材料、AI 输出、审核、API key 或 write result；已由用户明确确认并写入 Anki 的 note 自然保留。config.json 不参与此流程。

## 完成文案

- 没有真实成功写入前：`演练完成，尚未写入 Anki`
- 至少成功创建一张 note 后：`写入完成，请在 Anki 中检查新卡片`

自动测试只使用 fake writer/fake collection，不访问真实 Anki 用户数据。
