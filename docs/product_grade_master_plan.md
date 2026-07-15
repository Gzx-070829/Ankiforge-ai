# AnkiForge AI Product-Grade Master Plan

## 1. 终局定位

AnkiForge AI 是本地优先、开源可信、中文优先的 Anki AI 制卡工作台。它接收用户主动提供的学习材料，生成候选卡，在本地执行可解释的质量检查，让用户逐张审核，再经过字段映射、重复检查和最终确认后安全写入 Anki。它不是共享牌组、网页服务、无人值守生成器或云端学习平台。

## 2. 当前能力

- Markdown / TXT / DOCX 基础文本导入、拖拽导入与 PDF fallback。
- DeepSeek 与 OpenAI-compatible Provider；API key 仅保留在当前窗口内存。
- 四种卡片模式及卡片数量、答案长度、输出语言设置。
- 确定性的本地质量规则、人工审核、重复检查、最终确认和安全写入。
- Tags、来源类型、写入摘要和当前窗口内的最后写入批次记录。
- 中英文 UI、可复现 `.ankiaddon` 打包和 forbidden-file 检查。

## 3. 当前问题

产品仍缺少统一组件与错误语言、可复用模板、跨学科质量基准、完整 Review 操作、字段智能建议、可信写入报告、首次使用帮助和成体系的开源文档。历史调试工作台仍保留持久化 Provider 设置代码，即使默认隐藏也不符合终局产品边界。

## 4. 本轮目标

v0.13 将现有安全链路升级为一个连续的 Create → Review → Write 工作台，并新增纯 Python 模板、示例、质量 v4、benchmark、字段建议、用户错误和统计模型。UI 只做这些纯内核的薄集成。最终产物是可人工安装验收的 `v0.13.0-product-grade-preview` 候选包及完整公开材料草稿。

## 5. 明确不做

不保存 API key；不自动调用 AI；不自动写入、修改或删除 Anki 数据；不创建字段或笔记类型；不实现完整 Undo；不做 OCR、联网 PDF 解析、Obsidian vault 扫描、剪贴板监听、账号、云数据库、支付或 Web app。Cloze 只保留模板与兼容性检查，不在不兼容笔记类型上写入。

## 6. 用户主流程

1. 用户粘贴、拖入或主动选择材料，也可主动选择内置示例。
2. 用户选择卡片模式；更多生成设置默认收起。
3. 用户在 Modal 中配置本次会话的 AI。
4. 只有用户点击“生成卡片”才发送当前材料。
5. 候选卡先经过本地质量评估，再进入 pending Review。
6. 用户编辑、复制、还原、保留或丢弃；编辑使重复检查和写入预览失效。
7. 用户选择 Anki 目标和字段；插件只读取必要元数据，不修改结构。
8. 用户主动检查重复并查看写入摘要。
9. 用户最终确认后才执行写入，并收到不暴露内部 ID 的报告。

## 7. UI 信息架构

Header 左侧显示产品名和短副标题；右侧依次为 AI 状态、AI 设置、帮助、语言切换。主屏左侧是学习材料、模式/模板和生成 CTA；右侧是 Review 工作台与底部写入操作台。主屏不显示 Provider/Model/API key 表单、调试入口、长篇安全说明、raw score、rule ID、内部对象名或堆栈。

## 8. AI 设置 Modal

沿用约 480px 的 frameless `AiSettingsDialog`，保留自定义关闭、Esc、取消、保存和标题栏拖动。默认只显示 Provider、Model、密码模式 API key；OpenAI-compatible 才显示 Base URL 和 Timeout。Save 返回不可变 runtime settings；没有 config、日志或持久化调用。关闭主窗口清空该状态。

## 9. 输入系统

输入保持本地、显式、单文件。Markdown/TXT 保留结构；DOCX 只提取段落和简单表格；PDF 始终给 fallback 指引。Markdown frontmatter 可识别 `title` 作为安全显示标签并从生成正文中移除，其余字段不执行。`.md` 文件天然支持 Obsidian 单文件，但绝不扫描相邻文件或 vault。导入结果只展示文件名、类型、字符数和安全警告，不显示完整路径。

