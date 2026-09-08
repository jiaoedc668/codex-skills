from __future__ import annotations

import copy
import json
import locale
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "boss-ip-video-script-writer"
SCRIPTS = SKILL / "scripts"
TESTS = SKILL / "tests"
REFERENCES = SKILL / "references"
SUBPROCESS_ENCODING = locale.getpreferredencoding(False)
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

from select_topics import select_topics, validate_source
from v5_fixtures import (
    valid_direct_batch,
    valid_direct_candidate,
    valid_persona,
    valid_source,
    valid_topic_pool,
)


def run_similarity(candidate: dict, ledger: Path) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        candidate_path = Path(tmp) / "candidate.json"
        candidate_path.write_text(
            json.dumps(candidate, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "check_content_similarity.py"),
                "--input",
                str(candidate_path),
                "--ledger",
                str(ledger),
            ],
            capture_output=True,
            text=True,
            encoding=SUBPROCESS_ENCODING,
            errors="replace",
            check=False,
        )


def historical_row(candidate: dict, *, reuse_text: bool = True) -> dict:
    script = candidate["script"]
    return {
        "schema_version": 1,
        "event_type": "script",
        "status": "existing",
        "topic_id": "historical-test-1",
        "title": script["theme"] if reuse_text else "一条完全不同的旧标题",
        "body_text": (
            "".join(line["text"] for line in script["lines"])
            if reuse_text
            else "旧稿只讨论展厅灯光维修和门店闭店检查"
        ),
        "premise": (
            candidate["topic_decision"]["concrete_event"]
            if reuse_text
            else "展厅闭店后值班人员检查灯光"
        ),
        "viewpoint": (
            candidate["conflict_blueprint"]["fage_judgment"]["decision"]
            if reuse_text
            else "维修记录当天归档"
        ),
        "causal_skeleton": {
            "speaker_role_sequence": [
                "counterparty",
                "fage",
                "counterparty",
                "fage",
                "counterparty",
                "fage",
                "counterparty",
                "fage",
            ],
            "dialogue_act_sequence": [
                "request",
                "refuse",
                "push_back",
                "request",
                "conceal",
                "decide",
                "push_back",
                "decide",
            ],
            "state_change_kind_sequence": ["choice", "fact", "choice"],
            "ending_kind": "action",
        },
    }


