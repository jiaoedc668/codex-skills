# 初始建设记录（历史归档）

原记录形成于 2026-09-08。以下内容仅保留历史证据，当前版本以 VERSION 和 CHANGELOG 为准；当时的工作树偏差不是当前阻塞判断。

# 进度
目标：建成产品资料到候选、确认、Word 拍摄稿及学习台账的可重复 Codex Skill。
顺序：基线与失败证据 → 契约测试与最小实现 → 学习闭环 → 安装与真实验收。
最大风险：老板 IP 工作树已有非本轮改动，必须避免覆盖并保持既有行为。
2026-09-08：复跑基线；HEAD 一致，老板 IP 200 项通过，compileall 与 diff-check 为 0。
2026-09-08：发现 5 个已修改文件和 1 个未跟踪测试，原始输出已置于 BLOCKED.md 顶部。
2026-09-08：完成无 Skill 独立压力场景；证实会跳过 3 候选与确认门、编造价格续航并超出口播时长。
2026-09-08：产品契约、追加式内容库、确认门、Word 版本及 Boss 双向共享偏好已实现并完成红绿回归。
2026-09-08：真实触发验证 3/3/6 与缺项清单；测试 Word 全链生成 V1/V2，Office 渲染 1 页并逐页目检通过，临时产物已删除。

# 基线偏差原始输出

```text
## main...origin/main
 M boss-ip-video-script-writer/scripts/create_candidate.py
 M boss-ip-video-script-writer/scripts/dual_format_contract.py
 M boss-ip-video-script-writer/scripts/select_topics.py
 M boss-ip-video-script-writer/tests/test_authoring_v6.py
 M boss-ip-video-script-writer/tests/test_dual_format_v6.py
?? boss-ip-video-script-writer/tests/test_viral_research_v6.py
552cb88e8215766f6989d3a802a61486824e5c2f
----------------------------------------------------------------------
Ran 200 tests in 8.695s

OK
warning: in the working copy of 'boss-ip-video-script-writer/scripts/create_candidate.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'boss-ip-video-script-writer/scripts/dual_format_contract.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'boss-ip-video-script-writer/scripts/select_topics.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'boss-ip-video-script-writer/tests/test_authoring_v6.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'boss-ip-video-script-writer/tests/test_dual_format_v6.py', LF will be replaced by CRLF the next time Git touches it
STATUS_EXIT=0 HEAD_EXIT=0 BOSS_TEST_EXIT=0 COMPILE_EXIT=0 DIFF_EXIT=0
```

影响：任务书记录的“工作树干净、194 项测试”与当前状态不符。现有改动归用户所有，本任务不覆盖、不回滚；产品 Skill 的独立工作可继续。共享偏好接入老板 IP 时，只允许评估并修改任务书白名单中的 `SKILL.md`、`scripts/history_manager.py` 及对应测试；若与现有改动发生内容冲突则保持阻塞。

