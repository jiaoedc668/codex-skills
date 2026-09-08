from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from content_contract import derive_causal_skeleton


def _clean(value: Any) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _normalize(value: Any) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", _clean(value)).lower()


def _ratio(left: Any, right: Any) -> float:
    first = _normalize(left)
    second = _normalize(right)
    if not first or not second:
        return 0.0
    return SequenceMatcher(None, first, second, autojunk=False).ratio()


def _longest_shared(left: Any, right: Any) -> str:
    first = _normalize(left)
    second = _normalize(right)
    if not first or not second:
        return ""
    block = max(
        SequenceMatcher(None, first, second, autojunk=False).get_matching_blocks(),
        key=lambda item: item.size,
    )
    return first[block.a : block.a + block.size]


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _read_ledger(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, 1):
            if not raw_line.strip():
                continue
            row = json.loads(raw_line)
            if not isinstance(row, dict):
                raise ValueError(f"ledger line {line_number} must be an object")
            rows.append(row)
    return rows


def _candidate_fields(candidate: Any) -> dict[str, Any]:
    if not isinstance(candidate, Mapping):
        raise ValueError("candidate must be an object")
    script = candidate.get("script")
    topic = candidate.get("topic_decision")
    blueprint = candidate.get("creative_blueprint") if candidate.get("schema_version") == 6 else candidate.get("conflict_blueprint")
    if not isinstance(script, Mapping):
        raise ValueError("candidate.script must be an object")
    if not isinstance(topic, Mapping):
        raise ValueError("candidate.topic_decision must be an object")
    if not isinstance(blueprint, Mapping):
        raise ValueError("candidate.conflict_blueprint must be an object")
    judgment = {"decision": blueprint.get("judgment")} if candidate.get("schema_version") == 6 else blueprint.get("fage_judgment")
    if not isinstance(judgment, Mapping):
        raise ValueError("candidate.conflict_blueprint.fage_judgment must be an object")
    lines = script.get("lines")
    if not isinstance(lines, list):
        raise ValueError("candidate.script.lines must be an array")
    body = "".join(
        _clean(line.get("text")) for line in lines if isinstance(line, Mapping)
    )
    return {
        "title": _clean(script.get("theme")),
        "body": body,
        "premise": _clean(topic.get("concrete_event")),
        "viewpoint": _clean(judgment.get("decision")),
        "skeleton": derive_causal_skeleton(candidate),
    }


def _stored_skeleton(row: Mapping[str, Any]) -> tuple[Any, ...] | None:
    value = row.get("causal_skeleton")
    if isinstance(value, Mapping):
        keys = (
            "speaker_role_sequence",
            "dialogue_act_sequence",
            "state_change_kind_sequence",
        )
        if all(isinstance(value.get(key), list) for key in keys):
            return (
                tuple(value["speaker_role_sequence"]),
                tuple(value["dialogue_act_sequence"]),
                tuple(value["state_change_kind_sequence"]),
                _clean(value.get("ending_kind")),
            )
    if isinstance(row.get("script"), Mapping):
        return derive_causal_skeleton(row)
    return None


def find_similarity_failures(
    candidate: Any,
    ledger_rows: list[dict[str, Any]],
    *,
    title_threshold: float = 0.76,
    body_threshold: float = 0.70,
    idea_threshold: float = 0.80,
    phrase_threshold: int = 22,
) -> list[str]:
    current = _candidate_fields(candidate)
    failures: list[str] = []
    for row in ledger_rows:
        if row.get("event_type") != "script" or row.get("status") not in {
            "existing",
            "produced",
        }:
            continue
        old_title = _clean(row.get("title"))
        title_ratio = _ratio(current["title"], old_title)
        body_ratio = _ratio(current["body"], row.get("body_text"))
        premise_ratio = _ratio(current["premise"], row.get("premise"))
        viewpoint_ratio = _ratio(current["viewpoint"], row.get("viewpoint"))
        shared = _longest_shared(current["body"], row.get("body_text"))
        if title_ratio >= title_threshold:
            failures.append(f"title similarity {title_ratio:.2f} with {old_title}")
        if body_ratio >= body_threshold:
            failures.append(f"body similarity {body_ratio:.2f} with {old_title}")
        if premise_ratio >= idea_threshold:
            failures.append(f"premise similarity {premise_ratio:.2f} with {old_title}")
        if viewpoint_ratio >= idea_threshold:
            failures.append(
                f"viewpoint similarity {viewpoint_ratio:.2f} with {old_title}"
            )
        if len(shared) >= phrase_threshold:
            failures.append(
                f"shared phrase has {len(shared)} characters with {old_title}: {shared}"
            )
        old_skeleton = _stored_skeleton(row)
        if (
            old_skeleton is not None
            and old_skeleton == current["skeleton"]
            and (premise_ratio >= idea_threshold or body_ratio >= body_threshold)
        ):
            failures.append(f"exact causal skeleton repeats {old_title}")

    latest_topics: dict[str, dict[str, Any]] = {}
    for row in ledger_rows:
        topic_id = _clean(row.get("topic_id"))
        if row.get("event_type") == "topic_status" and topic_id:
            latest_topics[topic_id] = row
    for row in latest_topics.values():
        if row.get("status") not in {"proposed", "rejected", "selected"}:
            continue
        similarity = max(
            _ratio(current["title"], row.get("title")),
            _ratio(current["premise"], row.get("premise")),
            _ratio(current["viewpoint"], row.get("viewpoint")),
        )
        if similarity >= idea_threshold:
            failures.append(
                f"candidate repeats a {row.get('status')} topic "
                f"({similarity:.2f}): {_clean(row.get('title'))}"
            )
    return failures


def revision_history(envelope, rows, root):
    """Exclude only verified old-source rows; same title/identity alone is insufficient."""
    import delivery_contract as dc
    dc.verify_lineage(envelope, root)
    old_path = dc.resolve(root, envelope["lineage"]["source_path"])
    expected = envelope["lineage"]["source_sha256"]
    filtered = []
    for row in rows:
        source_path = row.get("source_json")
        own = False
        if isinstance(source_path, str) and source_path.strip():
            path = dc.resolve(root, source_path)
            own = path == old_path and path.is_file() and dc.file_hash(path) == expected
        if not own:
            filtered.append(row)
    return filtered


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check one schema v5 candidate against read-only history."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--title-threshold", type=float, default=0.76)
    parser.add_argument("--body-threshold", type=float, default=0.70)
    parser.add_argument("--idea-threshold", type=float, default=0.80)
    parser.add_argument("--phrase-threshold", type=int, default=22)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        candidate = _read_json(args.input)
        ledger_rows = _read_ledger(args.ledger)
        if candidate.get("document_kind") == "boss_ip_delivery":
            if candidate.get("lineage") is not None:
                ledger_rows = revision_history(candidate, ledger_rows, args.workspace_root)
            candidate = candidate["candidate_doc"]
        failures = find_similarity_failures(
            candidate,
            ledger_rows,
            title_threshold=args.title_threshold,
            body_threshold=args.body_threshold,
            idea_threshold=args.idea_threshold,
            phrase_threshold=args.phrase_threshold,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        print("INTEGRITY FAIL")
        return 2
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print("INTEGRITY FAIL")
        return 2
    print("INTEGRITY PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
