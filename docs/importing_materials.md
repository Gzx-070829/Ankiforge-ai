# Importing Materials / 导入学习材料

导入只把用户主动选择的内容放入当前学习材料区域，不会自动生成、调用 Provider 或写入 Anki。

| 类型 | 行为 | 边界 |
| --- | --- | --- |
| 粘贴文本 | 保留用户输入 | 不监听剪贴板 |
| `.md` / `.markdown` | 保留 Markdown 结构 | 单文件、无 vault 扫描 |
| `.txt` | 保留换行 | 按安全编码读取 |
| `.docx` | 提取段落和简单表格文本 | 图片、公式、批注、修订和复杂样式不保留 |
| `.pdf` | 显示 fallback 指引 | 不解析、不 OCR、不联网上传 |

## Markdown and Obsidian

Markdown frontmatter 中的 `title` 可以作为安全显示标签，生成正文可忽略 frontmatter。其他字段不执行，也不能触发文件读取。Obsidian 单文件 Markdown 与普通 `.md` 一样处理；插件不读取链接目标、附件、相邻文件或 vault 配置。

## Import result

成功提示应包含安全文件名、类型、字符数和必要 warning，不显示完整本地路径。多文件拖入时只处理明确支持的第一项并提示。已有材料不得被静默覆盖；追加行为必须可见。

DOCX 只能做基础文本提取。如果内容可能不完整，应提示用户核对。PDF 提示为：请复制可选文本，或转换为 Markdown / TXT / DOCX。

## Clipboard boundary

剪贴板增强只能由用户主动点击触发，不自动监听或后台收集。本候选版本不扫描剪贴板历史。

## Error reporting

导入失败只显示短消息和下一步，不显示 traceback、完整路径或原始压缩包内容。不要在公开 issue 上传私人材料；优先使用最小合成文件复现。

## English summary

Paste, Markdown, TXT, and basic DOCX extraction are local and user-initiated. PDF is fallback-only with no OCR or network parsing. A single Obsidian Markdown file is treated as ordinary Markdown; the vault is never scanned. Import does not automatically call AI or write to Anki, and user-facing summaries avoid full local paths.
