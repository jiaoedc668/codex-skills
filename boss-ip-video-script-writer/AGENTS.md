# Boss IP Skill维护

本目录为现役可复用Skill，入口是SKILL.md。版本唯一值为其metadata.version；迭代与清理遵守references/release-management.md，历史见CHANGELOG.md。

- 业务人物实例、用户聊天、草稿、台账和交付留在业务项目，不进入本仓库。
- references/persona-template.json是新项目默认人物；修改相关规则时同时检查初始化器、迁移器及实际项目人物实例，不能只改说明。
- 新生产保留schema v6，历史v5/v4读取兼容；历史样例不升级为新候选或人工认可。
- Python修改先运行定向测试，再运行本目录tests全量unittest及scripts的compileall；git diff --check必须通过。
- Skill修改完成后按仓库迭代流程提交和推送，逐路径暂存，标签使用boss-ip-v<版本>；不混入其他Skill的既有改动。