class TopicCompetitionV5Tests(unittest.TestCase):
    def test_reference_contract_has_no_fixed_form_quota(self) -> None:
        text = (REFERENCES / "candidate-batch-schema.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("允许同母题或同拍法", text)
        self.assertNotIn("三种不同叙事", text)

    def test_current_issue_requires_recent_heat_signal(self) -> None:
        pool = valid_topic_pool()
        pool["prospects"][0]["research_evidence"]["heat_signals"] = []
        with self.assertRaisesRegex(ValueError, "recent heat signal"):
            select_topics(pool)

    def test_evergreen_requires_recurrence_and_high_interaction(self) -> None:
        pool = valid_topic_pool()
        topic = pool["prospects"][0]
        topic["topic_kind"] = "evergreen"
        topic["research_evidence"] = {
            "recurrence_sources": [valid_source("2026-01-01")],
            "high_interaction_sources": [],
        }
        with self.assertRaisesRegex(ValueError, "evergreen"):
            select_topics(pool)

    def test_author_scores_and_weights_are_rejected(self) -> None:
        pool = valid_topic_pool()
        pool["prospects"][0]["shootability_score"] = 100
        with self.assertRaisesRegex(ValueError, "score and rank fields are forbidden"):
            select_topics(pool)

    def test_same_theme_selected_topics_are_allowed(self) -> None:
        pool = valid_topic_pool()
        for item in pool["prospects"]:
            item["priority_category"] = "money_housing_pension_family"
        self.assertEqual(3, len(select_topics(pool)["selected"]))

    def test_selected_topics_must_win_recorded_comparisons(self) -> None:
        pool = valid_topic_pool(with_unselected=True)
        pool["pairwise_decisions"] = []
        with self.assertRaisesRegex(ValueError, "missing pairwise decision"):
            select_topics(pool)

    def test_current_issue_rejects_stale_heat_signal(self) -> None:
        pool = valid_topic_pool()
        signal = pool["prospects"][0]["research_evidence"]["heat_signals"][0]
        signal["source_date"] = "2026-08-01"
        with self.assertRaisesRegex(ValueError, "within seven days"):
            select_topics(pool)

    def test_evergreen_recurrence_must_span_ninety_days(self) -> None:
        pool = valid_topic_pool()
        topic = pool["prospects"][1]
        topic["research_evidence"]["recurrence_sources"][0]["source_date"] = "2026-06-15"
        with self.assertRaisesRegex(ValueError, "at least ninety days"):
            select_topics(pool)

    def test_high_interaction_source_requires_visible_interaction(self) -> None:
        pool = valid_topic_pool()
        source = pool["prospects"][1]["research_evidence"]["high_interaction_sources"][0]
        source.pop("visible_interaction")
        with self.assertRaisesRegex(ValueError, "visible_interaction"):
            select_topics(pool)

    def test_selected_topic_must_beat_unselected_eligible_topic(self) -> None:
        pool = valid_topic_pool(with_unselected=True)
        pool["pairwise_decisions"][3]["preferred_topic_id"] = "topic-4"
        with self.assertRaisesRegex(ValueError, "selected topic must be preferred"):
            select_topics(pool)

    def test_pairwise_comparison_cannot_be_duplicated_in_reverse_order(self) -> None:
        pool = valid_topic_pool()
        duplicate = dict(pool["pairwise_decisions"][0])
        duplicate["left_topic_id"], duplicate["right_topic_id"] = (
            duplicate["right_topic_id"],
            duplicate["left_topic_id"],
        )
        pool["pairwise_decisions"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "duplicate pairwise decision"):
            select_topics(pool)

    def test_source_requires_http_url_and_iso_dates(self) -> None:
        source = valid_source()
        source["url"] = "search result only"
        with self.assertRaisesRegex(ValueError, "HTTP\(S\) URL"):
            validate_source(source)
        source = valid_source()
        source["source_date"] = "September 3"
        with self.assertRaisesRegex(ValueError, "ISO date"):
            validate_source(source)

    def test_cli_outputs_selected_topics_without_scores_or_ranks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "pool.json"
            pool_path.write_text(
                json.dumps(valid_topic_pool(), ensure_ascii=False), encoding="utf-8"
            )
            process = subprocess.run(
                [sys.executable, str(SCRIPTS / "select_topics.py"), "--input", str(pool_path)],
                capture_output=True,
                text=True,
                encoding=SUBPROCESS_ENCODING,
                errors="replace",
                check=False,
            )
        self.assertEqual(
            0,
            process.returncode,
            (process.stdout or "") + (process.stderr or ""),
        )
        output = json.loads(process.stdout)
        self.assertEqual(["topic-1", "topic-2", "topic-3"], [x["topic_id"] for x in output["selected"]])
        encoded = json.dumps(output, ensure_ascii=False)
        for forbidden in ("score", "weights", "rank"):
            self.assertNotIn(forbidden, encoded)


class BatchIntegrityV5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ledger = self.root / "history.jsonl"
        self.ledger.write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_batch_requires_exactly_three_one_mode_candidates(self) -> None:
        from content_contract import validate_batch

        failures = validate_batch(
            valid_direct_batch()[:2], valid_persona(), [], valid_topic_pool()
        )
        self.assertIn(
            "candidate batch must contain exactly 3 complete scripts", failures
        )

    def test_same_theme_and_same_mode_do_not_form_a_quota_failure(self) -> None:
        from content_contract import validate_batch

        batch = valid_direct_batch()
        for item in batch:
            item["topic_decision"][
                "priority_category"
            ] = "money_housing_pension_family"
        pool = valid_topic_pool()
        for item in pool["prospects"]:
            item["priority_category"] = "money_housing_pension_family"
        self.assertEqual(
            [], validate_batch(batch, valid_persona(), [], pool)
        )

    def test_all_three_identical_causal_skeletons_fail(self) -> None:
        from content_contract import validate_batch

        batch = valid_direct_batch()
        skeleton = batch[0]["script"]["lines"]
        for item in batch[1:]:
            item["script"]["lines"] = copy.deepcopy(skeleton)
        self.assertTrue(
            any(
                "same causal skeleton" in item
                for item in validate_batch(
                    batch, valid_persona(), [], valid_topic_pool()
                )
            )
        )

    def test_batch_rejects_duplicate_ids_positions_modes_and_topics(self) -> None:
        from content_contract import validate_batch

        mutations = {
            "unique candidate IDs": lambda batch: batch[1]["candidate"].update(
                {"candidate_id": batch[0]["candidate"]["candidate_id"]}
            ),
            "positions 1, 2, and 3": lambda batch: batch[1]["candidate"].update(
                {"position": 1}
            ),
            "one duration_mode": lambda batch: batch[1].update(
                {"duration_mode": "light_story_60"}
            ),
            "one batch ID": lambda batch: batch[1]["candidate"].update(
                {"batch_id": "batch-other"}
            ),
            "identical feedback context": lambda batch: batch[1][
                "feedback_context"
            ].update({"keep": ["被篡改的快照"]}),
            "selected topic set": lambda batch: batch[1]["topic_decision"].update(
                {"topic_id": "topic-not-selected"}
            ),
        }
        for expected, mutate in mutations.items():
            with self.subTest(expected=expected):
                batch = valid_direct_batch()
                mutate(batch)
                self.assertTrue(
                    any(
                        expected in item
                        for item in validate_batch(
                            batch, valid_persona(), [], valid_topic_pool()
                        )
                    )
                )

    def test_malformed_duration_mode_returns_failure_instead_of_crashing(self) -> None:
        from content_contract import validate_batch

        batch = valid_direct_batch()
        batch[0]["duration_mode"] = []
        failures = validate_batch(
            batch, valid_persona(), [], valid_topic_pool()
        )
        self.assertTrue(any("duration_mode" in item for item in failures))

    def test_candidate_topic_decision_must_match_selected_pool_record(self) -> None:
        from content_contract import validate_batch

        batch = valid_direct_batch()
        batch[0]["topic_decision"]["fage_choice"] = "选中后偷偷换掉判断"
        failures = validate_batch(
            batch, valid_persona(), [], valid_topic_pool()
        )
        self.assertTrue(
            any("topic decision must match selected topic" in item for item in failures)
        )

    def test_batch_cli_accepts_valid_batch_and_prints_only_status(self) -> None:
        batch = valid_direct_batch()
        paths: list[Path] = []
        for index, candidate in enumerate(batch, 1):
            path = self.root / f"candidate-{index}.json"
            path.write_text(
                json.dumps(candidate, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            paths.append(path)
        persona_path = self.root / "persona.json"
        pool_path = self.root / "pool.json"
        feedback_path = self.root / "feedback.jsonl"
        persona_path.write_text(
            json.dumps(valid_persona(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        pool_path.write_text(
            json.dumps(valid_topic_pool(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        feedback_path.write_text("", encoding="utf-8")
        process = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "check_batch_integrity.py"),
                "--inputs",
                *(str(path) for path in paths),
                "--topic-pool",
                str(pool_path),
                "--persona",
                str(persona_path),
                "--feedback-ledger",
                str(feedback_path),
            ],
            capture_output=True,
            text=True,
            encoding=SUBPROCESS_ENCODING,
            errors="replace",
            check=False,
        )
        self.assertEqual(
            0,
            process.returncode,
            (process.stdout or "") + (process.stderr or ""),
        )
        self.assertEqual("INTEGRITY PASS", process.stdout.strip())

    def test_v5_similarity_reads_history_without_writing(self) -> None:
        candidate = valid_direct_candidate()
        self.ledger.write_text(
            json.dumps(historical_row(candidate), ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        before = self.ledger.read_bytes()
        run = run_similarity(candidate, self.ledger)
        self.assertEqual(2, run.returncode)
        self.assertIn("INTEGRITY FAIL", run.stdout)
        self.assertEqual(before, self.ledger.read_bytes())

    def test_exact_skeleton_alone_does_not_create_similarity_failure(self) -> None:
        candidate = valid_direct_candidate()
        self.ledger.write_text(
            json.dumps(
                historical_row(candidate, reuse_text=False), ensure_ascii=False
            )
            + "\n",
            encoding="utf-8",
        )
        run = run_similarity(candidate, self.ledger)
        self.assertEqual(
            0,
            run.returncode,
            (run.stdout or "") + (run.stderr or ""),
        )
        self.assertEqual("INTEGRITY PASS", run.stdout.strip())

    def test_exact_skeleton_plus_similar_premise_is_reported(self) -> None:
        candidate = valid_direct_candidate()
        row = historical_row(candidate, reuse_text=False)
        row["premise"] = candidate["topic_decision"]["concrete_event"]
        self.ledger.write_text(
            json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        run = run_similarity(candidate, self.ledger)
        self.assertEqual(2, run.returncode)
        self.assertIn("exact causal skeleton", run.stdout)
        self.assertTrue(run.stdout.rstrip().endswith("INTEGRITY FAIL"))


if __name__ == "__main__":
    unittest.main()
