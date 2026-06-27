# AnkiForge AI v0.4 手动验收手册

## 验收范围

本手册只验收 v0.4 新增的 mock pipeline 只读 review bridge。它不验证真实 AI provider，不验证 Anki 写入，也不验证 duplicate check。

测试资料建议使用：

```text
docs/fixtures/chinese_learning_source.md
```

## 安装前准备

1. 确认当前 Git 分支和 commit 是待验收版本。
2. 运行 `git status --short`，确认工作区 clean。
3. 完全退出 Anki。
4. 找到 Anki add-on 目录：Windows 通常为 `%APPDATA%\Anki2\addons21\ankiforge_ai`。
5. 把目标目录中的本机 `config.json` 备份到插件目录之外。

本机 `config.json` 可能包含用户自己的 provider 设置或 API key。不要用仓库中的默认配置覆盖它，也不要把本机配置复制回 Git 仓库。

## 复制插件代码

1. 源目录为仓库中的 `ankiforge_ai` 文件夹。
2. 先备份当前 add-on 目录，以便验收失败时恢复。
3. 清除目标 add-on 目录中的旧插件代码，避免 Anki 继续加载旧版本。
4. 将当前分支的 `ankiforge_ai` 内容复制到目标目录。
5. 恢复之前备份的本机 `config.json`。
6. 不需要复制 `__pycache__`、`.pyc` 或测试目录。
7. 重启 Anki，然后通过 `工具 (Tools) -> AnkiForge AI` 打开插件窗口。

## PR1：只读 Pipeline 预览

1. 选择 `docs/fixtures/chinese_learning_source.md`。
2. 点击 `Mock Pipeline 只读预览`。
3. 确认弹窗显示 run status 和 summary。
4. 确认能看到中文 source、中文内容对应的候选卡，以及 quality 和 review 状态。
5. 确认所有 HumanReview 默认都是 `pending`。
6. 关闭弹窗，确认原候选卡表格没有新增、删除或改变任何内容。

## PR2：KnowledgePoint 选择

1. 点击 `Mock 知识点选择`。
2. 确认 checkbox 列表显示中文 KnowledgePoint 标题、说明和来源。
3. 取消选择部分知识点，然后点击 `继续只读预览`。
4. 确认只读 preview 只包含被选中知识点对应的候选卡。
5. 再次打开并取消全部选择，确认结果为空且没有偷偷恢复为全选。
6. 确认原候选卡表格仍未被修改。

## PR4：Quality / Review / Write eligible

1. 在只读 preview 中确认存在 `Quality`、`Issues`、`Review` 和 `Write eligible` 列。
2. 当前正常 mock candidate 的 `Quality` 应为 `passed`；如果规则产生 warning，应明确显示 `warning`，不能伪装成 `passed`。
3. `Review` 默认应为 `pending`。
4. `Write eligible` 默认应为 `no`。
5. 不应出现自动 `approved`。

## 安全确认

- 不要点击主工作台中的 `添加到 Anki`。
- v0.4 不验证真实写入，也不要求创建或修改任何 Anki note。
- 只读 preview 和 KnowledgePoint 选择不能修改 `self.cards` 或原审核工作台。
- 验收过程中不应产生网络请求。
- 关闭所有 preview 弹窗后，现有生成、编辑、勾选、删除和确认写入控件应保持原样。

## 验收失败时恢复

1. 关闭 Anki。
2. 删除或移走本次复制的 add-on 代码。
3. 恢复验收前备份的整个 add-on 目录。
4. 确认本机 `config.json` 已恢复。
5. 重启 Anki，并记录失败步骤、当前 commit 和错误信息。
