# 候选数据契约

内部 UTF-8 JSON 顶层包含：

```json
{
  "schema_version": 1,
  "brief": {},
  "product_facts_sha256": "64位小写SHA256",
  "research": [],
  "research_fallback_reason": null,
  "candidates": []
}
```

`brief` 必填 `product_name`、`category`、`use`、`selling_points`、`target_customer`、`format`，并保存用户给出的选填项。为保持产品事实哈希与校验器一致，调用：

```python
from contract import product_facts_sha256
packet["product_facts_sha256"] = product_facts_sha256(packet["brief"])
```

每条 `research` 包含 `platform`、`url`、`published_at`、`comparability_note`、`performance_evidence`、`learned`。分别保存发布时间、为何与本产品同类、可复核的高表现依据及抽象学习点；不写入用户本地资料。用户提供的参考也要注明其高表现依据来自用户说明，不得冒充已联网核验。

每个候选包含：

```json
{
  "candidate_id": "稳定且批内唯一的ID",
  "format": "monologue或story",
  "theme": "主题",
  "creative_note": "创意说明",
  "full_copy": "完整文案",
  "estimated_seconds": 30,
  "main_selling_point": "一个用户原始卖点",
  "used_selling_points": ["用户原始卖点"],
  "fact_claims": [
    {"claim": "文案中的产品事实表达", "source_text": "对应的用户原始事实"}
  ]
}
```

`fact_claims.source_text` 必须原样对应产品名、种类、用途、型号或卖点之一。普通生活场景和拍摄动作不作为产品事实，但不得暗含新的产品能力。内部可添加未知字段，公开输出始终由 `check_packet.py --public-json` 过滤。

新包追加 `skill_version`（读取技能 VERSION）和 `batch_revision`（当前候选版本）。二者与 schema_version 独立，不回填历史包。剧情语义自检可放在 `story_review`，遵循 story-craft.md；这些字段不改变公开输出。机器校验不验证故事动机或创作质量。
