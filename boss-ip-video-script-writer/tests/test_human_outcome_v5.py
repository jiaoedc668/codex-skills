from __future__ import annotations

import copy
import json
import locale
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "boss-ip-video-script-writer"
SCRIPTS = SKILL / "scripts"
TESTS = SKILL / "tests"
SKILL_PATH = SKILL / "SKILL.md"
OPENAI_METADATA = SKILL / "agents" / "openai.yaml"
SUBPROCESS_ENCODING = locale.getpreferredencoding(False)
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

from content_contract import validate_candidate
import generate_script_docx as docx_generator
from history_manager import feedback_context, validate_feedback_event
from v5_fixtures import (
    valid_direct_candidate,
    valid_direct_manifest,
    valid_persona,
    valid_story_manifest,
)


def valid_length_feedback(judgment: str = "too_long") -> dict:
    return {
        "event_type": "candidate_length_evaluation",
        "feedback_id": "length-direct-01-c1-r1",
        "batch_id": "batch-20260904-direct-01",
        "candidate_id": "batch-20260904-direct-01-c1",
        "revision_id": "r1",
        "length_judgment": judgment,
        "user_quote": "这条偏长，收一点",
    }


def valid_selection_event() -> dict:
    return {
        "event_type": "candidate_selection",
        "event_at": "2026-09-05T12:00:00+08:00",
        "feedback_id": "selection-direct-01-c1",
        "batch_id": "batch-20260904-direct-01",
        "candidate_id": "batch-20260904-direct-01-c1",
        "revision_id": "r1",
        "user_quote": "选第一条继续改",
    }


def valid_confirmation_event(content_sha256: str | None = None) -> dict:
    return {
        "event_type": "copy_confirmation",
        "event_at": "2026-09-05T12:01:00+08:00",
        "feedback_id": "confirmation-direct-01-c1-r1",
        "batch_id": "batch-20260904-direct-01",
        "candidate_id": "batch-20260904-direct-01-c1",
        "revision_id": "r1",
        "content_sha256": content_sha256 or "a" * 64,
        "user_quote": "这版文案确认",
    }


def valid_direct_shoot_event() -> dict:
    return evaluation_event(valid_direct_manifest(), 1, "direct_shoot")


def valid_confirmed_source() -> dict:
    data = valid_direct_candidate()
    data["output_version"] = "auto"
    data["production_package"] = {
        "estimated_duration_label": "30 秒稿",
        "scene": "公司会客区",
        "cast": [
            {"role": "发哥", "visibility": "露脸", "purpose": "核对账目并作决定"},
            {"role": "员工", "visibility": "画外音", "purpose": "提出不能拖延的现实反方"},
        ],
        "props": [
            {"item": "医院缴费单", "purpose": "展示两万元押金缺口"},
            {"item": "工资预支单和借条", "purpose": "让两种责任分别落纸"},
        ],
        "storyboard": [
            {
                "beat": "开场请求",
                "line_ids": ["L1", "L2", "L3"],
                "action": "员工把缴费单推到桌上",
                "shot": "发哥中景转缴费单特写",
            },
            {
                "beat": "核实新信息",
                "line_ids": ["L4", "L5"],
                "action": "发哥查看缴费单，员工说出已挪用房贷钱",
                "shot": "双人侧面与单据近景",
            },
            {
                "beat": "决定落地",
                "line_ids": ["L6", "L7", "L8"],
                "action": "发哥把预支单和借条分开放好",
                "shot": "俯拍两张单据后回到发哥",
            },
        ],
        "actions": ["员工递出缴费单", "发哥分开放置工资预支单和借条"],
        "subtitles": [
            {"line_id": "L1", "text": "住院押金还差两万元"},
            {"line_id": "L8", "text": "救急也要把责任写清楚"},
        ],
    }
    return data


