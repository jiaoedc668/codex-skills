from __future__ import annotations

import copy


def valid_persona() -> dict:
    return {
        "schema_version": 3,
        "identity": {
            "display_name": "发哥",
            "age_band": "40+",
            "audience": "40+泛人群",
            "fiction_status": "授权虚构人设",
        },
        "viewpoint_principles": [
            {
                "id": "P01",
                "status": "active",
                "active_version": 1,
                "versions": [
                    {
                        "version": 1,
                        "tension": "制度与人情",
                        "default_choice": "先守规则，再为真实困难做可说明的调整",
                        "rejected_choice": "公司替员工家庭作最终决定",
                        "exceptions": ["眼前存在可核实的人身安全风险"],
                        "cost": "发哥或公司承担眼前排班麻烦",
                        "source_candidate_id": "baseline-persona",
                        "reason": "从既有价值取舍迁移",
                    }
                ],
            }
        ],
        "fictional_continuity": [],
        "forbidden_biography_patterns": [
            "我女儿",
            "我儿子",
            "我妻子",
            "我当年负债",
            "我创业时",
        ],
    }


def valid_principle_revision() -> dict:
    return {
        "schema_version": 1,
        "event_type": "viewpoint_principle",
        "operation": "revise",
        "record_id": "P01",
        "source_candidate_id": "batch-persona-test-c1",
        "reason": "明确反馈要求把救急边界说清楚",
        "record": {
            "tension": "制度与人情",
            "default_choice": "先核实急事，再把公司责任与个人帮助分开",
            "rejected_choice": "公司或老板替当事人承担全部家庭责任",
            "exceptions": ["眼前存在可核实的人身安全风险"],
            "cost": "发哥承担个人帮助的风险，也接受对方不感恩",
        },
    }


def valid_source(source_date: str = "2026-09-03", suffix: str = "source") -> dict:
    return {
        "title": f"测试来源 {suffix}",
        "url": f"https://example.com/{suffix}",
        "source_date": source_date,
        "retrieved_at": "2026-09-04",
        "supports": "支持当前议题中可核验的具体事实",
        "limits": "测试夹具不代表生产研究或真实热度",
    }


def _current_evidence(suffix: str) -> dict:
    return {
        "fact_sources": [valid_source("2026-09-02", f"fact-{suffix}")],
        "heat_signals": [valid_source("2026-09-03", f"heat-{suffix}")],
    }


def _evergreen_evidence(suffix: str) -> dict:
    high_interaction = valid_source("2026-07-01", f"interaction-{suffix}")
    high_interaction["visible_interaction"] = "页面公开显示10万次点赞"
    return {
        "fact_sources": [valid_source("2026-08-20", f"fact-{suffix}")],
        "recurrence_sources": [
            valid_source("2026-01-01", f"recurrence-old-{suffix}"),
            valid_source("2026-07-01", f"recurrence-new-{suffix}"),
        ],
        "high_interaction_sources": [high_interaction],
    }


