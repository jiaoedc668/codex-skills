from __future__ import annotations

import copy
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "boss-ip-video-script-writer"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_candidate_batch as batch_checker
import check_script_quality as quality
import build_v3_demo_batch as demo_builder
import generate_script_docx as docx_generator
import history_manager
import rank_topics
import semantic_review


PERSONA_PATH = ROOT / "老板IP内容库" / "人物设定.json"
HISTORY_LEDGER = ROOT / "老板IP内容库" / "选题台账.jsonl"


def candidate_script(index: int = 1, batch_id: str = "batch-test-001") -> dict:
    variants = {
        1: {
            "title": "周六自愿表",
            "cover": "自愿后面为什么写全员",
            "category": "职场关系",
            "premise": "员工拿着周六自愿到场表要求发哥解释全员签名",
            "conflict": "员工要守住周末，发哥要处理自己含糊的安排",
            "device": "规则照字面执行",
            "viewpoint": "自愿和全员不能写在同一张表上，安排说不清就由定安排的人改",
            "incident": "周六自愿表上又写全员签名",
            "goal": "员工要删掉周六到场，发哥要把急活重新排开",
            "mechanism": "员工用自愿和全员两个词让发哥认账",
            "payoff": "发哥划掉周六并把急活改到周一",
            "behavior": "B02",
            "expression": "E03",
            "tradeoff": "V03",
            "weakness": "W01",
            "relationship": "R01",
            "action": "发哥划掉表上的周六并重新签字",
            "consequence": "周六不再要求到场，急活由发哥改到周一",
            "hook": "这张表写着自愿到场，后面怎么又是全员签名？",
            "visual": "员工把两处红圈的安排表推到发哥面前",
            "public_question": "写着自愿的周六到场安排，员工能否拒绝已经代签的全员要求？",
            "positions": ["急活当前，全员先按表到场", "没有本人同意，自愿安排不能代签"],
            "stakes": [("规则冲突", "全员签名"), ("个人时间", "周六这批急活")],
            "expected_pattern": "老板解释急活后要求员工顾全大局",
            "story_break": "发哥划掉周六并把急活改到周一",
            "lines": [
                ("员工画外音", "这张表写着自愿到场，后面怎么又是全员签名？"),
                ("发哥", "我看看。"),
                ("员工画外音", "你昨天说大家自己选，我今天不来，名字却已经替我打了勾。"),
                ("发哥", "这个勾不是你打的，就不能算你选的。"),
                ("员工画外音", "那周六这批急活怎么办？总不能还让我自愿背回去。"),
                ("发哥", "我把周六划掉，急活拆到周一；真赶不上，我先来顶半天。"),
                ("发哥", "安排没说清，不能拿自愿两个字让员工替我收尾。"),
            ],
        },
        2: {
            "title": "AI先替老板回信",
            "cover": "AI写的道歉谁负责",
            "category": "AI与中年成长",
            "premise": "年轻员工让AI替发哥回复客户道歉邮件",
            "conflict": "员工想用工具省时间，发哥要确认承诺由谁承担",
            "device": "当场试用后责任回收",
            "viewpoint": "AI可以起草道歉，但承诺的交期必须由按下发送的人负责",
            "incident": "AI替发哥写好一封带新交期的道歉邮件",
            "goal": "员工要马上发送，发哥要核对邮件里的交期承诺",
            "mechanism": "AI自己补了三天交期，发哥先打给仓库确认",
            "payoff": "发哥拿起手机询问仓库后改掉交期再发送",
            "behavior": "B04",
            "expression": "E01",
            "tradeoff": "V02",
            "weakness": "W03",
            "relationship": "R02",
            "action": "发哥拿起手机打给仓库并改掉交期",
            "consequence": "邮件按真实库存发送，员工保留AI起草但不让它替人承诺",
            "hook": "发哥，AI替你道歉了，还顺便答应客户三天交货。",
            "visual": "员工把写好新交期的邮件页面转向发哥",
            "public_question": "AI替人写下交期承诺时，责任应算在工具还是发送的人身上？",
            "positions": ["AI生成的承诺可以直接采用", "按下发送的人必须核对并承担承诺"],
            "stakes": [("技术替代", "AI替你道歉"), ("公平责任", "三天交货")],
            "expected_pattern": "老板禁止员工使用AI处理客户邮件",
            "story_break": "发哥拿起手机打给仓库并改掉交期",
            "lines": [
                ("员工画外音", "发哥，AI替你道歉了，还顺便答应客户三天交货。"),
                ("发哥", "它答应得挺快，仓库也答应了吗？"),
                ("员工画外音", "我只让它把语气写诚恳，交期是它自己补的，我还没点发送。"),
                ("发哥", "没发就好，我也不会装懂库存，先问清楚。"),
                ("员工画外音", "那这封邮件还用不用？前半段其实写得挺顺。"),
                ("发哥", "前半段留着，三天删掉。我打给仓库，确认五天，再由我发送。"),
                ("发哥", "AI替我们省了写字时间，交期这句话还是按发送的人算。"),
            ],
        },
        3: {
            "title": "体检单别藏抽屉",
            "cover": "父亲藏体检单怎么办",
            "category": "家庭边界",
            "premise": "画外音发现父亲把复查体检单藏进抽屉",
            "conflict": "画外音怕耽误工作，父亲又怕给孩子添麻烦",
            "device": "先落实明天陪诊再处理请假",
            "viewpoint": "面对父母藏起的复查单，先把明天的号挂上比隔着电话劝安心更有用",
            "incident": "画外音在抽屉里发现父亲藏着的复查单",
            "goal": "画外音要安排陪诊又怕工作断档，发哥要给出当天能执行的一步",
            "mechanism": "先挂明天复查号，再由发哥顶上午客户资料",
            "payoff": "发哥改掉上午分工并让员工明天陪父亲复查",
            "behavior": "B01",
            "expression": "E02",
            "tradeoff": "V01",
            "weakness": "W02",
            "relationship": "R03",
            "action": "发哥改掉白板上的上午分工并写上自己名字",
            "consequence": "员工明天能陪父亲复查，下午回来再接回工作",
            "hook": "我爸把复查单藏抽屉里，还说不想耽误我上班。",
            "visual": "画外音把折过的复查单放在发哥桌上",
            "public_question": "父亲怕拖累子女藏起复查单时，子女应尊重隐瞒还是立刻介入？",
            "positions": ["尊重父亲不愿添麻烦的选择", "先落实复查再讨论彼此边界"],
            "stakes": [("家庭权责", "我爸把复查单"), ("信任破裂", "藏抽屉里")],
            "expected_pattern": "老板用亲身经历劝员工多陪父母",
            "story_break": "发哥改掉上午分工并让员工明天陪父亲复查",
            "lines": [
                ("员工画外音", "我爸把复查单藏抽屉里，还说不想耽误我上班。"),
                ("发哥", "先把明天的号挂上，别隔着电话猜他到底严不严重。"),
                ("员工画外音", "号我能挂，可明早的客户资料本来归我，临时没人接。"),
                ("发哥", "你把目录发我，上午我先顶；你陪他看完，下午再回来接。"),
                ("员工画外音", "我怕一请假，他更觉得自己拖累我，以后还会继续藏。"),
                ("发哥", "那就别把陪诊说成牺牲。你去医院，我改上午分工，各做一件该做的事。"),
                ("发哥", "这张单先别塞回抽屉，明天看完再决定下一步。"),
            ],
        },
    }
    v = variants[index]
    macro_themes = {
        1: "labor_and_power",
        2: "technology_and_work",
        3: "family_roles",
    }
    labelled = [f"{speaker}：{line}" for speaker, line in v["lines"]]
    segments = [
        {
            "time": "0-5秒",
            "stage": "hook",
            "speaker": "员工画外音、发哥",
            "dialogue": "".join(labelled[:2]),
            "visual_action": v["visual"],
            "story_change": f"{v['incident']}进入发哥眼前",
            "humor_function": "身份关系带来短停顿",
            "camera": "固定中景接道具特写",
            "screen_audio": v["cover"],
        },
        {
            "time": "5-32秒",
            "stage": "conflict",
            "speaker": "员工画外音、发哥",
            "dialogue": "".join(labelled[2:6]),
            "visual_action": v["action"],
            "story_change": f"{v['mechanism']}并形成决定",
            "humor_function": "发哥被具体证据架住后用动作回应",
            "camera": "中景拍发哥动作",
            "screen_audio": "保留关键动作原声",
        },
        {
            "time": "32-48秒",
            "stage": "ending",
            "speaker": "发哥",
            "dialogue": "".join(labelled[6:]),
            "visual_action": v["action"],
            "story_change": v["consequence"],
            "humor_function": "无，承担剧情推进",
            "camera": "中景自然收住",
            "screen_audio": "无",
        },
    ]
    return {
        "schema_version": 2,
        "candidate": {
            "batch_id": batch_id,
            "candidate_id": f"{batch_id}-c{index}",
            "position": index,
            "selection_status": "awaiting_selection",
            "difference_axes": {
                "inciting_incident": v["incident"],
                "character_goal": v["goal"],
                "conflict_mechanism": v["mechanism"],
                "fage_payoff": v["payoff"],
            },
            "feedback_context": {
                "read_at": "2026-09-01T10:00:00+08:00",
                "latest_feedback_ids": [],
                "keep": ["无"],
                "avoid": ["无"],
                "publication_data": "无用户提供的发布数据",
            },
            "research_scope": {
                "mode": "broad_pool",
                "focus_label": "无",
                "basis": "测试用广谱候选池",
            },
        },
        "topic_strategy": {
            "topic_mode": "public_tension",
            "macro_theme": macro_themes[index],
            "public_question": v["public_question"],
            "opposing_positions": v["positions"],
            "stake_evidence": [
                {"tag": tag, "public_proof": proof} for tag, proof in v["stakes"]
            ],
            "novelty_break": {
                "expected_pattern": v["expected_pattern"],
                "story_break": v["story_break"],
            },
            "escalation_event": v["hook"],
            "heat_basis": {
                "status": "evergreen_public_tension",
                "source_ref": "长期公共矛盾；测试未使用实时趋势数据",
                "claim": "不宣称当前热点",
            },
            "selection_ranking": {
                "pool_id": f"{batch_id}-topic-pool",
                "pool_size": 9,
                "eligible_count": 9,
                "heat_rank": index,
                "final_rank": index,
                "heat_evidence": {
                    "freshness_days": 999,
                    "evidence_tier": "no_current_signal",
                    "hotlist_minutes": 0,
                    "distinct_domains": 0,
                    "derivative_work_count": 0,
                },
                "heat_score": 0,
                "audience_conflict_score": 100 - index * 10,
                "fage_fit_score": 100 - index * 10,
                "shootability_score": 100 - index * 10,
                "selection_score": round((100 - index * 10) * 0.55, 2),
                "evidence_refs": ["老板IP内容库/选题台账.jsonl"],
                "decision_note": "测试池按公共冲突、发哥适配和可拍性依次保留前三名",
            },
        },
        "workflow": {
            "stage": "candidate",
            "revision_id": "r1",
            "selected_candidate_id": "",
            "copy_confirmation": {
                "confirmed": False,
                "confirmed_revision_id": "",
                "confirmed_at": "",
                "user_quote": "",
                "content_sha256": "",
            },
        },
        "meta": {
            "account_name": "发哥",
            "generation_date": "2026-09-01",
            "platform": "抖音自然流量",
            "estimated_duration": "约30-50秒",
            "scene": "公司办公室",
            "format": "员工画外音对话轻剧情",
            "generation_mode": "new_script",
            "topic_id": f"topic-test-{index}",
            "filename_topic": v["title"],
            "version": "auto",
        },
        "title": v["title"],
        "cover_title": v["cover"],
        "content_positioning": f"{v['category']}里的具体选择轻剧情",
        "core_viewpoint": v["viewpoint"],
        "content_signature": {
            "category": v["category"],
            "premise": v["premise"],
            "conflict": v["conflict"],
            "hook_mechanism": "具体异常结果",
            "plot_device": v["device"],
            "ending_type": "动作后果",
            "key_line": v["lines"][-1][1],
        },
        "creative_diagnostics": {
            "format_fit": f"{v['incident']}可在一个场景靠道具和决定拍完",
            "audience_resonance": f"40+观众常遇到的{v['conflict']}",
            "content_value": f"观众能看见{v['viewpoint']}",
            "cognitive_gap": "不靠老板讲道理，先让决定造成具体后果",
            "hook_topic": v["incident"],
            "hook_gap": "观众想看发哥怎样处理眼前证据",
            "hook_credibility": v["visual"],
            "hook_payoff": v["payoff"],
        },
        "story_blueprint": {
            "one_sentence_story": f"{v['premise']}，经过冲突后，{v['payoff']}",
            "structure_mode": "three_part",
            "fage_want": v["goal"].split("，")[-1],
            "counterparty_want": v["goal"].split("，")[0],
            "why_now": v["incident"],
            "primary_comedy_engine": v["device"],
            "core_choice": v["payoff"],
            "choice_cost": v["consequence"],
            "core_meaning": v["viewpoint"],
            "plain_conclusion": v["lines"][-1][1],
            "ending_change": v["consequence"],
            "extra_beat_reason": "无",
            "expected_effect": "无",
        },
        "persona_evidence": {
            "behavior_id": v["behavior"],
            "expression_id": v["expression"],
            "tradeoff_id": v["tradeoff"],
            "weakness_id": v["weakness"],
            "relationship_id": v["relationship"],
            "visible_action": v["action"],
            "action_consequence": v["consequence"],
        },
        "primary_hook": {
            "voiceover": v["hook"],
            "visual": v["visual"],
            "screen_text": v["cover"],
        },
        "cast": [
            {"role": "发哥", "visibility": "露脸", "purpose": "处理现场并承担决定"},
            {"role": "员工画外音", "visibility": "不露脸", "purpose": "带着自己的目标交涉"},
        ],
        "preparation": [
            {"category": "道具", "items": v["visual"], "notes": "开拍前放到桌边"}
        ],
        "segments": segments,
        "full_dialogue": [
            {"speaker": speaker, "line": line} for speaker, line in v["lines"]
        ],
        "comment_prompt": "无",
        "shooting_notes": ["保留发哥动作前的短停顿，不追加演讲"],
        "research_summary": "读取本地历史，只借鉴短对话结构并避开旧事件",
        "research_sources": [
            {
                "source_kind": "local_history",
                "title": "老板IP历史选题台账",
                "locator": "老板IP内容库/选题台账.jsonl",
                "source_date": "2026-09-01",
                "retrieved_at": "2026-09-01",
                "metrics_provided": False,
                "metric_note": "无用户提供的发布数据",
                "borrowed_mechanism": "只读取历史事件用于查重",
            }
        ],
        "continuity_claims": [],
    }


