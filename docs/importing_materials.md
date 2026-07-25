# Importing Materials / 导入学习材料（v0.14.0）

导入只把用户主动选择的内容放入当前学习材料区域，不会自动生成、调用 Provider 或写入 Anki。

| 类型 | 行为 | 边界 |
| --- | --- | --- |
| 粘贴文本 | 保留用户输入 | 不监听剪贴板 |
| 原生结构格式 | TXT/Markdown、DOCX/PPTX/XLSX、CSV/TSV、HTML、JSON/JSONL/XML、IPYNB、EPUB、SRT/VTT | 最多 20 个明确选择的本地文件，无目录/vault 扫描 |
| 安全文本/代码 | YAML、RST、Org、TeX、日志、SQL、Python/JS/TS/Java/C/C++/Rust/Go/Shell/PowerShell | 不执行代码、include、宏或公式 |
| `.pdf` | fallback 或明确启用的本地 optional backend | Core 不解析、不 OCR、不联网上传 |

## Markdown and Obsidian

Markdown frontmatter 中的 `title` 可以作为安全显示标签，生成正文可忽略 frontmatter。其他字段不执行，也不能触发文件读取。Obsidian 单文件 Markdown 与普通 `.md` 一样处理；插件不读取链接目标、附件、相邻文件或 vault 配置。

## Import result

成功提示包含安全文件名、类型、字符数和必要 warning，不显示完整本地路径。多文件拖入时分别保留成功、warning 和失败结果；一个失败不清除其他已解析项目。导入失败会显示安全原因与转换/配置后端/复制文本等下一步。编辑框最多显示 50,000 字符并明确标记为本地预览；智能文档运行使用已解析的完整文档，同时继续受分块、卡片与调用上限约束。生成进度通过 Anki 主线程回调显示分析/规划、分组生成、质量检查、覆盖检查和去重阶段；离线截图仍明确标记为 Mock，不代表真实 Provider 响应。

DOCX 只能做基础文本提取。如果内容可能不完整，应提示用户核对。PDF 提示为：请复制可选文本，或转换为 Markdown / TXT / DOCX。

## Clipboard boundary

剪贴板增强只能由用户主动点击触发，不自动监听或后台收集。本候选版本不扫描剪贴板历史。

## Error reporting

导入失败只显示短消息和下一步，不显示 traceback、完整路径或原始压缩包内容。不要在公开 issue 上传私人材料；优先使用最小合成文件复现。

## English summary

All v0.14.0 imports are local and user-initiated. Native structured formats are TXT/Markdown, DOCX/PPTX/XLSX, CSV/TSV, HTML, JSON/JSONL/safe XML, IPYNB, EPUB, and SRT/VTT. Safe text/code formats are YAML, RST, Org, TeX/LaTeX, logs, SQL, Python, JavaScript/TypeScript, Java, C/C++, Rust, Go, Shell, and PowerShell; none executes. PDF is fallback-only in Core, with no OCR or network parsing; a separately installed explicit local backend is optional. A single Obsidian Markdown file is ordinary Markdown and its vault is never scanned. Import does not automatically call AI or write to Anki, and user-facing summaries avoid full local paths.
