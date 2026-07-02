# v0.10 PR3：真实 AI 候选卡草稿预览契约

## 产品边界

本 PR 为新手模式增加可选的真实 AI 候选卡草稿预览。默认离线流程继续可用；打开窗口、输入材料或修改设置都不会自动联网。

唯一允许触发网络请求的动作是用户主动点击“用 AI 生成候选卡”。按钮启用前必须同时具备：

- 当前材料；
- Provider、Base URL 与模型；
- 仅用于当前窗口的 API key；
- 用户对联网发送当前材料的明确勾选。

## 会话与敏感信息

- API key 仅用于构造当前一次请求的 Authorization header。
- API key 不写入 `BeginnerFlowSession`、配置、日志、异常文本、文档示例或安全摘要。
- 材料、AI 输出和审核选择只保留在当前窗口的内存中。
- 修改材料或 Provider 运行设置会清除旧 AI 草稿、审核选择和所有下游预览。
- 关闭窗口会清除材料、AI 草稿、审核选择，并清空 API key 输入框。

## Provider 与输出

- 复用现有 OpenAI-compatible HTTP transport 与 Chat Completions URL 规则。
- Prompt 要求最多五张简洁问答卡，只使用材料内事实，并返回结构化 JSON。
- 接受 JSON 数组或包含 `cards` 数组的 JSON object。
- 输出解析为 `BeginnerAICardDraft`，再映射为 Step 4 的只读候选卡预览。
- 不生成正式 `GeneratedCard` 或 `WriteReadyPreviewItem`。
- Provider、HTTP 或解析失败只显示固定安全错误，不展示原始响应、异常或凭据。

## 明确不具备

- 不访问 Anki collection；
- 不执行 duplicate check；
- 不调用 writer；
- 不创建 note；
- 不写入 Anki；
- 不保存 API key、材料、AI 输出或审核结果；
- 不修改 `config.json`。

Step 5 仍只展示未来真正写入前需要确认的目标牌组、笔记类型、字段映射、重复检查和最终确认。终点文案保持：

> 演练完成，尚未写入 Anki

## 验收状态

自动测试使用注入的 mock transport，不进行真实网络请求。Anki 内真实 Provider 手动验收应在 PR commit 后由用户执行；通过前不得 merge。
