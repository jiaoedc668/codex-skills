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
SUBPROCESS_ENCODING = locale.getpreferredencoding(False)
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

from v5_fixtures import (
    valid_direct_candidate,
    valid_persona,
    valid_principle_revision,
    valid_story_candidate,
)


class ContentContractV5Tests(unittest.TestCase):
    def test_missing_one_of_four_blueprint_items_fails(self) -> None:
        from content_contract import validate_candidate

        for key in (
            "immediate_wants",
            "strongest_counterargument",
            "fage_judgment",
            "turning_information",
        ):
            with self.subTest(key=key):
                data = valid_direct_candidate()
                data["conflict_blueprint"].pop(key)
                self.assertTrue(
                    any(
                        key in item
                        for item in validate_candidate(
                            data, valid_persona(), []
                        ).failures
                    )
                )

    def test_every_line_has_an_allowed_dialogue_act(self) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data["script"]["lines"][2]["dialogue_act"] = "explain_background"
        self.assertTrue(
            any(
                "dialogue_act" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

    def test_candidate_research_evidence_uses_validated_sources(self) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data["research_evidence"]["sources"][0]["url"] = "search result only"
        self.assertTrue(
            any(
                "research_evidence" in item and "HTTP(S) URL" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

    def test_immediate_wants_are_exactly_fage_and_one_counterparty(self) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data["conflict_blueprint"]["immediate_wants"] = [
            data["conflict_blueprint"]["immediate_wants"][0]
        ]
        self.assertTrue(
            any(
                "exactly two parties including 发哥" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

    def test_state_changes_cover_every_two_or_three_lines(self) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data["script"]["state_changes"][1]["after_line_id"] = "L6"
        self.assertTrue(
            any(
                "two or three lines" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

    def test_state_change_and_ending_kinds_are_closed_sets(self) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data["script"]["state_changes"][0]["kind"] = "mood"
        self.assertTrue(
            any(
                "state change kind" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

        data = valid_direct_candidate()
        data["script"]["ending"]["kind"] = "slogan"
        self.assertTrue(
            any(
                "ending kind" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

    def test_counterargument_must_survive_fage_judgment(self) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data["conflict_blueprint"]["strongest_counterargument"][
            "survives_after_judgment"
        ] = False
        self.assertTrue(
            any(
                "counterargument must survive" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

    def test_ending_requires_referenced_action_and_consequence(self) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data["script"]["ending"]["consequence"] = ""
        self.assertTrue(
            any(
                "ending consequence" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

    def test_direct_mode_has_one_dilemma_one_judgment_and_no_second_theme(
        self,
    ) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data["script"]["mode_contract"]["judgment_count"] = 2
        self.assertTrue(
            any(
                "one dilemma and one judgment" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

        data = valid_direct_candidate()
        data["script"]["secondary_theme"] = "顺便讨论代际沟通"
        self.assertTrue(
            any(
                "one dilemma and one judgment" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

    def test_story_turning_evidence_must_change_a_later_action(self) -> None:
        from content_contract import validate_candidate

        data = valid_story_candidate()
        data["script"]["mode_contract"]["turning_evidence_line_id"] = "L1"
        self.assertTrue(
            any(
                "middle turning evidence" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

    def test_persona_requires_versioned_principles_and_continuity(self) -> None:
        from content_contract import validate_persona_model

        persona = valid_persona()
        persona.pop("viewpoint_principles")
        persona.pop("fictional_continuity")
        failures = validate_persona_model(persona)
        self.assertTrue(any("viewpoint_principles" in item for item in failures))
        self.assertTrue(any("fictional_continuity" in item for item in failures))

    def test_principle_revision_appends_and_never_overwrites(self) -> None:
        from history_manager import apply_persona_evolution

        original = valid_persona()
        updated = apply_persona_evolution(original, valid_principle_revision())
        self.assertEqual(
            [1],
            [
                version["version"]
                for version in original["viewpoint_principles"][0]["versions"]
            ],
        )
        self.assertEqual(
            [1, 2],
            [
                version["version"]
                for version in updated["viewpoint_principles"][0]["versions"]
            ],
        )
        self.assertEqual(2, updated["viewpoint_principles"][0]["active_version"])

    def test_unknown_or_stale_persona_reference_fails_candidate(self) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data["persona_continuity"]["principle_version"] = 99
        self.assertTrue(
            any(
                "unknown principle version" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

        evolved = __import__("history_manager").apply_persona_evolution(
            valid_persona(), valid_principle_revision()
        )
        data["persona_continuity"]["principle_version"] = 1
        self.assertTrue(
            any(
                "stale principle version" in item
                for item in validate_candidate(data, evolved, []).failures
            )
        )

    def test_major_verifiable_biography_remains_forbidden(self) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data["script"]["lines"][0]["text"] = "我女儿当年也被骗了十万"
        self.assertTrue(
            any(
                "forbidden biography" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

    def test_continuity_add_creates_first_immutable_version(self) -> None:
        from history_manager import apply_persona_evolution

        original = valid_persona()
        event = {
            "schema_version": 1,
            "event_type": "fictional_continuity",
            "operation": "add",
            "record_id": "C01",
            "source_candidate_id": "batch-persona-test-c2",
            "reason": "保留可低风险复用的当场动作",
            "record": {
                "claim": "发哥遇到员工急事时会先看凭证再作决定",
                "scope": "reusable_low_risk",
                "allowed_reuse": "只复用核实动作，不复用具体金额或家庭关系",
                "forbidden_expansion": "不得扩写成真实公司制度或发哥个人履历",
            },
        }
        updated = apply_persona_evolution(original, event)
        self.assertEqual([], original["fictional_continuity"])
        self.assertEqual(1, updated["fictional_continuity"][0]["active_version"])
        self.assertEqual(
            [1],
            [
                version["version"]
                for version in updated["fictional_continuity"][0]["versions"]
            ],
        )

    def test_retire_preserves_versions_and_appends_history(self) -> None:
        from history_manager import apply_persona_evolution

        original = valid_persona()
        before_versions = copy.deepcopy(original["viewpoint_principles"][0]["versions"])
        event = {
            "schema_version": 1,
            "event_type": "viewpoint_principle",
            "operation": "retire",
            "record_id": "P01",
            "source_candidate_id": "batch-persona-test-c3",
            "reason": "后续明确反馈不再沿用该判断",
            "record": {},
        }
        updated = apply_persona_evolution(original, event)
        record = updated["viewpoint_principles"][0]
        self.assertEqual("active", original["viewpoint_principles"][0]["status"])
        self.assertEqual("retired", record["status"])
        self.assertEqual(before_versions, record["versions"])
        self.assertEqual(1, record["active_version"])
        self.assertEqual(
            "batch-persona-test-c3",
            record["retirement_history"][0]["source_candidate_id"],
        )

    def test_invalid_persona_evolution_never_mutates_input(self) -> None:
        from history_manager import apply_persona_evolution

        original = valid_persona()
        before = copy.deepcopy(original)
        event = valid_principle_revision()
        event["record"].pop("cost")
        with self.assertRaises(ValueError):
            apply_persona_evolution(original, event)
        self.assertEqual(before, original)

    def test_persona_evolution_cli_is_atomic_on_validation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona_path = root / "persona.json"
            event_path = root / "event.json"
            persona_path.write_text(
                json.dumps(valid_persona(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            before = persona_path.read_bytes()
            invalid_event = valid_principle_revision()
            invalid_event["record"].pop("cost")
            event_path.write_text(
                json.dumps(invalid_event, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            process = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "history_manager.py"),
                    "record-persona-evolution",
                    "--persona",
                    str(persona_path),
                    "--input",
                    str(event_path),
                ],
                capture_output=True,
                text=True,
                encoding=SUBPROCESS_ENCODING,
                errors="replace",
                check=False,
            )
            self.assertNotEqual(0, process.returncode)
            self.assertEqual(before, persona_path.read_bytes())

    def test_persona_evolution_cli_replaces_only_after_valid_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona_path = root / "persona.json"
            event_path = root / "event.json"
            persona_path.write_text(
                json.dumps(valid_persona(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            event_path.write_text(
                json.dumps(valid_principle_revision(), ensure_ascii=False, indent=2)
                + "\n",
                encoding="utf-8",
            )
            process = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "history_manager.py"),
                    "record-persona-evolution",
                    "--persona",
                    str(persona_path),
                    "--input",
                    str(event_path),
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
            updated = json.loads(persona_path.read_text(encoding="utf-8"))
            self.assertEqual(
                [1, 2],
                [
                    version["version"]
                    for version in updated["viewpoint_principles"][0]["versions"]
                ],
            )

    def test_v5_candidate_passes_objective_contract(self) -> None:
        from content_contract import validate_candidate

        self.assertTrue(validate_candidate(valid_direct_candidate(), valid_persona(), []).ok)

    def test_v4_cannot_pass_current_production_gate(self) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data["schema_version"] = 4
        self.assertIn(
            "schema_version must be 5",
            validate_candidate(data, valid_persona(), []).failures,
        )

    def test_author_cannot_write_human_quality_label(self) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data["candidate"]["evaluation"] = "direct_shoot"
        self.assertTrue(
            any(
                "human evaluation fields are forbidden" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

    def test_duration_modes_are_labels_without_timing_fields(self) -> None:
        from content_contract import duration_label, validate_candidate

        data = valid_direct_candidate()
        data["read_aloud_timing"] = {"median_seconds": 30}
        result = validate_candidate(data, valid_persona(), [])
        self.assertTrue(any("timing fields are forbidden" in item for item in result.failures))
        self.assertEqual("30 秒稿", duration_label("direct_dialogue_30"))

    def test_public_candidate_contains_only_review_content(self) -> None:
        from content_contract import build_public_candidate

        public = build_public_candidate(valid_direct_candidate())
        self.assertEqual(
            {"duration_label", "theme", "dialogue", "key_actions", "necessary_shots"},
            set(public),
        )
        self.assertNotIn("conflict_blueprint", json.dumps(public, ensure_ascii=False))
        self.assertEqual(
            {"speaker", "text"},
            set(public["dialogue"][0]),
        )

    def test_candidate_requires_exact_top_level_keys(self) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data.pop("research_evidence")
        data["integrity_checks"] = {"ok": True}
        failures = validate_candidate(data, valid_persona(), []).failures
        self.assertTrue(any("top-level keys" in item for item in failures))

    def test_evaluation_status_must_wait_for_user(self) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data["candidate"]["evaluation_status"] = "direct_shoot"
        self.assertIn(
            "candidate.evaluation_status must be awaiting_user_evaluation",
            validate_candidate(data, valid_persona(), []).failures,
        )

    def test_feedback_context_must_match_explicit_ledger_projection(self) -> None:
        from content_contract import validate_candidate

        rows = [
            {
                "event_type": "candidate_evaluation",
                "feedback_id": "feedback-1",
                "preserve": ["保留写借条的动作"],
                "avoid": ["不要让员工立刻感恩"],
            }
        ]
        data = valid_direct_candidate()
        data["feedback_context"] = {
            "latest_feedback_ids": ["feedback-1"],
            "keep": ["保留写借条的动作"],
            "avoid": ["不要让员工立刻感恩"],
            "length_feedback": [],
            "publication_data": "无用户提供的发布数据",
        }
        self.assertTrue(validate_candidate(data, valid_persona(), rows).ok)
        data["feedback_context"]["keep"] = ["模型自行猜的优点"]
        self.assertTrue(
            any(
                "feedback_context differs from current explicit ledger" in item
                for item in validate_candidate(data, valid_persona(), rows).failures
            )
        )

    def test_line_references_must_point_to_existing_dialogue(self) -> None:
        from content_contract import validate_candidate

        data = valid_direct_candidate()
        data["script"]["key_actions"][0]["after_line_id"] = "L99"
        self.assertTrue(
            any(
                "unknown line reference L99" in item
                for item in validate_candidate(data, valid_persona(), []).failures
            )
        )

    def test_candidate_cli_reports_integrity_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_path = root / "candidate.json"
            persona_path = root / "persona.json"
            ledger_path = root / "feedback.jsonl"
            candidate_path.write_text(
                json.dumps(valid_direct_candidate(), ensure_ascii=False), encoding="utf-8"
            )
            persona_path.write_text(
                json.dumps(valid_persona(), ensure_ascii=False), encoding="utf-8"
            )
            ledger_path.write_text("", encoding="utf-8")
            process = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "check_candidate_integrity.py"),
                    "--input",
                    str(candidate_path),
                    "--persona",
                    str(persona_path),
                    "--feedback-ledger",
                    str(ledger_path),
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


class ProtectedStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.allowed_run = (
            self.root / "老板IP内容库" / "草稿" / "2026-09-04-content-system-rebuild"
        )
        paths = {
            self.root / "老板IP内容库" / "选题台账.jsonl": "history\n",
            self.root / "老板IP内容库" / "草稿" / "older.md": "older\n",
            self.allowed_run / "new.json": "allowed\n",
            self.root / "boss-ip-video-script-writer" / "output" / "old.docx": "output\n",
            self.root / "已有成品" / "old.docx": "finished\n",
            self.root / "unrelated.txt": "outside protected scope\n",
        }
        for path, body in paths.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_protected_snapshot_excludes_only_current_run_directory(self) -> None:
        from audit_protected_state import snapshot_protected

        snapshot = snapshot_protected(self.root, self.allowed_run)
        self.assertIn("老板IP内容库/选题台账.jsonl", snapshot)
        self.assertIn("老板IP内容库/草稿/older.md", snapshot)
        self.assertIn("boss-ip-video-script-writer/output/old.docx", snapshot)
        self.assertIn("已有成品/old.docx", snapshot)
        self.assertNotIn(
            "老板IP内容库/草稿/2026-09-04-content-system-rebuild/new.json",
            snapshot,
        )
        self.assertNotIn("unrelated.txt", snapshot)

    def test_compare_snapshot_reports_changed_missing_and_added_paths(self) -> None:
        from audit_protected_state import compare_snapshot, snapshot_protected

        expected = snapshot_protected(self.root, self.allowed_run)
        (self.root / "老板IP内容库" / "草稿" / "older.md").write_text(
            "changed\n", encoding="utf-8"
        )
        (self.root / "已有成品" / "old.docx").unlink()
        added = self.root / "boss-ip-video-script-writer" / "output" / "added.docx"
        added.write_text("added\n", encoding="utf-8")
        actual = snapshot_protected(self.root, self.allowed_run)
        failures = compare_snapshot(expected, actual)
        self.assertIn("changed: 老板IP内容库/草稿/older.md", failures)
        self.assertIn("missing: 已有成品/old.docx", failures)
        self.assertIn("added: boss-ip-video-script-writer/output/added.docx", failures)

    def test_audit_cli_snapshot_then_detects_protected_change(self) -> None:
        snapshot_path = self.allowed_run / "baseline.json"
        snapshot = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "audit_protected_state.py"),
                "snapshot",
                "--root",
                str(self.root),
                "--allowed-run-dir",
                str(self.allowed_run),
                "--output",
                str(snapshot_path),
            ],
            capture_output=True,
            text=True,
            encoding=SUBPROCESS_ENCODING,
            errors="replace",
            check=False,
        )
        self.assertEqual(
            0,
            snapshot.returncode,
            (snapshot.stdout or "") + (snapshot.stderr or ""),
        )
        self.assertIn("INTEGRITY PASS: protected baseline written", snapshot.stdout)
        (self.root / "老板IP内容库" / "草稿" / "older.md").write_text(
            "tampered\n", encoding="utf-8"
        )
        verify = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "audit_protected_state.py"),
                "verify",
                "--root",
                str(self.root),
                "--allowed-run-dir",
                str(self.allowed_run),
                "--snapshot",
                str(snapshot_path),
            ],
            capture_output=True,
            text=True,
            encoding=SUBPROCESS_ENCODING,
            errors="replace",
            check=False,
        )
        self.assertEqual(2, verify.returncode)
        self.assertIn("changed: 老板IP内容库/草稿/older.md", verify.stdout)
        self.assertTrue(verify.stdout.rstrip().endswith("INTEGRITY FAIL"))


if __name__ == "__main__":
    unittest.main()
