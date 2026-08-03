# v0.14.1 Manual Anki Acceptance / 真实 Anki 人工验收

## Packaged startup hotfix gate

- [ ] 在 Anki 26.05 中从最终 `.ankiaddon` 安装并重启。
- [ ] 重启后不出现“插件启动失败”窗口，也不出现 `ModuleNotFoundError: No module named 'ankiforge_ai'`。
- [ ] 从“工具”菜单打开 AnkiForge AI，再直接关闭窗口；此步骤不输入 API key、不调用 Provider、不写入 Anki。
- [ ] 确认插件管理器显示 `0.14.1`，且加载目录名称不影响启动。

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

## Workbench application-core candidate

- [ ] 打开插件后，粘贴材料、导入文件、打开 AI 设置和语言切换与 v0.14.1 行为一致。
- [ ] 生成中修改材料或开始新请求时，旧请求完成后不覆盖当前候选卡或状态提示。
- [ ] 对候选卡执行保留、丢弃、编辑、还原、复制和批量操作；每次变化都正确清除旧 duplicate/write readiness。
- [ ] 更换 deck、note type 或字段 mapping 后，旧 duplicate check 不再允许写入。
- [ ] 取消最终确认后不调用 writer；确认前再次查重，只有当前 snapshot 可写。
- [ ] 关闭窗口后材料、候选卡、审核选择、API key 和 Endpoint 确认均被丢弃；重开窗口是新会话。
- [ ] 在较大测试 collection 上观察 duplicate check 和最多 10 张写入；当前仍使用 Anki collection 允许的同步路径，不应被误改到普通后台线程。
- [ ] 使用最终 `.ankiaddon` 安装，确认任意 Anki 分配的 add-on 目录名都能导入 `workbench` 模块并正常打开主界面。

## v0.15 quality / source / preferences candidate

- [ ] 导入包含多个段落/表格/代码块的脱敏材料，确认每张卡的 source evidence 只显示文件名与真实可得的位置；无可靠页码时不编造页码，普通 UI 不显示绝对路径。
- [ ] 编辑、复制、还原候选卡后，来源提示仍对应原来源；关闭窗口后来源正文和路径不会被保留。
- [ ] 准备 `exact / canonical / similar` 候选对，确认每张候选仍可见，近重复只给出配对和原因，不自动丢弃或保留。
- [ ] 确认 `ready / review / blocked` 文案简短自然；ready 仍必须人工审核，blocked 在修正或丢弃前不能写入。
- [ ] 重开窗口后，语言、Provider/Model、卡片模式、数量、答案长度、输出语言和智能级别恢复；`user_files/preferences.json` 只包含这些非敏感字段。
- [ ] 输入 API key 和自定义 Base URL 后关闭并重开窗口，确认二者均为空；偏好文件、日志和 package 中均无 API key、Endpoint、材料、候选正文、审核状态或写入历史。
- [ ] 手工损坏或加入未知字段到 `user_files/preferences.json`，确认插件安全回退到默认值且仍可打开，不回显文件内容。
- [ ] 使用最终 `.ankiaddon` 检查 archive：运行时偏好模块存在，但 `user_files/preferences.json` 和整个 runtime `user_files` 内容均不在包内。

## v0.15 Warm Charcoal + Soft Orange visual pass

- [ ] 中文和英文空状态下，Warm Charcoal 背景、面板与输入区层级清楚；Soft Orange 只强调主操作、focus 和少量 chip，不形成整屏高亮。
- [ ] Generate / Write 主按钮在正常、hover、pressed 与 disabled 状态都能一眼区分；disabled 不像可点击，也不显得报错。
- [ ] 用键盘依次进入材料、卡片模式、生成设置、审核操作、mapping 和写入操作，确认 focus 边框完整、没有裁切或跳动。
- [ ] 检查 success / warning / error、AI 已配置、来源 chip、导入队列、空状态和滚动条；文字清晰，语义不能只依赖颜色。
- [ ] 在 100% / 125% / 150% high DPI 和较小窗口中检查主屏、AI Settings、Help 与确认框；没有重叠、截断或控件消失。
- [ ] 对比 `docs/assets/ui_preview_v0_15.html` 仅核对色彩方向；真实 Qt 渲染优先，mock 不能替代 Anki 验收。
- [ ] 抽查写入后的卡片外观，确认 generated Anki card template 未随产品 QSS 改变。

## PR28 UI convergence

- [ ] 首次打开时，“学习材料”编辑区是左侧最大的、最先可操作的控件；不会呈现成文件选择优先的空页面。
- [ ] 在材料编辑区中粘贴文本、拖入 TXT / MD / DOCX、点击“选择文件”三条路径都可用；拖入或选择文件后仍进入原有队列，不会自动调用 Provider。
- [ ] 文件导入提示在编辑区下方保持辅助层级；导入队列、状态、警告、失败重试、示例材料和“支持能力”仍可访问。
- [ ] 卡片模式在首次打开时可见，默认值为概念卡；“生成设置（可选）”默认收起，展开后仍可调整智能级别、卡片数量、答案长度和输出语言。
- [ ] 中英文切换会同步更新文件导入提示和生成设置按钮；AI Provider / Model / API key 仍只在 AI Settings Modal 中出现。
- [ ] 生成候选卡片、审核候选卡片、重复检查和最终写入确认的触发条件、状态和结果与 PR27 相同。

