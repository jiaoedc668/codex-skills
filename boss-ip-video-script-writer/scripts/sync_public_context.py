from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import history_manager


OUTPUT_NAMES = (
    "persona-current.json",
    "recent-feedback.json",
    "recent-topics.json",
    "shared-preferences.json",
)
PUBLIC_LIMITS = {"feedback": 12, "topics": 24, "shared": 12}
FORBIDDEN_KEYS = {
    "user_quote",
    "script",
    "full_script",
    "draft",
    "research_evidence",
    "research",
    "ledger",
    "private_path",
    "internal_path",
    "api_key",
    "password",
    "token",
    "secret",
}
PATH_PATTERN = re.compile(
    r"(?:[A-Za-z]:[\\/]|(?:^|[\\/])(?:Users|home|tmp|var|private|business)[\\/])",
    re.IGNORECASE,
)
SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?<!\d)1[3-9]\d{9}(?!\d)|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
    re.IGNORECASE,
)


class PublicContextSafetyError(ValueError):
    """Raised when a public projection contains a forbidden value or shape."""


def _clean(value: Any) -> str:
    return history_manager.clean(value)


def _copy_fields(source: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: source[field] for field in fields if field in source}


def _public_persona(persona: dict[str, Any]) -> dict[str, Any]:
    identity = persona.get("identity")
    frame = persona.get("production_frame")
    if not isinstance(identity, dict) or not isinstance(frame, dict):
        raise PublicContextSafetyError("persona identity and production_frame must be objects")

    public_identity = _copy_fields(
        identity,
        (
            "display_name",
            "age_band",
            "role",
            "public_role_usage",
            "audience",
            "fiction_status",
        ),
    )
    public_frame = _copy_fields(
        frame,
        (
            "platform",
            "locations",
            "default_format",
            "scene_selection",
            "relationship_boundary",
            "duration",
            "brand_exposure",
            "commerce_stage",
            "duration_reference",
        ),
    )

    behaviors = []
    for item in persona.get("authorized_fictional_behaviors", []):
        if isinstance(item, dict):
            behaviors.append(_copy_fields(item, ("id", "behavior", "visible_proof", "limit")))

    expressions = []
    for item in persona.get("stable_expression", []):
        if isinstance(item, dict):
            expressions.append(_copy_fields(item, ("id", "pattern", "avoid")))

    principles = []
    for item in persona.get("viewpoint_principles", []):
        if not isinstance(item, dict) or item.get("status") != "active":
            continue
        versions = item.get("versions")
        if not isinstance(versions, list):
            continue
        active_version = item.get("active_version")
        current = next(
            (
                version
                for version in versions
                if isinstance(version, dict) and version.get("version") == active_version
            ),
            None,
        )
        if isinstance(current, dict):
            principles.append(
                {
                    "id": item.get("id"),
                    "active_version": active_version,
                    **_copy_fields(
                        current,
                        (
                            "tension",
                            "default_choice",
                            "rejected_choice",
                            "exceptions",
                            "cost",
                        ),
                    ),
                }
            )

    weaknesses = []
    for item in persona.get("visible_weaknesses", []):
        if isinstance(item, dict):
            weaknesses.append(_copy_fields(item, ("id", "weakness", "safe_payoff")))

    return {
        "schema_version": persona.get("schema_version"),
        "identity": public_identity,
        "production_frame": public_frame,
        "authorized_fictional_behaviors": behaviors,
        "stable_expression": expressions,
        "viewpoint_principles": principles,
        "visible_weaknesses": weaknesses,
    }


def _public_feedback(rows: list[dict[str, Any]]) -> dict[str, Any]:
    recent = rows[-PUBLIC_LIMITS["feedback"] :]
    context = history_manager.feedback_context(rows, PUBLIC_LIMITS["feedback"])
    items = []
    allowed = (
        "event_type",
        "event_at",
        "feedback_id",
        "batch_id",
        "candidate_id",
        "revision_id",
        "format",
        "evaluation",
        "reason_codes",
        "preserve",
        "avoid",
        "length_judgment",
        "source",
        "data_date",
        "metrics",
    )
    for row in recent:
        items.append(_copy_fields(row, allowed))
    safe_context = {
        "latest_feedback_ids": context["latest_feedback_ids"],
        "keep": context["keep"],
        "avoid": context["avoid"],
        "length_feedback": [
            _copy_fields(item, ("feedback_id", "batch_id", "candidate_id", "revision_id", "length_judgment"))
            for item in context["length_feedback"]
        ],
        "publication_data": context["publication_data"],
    }
    return {"items": items, "summary": safe_context}


