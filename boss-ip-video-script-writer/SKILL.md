---
name: boss-ip-video-script-writer
description: Use when 为发哥老板IP创作或优化抖音、视频号自然流量剧情、口播、标题、发布介绍，参考续写或制作确认后的Word；不用于商品口播、千川广告或直播带货。
metadata:
  version: "1.1.0"
---

# Boss IP Video Script Writer

新生产为schema v6，默认剧情story，可指定单人口播monologue、话题topic和核心观点core_viewpoint。人物边界与用户核心立场优先，其次故事完整和观点力度，再考虑时长及流程。机器只给INTEGRITY PASS/FAIL，不代替谢总判断共鸣、可拍或满意。

目标效果：标题和开头让观众愿意听，正文说透具体难处及被忽略的理由，发哥的判断建立人物信任；前期弱化公司和产品。维护本技能时读 [references/release-management.md](references/release-management.md)，版本历史见 [CHANGELOG.md](CHANGELOG.md)。技能版本独立于数据schema和成品编号。

## 先判断任务

| 用户请求 | 执行范围 |
|---|---|
| 新写、参考续写 | 新候选流程；数量按用户本轮要求，否则三条。先读参考正文，附件缺失就说明缺什么，不假装参考 |
| 优化现有稿、只改某段 | 先锁定源稿和允许范围，沿用已验证且仍适用的研究；换题、重构核心冲突或明确要求高赞研究时走对应研究门。按新修订保存，不覆盖旧稿 |
| 只改标题 | 读取完整正文，按标题与开头兑现审读后仅交标题；正文不改，不新建三候选，不自动重跑高赞选题研究 |
| 发布介绍、标签 | 从给定正文提炼，按指定平台与数量交付，不加未经正文支持的事实，不修改候选或替用户发布 |

标题、发布包装与限定改稿细则读 [references/task-routing.md](references/task-routing.md)。纯包装仅需当前正文及相关边界，不加载整套研究和台账；用户明确要求联网研究时仍服从。下文1—4节的研究、组装和三候选展示适用于新候选，不强加给纯包装任务。

## 开始与范围

以项目根为workspace-root、本技能目录为skill-dir。先读AGENTS.md及PROGRESS.md、BLOCKED.md末尾，然后读references/authorized-fiction-persona.md和老板IP内容库/人物设定.json。安装入口是指向本目录的Junction，不复制第二套。

创作时人物模型、选题台账、旧草稿和旧交付只读；用户明确授权维护人物时按人物版本规则迁移。反馈台账只追加真实用户原话，不把选中、生成Word和可拍评价互相代换。新建运行目录前在项目AGENTS补用途、命名和清理规则。

另读取可配置状态根下的 `shared-creative-preferences.jsonl`，只采用用户明确给出的跨内容抽象偏好，例如开头是否直接、表达是否说教。不得从这里读取或写入人设、题材规则、固定文案、产品事实或未明说的推断。默认共享状态根为 `<workspace-root>/产品视频内容库`；项目或用户指定其他路径时，两个 Skill 必须指向同一文件。

```powershell
python <skill-dir>/scripts/history_manager.py recent-shared-preferences --shared-ledger <shared-state-root>/shared-creative-preferences.jsonl --limit 12
python <skill-dir>/scripts/history_manager.py record-shared-preference --input <explicit-shared-event.json> --shared-ledger <shared-state-root>/shared-creative-preferences.jsonl
```

共享事件必须使用 `schema_version: 1`、全局唯一 `event_id`、`event_type: creative_preference`、`occurred_at`、`product_id`、非空 `user_quote`，以及含 `source_skill` 和 `preference` 的 `payload`。只追加，不覆盖；损坏事件、重复 ID 或缺少原话时拒绝写入。

## 1 输入与形式

