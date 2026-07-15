# Demo Script v0.13

目标时长：3–5 分钟。使用合成材料、fake deck 名和脱敏界面；录制中不得出现 API key、完整路径、私人 Anki 数据、Provider 请求或 cookie。

## 0. 开场

旁白：AnkiForge AI 是本地 Anki 插件，不是共享牌组或网页应用，也不提供现成卡组。它帮助你把自己的材料变成必须审核的候选卡。

画面：Anki Desktop → Tools / 工具 → Add-ons / 插件。展示插件代码 `1227582295`，不要重复下载安装。

## 1. 打开工作台

展示中文默认空状态：Header、AI 未配置、左侧学习材料与模式、右侧 Review/Write。指出主屏没有 Provider / Model / API key 和调试工具。

## 2. AI 设置

打开 Modal，展示 Provider/Model/API key 的布局。API key 输入保持空白或使用不可辨识遮罩。说明“只在本次会话，不保存”。取消一次，再重新打开并保存安全测试配置。

## 3. 添加材料

选择“使用示例”中的中文概念示例，或粘贴一段公开合成材料。简短展示 Markdown/TXT/DOCX 导入入口，并说明 PDF 当前只给 fallback、不做 OCR。

## 4. 模式与生成

选择 concept，展开一次更多生成设置，再收起。主动点击生成，并强调没有点击前不会调用 AI。

如果录制环境不允许真实 Provider，使用预先准备的脱敏 mock/review 状态，不伪装成在线调用结果。

## 5. Review

展示 pending 卡、Front/Back 编辑、短质量提示、保留/丢弃、复制、还原和统计。演示一张 warning 可人工保留、一张 blocking 不能保留；不显示 raw score 或 rule ID。

## 6. Duplicate 与写入摘要

选择一个明确标为 Test Deck 的已有牌组和 Basic 字段，运行重复检查。展示 planned/written、skipped duplicate、warning/blocking、Tags 和短来源标签。

## 7. 最终确认

第一次点击写入后取消，确认没有创建 notes。第二次在已授权的测试环境中完成确认，展示写入报告和“上次写入”摘要，不展示 note IDs。

## 8. 结尾

强调：AI 和本地质量提示不能保证正确，用户对最终卡片负责；建议测试牌组。给出 GitHub issue 和安全报告入口。

## English caption set

- An Anki add-on—not a shared deck or web app.
- Your material, your provider, session-only API key.
- AI generates candidates; you review every card.
- Duplicate check and final confirmation before writing.
- Start with a test deck.
