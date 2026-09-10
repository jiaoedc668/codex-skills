#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from workflow import EventError, WorkflowError, Workspace


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise WorkflowError("input JSON root must be an object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage append-only product-video workspace state")
    sub = parser.add_subparsers(dest="command", required=True)

    def command(name: str) -> argparse.ArgumentParser:
        child = sub.add_parser(name)
        child.add_argument("--workspace-root", required=True, type=Path)
        return child

    command("init")
    register = command("register-product")
    register.add_argument("--input", required=True, type=Path)
    register.add_argument("--user-quote", required=True)

    for name in ("select", "revise", "confirm"):
        child = command(name)
        child.add_argument("--product-id", required=True)
        if name == "select":
            child.add_argument("--candidate-id", required=True)
        child.add_argument("--copy-file", required=True, type=Path)
        child.add_argument("--user-quote", required=True)

    gate = command("can-generate-word")
    gate.add_argument("--product-id", required=True)
    gate.add_argument("--copy-file", required=True, type=Path)

    reject = command("reject")
    reject.add_argument("--product-id", required=True)
    reject.add_argument("--candidate-id", required=True)
    reject.add_argument("--user-quote", required=True)
    reject.add_argument("--reason-category", choices=("topic", "structure", "expression", "one_off"))

    preference = command("record-preference")
    preference.add_argument("--product-id", required=True)
    preference.add_argument("--source-skill", required=True)
    preference.add_argument("--preference", required=True)
    preference.add_argument("--user-quote", required=True)

    publishing = command("record-publishing")
    publishing.add_argument("--product-id", required=True)
    publishing.add_argument("--candidate-id", required=True)
    publishing.add_argument("--user-quote", required=True)
    publishing.add_argument("--views-24h", type=int)
    publishing.add_argument("--views-7d", type=int)
    publishing.add_argument("--recent-10-median", type=float)

    recent = command("read-ledger")
    recent.add_argument("--ledger", required=True, choices=("products", "used", "rejected", "feedback", "shared_preferences", "publishing"))
    recent.add_argument("--product-id")
    return parser


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    workspace = Workspace(args.workspace_root)
    try:
        if args.command == "init":
            workspace.initialize()
            result: Any = {"workspace_root": str(workspace.root.resolve()), "initialized": True}
        elif args.command == "register-product":
            result = workspace.register_product(read_json(args.input), args.user_quote)
        elif args.command == "select":
            result = workspace.record_selection(args.product_id, args.candidate_id, args.copy_file.read_text(encoding="utf-8"), args.user_quote)
        elif args.command == "revise":
            result = workspace.record_revision(args.product_id, args.copy_file.read_text(encoding="utf-8"), args.user_quote)
        elif args.command == "confirm":
            result = workspace.record_confirmation(args.product_id, args.copy_file.read_text(encoding="utf-8"), args.user_quote)
        elif args.command == "can-generate-word":
            allowed = workspace.can_generate_word(args.product_id, args.copy_file.read_text(encoding="utf-8"))
            result = {"allowed": allowed}
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if allowed else 2
        elif args.command == "reject":
            result = workspace.record_rejection(args.product_id, args.candidate_id, args.user_quote, args.reason_category)
        elif args.command == "record-preference":
            result = workspace.record_shared_preference(args.product_id, args.source_skill, args.preference, args.user_quote)
        elif args.command == "record-publishing":
            result = workspace.record_publish_data(args.product_id, args.candidate_id, args.user_quote, args.views_24h, args.views_7d, args.recent_10_median)
        else:
            rows = workspace.events_for_product(args.ledger, args.product_id) if args.product_id else workspace.read_events(args.ledger)
            result = {"ledger": args.ledger, "event_count": len(rows), "events": rows}
    except (OSError, json.JSONDecodeError, EventError, WorkflowError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
