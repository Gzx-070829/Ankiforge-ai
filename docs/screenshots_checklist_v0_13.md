# Screenshot Checklist v0.13

使用合成学习材料、虚构牌组/笔记类型和空白或完全遮罩的 API key。每张图检查完整路径、用户名、note IDs、collection、cookie、token、Provider payload 和通知区域。

建议统一放入 `docs/screenshots/v0_13/`，使用 1440×900 或等比例清晰尺寸。

1. [ ] `01_zh_default_empty.png` — 中文默认主界面空状态
2. [ ] `02_ai_settings_dialog.png` — AI Settings Dialog，无 key 内容
3. [ ] `03_ai_configured_main.png` — AI 已配置状态 chip
4. [ ] `04_generation_settings_expanded.png` — 生成设置展开
5. [ ] `05_help_dialog.png` — Help Dialog
6. [ ] `06_en_default_empty.png` — English default main screen
7. [ ] `07_example_loaded.png` — 使用示例后的材料与推荐 mode
8. [ ] `08_review_workbench.png` — 生成后的 Review 工作台
9. [ ] `09_warning_blocking_cards.png` — warning / blocking 的短用户提示
10. [ ] `10_write_summary_ready.png` — duplicate 完成后的写入摘要 ready 状态
11. [ ] `11_final_confirmation.png` — 执行最终确认前状态

## 每张图必须证明

- 主屏没有 Provider / Model / API key、调试工具、raw score、rule ID 或 traceback；
- Create → Review → Write 层级清楚，CTA 可见；
- 文案短、无重叠、无被截断关键文字；
- warning/blocking 不压过 Front/Back 编辑；
- Write 区清楚表达 duplicate、mapping 和 final confirmation；
- 不出现私人材料、真实 key、完整本地路径或 Anki 用户数据。

## 记录

对每张图记录 commit、Anki version、OS、语言、窗口尺寸和是否来自真实 Anki。静态 HTML preview 只能用于布局讨论，不能替代真实 Anki 验收。
