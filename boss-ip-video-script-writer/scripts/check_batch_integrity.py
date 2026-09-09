from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from content_contract import validate_batch


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, 1):
            if not raw_line.strip():
                continue
            value = json.loads(raw_line)
            if not isinstance(value, dict):
                raise ValueError(
                    f"feedback ledger line {line_number} must be an object"
                )
            rows.append(value)
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a v6 requested-count batch or historical v5 three-candidate batch."
    )
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--topic-pool", type=Path, required=True)
    parser.add_argument("--persona", type=Path, required=True)
    parser.add_argument("--feedback-ledger", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        candidates = [_load_json(path) for path in args.inputs]
        topic_pool = _load_json(args.topic_pool)
        persona = _load_json(args.persona)
        feedback_rows = _load_jsonl(args.feedback_ledger)
        failures = validate_batch(candidates, persona, feedback_rows, topic_pool)
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
