import copy
import importlib
import importlib.util
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from v5_fixtures import valid_topic_pool,valid_persona
from test_dual_format_v6 import candidate_v6
import content_contract

def pool6():
    p=valid_topic_pool(with_unselected=True);p["schema_version"]=6
    for r in p["prospects"]:r["production_case"]["stakeholder_cost"]=r["production_case"].pop("fage_cost")
    return p

class AuthoringV6Tests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("create_candidate"),"authoring entry is not implemented")
        self.m=importlib.import_module("create_candidate")

    def test_defaults_and_derived_viewpoint(self):
        brief=self.m.prepare(pool6(),"topic-1")
        self.assertEqual("story",brief["request"]["format"])
        self.assertIsNone(brief["request"]["topic"])
        self.assertEqual(brief["topic_decision"]["fage_choice"],brief["resolved_core_viewpoint"])

    def test_explicit_request_preserved(self):
        b=self.m.prepare(pool6(),"topic-1",format="monologue",topic="家庭责任",core_viewpoint="照护应共同分担")
        self.assertEqual({"format":"monologue","topic":"家庭责任","core_viewpoint":"照护应共同分担"},b["request"])
        self.assertEqual("照护应共同分担",b["resolved_core_viewpoint"])
        with self.assertRaises(ValueError):self.m.prepare(pool6(),"topic-1",format="direct_dialogue_30")

    def test_vetoed_or_unselected_cannot_enter_writing(self):
        with self.assertRaises(ValueError):self.m.prepare(pool6(),"topic-4")

    def test_assemble_real_candidate_and_reject_mode_mismatch(self):
        b=self.m.prepare(pool6(),"topic-1",core_viewpoint=candidate_v6()["script"]["core_viewpoint"])
        c=candidate_v6()
        result=self.m.assemble(b,c,valid_persona(),[])
        self.assertEqual([],content_contract.validate_candidate(result,valid_persona(),[]).failures)
        c["format"]="monologue"
        with self.assertRaises(ValueError):self.m.assemble(b,c,valid_persona(),[])

    def test_mixed_v6_formats_rejected_by_batch(self):
        cs=[candidate_v6(),candidate_v6("monologue"),candidate_v6()]
        failures=content_contract.validate_batch(cs,valid_persona(),[],pool6())
        self.assertTrue(any("one format" in x for x in failures))

    def test_explicit_direction_is_not_silently_replaced(self):
        b=self.m.prepare(pool6(),"topic-1",core_viewpoint="不能默认妻子辞职")
        c=candidate_v6()
        with self.assertRaises(ValueError):self.m.assemble(b,c,valid_persona(),[])

    def test_explicit_topic_requires_traceable_script_evidence(self):
        c=candidate_v6()
        b=self.m.prepare(pool6(),"topic-1",topic="照护分担",core_viewpoint=c["script"]["core_viewpoint"])
        with self.assertRaises(ValueError):self.m.assemble(b,c,valid_persona(),[])
        c["request"]["topic_alignment"]={"requested_topic":"照护分担","script_excerpt":c["script"]["lines"][0]["text"],"explanation":"母亲出院后由谁照顾，是照护分担的具体处境。"}
        self.m.assemble(b,c,valid_persona(),[])
        c["request"]["topic_alignment"]["script_excerpt"]="不存在的主题证据"
        with self.assertRaises(ValueError):self.m.assemble(b,c,valid_persona(),[])

if __name__=="__main__":unittest.main()