def craft_v3_candidate(index: int = 1, batch_id: str = "batch-craft-v3") -> dict:
    script = candidate_script(index, batch_id)
    patterns = {
        1: "rule_escalation",
        2: "counter_reversal",
        3: "realtime_pressure",
    }
    designs = {
        1: {
            "mode": "keyword_rebound",
            "anchor_word": "自愿",
            "payoff_method": "自愿从员工选择回到发哥责任",
            "jargon_resolution": "无",
        },
        2: {
            "mode": "rapid_exchange",
            "anchor_word": "三天",
            "payoff_method": "短句连续追问后由发哥打电话核实",
            "jargon_resolution": "无",
        },
        3: {
            "mode": "deadpan_setback",
            "anchor_word": "请假",
            "payoff_method": "发哥停顿改口并重排上午分工",
            "jargon_resolution": "无",
        },
    }
    lines = {
        1: [
            ("员工画外音", "这张表写自愿，后面怎么又是全员，这到底算哪个？"),
            ("发哥", "我看看。"),
            ("员工画外音", "你说自己选，我本人没碰过，名字已经被人打了勾。"),
            ("发哥", "这个勾谁打的？"),
            ("员工画外音", "行政，说你默认全员都来。"),
            ("发哥", "我说过自愿。"),
            ("员工画外音", "那我算自愿，还是算全员？"),
            ("发哥", "……全员划掉。"),
            ("员工画外音", "周六这批急活怎么办？"),
            ("发哥", "我先来顶，周一重排。"),
        ],
        2: [
            ("员工画外音", "AI替你写完道歉，还答应客户三天交货。"),
            ("发哥", "仓库答应了吗？"),
            ("员工画外音", "没问，它看前文自己补了三天。"),
            ("发哥", "你发了？"),
            ("员工画外音", "还没有，我正准备按发送，幸亏你进来了。"),
            ("发哥", "那先别发。"),
            ("员工画外音", "那前半封道歉还留不留？"),
            ("发哥", "道歉留着，三天删掉。"),
            ("员工画外音", "真实交期谁去问仓库？"),
            ("发哥", "我打电话，你来改。"),
        ],
        3: [
            ("员工画外音", "我爸把复查单藏抽屉里，还说不想耽误我上班。"),
            ("发哥", "先把明天的号挂上。"),
            ("员工画外音", "号能挂，明早的客户资料没人接。"),
            ("发哥", "目录发我，我先顶。"),
            ("员工画外音", "他知道我请假，更觉得自己拖累我，以后还会藏。"),
            ("发哥", "……那就别说请假。"),
            ("员工画外音", "那我明早该怎么跟他说？"),
            ("发哥", "你陪他看病，我改分工。"),
        ],
    }[index]
    script["schema_version"] = 3
    script["story_blueprint"]["narrative_pattern"] = patterns[index]
    script["dialogue_design"] = designs[index]
    script["full_dialogue"] = [
        {"speaker": speaker, "line": line} for speaker, line in lines
    ]
    labelled = [f"{speaker}：{line}" for speaker, line in lines]
    split_a = 2
    split_b = len(lines) - 2
    script["segments"][0]["dialogue"] = "".join(labelled[:split_a])
    script["segments"][1]["dialogue"] = "".join(labelled[split_a:split_b])
    script["segments"][2]["dialogue"] = "".join(labelled[split_b:])
    script["story_blueprint"]["plain_conclusion"] = lines[-1][1]
    script["content_signature"]["key_line"] = lines[-1][1]
    return script


