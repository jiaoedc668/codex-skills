---
name: boss-ip-video-script-writer
description: Use when 为发哥老板IP创作或优化抖音、视频号自然流量剧情、口播、标题、发布介绍，参考续写或制作确认后的Word；不用于商品口播、千川广告或直播带货。
metadata:
  version: "1.4.0"
---

# Boss IP Video Script Writer

## 创作最高原则

**老板 IP 不是负责讲大道理，而是负责帮普通人把一件复杂的事想明白。** 发哥的可信度来自听事实、抓关键、看清成本与选择；家庭、婚姻、养老也遵守这个定位，不把他写成情感导师或咨询师。

本 Skill 首先是短视频创作工具，其次才是流程和数据管理工具。新稿优先级固定为：

**观众愿意继续看 > 人物像真人 > 冲突与观点成立 > 人物与事实边界安全 > schema、时长及流程完整。**

人物与事实安全始终是硬约束，用户核心立场不得擅改；上述顺序不是越界许可。发哥人物成立要体现在具体反应和判断中。流程规则不得以牺牲停留感、人物真实感和故事张力为代价。机器校验用于发现越界、缺失和历史重复，只给 INTEGRITY PASS/FAIL，不负责判断一篇稿是否好看，也不代替谢总判断共鸣、可拍或满意。

结构完整但平淡，仍属于创作失败；schema 完整但角色像作者传声筒，也属于创作失败。发哥不能只承担“正确答案输出者”的功能，他需要有听、问、误判、停顿、被反驳以及调整判断的过程；按事件自然发生，不逐项凑齐。

**不要为了证明完成了创作流程，而牺牲一篇稿本来可以拥有的生命力。流程负责约束创作，不负责代替创作。**

新生产保留 schema v6，默认剧情 story，可指定单人口播 monologue、话题 topic 和核心观点 core_viewpoint。

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

创作时人物模型、选题台账、旧草稿和旧交付只读；用户明确授权维护人物时按人物版本规则迁移。反馈台账只追加有真实用户反馈依据的事件，user_quote保留原话，系统提炼机制另放preserve并标明来源，不把选中、生成Word和可拍评价互相代换。新建运行目录前在项目AGENTS补用途、命名和清理规则。

另读取可配置状态根下的 `shared-creative-preferences.jsonl`，只采用用户明确给出的跨内容抽象偏好，例如开头是否直接、表达是否说教。不得从这里读取或写入人设、题材规则、固定文案、产品事实或未明说的推断。默认共享状态根为 `<workspace-root>/产品视频内容库`；项目或用户指定其他路径时，两个 Skill 必须指向同一文件。

```powershell
python <skill-dir>/scripts/history_manager.py recent-shared-preferences --shared-ledger <shared-state-root>/shared-creative-preferences.jsonl --limit 12
python <skill-dir>/scripts/history_manager.py record-shared-preference --input <explicit-shared-event.json> --shared-ledger <shared-state-root>/shared-creative-preferences.jsonl
```

需要更新普通 ChatGPT Chat 可读的公开状态时，明确指定本地业务文件和共享状态文件，只运行以下只读输入、白名单输出的同步器：

```powershell
python <skill-dir>/scripts/sync_public_context.py --persona <business-root>/人物设定.json --feedback-ledger <business-root>/反馈台账.jsonl --topic-ledger <business-root>/选题台账.jsonl --shared-ledger <shared-root>/shared-creative-preferences.jsonl --output-dir <skill-dir>/chat-context
```

同步器不得把 `user_quote`、内部路径、完整稿件、研究正文、认证信息或可识别敏感信息写入 `chat-context/`；失败时保留已有快照。

共享事件必须使用 `schema_version: 1`、全局唯一 `event_id`、`event_type: creative_preference`、`occurred_at`、`product_id`、非空 `user_quote`，以及含 `source_skill` 和 `preference` 的 `payload`。只追加，不覆盖；损坏事件、重复 ID 或缺少原话时拒绝写入。

## 1 输入与形式

输入可只给形式、话题或观点中的任意项；未给形式就是story。没给话题和观点时，作者从具体事件及人物损失寻找题目，不向用户追问空泛参数。用户给了方向就围绕该方向创作；笼统观点可深化，结构化时在brief记录原话、深化结论及理由，不改变原方向。