def _production_case(index: int) -> dict:
    variants = {
        1: {
            "audience_stake": "中年家庭同时面对医疗支出和房贷现金流",
            "concrete_event": "员工当晚要补齐父亲住院押金",
            "concrete_anchor": "押金还差两万元",
            "strongest_counterargument": "公司不能凭口头困难替员工家庭兜底",
            "fage_choice": "公司预支一万，发哥个人借一万并写借条",
            "fage_cost": "发哥承担一万元个人借款风险",
            "ending_consequence": "员工当天保住床位并承担还款责任",
            "audience_response_space": "观众可以争论老板该帮到哪一步",
        },
        2: {
            "audience_stake": "父母养老资金与子女住房压力发生正面冲突",
            "concrete_event": "母亲准备卖掉唯一住房替儿子补首付",
            "concrete_anchor": "卖房后每月租金三千元",
            "strongest_counterargument": "父母自愿处置房产也有帮助子女的权利",
            "fage_choice": "先算十年租金，再决定只支持可承受的一部分",
            "fage_cost": "发哥承认自己无权替母亲决定并暂停劝说",
            "ending_consequence": "母亲收回当天签约决定并带账单回家讨论",
            "audience_response_space": "观众可以争论父母的钱是否应优先养老",
        },
        3: {
            "audience_stake": "四十岁失业者在收入和体面之间必须立刻选择",
            "concrete_event": "朋友瞒着家人去做夜班分拣",
            "concrete_anchor": "试岗一晚能拿三百元",
            "strongest_counterargument": "暂时隐瞒能避免家人焦虑和无谓争执",
            "fage_choice": "先去试岗，但当天把收入和风险告诉家人",
            "fage_cost": "发哥陪朋友跑一趟并承担劝错的关系压力",
            "ending_consequence": "朋友发出消息后走进试岗仓库",
            "audience_response_space": "观众可以争论失业后该不该向家人坦白",
        },
        4: {
            "audience_stake": "子女照护责任与中年人的工作稳定互相挤压",
            "concrete_event": "姐姐要求弟弟辞职回家照顾父亲",
            "concrete_anchor": "护理费每月六千元",
            "strongest_counterargument": "谁离家近，谁就应该先承担照护",
            "fage_choice": "先按时间和钱拆分责任，不让一人退出工作",
            "fage_cost": "发哥放弃替朋友站队并承担双方不满意",
            "ending_consequence": "姐弟在当天排出首月轮班和费用表",
            "audience_response_space": "观众可以补充自己家如何分担养老",
        },
    }
    return copy.deepcopy(variants[index])


def valid_topic_pool(with_unselected: bool = False) -> dict:
    titles = {
        1: "员工家里急用钱，公司该帮到哪一步",
        2: "父母卖房给子女首付，要先算哪笔账",
        3: "四十岁失业后，要不要先瞒着家人",
        4: "照顾老人，能不能只让离家近的人辞职",
    }
    kinds = {1: "current_issue", 2: "evergreen", 3: "current_issue", 4: "evergreen"}
    categories = {
        1: "money_housing_pension_family",
        2: "money_housing_pension_family",
        3: "midlife_work_business",
        4: "children_intergenerational",
    }
    count = 4 if with_unselected else 3
    prospects = []
    for index in range(1, count + 1):
        evidence = (
            _current_evidence(str(index))
            if kinds[index] == "current_issue"
            else _evergreen_evidence(str(index))
        )
        prospects.append(
            {
                "topic_id": f"topic-{index}",
                "title": titles[index],
                "topic_kind": kinds[index],
                "priority_category": categories[index],
                "research_evidence": evidence,
                "production_case": _production_case(index),
                "veto_reasons": [],
            }
        )

    comparisons = [
        {
            "left_topic_id": "topic-1",
            "right_topic_id": "topic-2",
            "preferred_topic_id": "topic-1",
            "evidence_reason": "两题证据均完整，topic-1 的近期事实更直接",
            "production_reason": "topic-1 的两万元押金能在前两句形成选择",
        },
        {
            "left_topic_id": "topic-1",
            "right_topic_id": "topic-3",
            "preferred_topic_id": "topic-3",
            "evidence_reason": "两题均有近七日信号，topic-3 的讨论边界更清楚",
            "production_reason": "topic-3 的坦白动作能在单场景落地",
        },
        {
            "left_topic_id": "topic-2",
            "right_topic_id": "topic-3",
            "preferred_topic_id": "topic-2",
            "evidence_reason": "topic-2 同时具备跨期复现和公开互动证据",
            "production_reason": "卖房与十年租金形成可见的具体账",
        },
    ]
    if with_unselected:
        comparisons.extend(
            [
                {
                    "left_topic_id": "topic-1",
                    "right_topic_id": "topic-4",
                    "preferred_topic_id": "topic-1",
                    "evidence_reason": "topic-1 的近期证据比 topic-4 更接近当前事件",
                    "production_reason": "两万元押金比泛化照护安排更快进入冲突",
                },
                {
                    "left_topic_id": "topic-2",
                    "right_topic_id": "topic-4",
                    "preferred_topic_id": "topic-2",
                    "evidence_reason": "topic-2 的跨期来源和互动证据更完整",
                    "production_reason": "卖房决定具有不可撤回后果",
                },
                {
                    "left_topic_id": "topic-3",
                    "right_topic_id": "topic-4",
                    "preferred_topic_id": "topic-3",
                    "evidence_reason": "topic-3 有近七日公开讨论信号",
                    "production_reason": "试岗和发消息构成当场可拍动作",
                },
            ]
        )
    return {
        "schema_version": 5,
        "pool_id": "pool-20260904-direct-01",
        "requested_candidate_count": 3,
        "prospects": prospects,
        "pairwise_decisions": comparisons,
        "selected_topic_ids": ["topic-1", "topic-2", "topic-3"],
    }


