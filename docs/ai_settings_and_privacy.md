# AI Settings and Privacy / AI 设置与隐私

AI 设置位于 Header 的独立 Modal，不占用 Create → Review → Write 主流程。

## 会话设置

Modal 包含 Provider、Model 和密码模式 API key 输入。选择 OpenAI-compatible 时才显示 Base URL 和 Timeout。点击“保存本次设置”只更新当前窗口内存；关闭窗口或重启 Anki 后不保留。

API key 不应写入 config、日志、文档、tests snapshot、Anki 字段或 `.ankiaddon`。主屏只显示“AI 未配置”或类似“DeepSeek · 已配置”的状态，不显示 key。

官方 DeepSeek/OpenAI HTTPS host 可直接使用。自定义公网 HTTPS、HTTP、本机和私网地址会要求本次会话显式确认；已知 metadata、内嵌账号密码、query/fragment 和无效地址会被拒绝。HTTP 警告会明确材料和 API key 可能明文传输；所有警告只显示 scheme、host 和 port。此分类本身不做 DNS 查询，但真正发起已确认请求时仍会使用系统 DNS/proxy/network stack；它不承诺完整 SSRF 防护，并保留用户主动使用可信本地 Provider 的能力。认证请求不会自动跟随 redirect。

## 何时会联网

安装、打开插件、导入文件、加载示例、编辑卡片、本地 quality 检查、benchmark，以及保存/确认 AI Settings 都不会调用 Provider。只有用户主动点击 Generate 后，当前材料、模板指引和生成设置才会发送到配置的 endpoint。

单次生成材料上限为 50,000 字符；UI 和生成内核都会检查，超限时不截断、不启动后台任务、不调用 Provider。AI 请求在 Anki 后台任务机制中执行，不访问 collection；关闭或修改上游内容后，晚到的旧结果会被忽略。当前没有自动 retry 或真正的网络请求 cancel。

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

Provider, model, and API key live in a session dialog. Saving updates memory only; the key is session-only and is not intentionally written to config, logs, docs, snapshots, Anki, or the package. Exact official HTTPS endpoints are allowed; custom/local/private/HTTP endpoints require per-session confirmation, while clearly invalid or known metadata endpoints are denied. This is risk classification, not complete SSRF protection. Network activity begins only after the user clicks Generate, and material over 50,000 characters is rejected before the request. Never share credentials or complete provider payloads in public reports.
