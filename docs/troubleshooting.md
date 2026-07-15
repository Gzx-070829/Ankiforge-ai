# Troubleshooting / 常见问题与排错

## 找不到插件

这是 Anki 插件，不是共享牌组。在 Anki Desktop 中选择 **工具 → 插件 → 获取插件**，输入 `1227582295`，安装后重启。不要在 Shared Decks 搜索。

## “AI 未配置”或无法生成

打开 AI 设置，检查 Provider、Model 和 API key 是否已填写。本次设置不会跨窗口保存。OpenAI-compatible 还需确认 Base URL。插件不会为了测试配置而自动调用 Provider；只有点击生成才联网。

## Provider 调用失败

检查网络、endpoint、model 名称、配额和 Provider 状态。不要把 key、Authorization header、完整请求/响应或私人材料发到 issue。若怀疑泄露，先 rotate key。

## 文件无法导入

- Markdown/TXT：检查文件大小和编码。
- DOCX：确认文件不是损坏或加密的，并核对基础提取是否遗漏公式/图片。
- PDF：当前不解析，请复制文本或转换为 Markdown/TXT/DOCX。
- Obsidian：只选择单个 Markdown 文件；不会扫描 vault。

## 卡片不能保留或写入

检查 blocking 提示、字段映射、Cloze 兼容性、是否存在 kept cards、duplicate check 是否为 current、目标是否有效，以及最终确认是否已完成。编辑卡片后旧的查重和写入预览会失效，这是安全设计。

## 写入数量与预期不同

查看写入报告中的 written、skipped duplicate、warning/blocking 和 failed 数量。可能重复的卡默认跳过。普通 UI 不显示 raw note IDs；如发生部分失败，不要重复点击写入，先检查 Anki Browser 和最后写入摘要。

## 如何提交安全的 bug report

提供 Anki version、add-on version、operating system、material type、Provider 名称、复现步骤、预期/实际结果和脱敏截图。不要提供 API key、私人学习材料、完整本地路径、collection 文件、note IDs、cookie、token 或 provider body。

涉及凭证泄露、无确认写入、Anki 数据修改或不必要文件访问时，请按 [SECURITY.md](../SECURITY.md) 私下报告。

## English summary

Confirm installation through Get Add-ons, configure the current AI session, and remember that editing invalidates duplicate/write previews. PDF is not parsed. Public reports should include versions, OS, material type, provider name, steps, and redacted screenshots—never API keys, private material, collection data, full paths, or raw provider payloads.
