# AnkiForge AI v0.10 AnkiWeb 发布说明

AnkiForge AI 是一个 Anki 插件，可以把 Markdown / 文本学习材料交给 AI，生成可审核、可写入 Anki 的卡片。

## 主要功能

- 粘贴 Markdown / 文本学习材料
- 调用 OpenAI-compatible Provider 生成卡片，默认支持 DeepSeek
- 在写入前审核生成结果
- 选择牌组、笔记类型和字段映射
- 写入前执行重复检查
- 每次写入都需要用户二次确认
- 中英文界面

## 安全与隐私

- API key 只在当前窗口中使用，不保存
- 不会自动向 Anki 写入卡片
- 可能重复的卡片默认跳过
- 不修改已有卡片、牌组或笔记类型
- 只有用户主动点击生成时，当前学习材料才会发送给用户配置的 AI Provider
- 插件不主动收集遥测数据

使用前请确认所选 AI Provider 的隐私政策，不要发送不适合交给第三方处理的材料。

## 安装

下载 `ankiforge_ai.ankiaddon`，在 Anki 的插件管理界面中选择从文件安装，然后重启 Anki。

## 当前状态

这是早期自用/体验版本，欢迎通过 GitHub issue 提交经过脱敏的反馈。请勿在 issue、截图或日志中公开 API key。
