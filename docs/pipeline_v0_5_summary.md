# AnkiForge AI v0.5 Integration Summary

## 1. v0.5 定位

v0.5 是新 pipeline 的 **internal AI provider integration foundation**，不是普通
用户的真实 AI 功能入口。它建立了从 `SourceChunk` 到经过本地 validator 校验的
`KnowledgePoint` 的 provider 边界，但没有把这条路径连接到插件 UI、Anki config
或 Anki writer。

插件原有的 v0.2 provider 和人工审核写入流程继续独立运行。v0.5 不改变该流程，
也不宣称新 provider path 已经可供普通用户使用。

## 2. PR1-PR10 完成内容

| PR | 完成内容 |
| --- | --- |
| PR1 | AI provider contracts、metadata、request/response envelope、structured result/error 和离线 `FakeAIProvider`。 |
| PR2 | AI JSON extraction service，强制通过 `parse_knowledge_points_json()` 进入本地 validator。 |
| PR3 | AI-backed `AIKnowledgePointExtractor` adapter。 |
| PR4 | `SafeKnowledgePointJSONProvider` safety wrapper，将 provider exception 转成 structured failure。 |
| PR5 | Transport-injected OpenAI-compatible provider skeleton。 |
| PR6 | 基于标准库的 OpenAI-compatible HTTP transport，以及完全离线的 transport tests。 |
| PR7 | Provider factory / wiring helper，显式组合 transport、provider、safety wrapper 和 extractor。 |
| PR8 | Provider safety contract、中文离线 smoke fixture 和 wiring smoke test。 |
| PR9 | 只读 `ProviderDryRunSummary` / diagnostics，固定 `will_write_to_anki=False`。 |
| PR10 | Dev-only real provider smoke harness，要求环境变量 key 和显式发送确认。 |

## 3. 当前安全链路

```text
SourceChunk
  -> KnowledgePointExtractionRequest
  -> KnowledgePointJSONProvider
  -> SafeKnowledgePointJSONProvider
  -> AIKnowledgePointExtractor
  -> KnowledgePointExtractionOutcome
  -> ProviderDryRunSummary
```

Provider 输出仍然必须通过 PR2 extraction service 和现有 KnowledgePoint validator。
Provider failure、invalid JSON、malformed response 和 provider exception 都使用结构化
结果表达；dry-run summary 不复用原始异常文本或用户资料。

## 4. 后续强制审核链路

Provider path 当前止于 KnowledgePoint extraction。任何未来的制卡和写入能力仍必须
经过：

```text
Human Selection
  -> CardCandidate
  -> Quality Gate
  -> Human Review
  -> Write Eligibility
  -> Anki
```

AI provider 不能绕过 Human Selection、Quality Gate 或 Human Review。Write
Eligibility 也只是受控写入桥的资格描述，不能取代用户确认或现有 duplicate check。

## 5. 安全红线与当前非目标

- AI provider 只能进入 KnowledgePoint extraction 阶段。
- AI 不生成最终 Anki note，也不直接写入 Anki。
- AI 不绕过 Human Selection、Quality Gate 或 Human Review。
- PR10 dev-only real provider smoke harness 不是普通用户入口。
- 真实 API 手动验证必须显式确认，并通过环境变量提供 API key。
- 自动测试不访问真实网络；仓库不提交真实 API key。
- 当前没有 UI provider selection 或真实 provider 的正式 UI 入口。
- 当前没有 API key storage、Anki config 接入或普通用户 consent flow。
- 当前没有 provider presets、retry/backoff 或 token/cost 统计。
- 当前没有从 AI provider path 写入 Anki 的路径。

即使 OpenAI-compatible HTTP transport 已存在，导入模块、运行 unittest 或打开插件
都不会自动调用真实 provider。

## 6. PR10 Dev-only 手动验证

开发者手动验证说明见 [`docs/dev_real_provider_smoke.md`](dev_real_provider_smoke.md)。

该工具是 **DEV ONLY**：它不是插件 UI 功能，真实运行会把输入文本发送给显式配置
的 provider。它不写入 Anki、不生成最终 Anki card，真实 API 的隐私、可用性和成本
风险由执行验证的开发者承担。

## 7. v0.5 Release Checklist

- [ ] `python -m unittest discover -s tests` 全部通过。
- [ ] `python -m compileall .` 通过。
- [ ] `git diff --check` 无输出。
- [ ] `git status --short` 无输出，工作区 clean。
- [ ] 仓库和文档中没有真实 API key。
- [ ] Automatic tests 使用 fake provider/transport，不访问真实网络。
- [ ] 本阶段没有 UI、config、writer、orchestrator 或 review bridge 行为变更。
- [ ] 不存在 AI provider-to-Anki write path。
- [ ] Provider safety contract：`docs/pipeline_v0_5_ai_provider_contract.md` 已存在。
- [ ] 中文 smoke fixture：`tests/fixtures/pipeline/ai_provider_smoke_source_zh.md` 已存在。
- [ ] Dry-run summary：`ankiforge_ai/pipeline/provider_dry_run_summary.py` 已存在。
- [ ] Dev-only smoke 文档：`docs/dev_real_provider_smoke.md` 已存在。

## 8. v0.6 Deferred / Next Phase

v0.6 才考虑面向普通用户的安全接入：

- provider config model 与 API key storage strategy
- provider selection UI
- privacy / consent prompt
- 明确提示“资料会发送给哪个 provider”
- safe dry-run UI 与 provider error display
- 只有用户明确确认后才发送资料
- 真实 provider 输出仍只进入 KnowledgePoint pipeline
- 仍不直接生成最终 Anki note
- 仍不绕过 Human Selection、Quality Gate 或 Human Review

这些是后续方向，不是 v0.5 已实现能力。
