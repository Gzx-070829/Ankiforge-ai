# v0.15 Interaction Visual QA

本轮以用户提供的 2048 × 1024 截图为问题证据，重点修正固定画布造成的底部
大面积留白、默认伪造候选卡带来的“测试用例感”，以及按钮点击后缺乏统一反馈。

## 验收步骤

1. **初始空态 — 健康**

   [截图](assets/visual_qa/01-empty-state.png)

   真实空态替代预置候选卡；创建与审核区域保持 45 / 55 主次关系，页面采用内容
   高度并在高屏幕中均衡上下空间。

2. **生成设置展开 — 健康**

   [截图](assets/visual_qa/02-generation-settings.png)

   可选项仍默认收起；展开按钮进入 checked 状态，设置区使用一层弱表面，不与
   主生成按钮竞争。

3. **AI 设置弹窗 — 健康**

   [截图](assets/visual_qa/03-ai-settings-modal.png)

   背景退后、表单聚焦，session-only 提示靠近 API key；保存是唯一主操作。

4. **帮助弹窗 — 健康**

   [截图](assets/visual_qa/04-help-modal.png)

   三步说明替代密集功能罗列，安全边界单独成块，首次使用路径清楚。

5. **生成后的审核态 — 健康**

   [截图](assets/visual_qa/05-generated-review.png)

   候选卡、质量提示、来源、审核操作和写入目标形成从上到下的阅读顺序；橙色只
   保留给主操作和少量来源标记。

6. **最终确认 — 健康**

   [截图](assets/visual_qa/06-write-confirmation.png)

   确认数量和目标先于操作，取消保持次要，确认写入保持唯一主操作；预览明确不
   访问 Anki。

## 可见性与无障碍检查

- 控件保留键盘 focus-visible；pressed、checked、disabled 不只依赖文案变化。
- success / warning / error 同时使用文字、边界和表面层级，不只依赖颜色。
- 弹窗支持 Esc 和背景点击关闭，并尊重 `prefers-reduced-motion`。
- 截图只能证明离线 HTML 预览的视觉状态；Qt 字体度量、系统主题、高 DPI、
  屏幕阅读器顺序和真实 Anki 模态行为仍须在 Anki 中人工验收。