def valid_direct_manifest(
    sequence: int = 1,
    *,
    root_cause_id: str | None = None,
) -> dict:
    batch_id = f"batch-20260904-direct-{sequence:02d}"
    return {
        "schema_version": 1,
        "batch_id": batch_id,
        "duration_mode": "direct_dialogue_30",
        "candidate_ids": [f"{batch_id}-c{index}" for index in (1, 2, 3)],
        "submitted_at": f"2026-09-04T{17 + sequence:02d}:00:00+08:00",
        "supersedes_batch_id": (
            "无" if sequence == 1 else f"batch-20260904-direct-{sequence - 1:02d}"
        ),
        "root_cause": {
            "id": root_cause_id or f"RC{sequence:02d}",
            "hypothesis": "前两句的具体利害仍不够清楚",
            "changed_layer": "opening_event",
            "root_level_change": False,
        },
    }


def valid_story_manifest(sequence: int = 1) -> dict:
    batch_id = f"batch-20260904-story-{sequence:02d}"
    return {
        "schema_version": 1,
        "batch_id": batch_id,
        "duration_mode": "light_story_60",
        "candidate_ids": [f"{batch_id}-c{index}" for index in (1, 2, 3)],
        "submitted_at": f"2026-09-04T{20 + sequence:02d}:00:00+08:00",
        "supersedes_batch_id": "无",
        "root_cause": {
            "id": f"RS{sequence:02d}",
            "hypothesis": "新证据出现后还没有改变人物行动",
            "changed_layer": "turning_information",
            "root_level_change": False,
        },
    }


