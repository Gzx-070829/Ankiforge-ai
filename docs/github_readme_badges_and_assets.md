# GitHub README Badges and Assets

本文件是发布资产规范，不表示所有 badge 或截图已经公开。

## 建议 badges

只使用能由仓库事实支持、链接到可验证目标的 badge：

- License: MIT → `LICENSE`
- Python tests → GitHub Actions workflow（只有 workflow 存在且稳定后再添加）
- Latest release → GitHub Releases（只有 v0.13 实际发布后再更新）
- AnkiWeb code `1227582295` → AnkiWeb 页面
- Languages: 简体中文 / English → 两份 README

不要添加虚假的下载量、兼容性、隐私、准确率或“100% local” badge。Provider 生成会按用户操作联网，因此不能把整个产品描述为完全离线。

## README hero

Hero 应包含：产品名、短定位、“Anki 插件，不是共享牌组”、主界面截图、AnkiWeb 安装入口和一个安全摘要。首屏避免堆满 badge。

## Asset paths

- Current product screenshots: `docs/screenshots/v0_13/`
- Demo script: `docs/demo_script_v0_13.md`
- Screenshot acceptance: `docs/screenshots_checklist_v0_13.md`
- AnkiWeb copy: `docs/ankiweb_description_v0_13.md`
- Release notes: `docs/release_notes_v0_13_product_grade.md`
- Video/article outline: `docs/bilibili_zhihu_demo_outline.md`

## Asset safety review

发布前逐项检查：

- 无真实 API key、token、cookie 或 Provider response；
- 无用户名、完整路径、Anki note IDs 或私人 collection；
- 无真实私人学习材料；
- UI 版本与 release commit 一致；
- 图中不出现调试入口、traceback、raw rule ID/score；
- alt text 描述可见内容，不做夸大声明；
- `.ankiaddon` SHA-256 来自最终双构建，不复用旧版数值。

## Release asset naming

GitHub Release 使用 `ankiforge_ai.ankiaddon`，并在 release notes 写明 commit、文件数、大小、SHA-256、测试结果、forbidden files 和人工验收状态。不要上传 config、source backup、collection 或包含 key 的诊断文件。
