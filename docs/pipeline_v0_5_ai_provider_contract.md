# AnkiForge AI v0.5 Provider Contract

## 目标与当前定位

v0.5 建立真实 AI provider 进入新 pipeline 所需的纯 Python 边界。它让
OpenAI-compatible provider 能够把 `SourceChunk` 转换为经过本地校验的
`KnowledgePoint`，但尚未开放真实用户入口，也不会自动调用真实 provider。

插件中原有的 v0.2 provider 与审核写入流程继续独立存在。v0.5 新路径尚未连接
UI、Anki config、API key storage、orchestrator 或 Anki writer。

## PR1-PR7 已完成能力

- **PR1 - Provider contracts**：定义 metadata、request/response envelope、result、
  error、provider protocol 和离线 `FakeAIProvider`。
- **PR2 - JSON extraction service**：调用 provider，并强制复用
  `parse_knowledge_points_json()` 进行本地结构校验。
- **PR3 - Extractor adapter**：提供 `AIKnowledgePointExtractor`，支持单 chunk 和
  多 chunk extraction outcome。
- **PR4 - Safety wrapper**：将 provider 直接抛出的 `Exception` 转换为安全、结构化
  的 `provider_exception`。
- **PR5 - OpenAI-compatible provider**：构造 Chat Completions 请求并提取 assistant
  返回的 KnowledgePoint JSON 文本。
- **PR6 - HTTP transport**：使用标准库提供可注入 opener 的最小 HTTP JSON transport。
- **PR7 - Provider factory**：显式组合 transport、provider、safety wrapper 和
  extractor，不读取全局状态，也不自动执行请求。

## 当前安全链路

```text
SourceChunk
  -> KnowledgePointExtractionRequest
  -> KnowledgePointJSONProvider
  -> AIProviderResult
  -> parse_knowledge_points_json()
  -> KnowledgePoint
```

Provider 输出止于 KnowledgePoint。后续仍必须经过：

```text
Human Selection
  -> CardCandidate
  -> Quality Gate
  -> Human Review
  -> Write Eligibility
```

Write Eligibility 只是后续 review/write bridge 的受控状态，不等于写入授权。

## Provider 组件职责

| 组件 | 职责 |
| --- | --- |
| `AIProviderMetadata` | 记录 provider ID 与 model，不包含 API key。 |
| `KnowledgePointExtractionRequest` | 携带稳定 request/chunk metadata 和待处理文本。 |
| `KnowledgePointExtractionResponse` | 携带 provider 返回的 JSON 文本与 metadata。 |
| `AIProviderResult` | 表达一次 provider success 或 structured error。 |
| `AIProviderError` | 表达稳定 error code/type、消息与 retryable 状态。 |
| `FakeAIProvider` | 提供确定性、无网络的 contract 测试实现。 |
| `OpenAICompatibleKnowledgePointProvider` | 构造最小 JSON-only 请求并解析 provider response envelope。 |
| `OpenAICompatibleHTTPTransport` | 执行 HTTP POST、UTF-8 解码和 JSON body 解析。 |
| `SafeKnowledgePointJSONProvider` | 隔离 provider exception，避免异常直接穿透 service。 |
| `AIKnowledgePointExtractor` | 将 provider extraction service 暴露为 pipeline-style adapter。 |
| Provider factory helpers | 显式组装上述组件，不读取 config，也不调用 provider。 |

## 安全红线

- AI provider 只能进入 KnowledgePoint extraction 阶段。
- AI 不能直接生成最终 Anki Note，也不能直接调用 Anki writer。
- AI 不能绕过 Human Selection、Quality Gate 或 Human Review。
- Quality Gate error 不能进入 approved/write-eligible 状态。
- Human Review 仍然必须由用户明确完成；AI 不能自动批准。
- Write eligibility 继续由后续 review/write bridge 控制。
- v0.5 不修改 `self.cards`、note type 或现有审核工作台。
- 当前 PR 不打开真实 UI 入口、不读取真实 API key，也不调用真实 API。

即使代码库已经具备 OpenAI-compatible HTTP transport，它也只是可注入的底层能力。
当前版本没有把该 transport 接到用户操作、真实配置或后台任务，因此不会自动向
OpenAI、DeepSeek 或任何其他服务发送资料。

## API Key 与隐私

- 不得把真实 API key 提交到代码、fixture、测试、文档、日志或截图。
- 自动测试只允许使用明显的 fake key，例如 `test-api-key`。
- Provider config 的 repr 和公开 dict 不得暴露 API key。
- Error message 不得包含 Authorization header、API key、response body 或 source text。
- 未来发送资料前，UI 必须明确展示 provider、model、资料传输范围和隐私提示。
- v0.5 尚未实现 UI consent flow、真实 config integration 或安全 key storage。

## 错误语义

| 情况 | 当前语义 |
| --- | --- |
| Provider 返回 failure result | 保留原始 structured `AIProviderError`，不调用 parser。 |
| Provider success 但 JSON 无效 | Service 返回 `invalid_json`，不返回部分解析结果。 |
| Provider response envelope 缺失 content | 返回 `malformed_response`。 |
| Provider 直接抛出异常 | Safety wrapper 返回 `provider_exception` / `unknown`。 |
| HTTP 非 2xx | Transport 保留 status code；provider 返回 `http_error`，不暴露 body。 |
| 空或纯空白 chunk | 合法 success，KnowledgePoint 数量为 0，不编造内容。 |

PR4 safety wrapper 当前只负责 exception 边界。v0.5 不实现 retry、sleep、backoff、
thread 或 async 策略。

## 离线 Smoke 验收

`tests/test_ai_provider_smoke_pipeline.py` 使用中文 Markdown fixture 和内存 fake
opener，覆盖以下链路：

```text
Markdown analyzer
  -> PR7 provider factory
  -> PR6 HTTP transport (fake opener)
  -> PR5 OpenAI-compatible provider
  -> PR2 validator
  -> KnowledgePointExtractionOutcome
```

测试会阻断 `urllib.request.urlopen` 和 socket connection。它不访问公网或 localhost，
不导入 Anki/Qt/writer，并且止于 KnowledgePoint extraction outcome。

## Deferred / Not Yet Implemented

- UI provider selection 与用户 consent flow
- API key storage 与 Anki config integration
- OpenAI、DeepSeek 或其他 provider presets
- 真实 API verification
- retry/backoff 与 rate-limit handling
- token/cost accounting
- 新 provider 路径的 orchestration integration
- 真实 provider 输出的 Human Selection UI integration
- Anki write integration 与 duplicate check
- prompt/template 大系统、其他 card type 或新导入源

这些项目属于后续 PR。实现时仍必须保留现有 validator、Human Selection、Quality
Gate、Human Review 和用户确认边界。
