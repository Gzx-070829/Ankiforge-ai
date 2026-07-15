# B站 / 知乎 Demo 大纲

## 标题方向

- 把自己的笔记变成 Anki 卡片：一个本地优先的 AI 制卡工作台
- AnkiForge AI：AI 只生成候选卡，审核和写入仍由你控制

避免暗示 AI 可以替代审核、PDF 已支持正文提取、第三方数据处理受插件控制，或整个流程可以无人值守。

## 文章 / 视频结构

1. **先澄清产品身份**
   - 这是 Anki 插件，不是共享牌组。
   - 安装入口是 Anki Desktop → 工具 → 插件 → 获取插件。
   - 插件代码 `1227582295`。
   - 它不是 Web app，也不提供现成卡组。
2. **为什么不是一个生成按钮**
   - 用户自己的材料和学习目标。
   - AI 生成候选卡。
   - 本地质量提示与人工审核。
   - duplicate、write summary 和 final confirmation。
3. **现场流程**
   - AI 设置 → 示例/Markdown → concept 模式 → 生成。
   - 编辑、warning/blocking、保留/丢弃。
   - 字段映射 → 重复检查 → 测试牌组写入。
4. **输入边界**
   - 适合 Markdown / TXT / 基础 DOCX。
   - PDF 只给 fallback，不做 OCR。
   - Obsidian 只处理用户选择的单文件，不扫描 vault。
5. **安全与隐私**
   - API key session-only，不保存。
   - 未点击生成不调用 AI。
   - 未审核/查重/确认不写入。
   - 不自动修改或删除已有 Anki 数据。
6. **质量边界**
   - 规则可解释、确定性、适合 regression。
   - 不能验证全部事实，用户对最终卡片负责。
7. **开源与反馈**
   - GitHub、issue templates、quality fixture contribution。
   - 反馈必须脱敏，安全问题私下报告。

## 素材清单

- 11 张 v0.13 验收截图；
- 3–5 分钟 demo；
- 一段中文公开合成材料；
- 一张 warning 与一张 blocking 卡；
- 一个虚构 Test Deck；
- package SHA-256 和验证摘要。
