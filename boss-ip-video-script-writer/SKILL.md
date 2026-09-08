---
name: boss-ip-video-script-writer
description: Use when 为发哥这一授权虚构老板IP研究或创作抖音自然流量剧情、单人口播及其Word交付；不用于商品口播、千川广告或直播带货。
---

# Boss IP Video Script Writer

新生产为schema v6，默认剧情story，可指定单人口播monologue、话题topic和核心观点core_viewpoint。人物边界与用户核心立场优先，其次故事完整和观点力度，再考虑时长及流程。机器只给INTEGRITY PASS/FAIL，不代替谢总判断共鸣、可拍或满意。

## 开始与范围

以项目根为workspace-root、本技能目录为skill-dir。先读AGENTS.md及PROGRESS.md、BLOCKED.md末尾，然后读references/authorized-fiction-persona.md和老板IP内容库/人物设定.json。安装入口是指向本目录的Junction，不复制第二套。

人物模型、选题台账、旧草稿和旧交付只读。反馈台账只追加真实用户原话，不把选中、生成Word和可拍评价互相代换。新建运行目录前在项目AGENTS补用途、命名和清理规则。

## 1 输入与形式

输入可只给形式、话题或观点中的任意项；未给形式就是story。没给话题和观点时，作者从证据竞争获胜题提炼，不向用户追问空泛参数。用户给了方向就围绕该方向选题；笼统观点可深化，但在写作brief记录原话、深化结论及理由，不改变原方向。

- story为剧情，约60秒、尽量90秒内。朋友或同事讲自己的事，发哥追问、分析、批评或建议，由当事人决定和行动，可以停在可执行下一步。
- monologue为口播，约30秒、尽量45秒内。全篇仅发哥说话，首句直接亮观点，连续用具体理由、例子和现实反驳把观点说透；不强塞对手或结果动作。

时长估算办法见references/writing-style.md，估算不等于实际表演时长；长短由谢总看稿后的明确反馈校准。历史direct_dialogue_30的“30 秒稿”和light_story_60的“60 秒稿”仍按schema v5读取，旧双人对话不能改标单人口播，旧验收不继承为口播成绩。

## 2 研究与三候选竞争

使用web-access研究公开议题，读取references/research-and-adaptation.md和content-strategy.md。真实证据、跨期复现与互动限制必须保存；只学抽象表达机制，不复制连续对白、情节或金句。不得上传本地材料。

建立v6选题池，保留证据、否决理由和成对比较，production_case用stakeholder_cost记录当事人代价。默认正好选三题，不设形式或母题配额。

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

先读references/story-engine.md、writing-style.md、candidate-batch-schema.md。先写creative_blueprint，再写完整script；不能事后补蓝图伪装写作顺序。故事丰富来自处境、委屈、选择与后果，不来自重复解释。

发哥可以直接反驳做错事的人，但在对白、动作、镜头、前史里均不能是事件参与者、介绍人、安排者或代办人；不能替人借款、招聘、催债、联系中介、调班或落实家务。建议须回应眼前难题，由当事人承担决定和行动。标题强化的冲突必须有正文支持，不泛化攻击性别群体。

作者写出完整v6候选后用brief组装。输入文件不覆盖；输出必须新建。

```powershell
python <skill-dir>/scripts/create_candidate.py assemble --brief <brief.json> --input <authored.json> --persona <workspace-root>/老板IP内容库/人物设定.json --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl --output <candidate.json>
python <skill-dir>/scripts/check_candidate_integrity.py --input <candidate.json> --persona <workspace-root>/老板IP内容库/人物设定.json --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl
python <skill-dir>/scripts/check_content_similarity.py --input <candidate.json> --ledger <workspace-root>/老板IP内容库/选题台账.jsonl
python <skill-dir>/scripts/check_batch_integrity.py --inputs <candidate-1.json> <candidate-2.json> <candidate-3.json> --topic-pool <topic-pool.json> --persona <workspace-root>/老板IP内容库/人物设定.json --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl
```

逐篇通读对白、动作、镜头、前史和现实出口；关键词检查不代替语义判断。未通过留在内部修订，不降低标准。专项七篇沿用已交付话题重写，单独走授权修订批，不拿它代替日常三候选。

## 4 展示与反馈

通过后从当前候选导出公开对象，正好展示三条“形式标签＋主题＋完整对白＋关键动作/必要镜头”。不展示内部字段或自评，不替用户选择。保存schema2 manifest，绑定format、三份候选身份和当前revision_id，记录公开时间和根因假设。

```powershell
python <skill-dir>/scripts/create_candidate.py public --input <candidate.json> --output <public.json>
python <skill-dir>/scripts/history_manager.py record-feedback --input <explicit-event.json> --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl
python <skill-dir>/scripts/acceptance_state.py --manifests <manifest.json> --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl
```

新事件记录format，旧事件不回填。v6只统计同批、同形式、当前修订的显式用户结果，不继承旧模式可拍成绩；故事与口播分别跟踪。默认等待逐条评价，少于两条可拍时改变根因；同根因连续三批失败须换方法。用户明确只改某篇或结尾时优先限定修订，保留其他正文；只有“不行”不擅自推断原因。详见references/feedback-loop.md。

## 5 Word、编号与专项授权

普通新稿先选中，再确认当前完整candidate_doc哈希，且用户要求生成Word。修订保留candidate_id、递增revision_id，不沿用旧确认。制作包另装delivery envelope，不污染候选；内容结构见references/document-schema.md。

正式编号按剧情B01、口播A01分别跨批次递增。独立登记文件记录稳定身份、版本、源与Word哈希。同稿修订保持编号，未选候选不占正式号。已有号不可换给其他稿，失败记录不可用来伪造完成。

用户明确专项授权可使用独立rewrite_delivery_authorization；本次仅覆盖七篇旧稿重写、B01—B07，不创建copy_confirmation或direct_shoot。源数据、任务原文、旧源和新源哈希均要绑定；其余新稿仍走普通门。

```powershell
python <skill-dir>/scripts/generate_script_docx.py --input <delivery-envelope.json> --registry <正式交付/编号登记.json> --persona <workspace-root>/老板IP内容库/人物设定.json --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl --workspace-root <workspace-root> --output-root <authorized-output-directory>
```

专项交付在同一命令另加--authorization <专项授权.json>。输出目录先按项目要求建立。生成器不覆盖旧文件，按确认的V3字体与加粗规则排版。完整性、授权和编号通过后，实际打开Word、渲染全部页面、逐页查看并核对每句对白及标题编号版本，才能交付。不能仅凭文件存在或结构测试宣称完成。生成Word不授权发布、提交或清理旧资料。
