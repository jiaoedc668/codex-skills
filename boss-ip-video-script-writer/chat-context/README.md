# Chat Context

这里保存给普通 ChatGPT Chat 读取的**公开安全快照**。它们不是业务项目的真相源，也不替代本地台账。

默认快照状态为 `not_synced`。只有本地 Codex 在明确检查公开安全边界后，才可以把快照更新为 `current`。

## 文件

- `persona-current.json`：当前人物的公开安全投影；未同步时回退到 `references/persona-template.json`。
- `recent-feedback.json`：近期反馈的脱敏摘要，不保存完整用户原话。
- `recent-topics.json`：近期选题的脱敏摘要，用于网页 Chat 做近似重复提醒。
- `shared-preferences.json`：跨内容抽象偏好的脱敏摘要。

## 安全原则

仓库为 Public 时，禁止把原始业务台账、完整聊天、未发布稿件、认证信息、内部路径或可识别私人信息直接复制到这里。

本地业务项目始终是 source of truth；本目录只是只读公开投影。
