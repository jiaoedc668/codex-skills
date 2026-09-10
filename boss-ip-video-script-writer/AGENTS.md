# Boss IP Skill维护

本目录为现役可复用Skill，入口是SKILL.md。版本唯一值为其metadata.version；迭代与清理遵守references/release-management.md，历史见CHANGELOG.md。

- 业务人物实例、用户聊天、草稿、完整台账和正式交付留在业务项目，不进入本仓库。
- `chat-context/` 只允许保存给普通 ChatGPT Chat 使用的脱敏、压缩、公开安全快照；它不是业务真相源，不能由快照反向覆盖本地人物或台账。
- `CHATGPT.md` 仅处理普通 ChatGPT Chat 的运行环境差异；本地 Codex 正常运行本 Skill 时忽略它，除非用户明确要求检查 Web 兼容性或同步公开快照。
- references/persona-template.json是新项目默认人物；修改相关规则时同时检查初始化器、迁移器及实际项目人物实例，不能只改说明。
- 新生产保留schema v6，历史v5/v4读取兼容；历史样例不升级为新候选或人工认可。
- Python修改先运行定向测试，再运行本目录tests全量unittest及scripts的compileall；git diff --check必须通过。
- Skill修改完成后按仓库迭代流程提交和推送，逐路径暂存，标签使用boss-ip-v<版本>；不混入其他Skill的既有改动。
