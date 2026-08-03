# Card Quality and Source Evidence / 卡片质量与来源证据

本页描述当前开发候选中的本地审核辅助。它们帮助用户更快发现问题，
但不会替用户判断事实，也不会改变人工确认和 Anki collection 查重门禁。

## 三种质量状态

- `ready`：本地规则没有发现已知问题；仍须人工审核。
- `review`：存在可修改或可接受的提醒；不会自动丢弃卡片。
- `blocked`：正反面为空等问题使卡片暂时不可写；需要修正或丢弃。

状态来自有限、确定性的本地规则。它们不调用额外 Provider，不是准确率、
事实核验结果或学习效果评分。Human review is always required。

## 来源证据

每张导入文档生成的候选卡可以携带一个安全的 `SourceSpan`。它最多包含
本次会话的文档 ID、仅文件名的来源标签、真实可得的位置类型/值、block ID
和可信的字符范围。不能证明页码或段落时，界面会诚实退化为 chunk 或文档级
提示；不会编造更精确的位置，也不会显示完整本地路径。

Source evidence is bounded review context, not factual proof. 它的用途是帮助
用户回到材料附近复核，不表示答案已被事实验证，也不表示模型只使用了该片段。

## 候选卡近重复

本地比较会标记 `exact`、`canonical` 和 `similar` 三类候选卡关系，并给出
配对卡片及简短原因。提示是 advisory：候选卡仍全部显示，由用户编辑、保留
或丢弃。This is not semantic deduplication；相似提示只使用有界的本地文本
特征，不调用 embedding 或外部服务。

Collection duplicate check remains authoritative。在写入前，插件仍针对当前
牌组、笔记类型、字段映射和最新候选快照执行原有 collection 查重；可能重复
的卡默认跳过。本地候选提示不能替代这一门禁。

## 会保留的非敏感 preferences

为了减少重复设置，插件仅在 add-on 的
`user_files/preferences.json` 中保存以下白名单选择：

- UI language；
- Provider name；
- Model name；
- Card mode；
- Card count；
- Answer length；
- Output language；
- Intelligence level。

文件具有版本号、大小上限、严格字段校验和原子替换。无效、未知或疑似敏感
内容会被拒绝并回退到默认值。运行时 `user_files` 内容不会进入 `.ankiaddon`。

以下内容永不由这个偏好层保存：API key、token、password、Authorization /
Bearer、cookie、Base URL、study material、source path、候选卡正文、review state、
write history 或 Anki 用户数据。API key 和自定义 Endpoint 确认仍只在当前窗口
内存在，关闭窗口后清除。

## English contract in brief

- Quality is `ready / review / blocked`; human review is always required.
- Source evidence is bounded review context, not factual proof.
- Candidate near-duplicate detection is local and advisory, not semantic deduplication.
- The collection duplicate check remains authoritative before writing.
- Only the eight non-sensitive preferences listed above persist.
- API key, Base URL, study material, review state, and write history never persist.
