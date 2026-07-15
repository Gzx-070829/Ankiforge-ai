# Future Roadmap

Roadmap 表示方向，不是当前功能承诺。所有涉及文件、Anki 数据、联网或凭证的能力都必须重新做威胁建模、测试和人工验收。

## v1.0 — 稳定与反馈

- 收集真实用户反馈并修正高频 workflow 问题；
- 扩大多学科 fixtures 和 regression tests；
- 稳定 AnkiWeb/手动安装与升级路径；
- 无严重 UI bug、无写入事故；
- 完整双语用户文档和排错材料。

## v1.1 — 安全增强

- 经过真实 Anki 验收的 Cloze 安全支持；
- 更强字段映射建议与兼容性解释；
- 更清晰的 pre/post-write report；
- 由脱敏用户反馈驱动的质量规则。

Full undo deferred，除非能够证明只处理当前批次、检测用户后续编辑、执行二次确认并逐项报告失败；绝不按 tag/deck 删除历史卡。

## v1.2 — 主动输入体验

- 更完整但不执行任意字段的 Markdown frontmatter；
- 更好的 Obsidian 单文件体验，仍不扫描 vault；
- 仅用户主动点击的 clipboard enhance，不监听历史；
- 更丰富的本地示例材料。

## v2.0 — 可选本地扩展

- 可选 local OCR；
- 可选 local PDF parser；
- advanced templates；
- local model support。

这些能力需要独立依赖、资源和隐私设计，not part of v0.13。

## v3.0 — 另行设计的可能性

- possible cloud services；
- 多端同步；
- 协作；
- 商业化。

Cloud services、账号、远端存储和支付都不是当前插件的隐含路线。任何 v3.0 工作都需要明确同意、数据生命周期设计和新的安全边界。

## 当前明确 deferred

完整 Undo、OCR、PDF parser、Obsidian vault 扫描、后台 clipboard 监听、账号、云数据库、协作和商业化全部不属于本轮实现。

高级 HTML/Markdown 卡片渲染同样延期。当前 writer 将生成和编辑后的字段视为纯文本，只转义 HTML 一次并安全保留换行。未来如增加富文本模式，必须单独设计 allowlist/parser、查重语义、迁移行为并通过真实 Anki 安全验收。

高级 HTML/Markdown 卡片渲染同样延期。当前 writer 将生成和编辑后的字段视为纯文本，只转义 HTML 一次并安全保留换行。未来如增加富文本模式，必须单独设计 allowlist/parser、查重语义、迁移行为并通过真实 Anki 安全验收。