def valid_word_events(data: dict) -> list[dict]:
    candidate = data["candidate"]
    selection = valid_selection_event()
    selection.update(
        {
            "batch_id": candidate["batch_id"],
            "candidate_id": candidate["candidate_id"],
        }
    )
    confirmation = valid_confirmation_event(
        docx_generator.confirmation_content_sha256(data)
    )
    confirmation.update(
        {
            "batch_id": candidate["batch_id"],
            "candidate_id": candidate["candidate_id"],
            "revision_id": candidate["revision_id"],
        }
    )
    return [selection, confirmation]


def docx_xml_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read("word/document.xml").decode("utf-8")


def evaluation_event(
    manifest: dict,
    index: int,
    evaluation: str,
    *,
    feedback_suffix: str = "1",
    event_minute: int | None = None,
) -> dict:
    event = {
        "event_type": "candidate_evaluation",
        "event_at": (
            f"2026-09-04T23:{event_minute:02d}:00+08:00"
            if event_minute is not None
            else "2026-09-04T23:00:00+08:00"
        ),
        "feedback_id": f"evaluation-{manifest['batch_id']}-c{index}-{feedback_suffix}",
        "batch_id": manifest["batch_id"],
        "candidate_id": manifest["candidate_ids"][index - 1],
        "revision_id": "r1",
        "evaluation": evaluation,
        "reason_codes": ["OTHER"],
        "preserve": ["保留这个具体选择"] if evaluation == "direct_shoot" else [],
        "avoid": ["避免当前结构"] if evaluation in {"major_revision", "rejected"} else [],
        "user_quote": "这条可以直接拍" if evaluation == "direct_shoot" else "这条不能直接拍",
    }
    return event


def batch_feedback(
    manifest: dict,
    direct_shoot_count: int,
    *,
    evaluated: int = 3,
) -> list[dict]:
    return [
        evaluation_event(
            manifest,
            index,
            "direct_shoot" if index <= direct_shoot_count else "rejected",
        )
        for index in range(1, evaluated + 1)
    ]


