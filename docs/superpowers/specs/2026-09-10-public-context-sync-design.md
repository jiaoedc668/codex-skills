# Boss IP 公共上下文同步设计

## 目标

为 `boss-ip-video-script-writer` 增加本地业务状态到 `chat-context/` 的公开安全同步器。业务项目中的人物、反馈台账、选题台账和共享偏好台账仍是唯一真相源；同步器只读取它们并原子写入四个公开快照。

## 输入与复用

新增 `scripts/sync_public_context.py`。脚本通过命令行显式接收人物文件、反馈台账、选题台账、共享偏好台账和输出目录，导入 `history_manager.py` 的 `read_json`、`read_feedback`、`feedback_context`、`read_ledger`、`read_shared_preferences` 与 `clean`。它不调用任何业务写入函数，也不修改输入文件。

## 四类公开投影

- `persona-current.json`：只输出公开创作身份、平台/形式边界、授权行为的行为描述与限制、稳定表达模式、当前有效观点的公开取舍、公开弱点及安全收束。排除来源候选、原因、内部版本细节、禁止传记模式和任何未明确允许的字段。
- `recent-feedback.json`：只输出最近 12 条反馈的类型、时间、候选/批次/修订 ID、评价枚举、原因码、保留/避免项、长度判断、公开发布数据。严格删除 `user_quote`、内部路径和原始事件的未知字段。
- `recent-topics.json`：从选题台账当前状态汇总最近 24 个主题的稳定 ID、标题、类别、状态和必要的去重摘要。不得输出完整稿件、研究正文、URL、原始台账路径或内部运行字段。
- `shared-preferences.json`：只输出共享事件的时间、来源 Skill 和抽象偏好；删除 `user_quote`、事件原始扩展字段、路径和可识别资料。

所有快照均包含 `schema_version`、`snapshot_status`、`updated_at`、`source_of_truth`、`public_safe_only` 和 `items`/投影主体。任一输入读取、校验或安全审查失败时不写任何目标文件。

## 安全与写入

投影使用固定白名单，禁止递归保留未知字段。所有字符串字段经过敏感字段名和内部绝对路径检查；安全审查发现 `user_quote`、认证信息、内部路径、完整稿件键或疑似私人资料时失败。先把四个结果写入同一临时目录，全部生成后再逐文件替换目标，确保失败不会留下部分更新。输出目录由 CLI 指定，脚本不从仓库推断业务目录。

## 验收

测试必须证明：四类投影包含允许字段且不含敏感字段；输入业务文件字节不变；失败时现有快照字节不变；四个输出均可解析且成功状态为 `current`；CLI 能使用显式路径运行。完成后运行本目录全量 unittest、scripts compileall、四个 JSON 校验和 `git diff --check`。
