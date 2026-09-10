"""Positive craft learning must not invent an acceptance decision or rewrite history."""
import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import format_acceptance
import history_manager


class PositiveFeedbackTests(unittest.TestCase):
    def event(self):
        return {
            "event_type": "candidate_feedback", "feedback_id": "positive-1",
            "batch_id": "b1", "candidate_id": "c1", "revision_id": "r1",
            "format": "story", "user_quote": "这版比之前好",
            "preserve": ["系统提炼（待复验）：发哥先问工资再改口，判断随事实推进。"],
            "avoid": [],
        }

    def test_positive_feedback_keeps_quote_and_projects_mechanism_separately(self):
        source = self.event()
        row = history_manager.validate_feedback_event(source)
        self.assertEqual(source["user_quote"], row["user_quote"])
        self.assertEqual(source["preserve"], history_manager.feedback_context([row])["keep"])
        self.assertNotIn("evaluation", row)
        self.assertEqual(2, row["schema_version"])

    def test_general_praise_does_not_count_as_evaluation_or_direct_shoot(self):
        manifest = {
            "schema_version": 2, "batch_id": "b1", "format": "story",
            "submitted_at": "2026-09-10T12:00:00+08:00",
            "candidates": [{"candidate_id": f"c{i}", "revision_id": "r1"} for i in range(1, 4)],
            "root_cause": {"id": "RC1", "hypothesis": "真人感不足", "changed_layer": "dialogue", "root_level_change": False},
        }
        state = format_acceptance.derive([manifest], [self.event()])["batches"][0]
        self.assertEqual("pending", state["state"])
        self.assertEqual(0, state["evaluated_candidate_count"])
        self.assertEqual(0, state["direct_shoot_count"])
        for field in ("evaluation", "selection", "content_sha256"):
            with self.subTest(field=field), self.assertRaises(SystemExit):
                history_manager.validate_feedback_event({**self.event(), field: "invented"})

    def test_append_preserves_old_bytes_and_duplicate_failure_preserves_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "feedback.jsonl"
            original = (json.dumps({"schema_version": 1, "event_type": "candidate_selection", "feedback_id": "old", "user_quote": "选第一条"}, ensure_ascii=False) + "\n").encode("utf-8")
            ledger.write_bytes(original)
            event_file = Path(directory) / "event.json"
            event_file.write_text(json.dumps(self.event(), ensure_ascii=False), encoding="utf-8")
            args = argparse.Namespace(input=event_file, feedback_ledger=ledger)
            history_manager.command_record_feedback(args)
            appended = ledger.read_bytes()
            self.assertTrue(appended.startswith(original))
            self.assertEqual(2, len(history_manager.read_feedback(ledger)))
            with self.assertRaises(SystemExit):
                history_manager.command_record_feedback(args)
            self.assertEqual(appended, ledger.read_bytes())

    def test_feedback_requires_real_quote_and_current_candidate(self):
        for field in ("user_quote", "candidate_id", "revision_id", "batch_id"):
            with self.subTest(field=field), self.assertRaises(SystemExit):
                history_manager.validate_feedback_event({**self.event(), field: ""})


if __name__ == "__main__":
    unittest.main()
