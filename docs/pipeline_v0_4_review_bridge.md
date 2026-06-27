# AnkiForge AI v0.4 Review Bridge

## 目标与定位

v0.4 将 v0.3 的内部 pipeline foundation 以受控、可回滚的方式接近现有审核工作台。它优先建立只读预览、知识点选择、质量与审核状态表达，以及写入资格判断，不替换已有工作流，也不执行新的 Anki 写入。

v0.4 的新 pipeline 路径仍是离线 mock 路径。插件中 v0.2.2 已有的 provider、候选卡审核和人工确认写入流程继续独立存在；真实 provider 尚未接入新 pipeline。

## PR1-PR5 已完成内容

### PR1：只读 Pipeline 预览

- 将 `PipelineRunWithStatus` 转换为 UI 友好的只读 preview DTO。
- 在现有窗口增加独立的 `Mock Pipeline 只读预览` 入口。
- 展示 run status、summary、候选卡、质量状态和 HumanReview decision。
- 不修改 `self.cards`，不接入现有候选卡编辑表。

### PR2：KnowledgePoint 选择桥接

- 将 `KnowledgePoint` 转换为可选择的 preview item。
- 使用 checkbox 收集用户选择的 `point_id`。
- 继续复用 `create_human_selections()` 和现有 full mock pipeline。
- `selected_point_ids=None` 表示默认全选，`selected_point_ids=[]` 表示一个都不选。

### PR3：CardCandidate 预览 adapter

- 将 `CardCandidate + QualityGateResult + HumanReview` 映射为只读 preview DTO。
- 严格校验三者的 `candidate_id`。
- 隔离 tags 和 quality issues 等可变字段。
- adapter 不依赖 Qt、Anki 或网络。

### PR4：Quality / Review 状态预览

- 统一推导 `unchecked / passed / warning / failed` 质量状态。
- 展示 `unreviewed / pending / approved / rejected / needs_edit` 审核状态。
- 展示只读 `Write eligible` 状态。
- `Write eligible` 是描述性状态，不是写入授权，也不会触发 writer。

### PR5：受控写入资格判断层

- 新增只读 `PipelineWriteEligibility` 和 `WriteReadyPreviewItem`。
- 复用 PR4 的状态推导，不复制审核规则。
- 只有明确 `approved` 且 Quality Gate 无 error 的候选才可进入 write-ready preview。
- missing quality、missing review、pending、rejected、needs_edit 和 failed quality 均不可进入。

## 当前完整 mock pipeline

```text
Source
  -> Chunks
  -> Knowledge Points
  -> Human Selection
  -> Card Candidates
  -> Quality Gate
  -> Human Review
  -> Write Eligibility
```

这条路径止于只读写入资格判断。`WriteReadyPreviewItem` 不是 Anki Note，不是 `GeneratedCard`，也不携带写入副作用。

## 安全边界

- AI 或 mock extractor 不能绕过 Human Selection 和 HumanReview。
- full mock pipeline 创建的 HumanReview 始终默认为 `pending`，不会自动批准。
- Quality Gate 有 error 时不能进入可批准或 write-ready 状态。
- 只有 `approved + passed` 或 `approved + warning` 才能得到 write-eligible 描述。
- write eligibility 不等于写入授权；v0.4 新 pipeline 不调用 Anki writer。
- v0.4 新路径不读写 `self.cards`，不改变现有生成、编辑、勾选、删除和确认写入流程。
- v0.4 不修改 note type、provider 配置或 API key 存储。
- pipeline 与 adapter 测试不依赖 Anki、Qt 或网络。
- 真实 API key 不得提交到仓库。

## 为什么 AI 仍不能直接写入 Anki

模型输出可能包含事实错误、范围不合适的知识点或不适合长期复习的问题。质量规则只能发现基础结构问题，不能替代人的事实核验和学习目标判断。因此，新 pipeline 必须保留明确的 Human Selection、Quality Gate 和 HumanReview 边界。即使未来接入真实 AI，模型也只能产生候选数据，不能直接调用 Anki 写入。

## 为什么 PR5 只有 eligibility

现有写入层使用的是已有 `GeneratedCard` 和人工确认流程，而新 pipeline 使用 `CardCandidate` 与 `HumanReview`。直接把二者连接起来会同时涉及审核状态转换、duplicate check、UI 确认、错误恢复和 note 字段映射，范围过大且容易误用既有 `approved` 语义。

PR5 因此只回答一个问题：某个 pipeline candidate 在质量和人工审核状态上是否具备进入后续写入候选层的条件。它不生成 `GeneratedCard`，不调用 writer，也不改变任何 Anki 数据。

## v0.4 明确未做

- 将真实 OpenAI、DeepSeek 或 OpenAI-compatible provider 接入新 pipeline
- 自动批准 HumanReview 或自动写入 Anki
- 将 pipeline candidate 放入 `self.cards` 或正式候选卡编辑表
- 生成 `GeneratedCard` 或调用现有 writer
- 新 pipeline 的 duplicate check、写入确认和失败恢复
- note type 或字段结构变更
- cloze、反向卡、多选题、图片遮挡或其他卡型
- 中文、英文或用户可配置模板系统
- PDF、Word、Obsidian vault 或批量导入
- 真实语义评分、AI scorer、持久化或运行历史

## 安全回滚

### Git 状态确认

1. 运行 `git branch --show-current`，确认所在分支。
2. 运行 `git status --short`，确认没有未提交改动。
3. 运行 `git log --oneline -10`，记录最后一个已验收的 merge commit。
4. 在回滚前再次运行全量 unittest 和 compileall。

不要在共享的 `main` 上使用 `git reset --hard`。需要检查旧版本时，可以从已知稳定 commit 创建临时恢复分支；需要撤销已经合并的 PR 时，优先使用经过审核的 `git revert -m 1 <merge_commit>`，然后重新运行全部验证。

### Add-on 目录恢复

1. 关闭 Anki。
2. 在替换插件前备份整个 add-on 目录，尤其是本机 `config.json`。
3. 从已验收的 Git commit 取出 `ankiforge_ai` 目录。
4. 替换旧插件代码，但恢复并保留备份的本机 `config.json`。
5. 重启 Anki 并重新执行手动验收。

## v0.5 Readiness Checklist

在真实 AI provider 进入新 pipeline 前，至少需要确认：

- [ ] 仓库和提交历史中没有真实 API key。
- [ ] 用户明确知道资料将发送给哪个 provider 和哪个 model。
- [ ] provider、model 和必要的生成 metadata 能被记录并供人工复核。
- [ ] token 成本、timeout、网络失败和重试边界有清晰策略。
- [ ] AI 输出进入 KnowledgePoint / CardCandidate pipeline，并继续经过本地 validator。
- [ ] AI 不能直接生成 Anki Note 或调用 writer。
- [ ] Human Selection、Quality Gate 和 HumanReview 仍然不可绕过。
- [ ] HumanReview 默认仍是 `pending`，批准必须由用户明确执行。
- [ ] 未来写入桥继续保留用户确认和 duplicate check。
- [ ] 错误提示不会静默改变已有 preview 或 Anki 数据。
- [ ] mock 路径继续作为默认、安全、离线的回退实现。
