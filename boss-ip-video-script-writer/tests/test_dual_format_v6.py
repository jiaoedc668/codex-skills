from __future__ import annotations
import copy
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import content_contract
import select_topics
from v5_fixtures import valid_direct_candidate, valid_persona, valid_topic_pool


def candidate_v6(format="story"):
    old = valid_direct_candidate()
    judgment = "照护需要兄弟姐妹共同分担，不能默认一个人辞职。"
    return {
        "schema_version": 6,
        "candidate": old["candidate"],
        "format": format,
        "request": {"format": format, "topic": None, "core_viewpoint": None},
        "research_evidence": old["research_evidence"],
        "topic_decision": {**{k:v for k,v in old["topic_decision"].items() if k != "fage_cost"}, "stakeholder_cost": "当事人失去工资和职业积累", "fage_choice": judgment},
        "persona_continuity": old["persona_continuity"],
        "feedback_context": old["feedback_context"],
        "creative_blueprint": {
            "situation": "母亲即将出院，三名子女还没商量照护",
            "stakeholder": "朋友",
            "grievance": "别人只愿出钱却要求朋友辞职",
            "choice_and_consequence": "辞职将失去固定收入",
            "counterargument": "出院不能等商量，弟弟还要还房贷",
            "judgment": judgment,
            "next_step": "当事人今晚协商头三天白夜班，核实护工空档与费用",
            "opening_claim": judgment if format == "monologue" else "",
            "reason": "子女都有工作，离得近不等于没有损失",
            "example": "出钱与出时间都应计入照护责任",
        },
        "script": {
            "theme": "照顾母亲凭什么默认我辞职",
            "core_viewpoint": judgment,
            "lines": ([{"line_id":"L1", "speaker":"发哥", "text":judgment, "dialogue_act":"judge"},
                       {"line_id":"L2", "speaker":"发哥", "text":"出钱和出时间都算责任。先把出院三天的白班夜班商量清楚，再讨论长期怎么分。", "dialogue_act":"advise"}]
                      if format == "monologue" else
                      [{"line_id":"L1", "speaker":"朋友", "text":"我妈后天出院，我弟出钱，让我辞职照护。", "dialogue_act":"tell"},
                       {"line_id":"L2", "speaker":"发哥", "text":judgment, "dialogue_act":"judge"},
                       {"line_id":"L3", "speaker":"朋友", "text":"我今晚先问清三天谁值白班夜班，空下来的时间一起问护工。", "dialogue_act":"decide"}]),
            "key_actions": [],
            "necessary_shots": ["发哥固定中景"],
            "backstory": "朋友在休息时讲自己家中的事，发哥仅提供建议。",
            "ending": {"kind":"advice" if format == "monologue" else "decision", "consequence":"由当事人回家协商照护，尚未解决全部分工"},
        },
    }

class DualFormatContractTests(unittest.TestCase):
    def test_story_without_fage_resource_cost_is_valid(self):
        result=content_contract.validate_candidate(candidate_v6(),valid_persona(),[])
        self.assertEqual([],result.failures)

    def test_monologue_without_two_party_or_result_action_is_valid(self):
        result=content_contract.validate_candidate(candidate_v6("monologue"),valid_persona(),[])
        self.assertEqual([],result.failures)

    def test_monologue_rejects_second_speaker(self):
        c=candidate_v6("monologue");c["script"]["lines"][1]["speaker"]="朋友"
        result=content_contract.validate_candidate(c,valid_persona(),[])
        self.assertTrue(any("single speaker" in x for x in result.failures))

    def test_rejects_fage_arranging_in_backstory(self):
        c=candidate_v6();c["script"]["backstory"]="发哥已经替朋友联系了护工。"
        result=content_contract.validate_candidate(c,valid_persona(),[])
        self.assertTrue(any("boundary" in x for x in result.failures))

    def test_public_label_separates_legacy_dialogue_from_monologue(self):
        self.assertEqual("口播",content_contract.build_public_candidate(candidate_v6("monologue"))["format_label"])
        self.assertEqual("30 秒稿",content_contract.build_public_candidate(valid_direct_candidate())["duration_label"])

    def test_original_v5_is_unchanged(self):
        self.assertEqual([],content_contract.validate_candidate(valid_direct_candidate(),valid_persona(),[]).failures)

    def test_v6_topic_selection_preserves_competition(self):
        pool=valid_topic_pool(with_unselected=True)
        expected=select_topics.select_topics(pool)
        pool["schema_version"]=6
        for row in pool["prospects"]:
            case=row["production_case"];case["stakeholder_cost"]=case.pop("fage_cost")
        result=select_topics.select_topics(pool)
        self.assertEqual([r["topic_id"] for r in expected["selected"]],[r["topic_id"] for r in result["selected"]])
        pool["pairwise_decisions"]=[]
        with self.assertRaises(ValueError): select_topics.select_topics(pool)

    def test_friend_family_is_allowed_but_fage_biography_is_not(self):
        c=candidate_v6();c["script"]["lines"][0]["text"]="我老婆要上班，我妈出院后得商量谁来照顾。"
        self.assertEqual([],content_contract.validate_candidate(c,valid_persona(),[]).failures)
        c["script"]["lines"][1]["text"]="我老婆以前也遇到过。"
        self.assertTrue(any("biography" in f for f in content_contract.validate_candidate(c,valid_persona(),[]).failures))
        c=candidate_v6();c["script"]["backstory"]="发哥的妻子曾在这家医院工作。"
        self.assertTrue(any("biography" in f for f in content_contract.validate_candidate(c,valid_persona(),[]).failures))

if __name__ == "__main__": unittest.main()