## 10. 卡片模式系统

模式扩展为 `concept`、`definition`、`exam`、`quick_review`、`compare_contrast`、`process_steps`、`formula_rule`、`mistake_trap` 与受限的 `cloze_candidate`。默认仍是 `concept`。每个模式绑定默认模板与独特 prompt guidance；旧四模式语义兼容。

## 11. 模板系统

`pipeline/card_templates.py` 提供不可变、可枚举、可安全表示的模板注册表。每个模板包含双语名称/说明、适用场景、正背面指导、理想形态、常见坏模式、质量优先级、Cloze 能力和笔记类型提示。模板不创建或修改 Anki 结构。

## 12. Prompt Profile v3

Prompt profile 组合 GenerationSettings 与 CardTemplate，确保模式、模板、数量、答案长度和语言都有明确差异。全局约束是一卡一知识点、正面具体、背面直接、只使用材料事实、保守生成和结构化 JSON 输出。Prompt 构建函数不接收 API key 或本地路径，safe repr 不包含学习材料。

## 13. Card Quality v4

在现有确定性引擎上扩展规则，不引入模型调用。每条规则有稳定 ID、severity、blocking、score delta、双语短消息和建议。主屏只显示短消息与“可用/建议检查/不能写入”状态，不显示 ID 或 raw score。评估函数不修改输入卡，结果 safe repr 不包含卡片内容。

## 14. Review Workbench v4

候选卡默认 pending；blocking 不能保留，warning 可人工保留。支持编辑、复制、还原原始候选、一键丢弃 blocking、一键保留 clean cards，以及总数/待审核/已保留/已丢弃/提醒/不能写入统计。编辑、复制或还原都重新评估并使 duplicate preview 与 final confirmation 失效。没有明确保留的卡不能写入。

## 15. Field Mapping v3

纯 Python 建议器按规范化字段名优先匹配 Front/Question/正面/问题、Back/Answer/背面/答案、Source/来源。Front 与 Back 必须不同且完整；Source 可选。不确定时不猜测。Cloze 候选只有在笔记类型/字段兼容时才允许进入写入准备。建议器只处理传入的字段名，绝不调用 Anki mutation API。

## 16. Write Safety v3

写入 gate 必须同时满足：存在 kept cards、没有 blocking card 进入列表、字段映射完整、重复检查为 current、用户最终确认、目标合法且生成已结束。摘要包含计划写入、跳过重复、提醒、阻止数量、目标、Tags 和安全来源标签。失败只影响当前批次并产生用户可读报告，不展示完整路径、raw note ID 或 traceback。

## 17. Last Write / Undo 策略

最后写入批次只在内存中保存 batch ID、时间、内部 note IDs、目标、Tags、来源和计数；普通 UI 只显示“上次写入：N 张到 deck”。窗口关闭后清空。Full Undo deferred。自动 Undo/删除继续 deferred，因为当前版本不能证明用户写入后是否编辑过每条 note；绝不按 tag 或 deck 批量删除。

## 18. Error System v3

`pipeline/user_errors.py` 提供固定错误代码、severity、双语短消息和 suggested action。UI 根据语言解析，不显示异常类型、网络响应正文、路径或堆栈。内部异常只能映射到安全错误。所有 code 必须在 zh/en 目录中完整存在。

## 19. Help / Onboarding

Header 的 Help Dialog 用一屏短说明解释插件身份、用户材料、Provider、session-only key、人工审核、最终确认、测试牌组、PDF fallback 和 issue 反馈。打开外部链接只能由用户点击，且本轮不新增后台联网。示例选择器兼作首次使用入口。

## 20. Example Materials

