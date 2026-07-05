# 从 `.ankiaddon` 文件手动安装 AnkiForge AI

## 安装前

- 从可信来源获取 `ankiforge_ai.ankiaddon`。
- 关闭正在编辑的卡片窗口，并按自己的日常习惯备份 Anki 数据。
- 不要把 API key 写入安装包、配置文件、截图或日志。

## 安装步骤

1. 启动 Anki，打开插件管理界面。
2. 选择“从文件安装”或对应的本地安装入口。
3. 选择 `ankiforge_ai.ankiaddon`。
4. 安装完成后重启 Anki。
5. 在 Anki 的“工具”菜单中打开 AnkiForge AI。

安装包内的 `__init__.py` 和 `manifest.json` 位于归档根目录，Anki 会把它们安装到独立的插件目录中。

## 首次使用

1. 粘贴 Markdown 或文本学习材料。
2. 选择 Provider 并在当前窗口输入 API key。
3. 主动点击生成后审核卡片。
4. 检查牌组、笔记类型、字段映射和重复项。
5. 仅在确认预览正确后批准写入。

API key 仅在当前窗口使用，不会由 AnkiForge AI 保存。

## 更新或卸载

更新时，从插件管理界面安装新的 `.ankiaddon` 文件并重启 Anki。卸载时使用 Anki 的插件管理界面；如需保留个人设置，请先自行确认 Anki 的插件数据处理方式。

## 从源码构建安装包

在仓库根目录运行：

```bash
python scripts/build_ankiaddon.py
```

构建结果位于 `dist/ankiforge_ai.ankiaddon`。构建脚本会在生成后检查归档内容，并拒绝包含配置、缓存、测试、文档、备份或 Anki 用户数据的包。