def craft_v4_candidate(index: int = 1, batch_id: str = "batch-craft-v4") -> dict:
    script = craft_v3_candidate(index, batch_id)
    script["schema_version"] = 4
    script["argument_engine"] = {
        "audience_takeaway": "写着自愿的安排由老板提出时，拒绝成本也应由老板承担",
        "common_belief": "员工不愿参加就直接拒绝",
        "non_obvious_claim": "自愿不能只免除老板责任，还要降低员工拒绝的代价",
        "competing_truths": [
            "临时任务需要有人处理，管理者必须安排人手",
            "写明自愿就不该让拒绝者承担隐性惩罚",
        ],
        "causal_proof": [
            {
                "beat": 1,
                "new_information": "名单上的自愿由发哥亲口提出",
                "caused_action": "员工要求发哥也写下自己的选择",
            },
            {
                "beat": 2,
                "new_information": "发哥发现自己没有被列入安排",
                "caused_action": "发哥收回只让员工承担的名单",
            },
            {
                "beat": 3,
                "new_information": "客户交期仍需有人负责",
                "caused_action": "发哥改排自己并承担改期",
            },
        ],
        "fage_entanglement": "规则由发哥提出，他本人却被排除在自愿成本之外",
        "action_cost": "发哥亲自进入安排并承担客户改期",
        "ending_without_slogan": True,
    }
    return script


def attach_passing_semantic_review(script: dict) -> dict:
    packet = semantic_review.build_public_review_packet(script)
    digest = semantic_review.packet_sha256(packet)
    target = script["argument_engine"]["audience_takeaway"]
    script["semantic_review"] = {
        "packet_sha256": digest,
        "reviews": [
            {
                "role": "viewpoint",
                "input_sha256": digest,
                "target_visible": False,
                "verdict": "pass",
                "inferred_takeaway": target,
                "debate_sides": script["argument_engine"]["competing_truths"],
                "generic_moral": False,
                "evidence": ["公开对白证据"],
            },
            {
                "role": "story",
                "input_sha256": digest,
                "target_visible": False,
                "verdict": "pass",
                "opening_event": "名单已经签下",
                "midpoint_change": "发哥发现自己未承担自愿成本",
                "caused_action": "发哥重排名单",
                "removable_beats": [],
            },
            {
                "role": "persona",
                "input_sha256": digest,
                "target_visible": False,
                "verdict": "pass",
                "fage_entanglement": "规则由发哥提出",
                "visible_weakness_or_interest": "发哥起初把自己排除在外",
                "action_cost": "发哥进入安排并承担改期",
                "generic_boss_substitution": False,
            },
        ],
        "aggregate": {
            "all_pass": True,
            "target_match": True,
            "mismatch_reason": "无",
            "reviewed_at": "2026-09-02T00:00:00+08:00",
        },
    }
    return script


def passing_v4_batch() -> list[dict]:
    scripts = [
        craft_v4_candidate(index, "batch-semantic-v4")
        for index in (1, 2, 3)
    ]
    for index, script in enumerate(scripts, 1):
        script["argument_engine"]["audience_takeaway"] += f"（方向{index}）"
        script["argument_engine"]["fage_entanglement"] += f"（责任位置{index}）"
        attach_passing_semantic_review(script)
    return scripts


