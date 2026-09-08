from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from content_contract import validate_candidate


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
                raise ValueError(f"feedback ledger line {line_number} must be an object")
            rows.append(value)
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate one schema v5 Boss IP candidate.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--persona", type=Path, required=True)
    parser.add_argument("--feedback-ledger", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        candidate = _load_json(args.input)
        persona = _load_json(args.persona)
        feedback_rows = _load_jsonl(args.feedback_ledger)
        result = validate_candidate(candidate, persona, feedback_rows)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        print("INTEGRITY FAIL")
        return 2

    if result.failures:
        for failure in result.failures:
            print(f"FAIL: {failure}")
        print("INTEGRITY FAIL")
        return 2
    print("INTEGRITY PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
