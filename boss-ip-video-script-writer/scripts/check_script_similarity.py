#!/usr/bin/env python3
"""Check a candidate boss-IP script against produced and rejected history."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


@dataclass
class ScriptMatch:
    title: str
    topic_id: str
    title_ratio: float
    hook_ratio: float
    body_ratio: float
    premise_ratio: float
    viewpoint_ratio: float
    signature_ratio: float
    longest_phrase: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--title-threshold", type=float, default=0.76)
    parser.add_argument("--hook-threshold", type=float, default=0.78)
    parser.add_argument("--body-threshold", type=float, default=0.70)
    parser.add_argument("--idea-threshold", type=float, default=0.80)
    parser.add_argument("--phrase-threshold", type=int, default=22)
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise SystemExit(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON at line {exc.lineno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise SystemExit("JSON root must be an object.")
    return data


def read_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid ledger line {number}: {exc.msg}") from exc
            if isinstance(row, dict):
                rows.append(row)
    return rows


def clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def normalize(value: Any) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", clean(value)).lower()


def ratio(left: Any, right: Any) -> float:
    a, b = normalize(left), normalize(right)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def longest_shared(left: Any, right: Any) -> str:
    a, b = normalize(left), normalize(right)
    if not a or not b:
        return ""
    block = max(SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks(), key=lambda item: item.size)
    return a[block.a : block.a + block.size]


def dialogue_text(data: dict[str, Any]) -> str:
    items = data.get("full_dialogue", [])
    if not isinstance(items, list):
        return ""
    return "".join(clean(item.get("line")) for item in items if isinstance(item, dict))


def signature_ratio(candidate: dict[str, Any], old: dict[str, Any]) -> float:
    keys = ["category", "hook_mechanism", "plot_device", "ending_type"]
    matches = 0
    available = 0
    for key in keys:
        left = normalize(candidate.get(key))
        right = normalize(old.get(key))
        if left and right:
            available += 1
            if left == right:
                matches += 1
    return matches / available if available else 0.0


def main() -> int:
    args = parse_args()
    data = read_json(args.input)
    signature = data.get("content_signature")
    meta = data.get("meta")
    hook = data.get("primary_hook")
    if not isinstance(signature, dict) or not isinstance(meta, dict) or not isinstance(hook, dict):
        raise SystemExit("meta, content_signature, and primary_hook are required objects.")
    candidate_topic_id = clean(meta.get("topic_id"))
    candidate_title = clean(data.get("title"))
    candidate_hook = clean(hook.get("voiceover"))
    candidate_body = dialogue_text(data)
    candidate_premise = clean(signature.get("premise"))
    candidate_viewpoint = clean(data.get("core_viewpoint"))
    generation_mode = clean(meta.get("generation_mode")) or "new_script"

    ledger = read_ledger(args.ledger)
    scripts = [
        row
        for row in ledger
        if row.get("event_type") == "script" and row.get("status") in {"existing", "produced"}
    ]
    matches: list[ScriptMatch] = []
    for row in scripts:
        if generation_mode == "revision" and clean(row.get("topic_id")) == candidate_topic_id:
            continue
        old_signature = {
            "category": row.get("category"),
            "hook_mechanism": row.get("hook_mechanism"),
            "plot_device": row.get("plot_device"),
            "ending_type": row.get("ending_type"),
        }
        matches.append(
            ScriptMatch(
                title=clean(row.get("title")),
                topic_id=clean(row.get("topic_id")),
                title_ratio=ratio(candidate_title, row.get("title")),
                hook_ratio=ratio(candidate_hook, row.get("hook")),
                body_ratio=ratio(candidate_body, row.get("body_text")),
                premise_ratio=ratio(candidate_premise, row.get("premise")),
                viewpoint_ratio=ratio(candidate_viewpoint, row.get("viewpoint")),
                signature_ratio=signature_ratio(signature, old_signature),
                longest_phrase=longest_shared(candidate_body, row.get("body_text")),
            )
        )
    matches.sort(
        key=lambda item: max(
            item.title_ratio,
            item.hook_ratio,
            item.body_ratio,
            item.premise_ratio,
            item.viewpoint_ratio,
            item.signature_ratio,
        ),
        reverse=True,
    )

    failures: list[str] = []
    if matches:
        top = matches[0]
        if top.title_ratio >= args.title_threshold:
            failures.append(f"title similarity {top.title_ratio:.2f} with {top.title}")
        if top.hook_ratio >= args.hook_threshold:
            failures.append(f"hook similarity {top.hook_ratio:.2f} with {top.title}")
        if top.body_ratio >= args.body_threshold:
            failures.append(f"body similarity {top.body_ratio:.2f} with {top.title}")
        if top.premise_ratio >= args.idea_threshold:
            failures.append(f"premise similarity {top.premise_ratio:.2f} with {top.title}")
        if top.viewpoint_ratio >= args.idea_threshold:
            failures.append(f"viewpoint similarity {top.viewpoint_ratio:.2f} with {top.title}")
        if top.signature_ratio >= 0.75 and top.premise_ratio >= 0.55:
            failures.append(f"structural signature repeats {top.title}")
        if len(top.longest_phrase) >= args.phrase_threshold:
            failures.append(
                f"shared phrase has {len(top.longest_phrase)} characters with {top.title}: {top.longest_phrase}"
            )

    latest_topics: dict[str, dict[str, Any]] = {}
    for row in ledger:
        if row.get("event_type") == "topic_status" and clean(row.get("topic_id")):
            latest_topics[clean(row.get("topic_id"))] = row
    topic_hits: list[tuple[float, dict[str, Any]]] = []
    for topic_id, row in latest_topics.items():
        if topic_id == candidate_topic_id:
            continue
        if row.get("status") not in {"proposed", "rejected", "selected"}:
            continue
        score = max(
            ratio(candidate_title, row.get("title")),
            ratio(candidate_premise, row.get("premise")),
            ratio(candidate_viewpoint, row.get("viewpoint")),
        )
        topic_hits.append((score, row))
    topic_hits.sort(key=lambda item: item[0], reverse=True)
    if topic_hits and topic_hits[0][0] >= args.idea_threshold:
        score, row = topic_hits[0]
        failures.append(
            f"candidate repeats a {row.get('status')} topic ({score:.2f}): {row.get('title')}"
        )

    print(f"Historical scripts checked: {len(scripts)}")
    print(f"Historical topic states checked: {len(latest_topics)}")
    for index, item in enumerate(matches[:3], 1):
        print(
            f"Match {index}: title={item.title_ratio:.2f}, hook={item.hook_ratio:.2f}, "
            f"body={item.body_ratio:.2f}, premise={item.premise_ratio:.2f}, "
            f"viewpoint={item.viewpoint_ratio:.2f}, structure={item.signature_ratio:.2f}, "
            f"longest={len(item.longest_phrase)} | {item.title}"
        )
    if failures:
        print("RESULT: FAIL")
        for failure in failures:
            print("- " + failure)
        return 0 if args.report_only else 2
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
