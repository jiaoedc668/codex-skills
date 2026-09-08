#!/usr/bin/env python3
"""Derive human-only acceptance state from batch manifests and feedback."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from history_manager import read_feedback, validate_feedback_event


VALID_MODES = {"direct_dialogue_30", "light_story_60"}
PENDING_STATE = {
    "direct_dialogue_30": "direct_dialogue_30_pending",
    "light_story_60": "light_story_60_pending",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _manifest_sort_key(manifest: Mapping[str, Any]) -> datetime:
    raw = _clean(manifest.get("submitted_at"))
    try:
        submitted_at = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("manifest.submitted_at must be a valid ISO datetime") from exc
    if submitted_at.tzinfo is None or submitted_at.utcoffset() is None:
        raise ValueError("manifest.submitted_at must include a timezone offset")
    return submitted_at


def _validate_manifest(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        raise ValueError("manifest must be an object")
    if manifest.get("schema_version") != 1:
        raise ValueError("manifest.schema_version must be 1")

    batch_id = _clean(manifest.get("batch_id"))
    mode = _clean(manifest.get("duration_mode"))
    candidate_ids = manifest.get("candidate_ids")
    supersedes_batch_id = _clean(manifest.get("supersedes_batch_id"))
    root_cause = manifest.get("root_cause")

    if not batch_id:
        raise ValueError("manifest.batch_id is required")
    if mode not in VALID_MODES:
        raise ValueError(
            "manifest.duration_mode must be direct_dialogue_30 or light_story_60"
        )
    if not isinstance(candidate_ids, list):
        raise ValueError("manifest.candidate_ids must contain three unique candidates")
    cleaned_ids = [_clean(candidate_id) for candidate_id in candidate_ids]
    if (
        len(cleaned_ids) != 3
        or any(not candidate_id for candidate_id in cleaned_ids)
        or len(set(cleaned_ids)) != 3
    ):
        raise ValueError("manifest.candidate_ids must contain three unique candidates")
    if not supersedes_batch_id:
        raise ValueError("manifest.supersedes_batch_id is required; use 无 when absent")
    if not isinstance(root_cause, Mapping):
        raise ValueError("manifest.root_cause must be an object")
    for key in ("id", "hypothesis", "changed_layer"):
        if not _clean(root_cause.get(key)):
            raise ValueError(f"manifest.root_cause.{key} is required")
    if not isinstance(root_cause.get("root_level_change"), bool):
        raise ValueError("manifest.root_cause.root_level_change must be boolean")

    _manifest_sort_key(manifest)
    result = dict(manifest)
    result["batch_id"] = batch_id
    result["duration_mode"] = mode
    result["candidate_ids"] = cleaned_ids
    result["supersedes_batch_id"] = supersedes_batch_id
    result["root_cause"] = dict(root_cause)
    return result


def _validated_feedback_rows(
    feedback_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in feedback_rows:
        if not isinstance(row, dict):
            raise ValueError("feedback rows must be objects")
        try:
            rows.append(validate_feedback_event(row))
        except SystemExit as exc:
            raise ValueError(str(exc)) from exc
    return rows


def evaluate_batch(
    manifest: Mapping[str, Any], feedback_rows: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    """Count only the latest explicit quality evaluation for each candidate."""
    checked = _validate_manifest(manifest)
    candidate_ids = set(checked["candidate_ids"])
    latest_by_pair: dict[tuple[str, str], tuple[int, dict[str, Any]]] = {}

    for index, row in enumerate(_validated_feedback_rows(feedback_rows)):
        if row.get("event_type") != "candidate_evaluation":
            continue
        candidate_id = _clean(row.get("candidate_id"))
        revision_id = _clean(row.get("revision_id"))
        if candidate_id not in candidate_ids:
            continue
        row_batch_id = _clean(row.get("batch_id"))
        if row_batch_id and row_batch_id != checked["batch_id"]:
            continue
        latest_by_pair[(candidate_id, revision_id)] = (index, row)

    latest_by_candidate: dict[str, tuple[int, dict[str, Any]]] = {}
    for (candidate_id, _revision_id), indexed_row in latest_by_pair.items():
        previous = latest_by_candidate.get(candidate_id)
        if previous is None or indexed_row[0] > previous[0]:
            latest_by_candidate[candidate_id] = indexed_row

    latest_rows = [indexed_row[1] for indexed_row in latest_by_candidate.values()]
    direct_shoot_count = sum(
        row.get("evaluation") == "direct_shoot" for row in latest_rows
    )
    evaluated_candidate_count = len(latest_rows)
    resolved = evaluated_candidate_count == 3
    passed = resolved and direct_shoot_count >= 2
    return {
        "batch_id": checked["batch_id"],
        "duration_mode": checked["duration_mode"],
        "direct_shoot_count": direct_shoot_count,
        "evaluated_candidate_count": evaluated_candidate_count,
        "resolved": resolved,
        "passed": passed,
    }


def derive_acceptance_state(
    manifests: Iterable[Mapping[str, Any]],
    feedback_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Replay manifests chronologically and derive the current two-mode state."""
    checked_manifests = [_validate_manifest(manifest) for manifest in manifests]
    if len({manifest["batch_id"] for manifest in checked_manifests}) != len(
        checked_manifests
    ):
        raise ValueError("manifest batch_id values must be unique")
    checked_manifests.sort(key=_manifest_sort_key)
    checked_feedback = _validated_feedback_rows(feedback_rows)

    state = "direct_dialogue_30_pending"
    direct_is_current = False
    failed_root_id = ""
    failed_same_root_cause_count = 0
    requires_root_cause_change = False
    required_change_from_root_id = ""
    requires_rollback = False
    last_mode_count: dict[str, int] = {}
    latest_result = {
        "batch_id": "",
        "duration_mode": "direct_dialogue_30",
        "direct_shoot_count": 0,
        "evaluated_candidate_count": 0,
        "resolved": False,
        "passed": False,
    }

    for manifest in checked_manifests:
        mode = manifest["duration_mode"]
        root_cause = manifest["root_cause"]
        root_id = _clean(root_cause.get("id"))
        root_level_change = root_cause.get("root_level_change") is True

        if root_level_change:
            direct_is_current = False
            state = "direct_dialogue_30_pending"
            requires_root_cause_change = False
            required_change_from_root_id = ""
            requires_rollback = False
            last_mode_count.clear()
        elif requires_root_cause_change and root_id != required_change_from_root_id:
            requires_root_cause_change = False
            required_change_from_root_id = ""

        result = evaluate_batch(manifest, checked_feedback)
        latest_result = result
        if not result["resolved"]:
            if mode == "light_story_60" and direct_is_current and not root_level_change:
                state = "light_story_60_pending"
            else:
                state = "direct_dialogue_30_pending"
            continue

        previous_count = last_mode_count.get(mode)
        requires_rollback = (
            previous_count is not None
            and result["direct_shoot_count"] < previous_count
        )
        last_mode_count[mode] = result["direct_shoot_count"]

        if result["passed"]:
            failed_root_id = ""
            failed_same_root_cause_count = 0
            requires_root_cause_change = False
            required_change_from_root_id = ""
            if mode == "direct_dialogue_30":
                direct_is_current = True
                state = "light_story_60_pending"
            elif direct_is_current and not root_level_change:
                state = "complete"
            else:
                state = "direct_dialogue_30_pending"
        else:
            if root_id == failed_root_id:
                failed_same_root_cause_count += 1
            else:
                failed_root_id = root_id
                failed_same_root_cause_count = 1
            direct_is_current = False
            state = "direct_dialogue_30_pending"
            requires_root_cause_change = True
            required_change_from_root_id = root_id

        if failed_same_root_cause_count >= 3:
            state = "redesign_required"
        elif requires_rollback:
            state = "rollback_required"

    return {
        "state": state,
        "latest_batch_id": latest_result["batch_id"],
        "direct_shoot_count": latest_result["direct_shoot_count"],
        "evaluated_candidate_count": latest_result["evaluated_candidate_count"],
        "requires_root_cause_change": requires_root_cause_change,
        "requires_rollback": requires_rollback,
        "failed_same_root_cause_count": failed_same_root_cause_count,
    }


def _read_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"manifest {path} must contain one JSON object")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifests", type=Path, nargs="+", required=True)
    parser.add_argument("--feedback-ledger", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifests = [_read_manifest(path) for path in args.manifests]
        feedback_rows = read_feedback(args.feedback_ledger)
        if any(m.get("schema_version") == 2 for m in manifests):
            from format_acceptance import derive
            state = derive(manifests, feedback_rows)
        else:
            state = derive_acceptance_state(manifests, feedback_rows)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, SystemExit) as exc:
        print(f"FAIL: {exc}")
        print("INTEGRITY FAIL")
        return 2
    print(json.dumps(state, ensure_ascii=False, indent=2))
    print("INTEGRITY PASS")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