class HumanOutcomeV5Tests(unittest.TestCase):
    def test_skill_uses_only_v5_production_commands(self) -> None:
        text = SKILL_PATH.read_text(encoding="utf-8")
        for required in (
            "select_topics.py",
            "check_candidate_integrity.py",
            "check_batch_integrity.py",
            "check_content_similarity.py",
            "acceptance_state.py",
        ):
            self.assertIn(required, text)
        for retired in (
            "semantic_review.py",
            "check_script_quality.py",
            "rank_topics.py",
            "--require-schema-version 4",
        ):
            self.assertNotIn(retired, text)

    def test_skill_says_duration_is_user_calibrated_not_timed(self) -> None:
        text = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("30 秒稿", text)
        self.assertIn("60 秒稿", text)
        self.assertIn("长短由谢总看稿后的明确反馈校准", text)
        for forbidden in ("朗读计时", "TTS", "硬秒数", "字符数估时"):
            self.assertNotIn(forbidden, text)

    def test_skill_exposes_no_machine_quality_certificate(self) -> None:
        text = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("INTEGRITY PASS", text)
        self.assertNotIn("target_match", text)
        self.assertNotIn("三路盲审", text)

    def test_openai_metadata_names_current_v5_workflow(self) -> None:
        text = OPENAI_METADATA.read_text(encoding="utf-8")
        for required in ("证据竞争", "schema v5", "显式用户结果", "30/60"):
            self.assertIn(required, text)

    def test_length_feedback_does_not_create_quality_evaluation(self) -> None:
        row = validate_feedback_event(valid_length_feedback("too_long"))
        self.assertEqual("candidate_length_evaluation", row["event_type"])
        self.assertNotIn("evaluation", row)

    def test_selection_and_confirmation_do_not_mean_direct_shoot(self) -> None:
        from acceptance_state import evaluate_batch

        rows = [
            validate_feedback_event(valid_selection_event()),
            validate_feedback_event(valid_confirmation_event()),
        ]
        result = evaluate_batch(valid_direct_manifest(), rows)
        self.assertEqual(0, result["direct_shoot_count"])

    def test_feedback_without_user_quote_is_rejected(self) -> None:
        event = evaluation_event(valid_direct_manifest(), 1, "direct_shoot")
        event["user_quote"] = ""
        with self.assertRaisesRegex(SystemExit, "user_quote"):
            validate_feedback_event(event)

    def test_candidate_file_cannot_supply_an_evaluation(self) -> None:
        data = valid_direct_candidate()
        data["candidate"]["evaluation"] = "direct_shoot"
        self.assertFalse(validate_candidate(data, valid_persona(), []).ok)

    def test_invalid_length_judgment_is_rejected(self) -> None:
        with self.assertRaisesRegex(SystemExit, "length_judgment"):
            validate_feedback_event(valid_length_feedback("about_right"))

    def test_confirmation_requires_lowercase_sha256(self) -> None:
        event = valid_confirmation_event()
        event["content_sha256"] = "A" * 64
        with self.assertRaisesRegex(SystemExit, "content_sha256"):
            validate_feedback_event(event)

    def test_feedback_context_keeps_length_feedback_separate(self) -> None:
        length_row = validate_feedback_event(valid_length_feedback())
        context = feedback_context([length_row])
        self.assertEqual(["length-direct-01-c1-r1"], context["latest_feedback_ids"])
        self.assertEqual(["无"], context["keep"])
        self.assertEqual(["无"], context["avoid"])
        self.assertEqual("too_long", context["length_feedback"][0]["length_judgment"])

    def test_two_direct_shoot_results_advance_to_story(self) -> None:
        from acceptance_state import derive_acceptance_state

        manifest = valid_direct_manifest()
        state = derive_acceptance_state([manifest], batch_feedback(manifest, 2))
        self.assertEqual("light_story_60_pending", state["state"])

    def test_partial_feedback_keeps_batch_pending(self) -> None:
        from acceptance_state import derive_acceptance_state

        manifest = valid_direct_manifest()
        state = derive_acceptance_state(
            [manifest], batch_feedback(manifest, 2, evaluated=2)
        )
        self.assertEqual("direct_dialogue_30_pending", state["state"])
        self.assertEqual(2, state["evaluated_candidate_count"])

    def test_passed_story_completes_consecutive_validation(self) -> None:
        from acceptance_state import derive_acceptance_state

        direct = valid_direct_manifest()
        story = valid_story_manifest()
        state = derive_acceptance_state(
            [story, direct], batch_feedback(direct, 2) + batch_feedback(story, 2)
        )
        self.assertEqual("complete", state["state"])

    def test_story_failure_resets_to_new_direct_batch(self) -> None:
        from acceptance_state import derive_acceptance_state

        direct = valid_direct_manifest()
        story = valid_story_manifest()
        state = derive_acceptance_state(
            [direct, story], batch_feedback(direct, 2) + batch_feedback(story, 1)
        )
        self.assertEqual("direct_dialogue_30_pending", state["state"])
        self.assertTrue(state["requires_root_cause_change"])

    def test_root_level_change_invalidates_both_old_mode_passes(self) -> None:
        from acceptance_state import derive_acceptance_state

        direct = valid_direct_manifest()
        story = valid_story_manifest()
        story["root_cause"]["root_level_change"] = True
        state = derive_acceptance_state(
            [direct, story], batch_feedback(direct, 2) + batch_feedback(story, 2)
        )
        self.assertEqual("direct_dialogue_30_pending", state["state"])

    def test_same_root_cause_three_failures_require_redesign(self) -> None:
        from acceptance_state import derive_acceptance_state

        manifests = [
            valid_direct_manifest(index, root_cause_id="RC01")
            for index in (1, 2, 3)
        ]
        rows = [row for manifest in manifests for row in batch_feedback(manifest, 1)]
        state = derive_acceptance_state(manifests, rows)
        self.assertEqual("redesign_required", state["state"])
        self.assertEqual(3, state["failed_same_root_cause_count"])

    def test_worse_same_mode_result_requires_rollback(self) -> None:
        from acceptance_state import derive_acceptance_state

        manifests = [valid_direct_manifest(1), valid_direct_manifest(2)]
        rows = batch_feedback(manifests[0], 2) + batch_feedback(manifests[1], 1)
        state = derive_acceptance_state(manifests, rows)
        self.assertEqual("rollback_required", state["state"])
        self.assertTrue(state["requires_rollback"])

    def test_latest_evaluation_for_same_candidate_revision_wins(self) -> None:
        from acceptance_state import evaluate_batch

        manifest = valid_direct_manifest()
        rows = batch_feedback(manifest, 2)
        rows.append(
            evaluation_event(
                manifest,
                1,
                "rejected",
                feedback_suffix="2",
                event_minute=5,
            )
        )
        result = evaluate_batch(manifest, rows)
        self.assertEqual(1, result["direct_shoot_count"])
        self.assertEqual(3, result["evaluated_candidate_count"])

    def test_manifest_requires_three_unique_candidates(self) -> None:
        from acceptance_state import evaluate_batch

        manifest = valid_direct_manifest()
        manifest["candidate_ids"][2] = manifest["candidate_ids"][1]
        with self.assertRaisesRegex(ValueError, "three unique"):
            evaluate_batch(manifest, [])

    def test_cli_prints_state_then_integrity_pass(self) -> None:
        direct = valid_direct_manifest()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifest_path = tmp_path / "manifest.json"
            ledger_path = tmp_path / "feedback.jsonl"
            manifest_path.write_text(
                json.dumps(direct, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            ledger_path.write_text(
                "".join(
                    json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                    for row in batch_feedback(direct, 2)
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "acceptance_state.py"),
                    "--manifests",
                    str(manifest_path),
                    "--feedback-ledger",
                    str(ledger_path),
                ],
                capture_output=True,
                text=True,
                encoding=SUBPROCESS_ENCODING,
                errors="replace",
                check=False,
            )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn('"state": "light_story_60_pending"', completed.stdout)
        self.assertTrue(completed.stdout.rstrip().endswith("INTEGRITY PASS"))

    def test_v5_word_blocked_without_selection_event(self) -> None:
        data = valid_confirmed_source()
        confirmation = valid_confirmation_event(
            docx_generator.confirmation_content_sha256(data)
        )
        with self.assertRaisesRegex(SystemExit, "selected"):
            docx_generator.validate_v5_word_gate(data, [confirmation])

    def test_v5_word_blocked_without_matching_confirmation_hash(self) -> None:
        data = valid_confirmed_source()
        rows = [valid_selection_event(), valid_confirmation_event("0" * 64)]
        with self.assertRaisesRegex(SystemExit, "content changed"):
            docx_generator.validate_v5_word_gate(data, rows)

    def test_direct_shoot_alone_does_not_unlock_word(self) -> None:
        with self.assertRaisesRegex(SystemExit, "selected"):
            docx_generator.validate_v5_word_gate(
                valid_confirmed_source(), [valid_direct_shoot_event()]
            )

    def test_v5_word_requires_confirmation_only_production_fields(self) -> None:
        data = valid_confirmed_source()
        data["production_package"].pop("storyboard")
        with self.assertRaisesRegex(SystemExit, "production_package.storyboard"):
            docx_generator.validate_v5_word_gate(data, valid_word_events(data))

    def test_output_version_does_not_change_v5_confirmation_hash(self) -> None:
        data = valid_confirmed_source()
        first = docx_generator.confirmation_content_sha256(data)
        data["output_version"] = "V7"
        self.assertEqual(first, docx_generator.confirmation_content_sha256(data))

    def test_production_package_does_not_change_confirmation_hash(self) -> None:
        data = valid_confirmed_source()
        first = docx_generator.confirmation_content_sha256(data)
        data["production_package"]["scene"] = "家中餐桌"
        self.assertEqual(first, docx_generator.confirmation_content_sha256(data))

    def test_confirmation_must_follow_selection_in_ledger_order(self) -> None:
        data = valid_confirmed_source()
        selection, confirmation = valid_word_events(data)
        with self.assertRaisesRegex(SystemExit, "confirmation"):
            docx_generator.validate_v5_word_gate(data, [confirmation, selection])

    def test_confirmation_must_match_current_revision(self) -> None:
        data = valid_confirmed_source()
        selection, confirmation = valid_word_events(data)
        confirmation["revision_id"] = "r0"
        with self.assertRaisesRegex(SystemExit, "current revision"):
            docx_generator.validate_v5_word_gate(data, [selection, confirmation])

    def test_v5_cli_requires_feedback_ledger(self) -> None:
        data = valid_confirmed_source()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = root / "confirmed.json"
            source_path.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "generate_script_docx.py"),
                    "--input",
                    str(source_path),
                    "--output-root",
                    str(root / "output"),
                ],
                capture_output=True,
                text=True,
                encoding=SUBPROCESS_ENCODING,
                errors="replace",
                check=False,
            )
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("feedback-ledger", completed.stdout + completed.stderr)

    def test_v5_cli_writes_only_temporary_versioned_outputs_with_all_fields(self) -> None:
        data = valid_confirmed_source()
        rows = valid_word_events(data)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = root / "confirmed.json"
            ledger_path = root / "feedback.jsonl"
            output_root = root / "output"
            source_path.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
            ledger_path.write_text(
                "".join(
                    json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                    for row in rows
                ),
                encoding="utf-8",
            )
            commands = [
                sys.executable,
                str(SCRIPTS / "generate_script_docx.py"),
                "--input",
                str(source_path),
                "--feedback-ledger",
                str(ledger_path),
                "--output-root",
                str(output_root),
            ]
            first = subprocess.run(
                commands,
                capture_output=True,
                text=True,
                encoding=SUBPROCESS_ENCODING,
                errors="replace",
                check=False,
            )
            second = subprocess.run(
                commands,
                capture_output=True,
                text=True,
                encoding=SUBPROCESS_ENCODING,
                errors="replace",
                check=False,
            )
            docx_paths = sorted(output_root.rglob("*.docx"))
            json_paths = sorted(output_root.rglob("*-源数据.json"))
            xml_text = docx_xml_text(docx_paths[0]) if docx_paths else ""
            saved_sources = [
                json.loads(path.read_text(encoding="utf-8")) for path in json_paths
            ]

        self.assertEqual(0, first.returncode, first.stdout + first.stderr)
        self.assertEqual(0, second.returncode, second.stdout + second.stderr)
        self.assertEqual(2, len(docx_paths))
        self.assertEqual(2, len(json_paths))
        for expected in (
            "30 秒稿",
            "公司会客区",
            "员工",
            "医院缴费单",
            "员工把缴费单推到桌上",
            "住院押金还差两万元",
        ):
            self.assertIn(expected, xml_text)
        self.assertEqual([5, 5], [source["schema_version"] for source in saved_sources])
        self.assertEqual(["V1", "V2"], [source["output_version"] for source in saved_sources])

    def test_standard_library_fallback_keeps_v5_production_fields(self) -> None:
        data = valid_confirmed_source()
        render_data = docx_generator.prepare_v5_render_data(data)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "fallback.docx"
            docx_generator.StandardLibraryDocument(render_data).save(output)
            xml_text = docx_xml_text(output)
        for expected in (
            "30 秒稿",
            "公司会客区",
            "医院缴费单",
            "员工把缴费单推到桌上",
            "住院押金还差两万元",
        ):
            self.assertIn(expected, xml_text)


if __name__ == "__main__":
    unittest.main()
