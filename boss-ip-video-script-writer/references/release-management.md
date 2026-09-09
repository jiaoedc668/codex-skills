# 版本、发布与文件维护

## 唯一版本来源

Skill版本读取SKILL.md的metadata.version，首次正式编号为1.0.0。CHANGELOG.md每次新增版本条目，写明日期、改动、兼容范围和实际验证。使用MAJOR.MINOR.PATCH：不兼容合同或迁移要求变化升MAJOR，兼容新增能力升MINOR，修复及不改变行为的文档更正升PATCH。未发布的同次修订可更新当前待发布条目；已发布版本不改标签，不重写历史成绩。

候选schema v6、人物schema 3、人物profile_revision、观点active_version、成品A/B及V版本各有用途，不能随Skill版本一并改号。Git标签为boss-ip-v<版本>，不占用其他Skill的版本空间。工作区版本文本不代表已提交或已发布。

## 一次迭代

1. 读本目录AGENTS、现役入口和CHANGELOG，检查git status、分支、remote及标签。已有未提交内容先列入本次范围或保留，不覆盖、不静默纳入其他Skill。
2. 先写清改什么与保留什么，再修改规则、代码及对应测试。用户已授权且范围明确时直接推进，不重复确认。
3. Python改动运行定向测试、全量unittest、compileall和git diff --check。规则改动用真实请求审读范围、事实、输出与反馈边界，不把词句匹配或机器通过当作脚本质量分。
4. 检查相对链接、初始化结果、受影响项目人物设定与Junction；必要时迁移并保存旧字节快照。更新CHANGELOG及项目PROGRESS末尾，不复制第二套现役规则。
5. 审查git diff后逐路径暂存本Skill及明确受影响的仓库文档，禁止git add .混入其他Skill、内容库、聊天记录、交付或测试缓存。提交前查看git diff --cached --stat及--check。
6. 在用户授权的仓库迭代范围内提交并创建带注释标签；按仓库既定流程推送明确分支和本Skill标签，不使用--tags推送其他标签。以远端分支和标签实际SHA核对发布；网络或权限失败保留本地结果并报告实际状态。

```powershell
python -m unittest discover -s boss-ip-video-script-writer/tests -p "test_*.py" -q
python -m compileall -q boss-ip-video-script-writer/scripts
git diff --check
git diff --cached --stat
git diff --cached --check
```

## 文件去留

- canonical Skill保存可复用规则、初始化模板、脚本、测试及版本历史；业务人物实例、台账、研究与交付留在业务项目，不上传仓库。
- 人物模板为references/persona-template.json；history_manager.py init从这里生成新实例，不再手写第二份默认设定。模板更新不自动覆盖现有项目人物实例。
- 迁移前快照保存原字节和哈希；现役人物删除重复legacy块和过期行为，版本集合的旧项继续保留但只读最新active_version。新稿读取当前人物，旧稿复验显式指定对应快照；不绕过过期引用校验。
- 删除本轮生成的缓存、锁文件及没有后续用途的临时文件前，核对绝对路径在本次目录内。旧草稿、已引用的历史样例、稳定测试夹具和有唯一差异的历史副本保留；不能以清理为由抹去失败记录。
- 清理与更新需记录具体对象及理由。发现旧说法先查实际调用和引用；修当前入口，历史文件标清身份，不无差别搜索替换。

## 回滚

从已验证Git标签恢复Skill代码须保留当前未提交改动；不强制reset或移动现有标签。人物回滚使用该版本的快照并保留现役副本，不能只回滚规则而让人物引用留在不兼容版本。回滚后重跑受影响门禁，候选人工评价仍绑定原版本。
