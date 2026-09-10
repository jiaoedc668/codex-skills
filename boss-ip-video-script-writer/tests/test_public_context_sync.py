from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "boss-ip-video-script-writer" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import sync_public_context


class PublicContextSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.persona = self.root / "人物设定.json"
        self.feedback = self.root / "反馈台账.jsonl"
        self.topics = self.root / "选题台账.jsonl"
        self.shared = self.root / "shared-creative-preferences.jsonl"
        self.output = self.root / "chat-context"

        self.persona.write_text(
            json.dumps(
                {
                    "schema_version": 3,
                    "updated_at": "2026-09-10T10:00:00+08:00",
                    "identity": {
                        "display_name": "发哥",
                        "age_band": "40+",
                        "role": "公开创作身份",
                        "public_role_usage": "只作创作坐标",
                        "audience": "40+泛人群",
                        "fiction_status": "授权虚构人设",
                        "source_candidate_id": "internal-candidate",
                    },
                    "production_frame": {
                        "platform": "抖音自然流量",
                        "default_format": "默认 story",
                        "brand_exposure": "前期弱化",
                        "commerce_stage": "暂不写商品",
                    },
                    "authorized_fictional_behaviors": [
                        {
                            "id": "B02",
                            "behavior": "听到新信息后修正判断",
                            "visible_proof": "公开可见的改口",
                            "limit": "不代替当事人决定",
                            "reason": "internal reason",
                        }
                    ],
                    "stable_expression": [
                        {
                            "id": "E01",
                            "pattern": "先接住具体问题",
                            "avoid": "空泛总结",
                            "private_note": r"C:\private\note.txt",
                        }
                    ],
                    "viewpoint_principles": [
                        {
                            "id": "P01",
                            "status": "active",
                            "active_version": 1,
                            "versions": [
                                {
                                    "version": 1,
                                    "tension": "制度与人情",
                                    "default_choice": "先看清双方责任",
                                    "rejected_choice": "替人兜底",
                                    "exceptions": ["信息不全时先追问"],
                                    "cost": "当事人承担现实代价",
                                    "source_candidate_id": "internal-candidate",
                                    "reason": "internal reason",
                                }
                            ],
                        }
                    ],
                    "visible_weaknesses": [
                        {
                            "id": "W01",
                            "weakness": "容易先嘴硬",
                            "safe_payoff": "听到反驳后调整建议",
                        }
                    ],
                    "forbidden_biography_patterns": ["我女儿"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.feedback.write_text(
            json.dumps(
                {
                    "event_type": "candidate_evaluation",
                    "event_at": "2026-09-09T10:00:00+08:00",
                    "feedback_id": "feedback-1",
                    "batch_id": "batch-1",
                    "candidate_id": "candidate-1",
                    "revision_id": "r1",
                    "user_quote": "这是不应公开的完整用户原话",
                    "evaluation": "minor_revision",
                    "reason_codes": ["开头绕"],
                    "preserve": ["具体冲突"],
                    "avoid": ["空泛总结"],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        self.topics.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "event_type": "topic_status",
                            "event_at": "2026-09-09T09:00:00+08:00",
                            "topic_id": "topic-1",
                            "title": "员工家里急用钱，公司该帮到哪一步",
                            "category": "家庭责任",
                            "status": "selected",
                            "research_evidence": {"full": "private research body"},
                            "ledger": r"C:\business\选题台账.jsonl",
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "event_type": "script",
                            "event_at": "2026-09-09T09:01:00+08:00",
                            "topic_id": "topic-1",
                            "title": "员工家里急用钱，公司该帮到哪一步",
                            "category": "家庭责任",
                            "status": "produced",
                            "script": {"lines": [{"text": "完整未发布稿件"}]},
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self.shared.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "event_id": "event-1",
                    "event_type": "creative_preference",
                    "occurred_at": "2026-09-09T08:00:00+08:00",
                    "product_id": "shared",
                    "user_quote": "用户原话不能公开",
                    "payload": {
                        "source_skill": "boss-ip-video-script-writer",
                        "preference": "开头直接进入冲突",
                    },
                    "private_path": r"C:\business\secret.jsonl",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    def _inputs(self):
        return self.persona, self.feedback, self.topics, self.shared

    def test_build_public_snapshots_keeps_allowlisted_fields_only(self):
        snapshots = sync_public_context.build_public_snapshots(
            *self._inputs(), now="2026-09-10T12:00:00+08:00"
        )
        serialized = json.dumps(snapshots, ensure_ascii=False)

        self.assertEqual("current", snapshots["persona-current.json"]["snapshot_status"])
        self.assertEqual("发哥", snapshots["persona-current.json"]["persona"]["identity"]["display_name"])
        self.assertEqual("feedback-1", snapshots["recent-feedback.json"]["items"][0]["feedback_id"])
        self.assertEqual("topic-1", snapshots["recent-topics.json"]["items"][0]["topic_id"])
        self.assertEqual("开头直接进入冲突", snapshots["shared-preferences.json"]["items"][0]["preference"])
        for forbidden in (
            "user_quote",
            "source_candidate_id",
            "private_note",
            "private_path",
            "research_evidence",
            "完整未发布稿件",
            r"C:\business",
            "internal reason",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_sync_does_not_modify_sources_and_writes_four_current_snapshots(self):
        before = {path: path.read_bytes() for path in self._inputs()}
        written = sync_public_context.sync_public_context(*self._inputs(), self.output)

        self.assertEqual(
            {
                "persona-current.json",
                "recent-feedback.json",
                "recent-topics.json",
                "shared-preferences.json",
            },
            {path.name for path in written.values()},
        )
        self.assertEqual(before, {path: path.read_bytes() for path in self._inputs()})
        for path in written.values():
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("current", data["snapshot_status"])

    def test_unsafe_input_does_not_replace_existing_snapshots(self):
        self.output.mkdir()
        seeded = {}
        for name in (
            "persona-current.json",
            "recent-feedback.json",
            "recent-topics.json",
            "shared-preferences.json",
        ):
            path = self.output / name
            path.write_text("old-" + name, encoding="utf-8")
            seeded[path] = path.read_bytes()

        unsafe_topics = self.root / "unsafe-topics.jsonl"
        unsafe_topics.write_text(
            json.dumps(
                {
                    "event_type": "topic_status",
                    "topic_id": "topic-unsafe",
                    "title": r"C:\business\private title",
                    "category": "家庭责任",
                    "status": "selected",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(sync_public_context.PublicContextSafetyError):
            sync_public_context.sync_public_context(
                self.persona, self.feedback, unsafe_topics, self.shared, self.output
            )
        self.assertEqual(seeded, {path: path.read_bytes() for path in seeded})

    def test_sensitive_public_value_is_rejected_without_replacing_outputs(self):
        unsafe_topics = self.root / "sensitive-topics.jsonl"
        unsafe_topics.write_text(
            json.dumps(
                {
                    "event_type": "topic_status",
                    "topic_id": "topic-sensitive",
                    "title": "请联系 13800138000",
                    "category": "家庭责任",
                    "status": "selected",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(sync_public_context.PublicContextSafetyError):
            sync_public_context.build_public_snapshots(
                self.persona, self.feedback, unsafe_topics, self.shared
            )

    def test_cli_accepts_explicit_paths(self):
        code = sync_public_context.main(
            [
                "--persona",
                str(self.persona),
                "--feedback-ledger",
                str(self.feedback),
                "--topic-ledger",
                str(self.topics),
                "--shared-ledger",
                str(self.shared),
                "--output-dir",
                str(self.output),
            ]
        )
        self.assertEqual(0, code)
        self.assertTrue((self.output / "persona-current.json").is_file())


if __name__ == "__main__":
    unittest.main()