输入可只给形式、话题或观点中的任意项；未给形式就是story。没给话题和观点时，作者从证据竞争获胜题提炼，不向用户追问空泛参数。用户给了方向就围绕该方向选题；笼统观点可深化，但在写作brief记录原话、深化结论及理由，不改变原方向。

- story为剧情，约60秒、尽量90秒内。朋友或同事讲自己的事，发哥追问、分析、批评或建议，由当事人决定和行动，可以停在可执行下一步。
- monologue为口播，约30秒、尽量45秒内。全篇仅发哥说话；主题是人生原则、人品价值或处世智慧，小事只作论据。首句用强判断、反常识或悬念抢停留，再用2至4个不重复理由、对照或例证说透，回应现实反驳，最后用前文托得住的走心判断收尾。

时长估算办法见references/writing-style.md，估算不等于实际表演时长；长短由谢总看稿后的明确反馈校准。历史direct_dialogue_30的“30 秒稿”和light_story_60的“60 秒稿”仍按schema v5读取，旧双人对话不能改标单人口播，旧验收不继承为口播成绩。

## 2 研究硬门与候选竞争

使用web-access研究公开议题，读取references/research-and-adaptation.md和content-strategy.md。选题前必须先核验至少3条不同原作：每条都是单视频点赞量不少于10万，且成功读取正文、字幕或可靠转写。账号总获赞、只有标题或内容不可读都不计入。不足3条立即停止创作并反馈访问限制。真实证据、跨期复现与互动限制必须保存；只学抽象表达机制，不复制连续对白、情节或金句。不得上传本地材料。

建立v6选题池，顶层 `viral_expression_samples` 保存上述3条以上原作及学到的机制和原创边界；同时保留证据、否决理由和成对比较，production_case用stakeholder_cost记录当事人代价。默认正好选三题；用户当轮明确指定数量时按指定数量，不设形式或母题配额。

选题确定前必须做批内语义差异审读，逐条列出主角身份、对立关系、核心损失、冲突因果和发哥裁决/出口五项。任意两条有三项相同或近义，就视为同题换皮并退回选题阶段；不能靠更换金额、亲属称谓、地点或道具伪造差异。机器文字查重通过不能替代这项人工审读。

```powershell
python <skill-dir>/scripts/select_topics.py --input <topic-pool.json>
python <skill-dir>/scripts/history_manager.py recent-feedback --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl --limit 12
```

只有选中集合通过，才能生成写作任务。以下参数按需添加，省略format为剧情；输出文件必须是新路径。

```powershell
python <skill-dir>/scripts/create_candidate.py prepare --topic-pool <topic-pool.json> --topic-id <selected-topic-id> --output <brief.json>
python <skill-dir>/scripts/create_candidate.py prepare --topic-pool <topic-pool.json> --topic-id <selected-topic-id> --format monologue --topic <用户话题> --core-viewpoint <用户观点> --output <brief.json>
```

深化笼统观点时另给--refined-core-viewpoint和--direction-rationale，并人工核对原方向未变。brief从选中题取得研究证据及topic_decision，保留原输入和推导结论。这个命令组装任务，不自动创作对白。

## 3 创作与组装

先读references/story-engine.md、writing-style.md、candidate-batch-schema.md。先写creative_blueprint，再写完整script；不能事后补蓝图伪装写作顺序。蓝图说清原理解、漏算因素及改变判断的依据；故事丰富来自处境、委屈、选择与后果，不来自重复解释。

发哥可以直接反驳做错事的人，但在对白、动作、镜头、前史里均不能是事件参与者、介绍人、安排者或代办人；不能替人借款、招聘、催债、联系中介、调班或落实家务。建议须回应眼前难题，由当事人承担决定和行动。标题强化的冲突必须有正文支持，不泛化攻击性别群体。

作者写出完整v6候选后用brief组装。新候选在script中同时写theme与title：theme是题材，title是面向观众的成片标题。输入文件不覆盖；输出必须新建。

