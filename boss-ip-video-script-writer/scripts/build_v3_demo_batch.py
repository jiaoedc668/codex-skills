#!/usr/bin/env python3
"""Rebuild a schema-v3 failure-reproduction example, never a submission batch."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from check_script_quality import expected_feedback_context, read_jsonl
from rank_topics import rank_pool


SKILL_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = SKILL_ROOT.parent
OUTPUT_DIR = SKILL_ROOT / "examples" / "skill-v3-run-20260902"
FEEDBACK_LEDGER = WORKSPACE / "老板IP内容库" / "反馈台账.jsonl"
BATCH_ID = "batch-20260902-craft-v3-01"
POOL_ID = f"{BATCH_ID}-topic-pool"
RETRIEVED_AT = "2026-09-02"


TOPICS = [
    {
        "topic_id": "paid-leave-proof",
        "title": "年假为什么还要证明有必要",
        "macro_theme": "labor_and_power",
        "heat_evidence": {"freshness_days": 17, "evidence_tier": "multiple_dated_reports", "hotlist_minutes": 0, "distinct_domains": 3, "derivative_work_count": 1},
        "audience_conflict_score": 96,
        "fage_fit_score": 96,
        "shootability_score": 98,
        "veto_reasons": [],
    },
    {
        "topic_id": "zero-bride-price-income-proof",
        "title": "零彩礼却要多开一万收入证明",
        "macro_theme": "marriage_and_property",
        "heat_evidence": {"freshness_days": 7, "evidence_tier": "multiple_dated_reports", "hotlist_minutes": 0, "distinct_domains": 3, "derivative_work_count": 2},
        "audience_conflict_score": 92,
        "fage_fit_score": 82,
        "shootability_score": 85,
        "veto_reasons": [],
    },
    {
        "topic_id": "mooncake-family-privacy",
        "title": "发月饼为何强收父母住址电话",
        "macro_theme": "privacy_and_platforms",
        "heat_evidence": {"freshness_days": 17, "evidence_tier": "multiple_dated_reports", "hotlist_minutes": 0, "distinct_domains": 2, "derivative_work_count": 1},
        "audience_conflict_score": 90,
        "fage_fit_score": 94,
        "shootability_score": 97,
        "veto_reasons": [],
    },
    {
        "topic_id": "emotional-consumption-plush",
        "title": "年轻人为什么为哭脸玩偶买单",
        "macro_theme": "emotional_consumption",
        "heat_evidence": {"freshness_days": 2, "evidence_tier": "multiple_dated_reports", "hotlist_minutes": 0, "distinct_domains": 2, "derivative_work_count": 2},
        "audience_conflict_score": 75,
        "fage_fit_score": 72,
        "shootability_score": 85,
        "veto_reasons": [],
    },
    {
        "topic_id": "autumn-recruitment-entry-jobs",
        "title": "秋招入门岗位越来越难抢",
        "macro_theme": "age_and_opportunity",
        "heat_evidence": {"freshness_days": 21, "evidence_tier": "multiple_dated_reports", "hotlist_minutes": 0, "distinct_domains": 2, "derivative_work_count": 0},
        "audience_conflict_score": 90,
        "fage_fit_score": 78,
        "shootability_score": 80,
        "veto_reasons": [],
    },
    {
        "topic_id": "interest-consumption",
        "title": "兴趣消费从买东西变成找同类",
        "macro_theme": "emotional_consumption",
        "heat_evidence": {"freshness_days": 4, "evidence_tier": "multiple_dated_reports", "hotlist_minutes": 0, "distinct_domains": 2, "derivative_work_count": 1},
        "audience_conflict_score": 70,
        "fage_fit_score": 70,
        "shootability_score": 82,
        "veto_reasons": [],
    },
    {
        "topic_id": "dual-worker-childcare",
        "title": "双职工家庭假期带娃难",
        "macro_theme": "family_roles",
        "heat_evidence": {"freshness_days": 20, "evidence_tier": "multiple_dated_reports", "hotlist_minutes": 0, "distinct_domains": 2, "derivative_work_count": 0},
        "audience_conflict_score": 88,
        "fage_fit_score": 86,
        "shootability_score": 78,
        "veto_reasons": [],
    },
    {
        "topic_id": "personal-account-company-video",
        "title": "公司视频发在员工个人账号归谁",
        "macro_theme": "privacy_and_platforms",
        "heat_evidence": {"freshness_days": 120, "evidence_tier": "single_dated_source", "hotlist_minutes": 0, "distinct_domains": 1, "derivative_work_count": 1},
        "audience_conflict_score": 86,
        "fage_fit_score": 80,
        "shootability_score": 86,
        "veto_reasons": [],
    },
    {
        "topic_id": "family-gift-address",
        "title": "企业福利要不要直接寄给家属",
        "macro_theme": "family_roles",
        "heat_evidence": {"freshness_days": 14, "evidence_tier": "single_dated_source", "hotlist_minutes": 0, "distinct_domains": 1, "derivative_work_count": 0},
        "audience_conflict_score": 75,
        "fage_fit_score": 83,
        "shootability_score": 92,
        "veto_reasons": ["与父母住址电话方向过近，仅保留证据不进入候选"],
    },
]


SPECS: list[dict[str, Any]] = [
    {
        "topic_id": "paid-leave-proof",
        "title": "年假还要证明必要？",
        "cover": "年假还要证明有必要？",
        "category": "职场权利",
        "macro_theme": "labor_and_power",
        "pattern": "result_first_flashback",
        "dialogue_mode": "rapid_exchange",
        "anchor": "必要",
        "payoff_method": "先给出发哥进交接名单的结果，再倒回十分钟前解释原因",
        "premise": "员工请三天年假却被要求证明有必要，发哥把自己写进客户交接名单",
        "conflict": "员工要依法休年假，人事担心三天无人接客户，发哥必须承担排班成本",
        "viewpoint": "年假可以协调日期，不该审问理由；没人接活就由定安排的人补上",
        "incident": "员工请三天年假，人事要求先证明这假有必要",
        "goal": "员工要休三天年假，发哥要补上客户交接缺口",
        "mechanism": "先亮出发哥进入交接名单的结果，再倒回十分钟前追问必要二字",
        "payoff": "发哥拿起名单写上自己并重排客户交接",
        "action": "发哥拿起名单写上自己并重排客户交接",
        "consequence": "员工的三天年假保留，上午由发哥顶，下午分给两名同事",
        "behavior": "B01", "expression": "E03", "tradeoff": "V01", "weakness": "W02", "relationship": "R01",
        "public_question": "员工请法定年假时，公司能不能先审查休假的理由是否必要？",
        "positions": ["只要工作有人接，年假无需交代理由", "客户无人接时，公司可以先问清休假必要性"],
        "stakes": [("个人时间", "三天年假"), ("规则冲突", "证明这假有必要")],
        "expected_pattern": "老板追问请假理由，员工靠一句硬话赢下争论",
        "story_break": "发哥说把我名字写上，亲自补进客户交接名单",
        "escalation": "员工请三天年假，人事要求先证明这假有必要",
        "lines": [
            ("员工画外音", "发哥，你怎么把自己排进我休假那三天了？"),
            ("发哥", "先看十分钟前。"),
            ("员工画外音", "我请三天年假，人事让我先证明这假有必要。"),
            ("发哥", "年假还要证明必要？"),
            ("员工画外音", "不写理由，就说那三天没人接我的客户。"),
            ("发哥", "日期可以排，理由不用审。"),
            ("员工画外音", "可谁来接？名单上确实没人。"),
            ("发哥", "把我名字写上。"),
            ("员工画外音", "所以你真替我顶三天？"),
            ("发哥", "上午我顶，下午分给两人。"),
        ],
        "segment_splits": [2, 5, 8, 10],
        "structure_mode": "four_part",
        "extra_reason": "先露出老板承担成本的结果，再回看冲突，避免常规顺叙",
        "expected_effect": "观众先追问发哥为什么进名单，再看到必要二字被具体排班化解",
        "hook_visual": "镜头先拍客户交接名单，发哥名字出现在员工休假三天的空档里",
        "source_title": "多省份发文推动落实职工带薪休假，多地要求领导干部带头休假",
        "source_url": "https://finance.eastmoney.com/a/202608053832727981.html",
        "source_date": "2026-08-05",
        "work_title": "员工请假理由让老板措不及防",
        "work_url": "https://www.douyin.com/video/7601458007222688883",
        "work_mechanism": "员工第一句直接抛请假冲突，老板用短反应接住",
        "adopted": "采用开门见山的请假冲突和短句接话，不采用原台词与人物关系",
    },
    {
        "topic_id": "zero-bride-price-income-proof",
        "title": "零彩礼，假工资？",
        "cover": "一分彩礼没出，却要多写一万工资",
        "category": "婚姻与财产",
        "macro_theme": "marriage_and_property",
        "pattern": "counter_reversal",
        "dialogue_mode": "deadpan_setback",
        "anchor": "一万",
        "payoff_method": "零彩礼的轻松开场被假收入证明反打，停顿后只批时间不签假数字",
        "premise": "员工一分彩礼没出，却让发哥把收入证明多写一万以便婚前买房",
        "conflict": "员工急着完成婚前买房条件，发哥拒绝替虚假收入承担签字责任",
        "viewpoint": "零彩礼不等于可以用假收入过关；婚前数字谈不拢，就先谈清而不是让老板签假证明",
        "incident": "员工说一分彩礼没出，转手递来要多写一万的收入证明",
        "goal": "员工要今天拿到更高收入证明，发哥要守住签字真实性",
        "mechanism": "一分彩礼的好消息被婚前买房和假收入证明连续反转",
        "payoff": "发哥递回收入证明并改批半天假让员工谈真实数字",
        "action": "发哥递回收入证明并改批半天假让员工谈真实数字",
        "consequence": "假收入证明没有签，员工得到半天时间重新谈婚前买房",
        "behavior": "B04", "expression": "E03", "tradeoff": "V02", "weakness": "W01", "relationship": "R03",
        "public_question": "一分彩礼不要但要求婚前买房时，能不能让单位多开收入证明先过关？",
        "positions": ["婚前买房是双方选择，收入证明临时多写一点可解燃眉之急", "假收入会把婚姻压力转成签字人的责任，不能代签"],
        "stakes": [("身份体面", "一分彩礼没出"), ("公平责任", "收入证明多写一万")],
        "expected_pattern": "老板被员工婚事打动，顺手签下更高收入证明",
        "story_break": "发哥说我批半天假，证明退回，只给谈清楚的时间",
        "escalation": "员工一分彩礼没出，却要求收入证明多写一万",
        "lines": [
            ("员工画外音", "发哥，我一分彩礼没出，收入证明多写一万行不行？"),
            ("发哥", "先把这两件事分开。"),
            ("员工画外音", "对方不要彩礼，要我婚前买房，银行说收入不够。"),
            ("发哥", "所以你来借我的字？"),
            ("员工画外音", "就多一万，房贷还是我自己还。"),
            ("发哥", "……假的一万，也得我签。"),
            ("员工画外音", "那房买不了，婚还怎么结？"),
            ("发哥", "先把真实数字说清。"),
            ("员工画外音", "今天就要给答复，我没时间谈了。"),
            ("发哥", "我批半天假，证明退回。"),
        ],
        "segment_splits": [2, 7, 10],
        "structure_mode": "three_part",
        "extra_reason": "无", "expected_effect": "无",
        "hook_visual": "员工把收入证明推到发哥面前，金额栏贴着一张加一万的便签",
        "source_title": "持续推进农村高额彩礼综合整治",
        "source_url": "https://www.news.cn/politics/20260826/b8a29e5e714048d38dfae9c7e096f0e0/c.html",
        "source_date": "2026-08-26",
        "work_title": "退还18.8万元彩礼的背后",
        "work_url": "https://tv.cctv.com/2026/03/29/VIDEd8o3TjbwCR2Vw40DPZt2260329.shtml",
        "work_mechanism": "先给具体金额，再追问掌声背后的现实条件",
        "adopted": "采用具体金额先行、随后揭开第二层条件；不采用人物经历与原句",
    },
    {
        "topic_id": "mooncake-family-privacy",
        "title": "月饼表，填父母电话？",
        "cover": "发个月饼，要填父母电话？",
        "category": "隐私与职场",
        "macro_theme": "privacy_and_platforms",
        "pattern": "rule_escalation",
        "dialogue_mode": "prop_reveal",
        "anchor": "必填",
        "payoff_method": "先看见福利登记标题，再翻开露出父母住址和家属电话必填列",
        "premise": "中秋福利登记表翻开后露出父母住址和家属电话必填，员工当场拒填",
        "conflict": "行政想把月饼直接寄到家显得贴心，员工不愿交家里人的电话",
        "viewpoint": "福利可以发给员工自己带回家，不能借贴心把父母住址和电话变成必填",
        "incident": "中秋福利表翻开，父母住址和家属电话两列都标着必填",
        "goal": "员工要删掉家属信息必填，发哥要保留福利又减少无关收集",
        "mechanism": "福利登记从本人地址一路升级到父母住址和家属电话",
        "payoff": "发哥拿起红笔划掉两列并让行政删除电子表必填",
        "action": "发哥拿起红笔划掉两列并让行政删除电子表必填",
        "consequence": "月饼改为发给员工本人，父母住址和家属电话不再收集",
        "behavior": "B02", "expression": "E01", "tradeoff": "V03", "weakness": "W02", "relationship": "R01",
        "public_question": "公司发中秋福利时，能不能把父母住址和家属电话设成必填？",
        "positions": ["直接寄到家更贴心，可以统一收家属地址电话", "福利发本人即可，不该强收家属信息"],
        "stakes": [("隐私边界", "父母住址"), ("信任破裂", "家里人的电话")],
        "expected_pattern": "老板强调公司好意，劝员工配合把家属信息填完整",
        "story_break": "发哥说把这两列删了，月饼发员工，愿意就自己带回家",
        "escalation": "中秋福利表把父母住址和家属电话都设成必填",
        "lines": [
            ("员工画外音", "发哥，中秋福利表为什么要填我父母住址和电话？"),
            ("发哥", "发个月饼，要这么多？"),
            ("行政画外音", "想直接寄到家，员工会觉得公司更贴心。"),
            ("员工画外音", "我只填自己地址，不想交家里人的电话。"),
            ("发哥", "那就填自己的。"),
            ("行政画外音", "可表格标了必填，少一项就交不了。"),
            ("发哥", "谁把必填加上的？"),
            ("行政画外音", "我照去年的表改的。"),
            ("发哥", "把这两列删了。"),
            ("发哥", "月饼发员工，愿意就自己带回家。"),
        ],
        "segment_splits": [2, 8, 10],
        "structure_mode": "three_part",
        "extra_reason": "无", "expected_effect": "无",
        "hook_visual": "镜头先拍中秋福利登记标题，翻开后露出父母住址和家属电话必填两列",
        "source_title": "2026青年关注的十大话题：隐私保护与数字安全感",
        "source_url": "https://theory.people.com.cn/n1/2026/0816/c40531-40780401.html",
        "source_date": "2026-08-16",
        "work_title": "公司强制员工打开朋友圈的后果有多严重",
        "work_url": "https://www.douyin.com/video/7555078040120806707",
        "work_mechanism": "从看似普通的公司要求逐步露出个人边界冲突",
        "adopted": "采用普通要求逐层露出隐私代价的升级方式；不采用原情节和台词",
    },
]


def source(kind: str, title: str, locator: str, source_date: str, borrowed: str) -> dict[str, Any]:
    return {
        "source_kind": kind,
        "title": title,
        "locator": locator,
        "source_date": source_date,
        "retrieved_at": RETRIEVED_AT,
        "metrics_provided": False,
        "metric_note": "仅作公开热点或创作机制研究；无用户提供的发布数据",
        "borrowed_mechanism": borrowed,
    }


def make_segments(spec: dict[str, Any]) -> list[dict[str, Any]]:
    labels = [f"{speaker}：{line}" for speaker, line in spec["lines"]]
    starts = [0] + spec["segment_splits"][:-1]
    ends = spec["segment_splits"]
    stages = ["hook", "turn", "conflict", "ending"] if len(ends) == 4 else ["hook", "conflict", "ending"]
    changes = {
        "paid-leave-proof": [
            "先看到发哥已经进入三天交接名单",
            "时间倒回十分钟前，必要性审查被摆上桌",
            "无人接客户的实际缺口被确认，发哥拿起名单写上自己",
            "三天年假保留并形成上午与下午的交接安排",
        ],
        "zero-bride-price-income-proof": [
            "零彩礼与多写一万收入同时出现",
            "婚前买房压力转成要求发哥签假数字",
            "发哥递回证明，只改批半天谈真实数字",
        ],
        "mooncake-family-privacy": [
            "福利登记翻开后露出父母住址和家属电话必填",
            "贴心寄送逐步升级为系统强制收集",
            "发哥划掉两列并删除电子表必填",
        ],
    }[spec["topic_id"]]
    visuals = {
        "paid-leave-proof": [spec["hook_visual"], "字幕显示十分钟前，员工递上年假申请", "发哥拿起名单写上自己并重排客户交接", "镜头停在补完的交接名单"],
        "zero-bride-price-income-proof": [spec["hook_visual"], "发哥放下笔，员工指出婚前买房条件", "发哥递回收入证明并改批半天假"],
        "mooncake-family-privacy": [spec["hook_visual"], "发哥翻开表格逐项看必填栏", "发哥拿起红笔划掉两列并让行政删除电子表必填"],
    }[spec["topic_id"]]
    return [
        {
            "time": f"{0 if i == 0 else i * 10}-{(i + 1) * 10}秒",
            "stage": stages[i],
            "speaker": "、".join(dict.fromkeys(s for s, _ in spec["lines"][starts[i]:ends[i]])),
            "dialogue": "".join(labels[starts[i]:ends[i]]),
            "visual_action": visuals[i],
            "story_change": changes[i],
            "humor_function": "用短停顿和关系错位推进，不另加段子",
            "camera": "固定中景接道具特写",
            "screen_audio": spec["cover"] if i == 0 else "保留现场短停顿",
        }
        for i in range(len(ends))
    ]


def build_candidate(spec: dict[str, Any], position: int, ranking: dict[str, Any], feedback: dict[str, Any]) -> dict[str, Any]:
    rank_row = next(item for item in ranking["ranked"] if item["topic_id"] == spec["topic_id"])
    lines = spec["lines"]
    segments = make_segments(spec)
    research_sources = [
        source("web", spec["source_title"], spec["source_url"], spec["source_date"], "记录当前议题与发生日期"),
        source("web", spec["work_title"], spec["work_url"], "未显示", spec["work_mechanism"]),
        source("local_history", "老板IP历史选题台账", "老板IP内容库/选题台账.jsonl", "2026-09-02", "只读查重，不登记新状态"),
    ]
    feedback_context = deepcopy(feedback)
    feedback_context["read_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "schema_version": 3,
        "candidate": {
            "batch_id": BATCH_ID,
            "candidate_id": f"{BATCH_ID}-c{position}",
            "position": position,
            "selection_status": "awaiting_selection",
            "difference_axes": {
                "inciting_incident": spec["incident"],
                "character_goal": spec["goal"],
                "conflict_mechanism": spec["mechanism"],
                "fage_payoff": spec["payoff"],
            },
            "feedback_context": feedback_context,
            "research_scope": {"mode": "broad_pool", "focus_label": "无", "basis": "跨职场、婚产、隐私、消费、家庭等九个公开议题统一按热度45%排序"},
        },
        "topic_strategy": {
            "topic_mode": "current_issue",
            "macro_theme": spec["macro_theme"],
            "public_question": spec["public_question"],
            "opposing_positions": spec["positions"],
            "stake_evidence": [{"tag": tag, "public_proof": proof} for tag, proof in spec["stakes"]],
            "novelty_break": {"expected_pattern": spec["expected_pattern"], "story_break": spec["story_break"]},
            "escalation_event": spec["escalation"],
            "heat_basis": {"status": "dated_source", "source_ref": spec["source_url"], "claim": f"{spec['source_date']}公开报道与相关作品共同支持本轮研究"},
            "selection_ranking": {
                "pool_id": ranking["pool_id"], "pool_size": ranking["pool_size"], "eligible_count": ranking["eligible_count"],
                "heat_rank": rank_row["heat_rank"], "final_rank": rank_row["final_rank"],
                "heat_evidence": rank_row["heat_evidence"], "heat_score": rank_row["heat_score"],
                "audience_conflict_score": rank_row["audience_conflict_score"], "fage_fit_score": rank_row["fage_fit_score"],
                "shootability_score": rank_row["shootability_score"], "selection_score": rank_row["selection_score"],
                "evidence_refs": [spec["source_url"], spec["work_url"]],
                "decision_note": "先按公开时效与传播证据计热度，再叠加公共冲突、发哥行动适配和低成本可拍性",
            },
        },
        "workflow": {"stage": "candidate", "revision_id": "r1", "selected_candidate_id": "", "copy_confirmation": {"confirmed": False, "confirmed_revision_id": "", "confirmed_at": "", "user_quote": "", "content_sha256": ""}},
        "meta": {"account_name": "发哥", "generation_date": RETRIEVED_AT, "platform": "抖音自然流量", "estimated_duration": "约35-50秒", "scene": "公司办公室", "format": "员工画外音对话轻剧情", "generation_mode": "new_script", "topic_id": spec["topic_id"], "filename_topic": spec["title"], "version": "r1"},
        "title": spec["title"], "cover_title": spec["cover"], "content_positioning": f"{spec['category']}中的异常选择轻剧情", "core_viewpoint": spec["viewpoint"],
        "content_signature": {"category": spec["category"], "premise": spec["premise"], "conflict": spec["conflict"], "hook_mechanism": "具体异常结果", "plot_device": spec["mechanism"], "ending_type": "老板承担动作成本", "key_line": lines[-1][1]},
        "creative_diagnostics": {"format_fit": f"{spec['incident']}可在办公室用一张表和一次动作拍完", "audience_resonance": spec["public_question"], "content_value": spec["viewpoint"], "cognitive_gap": spec["story_break"], "hook_topic": spec["incident"], "hook_gap": "观众会追问发哥最终签什么、删什么或承担什么", "hook_credibility": spec["hook_visual"], "hook_payoff": spec["payoff"]},
        "story_blueprint": {"one_sentence_story": f"{spec['premise']}，最后{spec['payoff']}", "structure_mode": spec["structure_mode"], "narrative_pattern": spec["pattern"], "fage_want": spec["goal"].split("，")[-1], "counterparty_want": spec["goal"].split("，")[0], "why_now": spec["incident"], "primary_comedy_engine": spec["mechanism"], "core_choice": spec["payoff"], "choice_cost": spec["consequence"], "core_meaning": spec["viewpoint"], "plain_conclusion": lines[-1][1], "ending_change": spec["consequence"], "extra_beat_reason": spec["extra_reason"], "expected_effect": spec["expected_effect"]},
        "dialogue_design": {"mode": spec["dialogue_mode"], "anchor_word": spec["anchor"], "payoff_method": spec["payoff_method"], "jargon_resolution": "公开对白不使用偏术语，所有冲突落到表格、数字、日期和具体动作"},
        "persona_evidence": {"behavior_id": spec["behavior"], "expression_id": spec["expression"], "tradeoff_id": spec["tradeoff"], "weakness_id": spec["weakness"], "relationship_id": spec["relationship"], "visible_action": spec["action"], "action_consequence": spec["consequence"]},
        "primary_hook": {"voiceover": lines[0][1], "visual": spec["hook_visual"], "screen_text": spec["cover"]},
        "cast": [{"role": "发哥", "visibility": "露脸", "purpose": "被具体证据架住后作决定并承担成本"}, {"role": "员工画外音", "visibility": "不露脸", "purpose": "带着自己的明确目标交涉"}],
        "preparation": [{"category": "道具", "items": spec["hook_visual"], "notes": "只用纸质表、红笔或电脑屏幕完成"}],
        "segments": segments,
        "full_dialogue": [{"speaker": speaker, "line": line} for speaker, line in lines],
        "comment_prompt": "你更在意哪一步？只评故事是否愿意拍。",
        "shooting_notes": ["按结构标注拍摄，不补宏大总结", "发哥动作前保留半秒真实停顿"],
        "research_summary": "先检索当前公共议题，再看相关短视频的开场、反转和道具用法；只借结构机制，不复制原句、口头禅或人物设定。",
        "research_sources": research_sources,
        "creative_adaptation": {"reviewed_works": [{"title": spec["work_title"], "locator": spec["work_url"], "decision": "adopted", "observed_mechanism": spec["work_mechanism"], "adopted_mechanism": spec["adopted"], "copyright_boundary": "仅借抽象叙事装置，未复制原台词、镜头顺序、人物关系或标志性表达"}], "adoption_disclosure": f"采用《{spec['work_title']}》的抽象机制：{spec['adopted']}"},
        "continuity_claims": [],
    }


def readable_markdown(candidates: list[dict[str, Any]], ranking: dict[str, Any]) -> str:
    lines = ["# Skill v3 新候选（待谢总验收）", "", "本轮先比较9个公开议题，热度权重45%，再看公共冲突20%、发哥适配20%、可拍性15%。未登记旧台账，未生成Word。", ""]
    for candidate in candidates:
        r = candidate["topic_strategy"]["selection_ranking"]
        lines.extend([f"## {candidate['candidate']['position']}. {candidate['title']}", "", f"- 排名：第{r['final_rank']}名；热度分{r['heat_score']}；总分{r['selection_score']}", f"- 结构：{candidate['story_blueprint']['narrative_pattern']}；对白：{candidate['dialogue_design']['mode']}", f"- 采用参考：[{candidate['creative_adaptation']['reviewed_works'][0]['title']}]({candidate['creative_adaptation']['reviewed_works'][0]['locator']})（只借抽象机制）", "", "完整对话：", ""])
        for item in candidate["full_dialogue"]:
            lines.append(f"{item['speaker']}：{item['line']}")
        lines.extend(["", f"发哥动作：{candidate['persona_evidence']['visible_action']}", ""])
    lines.extend(["## 热点池排名", ""])
    for item in ranking["ranked"]:
        lines.append(f"{item['final_rank']}. {item['title']}｜热度{item['heat_score']}｜总分{item['selection_score']}")
    if ranking["vetoed"]:
        lines.extend(["", "未入选（相似方向否决）："])
        for item in ranking["vetoed"]:
            lines.append(f"- {item['title']}：{'；'.join(item['veto_reasons'])}")
    return "\n".join(lines) + "\n"


def main() -> int:
    print(
        "EXAMPLE ONLY: output is not a validated or user-submitted candidate batch",
        file=sys.stderr,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pool = {"pool_id": POOL_ID, "prospects": TOPICS}
    ranking = rank_pool(pool)
    feedback = expected_feedback_context(read_jsonl(FEEDBACK_LEDGER))
    ranked_specs = sorted(SPECS, key=lambda spec: next(row["final_rank"] for row in ranking["ranked"] if row["topic_id"] == spec["topic_id"]))
    candidates = [build_candidate(spec, index, ranking, feedback) for index, spec in enumerate(ranked_specs, 1)]
    (OUTPUT_DIR / "topic-pool.json").write_text(json.dumps(pool, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "topic-ranking.json").write_text(json.dumps(ranking, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for index, candidate in enumerate(candidates, 1):
        (OUTPUT_DIR / f"candidate-{index}.json").write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "候选易读版.md").write_text(readable_markdown(candidates, ranking), encoding="utf-8")
    print(f"OUTPUT_DIR={OUTPUT_DIR}")
    print("FINAL_TOP3=" + ",".join(item["topic_id"] for item in ranking["ranked"][:3]))
    print(f"CANDIDATE_COUNT={len(candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
