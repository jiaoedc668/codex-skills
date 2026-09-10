# ChatGPT Web Adapter

本文件仅处理普通 ChatGPT Chat 读取本 Skill 时的运行环境差异。所有创作、研究、人物、验收与交付规则仍以 `SKILL.md` 及其引用的 `references/` 为唯一业务规则来源。

本地 Codex 正常运行本 Skill 时忽略本文件，除非用户明确要求检查 ChatGPT Web 兼容性或同步公开 Chat 上下文。

## 启动顺序

1. 先读取当前目录的 `SKILL.md`。
2. 按用户任务读取 `SKILL.md` 指向的必要 `references/`；纯标题、发布包装和局部修改继续遵守 `references/task-routing.md` 的最小加载原则。
3. 读取 `chat-context/` 中可用的公开安全快照；快照不是业务项目真相源。
4. `AGENTS.md` 可从仓库读取；业务项目里的 `PROGRESS.md`、`BLOCKED.md` 或其他本地文件不可访问时，不得虚构其内容。

## 人物与状态 fallback

优先读取 `chat-context/persona-current.json`。只有当 `snapshot_status` 为 `current` 且 `persona` 非空时，才把它作为当前公开人物投影使用；否则回退到 `references/persona-template.json`。

以下公开快照仅在 `snapshot_status=current` 时使用：

- `chat-context/recent-feedback.json`
- `chat-context/recent-topics.json`
- `chat-context/shared-preferences.json`

快照缺失、为空、过期或 `not_synced` 时：

- 只使用当前对话中用户明确提供的信息；
- 不声称读取过本地反馈台账、选题台账、共享偏好或项目状态；
- 不声称完成历史去重、人物迁移、反馈投影或状态写入；
- 需要这些状态才能严格完成任务时，明确说明当前限制。

## Web 研究

`SKILL.md` 与 `references/research-and-adaptation.md` 中的 `web-access` Skill，在普通 ChatGPT Chat 中由 ChatGPT 原生 Web Search 代替。

研究分流不因环境变化而改变：普通常青虚构剧情可以无高赞原作开始 Raw Draft；热点、事实及用户明确研究任务仍须真实来源核验。填写高互动原作时，单视频点赞、正文/字幕可读性、来源日期和证据边界必须真实；访问受限时只停止依赖该证据的任务，不用模型记忆或搜索摘要补造研究，也不把可选原作研究恢复为普通新稿许可门。

## Python 与本地执行

普通 Chat 没有连接到本地可执行环境时：

- 不得声称运行了仓库中的 Python 脚本；
- 不得声称获得 `INTEGRITY PASS` 或其他 CLI 成功结果；
- 不得伪造 `hash`、`manifest`、`revision_id`、编号登记或 ledger 写入；
- 可以依据同一规则执行模型级语义审读，并明确这是语义检查而非本地脚本验证。

需要正式运行 `select_topics.py`、`history_manager.py`、完整性检查、状态写入、编号或本机 Word 核验时，生成清晰的 Codex 执行任务交给本地 Codex。

本地 Codex 如需更新公开快照，必须由用户明确提供业务文件和共享状态文件路径后运行 `sync_public_context.py`。同步器只读取本地状态，按固定白名单写入 `chat-context/`；它不会把完整反馈、选题、聊天或稿件发布到网页 Chat。

## Word 与正式交付

普通 Chat 可以帮助整理文案或制作非正式预览文件，但正式 Word 交付仍必须满足 `SKILL.md` 与 `references/document-schema.md` 的确认、编号、SHA256、生成和逐页视觉检查流程。

不能仅因为生成了一个文件就声明正式交付完成。

## 公开快照安全边界

`chat-context/` 是为网页 Chat 准备的公开安全投影，不是原始业务数据库。仓库为 Public 时，不得把以下内容直接复制进快照：

- 原始用户聊天或完整 `user_quote`；
- 可识别个人的私密资料；
- 未发布完整脚本、研究包或内部经营数据；
- 认证信息、账号、密钥、内部路径或需要登录才能访问的私人 URL；
- 完整反馈台账、选题台账、正式交付文件或运行目录。

如无法确定某字段是否适合公开，默认不发布该字段。