def valid_direct_candidate() -> dict:
    candidate = {
        "schema_version": 5,
        "candidate": {
            "batch_id": "batch-20260904-direct-01",
            "candidate_id": "batch-20260904-direct-01-c1",
            "position": 1,
            "revision_id": "r1",
            "evaluation_status": "awaiting_user_evaluation",
        },
        "duration_mode": "direct_dialogue_30",
        "research_evidence": {
            "topic_kind": "current_issue",
            "sources": [
                {
                    "title": "测试用公开议题来源",
                    "url": "https://example.com/topic-1",
                    "source_date": "2026-09-03",
                    "retrieved_at": "2026-09-04",
                    "supports": "医院押金与家庭现金流形成现实两难",
                    "limits": "测试夹具不声称真实热度",
                }
            ],
            "heat_signals": [
                {
                    "title": "测试用互动证据",
                    "url": "https://example.com/heat-1",
                    "source_date": "2026-09-03",
                    "retrieved_at": "2026-09-04",
                    "supports": "该议题近期有人公开讨论",
                    "limits": "测试夹具不代表生产研究",
                }
            ],
        },
        "topic_decision": {
            "pool_id": "pool-20260904-direct-01",
            "topic_id": "topic-1",
            "priority_category": "money_housing_pension_family",
            "concrete_event": "员工当晚要补齐父亲住院押金",
            "concrete_anchor": "押金还差两万元",
            "audience_stake": "中年家庭同时面对医疗支出和房贷现金流",
            "strongest_counterargument": "公司不能凭口头困难替员工家庭兜底",
            "fage_choice": "公司预支一万，发哥个人借一万并写借条",
            "fage_cost": "发哥承担一万元个人借款风险",
            "ending_consequence": "员工当天保住床位并承担还款责任",
            "audience_response_space": "观众可以争论老板该帮到哪一步",
        },
        "conflict_blueprint": {
            "immediate_wants": [
                {"party": "员工", "want": "今晚凑齐住院押金", "line_ids": ["L1", "L3"]},
                {"party": "发哥", "want": "救急但不让公司替家庭兜底", "line_ids": ["L2", "L8"]},
            ],
            "strongest_counterargument": {
                "speaker": "员工",
                "argument": "预支工资会让下个月现金流更紧",
                "survives_after_judgment": True,
                "line_ids": ["L3", "L7"],
            },
            "fage_judgment": {
                "decision": "公司预支一万，发哥个人借一万并写借条",
                "rejected_option": "公司无条件承担全部两万元",
                "cost": "发哥承担个人借款风险",
                "line_ids": ["L6", "L8"],
            },
            "turning_information": {
                "new_information": "员工已经挪用一万元房贷钱",
                "before_action": "员工请求公司借出全部两万元",
                "after_action": "双方把救急款拆成工资预支和个人借款",
                "line_ids": ["L4", "L5", "L6"],
            },
        },
        "persona_continuity": {
            "principle_id": "P01",
            "principle_version": 1,
            "use_mode": "follow",
            "use_explanation": "先核实眼前风险，再让双方各自承担可说明的代价",
            "continuity_refs": [],
        },
        "script": {
            "theme": "员工家里急用钱，公司该帮到哪一步",
            "secondary_theme": "无",
            "lines": [
                {"line_id": "L1", "speaker": "员工", "text": "发哥，我爸住院押金还差两万，公司能不能先借我？", "dialogue_act": "request"},
                {"line_id": "L2", "speaker": "发哥", "text": "公司不能替你家做决定，这两万也不能只凭一句着急批出去。", "dialogue_act": "refuse"},
                {"line_id": "L3", "speaker": "员工", "text": "可我今晚不交，床位就保不住；我不是来占便宜。", "dialogue_act": "push_back"},
                {"line_id": "L4", "speaker": "发哥", "text": "把医院缴费单和你家能承担的数给我看。", "dialogue_act": "request"},
                {"line_id": "L5", "speaker": "员工", "text": "单子是真的，但我没告诉家里，我把房贷钱先垫了一万。", "dialogue_act": "conceal"},
                {"line_id": "L6", "speaker": "发哥", "text": "那先别碰下月房贷，公司预支一万，我个人再借你一万。", "dialogue_act": "decide"},
                {"line_id": "L7", "speaker": "员工", "text": "预支以后我下个月更紧，这个窟窿还是我的。", "dialogue_act": "push_back"},
                {"line_id": "L8", "speaker": "发哥", "text": "所以两笔都写清楚；你今天保床位，下周把还款安排给我。", "dialogue_act": "decide"},
            ],
            "key_actions": [
                {
                    "action_id": "A1",
                    "after_line_id": "L4",
                    "action": "员工把医院缴费单推到发哥面前",
                    "consequence": "口头求助变成可核实的眼前急事",
                },
                {
                    "action_id": "A2",
                    "after_line_id": "L8",
                    "action": "发哥把工资预支单和个人借条分开放好",
                    "consequence": "员工当天能交押金，同时留下还款责任",
                },
            ],
            "necessary_shots": ["医院缴费单金额特写", "工资预支单与个人借条分开入镜"],
            "state_changes": [
                {
                    "after_line_id": "L2",
                    "line_ids": ["L1", "L2"],
                    "kind": "choice",
                    "before": "员工等公司直接借出两万元",
                    "after": "发哥拒绝只凭口头批钱",
                },
                {
                    "after_line_id": "L5",
                    "line_ids": ["L3", "L4", "L5"],
                    "kind": "fact",
                    "before": "发哥只知道押金短缺",
                    "after": "双方知道员工已经动用房贷钱",
                },
                {
                    "after_line_id": "L8",
                    "line_ids": ["L6", "L7", "L8"],
                    "kind": "choice",
                    "before": "员工担心工资预支把困难推到下月",
                    "after": "救急款被拆分并写清两种责任",
                },
            ],
            "ending": {
                "after_line_id": "L8",
                "kind": "action",
                "consequence": "员工当天保住床位并约定下周交还款安排",
            },
            "mode_contract": {
                "dilemma_count": 1,
                "judgment_count": 1,
                "turning_evidence_line_id": "L5",
                "result_action_id": "A2",
            },
        },
        "feedback_context": {
            "latest_feedback_ids": [],
            "keep": ["无"],
            "avoid": ["无"],
            "length_feedback": [],
            "publication_data": "无用户提供的发布数据",
        },
    }
    return copy.deepcopy(candidate)


