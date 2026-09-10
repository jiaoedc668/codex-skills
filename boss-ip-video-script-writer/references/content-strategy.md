# schema v6 创作优先选题与结构化

本文件只负责选题池、证据门、否决和成对比较。研究来源怎样取得见 `research-and-adaptation.md`；故事蓝图见 `story-engine.md`。

## 目标与优先级

先做题目判断及必要事实核验，再 Raw Draft → Creative Review，故事成立后才整理本文件的选题池、比较与brief。普通常青虚构剧情不以高赞研究为许可。剧情先看人物做了什么、谁正受损、双方为何不肯退、发哥听到新信息后如何判断、当事人下一步怎样改变。口播围绕多数人的人生原则、人品价值和处世智慧，具体小事作论据。机器不打质量分，也不预测可拍。

优先找“人做了什么”，不先给角色贴观点标签。“哥哥姐姐不愿承担养老责任”要落实成“他们一人愿意出5000，却都让我这个工资最低的辞职照顾老人”。具体行为带出观点，不由抽象观点制造对白。strongest_counterargument保留现实动机；表达层尽量找到符合身份的情绪触发句，让观众感觉到伤害或不公平，方法与边界见 story-engine.md。

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

`viral_expression_samples` 是可选表达研究，不属于某个候选题；数组保留，允许为空或不足3条。填写的每条仍须单视频点赞不少于10万且内容可读，不得伪造数据。详细字段与原创边界见 `research-and-adaptation.md`。选题池的机器校验发生在故事审读后，不是 Raw Draft 的前置许可。

候选题 `prospects[]` 包含：

- `topic_id`、`title`、`topic_kind`、`priority_category`；
- `research_evidence`；
- `production_case`；
- `veto_reasons`，未否决时为空数组。

池子只需有足够的未否决题支撑本轮请求数量，不设固定题数、母题数或拍法数。

## 证据门

来源统一保存 `title`、HTTP(S) `url`、ISO日期 `source_date` 与 `retrieved_at`、`supports`、`limits`。

- `current_issue` 必须至少有一条 `heat_signals`，来源日期距读取日期不超过七天。
- 普通虚构 `evergreen` 可用空 `research_evidence`，不要求跨九十天来源或高互动来源；所有主动提供的来源仍须合规，未研究不能宣称热度或跨期复现。
- 热点、事实或明确研究任务必须标记 `research_required: true`，并有非空 `sources` 或 `fact_sources`。常青题涉及政策、真实主体、真实数据也适用；故事内明确虚构的生活金额不冒充现实数据。作者核对实际任务，不得漏标逃避研究。
- 事实来源与热度来源可以是同一链接，但要分别说明它证明什么、不能证明什么。
- 搜索结果数量、排序和模型熟悉度都不是热度证据。

任务所需事实证据不完整时写入 `veto_reasons`，不能靠作者评价补齐。普通常青虚构题没有可选平台材料不构成否决理由。成对比较的 evidence_reason 可如实说明双方均为虚构常青、无平台证据，不编造热度排名；主要比较具体行为和损失能否抓住观众。

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

退出0和返回的 `selected` 只证明所需证据、否决、比较与选中集合相互一致。选中的每题原样进入候选 `topic_decision`。创作审读后若事件、反方或代价仍需改变，先修故事再同步新选题池、brief及候选，保留旧修订；不能为迁就旧字段把故事写死，也不能让各工件互相矛盾。

旧schema v5的fage_cost与研究合同保留历史读取；v6仅放宽常青虚构及可选原作研究门，保留否决和比较校验，不强迫发哥成为事件参与人。
