#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from contract import ContractError, public_candidates, validate_candidate_packet


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Validate a product-video candidate packet")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--public-json", action="store_true")
    args = parser.parse_args()
    try:
        value = json.loads(args.input.read_text(encoding="utf-8-sig"))
        candidates = public_candidates(value) if args.public_json else validate_candidate_packet(value)
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    if args.public_json:
        print(json.dumps(candidates, ensure_ascii=False, indent=2))
    else:
        print(f"VALID candidate_count={len(candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