```powershell
python <skill-dir>/scripts/create_candidate.py assemble --brief <brief.json> --input <authored.json> --persona <workspace-root>/老板IP内容库/人物设定.json --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl --output <candidate.json>
python <skill-dir>/scripts/check_candidate_integrity.py --input <candidate.json> --persona <workspace-root>/老板IP内容库/人物设定.json --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl
python <skill-dir>/scripts/check_content_similarity.py --input <candidate.json> --ledger <workspace-root>/老板IP内容库/选题台账.jsonl
python <skill-dir>/scripts/check_batch_integrity.py --inputs <candidate-1.json> <candidate-2.json> <candidate-3.json> --topic-pool <topic-pool.json> --persona <workspace-root>/老板IP内容库/人物设定.json --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl
```

逐篇通读对白、动作、镜头、前史和现实出口；关键词检查不代替语义判断。标题和首两句一起做吸引力与兑现审读：至少由明确冲突、利益后果、身份反差或认知悬念驱动，开头立即接住标题问题，正文给出相应解释；平淡概括、空泛大道理和夸大后果退回重写。口播额外审读主题是否属于大范围人生判断、小事是否只作论据、收尾是否由前文自然得出。具体方法见writing-style.md；未通过留在内部修订，不降低标准。

## 4 展示与反馈

通过后从当前候选导出公开对象。默认展示三条，每条固定且只按“题材＋标题＋完整文案”的顺序呈现；用户明确指定数量时按当轮数量。不展示形式标签、时长、自评、内部字段、动作或镜头，也不替用户选择。保存manifest，绑定format、已展示候选身份和当前revision_id，记录公开时间和根因假设。

```powershell
python <skill-dir>/scripts/create_candidate.py public --input <candidate.json> --output <public.json>
python <skill-dir>/scripts/history_manager.py record-feedback --input <explicit-event.json> --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl
python <skill-dir>/scripts/acceptance_state.py --manifests <manifest.json> --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl
```

新事件记录format，旧事件不回填。v6只统计同批、同形式、当前修订的显式用户结果，不继承旧模式可拍成绩；故事与口播分别跟踪。默认三条批次等待逐条评价，少于两条可拍时改变根因；同根因连续三批失败须换方法。指定非三条逐条记录，不混算三条批次成绩。用户明确只改某篇或结尾时优先限定修订，保留其他正文；只有“不行”不擅自推断原因。详见references/feedback-loop.md。

## 5 Word、编号与专项授权

普通新稿先选中，再确认当前完整candidate_doc哈希，且用户要求生成Word。修订保留candidate_id、递增revision_id，不沿用旧确认。制作包另装delivery envelope，不污染候选；内容结构见references/document-schema.md。

正式编号按剧情B01、口播A01分别跨批次递增。独立登记文件记录稳定身份、版本、源与Word哈希。同稿修订保持编号，未选候选不占正式号。已有号不可换给其他稿，失败记录不可用来伪造完成。

用户明确专项授权时可使用独立 `rewrite_delivery_authorization`，必须绑定任务原文、授权范围、旧源与新源哈希，不创建虚假 `copy_confirmation` 或 `direct_shoot`。授权范围外的新稿仍走普通门。

```powershell
python <skill-dir>/scripts/generate_script_docx.py --input <delivery-envelope.json> --registry <workspace-root>/生成脚本/发哥老板IP/内部资料/编号登记.json --persona <workspace-root>/老板IP内容库/人物设定.json --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl --workspace-root <workspace-root> --output-root <authorized-output-directory>
```

专项交付在同一命令另加--authorization <专项授权.json>。输出目录先按项目要求建立。生成器不覆盖旧文件，按确认的V3字体与加粗规则排版。完整性、授权和编号通过后，实际打开Word、渲染全部页面、逐页查看并核对每句对白及标题编号版本，才能交付。不能仅凭文件存在或结构测试宣称完成。生成Word不授权发布、提交或清理旧资料。