def _retarget_direct_candidate(index: int) -> dict:
    data = valid_direct_candidate()
    case = _production_case(index)
    categories = {
        2: "money_housing_pension_family",
        3: "midlife_work_business",
    }
    titles = {
        2: "父母卖房给子女首付，要先算哪笔账",
        3: "四十岁失业后，要不要先瞒着家人",
    }
    data["candidate"].update(
        {
            "candidate_id": f"batch-20260904-direct-01-c{index}",
            "position": index,
        }
    )
    data["research_evidence"] = {
        "topic_kind": "evergreen" if index == 2 else "current_issue",
        **(
            _evergreen_evidence(str(index))
            if index == 2
            else _current_evidence(str(index))
        ),
    }
    data["topic_decision"] = {
        "pool_id": "pool-20260904-direct-01",
        "topic_id": f"topic-{index}",
        "priority_category": categories[index],
        "concrete_event": case["concrete_event"],
        "concrete_anchor": case["concrete_anchor"],
        "audience_stake": case["audience_stake"],
        "strongest_counterargument": case["strongest_counterargument"],
        "fage_choice": case["fage_choice"],
        "fage_cost": case["fage_cost"],
        "ending_consequence": case["ending_consequence"],
        "audience_response_space": case["audience_response_space"],
    }
    data["script"]["theme"] = titles[index]

    if index == 2:
        data["conflict_blueprint"] = {
            "immediate_wants": [
                {
                    "party": "朋友",
                    "want": "请发哥支持母亲当天卖房补首付",
                    "line_ids": ["L1", "L5"],
                },
                {
                    "party": "发哥",
                    "want": "先保住母亲未来十年的住处和养老钱",
                    "line_ids": ["L2", "L8"],
                },
            ],
            "strongest_counterargument": {
                "speaker": "朋友",
                "argument": "母亲自愿处分房产，错过当前房源也有真实代价",
                "survives_after_judgment": True,
                "line_ids": ["L3", "L5", "L7"],
            },
            "fage_judgment": {
                "decision": "当天不签，先把十年租金和养老费用写成一张表",
                "rejected_option": "直接禁止母亲卖房",
                "cost": "发哥承认自己无权替母亲决定并承担朋友的不满",
                "line_ids": ["L6", "L8"],
            },
            "turning_information": {
                "new_information": "卖房后每月租金三千元，十年就是三十六万元",
                "before_action": "朋友准备当天带母亲签约",
                "after_action": "朋友先带合同和费用表回家讨论",
                "line_ids": ["L2", "L3", "L8"],
            },
        }
        data["script"].update(
            {
                "lines": [
                    {"line_id": "L1", "speaker": "朋友", "text": "发哥，我妈今天要卖房给我补首付，你替我劝她赶紧签。", "dialogue_act": "request"},
                    {"line_id": "L2", "speaker": "发哥", "text": "她卖完住哪？", "dialogue_act": "request"},
                    {"line_id": "L3", "speaker": "朋友", "text": "租房，一个月三千；我现在不上车，以后更贵。", "dialogue_act": "push_back"},
                    {"line_id": "L4", "speaker": "发哥", "text": "十年租金三十六万，这笔账不能藏在首付后面。", "dialogue_act": "refuse"},
                    {"line_id": "L5", "speaker": "朋友", "text": "可她自己愿意，我少这笔钱就买不上。", "dialogue_act": "push_back"},
                    {"line_id": "L6", "speaker": "发哥", "text": "愿意也得先留下她住和看病的钱。", "dialogue_act": "decide"},
                    {"line_id": "L7", "speaker": "朋友", "text": "你一句不卖容易，我错过这套房谁补？", "dialogue_act": "save_face"},
                    {"line_id": "L8", "speaker": "发哥", "text": "我不替她决定。合同先带回去，今晚把十年租金和养老费写一张表。", "dialogue_act": "decide"},
                ],
                "key_actions": [
                    {
                        "action_id": "A1",
                        "after_line_id": "L3",
                        "action": "发哥在纸上写下三千乘一百二十",
                        "consequence": "卖房后的长期租金第一次出现在桌面上",
                    },
                    {
                        "action_id": "A2",
                        "after_line_id": "L8",
                        "action": "朋友收回合同，拿起租金养老费用表",
                        "consequence": "当天签约暂停，决定带着完整账单回家讨论",
                    },
                ],
                "necessary_shots": ["卖房合同封面", "三千乘一百二十的手写费用表"],
                "state_changes": [
                    {
                        "after_line_id": "L2",
                        "line_ids": ["L1", "L2"],
                        "kind": "choice",
                        "before": "朋友只等发哥支持当天签约",
                        "after": "发哥先追问卖房后的住处",
                    },
                    {
                        "after_line_id": "L5",
                        "line_ids": ["L3", "L4", "L5"],
                        "kind": "fact",
                        "before": "首付缺口是桌上唯一一笔账",
                        "after": "十年租金与错过房源的代价同时摆上桌",
                    },
                    {
                        "after_line_id": "L8",
                        "line_ids": ["L6", "L7", "L8"],
                        "kind": "choice",
                        "before": "双方争论卖或不卖",
                        "after": "合同暂停，先核算母亲可承受的支持金额",
                    },
                ],
                "ending": {
                    "after_line_id": "L8",
                    "kind": "action",
                    "consequence": "朋友收回当天签约决定并带费用表回家讨论",
                },
                "mode_contract": {
                    "dilemma_count": 1,
                    "judgment_count": 1,
                    "turning_evidence_line_id": "L3",
                    "result_action_id": "A2",
                },
            }
        )
    else:
        data["conflict_blueprint"] = {
            "immediate_wants": [
                {
                    "party": "朋友",
                    "want": "先瞒着家人完成一晚夜班试岗",
                    "line_ids": ["L1", "L3"],
                },
                {
                    "party": "发哥",
                    "want": "让朋友先查清风险并当天把事实告诉家人",
                    "line_ids": ["L2", "L8"],
                },
            ],
            "strongest_counterargument": {
                "speaker": "朋友",
                "argument": "暂时隐瞒能避免家人在结果确定前徒增焦虑",
                "survives_after_judgment": True,
                "line_ids": ["L3", "L7"],
            },
            "fage_judgment": {
                "decision": "可以先试岗，但进门前要把收入和风险发给家人",
                "rejected_option": "替朋友继续隐瞒夜班试岗",
                "cost": "发哥陪朋友跑一趟并承担劝错的关系压力",
                "line_ids": ["L7", "L8"],
            },
            "turning_information": {
                "new_information": "试岗协议写着夜班受伤只按临时劳务处理",
                "before_action": "朋友准备不看协议直接进仓",
                "after_action": "朋友先拍下协议并向家人说明风险",
                "line_ids": ["L4", "L5", "L6"],
            },
        }
        data["script"].update(
            {
                "lines": [
                    {"line_id": "L1", "speaker": "朋友", "text": "发哥，我今晚去仓库试岗，先替我瞒着家里。", "dialogue_act": "request"},
                    {"line_id": "L2", "speaker": "发哥", "text": "工作能试，风险不能替你藏。", "dialogue_act": "refuse"},
                    {"line_id": "L3", "speaker": "朋友", "text": "一晚三百，没做成就别让他们白担心。", "dialogue_act": "push_back"},
                    {"line_id": "L4", "speaker": "朋友", "text": "协议我还没看，反正只是搬货。", "dialogue_act": "conceal"},
                    {"line_id": "L5", "speaker": "发哥", "text": "先把受伤那一条念完。", "dialogue_act": "request"},
                    {"line_id": "L6", "speaker": "朋友", "text": "临时劳务，夜班受伤只按协议处理。", "dialogue_act": "push_back"},
                    {"line_id": "L7", "speaker": "朋友", "text": "我失业还要报备，面子往哪放？", "dialogue_act": "save_face"},
                    {"line_id": "L8", "speaker": "发哥", "text": "面子先放兜里。协议拍给家里，消息发完我陪你进去。", "dialogue_act": "decide"},
                ],
                "key_actions": [
                    {
                        "action_id": "A1",
                        "after_line_id": "L5",
                        "action": "发哥把试岗协议翻到风险条款",
                        "consequence": "一晚三百之外的受伤责任进入选择",
                    },
                    {
                        "action_id": "A2",
                        "after_line_id": "L8",
                        "action": "朋友拍下协议并把消息发给家人",
                        "consequence": "朋友不再隐瞒，随后走进试岗仓库",
                    },
                ],
                "necessary_shots": ["试岗协议风险条款", "消息发送成功后两人走进仓库"],
                "state_changes": [
                    {
                        "after_line_id": "L2",
                        "line_ids": ["L1", "L2"],
                        "kind": "choice",
                        "before": "朋友希望发哥帮忙隐瞒",
                        "after": "发哥拒绝替朋友藏住风险",
                    },
                    {
                        "after_line_id": "L5",
                        "line_ids": ["L3", "L4", "L5"],
                        "kind": "fact",
                        "before": "朋友只看见一晚三百元收入",
                        "after": "协议中的受伤责任必须先查清",
                    },
                    {
                        "after_line_id": "L8",
                        "line_ids": ["L6", "L7", "L8"],
                        "kind": "choice",
                        "before": "朋友在收入、风险和面子间犹豫",
                        "after": "朋友先告知家人，再进入仓库试岗",
                    },
                ],
                "ending": {
                    "after_line_id": "L8",
                    "kind": "action",
                    "consequence": "朋友发出消息后走进试岗仓库",
                },
                "mode_contract": {
                    "dilemma_count": 1,
                    "judgment_count": 1,
                    "turning_evidence_line_id": "L6",
                    "result_action_id": "A2",
                },
            }
        )
    return data


