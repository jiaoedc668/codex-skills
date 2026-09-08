#!/usr/bin/env python3
"""Build a public-only semantic-review packet for a boss-IP candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


PUBLIC_PACKET_VERSION = 1
ARGUMENT_ENGINE_FIELDS = (
    "audience_takeaway",
    "common_belief",
    "non_obvious_claim",
    "competing_truths",
    "causal_proof",
    "fage_entanglement",
    "action_cost",
    "ending_without_slogan",
)
GENERIC_MORALS = (
    "要讲理",
    "要负责",
    "要关心员工",
    "要保护隐私",
    "加强沟通",
    "正确处理",
)
ARGUMENT_TEXT_FIELDS = (
    "audience_takeaway",
    "common_belief",
    "non_obvious_claim",
)


def _normalized(value: Any) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", str(value or "")).lower()


def _content_overlap(left: Any, right: Any) -> float:
    left_text = _normalized(left)
    right_text = _normalized(right)
    if not left_text or not right_text:
        return 0.0
    left_chars = set(left_text)
    return len(left_chars.intersection(set(right_text))) / len(left_chars)


def validate_argument_engine(data: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    engine = data.get("argument_engine")
    if not isinstance(engine, dict):
        return ["schema v4 requires argument_engine object"]

    for field in ARGUMENT_ENGINE_FIELDS:
        if field not in engine:
            failures.append(f"Required argument_engine field: {field}")
    for field in ARGUMENT_TEXT_FIELDS:
        if field in engine and not _normalized(engine.get(field)):
            failures.append(f"argument_engine.{field} is required")

    audience_takeaway = engine.get("audience_takeaway")
    if audience_takeaway is not None and any(
        _content_overlap(generic, audience_takeaway) >= 1.0
        for generic in GENERIC_MORALS
    ):
        failures.append("argument_engine.audience_takeaway is a generic moral")

    common_belief = engine.get("common_belief")
    non_obvious_claim = engine.get("non_obvious_claim")
    if _normalized(common_belief) and _normalized(non_obvious_claim) and (
        _content_overlap(common_belief, non_obvious_claim) >= 0.8
        and _content_overlap(non_obvious_claim, common_belief) >= 0.8
    ):
        failures.append(
            "argument_engine.non_obvious_claim must advance beyond common_belief"
        )

    truths = engine.get("competing_truths")
    if (
        not isinstance(truths, list)
        or len(truths) != 2
        or any(not _normalized(item) for item in truths)
        or _normalized(truths[0]) == _normalized(truths[1])
    ):
        failures.append(
            "argument_engine.competing_truths must contain exactly two distinct positions"
        )

    causal_proof = engine.get("causal_proof")
    if not isinstance(causal_proof, list) or len(causal_proof) != 3:
        failures.append(
            "argument_engine.causal_proof must contain exactly three causal beats"
        )
    else:
        beats: list[Any] = []
        for index, item in enumerate(causal_proof, 1):
            if not isinstance(item, dict):
                failures.append(
                    f"argument_engine.causal_proof[{index}] must be an object"
                )
                continue
            beats.append(item.get("beat"))
            if not _normalized(item.get("new_information")) or not _normalized(
                item.get("caused_action")
            ):
                failures.append(
                    f"argument_engine.causal_proof[{index}] requires new_information and caused_action"
                )
        if (
            len(beats) != 3
            or any(type(beat) is not int for beat in beats)
            or beats != [1, 2, 3]
        ):
            failures.append(
                "argument_engine.causal_proof beats must be integers 1, 2, and 3"
            )

    for field in ("fage_entanglement", "action_cost"):
        if field in engine and len(_normalized(engine.get(field))) < 6:
            failures.append(f"argument_engine.{field} must be concrete")

    if engine.get("ending_without_slogan") is not True:
        failures.append("argument_engine.ending_without_slogan must be true")

    return failures


def _has_text(value: Any) -> bool:
    return bool(_normalized(value))


def _is_iso8601(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_semantic_review(data: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    record = data.get("semantic_review")
    if not isinstance(record, dict):
        return ["schema v4 requires semantic_review object"]

    digest = packet_sha256(build_public_review_packet(data))
    if record.get("packet_sha256") != digest:
        failures.append(
            "semantic_review packet hash differs from current public packet"
        )

    reviews = record.get("reviews")
    review_items = reviews if isinstance(reviews, list) else []
    role_names = [
        item.get("role")
        for item in review_items
        if isinstance(item, dict)
    ]
    required_roles = {"viewpoint", "story", "persona"}
    if (
        len(review_items) != 3
        or len(role_names) != 3
        or len(set(role_names)) != 3
        or set(role_names) != required_roles
    ):
        failures.append(
            "semantic_review reviews must contain exactly viewpoint, story, and persona roles"
        )

    if len(review_items) != 3 or any(
        not isinstance(item, dict) or item.get("verdict") != "pass"
        for item in review_items
    ):
        failures.append("semantic_review all three reviews must pass")

    reviews_by_role: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(review_items, 1):
        if not isinstance(item, dict):
            failures.append(f"semantic_review reviews[{index}] must be an object")
            continue
        role = str(item.get("role") or f"review-{index}")
        reviews_by_role.setdefault(role, item)
        if item.get("input_sha256") != digest:
            failures.append(
                f"semantic_review {role} input hash differs from current public packet"
            )
        if item.get("target_visible") is not False:
            failures.append(f"semantic_review {role} must not see target")

    viewpoint = reviews_by_role.get("viewpoint")
    if viewpoint is not None:
        if not _has_text(viewpoint.get("inferred_takeaway")):
            failures.append("semantic_review viewpoint inferred_takeaway is required")
        sides = viewpoint.get("debate_sides")
        if (
            not isinstance(sides, list)
            or len(sides) != 2
            or any(not _has_text(side) for side in sides)
            or _normalized(sides[0]) == _normalized(sides[1])
        ):
            failures.append(
                "semantic_review viewpoint debate_sides must contain two distinct positions"
            )
        if viewpoint.get("generic_moral") is not False:
            failures.append("semantic_review viewpoint generic_moral must be false")
        evidence = viewpoint.get("evidence")
        if (
            not isinstance(evidence, list)
            or not evidence
            or any(not _has_text(item) for item in evidence)
        ):
            failures.append("semantic_review viewpoint evidence is required")

    story = reviews_by_role.get("story")
    if story is not None:
        for field in ("opening_event", "midpoint_change", "caused_action"):
            if not _has_text(story.get(field)):
                failures.append(f"semantic_review story {field} is required")
        if story.get("removable_beats") != []:
            failures.append("semantic_review story removable_beats must be empty")

    persona = reviews_by_role.get("persona")
    if persona is not None:
        for field in (
            "fage_entanglement",
            "visible_weakness_or_interest",
            "action_cost",
        ):
            if not _has_text(persona.get(field)):
                failures.append(f"semantic_review persona {field} is required")
        if persona.get("generic_boss_substitution") is not False:
            failures.append(
                "semantic_review persona generic_boss_substitution must be false"
            )

    aggregate = record.get("aggregate")
    if not isinstance(aggregate, dict):
        failures.append("semantic_review aggregate object is required")
    else:
        if aggregate.get("all_pass") is not True:
            failures.append("semantic_review aggregate all_pass must be true")
        if aggregate.get("target_match") is not True:
            failures.append("semantic_review aggregate target_match must be true")
        if aggregate.get("mismatch_reason") != "无":
            failures.append(
                "semantic_review aggregate mismatch_reason must be 无 when passing"
            )
        if not _is_iso8601(aggregate.get("reviewed_at")):
            failures.append("semantic_review aggregate reviewed_at must be ISO-8601")

    return failures


def build_public_review_packet(data: dict[str, Any]) -> dict[str, Any]:
    segments = data.get("segments") if isinstance(data.get("segments"), list) else []
    candidate = data.get("candidate") if isinstance(data.get("candidate"), dict) else {}
    workflow = data.get("workflow") if isinstance(data.get("workflow"), dict) else {}
    hook = data.get("primary_hook") if isinstance(data.get("primary_hook"), dict) else {}
    dialogue = (
        data.get("full_dialogue")
        if isinstance(data.get("full_dialogue"), list)
        else []
    )
    return {
        "packet_version": PUBLIC_PACKET_VERSION,
        "candidate_id": candidate.get("candidate_id", ""),
        "revision_id": workflow.get("revision_id", ""),
        "title": data.get("title", ""),
        "cover_title": data.get("cover_title", ""),
        "primary_hook": {
            key: hook.get(key, "")
            for key in ("voiceover", "visual", "screen_text")
            if key in hook
        },
        "full_dialogue": [
            {
                key: item.get(key, "")
                for key in ("speaker", "line")
                if key in item
            }
            for item in dialogue
            if isinstance(item, dict)
        ],
        "visual_actions": [
            item.get("visual_action", "")
            for item in segments
            if isinstance(item, dict)
        ],
        "on_screen_text": [
            item.get("screen_audio", "")
            for item in segments
            if isinstance(item, dict)
        ],
    }


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def packet_sha256(packet: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(packet).encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--hash-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    packet = build_public_review_packet(data)
    print(packet_sha256(packet) if args.hash_only else canonical_json(packet))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
