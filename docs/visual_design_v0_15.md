# v0.15 Visual Design: Warm Charcoal + Soft Orange

本次视觉层采用 **Warm Charcoal + Soft Orange**：暖木炭色作为主背景，
较安静的暖黑表面承载内容，低饱和橙色只用于主操作、焦点和少量状态强调。
目标是让界面柔和、清楚、像完整产品，同时避免给用户增加视觉或操作负担。

## 保持不变

- 可见流程仍是 `Create → Review → Write`；
- 两栏布局、控件数量、默认收起的生成设置和 AI Settings Modal 均不变；
- No new controls；没有新增主题选择、质量阈值或高级开关；
- Provider、API key、查重、最终确认和写入边界均不变；
- generated Anki card template CSS 不属于本轮范围，`theme/style.css` 未改；
- 不启动 Anki、不调用 Provider、不访问或写入 collection 即可查看离线 mock。

## 视觉层级

- 背景和面板使用相邻的暖中性色，依靠留白和字号而不是多层边框分组；
- 输入框保留清楚边界，focus 使用柔和橙色单线描边；
- 主按钮使用柔和橙色和深色文字，次要按钮保持低对比表面；
- hover、pressed、checked、focus 和 disabled 均有独立但克制的反馈；
- 示例菜单、生成设置 disclosure、AI Settings、Help、文档能力和最终确认
  使用一致的弹层、圆角、边界与操作层级；
- success / warning / error 使用降饱和绿、金、珊瑚色，不使用高亮霓虹色；
- 来源 chip 和 AI 已配置状态使用很浅的橙色表面，不与主操作竞争；
- 原有 12/13/16/18px 字体层级、10/12px 圆角和 spacing tokens 保持稳定。

关键文本组合的静态 WCAG 对比度核对均高于 5.5:1；真实可读性仍须在
Anki 的 Qt 渲染、高 DPI、系统字体和不同窗口大小下人工验收。

## 离线预览

[打开 v0.15 交互预览](assets/ui_preview_v0_15.html)

`ui_preview_v0_15.html` 是本地 **Interactive UI preview**，用于核对空态、
progressive disclosure、菜单、弹窗、审核与最终确认的视觉层级。示例内容只会在
用户主动点击后出现；预览不读取文件内容、不包含凭证、不发出 Provider 请求、
不访问 Anki collection，也不等同于真实 Qt 渲染。最终发布仍需要真实 Anki
截图和人工验收。
