# v1 Candidate Acceptance Checklist

本清单用于决定 product-grade candidate 是否可进入真实 Anki 人工验收；它不等于公开发布授权。

## Automated gates

- [ ] `python -m unittest discover` 全部通过，数量高于基线。
- [ ] `python -m compileall .` 通过。
- [ ] `git diff --check` 通过。
- [ ] templates、prompt profiles、quality rules、benchmark、review、mapping、write safety、errors、i18n 和 docs tests 通过。
- [ ] 两次 package build SHA-256 一致。
- [ ] package forbidden files = 0。
- [ ] source/package consistency 通过。
- [ ] tracked-file 与 package secret scan 无真实凭证。

## Product gates

- [ ] 主屏只有 Create → Review → Write 主流程；AI 配置在 Modal。
- [ ] Help、examples、templates、quality suggestions 和 errors 中英文完整。
- [ ] 质量 UI 不显示 raw score/rule ID，文档不宣称正确率保证。
- [ ] Review pending、编辑、复制、还原、批量操作和统计符合规范。
- [ ] Field mapping 不修改 note type/fields，Cloze 不兼容会阻止。
- [ ] duplicate check、write summary 和 final confirmation 均不可绕过。
- [ ] Last Write 只展示安全摘要；Full Undo deferred。

## Documentation and governance

- [ ] README 双语、Getting Started、安装、隐私、导入、模式、质量、Review、mapping、write safety 和 troubleshooting 对应当前行为。
- [ ] SECURITY、PRIVACY、CONTRIBUTING、Code of Conduct 和 issue/PR templates 完整。
- [ ] AnkiWeb、release notes、demo、截图和增长材料只作为草稿，未越权发布。
- [ ] 文档不暗示 AI 替代审核、PDF 支持正文提取、插件控制第三方数据处理或工作流可无人值守。

## Manual acceptance required

- [ ] 完成 [Manual Anki Acceptance](manual_anki_acceptance.md)。
- [ ] 使用最终 main-bound package，而不是旧分支包。
- [ ] 人工核对全部截图不含 key、路径、私人材料或 Anki 数据。
- [ ] 用户另行确认是否 merge、push main、更新 AnkiWeb、tag 或创建 Release。
