# 内容库与事件契约

状态目录可配置，默认 `<workspace-root>/产品视频内容库`。`scripts/manage_workspace.py` 会创建 `workspace.json`，并按用途追加以下 JSONL：

- `product-catalog.jsonl` 产品库
- `used-ideas.jsonl` 已用库及 Word 版本记录
- `rejection-pool.jsonl` 淘汰池
- `feedback-ledger.jsonl` 选择、修订、确认
- `shared-creative-preferences.jsonl` 双 Skill 共享抽象偏好
- `publishing-data.jsonl` 用户提供的播放数据

所有事件使用 `schema_version`、`event_id`、`event_type`、`occurred_at`、`product_id`、`user_quote`、`payload`。未知字段原样保留；同一状态目录内 `event_id` 全局唯一。用户派生事件必须保留非空 `user_quote`。

常用命令：

```powershell
python <skill-dir>/scripts/manage_workspace.py register-product --workspace-root <state-root> --input <brief.json> --user-quote <用户原话>
python <skill-dir>/scripts/manage_workspace.py select --workspace-root <state-root> --product-id <id> --candidate-id <id> --copy-file <copy.txt> --user-quote <用户原话>
python <skill-dir>/scripts/manage_workspace.py revise --workspace-root <state-root> --product-id <id> --copy-file <copy.txt> --user-quote <用户原话>
python <skill-dir>/scripts/manage_workspace.py confirm --workspace-root <state-root> --product-id <id> --copy-file <copy.txt> --user-quote <用户原话>
python <skill-dir>/scripts/manage_workspace.py reject --workspace-root <state-root> --product-id <id> --candidate-id <id> --user-quote <用户原话> [--reason-category topic|structure|expression|one_off]
python <skill-dir>/scripts/manage_workspace.py record-preference --workspace-root <state-root> --product-id <id> --source-skill product-video-script-writer --preference <偏好> --user-quote <用户原话>
python <skill-dir>/scripts/manage_workspace.py record-publishing --workspace-root <state-root> --product-id <id> --candidate-id <id> --user-quote <用户原话> [--views-24h N] [--views-7d N] [--recent-10-median N]
```

用户只说“不合适”时，先追问原因。仍无原因则不传 `--reason-category`，事件范围自动记为 `similarity_only`。

“第2条题材可以”尚不构成全文选择或确认，不调用 select/confirm。未确定原因的否定与独立参考案例分开记录，不猜测归因。当前 CLI 没有专门的角度认可事件；将这类原话与认可范围保存在项目的反馈记录中，不伪造其他类型事件。旧接口不变。

项目没有既定格式时，反馈记录放在 `<state-root>/<产品名>/反馈记录/YYYYMMDD_产品名_反馈记录_Vn.md`，包含产品 ID、批次、候选 ID 与版本、用户原话、明确认可/否定范围、待确认项。独立案例另列来源文件、用户要求、助手建议、用户接受范围和分析推断；没有关联候选时明确写“不关联”，不要自行挂到某条候选下。

“仍无原因”指用户明确不补充原因或要求直接换稿；没有回复不算。追问不应阻塞已明确授权且无需该答案的其他工作。现有 CLI 不能完整表达上述细分状态，Markdown 反馈记录负责保存它们，机器事件保持原语义。
