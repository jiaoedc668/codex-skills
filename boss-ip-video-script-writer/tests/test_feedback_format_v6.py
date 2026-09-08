import importlib
import importlib.util
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import history_manager

class FormatFeedbackTests(unittest.TestCase):
    def test_format_is_preserved_and_invalid_value_rejected(self):
        e={"event_type":"candidate_selection","feedback_id":"s1","batch_id":"b1","candidate_id":"c1","user_quote":"选这条","format":"monologue"}
        self.assertEqual("monologue",history_manager.validate_feedback_event(e).get("format"))
        e["format"]="direct_dialogue_30"
        with self.assertRaises(SystemExit):history_manager.validate_feedback_event(e)

    def test_old_evaluations_cannot_count_as_new_monologue(self):
        self.assertIsNotNone(importlib.util.find_spec("format_acceptance"),"v6 feedback projection not implemented")
        m=importlib.import_module("format_acceptance")
        manifest={"schema_version":2,"batch_id":"b1","format":"monologue","submitted_at":"2026-09-07T12:00:00+08:00","candidates":[{"candidate_id":f"c{i}","revision_id":"r2"} for i in range(1,4)],"root_cause":{"id":"RC1","hypothesis":"观点缺乏具体理由","changed_layer":"argument","root_level_change":False}}
        events=[{"event_type":"candidate_evaluation","feedback_id":f"e{i}","batch_id":"b1","candidate_id":f"c{i}","revision_id":"r2","evaluation":"direct_shoot","reason_codes":["OTHER"],"preserve":["观点清楚"],"avoid":[],"user_quote":"可以拍"} for i in range(1,4)]
        state=m.derive([manifest],events)
        self.assertEqual(0,state["batches"][0]["direct_shoot_count"])
        for e in events:e["format"]="monologue"
        state=m.derive([manifest],events)
        self.assertEqual(3,state["batches"][0]["direct_shoot_count"])
        events[0]["revision_id"]="r1"
        self.assertEqual(2,m.derive([manifest],events)["batches"][0]["evaluated_candidate_count"])

if __name__=="__main__":unittest.main()