## 输入与示例

- [ ] 粘贴、选择和拖入 Markdown / TXT / DOCX 均可用。
- [ ] Frontmatter title 与 Obsidian 单文件不会触发 vault 扫描。
- [ ] DOCX 不完整提取有清晰提示。
- [ ] PDF 只显示 fallback，不 OCR、不联网解析。
- [ ] 每个示例能填入材料并推荐 mode，但不自动生成。

### v0.14 native-format matrix

- [ ] Structured: TXT, Markdown, DOCX, PPTX, XLSX, CSV, TSV, HTML, JSON, JSONL, safe XML, IPYNB, EPUB, SRT, and VTT all import only after explicit local selection and preserve the documented bounded structure/source hints.
- [ ] Safe text/code: YAML, RST, Org, TeX/LaTeX, logs, SQL, Python, JavaScript, TypeScript, Java, C/C++, Rust, Go, Shell, and PowerShell import as text/code without execution, include expansion, macro execution, or remote reads.
- [ ] For native Office/EPUB/XML inputs, test malformed/suspicious files and verify clear safe errors; formulas/notebook code/macros never execute, hidden XLSX sheets remain excluded by default, and one bad queue item does not remove successful ones.
- [ ] PDF is fallback-only in Core: no native parsing/OCR/upload. If a user has separately installed and explicitly enabled a local backend, test its capability indication and local conversion path independently; it is not a bundled feature.
- [ ] “支持能力 / Document capabilities” starts on native Core only. Detection alone must not enable Docling/MarkItDown/Pandoc; enable at most one backend, then select “仅使用原生 Core / Use native Core only” and confirm the optional selection is cleared.
- [ ] Choose an invalid Pandoc path and confirm the dialog reports rejection without exposing the path; choose an installed `pandoc`/`pandoc.exe` and confirm the accepted status is visible and disappears after closing the main window.
- [ ] Treat Docling and MarkItDown as optional adapter implementations until they pass a real Anki embedded-runtime launch/import test. A Python package being detected is not by itself proof that `sys.executable -I -m ...` can run in that Anki build.

## PR27 document acceptance

- [ ] 在独立 profile/test deck 中确认 v0.14.1 的原生格式、多文件队列、独立失败、可选 backend 缺失提示和 PDF fallback。
- [ ] 确认导入不会调用 Provider；手工粘贴仍是 legacy one-call 路径，导入文档才使用有界 intelligence。
- [ ] 确认实际进度依次显示规划、生成分组、质量/修复、覆盖检查、去重与终态；新 run 或关闭窗口后旧进度不得覆盖 UI。
- [ ] 确认 Fast/Standard/Deep 预算、显式确认、失败 chunk 的显式 retry、source chips、review/duplicate/final-write gates；retry 期间也应显示分组与后处理阶段，并继续受同一调用/卡片上限约束。

## Generate 与 Review

- [ ] 未点击 Generate 前无 Provider 请求。
- [ ] 覆盖各公开可选 card mode/template，确认风格有差异。
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

## PR26 metadata / lifecycle polish

1. [ ] Add-ons 列表、安装包 manifest、运行时版本、README、release draft 和 AnkiWeb draft 均显示 `0.14.1`。
2. [ ] 连续执行打开 → X/Esc/关闭 → 重开，旧材料、审核结果、API key 和 Endpoint 确认均不恢复。
3. [ ] 关闭生成中的窗口后，晚到结果不更新新窗口；重复打开关闭不会累积隐藏窗口或出现 callback 错误。
4. [ ] 重启 Anki、禁用再启用插件后，Tools 菜单中不出现重复入口。
5. [ ] legacy config 中的 API key/token/secret/bearer/password 不会进入当前 AI Settings，也不能通过 legacy save 写回磁盘。
6. [ ] 公共 UI 不显示 Cloze 模式；现有 Cloze 兼容检查保持 fail-closed，且不创建或修改 note type/field。
7. [ ] 失败、timeout 或 429 不会自动 retry；只有用户再次点击 Generate 才开始新请求。
8. [ ] Endpoint 提示按风险分类并要求本次会话确认；不要把它验收为完整 SSRF 防护。

## Collection 性能与同步锁观察

- [ ] 在包含大量已有 notes 的测试 collection 上运行 duplicate check，记录 UI 可操作性和完成耗时。
- [ ] 对本轮允许的最大 10 张 kept cards 执行最终 duplicate recheck + write，记录总耗时并确认没有重复写入或重入。
- [ ] 在 Anki 同步占用/collection lock 场景观察提示、取消和恢复行为；任何冻结、双写或不可信结果都阻止发布。
- [ ] 当前写入保持 Anki collection 约束内的同步安全路径。未来若异步化，必须单独评估 `QueryOp` / `CollectionOp`，不得把 collection mutation 放入普通后台线程。

任一自动 AI 调用、未确认写入、结构 mutation、删除、key 持久化、私人数据泄露或错误报告不可信，都应阻止 merge 和公开发布。
