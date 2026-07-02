# v0.10 PR4：AI 生成重试与输出修复契约

## 状态模型

一次显式 AI 候选卡生成使用以下安全状态：

- `idle`：尚未请求，或材料/运行设置变化后已清除旧状态；
- `running`：用户点击后，本次请求正在进行；
- `success`：已得到只读候选卡草稿；
- `provider_error`：Provider 或 HTTP 请求失败；
- `timeout`：请求超时；
- `invalid_json`：无法提取有效 JSON，或卡片字段不完整；
- `empty_output`：Provider 没有返回内容；
- `empty_cards`：返回了空候选卡数组。

用户点击“用 AI 生成候选卡”或“重新生成”后，session 必须先进入 `running`，并清除旧 AI 草稿、旧审核和 eligibility / write plan / final confirmation 等下游预览。失败结果不得回退显示旧候选卡。

## 输出修复

解析器优先接受 JSON 数组，同时容忍：

- 顶层 object 的 `cards` 数组；
- Markdown code fence 包裹的 JSON；
- JSON 前后带少量说明文字，并从中提取第一个有效数组或 object。

修复只在本地解析当前响应，不自动再次调用 Provider。只有用户再次点击生成按钮才允许发起新请求。

## 安全错误

每种失败只显示固定普通中文文案。文案不得包含原始异常、原始响应、材料或 API key，并必须明确：

- 没有写入 Anki；
- 没有访问 Anki collection。

API key 仍只用于当前窗口中的显式请求，不写入 session、配置、日志、异常文本、安全摘要或文档示例。

## 不变边界

- 不访问 Anki collection；
- 不执行 duplicate check；
- 不调用 writer；
- 不创建 note；
- 不写入 Anki；
- 不保存材料、AI 输出、审核结果或 API key；
- 不修改 `config.json`；
- 不生成正式 `GeneratedCard` 或 `WriteReadyPreviewItem`。

终点文案保持：

> 演练完成，尚未写入 Anki

自动测试只使用 mock transport，不进行真实网络请求。Anki 手动验收通过前不得 merge。
