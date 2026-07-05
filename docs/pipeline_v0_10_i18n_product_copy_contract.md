# v0.10 PR11：产品文案与中英文切换契约

PR11 为 PR10 单屏制卡面板增加轻量中英文切换，并把普通用户界面的文案集中到 `product_i18n.py`。

## 语言状态

- 默认语言为中文。
- 标题区域的“中文 / EN”按钮在中文和 English 间切换。
- 语言状态只存在于当前 `MainDialog` 和 `CardMakerPanel` 实例中。
- 关闭窗口后语言状态丢弃；不写 `config.json`，不保存用户偏好。
- 标题、区域、输入提示、按钮、空状态、动态结果和二次确认均从统一文案目录读取。

## 产品文案边界

普通用户只需理解“材料 → 生成卡片 → 检查卡片 → 写入 Anki”。内部审核、准备状态和写入命令仍保留在模型层，但不会出现在默认产品表面。旧功能继续位于默认折叠的高级调试区。

## DeepSeek 预设

- 默认 Provider 为 DeepSeek。
- 默认模型为 `deepseek-v4-flash`。
- 默认 Base URL 为 `https://api.deepseek.com`。
- 失败提示建议检查模型，并可尝试 `deepseek-v4-flash` 或 `deepseek-v4-pro`。
- Base URL 和 Timeout 仍位于默认折叠的高级设置中。

## 安全不变量

- 切换语言不会触发 Provider、collection 或 writer。
- API key 不进入文案目录、配置、日志、安全摘要、错误文本或写入命令。
- 真实写入仍需用户点击写入按钮并通过二次确认。
- 取消确认不调用 writer；可能重复项默认跳过；成功快照不能重复写入。
- writer 不修改 Deck、Note type 或已有 note/card。
