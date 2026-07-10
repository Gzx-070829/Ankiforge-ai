# AnkiForge AI

把学习材料变成可复习的 Anki 卡片。

[English](README.en.md)

AnkiForge AI 是一个 Anki 插件，可以把 Markdown / 文本学习材料交给 AI，生成可审核、可写入 Anki 的卡片。

## 安装

### 方式一：通过 AnkiWeb 安装

插件代码：

```text
1227582295
```

在 Anki 中打开：

**工具 → 插件 → 获取插件**

输入插件代码 `1227582295`，安装完成后重启 Anki，再打开 AnkiForge AI。

AnkiWeb 页面：[https://ankiweb.net/shared/info/1227582295](https://ankiweb.net/shared/info/1227582295)

> AnkiWeb 当前提供的是 v0.10 public preview。v0.11 文件导入功能尚未上传 AnkiWeb。

### 方式二：从源码安装

1. 克隆仓库：

   ```bash
   git clone https://github.com/Gzx-070829/Ankiforge-ai.git
   ```

2. 将 `ankiforge_ai` 文件夹复制到 Anki 的 `addons21` 目录。
3. 重启 Anki。

## 功能

- 粘贴 Markdown / 文本学习材料
- 拖入或选择 `.md`、`.markdown`、`.txt`、`.docx` 文件
- DOCX 文本导入（图片、公式和复杂排版不会保留）
- 识别 `.pdf` 文件并安全提示；当前构建未内置 PDF 解析器
- 调用 OpenAI-compatible / DeepSeek 生成卡片
- 审核生成的卡片
- 选择牌组、笔记类型、字段映射
- 重复检查
- 写入前二次确认
- 中英文界面

## 文件导入说明

- Markdown / TXT：保留原始文本结构，单个文件最大 5 MB。
- DOCX：使用插件内置的纯 Python 文本提取，只读取段落和简单表格；不读取图片、公式、批注或复杂样式。
- PDF：当前构建为 fallback-only。可以选择或拖入 `.pdf`，但会提示先复制可选文本，或转换为 TXT / Markdown。本版本不包含 OCR，也不承诺扫描版或复杂排版解析。
- 拖入多个文件时只导入第一个并显示提示。
- 输入框已有内容时，新文件会带文件名分隔线追加到末尾，不会静默覆盖。

文件导入只更新学习材料文本框，不会自动调用 AI，也不会自动写入 Anki。详见[文件导入说明](docs/file_import.md)。

## 安全说明

- API key 只在本次窗口使用，不保存。
- 不会自动写入 Anki。
- 写入前必须确认。
- 可能重复的卡默认跳过。
- 不修改已有卡片、牌组、笔记类型。

## 开发

运行单元测试：

```bash
python -m unittest discover -s tests
```

编译检查全部 Python 源码：

```bash
python -m compileall .
```

## 当前状态

早期自用/体验版本，欢迎反馈。
