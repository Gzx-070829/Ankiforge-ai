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

### 方式二：从源码安装

1. 克隆仓库：

   ```bash
   git clone https://github.com/Gzx-070829/Ankiforge-ai.git
   ```

2. 将 `ankiforge_ai` 文件夹复制到 Anki 的 `addons21` 目录。
3. 重启 Anki。

## 功能

- 粘贴 Markdown / 文本学习材料
- 调用 OpenAI-compatible / DeepSeek 生成卡片
- 审核生成的卡片
- 选择牌组、笔记类型、字段映射
- 重复检查
- 写入前二次确认
- 中英文界面

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