def _public_topics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("event_type") != "topic_status":
            continue
        topic_id = _clean(row.get("topic_id"))
        if topic_id:
            latest[topic_id] = row
    items = []
    for row in list(latest.values())[-PUBLIC_LIMITS["topics"] :]:
        items.append(
            _copy_fields(
                row,
                ("topic_id", "title", "category", "status", "event_at", "topic_kind"),
            )
        )
    return {"items": items}


def _public_shared(rows: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for row in rows[-PUBLIC_LIMITS["shared"] :]:
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        items.append(
            {
                "event_id": row.get("event_id"),
                "occurred_at": row.get("occurred_at"),
                "source_skill": payload.get("source_skill"),
                "preference": payload.get("preference"),
            }
        )
    return {"items": items}


def _walk_public(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise PublicContextSafetyError(f"forbidden public field at {path}.{key}")
            _walk_public(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_public(child, f"{path}[{index}]")
    elif isinstance(value, str):
        if PATH_PATTERN.search(value):
            raise PublicContextSafetyError(f"internal path-like value at {path}")
        if SENSITIVE_VALUE_PATTERN.search(value):
            raise PublicContextSafetyError(f"sensitive value at {path}")


def _envelope(source: str, now: str, body: dict[str, Any]) -> dict[str, Any]:
    result = {
        "schema_version": 1,
        "snapshot_status": "current",
        "updated_at": now,
        "source_of_truth": source,
        "public_safe_only": True,
    }
    result.update(body)
    _walk_public(result)
    return result


def build_public_snapshots(
    persona_path: Path,
    feedback_path: Path,
    topic_path: Path,
    shared_path: Path,
    now: str | None = None,
) -> dict[str, dict[str, Any]]:
    timestamp = now or history_manager.now_iso()
    persona = history_manager.read_json(persona_path)
    feedback = history_manager.read_feedback(feedback_path)
    topics = history_manager.read_ledger(topic_path)
    shared = history_manager.read_shared_preferences(shared_path)
    snapshots = {
        "persona-current.json": _envelope(
            "local business project", timestamp, {"persona": _public_persona(persona)}
        ),
        "recent-feedback.json": _envelope(
            "local feedback ledger", timestamp, {"max_items": PUBLIC_LIMITS["feedback"], **_public_feedback(feedback)}
        ),
        "recent-topics.json": _envelope(
            "local topic ledger", timestamp, {"max_items": PUBLIC_LIMITS["topics"], **_public_topics(topics)}
        ),
        "shared-preferences.json": _envelope(
            "local shared creative preferences ledger",
            timestamp,
            {"max_items": PUBLIC_LIMITS["shared"], **_public_shared(shared)},
        ),
    }
    return snapshots


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))


def sync_public_context(
    persona_path: Path,
    feedback_path: Path,
    topic_path: Path,
    shared_path: Path,
    output_dir: Path,
) -> dict[str, Path]:
    snapshots = build_public_snapshots(
        persona_path, feedback_path, topic_path, shared_path
    )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".public-context-", dir=output_dir.parent) as temp_name:
        temp_dir = Path(temp_name)
        for name, data in snapshots.items():
            _write_json(temp_dir / name, data)
        written: dict[str, Path] = {}
        for name in OUTPUT_NAMES:
            target = output_dir / name
            os.replace(temp_dir / name, target)
            written[name] = target
    return written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--persona", required=True, type=Path)
    parser.add_argument("--feedback-ledger", required=True, type=Path)
    parser.add_argument("--topic-ledger", required=True, type=Path)
    parser.add_argument("--shared-ledger", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        written = sync_public_context(
            args.persona,
            args.feedback_ledger,
            args.topic_ledger,
            args.shared_ledger,
            args.output_dir,
        )
    except PublicContextSafetyError as exc:
        print(f"Public context sync rejected: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({name: str(path) for name, path in written.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
