# 显式反馈与双形式跟踪

老板IP内容库/反馈台账.jsonl只追加有真实用户反馈依据的事件，旧字节不可改写。user_quote保存用户原话，系统提炼另放preserve，不得冒充用户点名肯定的机制。沉默、猜测、机器通过、生成Word均不能转为人工质量评价。

## 事件
沿用schema2事件与history_manager.py校验，新v6事件增加format=story或monologue；历史事件不回填形式。
- candidate_selection只表示选中，含batch_id/candidate_id/user_quote。
- candidate_feedback绑定batch_id/candidate_id/当前revision_id，复用preserve/avoid记录未达到正式评价语义的反馈，不含evaluation，不表示选中、可拍或文案确认；例如“好”“不错”“这版比之前好”“就按这个方向”。
- candidate_evaluation绑定当前revision_id，evaluation仅direct_shoot/minor_revision/major_revision/rejected；evaluation、reason_codes和avoid必须有明确反馈依据，preserve可分别记录用户明确指出的优点和标明来源的系统提炼。
- candidate_length_evaluation只记录too_short/appropriate/too_long，不改变可拍数量。
- copy_confirmation绑定当前revision_id和完整candidate_doc的content_sha256，不等于可拍。
- revision记录from_revision/to_revision/changes与原话，不覆盖旧稿。
- publication_metrics只用用户提供的source/data_date/metrics，不推断传播效果。

只有“不行”时记淘汰，原因待明，不擅自把题材或人物关系列为禁区。允许精修或Word不能替代copy_confirmation，明确专项Word授权走独立文件而非虚构反馈事件。

## 读取与写入
使用history_manager.py recent-feedback读取近期投影，record-feedback追加单事件；反馈上下文与候选必须一致。原事件JSON保存用户原话，再调用现成校验器，不能手改账本内容。

## 正向机制要实际复用

用户明确说“好”“不错”“这版比之前好”“可拍”“就按这个方向”时，不能只记accepted或选中。结合被评价的当前完整稿提炼可复用机制，放入已有preserve数组，不新增effective_mechanisms或评分字段。泛认可用candidate_feedback；明确说可拍才用candidate_evaluation的direct_shoot；只有选中则仍只记candidate_selection，不自动推断质量认可。

user_quote保持原话，preserve中系统推断统一写成“系统提炼（待复验）：具体行为冲突有效，稿中……”。只有用户确实点名了机制，才能写“用户明确肯定：……”。不要补造用户没说过的引语。系统提炼是基于本稿的创作假设，不能说成用户逐项确认，也不自动上升为永久规则；缺少被评价稿时保留原话并标明机制待补，不凭空提炼。

优先提炼“具体行为冲突有效”“反方一句符合身份的刺耳原话有效”“发哥先追问再判断有效”“用具体矛盾拆穿问题有效”“结尾直接回收当前冲突有效”等有本稿证据的机制。不要保存固定台词供下一篇照搬，不要因为本次认可就忽略人物和事实边界。

recent-feedback把preserve投影为candidate_context.keep。新稿题目判断与Raw Draft前先读keep，选择适合当前故事的机制实际使用；Creative Review回看它是否带来真人感和推进，不能只把keep复制进候选字段。avoid只用于已明确的问题，不从一次失败扩张成题材或人物禁区；新稿既复用有效机制，也检查真实禁忌，防止越学越保守。

新增candidate_feedback仍用事件schema2，旧事件无需迁移或回填；反馈读取与keep/avoid投影兼容，正式评价和验收状态仍只统计candidate_evaluation。系统不得自行补写历史好评、修正原台账或把泛认可升级为可拍。

## v6状态
schema2 manifest绑定format、batch_id、submitted_at、候选candidate_id/revision_id与可证伪root_cause。默认三份，用户指定数量时记录实际集合并遵循现有状态机合同；不能补造候选凑数。acceptance_state.py对新manifest调用format_acceptance，仅统计同批同形式当前修订的显式评价；旧v5事件和成绩不能自动继承为口播通过。

剧情与口播分别跟踪。全部三份评价前保持pending；至少两份direct_shoot才是这一批的用户通过，不代表未来稿稳定可拍。未通过须保留失败稿改变根因，同根因连续三次失败推倒方法；同形式退步标注回退需要，记录比较。

上段是默认三条的批次标准。指定非三条时manifest显式写requested_candidate_count，未评完保持pending；评完标user_reviewed_custom_batch，逐条保留真实结果，不称三条批次通过，也不并入默认三条的退步比较和失败次数。需要怎样继续按用户反馈决定，不自动凑三条或外推通过阈值。

用户明确只改某条或某段时，优先限定修订，不自动重做其他已认可正文。初稿与修订结果分别报告，不能将精修通过倒写为初稿成功。新候选通常展示后等逐条评价；明确专项交付授权不因没有新版人类评分阻塞授权范围内的交付，也不代填评价。

历史schema1 manifest继续使用原v5状态机读取；不要把新旧manifest混在同一次新形式统计。人工认可只由真实用户事件支持，生成器与审稿器不能自行追加。
