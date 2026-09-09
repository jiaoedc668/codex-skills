from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOSS_SCRIPTS = ROOT / "boss-ip-video-script-writer" / "scripts"
PRODUCT_SCRIPTS = ROOT / "product-video-script-writer" / "scripts"
sys.path.insert(0, str(BOSS_SCRIPTS))

import history_manager

if (PRODUCT_SCRIPTS / "workflow.py").is_file():
    sys.path.insert(0, str(PRODUCT_SCRIPTS))
    from workflow import Workspace
else:
    Workspace = None


class SharedPreferenceContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = self.root / "shared-creative-preferences.jsonl"

    @unittest.skipUnless(Workspace, "Optional product Skill not installed; cross-skill integration only")
    def test_boss_append_is_readable_by_product_workspace(self):
        event = {
            "schema_version": 1,
            "event_id": "evt-boss-1",
            "event_type": "creative_preference",
            "occurred_at": "2026-09-08T12:00:00+08:00",
            "product_id": "shared",
            "user_quote": "用户原话：开头别绕",
            "payload": {"source_skill": "boss-ip-video-script-writer", "preference": "开头直接进入冲突"},
            "future_field": "preserve-me",
        }
        history_manager.append_shared_preference(self.ledger, event)
        product = Workspace(self.root)
        loaded = product.read_shared_preferences()
        self.assertEqual(loaded[0]["payload"]["source_skill"], "boss-ip-video-script-writer")
        self.assertEqual(loaded[0]["future_field"], "preserve-me")

    @unittest.skipUnless(Workspace, "Optional product Skill not installed; cross-skill integration only")
    def test_product_append_is_readable_by_boss(self):
        product = Workspace(self.root)
        product.initialize()
        product.record_shared_preference(
            product_id="test-product",
            source_skill="product-video-script-writer",
            preference="字幕别堆卖点",
            user_quote="用户原话：字幕不要堆卖点",
        )
        loaded = history_manager.read_shared_preferences(self.ledger)
        self.assertEqual(loaded[0]["payload"]["preference"], "字幕别堆卖点")

    def test_boss_rejects_corrupt_duplicate_and_missing_quote_events(self):
        missing_quote = {
            "schema_version": 1,
            "event_id": "evt-bad",
            "event_type": "creative_preference",
            "occurred_at": "2026-09-08T12:00:00+08:00",
            "product_id": "shared",
            "user_quote": "",
            "payload": {"source_skill": "boss-ip-video-script-writer", "preference": "开头直接"},
        }
        with self.assertRaisesRegex(ValueError, "用户原话"):
            history_manager.append_shared_preference(self.ledger, missing_quote)

        good = dict(missing_quote, user_quote="用户原话：开头直接")
        history_manager.append_shared_preference(self.ledger, good)
        with self.assertRaisesRegex(ValueError, "重复 event_id"):
            history_manager.append_shared_preference(self.ledger, good)

        self.ledger.write_text("{broken json}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "损坏"):
            history_manager.read_shared_preferences(self.ledger)

    def test_boss_cli_appends_and_reads_shared_preference(self):
        event = {
            "schema_version": 1,
            "event_id": "evt-boss-cli",
            "event_type": "creative_preference",
            "occurred_at": "2026-09-08T12:00:00+08:00",
            "product_id": "shared",
            "user_quote": "用户原话：开头别绕",
            "payload": {"source_skill": "boss-ip-video-script-writer", "preference": "开头直接进入事件"},
        }
        source = self.root / "event.json"
        source.write_text(json.dumps(event, ensure_ascii=False), encoding="utf-8")
        script = BOSS_SCRIPTS / "history_manager.py"
        written = subprocess.run(
            [sys.executable, str(script), "record-shared-preference", "--input", str(source), "--shared-ledger", str(self.ledger)],
            text=True, encoding="utf-8", capture_output=True,
        )
        self.assertEqual(written.returncode, 0, written.stderr)
        read = subprocess.run(
            [sys.executable, str(script), "recent-shared-preferences", "--shared-ledger", str(self.ledger), "--limit", "10"],
            text=True, encoding="utf-8", capture_output=True,
        )
        self.assertEqual(read.returncode, 0, read.stderr)
        self.assertEqual(json.loads(read.stdout)["event_count"], 1)


if __name__ == "__main__":
    unittest.main()
