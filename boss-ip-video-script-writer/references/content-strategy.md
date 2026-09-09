# schema v6 证据型选题竞争

本文件只负责选题池、证据门、否决和成对比较。研究来源怎样取得见 `research-and-adaptation.md`；故事蓝图见 `story-engine.md`。

## 目标与优先级

通过表达研究硬门后再选题。剧情先判断40—50+泛人群会失去什么、议题不同立场为何有现实理由、发哥提出什么具体判断、当事人有哪些选择及代价。口播先竞争能覆盖多数人经验的人生原则、人品价值和处世智慧，具体小事只能作论据，不能成为主题本身。机器不打质量分，也不预测可拍。

用户当轮指定题材、数量或拍法时优先服从。没有指定且候选难以区分时，依次考虑：钱/房/养老/家庭责任，中年事业/失业/创业，子女与代际，婚姻，年龄与重启，人情面子。该顺序只用于人工破平局，不写成分数或配额。

## 选题池结构

选题池顶层必须且只能包含：

```json
{
  "schema_version": 6,
  "pool_id": "pool-YYYYMMDD-...",
  "requested_candidate_count": 3,
  "viral_expression_samples": [],
  "prospects": [],
  "pairwise_decisions": [],
  "selected_topic_ids": []
}
```

`viral_expression_samples` 是创作运行共享的表达研究，不属于某个候选题。必须至少3条不同原作，每条是单视频点赞不少于10万且内容可读，详细字段和原创边界见 `research-and-adaptation.md`。这一项在选题证据比较前先校验。

候选题 `prospects[]` 包含：

- `topic_id`、`title`、`topic_kind`、`priority_category`；
- `research_evidence`；
- `production_case`；
- `veto_reasons`，未否决时为空数组。

池子只需有足够的未否决题支撑本轮请求数量，不设固定题数、母题数或拍法数。

## 证据门

来源统一保存 `title`、HTTP(S) `url`、ISO日期 `source_date` 与 `retrieved_at`、`supports`、`limits`。

- `current_issue` 必须至少有一条 `heat_signals`，来源日期距读取日期不超过七天。
- `evergreen` 必须至少有两条相隔九十天以上的 `recurrence_sources`，并至少有一条写明 `visible_interaction` 的 `high_interaction_sources`。
- 事实来源与热度来源可以是同一链接，但要分别说明它证明什么、不能证明什么。
- 搜索结果数量、排序和模型熟悉度都不是热度证据。

证据不完整时写入 `veto_reasons`，不能靠作者评价补齐。

## 成片依据

每个题的 `production_case` 必须写全：

- `audience_stake`：观众会承担的现实利害；
- `concrete_event`：此刻已发生并逼人选择的事件；
- `concrete_anchor`：账单、期限、金额、合同、消息或可见物；
- `strongest_counterargument`：现实中有人会坚持的最强反方；
- `fage_choice` 与 `stakeholder_cost`：发哥的具体判断，以及当事人承担的现实代价；
- `ending_consequence`：镜头结束时谁的下一步改变；
- `audience_response_space`：观众还能补充或反对什么。

“有共鸣”“很现实”“可拍性强”不能代替具体字段。事实风险不可控、无法形成选择、必须依赖复杂演员或地点、违反谢总明确反馈的题直接否决；热度不能复活已否决题。

## 成对比较

对拟选题与所有其他未否决题逐对比较。每对只保留一次：

```json
{
  "left_topic_id": "topic-a",
  "right_topic_id": "topic-b",
  "preferred_topic_id": "topic-a",
  "evidence_reason": "具体证据差异",
  "production_reason": "具体成片差异"
}
```

拟选题遇到未选题时必须胜出；两个拟选题互比时允许任一方胜出。禁止 `score`、`weights`、`rank`、`shootability_score` 或任何 `*_score` 字段，也不能左右调换同一对题重复计票。

运行：

```powershell
python <skill-dir>/scripts/select_topics.py --input <topic-pool.json>
```

退出0和返回的 `selected` 只证明证据、否决、比较与选中集合相互一致。选中的每题必须原样进入候选 `topic_decision`；写稿时不得偷换事件、反方、判断方向或当事人代价。

旧schema v5的fage_cost只保留历史读取；v6复用原证据、否决和比较校验，不强迫发哥成为事件参与人。
