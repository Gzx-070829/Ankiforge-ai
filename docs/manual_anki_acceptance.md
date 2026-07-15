# Manual Anki Acceptance / 真实 Anki 人工验收

自动测试不能证明 PyQt 布局、Anki 版本兼容性或真实写入行为。候选包必须在独立 profile 或测试牌组中验收；不要使用私人主 collection 作为首测环境。

## 准备

- [ ] 记录 commit、package SHA-256、文件数和大小。
- [ ] 确认两次构建 SHA-256 一致且 forbidden files 为 0。
- [ ] 使用独立 Anki profile 或明确的测试牌组。
- [ ] 使用测试 Provider key；不要记录、截图或提交 key。
- [ ] 备份测试环境并记录 Anki / OS / add-on 版本。

## UI 与会话

- [ ] 中文和英文默认主屏无 Provider / Model / API key 表单、调试入口或重叠。
- [ ] AI Settings Modal 可打开、拖动、取消、Esc/关闭和保存。
- [ ] API key 为密码显示，提示只出现一次；关闭窗口后配置消失。
- [ ] Help Dialog、语言切换、高 DPI 和窗口缩放可用。
- [ ] 生成设置默认收起；卡片模式常显。

## 输入与示例

- [ ] 粘贴、选择和拖入 Markdown / TXT / DOCX 均可用。
- [ ] Frontmatter title 与 Obsidian 单文件不会触发 vault 扫描。
- [ ] DOCX 不完整提取有清晰提示。
- [ ] PDF 只显示 fallback，不 OCR、不联网解析。
- [ ] 每个示例能填入材料并推荐 mode，但不自动生成。

## Generate 与 Review

- [ ] 未点击 Generate 前无 Provider 请求。
- [ ] 覆盖各 card mode/template，确认风格有差异。
- [ ] 新卡默认 pending；warning 可人工保留，blocking 不能保留。
- [ ] 编辑、复制、还原和批量操作重新评估并清除 stale preview。
- [ ] 普通 UI 不显示 rule ID、raw score、内部对象名、路径或 traceback。

## Mapping、duplicate 与 write

- [ ] Basic 与中文字段能建议 Front/Back，Source 可选。
- [ ] mapping 不完整、Cloze 不兼容、无 kept cards 均阻止写入。
- [ ] duplicate check 是硬 gate，可能重复默认跳过。
- [ ] 写入摘要显示数量、目标、字段、Tags、来源和提醒。
- [ ] 取消最终确认后 Anki 无新增 note。
- [ ] 最终确认后只写入计划中的新 notes，existing notes/decks/note types/fields 不变。
- [ ] 写入报告准确区分 written/skipped/failed，普通 UI 无 raw note IDs。
- [ ] 上次写入摘要只指向当前批次；没有自动 Undo/delete。

## 升级与退出

- [ ] 从上一公开版安装升级后主入口可用，旧 config 不恢复 API key。
- [ ] 重启 Anki 后新增 notes 正常、key 消失、UI 状态合理。
- [ ] 卸载/禁用插件不修改已有 collection 内容。

## PR25 运行时安全 hardening

1. [ ] 点击生成后窗口仍可移动、滚动，Anki 不显示“未响应”。
2. [ ] 生成中按钮禁用，重复操作不会提交第二个相同请求。
3. [ ] 生成中关闭窗口，任务完成后不崩溃、不更新重开的界面，也不泄露凭证或错误细节。
4. [ ] 发起新生成并让旧请求稍后完成，旧结果不会覆盖新状态。
5. [ ] 生成中修改材料、生成设置或 Provider 设置，旧任务结果不会写回。
6. [ ] 超过 50,000 字符的材料被 UI 阻止，并显示正确的中英文短提示。
7. [ ] 超长材料不会启动后台任务，也不会调用 Provider。
8. [ ] Endpoint：官方地址直接保存；localhost/private/http 要求确认；HTTP 警告材料/key 可能明文传输；取消后不保存；改变 scheme/host/port 或重启窗口后重新确认；metadata、内嵌凭证、query/fragment 地址被拒绝；redirect 不会把凭证自动带到新地址。
9. [ ] 401、429 和其他 Provider error 只显示短提示，不包含 API key、Authorization、raw body 或私人材料。
10. [ ] 写入包含 `<`、`>`、`&`、换行、`<script>`、`<img onerror>` 的卡片，确认它们以无害纯文本显示且换行稳定。
11. [ ] 特殊字符写入后再次查重，等价的 escaped 字符与换行仍能识别为可能重复。
12. [ ] 同一内容经过一次写入、审核和查重流程后不发生重复转义。
13. [ ] 写入仍要求当前 duplicate check、完整 mapping、可写 kept cards 和 final confirmation。

任一自动 AI 调用、未确认写入、结构 mutation、删除、key 持久化、私人数据泄露或错误报告不可信，都应阻止 merge 和公开发布。