- story为剧情，约60秒、尽量90秒内。朋友或同事讲自己的事，发哥追问、分析、批评或建议，由当事人决定和行动，可以停在可执行下一步。
- monologue为口播，约30秒、尽量45秒内。全篇仅发哥说话；主题是人生原则、人品价值或处世智慧，小事只作论据。首句用强判断、反常识或悬念抢停留，再用2至4个不重复理由、对照或例证说透，回应现实反驳，最后用前文托得住的走心判断收尾。

时长估算办法见references/writing-style.md，估算不等于实际表演时长；长短由谢总看稿后的明确反馈校准。历史direct_dialogue_30的“30 秒稿”和light_story_60的“60 秒稿”仍按schema v5读取，旧双人对话不能改标单人口播，旧验收不继承为口播成绩。

## 2 题目判断 → Raw Draft → Creative Review

先读 references/research-and-adaptation.md，判断题目是否涉及热点、新闻、政策法规、真实人物或机构、平台实时趋势、具体真实数据，或用户明确要求研究、仿写近期爆款。这些任务必须通过 web-access 联网研究和事实核验；来源不足时停止依赖该事实的创作，不伪造证据。普通婚姻、家庭、养老、职场、人情、中年、子女、代际、创业认知和人生选择等常青虚构剧情，不因缺少3条10万赞原作或平台热度证据停止创作。高互动原作只是可选表达增强，研究与原创边界见该参考。

正式结构化之前必须先自由创作一次 Raw Draft。此时不写 schema、不填 JSON、不为通过 integrity check 编对白；作者首先只解决故事本身。读 story-engine.md 和 writing-style.md，并从近期反馈的 keep/preserve 选择适用于本题的有效机制来试用，不照抄旧情节，不把 avoid 当作题材封锁表。

剧情同时读 [现役创作校准](references/creative-quality-calibration.md)：Raw Draft 就寻找冲突方那句真实、刺耳且有现实动机的原话；开场通常在1～2个来回内出现人物与异常行为、损失或冲突。大白话承载故事，传播句从交锋里长出来，不在写完后硬补。

Raw Draft 用自然对白与必要动作回答：谁在吃亏、受委屈或承担损失？对方具体做了什么？哪句话最容易触发情绪？反方现实中为什么仍会坚持？哪条新信息使发哥改变或细化判断？最后谁需要决定？他的下一步发生了什么变化？答不自然就重搭故事，不能补字段掩盖。口播对应检查开场、现实反驳、被忽略的一层和听众可改变的选择，不硬造第二角色。

Creative Review 先按“前3秒测试”、演员口语和事件内生结尾通读，再问：我为什么继续看？谁让我生气、心疼或好奇？双方为什么都不愿退？发哥说出了哪层别人没有说出的东西？最后谁的下一步变了？逻辑对但不像人话、现场不会说或只替作者解释主题的句子，重写、删除或改成行为。详见 references/semantic-review.md。不设评分字段，也不把这轮审读做成程序对象或新表格。Raw Draft 留在内部，不进入最终公开输出。

去作者感、去导师感是核心判废条件：完整分析连续接力、教程接管故事、朋友只递问题并迅速被说服时，回到对白重写。多篇还须做 batch Creative Review，比开场发动、信息揭示、判断时机、认同程度、停止位置与收尾；题材不同不代表推进不同。不设结构配额，不能只改首句假装异质化。标题按 writing-style.md 做冲突压缩。全部属于模型语义审读，不新增 schema 或机器质量门。

## 3 结构化与正式候选

**schema 用来描述已经成立的故事，不允许 schema 反过来生成故事。** Creative Review 后再读 content-strategy.md 与 candidate-batch-schema.md，把已成立的草稿整理为选题池、brief、creative_blueprint 和正式 script；蓝图是此时的结构描述，不声称它先于 Raw Draft。发现结构缺口回到故事修订。

建立v6选题池，顶层 `viral_expression_samples` 仅保存真实核验且适用的原作及机制，没有则为空数组，不凑数量。同时保留适用证据、否决理由和成对比较，production_case用stakeholder_cost记录当事人代价。默认正好选三题；用户当轮明确指定数量时按指定数量，不设形式或母题配额。

