# AnkiForge AI v0.10 `.ankiaddon` 手工验收

本清单用于 AnkiWeb 上传前的人工验收。本 PR 只准备安装包，不执行 AnkiWeb 上传。

## 1. 自动检查

- [ ] `python -m unittest discover -s tests` 通过
- [ ] `python -m compileall .` 通过
- [ ] `python scripts/build_ankiaddon.py` 通过
- [ ] `git diff --check` 通过
- [ ] 工作区只包含预期的打包脚本、发布文档和安装包变更

## 2. 归档内容

- [ ] `dist/ankiforge_ai.ankiaddon` 是有效的 ZIP 格式文件
- [ ] `__init__.py` 和 `manifest.json` 位于归档根目录
- [ ] Python 包路径和主题资源路径保持相对于 `ankiforge_ai/` 的结构
- [ ] 包内不含 `.git`、`tests`、`docs` 或 `__pycache__`
- [ ] 包内不含 `.pyc`、`.env`、日志或备份
- [ ] 包内不含 `config.json`、`.anki2`、`.apkg` 或其他个人 Anki 数据
- [ ] 包内不含真实 API key、token、password 或私钥
- [ ] README、LICENSE、配置示例和开发文档未打入运行包

## 3. 隔离环境安装

以下步骤应由发布者稍后在专用测试配置中执行；不要使用包含重要个人数据的 Anki 配置。

- [ ] 使用“从文件安装”安装 `.ankiaddon`
- [ ] 重启 Anki 后未出现加载错误
- [ ] “工具”菜单中出现 AnkiForge AI 入口
- [ ] 主界面可以打开和关闭
- [ ] 中英文界面可以切换
- [ ] 未输入 API key、未点击生成时，不会调用 Provider
- [ ] 未完成最终确认时，不会写入 Anki

## 4. 最小功能验收

使用假材料和专用测试牌组；Provider 测试应使用发布者明确授权的测试凭据。

- [ ] 可以粘贴 Markdown / 文本材料
- [ ] 生成结果可以在写入前审核
- [ ] 可以选择牌组、笔记类型和字段映射
- [ ] 重复检查结果可见，可能重复的卡默认跳过
- [ ] 写入前出现最终确认
- [ ] 取消确认不会写入任何卡片
- [ ] 批准后只新增确认过且未重复的卡片
- [ ] 不修改已有卡片、牌组或笔记类型

## 5. 发布门禁

- [ ] 发布说明已经复核
- [ ] 安装说明已经复核
- [ ] Git 工作区 clean
- [ ] 最终安装包的文件数量和大小已经记录
- [ ] AnkiWeb 上传需要单独、明确的发布授权
