# AI Settings and Privacy / AI 设置与隐私

AI 设置位于 Header 的独立 Modal，不占用 Create → Review → Write 主流程。

## 会话设置

Modal 包含 Provider、Model 和密码模式 API key 输入。选择 OpenAI-compatible 时才显示 Base URL 和 Timeout。点击“保存本次设置”只更新当前窗口内存；关闭窗口或重启 Anki 后不保留。

API key 不应写入 config、日志、文档、tests snapshot、Anki 字段或 `.ankiaddon`。主屏只显示“AI 未配置”或类似“DeepSeek · 已配置”的状态，不显示 key。

## 何时会联网

安装、打开插件、导入文件、加载示例、编辑卡片、本地 quality 检查和 benchmark 都不会调用 Provider。只有用户主动点击 Generate 后，当前材料、模板指引和生成设置才会发送到配置的 endpoint。

AnkiForge AI 不自动监听剪贴板，不扫描目录或 Obsidian vault，也不引入后台 Provider 调用。

## Provider privacy

Provider 可能根据自己的条款处理或保留材料、请求元数据和输出。发送敏感学习材料前，请阅读所选 Provider 的隐私政策，并使用你信任的 endpoint。AnkiForge AI 的本地控制无法替第三方 Provider、操作系统或其他插件承诺其数据处理方式。

## 安全使用建议

- 不要把 API key 粘贴到 issue、截图、日志或卡片字段。
- 不要使用从陌生人处获得的 Base URL。
- 发现泄露后立即 rotate/revoke key。
- Provider 失败时只分享脱敏错误类型，不分享完整请求/响应。
- 关闭窗口后重新打开，确认 AI 状态恢复为未配置。

## English summary

Provider, model, and API key live in a session dialog. Saving updates memory only; the key is session-only and is not intentionally written to config, logs, docs, snapshots, Anki, or the package. Network activity begins only after the user clicks Generate. Material is then subject to the configured provider's privacy terms. Never share credentials or complete provider payloads in public reports.