选题确定前必须做批内语义差异审读，逐条列出主角身份、对立关系、核心损失、冲突因果和发哥裁决/出口五项。任意两条有三项相同或近义，就视为同题换皮并退回选题阶段；不能靠更换金额、亲属称谓、地点或道具伪造差异。机器文字查重通过不能替代这项人工审读。

```powershell
python <skill-dir>/scripts/select_topics.py --input <topic-pool.json>
python <skill-dir>/scripts/history_manager.py recent-feedback --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl --limit 12
```

选中集合通过后组装结构化brief；这不是开始 Raw Draft 的许可门。以下参数按需添加，省略format为剧情；输出文件必须是新路径。

```powershell
python <skill-dir>/scripts/create_candidate.py prepare --topic-pool <topic-pool.json> --topic-id <selected-topic-id> --output <brief.json>
python <skill-dir>/scripts/create_candidate.py prepare --topic-pool <topic-pool.json> --topic-id <selected-topic-id> --format monologue --topic <用户话题> --core-viewpoint <用户观点> --output <brief.json>
```

深化笼统观点时另给--refined-core-viewpoint和--direction-rationale，并人工核对原方向未变。brief从选中题取得研究证据及topic_decision，保留原输入和推导结论。这个命令组装任务，不自动创作对白。

蓝图描述原理解、漏算因素及改变判断的依据；故事丰富来自处境、委屈、选择与后果，不来自重复解释。剧情发哥原则上最多保留一次较完整的观点输出，其余优先追问、短判断、停顿或改口，不默认第一句就知道全部答案。

发哥可以直接反驳做错事的人，但在对白、动作、镜头、前史里均不能是事件参与者、介绍人、安排者或代办人；不能替人借款、招聘、催债、联系中介、调班或落实家务。建议须回应眼前难题，由当事人承担决定和行动。标题强化的冲突必须有正文支持，不泛化攻击性别群体。

作者先对完整稿做下述真人语义审读，通过后用brief组装v6候选，再运行以下完整性检查。新候选在script中同时写theme与title：theme是题材，title是面向观众的成片标题。输入文件不覆盖；输出必须新建。

```powershell
python <skill-dir>/scripts/create_candidate.py assemble --brief <brief.json> --input <authored.json> --persona <workspace-root>/老板IP内容库/人物设定.json --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl --output <candidate.json>
python <skill-dir>/scripts/check_candidate_integrity.py --input <candidate.json> --persona <workspace-root>/老板IP内容库/人物设定.json --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl
python <skill-dir>/scripts/check_content_similarity.py --input <candidate.json> --ledger <workspace-root>/老板IP内容库/选题台账.jsonl
python <skill-dir>/scripts/check_batch_integrity.py --inputs <candidate-1.json> <candidate-2.json> <candidate-3.json> --topic-pool <topic-pool.json> --persona <workspace-root>/老板IP内容库/人物设定.json --feedback-ledger <workspace-root>/老板IP内容库/反馈台账.jsonl
```

正式候选生成前再做真人优先语义审读：这个人会这么说吗？人在这个情绪里会这样说吗？是否作者借人物的嘴总结？是在解决当前问题，还是给观众解释主题？先审人话再审逻辑。标题＋前两句至少具备明确人物、具体行为、具体损失、明显不公平、明显反常识、让人想反驳的话中的两项，并能明确回答“观众现在最想知道什么”；正文兑现这个问题。逐篇通读对白、动作、镜头、前史和现实出口，人物边界不能靠关键词通过代替。口播仍审主题与论据关联。未通过留在内部修订；通过后才运行 Schema / Integrity Check，上列命令不构成创作质量证明。

## 4 展示与反馈

用户说“好”“不错”“这版比之前好”“就按这个方向”时，用candidate_feedback保留原话，并在preserve提炼有本稿依据的有效机制，标为“系统提炼（待复验）”；不冒充用户逐项肯定，也不升级为direct_shoot。明确“可拍”才记录对应正式评价。新稿实际试用keep机制，不能只累计avoid；详细合同见references/feedback-loop.md。

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
