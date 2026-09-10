#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from generate_word import WordGateError, generate_word
from workflow import EventError, Workspace


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Generate a confirmed product-video shooting DOCX")
    parser.add_argument("--workspace-root", required=True, type=Path)
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        value = json.loads(args.input.read_text(encoding="utf-8-sig"))
        path = generate_word(Workspace(args.workspace_root), args.product_id, value, args.output_root)
    except (OSError, json.JSONDecodeError, WordGateError, EventError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(str(path.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
