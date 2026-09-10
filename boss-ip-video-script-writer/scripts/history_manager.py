#!/usr/bin/env python3
"""Read historical state and maintain the separate append-only feedback ledger."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterable


VALID_FEEDBACK_TYPES = {
    "candidate_feedback",
    "candidate_selection",
    "candidate_evaluation",
    "candidate_length_evaluation",
    "copy_confirmation",
    "revision",
    "publication_metrics",
}
VALID_EVALUATIONS = {
    "direct_shoot",
    "minor_revision",
    "major_revision",
    "rejected",
}
VALID_REASON_CODES = {
    "HOOK_WEAK",
    "EVENT_THIN",
    "DIALOGUE_UNNATURAL",
    "FAGE_GENERIC",
    "TOO_PREACHY",
    "UNSHOOTABLE",
    "FACT_RISK",
    "TOO_SIMILAR",
    "OTHER",
}
VALID_LENGTH_JUDGMENTS = {"too_short", "appropriate", "too_long"}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise SystemExit(f"Input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(data, dict):
        raise SystemExit("JSON root must be an object.")
    return data


def read_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for number, raw in enumerate(handle, 1):
            value = raw.strip()
            if not value:
                continue
            try:
                row = json.loads(value)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid ledger JSON at line {number}: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise SystemExit(f"Ledger line {number} must be an object.")
            rows.append(row)
    return rows


def append_rows(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    return count


def _validate_shared_preference_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise ValueError("共享偏好事件必须是对象")
    required = {
        "schema_version", "event_id", "event_type", "occurred_at",
        "product_id", "user_quote", "payload",
    }
    missing = sorted(required - set(event))
    if missing:
        raise ValueError("共享偏好事件缺少字段: " + ", ".join(missing))
    if event.get("schema_version") != 1 or event.get("event_type") != "creative_preference":
        raise ValueError("共享偏好事件必须使用 schema_version 1 和 creative_preference")
    if not clean(event.get("event_id")):
        raise ValueError("共享偏好事件缺少 event_id")
    if not clean(event.get("user_quote")):
        raise ValueError("共享偏好事件必须保留用户原话")
    payload = event.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("共享偏好 payload 必须是对象")
    if not clean(payload.get("source_skill")) or not clean(payload.get("preference")):
        raise ValueError("共享偏好 payload 必须包含 source_skill 和 preference")
    return deepcopy(event)


def read_shared_preferences(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8-sig") as handle:
        for number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"共享偏好第 {number} 行是损坏事件: {exc.msg}") from exc
            event = _validate_shared_preference_event(value)
            event_id = clean(event.get("event_id"))
            if event_id in seen:
                raise ValueError(f"重复 event_id: {event_id}")
            seen.add(event_id)
            rows.append(event)
    return rows


def append_shared_preference(path: Path, event: dict[str, Any]) -> dict[str, Any]:
    normalized = _validate_shared_preference_event(event)
    event_id = clean(normalized.get("event_id"))
    if any(clean(item.get("event_id")) == event_id for item in read_shared_preferences(path)):
        raise ValueError(f"重复 event_id: {event_id}")
    append_rows(path, [normalized])
    return normalized


def read_feedback(path: Path) -> list[dict[str, Any]]:
    """Read only explicit feedback events; blank or absent files mean no feedback."""
    rows = read_ledger(path)
    for number, row in enumerate(rows, 1):
        if row.get("event_type") not in VALID_FEEDBACK_TYPES:
            raise SystemExit(
                f"Invalid feedback event_type at line {number}: {row.get('event_type')}"
            )
    return rows


def clean_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise SystemExit(f"{field} must be an array.")
    items = [clean(item) for item in value if clean(item)]
    if len(items) != len(value):
        raise SystemExit(f"{field} cannot contain blank values.")
    return items


def validate_feedback_event(data: dict[str, Any]) -> dict[str, Any]:
    event_type = clean(data.get("event_type"))
    if event_type not in VALID_FEEDBACK_TYPES:
        raise SystemExit(
            "event_type must be candidate_feedback, candidate_selection, candidate_evaluation, "
            "candidate_length_evaluation, copy_confirmation, revision, or "
            "publication_metrics."
        )
    feedback_id = clean(data.get("feedback_id"))
    batch_id = clean(data.get("batch_id"))
    candidate_id = clean(data.get("candidate_id"))
    user_quote = clean(data.get("user_quote"))
    if not feedback_id or not user_quote:
        raise SystemExit("feedback_id and user_quote are required explicit signals.")

    row: dict[str, Any] = {
        "schema_version": 2,
        "event_type": event_type,
        "event_at": clean(data.get("event_at")) or now_iso(),
        "feedback_id": feedback_id,
        "batch_id": batch_id,
        "candidate_id": candidate_id,
        "revision_id": clean(data.get("revision_id")),
        "user_quote": user_quote,
    }
    if "format" in data:
        if data["format"] not in {"story", "monologue"}:
            raise SystemExit("feedback format must be story or monologue")
        row["format"] = data["format"]
    if event_type == "candidate_feedback":
        if not batch_id or not candidate_id or not row["revision_id"]:
            raise SystemExit("candidate_feedback requires batch_id, candidate_id, and revision_id.")
        preserve = clean_list(data.get("preserve", []), "preserve")
        avoid = clean_list(data.get("avoid", []), "avoid")
        if not preserve and not avoid:
            raise SystemExit("candidate_feedback requires preserve or avoid items.")
        if any(key in data for key in ("evaluation", "selection", "content_sha256")):
            raise SystemExit("candidate_feedback cannot imply evaluation, selection, or copy confirmation.")
        row.update({"preserve": preserve, "avoid": avoid})
    elif event_type == "candidate_selection":
        if not batch_id or not candidate_id:
            raise SystemExit("candidate_selection requires batch_id and candidate_id.")
        row["selection"] = "selected"
    elif event_type == "candidate_evaluation":
        evaluation = clean(data.get("evaluation"))
        if evaluation not in VALID_EVALUATIONS:
            raise SystemExit(
                "evaluation must be direct_shoot, minor_revision, major_revision, or rejected."
            )
        reason_codes = clean_list(data.get("reason_codes"), "reason_codes")
        unknown = sorted(set(reason_codes) - VALID_REASON_CODES)
        if unknown:
            raise SystemExit(f"Unknown reason_codes: {', '.join(unknown)}")
        preserve = clean_list(data.get("preserve", []), "preserve")
        avoid = clean_list(data.get("avoid", []), "avoid")
        if evaluation == "direct_shoot" and not preserve:
            raise SystemExit("direct_shoot feedback requires at least one preserve item with attribution.")
        if evaluation in {"major_revision", "rejected"} and not avoid:
            raise SystemExit(f"{evaluation} feedback requires at least one explicit avoid item.")
        if not candidate_id or not row["revision_id"]:
            raise SystemExit("candidate_evaluation requires candidate_id and revision_id.")
        row.update(
            {
                "evaluation": evaluation,
                "reason_codes": reason_codes,
                "preserve": preserve,
                "avoid": avoid,
            }
        )
    elif event_type == "candidate_length_evaluation":
        length_judgment = clean(data.get("length_judgment"))
        if not batch_id or not candidate_id or not row["revision_id"]:
            raise SystemExit(
                "candidate_length_evaluation requires batch_id, candidate_id, "
                "and revision_id."
            )
        if length_judgment not in VALID_LENGTH_JUDGMENTS:
            raise SystemExit(
                "length_judgment must be too_short, appropriate, or too_long."
            )
        row["length_judgment"] = length_judgment
    elif event_type == "copy_confirmation":
        content_sha256 = clean(data.get("content_sha256"))
        if not batch_id or not candidate_id or not row["revision_id"]:
            raise SystemExit(
                "copy_confirmation requires batch_id, candidate_id, and revision_id."
            )
        if SHA256_PATTERN.fullmatch(content_sha256) is None:
            raise SystemExit(
                "copy_confirmation content_sha256 must be 64 lowercase hex characters."
            )
        row["content_sha256"] = content_sha256
    elif event_type == "revision":
        from_revision = clean(data.get("from_revision"))
        to_revision = clean(data.get("to_revision"))
        changes = clean_list(data.get("changes"), "changes")
        if not candidate_id or not from_revision or not to_revision or not changes:
            raise SystemExit(
                "revision requires candidate_id, from_revision, to_revision, and changes."
            )
        if from_revision == to_revision:
            raise SystemExit("revision must create a new revision id.")
        row.update(
            {
                "from_revision": from_revision,
                "to_revision": to_revision,
                "changes": changes,
            }
        )
    else:
        source = clean(data.get("source"))
        data_date = clean(data.get("data_date"))
        metrics = data.get("metrics")
        if not source or not data_date or not isinstance(metrics, dict) or not metrics:
            raise SystemExit(
                "publication_metrics requires source, data_date, and a non-empty metrics object."
            )
        if any(
            isinstance(value, (dict, list)) or value in {"", None}
            for value in metrics.values()
        ):
            raise SystemExit(
                "publication metrics must contain non-blank scalar values, never inferred values."
            )
        row.update({"source": source, "data_date": data_date, "metrics": metrics})
    return row


def feedback_context(rows: list[dict[str, Any]], limit: int = 12) -> dict[str, Any]:
    recent = rows[-limit:] if limit > 0 else []
    preserve: list[str] = []
    avoid: list[str] = []
    publications: list[dict[str, Any]] = []
    length_feedback: list[dict[str, Any]] = []
    for row in recent:
        for item in row.get("preserve", []):
            if clean(item) and clean(item) not in preserve:
                preserve.append(clean(item))
        for item in row.get("avoid", []):
            if clean(item) and clean(item) not in avoid:
                avoid.append(clean(item))
        if row.get("event_type") == "publication_metrics":
            publications.append(
                {
                    "feedback_id": row.get("feedback_id"),
                    "source": row.get("source"),
                    "data_date": row.get("data_date"),
                    "metrics": row.get("metrics"),
                }
            )
        if row.get("event_type") == "candidate_length_evaluation":
            length_feedback.append(
                {
                    "feedback_id": row.get("feedback_id"),
                    "batch_id": row.get("batch_id"),
                    "candidate_id": row.get("candidate_id"),
                    "revision_id": row.get("revision_id"),
                    "length_judgment": row.get("length_judgment"),
                    "user_quote": row.get("user_quote"),
                }
            )
    return {
        "latest_feedback_ids": [row.get("feedback_id") for row in recent],
        "keep": preserve or ["无"],
        "avoid": avoid or ["无"],
        "length_feedback": length_feedback,
        "publication_data": publications or "无用户提供的发布数据",
    }


def clean(value: Any) -> str:
    return " ".join(str(value or "").split())


PERSONA_EVENT_KEYS = {
    "schema_version",
    "event_type",
    "operation",
    "record_id",
    "source_candidate_id",
    "reason",
    "record",
}
PERSONA_EVENT_TYPES = {
    "viewpoint_principle": (
        "viewpoint_principles",
        {"tension", "default_choice", "rejected_choice", "exceptions", "cost"},
    ),
    "fictional_continuity": (
        "fictional_continuity",
        {"claim", "scope", "allowed_reuse", "forbidden_expansion"},
    ),
}
PERSONA_OPERATIONS = {"add", "revise", "retire"}


def _validate_persona_evolution_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise ValueError("persona evolution event must be an object")
    actual_keys = set(event)
    if actual_keys != PERSONA_EVENT_KEYS:
        missing = sorted(PERSONA_EVENT_KEYS - actual_keys)
        unexpected = sorted(actual_keys - PERSONA_EVENT_KEYS)
        raise ValueError(
            "persona evolution event keys must be exact; "
            f"missing={missing}; unexpected={unexpected}"
        )
    if event.get("schema_version") != 1:
        raise ValueError("persona evolution schema_version must be 1")
    event_type = clean(event.get("event_type"))
    if event_type not in PERSONA_EVENT_TYPES:
        raise ValueError(
            "persona evolution event_type must be viewpoint_principle "
            "or fictional_continuity"
        )
    operation = clean(event.get("operation"))
    if operation not in PERSONA_OPERATIONS:
        raise ValueError("persona evolution operation must be add, revise, or retire")
    for key in ("record_id", "source_candidate_id", "reason"):
        if not clean(event.get(key)):
            raise ValueError(f"persona evolution {key} must be non-empty text")
    record = event.get("record")
    if not isinstance(record, dict):
        raise ValueError("persona evolution record must be an object")
    if operation == "retire":
        if record:
            raise ValueError("retire record must be empty so no version data can change")
    else:
        required_fields = PERSONA_EVENT_TYPES[event_type][1]
        if set(record) != required_fields:
            missing = sorted(required_fields - set(record))
            unexpected = sorted(set(record) - required_fields)
            raise ValueError(
                "persona evolution record fields must be exact; "
                f"missing={missing}; unexpected={unexpected}"
            )
        for key in sorted(required_fields - {"exceptions"}):
            if not clean(record.get(key)):
                raise ValueError(f"persona evolution record.{key} must be non-empty text")
        if event_type == "viewpoint_principle":
            exceptions = record.get("exceptions")
            if not isinstance(exceptions, list) or any(
                not clean(item) for item in exceptions
            ):
                raise ValueError(
                    "persona evolution record.exceptions must be an array of text"
                )
        elif record.get("scope") not in {"single_script", "reusable_low_risk"}:
            raise ValueError(
                "persona evolution record.scope must be single_script "
                "or reusable_low_risk"
            )
    normalized = deepcopy(event)
    normalized["event_type"] = event_type
    normalized["operation"] = operation
    for key in ("record_id", "source_candidate_id", "reason"):
        normalized[key] = clean(event[key])
    return normalized


def apply_persona_evolution(
    persona: dict[str, Any], event: dict[str, Any]
) -> dict[str, Any]:
    """Return a validated copy with one append-only persona evolution applied."""
    from content_contract import validate_persona_model

    current_failures = validate_persona_model(persona)
    if current_failures:
        raise ValueError("invalid current persona: " + "; ".join(current_failures))
    normalized_event = _validate_persona_evolution_event(event)
    updated = deepcopy(persona)
    event_type = normalized_event["event_type"]
    operation = normalized_event["operation"]
    collection_name = PERSONA_EVENT_TYPES[event_type][0]
    collection = updated[collection_name]
    record_id = clean(normalized_event["record_id"])
    matching = [record for record in collection if record.get("id") == record_id]

    if operation == "add":
        if matching:
            raise ValueError(f"persona record already exists: {record_id}")
        version = {
            "version": 1,
            **deepcopy(normalized_event["record"]),
            "source_candidate_id": clean(normalized_event["source_candidate_id"]),
            "reason": clean(normalized_event["reason"]),
        }
        collection.append(
            {
                "id": record_id,
                "status": "active",
                "active_version": 1,
                "versions": [version],
            }
        )
    else:
        if not matching:
            raise ValueError(f"unknown persona record: {record_id}")
        target = matching[0]
        if target.get("status") != "active":
            raise ValueError(f"retired persona record cannot change: {record_id}")
        if operation == "revise":
            next_version = target["active_version"] + 1
            target["versions"].append(
                {
                    "version": next_version,
                    **deepcopy(normalized_event["record"]),
                    "source_candidate_id": clean(
                        normalized_event["source_candidate_id"]
                    ),
                    "reason": clean(normalized_event["reason"]),
                }
            )
            target["active_version"] = next_version
        else:
            target["status"] = "retired"
            target.setdefault("retirement_history", []).append(
                {
                    "retired_version": target["active_version"],
                    "source_candidate_id": clean(
                        normalized_event["source_candidate_id"]
                    ),
                    "reason": clean(normalized_event["reason"]),
                }
            )

    updated_failures = validate_persona_model(updated)
    if updated_failures:
        raise ValueError("invalid updated persona: " + "; ".join(updated_failures))
    return updated


def _replace_json_atomically(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            temporary_path = Path(handle.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def command_record_persona_evolution(args: argparse.Namespace) -> int:
    persona = read_json(args.persona)
    event = read_json(args.input)
    try:
        updated = apply_persona_evolution(persona, event)
    except ValueError as exc:
        raise SystemExit(f"Invalid persona evolution: {exc}") from exc
    _replace_json_atomically(args.persona, updated)
    print(
        f"Recorded persona evolution {event['operation']} "
        f"{event['record_id']} in {args.persona.resolve()}"
    )
    return 0


def default_persona() -> dict[str, Any]:
    """Load the single maintained template; never overwrite existing instances."""
    template = Path(__file__).resolve().parents[1] / "references" / "persona-template.json"
    persona = json.loads(template.read_text(encoding="utf-8"))
    persona["updated_at"] = now_iso()
    return persona


def command_init(args: argparse.Namespace) -> int:
    data_root: Path = args.data_root
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "草稿").mkdir(parents=True, exist_ok=True)
    persona_path = data_root / "人物设定.json"
    ledger_path = data_root / "选题台账.jsonl"
    feedback_path = data_root / "反馈台账.jsonl"
    if not persona_path.exists():
        persona_path.write_text(
            json.dumps(default_persona(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Created persona: {persona_path.resolve()}")
    else:
        print(f"Kept existing persona: {persona_path.resolve()}")
    if ledger_path.exists():
        print(f"Kept existing ledger: {ledger_path.resolve()}")
    else:
        print(f"Historical ledger absent and kept absent: {ledger_path.resolve()}")
    if not feedback_path.exists():
        feedback_path.touch()
        print(f"Created feedback ledger: {feedback_path.resolve()}")
    else:
        print(f"Kept existing feedback ledger: {feedback_path.resolve()}")
    return 0


def command_record_topics(args: argparse.Namespace) -> int:
    raise SystemExit(
        "Historical topic ledger is read-only. Store explicit selection and evaluation "
        "in the independent feedback ledger."
    )


def command_set_status(args: argparse.Namespace) -> int:
    raise SystemExit(
        "Historical topic ledger is read-only. Record user decisions in the independent "
        "feedback ledger."
    )


def command_record_script(args: argparse.Namespace) -> int:
    raise SystemExit(
        "Historical topic ledger is read-only. Produced-script registration requires a "
        "separately authorized destination."
    )


def command_record_feedback(args: argparse.Namespace) -> int:
    data = read_json(args.input)
    row = validate_feedback_event(data)
    existing = read_feedback(args.feedback_ledger)
    feedback_id = clean(row.get("feedback_id"))
    if any(clean(item.get("feedback_id")) == feedback_id for item in existing):
        raise SystemExit(f"Duplicate feedback_id: {feedback_id}")
    append_rows(args.feedback_ledger, [row])
    print(
        f"Recorded explicit {row['event_type']} feedback {feedback_id} "
        f"in {args.feedback_ledger.resolve()}"
    )
    return 0


def command_recent_feedback(args: argparse.Namespace) -> int:
    rows = read_feedback(args.feedback_ledger)
    recent = rows[-args.limit :] if args.limit > 0 else []
    result = {
        "feedback_ledger": str(args.feedback_ledger.resolve()),
        "event_count": len(rows),
        "recent_events": recent,
        "candidate_context": feedback_context(rows, args.limit),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_record_shared_preference(args: argparse.Namespace) -> int:
    event = read_json(args.input)
    try:
        row = append_shared_preference(args.shared_ledger, event)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(
        f"Recorded shared creative preference {row['event_id']} "
        f"in {args.shared_ledger.resolve()}"
    )
    return 0


def command_recent_shared_preferences(args: argparse.Namespace) -> int:
    try:
        rows = read_shared_preferences(args.shared_ledger)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    recent = rows[-args.limit :] if args.limit > 0 else []
    print(json.dumps({
        "shared_ledger": str(args.shared_ledger.resolve()),
        "event_count": len(rows),
        "recent_events": recent,
    }, ensure_ascii=False, indent=2))
    return 0


def command_summarize(args: argparse.Namespace) -> int:
    events = read_ledger(args.ledger)
    latest_topics: dict[str, dict[str, Any]] = {}
    scripts: list[dict[str, Any]] = []
    for row in events:
        topic_id = clean(row.get("topic_id"))
        if row.get("event_type") == "topic_status" and topic_id:
            latest_topics[topic_id] = row
        if row.get("event_type") == "script" and row.get("status") in {"existing", "produced"}:
            scripts.append(row)
    summary = {
        "ledger": str(args.ledger.resolve()),
        "event_count": len(events),
        "topic_status_counts": dict(Counter(row.get("status", "unknown") for row in latest_topics.values())),
        "script_count": len(scripts),
        "category_counts": dict(Counter(clean(row.get("category")) or "未分类" for row in scripts)),
        "recent_scripts": [
            {
                "topic_id": row.get("topic_id"),
                "title": row.get("title"),
                "category": row.get("category"),
                "hook_mechanism": row.get("hook_mechanism"),
                "plot_device": row.get("plot_device"),
            }
            for row in scripts[-12:]
        ],
        "rejected_topics": [
            {
                "topic_id": row.get("topic_id"),
                "title": row.get("title"),
                "category": row.get("category"),
            }
            for row in latest_topics.values()
            if row.get("status") == "rejected"
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create missing state files without overwriting")
    init_parser.add_argument("--data-root", required=True, type=Path)
    init_parser.set_defaults(func=command_init)

    topics_parser = subparsers.add_parser(
        "record-topics", help="Retired: historical topic ledger is read-only"
    )
    topics_parser.add_argument("--input", required=True, type=Path)
    topics_parser.add_argument("--ledger", required=True, type=Path)
    topics_parser.set_defaults(func=command_record_topics)

    status_parser = subparsers.add_parser(
        "set-status", help="Retired: historical topic ledger is read-only"
    )
    status_parser.add_argument("--ledger", required=True, type=Path)
    status_parser.add_argument("--topic-id", required=True)
    status_parser.add_argument("--status", required=True)
    status_parser.add_argument("--note", default="")
    status_parser.set_defaults(func=command_set_status)

    script_parser = subparsers.add_parser(
        "record-script", help="Retired: historical topic ledger is read-only"
    )
    script_parser.add_argument("--input", required=True, type=Path)
    script_parser.add_argument("--ledger", required=True, type=Path)
    script_parser.add_argument("--document", type=Path)
    script_parser.set_defaults(func=command_record_script)

    feedback_parser = subparsers.add_parser(
        "record-feedback", help="Append one explicit event to the independent feedback ledger"
    )
    feedback_parser.add_argument("--input", required=True, type=Path)
    feedback_parser.add_argument("--feedback-ledger", required=True, type=Path)
    feedback_parser.set_defaults(func=command_record_feedback)

    persona_parser = subparsers.add_parser(
        "record-persona-evolution",
        help="Apply one validated append-only persona evolution event",
    )
    persona_parser.add_argument("--persona", required=True, type=Path)
    persona_parser.add_argument("--input", required=True, type=Path)
    persona_parser.set_defaults(func=command_record_persona_evolution)

    recent_parser = subparsers.add_parser(
        "recent-feedback", help="Read recent explicit feedback and candidate context"
    )
    recent_parser.add_argument("--feedback-ledger", required=True, type=Path)
    recent_parser.add_argument("--limit", type=int, default=12)
    recent_parser.set_defaults(func=command_recent_feedback)

    shared_record_parser = subparsers.add_parser(
        "record-shared-preference",
        help="Append one explicit shared creative preference",
    )
    shared_record_parser.add_argument("--input", required=True, type=Path)
    shared_record_parser.add_argument("--shared-ledger", required=True, type=Path)
    shared_record_parser.set_defaults(func=command_record_shared_preference)

    shared_recent_parser = subparsers.add_parser(
        "recent-shared-preferences",
        help="Read recent cross-skill creative preferences",
    )
    shared_recent_parser.add_argument("--shared-ledger", required=True, type=Path)
    shared_recent_parser.add_argument("--limit", type=int, default=12)
    shared_recent_parser.set_defaults(func=command_recent_shared_preferences)

    summary_parser = subparsers.add_parser("summarize", help="Print current topic and script state")
    summary_parser.add_argument("--ledger", required=True, type=Path)
    summary_parser.set_defaults(func=command_summarize)
    return parser


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
