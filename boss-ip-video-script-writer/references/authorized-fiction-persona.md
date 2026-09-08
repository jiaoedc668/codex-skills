# schema 3 授权虚构人物版本

本文件只负责发哥人物模型的版本、引用、演化和事实禁区。故事蓝图与对白写法分别见 `story-engine.md`、`writing-style.md`。

发哥是授权虚构人设。创作者可以安排合规的小事件、动作、选择和对白，不需要宣称这些事件真实发生；不得借虚构故事补写未知履历、家庭、财务或公司事实。

## 当前人物模型

生产文件是 `老板IP内容库/人物设定.json`，`schema_version=3`。身份、拍摄框架、允许行为、稳定表达、可见弱点、喜剧关系和事实禁区提供创作边界；长期判断与可复用虚构连续性使用版本记录。

### viewpoint_principles

每条长期判断包含稳定 `id`、`status`、`active_version` 和连续递增的 `versions`。每个版本写：

- `version`；
- `tension`；
- `default_choice`；
- `rejected_choice`；
- `exceptions`；
- `cost`；
- `source_candidate_id`；
- `reason`。

既有人物模型中的cost保持只读。新稿引用其取舍时记录现实理由和当事人代价，不强迫发哥承担生活、资源或安排责任。不能只写负责、善良或讲道理。

### fictional_continuity

每条连续性同样版本化。版本写 `claim`、`scope`、`allowed_reuse`、`forbidden_expansion`、来源和理由。

`scope` 只允许：

- `single_script`：只在来源候选当前故事内成立；
- `reusable_low_risk`：只复用低风险动作、偏好或关系互动，并严格遵守允许与禁止范围。

初始可以为空，不得为了填字段主动创造经历。

## 候选引用

v5/v6 候选的 `persona_continuity` 必须：

- 用 `principle_id` 和 `principle_version` 引用仍为 active 的最新观点版本；
- 用 `use_mode=follow|exception|revise` 和 `use_explanation` 说明本稿怎样使用判断；
- 用 `continuity_refs` 引用仍有效的最新连续性版本，或保持空数组。

未知、过期、已停用版本都失败。`revise` 只表示当前候选提出修订依据，不能自行改人物文件。候选阶段不向谢总展示内部版本号，也不能把人物引用冒充用户质量评价。

## 演化事件

人物演化只通过 schema 1 事件执行，事件包含 `event_type`、`operation`、`record_id`、`source_candidate_id`、`reason` 和 `record`。

- `add`：新增稳定 ID 和版本1，已有 ID 不得重复；
- `revise`：只给 active 记录追加 `active_version+1`，旧版本保持只读；
- `retire`：把记录标为 retired，保存来源与理由，不删除旧版本，`record` 为空。

运行：

```powershell
python <skill-dir>/scripts/history_manager.py record-persona-evolution --persona <workspace-root>/老板IP内容库/人物设定.json --input <event.json>
```

命令只有在原模型、事件和完整新模型全部通过时才替换文件。人物变化必须来自已公开候选的明确反馈或经批准的创作连续性，不从机器评价、沉默或推测学习。

## 重大事实禁区

不得擅自写实发哥的精确年龄、婚姻状态、子女、父母、籍贯、创业年限、财富债务、可核验的个人失败或家庭经历，也不得虚构公司制度、经营数据、员工处分或违法事件。

禁止用“我老婆”“我女儿”“我儿子”“我妻子”“我当年负债”“我创业时”等第一人称补齐未知事实。员工、朋友或亲戚可以是单条授权虚构关系，但不会自动成为发哥真实履历或下一条的连续事实。

允许发哥评价、追问、直接反驳或建议，由当事人作决定；不能用虚构履历背书。对白、动作、镜头、前史中发哥均不得参与、介绍、安排、代办，不能替人借款、招聘、催债、联系中介、调班或落实家务。
