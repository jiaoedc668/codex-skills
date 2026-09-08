#!/usr/bin/env python3
"""Reject the retired short-introduction candidate format."""

from __future__ import annotations

import argparse
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input")
    parser.add_argument("--ledger")
    return parser.parse_args()


def main() -> int:
    parse_args()
    print(
        "RESULT: FAIL\n"
        "- Short topic-introduction batches are retired. "
        "Create exactly three complete script JSON files and run check_candidate_batch.py."
    )
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