class SkillV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.persona = quality.read_json(PERSONA_PATH)

    def test_complete_three_candidate_batch_passes(self) -> None:
        scripts = [candidate_script(i) for i in (1, 2, 3)]
        self.assertEqual([], batch_checker.validate_batch(scripts, self.persona, []))

    def test_schema_v3_craft_batch_passes(self) -> None:
        scripts = [craft_v3_candidate(i) for i in (1, 2, 3)]
        self.assertEqual([], batch_checker.validate_batch(scripts, self.persona, []))

    def test_complete_v4_batch_passes_submission_gate(self) -> None:
        self.assertEqual(
            [],
            batch_checker.validate_batch(
                passing_v4_batch(),
                self.persona,
                [],
                required_schema_version=4,
            ),
        )

    def test_v4_submission_requires_three_v4_semantic_passes(self) -> None:
        scripts = passing_v4_batch()
        scripts[1]["semantic_review"]["aggregate"]["all_pass"] = False
        scripts[2]["semantic_review"]["aggregate"]["target_match"] = False
        failures = batch_checker.validate_batch(
            scripts,
            self.persona,
            [],
            required_schema_version=4,
        )
        self.assertTrue(
            any(
                "candidate[2] semantic review aggregate must pass" in item
                for item in failures
            )
        )
        self.assertTrue(
            any(
                "candidate[3] semantic review target must match" in item
                for item in failures
            )
        )

    def test_v4_batch_rejects_repeated_takeaway_or_responsibility(self) -> None:
        scripts = passing_v4_batch()
        for script in scripts:
            script["argument_engine"]["audience_takeaway"] = "同一个判断"
            script["argument_engine"]["fage_entanglement"] = "同一个责任位置"
        failures = batch_checker.validate_batch(
            scripts,
            self.persona,
            [],
            required_schema_version=4,
        )
        self.assertTrue(any("distinct audience takeaways" in item for item in failures))
        self.assertTrue(any("distinct fage responsibility" in item for item in failures))

    def test_v4_batch_preserves_craft_diversity_gates(self) -> None:
        scripts = passing_v4_batch()
        for script in scripts:
            script["story_blueprint"]["narrative_pattern"] = "rule_escalation"
            script["dialogue_design"] = copy.deepcopy(scripts[0]["dialogue_design"])
        failures = batch_checker.validate_batch(
            scripts,
            self.persona,
            [],
            required_schema_version=4,
        )
        self.assertIn("schema v3/v4 batch requires three distinct narrative patterns", failures)
        self.assertIn("schema v3/v4 batch requires three distinct dialogue modes", failures)

    def test_v4_submission_requires_version_four_for_all_candidates(self) -> None:
        scripts = passing_v4_batch()
        scripts[0]["schema_version"] = 3
        failures = batch_checker.validate_batch(
            scripts,
            self.persona,
            [],
            required_schema_version=4,
        )
        self.assertIn(
            "v4 submission requires schema_version 4 for all candidates",
            failures,
        )

    def test_rank_gap_names_found_ranks_and_requires_reranking(self) -> None:
        scripts = [candidate_script(index, "batch-rank-gap") for index in (1, 2, 3)]
        scripts[2]["topic_strategy"]["selection_ranking"]["final_rank"] = 4
        failures = batch_checker.validate_batch(scripts, self.persona, [])
        self.assertIn(
            "candidate batch must contain final topic ranks 1, 2, and 3; "
            "found 1, 2, 4; rerank after an explicit veto instead of silently "
            "skipping rank 3",
            failures,
        )

    def test_batch_cli_forwards_required_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for index in (1, 2, 3):
                path = Path(tmp) / f"candidate-{index}.json"
                path.write_text(
                    json.dumps(craft_v3_candidate(index), ensure_ascii=False),
                    encoding="utf-8",
                )
                paths.append(path)
            run = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "check_candidate_batch.py"),
                    "--inputs",
                    *(str(path) for path in paths),
                    "--persona",
                    str(PERSONA_PATH),
                    "--require-schema-version",
                    "4",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
        self.assertEqual(2, run.returncode)
        self.assertIn("submission requires schema_version 4", run.stdout)
        self.assertIn(
            "v4 submission requires schema_version 4 for all candidates",
            run.stdout,
        )

    def test_v3_demo_generator_warns_that_output_is_not_a_submission(self) -> None:
        expected_warning = (
            "EXAMPLE ONLY: output is not a validated or user-submitted candidate batch"
        )
        original_output_dir = demo_builder.OUTPUT_DIR
        try:
            with tempfile.TemporaryDirectory() as tmp:
                demo_builder.OUTPUT_DIR = Path(tmp)
                stdout = io.StringIO()
                stderr = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    return_code = demo_builder.main()
                self.assertEqual(0, return_code)
                self.assertEqual(expected_warning, stderr.getvalue().strip())
                self.assertEqual(3, len(list(Path(tmp).glob("candidate-*.json"))))
        finally:
            demo_builder.OUTPUT_DIR = original_output_dir

    def test_schema_v3_requires_craft_fields(self) -> None:
        script = candidate_script(1)
        script["schema_version"] = 3
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(any("narrative_pattern" in item for item in result.failures))
        self.assertTrue(any("dialogue_design" in item for item in result.failures))

    def test_schema_v4_requires_argument_engine_and_semantic_review(self) -> None:
        script = craft_v4_candidate()
        script.pop("argument_engine")
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(any("argument_engine" in item for item in result.failures))
        self.assertTrue(any("semantic_review" in item for item in result.failures))

    def test_schema_v3_remains_readable_but_cannot_satisfy_v4_submission(self) -> None:
        script = craft_v3_candidate()
        self.assertFalse(
            any(
                "schema_version must" in item
                for item in quality.validate_script(script, self.persona, []).failures
            )
        )
        result = quality.validate_script(
            script,
            self.persona,
            [],
            required_schema_version=4,
        )
        self.assertTrue(any("requires schema_version 4" in item for item in result.failures))

    def test_public_review_packet_excludes_internal_author_notes(self) -> None:
        script = craft_v4_candidate()
        script["primary_hook"]["core_viewpoint"] = "钩子对象中的内部答案"
        script["full_dialogue"][0]["story_blueprint"] = "对白对象中的作者蓝图"
        packet = semantic_review.build_public_review_packet(script)
        text = json.dumps(packet, ensure_ascii=False)
        for forbidden in (
            "core_viewpoint",
            "argument_engine",
            "story_blueprint",
            "topic_strategy",
            "creative_diagnostics",
        ):
            self.assertNotIn(forbidden, text)

    def test_public_review_packet_hash_uses_canonical_utf8_json(self) -> None:
        value = {"b": "中文", "a": 1}
        self.assertEqual('{"a":1,"b":"中文"}', semantic_review.canonical_json(value))
        self.assertEqual(
            "db1e1d174330db0f00974178407b16d090326f28edd3798338fe91c275dc5466",
            semantic_review.packet_sha256(value),
        )

    def test_semantic_review_cli_outputs_only_packet_or_hash(self) -> None:
        source = {
            "candidate": {"candidate_id": "candidate-1"},
            "workflow": {"revision_id": "r1"},
            "title": "标题",
            "cover_title": "封面",
            "primary_hook": {"voiceover": "开场"},
            "full_dialogue": [{"speaker": "发哥", "line": "公开对白"}],
            "segments": [{"visual_action": "公开动作", "screen_audio": "公开字幕"}],
            "argument_engine": {"audience_takeaway": "禁止泄漏"},
        }
        expected_packet = {
            "packet_version": 1,
            "candidate_id": "candidate-1",
            "revision_id": "r1",
            "title": "标题",
            "cover_title": "封面",
            "primary_hook": {"voiceover": "开场"},
            "full_dialogue": [{"speaker": "发哥", "line": "公开对白"}],
            "visual_actions": ["公开动作"],
            "on_screen_text": ["公开字幕"],
        }
        expected_json = json.dumps(
            expected_packet,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        expected_hash = hashlib.sha256(expected_json.encode("utf-8")).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "candidate.json"
            source_path.write_text(
                json.dumps(source, ensure_ascii=False),
                encoding="utf-8",
            )
            packet_run = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "semantic_review.py"),
                    "--input",
                    str(source_path),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            hash_run = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "semantic_review.py"),
                    "--input",
                    str(source_path),
                    "--hash-only",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
        self.assertEqual(0, packet_run.returncode)
        self.assertEqual(expected_json, packet_run.stdout.strip())
        self.assertEqual("", packet_run.stderr)
        self.assertEqual(0, hash_run.returncode)
        self.assertEqual(expected_hash, hash_run.stdout.strip())
        self.assertEqual("", hash_run.stderr)

    def test_hidden_core_viewpoint_cannot_prove_public_escalation(self) -> None:
        script = craft_v3_candidate()
        script["topic_strategy"]["escalation_event"] = "只有内部观点写到的全国身份危机"
        script["core_viewpoint"] = "只有内部观点写到的全国身份危机"
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(
            any(
                "escalation_event is not evidenced" in item
                for item in result.failures
            )
        )

    def test_v4_rejects_generic_or_identical_argument(self) -> None:
        script = craft_v4_candidate()
        script["argument_engine"]["audience_takeaway"] = "老板要讲道理"
        script["argument_engine"]["non_obvious_claim"] = script["argument_engine"][
            "common_belief"
        ]
        failures = semantic_review.validate_argument_engine(script)
        self.assertIn(
            "argument_engine.audience_takeaway is a generic moral",
            failures,
        )
        self.assertIn(
            "argument_engine.non_obvious_claim must advance beyond common_belief",
            failures,
        )

    def test_v4_requires_three_causal_beats_and_visible_fage_cost(self) -> None:
        script = craft_v4_candidate()
        script["argument_engine"]["causal_proof"] = script["argument_engine"][
            "causal_proof"
        ][:2]
        script["argument_engine"]["action_cost"] = "负责处理"
        failures = semantic_review.validate_argument_engine(script)
        self.assertTrue(any("exactly three causal beats" in item for item in failures))
        self.assertTrue(any("action_cost must be concrete" in item for item in failures))

    def test_v4_argument_engine_requires_complete_distinct_structure(self) -> None:
        script = craft_v4_candidate()
        engine = script["argument_engine"]
        engine.pop("fage_entanglement")
        engine["competing_truths"] = ["同一个立场", "同一个立场"]
        engine["causal_proof"] = [
            {"beat": 1, "new_information": "", "caused_action": "行动"},
            {"beat": "2", "new_information": "信息", "caused_action": "行动"},
            {"beat": 3, "new_information": "信息", "caused_action": ""},
        ]
        engine["ending_without_slogan"] = False
        failures = semantic_review.validate_argument_engine(script)
        self.assertTrue(any("fage_entanglement" in item for item in failures))
        self.assertTrue(any("two distinct positions" in item for item in failures))
        self.assertTrue(any("integers 1, 2, and 3" in item for item in failures))
        self.assertTrue(any("requires new_information and caused_action" in item for item in failures))
        self.assertTrue(any("ending_without_slogan must be true" in item for item in failures))

    def test_valid_v4_argument_engine_passes(self) -> None:
        self.assertEqual(
            [],
            semantic_review.validate_argument_engine(craft_v4_candidate()),
        )

    def test_v4_argument_engine_rejects_blank_required_text(self) -> None:
        script = craft_v4_candidate()
        script["argument_engine"]["audience_takeaway"] = ""
        script["argument_engine"]["common_belief"] = "  "
        script["argument_engine"]["non_obvious_claim"] = None
        failures = semantic_review.validate_argument_engine(script)
        for field in (
            "audience_takeaway",
            "common_belief",
            "non_obvious_claim",
        ):
            self.assertIn(f"argument_engine.{field} is required", failures)

    def test_quality_cli_forwards_required_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "candidate-v3.json"
            source_path.write_text(
                json.dumps(craft_v3_candidate(), ensure_ascii=False),
                encoding="utf-8",
            )
            run = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "check_script_quality.py"),
                    "--input",
                    str(source_path),
                    "--persona",
                    str(PERSONA_PATH),
                    "--require-schema-version",
                    "4",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
        self.assertEqual(2, run.returncode)
        self.assertIn("submission requires schema_version 4", run.stdout)

    def test_valid_v4_semantic_review_passes(self) -> None:
        script = attach_passing_semantic_review(craft_v4_candidate())
        self.assertEqual([], semantic_review.validate_argument_engine(script))
        self.assertEqual([], semantic_review.validate_semantic_review(script))

    def test_v4_rejects_stale_or_target_leaking_reviews(self) -> None:
        script = attach_passing_semantic_review(craft_v4_candidate())
        script["semantic_review"]["packet_sha256"] = "0" * 64
        script["semantic_review"]["reviews"][0]["input_sha256"] = "0" * 64
        script["semantic_review"]["reviews"][1]["target_visible"] = True
        failures = semantic_review.validate_semantic_review(script)
        self.assertTrue(any("packet hash differs" in item for item in failures))
        self.assertTrue(any("input hash differs" in item for item in failures))
        self.assertTrue(any("must not see target" in item for item in failures))

    def test_v4_rejects_any_review_failure_or_target_mismatch(self) -> None:
        script = attach_passing_semantic_review(craft_v4_candidate())
        script["semantic_review"]["reviews"][2]["verdict"] = "reject"
        script["semantic_review"]["aggregate"]["target_match"] = False
        failures = semantic_review.validate_semantic_review(script)
        self.assertTrue(any("all three reviews must pass" in item for item in failures))
        self.assertTrue(any("target_match must be true" in item for item in failures))

    def test_v4_semantic_review_requires_exact_roles_and_role_fields(self) -> None:
        script = attach_passing_semantic_review(craft_v4_candidate())
        reviews = script["semantic_review"]["reviews"]
        reviews[2]["role"] = "story"
        reviews[0]["evidence"] = []
        reviews[1]["midpoint_change"] = ""
        reviews[1]["removable_beats"] = ["中段可以删除"]
        reviews[2]["generic_boss_substitution"] = True
        failures = semantic_review.validate_semantic_review(script)
        self.assertTrue(any("exactly viewpoint, story, and persona" in item for item in failures))
        self.assertTrue(any("viewpoint evidence" in item for item in failures))
        self.assertTrue(any("story midpoint_change" in item for item in failures))
        self.assertTrue(any("story removable_beats must be empty" in item for item in failures))

    def test_v4_semantic_review_requires_valid_aggregate(self) -> None:
        script = attach_passing_semantic_review(craft_v4_candidate())
        aggregate = script["semantic_review"]["aggregate"]
        aggregate["all_pass"] = False
        aggregate["mismatch_reason"] = "仍写着不一致"
        aggregate["reviewed_at"] = "not-a-time"
        failures = semantic_review.validate_semantic_review(script)
        self.assertTrue(any("aggregate all_pass must be true" in item for item in failures))
        self.assertTrue(any("mismatch_reason must be 无" in item for item in failures))
        self.assertTrue(any("reviewed_at must be ISO-8601" in item for item in failures))

    def test_v4_semantic_review_rejects_generic_persona_review(self) -> None:
        script = attach_passing_semantic_review(craft_v4_candidate())
        persona = script["semantic_review"]["reviews"][2]
        persona["visible_weakness_or_interest"] = ""
        persona["action_cost"] = ""
        persona["generic_boss_substitution"] = True
        failures = semantic_review.validate_semantic_review(script)
        self.assertTrue(any("persona visible_weakness_or_interest" in item for item in failures))
        self.assertTrue(any("persona action_cost" in item for item in failures))
        self.assertTrue(any("generic_boss_substitution must be false" in item for item in failures))

    def test_quality_gate_includes_semantic_review_failures(self) -> None:
        script = attach_passing_semantic_review(craft_v4_candidate())
        script["semantic_review"]["reviews"][0]["generic_moral"] = True
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(
            any("viewpoint generic_moral must be false" in item for item in result.failures)
        )

    def test_required_v4_submission_runs_semantic_gate_for_v3_input(self) -> None:
        result = quality.validate_script(
            craft_v3_candidate(),
            self.persona,
            [],
            required_schema_version=4,
        )
        self.assertTrue(any("semantic_review object" in item for item in result.failures))

    def test_schema_v3_batch_rejects_repeated_narrative_pattern(self) -> None:
        scripts = [craft_v3_candidate(i) for i in (1, 2, 3)]
        for script in scripts:
            script["story_blueprint"]["narrative_pattern"] = "rule_escalation"
        failures = batch_checker.validate_batch(scripts, self.persona, [])
        self.assertIn("schema v3/v4 batch requires three distinct narrative patterns", failures)

    def test_schema_v3_batch_rejects_repeated_dialogue_mode(self) -> None:
        scripts = [craft_v3_candidate(i) for i in (1, 2, 3)]
        for script in scripts:
            script["dialogue_design"] = copy.deepcopy(scripts[0]["dialogue_design"])
        failures = batch_checker.validate_batch(scripts, self.persona, [])
        self.assertIn("schema v3/v4 batch requires three distinct dialogue modes", failures)

    def test_schema_v3_rejects_long_explanation_line(self) -> None:
        script = craft_v3_candidate(1)
        script["full_dialogue"][1]["line"] = "这件事情需要我们从多个角度进行综合判断以后再形成一套更加完整而且稳妥的处理方案。"
        script["segments"][0]["dialogue"] = "".join(
            f"{x['speaker']}：{x['line']}" for x in script["full_dialogue"][:2]
        )
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(any("exceeds 32" in item for item in result.failures))

    def test_schema_v3_rejects_ungrounded_empty_jargon(self) -> None:
        script = craft_v3_candidate(2)
        script["full_dialogue"][2]["line"] = "上面只说要加强协同。"
        script["full_dialogue"][3]["line"] = "这个事情确实很重要。"
        script["segments"][1]["dialogue"] = "".join(
            f"{x['speaker']}：{x['line']}" for x in script["full_dialogue"][2:8]
        )
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(any("empty jargon" in item for item in result.failures))

    def test_keyword_rebound_requires_both_sides(self) -> None:
        script = craft_v3_candidate(1)
        script["dialogue_design"]["anchor_word"] = "行政"
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(any("anchor must appear" in item for item in result.failures))

    def test_batch_requires_exactly_three(self) -> None:
        scripts = [candidate_script(i) for i in (1, 2)]
        failures = batch_checker.validate_batch(scripts, self.persona, [])
        self.assertIn("candidate batch must contain exactly 3 complete scripts", failures)

    def test_three_skin_swaps_fail_difference_gate(self) -> None:
        scripts = [candidate_script(1) for _ in range(3)]
        for i, script in enumerate(scripts, 1):
            script["candidate"]["candidate_id"] = f"same-c{i}"
            script["candidate"]["position"] = i
            script["meta"]["topic_id"] = f"same-topic-{i}"
        failures = batch_checker.validate_batch(scripts, self.persona, [])
        self.assertTrue(any("difference axis is identical" in item for item in failures))
        self.assertTrue(any("cosmetic changes" in item for item in failures))

    def test_authorized_fictional_action_is_allowed(self) -> None:
        result = quality.validate_script(candidate_script(1), self.persona, [])
        self.assertTrue(result.ok, result.failures)

    def test_unknown_family_fact_is_forbidden(self) -> None:
        script = candidate_script(1)
        script["full_dialogue"][1]["line"] = "我老婆以前也让我周六加班。"
        script["segments"][0]["dialogue"] = "".join(
            f"{x['speaker']}：{x['line']}" for x in script["full_dialogue"][:2]
        )
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(any("unconfirmed biography claim" in item for item in result.failures))

    def test_lecture_only_script_fails(self) -> None:
        script = candidate_script(1)
        script["persona_evidence"]["visible_action"] = "发哥认真讲道理"
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(any("testable action" in item for item in result.failures))

    def test_universal_conclusion_fails(self) -> None:
        script = candidate_script(1)
        script["story_blueprint"]["plain_conclusion"] = "办法总比困难多"
        script["full_dialogue"][-1]["line"] = "办法总比困难多"
        script["segments"][-1]["dialogue"] = "发哥：办法总比困难多"
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(any("universal conclusion" in item for item in result.failures))

    def test_explicit_feedback_record_and_read(self) -> None:
        event = {
            "event_type": "candidate_evaluation",
            "feedback_id": "feedback-test-1",
            "candidate_id": "candidate-1",
            "revision_id": "r1",
            "evaluation": "minor_revision",
            "reason_codes": ["DIALOGUE_UNNATURAL"],
            "preserve": ["保留划掉排班表的动作"],
            "avoid": ["避开最后一段长解释"],
            "user_quote": "动作能拍，结尾短一点",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "event.json"
            ledger_path = root / "feedback.jsonl"
            input_path.write_text(json.dumps(event, ensure_ascii=False), encoding="utf-8")
            args = Namespace(input=input_path, feedback_ledger=ledger_path)
            self.assertEqual(0, history_manager.command_record_feedback(args))
            rows = history_manager.read_feedback(ledger_path)
            context = history_manager.feedback_context(rows)
            self.assertEqual(["保留划掉排班表的动作"], context["keep"])
            self.assertEqual(["避开最后一段长解释"], context["avoid"])

    def test_silence_is_not_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "feedback.jsonl"
            path.write_text("", encoding="utf-8")
            rows = history_manager.read_feedback(path)
            self.assertEqual([], rows)
            self.assertEqual(["无"], history_manager.feedback_context(rows)["keep"])

    def test_old_ledger_remains_read_only_when_recording_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "old.jsonl"
            feedback = root / "feedback.jsonl"
            event_path = root / "event.json"
            old.write_text('{"event_type":"script","title":"old"}\n', encoding="utf-8")
            before = hashlib.sha256(old.read_bytes()).hexdigest()
            event_path.write_text(
                json.dumps(
                    {
                        "event_type": "candidate_selection",
                        "feedback_id": "selection-1",
                        "batch_id": "batch-1",
                        "candidate_id": "candidate-1",
                        "user_quote": "选第一条",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            history_manager.command_record_feedback(
                Namespace(input=event_path, feedback_ledger=feedback)
            )
            self.assertEqual(before, hashlib.sha256(old.read_bytes()).hexdigest())

    def test_word_generation_blocked_before_confirmation(self) -> None:
        with self.assertRaises(SystemExit):
            docx_generator.validate_minimum(candidate_script(1))

    def test_word_generation_allowed_after_confirmation(self) -> None:
        script = candidate_script(1)
        script["candidate"]["selection_status"] = "selected"
        script["workflow"]["stage"] = "copy_confirmed"
        script["workflow"]["selected_candidate_id"] = script["candidate"]["candidate_id"]
        confirmation = script["workflow"]["copy_confirmation"]
        confirmation.update(
            {
                "confirmed": True,
                "confirmed_revision_id": "r1",
                "confirmed_at": "2026-09-01T12:00:00+08:00",
                "user_quote": "确认，按这版生成Word",
            }
        )
        confirmation["content_sha256"] = docx_generator.confirmation_content_sha256(script)
        docx_generator.validate_minimum(script)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "confirmed.docx"
            docx_generator.build_document(script).save(output)
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 0)

    def test_content_change_invalidates_word_confirmation(self) -> None:
        script = candidate_script(1)
        script["candidate"]["selection_status"] = "selected"
        script["workflow"]["stage"] = "copy_confirmed"
        script["workflow"]["selected_candidate_id"] = script["candidate"]["candidate_id"]
        confirmation = script["workflow"]["copy_confirmation"]
        confirmation.update(
            {
                "confirmed": True,
                "confirmed_revision_id": "r1",
                "confirmed_at": "2026-09-01T12:00:00+08:00",
                "user_quote": "确认生成",
            }
        )
        confirmation["content_sha256"] = docx_generator.confirmation_content_sha256(script)
        script["full_dialogue"][-1]["line"] += "再加一句。"
        with self.assertRaises(SystemExit):
            docx_generator.validate_word_confirmation(script)

    def test_output_version_does_not_invalidate_copy_confirmation(self) -> None:
        script = candidate_script(1)
        script["candidate"]["selection_status"] = "selected"
        script["workflow"]["stage"] = "copy_confirmed"
        script["workflow"]["selected_candidate_id"] = script["candidate"]["candidate_id"]
        confirmation = script["workflow"]["copy_confirmation"]
        confirmation.update(
            {
                "confirmed": True,
                "confirmed_revision_id": "r1",
                "confirmed_at": "2026-09-01T12:00:00+08:00",
                "user_quote": "确认生成",
            }
        )
        confirmation["content_sha256"] = docx_generator.confirmation_content_sha256(script)
        script["meta"]["version"] = "V1"
        docx_generator.validate_word_confirmation(script)

    def test_stale_feedback_context_fails(self) -> None:
        script = candidate_script(1)
        rows = [
            {
                "event_type": "candidate_evaluation",
                "feedback_id": "latest-1",
                "preserve": ["动作"],
                "avoid": ["演讲"],
            }
        ]
        result = quality.validate_script(script, self.persona, rows)
        self.assertTrue(any("stale" in item for item in result.failures))

    def test_history_similarity_rejects_reused_dialogue(self) -> None:
        script = candidate_script(1)
        body = "\n".join(
            f"{x['speaker']}：{x['line']}" for x in script["full_dialogue"]
        )
        old = {
            "event_type": "script",
            "status": "existing",
            "topic_id": "old-same",
            "title": script["title"],
            "category": script["content_signature"]["category"],
            "premise": script["content_signature"]["premise"],
            "viewpoint": script["core_viewpoint"],
            "hook": script["primary_hook"]["voiceover"],
            "hook_mechanism": script["content_signature"]["hook_mechanism"],
            "plot_device": script["content_signature"]["plot_device"],
            "ending_type": script["content_signature"]["ending_type"],
            "body_text": body,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_path = root / "candidate.json"
            ledger_path = root / "history.jsonl"
            candidate_path.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
            ledger_path.write_text(json.dumps(old, ensure_ascii=False) + "\n", encoding="utf-8")
            process = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "check_script_similarity.py"),
                    "--input",
                    str(candidate_path),
                    "--ledger",
                    str(ledger_path),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(2, process.returncode)
            self.assertIn("RESULT: FAIL", process.stdout)

    def test_publication_metrics_need_source_and_date(self) -> None:
        with self.assertRaises(SystemExit):
            history_manager.validate_feedback_event(
                {
                    "event_type": "publication_metrics",
                    "feedback_id": "metric-1",
                    "user_quote": "播放一千",
                    "metrics": {"plays": 1000},
                }
            )

    def test_persona_model_rejects_vague_fields(self) -> None:
        persona = copy.deepcopy(self.persona)
        persona["stable_expression"][0]["pattern"] = "真实亲切"
        result = quality.validate_script(candidate_script(1), persona, [])
        self.assertTrue(
            any("persona.stable_expression" in item and "too vague" in item for item in result.failures)
        )

    def test_feedback_context_cannot_fabricate_keep_or_avoid(self) -> None:
        script = candidate_script(1)
        script["candidate"]["feedback_context"].update(
            {
                "latest_feedback_ids": ["feedback-latest"],
                "keep": ["模型自行猜的优点"],
                "avoid": ["模型自行猜的问题"],
            }
        )
        rows = [
            {
                "event_type": "candidate_evaluation",
                "feedback_id": "feedback-latest",
                "preserve": ["保留用户明确说的动作"],
                "avoid": ["避开用户明确说的长结尾"],
            }
        ]
        result = quality.validate_script(script, self.persona, rows)
        self.assertTrue(
            any("differs from the latest explicit ledger" in item for item in result.failures)
        )

    def test_irrelevant_visible_action_still_fails_lecture_gate(self) -> None:
        script = candidate_script(1)
        script["persona_evidence"]["visible_action"] = "发哥改了坐姿"
        script["segments"][1]["visual_action"] = "发哥改了坐姿"
        script["segments"][2]["visual_action"] = "发哥改了坐姿"
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(
            any("does not drive the public story payoff" in item for item in result.failures)
        )

    def test_all_legacy_history_write_commands_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "history.jsonl"
            old.write_text('{"event_type":"script","title":"old"}\n', encoding="utf-8")
            before = hashlib.sha256(old.read_bytes()).hexdigest()
            commands = [
                (
                    history_manager.command_record_topics,
                    Namespace(input=root / "unused.json", ledger=old),
                ),
                (
                    history_manager.command_set_status,
                    Namespace(ledger=old, topic_id="old", status="selected", note=""),
                ),
                (
                    history_manager.command_record_script,
                    Namespace(input=root / "unused.json", ledger=old, document=None),
                ),
            ]
            for command, args in commands:
                with self.assertRaises(SystemExit):
                    command(args)
            self.assertEqual(before, hashlib.sha256(old.read_bytes()).hexdigest())

    def test_init_does_not_create_historical_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp) / "data"
            self.assertEqual(0, history_manager.command_init(Namespace(data_root=data_root)))
            self.assertFalse((data_root / "选题台账.jsonl").exists())
            self.assertTrue((data_root / "反馈台账.jsonl").exists())

    def test_default_persona_supports_non_workplace_scenes_and_partners(self) -> None:
        persona = history_manager.default_persona()
        frame = persona["production_frame"]
        self.assertIn("家中公共空间", frame["locations"])
        self.assertIn("朋友", frame["default_format"])
        self.assertIn("亲戚", frame["default_format"])
        pairs = {item["pair"] for item in persona["comedy_relationships"]}
        self.assertIn("发哥—朋友", pairs)
        self.assertIn("发哥—亲戚", pairs)

    def test_workspace_persona_supports_non_workplace_scenes_and_partners(self) -> None:
        frame = self.persona["production_frame"]
        self.assertIn("家中公共空间", frame["locations"])
        self.assertIn("朋友", frame["default_format"])
        self.assertIn("亲戚", frame["default_format"])
        pairs = {item["pair"] for item in self.persona["comedy_relationships"]}
        self.assertIn("发哥—朋友", pairs)
        self.assertIn("发哥—亲戚", pairs)

    def test_short_intro_checker_is_retired(self) -> None:
        process = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_topic_similarity.py")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(2, process.returncode)
        self.assertIn("Short topic-introduction batches are retired", process.stdout)

    def test_public_tension_topic_strategy_passes(self) -> None:
        result = quality.validate_script(candidate_script(2), self.persona, [])
        self.assertFalse(
            [item for item in result.failures if item.startswith("topic_strategy")],
            result.failures,
        )

    def test_routine_topic_cannot_invent_hidden_escalation(self) -> None:
        script = candidate_script(1)
        script["topic_strategy"]["escalation_event"] = "全国关注的职业身份危机"
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(any("escalation_event is not evidenced" in item for item in result.failures))

    def test_self_declared_hot_topic_needs_dated_source(self) -> None:
        script = candidate_script(1)
        script["topic_strategy"]["topic_mode"] = "current_issue"
        script["topic_strategy"]["heat_basis"] = {
            "status": "dated_source",
            "source_ref": "模型声称最近很火",
            "claim": "当前热点",
        }
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(any("dated heat basis" in item for item in result.failures))

    def test_current_issue_with_dated_web_source_passes(self) -> None:
        script = candidate_script(1)
        source_url = "https://www.stdaily.com/web/gdxw/2026-08/26/content_569915.html"
        script["topic_strategy"]["topic_mode"] = "current_issue"
        script["topic_strategy"]["heat_basis"] = {
            "status": "dated_source",
            "source_ref": source_url,
            "claim": "2026年8月公开发布的AI就业调查",
        }
        script["research_sources"][0].update(
            {
                "source_kind": "web",
                "title": "调查显示：超六成职场人担心被更懂AI的人取代",
                "locator": source_url,
                "source_date": "2026-08-26",
                "retrieved_at": "2026-09-01",
                "metrics_provided": False,
                "metric_note": "公开议题证据，不是用户提供的发布数据",
            }
        )
        result = quality.validate_script(script, self.persona, [])
        self.assertFalse(
            [item for item in result.failures if "heat basis" in item or "current_issue" in item],
            result.failures,
        )

    def test_novelty_break_cannot_repeat_expected_pattern(self) -> None:
        script = candidate_script(1)
        expected = script["topic_strategy"]["novelty_break"]["expected_pattern"]
        script["topic_strategy"]["novelty_break"]["story_break"] = expected
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(any("only repeats the expected pattern" in item for item in result.failures))

    def test_batch_rejects_one_repeated_public_question(self) -> None:
        scripts = [candidate_script(index, "batch-topic-gate") for index in (1, 2, 3)]
        for script in scripts:
            script["topic_strategy"]["public_question"] = "老板是否应该替员工做出所有困难决定？"
        failures = batch_checker.validate_batch(scripts, self.persona, [])
        self.assertTrue(any("three distinct public questions" in item for item in failures))

    def test_broad_pool_rejects_one_macro_theme(self) -> None:
        scripts = [candidate_script(index, "batch-theme-collapse") for index in (1, 2, 3)]
        for script in scripts:
            script["topic_strategy"]["macro_theme"] = "technology_and_work"
        failures = batch_checker.validate_batch(scripts, self.persona, [])
        self.assertTrue(any("broad_pool requires three distinct macro themes" in item for item in failures))

    def test_category_focus_still_needs_two_macro_themes(self) -> None:
        scripts = [candidate_script(index, "batch-focused-collapse") for index in (1, 2, 3)]
        for script in scripts:
            script["candidate"]["research_scope"] = {
                "mode": "category_focus",
                "focus_label": "AI与中年成长",
                "basis": "任务书指定盲评分类",
            }
            script["topic_strategy"]["macro_theme"] = "technology_and_work"
        failures = batch_checker.validate_batch(scripts, self.persona, [])
        self.assertTrue(any("category_focus requires at least two distinct macro themes" in item for item in failures))

    def test_revision_feedback_round_trips_new_version(self) -> None:
        row = history_manager.validate_feedback_event(
            {
                "event_type": "revision",
                "feedback_id": "revision-test-1",
                "candidate_id": "candidate-1",
                "from_revision": "r1",
                "to_revision": "r2",
                "changes": ["重写开场冲突", "缩短结尾"],
                "user_quote": "开场重写，结尾短一点",
            }
        )
        self.assertEqual("r1", row["from_revision"])
        self.assertEqual("r2", row["to_revision"])
        self.assertEqual(2, len(row["changes"]))

    def test_duplicate_feedback_id_is_rejected(self) -> None:
        event = {
            "event_type": "candidate_selection",
            "feedback_id": "selection-duplicate",
            "batch_id": "batch-1",
            "candidate_id": "candidate-1",
            "user_quote": "选第一条",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "event.json"
            ledger_path = root / "feedback.jsonl"
            input_path.write_text(json.dumps(event, ensure_ascii=False), encoding="utf-8")
            args = Namespace(input=input_path, feedback_ledger=ledger_path)
            self.assertEqual(0, history_manager.command_record_feedback(args))
            with self.assertRaises(SystemExit):
                history_manager.command_record_feedback(args)

    def test_heat_signal_has_largest_weight_in_topic_ranking(self) -> None:
        def prospect(topic_id: str, minutes: int) -> dict:
            return {
                "topic_id": topic_id,
                "title": topic_id,
                "heat_evidence": {
                    "freshness_days": 2,
                    "evidence_tier": "archived_hotlist",
                    "hotlist_minutes": minutes,
                    "distinct_domains": 2,
                    "derivative_work_count": 1,
                },
                "audience_conflict_score": 70,
                "fage_fit_score": 70,
                "shootability_score": 70,
                "veto_reasons": [],
            }

        prospects = [prospect("low", 5), prospect("mid", 30), prospect("high", 300)]
        prospects.extend(prospect(f"filler-{index}", 0) for index in range(6))
        result = rank_topics.rank_pool({"pool_id": "pool-heat", "prospects": prospects})
        self.assertEqual(["high", "mid"], [item["topic_id"] for item in result["ranked"][:2]])
        self.assertEqual(0.45, result["weights"]["heat"])

    def test_explicit_feedback_veto_excludes_even_hottest_topic(self) -> None:
        prospects = []
        for index, minutes in enumerate((400, 60, 20, 15, 10, 8, 6, 4, 2), 1):
            prospects.append(
                {
                    "topic_id": f"topic-{index}",
                    "title": f"题{index}",
                    "heat_evidence": {
                        "freshness_days": 1,
                        "evidence_tier": "archived_hotlist",
                        "hotlist_minutes": minutes,
                        "distinct_domains": 3,
                        "derivative_work_count": 2,
                    },
                    "audience_conflict_score": 80,
                    "fage_fit_score": 80,
                    "shootability_score": 80,
                    "veto_reasons": ["谢总已明确否决"] if index == 1 else [],
                }
            )
        result = rank_topics.rank_pool({"pool_id": "pool-veto", "prospects": prospects})
        self.assertEqual("topic-1", result["vetoed"][0]["topic_id"])
        self.assertNotIn("topic-1", [item["topic_id"] for item in result["ranked"]])

    def test_quality_rejects_tampered_heat_score(self) -> None:
        script = candidate_script(1)
        script["topic_strategy"]["selection_ranking"]["heat_score"] = 99
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(any("heat_score does not match" in item for item in result.failures))

    def test_batch_requires_scores_to_follow_final_topic_ranks(self) -> None:
        scripts = [candidate_script(index, "batch-rank-order") for index in (1, 2, 3)]
        scripts[0]["topic_strategy"]["selection_ranking"]["final_rank"] = 3
        scripts[2]["topic_strategy"]["selection_ranking"]["final_rank"] = 1
        failures = batch_checker.validate_batch(scripts, self.persona, [])
        self.assertTrue(any("descending selection_score" in item for item in failures))

    def test_selected_refinement_requires_related_work_review(self) -> None:
        script = candidate_script(1)
        script["candidate"]["selection_status"] = "selected"
        script["workflow"]["stage"] = "refined"
        script["workflow"]["selected_candidate_id"] = script["candidate"]["candidate_id"]
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(any("requires creative_adaptation" in item for item in result.failures))

    def test_adoption_disclosure_must_name_adopted_work(self) -> None:
        script = candidate_script(1)
        script["candidate"]["selection_status"] = "selected"
        script["workflow"]["stage"] = "refined"
        script["workflow"]["selected_candidate_id"] = script["candidate"]["candidate_id"]
        links = ["https://example.com/work-a", "https://example.org/work-b"]
        for index, link in enumerate(links, 1):
            script["research_sources"].append(
                {
                    "source_kind": "web",
                    "title": f"相关作品{index}",
                    "locator": link,
                    "source_date": "2026-08-31",
                    "retrieved_at": "2026-09-01",
                    "metrics_provided": False,
                    "metric_note": "相关二创，不是用户发布数据",
                    "borrowed_mechanism": "只观察冲突推进机制，不复制对白",
                }
            )
        script["creative_adaptation"] = {
            "reviewed_works": [
                {
                    "title": "相关作品1",
                    "locator": links[0],
                    "decision": "adopted",
                    "observed_mechanism": "用连续代价推进冲突",
                    "adopted_mechanism": "借连续代价推进，不借原句",
                    "copyright_boundary": "不复制完整情节、对白和标志表达",
                },
                {
                    "title": "相关作品2",
                    "locator": links[1],
                    "decision": "observe_only",
                    "observed_mechanism": "用人物体面形成迟疑",
                    "adopted_mechanism": "无",
                    "copyright_boundary": "只观察结构，不复制文字",
                },
            ],
            "adoption_disclosure": "采用了一个相关作品的结构",
        }
        result = quality.validate_script(script, self.persona, [])
        self.assertTrue(any("disclosure must name" in item for item in result.failures))

    def test_prop_reveal_cannot_change_document_semantics(self) -> None:
        script = candidate_script(1)
        script["candidate"]["feedback_context"] = {
            "read_at": "2026-09-01T22:00:00+08:00",
            "latest_feedback_ids": ["feedback-prop-logic"],
            "keep": ["保留签字反转"],
            "avoid": ["前一句明确点名工资预支单，后一句把同一道具当请假单，造成前后逻辑矛盾"],
            "publication_data": "无用户提供的发布数据",
        }
        script["full_dialogue"][1]["line"] = "工资预支单给我。"
        script["full_dialogue"][-1]["line"] = "我批你一天假，三十五万一分不批。"
        script["segments"][0]["dialogue"] = "".join(
            f"{x['speaker']}：{x['line']}" for x in script["full_dialogue"][:2]
        )
        script["segments"][-1]["dialogue"] = "".join(
            f"{x['speaker']}：{x['line']}" for x in script["full_dialogue"][6:]
        )
        result = quality.validate_script(script, self.persona)
        self.assertTrue(any("prop logic conflict" in item for item in result.failures))

    def test_unexplained_role_jargon_fails_after_feedback(self) -> None:
        script = candidate_script(1)
        script["candidate"]["feedback_context"] = {
            "read_at": "2026-09-01T22:00:00+08:00",
            "latest_feedback_ids": ["feedback-jargon"],
            "keep": ["保留具体处理动作"],
            "avoid": ["第三方等需要观众停顿解释、却不承担剧情作用的偏术语用词"],
            "publication_data": "无用户提供的发布数据",
        }
        script["full_dialogue"][3]["line"] += "交给第三方看。"
        script["segments"][1]["dialogue"] = "".join(
            f"{x['speaker']}：{x['line']}" for x in script["full_dialogue"][2:6]
        )
        result = quality.validate_script(script, self.persona)
        self.assertTrue(
            any("unexplained role jargon" in item for item in result.failures)
        )


if __name__ == "__main__":
    unittest.main()