纯 Python 示例注册表包含中文概念、英文概念、术语定义、考试复习、快速回顾、Markdown、对比、流程、公式和误区示例。每项有稳定 ID、双语标题/说明、推荐模式、3–5 卡预期范围与安全来源标签。示例不含真实人物隐私、凭证、网络依赖或本地路径。

## 21. Local Benchmark / Evaluation

`eval/card_quality_benchmark.py` 对仓库 fixtures 中的 mock cards 运行同一质量引擎，输出 pass/warning/blocking 数和分数分布。多学科 fixtures 覆盖 Python、SQL、BCI/EEGNet、英语、生物、数学、历史、政策、Markdown 和中英混合。Benchmark 完全离线、确定性、无额外依赖，用于发现 prompt/quality/parser 回归，而不是宣称事实正确率。

## 22. Fixtures

Fixture 只包含公开、合成或教学性材料及预期结构，不包含用户 Anki 数据、真实 API key、个人路径或受限材料。JSON schema 固定 source、recommended mode、good/bad patterns、card range、notes 和 sample cards；测试校验所有 fixture。

## 23. Documentation System

中文 README 作为主页，英文 README 对等。Getting Started、安装、AI/隐私、模式/模板、质量、Review、字段、写入、导入、排错和人工验收各自负责一个主题并互相链接。文档明确质量规则不是事实保证、用户对最终卡片负责，并避免“完美、全自动、绝对隐私、完整 PDF”等夸大表述。

## 24. Open Source Governance

SECURITY 覆盖凭证、Anki 数据、错误写入、Provider 隐私和文件导入；CONTRIBUTING 覆盖代码、文档、fixture、bug 与安全报告。Issue/PR 模板主动提醒删除 API key、用户材料和 collection 数据。CODE_OF_CONDUCT 使用 Contributor Covenant 风格的简洁社区规范。

## 25. Release / AnkiWeb / GitHub 策略

本轮只准备 v0.13 release notes、AnkiWeb 双语描述、截图清单和 GitHub Release 文案，不创建 tag/Release，不更新 AnkiWeb。只有 PR24 人工 diff review、真实 Anki 安装、Modal/Review/duplicate/final-confirm/write 测试通过后，才能另行授权 merge 和发布。

## 26. Growth Assets

Demo 脚本和 B站/知乎大纲展示“安装 → AI 设置 → 用户材料 → 模式 → 生成候选 → 人工审核 → 重复检查 → 测试牌组写入”，始终强调不是共享牌组、不是 Web app、没有现成卡组。公开截图使用合成材料和虚构目标，不出现 key、路径或用户数据。

## 27. Manual Acceptance Checklist

人工验收至少覆盖：中英文首次打开、缩放/高 DPI、Modal 关闭与拖动、示例选择、四种文件导入/PDF fallback、每个模式、Provider 失败、Review 编辑/复制/还原/批量操作、中文字段映射、重复硬 gate、取消最终确认、测试牌组写入、写入报告、重启后 key 消失及 package 升级安装。任何自动写入、结构变更、key 持久化或真实数据泄露都阻止发布。

## 28. Future Roadmap

- **v1.0:** 真实用户反馈、多学科回归、安装稳定、无严重 UI/写入事故、完整文档。
- **v1.1:** 严格验证后的 Cloze、增强字段映射与报告、反馈驱动质量规则。
- **v1.2:** 更完整 frontmatter、Obsidian 单文件体验、用户主动 clipboard enhance、更丰富示例。
- **v2.0:** 可选本地 OCR/PDF parser、高级模板和本地模型；全部需独立威胁建模。
- **v3.0:** 可能的云服务、同步、协作和商业化；不是当前插件的隐含承诺，必须另行设计与授权。

## 29. 实施与发布门槛

实现最多四个聚合提交。每个新增纯 Python 能力先写失败测试，再最小实现。最终必须通过完整 unittest、compileall、diff check、两次一致打包、独立 archive 审计、tracked-file/secret 扫描和静态截图审查。PR24 只可推送同名分支；不得 merge/push `main`、上传 AnkiWeb 或创建 Release。
