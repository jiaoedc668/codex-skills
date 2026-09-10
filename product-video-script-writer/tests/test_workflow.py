from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = TEST_ROOT.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(TEST_ROOT))

from fixtures import brief, packet

from workflow import EventError, WorkflowError, Workspace, copy_sha256


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = Workspace(self.root)
        self.workspace.initialize()
        self.workspace.register_product(brief(), "用户原话：这是测试产品资料")

    def test_selection_revision_and_current_confirmation_gate_word(self):
        copy_v1 = packet()["candidates"][0]["full_copy"]
        self.workspace.record_selection("test-cleaner-x1", "m1", copy_v1, "用户原话：选第一条")
        self.assertFalse(self.workspace.can_generate_word("test-cleaner-x1", copy_v1))
        self.workspace.record_confirmation("test-cleaner-x1", copy_v1, "用户原话：这版完整文案确认")
        self.assertTrue(self.workspace.can_generate_word("test-cleaner-x1", copy_v1))

        copy_v2 = copy_v1 + " 我想把结尾再收短一点。"
        self.workspace.record_revision("test-cleaner-x1", copy_v2, "用户原话：把结尾收短")
        self.assertFalse(self.workspace.can_generate_word("test-cleaner-x1", copy_v2))
        self.workspace.record_confirmation("test-cleaner-x1", copy_v2, "用户原话：修改后这版确认")
        self.assertTrue(self.workspace.can_generate_word("test-cleaner-x1", copy_v2))

    def test_deleting_confirmation_event_makes_word_gate_fail(self):
        text = packet()["candidates"][0]["full_copy"]
        self.workspace.record_selection("test-cleaner-x1", "m1", text, "用户原话：选第一条")
        self.workspace.record_confirmation("test-cleaner-x1", text, "用户原话：确认")
        ledger = self.root / "feedback-ledger.jsonl"
        kept = [line for line in ledger.read_text(encoding="utf-8").splitlines() if '"copy_confirmation"' not in line]
        ledger.write_text("\n".join(kept) + "\n", encoding="utf-8")
        self.assertFalse(self.workspace.can_generate_word("test-cleaner-x1", text))

    def test_product_events_are_isolated_by_product_id(self):
        second = brief(product_id="test-cleaner-x2")
        second["product_name"] = "测试专用虚构产品净桌便携清洁器 X2"
        self.workspace.register_product(second, "用户原话：这是第二个测试产品")
        text = packet()["candidates"][0]["full_copy"]
        self.workspace.record_selection("test-cleaner-x1", "m1", text, "用户原话：选择 X1 第一条")
        self.assertEqual(len(self.workspace.events_for_product("feedback", "test-cleaner-x1")), 1)
        self.assertEqual(self.workspace.events_for_product("feedback", "test-cleaner-x2"), [])

    def test_rejection_without_reason_is_similarity_only_not_permanent_ban(self):
        event = self.workspace.record_rejection("test-cleaner-x1", "m1", "用户原话：这条不合适")
        self.assertEqual(event["payload"]["scope"], "similarity_only")
        self.assertIsNone(event["payload"]["reason_category"])

    def test_rejection_reason_is_limited_to_contract_categories(self):
        for category in ("topic", "structure", "expression", "one_off"):
            self.workspace.record_rejection("test-cleaner-x1", "m1", f"用户原话：因为{category}", category)
        with self.assertRaisesRegex(WorkflowError, "reason_category"):
            self.workspace.record_rejection("test-cleaner-x1", "m1", "用户原话：因为价格", "price")

    def test_publish_data_allows_missing_metrics(self):
        event = self.workspace.record_publish_data(
            "test-cleaner-x1",
            candidate_id="m1",
            user_quote="用户原话：发了，暂时还没有数据",
            views_24h=None,
            views_7d=None,
            recent_10_median=None,
        )
        self.assertIsNone(event["payload"]["views_24h"])
        self.assertIsNone(event["payload"]["views_7d"])
        self.assertIsNone(event["payload"]["recent_10_median"])

    def test_corrupt_event_is_reported_instead_of_ignored(self):
        path = self.root / "feedback-ledger.jsonl"
        path.write_text("{broken json}\n", encoding="utf-8")
        with self.assertRaisesRegex(EventError, "损坏"):
            self.workspace.read_events("feedback")

    def test_duplicate_event_id_across_ledgers_is_rejected(self):
        first = {
            "schema_version": 1,
            "event_id": "evt-fixed",
            "event_type": "candidate_selection",
            "occurred_at": "2026-09-08T10:00:00+08:00",
            "product_id": "test-cleaner-x1",
            "user_quote": "用户原话：选第一条",
            "payload": {"candidate_id": "m1", "copy_sha256": "abc"},
        }
        self.workspace.append_event("feedback", first)
        duplicate = copy.deepcopy(first)
        duplicate["event_type"] = "idea_used"
        with self.assertRaisesRegex(EventError, "重复 event_id"):
            self.workspace.append_event("used", duplicate)

    def test_unknown_event_fields_are_preserved(self):
        event = {
            "schema_version": 1,
            "event_id": "evt-future",
            "event_type": "future_event",
            "occurred_at": "2026-09-08T10:00:00+08:00",
            "product_id": "test-cleaner-x1",
            "user_quote": None,
            "payload": {"future_value": 7},
            "future_top_level": "kept",
        }
        self.workspace.append_event("used", event)
        loaded = self.workspace.read_events("used")[0]
        self.assertEqual(loaded["future_top_level"], "kept")
        self.assertEqual(loaded["payload"]["future_value"], 7)

    def test_user_derived_events_require_original_quote(self):
        with self.assertRaisesRegex(EventError, "用户原话"):
            self.workspace.append_event(
                "shared_preferences",
                {
                    "schema_version": 1,
                    "event_id": "evt-no-quote",
                    "event_type": "creative_preference",
                    "occurred_at": "2026-09-08T10:00:00+08:00",
                    "product_id": "test-cleaner-x1",
                    "user_quote": "",
                    "payload": {"preference": "开头更直接"},
                },
            )

    def test_shared_preference_round_trip(self):
        self.workspace.record_shared_preference(
            product_id="test-cleaner-x1",
            source_skill="product-video-script-writer",
            preference="开头更直接",
            user_quote="用户原话：开头再直接一点",
        )
        events = self.workspace.read_shared_preferences()
        self.assertEqual(events[0]["payload"]["preference"], "开头更直接")
        self.assertEqual(events[0]["payload"]["source_skill"], "product-video-script-writer")


if __name__ == "__main__":
    unittest.main()