def valid_direct_batch() -> list[dict]:
    return [
        valid_direct_candidate(),
        _retarget_direct_candidate(2),
        _retarget_direct_candidate(3),
    ]


def valid_story_candidate() -> dict:
    data = _retarget_direct_candidate(3)
    data["candidate"].update(
        {
            "batch_id": "batch-20260904-story-01",
            "candidate_id": "batch-20260904-story-01-c1",
            "position": 1,
        }
    )
    data["duration_mode"] = "light_story_60"
    data["conflict_blueprint"]["immediate_wants"][0]["line_ids"] = ["L1", "L3"]
    data["conflict_blueprint"]["immediate_wants"][1]["line_ids"] = ["L2", "L4", "L8"]
    data["conflict_blueprint"]["strongest_counterargument"]["line_ids"] = ["L3", "L7", "L9"]
    data["conflict_blueprint"]["fage_judgment"]["line_ids"] = ["L8", "L10", "L12"]
    data["conflict_blueprint"]["turning_information"]["line_ids"] = ["L4", "L5", "L6"]
    data["script"].update(
        {
            "lines": [
                {"line_id": "L1", "speaker": "朋友", "text": "发哥，我今晚去仓库试岗，先替我瞒着家里。", "dialogue_act": "request"},
                {"line_id": "L2", "speaker": "发哥", "text": "你连做什么都没说，我替你瞒什么？", "dialogue_act": "refuse"},
                {"line_id": "L3", "speaker": "朋友", "text": "夜班分拣，一晚三百，没做成就别让他们白担心。", "dialogue_act": "push_back"},
                {"line_id": "L4", "speaker": "发哥", "text": "可以试，协议先给我看。", "dialogue_act": "request"},
                {"line_id": "L5", "speaker": "朋友", "text": "这条字太小，应该没什么。", "dialogue_act": "conceal"},
                {"line_id": "L6", "speaker": "发哥", "text": "写着夜班受伤只按临时劳务处理。", "dialogue_act": "push_back"},
                {"line_id": "L7", "speaker": "朋友", "text": "那我不去了？可家里这个月还等着钱。", "dialogue_act": "save_face"},
                {"line_id": "L8", "speaker": "发哥", "text": "不替你退，也不替你瞒。先把收入和风险发回去。", "dialogue_act": "decide"},
                {"line_id": "L9", "speaker": "朋友", "text": "字打好了，我怕一发出去，他们觉得我混得太差。", "dialogue_act": "save_face"},
                {"line_id": "L10", "speaker": "发哥", "text": "让家里知道风险，不等于让他们替你丢脸。发。", "dialogue_act": "decide"},
                {"line_id": "L11", "speaker": "朋友", "text": "发了。他们让我注意安全，没拦我。", "dialogue_act": "push_back"},
                {"line_id": "L12", "speaker": "发哥", "text": "走吧，我陪你到门口，明早别硬撑着开车。", "dialogue_act": "decide"},
            ],
            "key_actions": [
                {
                    "action_id": "A1",
                    "after_line_id": "L6",
                    "action": "发哥把试岗协议风险条款圈出来",
                    "consequence": "新证据把是否隐瞒改成是否知情承担风险",
                },
                {
                    "action_id": "A2",
                    "after_line_id": "L12",
                    "action": "朋友展示已发送消息，两人一起走到仓库门口",
                    "consequence": "朋友告知家人后仍去试岗，发哥承担陪同成本",
                },
            ],
            "necessary_shots": ["试岗协议风险条款特写", "消息发送成功与仓库入口同框"],
            "state_changes": [
                {
                    "after_line_id": "L3",
                    "line_ids": ["L1", "L2", "L3"],
                    "kind": "choice",
                    "before": "朋友要求发哥帮忙隐瞒",
                    "after": "发哥拒绝在未知风险下答应，朋友坚持收入的现实压力",
                },
                {
                    "after_line_id": "L6",
                    "line_ids": ["L4", "L5", "L6"],
                    "kind": "fact",
                    "before": "一晚三百是唯一可见筹码",
                    "after": "双方查到夜班受伤责任条款",
                },
                {
                    "after_line_id": "L9",
                    "line_ids": ["L7", "L8", "L9"],
                    "kind": "relationship",
                    "before": "朋友准备不知情地进仓",
                    "after": "朋友接受先告知家人，但仍担心失业损伤尊严",
                },
                {
                    "after_line_id": "L12",
                    "line_ids": ["L10", "L11", "L12"],
                    "kind": "choice",
                    "before": "朋友仍未告诉家人",
                    "after": "朋友发出消息并在发哥陪同下进入试岗",
                },
            ],
            "ending": {
                "after_line_id": "L12",
                "kind": "action",
                "consequence": "朋友告知家人后走进试岗仓库，发哥陪到门口",
            },
            "mode_contract": {
                "dilemma_count": 1,
                "judgment_count": 1,
                "turning_evidence_line_id": "L6",
                "result_action_id": "A2",
            },
        }
    )
    return data
