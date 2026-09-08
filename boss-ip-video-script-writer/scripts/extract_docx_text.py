#!/usr/bin/env python3
"""Extract paragraphs and tables from a Word reference in document order."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from docx import Document
    from docx.document import Document as DocumentObject
    from docx.table import Table
    from docx.text.paragraph import Paragraph
except ImportError as exc:
    raise SystemExit(
        "Missing python-docx. Load the Codex workspace dependencies and run this script "
        "with the bundled Python runtime."
    ) from exc


def iter_blocks(document: DocumentObject):
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, document)
        elif child.tag.endswith("}tbl"):
            yield Table(child, document)


def clean(value: str) -> str:
    return " ".join(value.split())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    if not args.input.is_file() or args.input.suffix.lower() != ".docx":
        raise SystemExit(f"Input must be an existing .docx file: {args.input}")
    document = Document(args.input)
    number = 0
    for block in iter_blocks(document):
        if isinstance(block, Paragraph):
            value = clean(block.text)
            if value:
                number += 1
                print(f"P{number}: {value}")
            continue
        number += 1
        print(f"TABLE{number}:")
        for row_number, row in enumerate(block.rows, 1):
            print(f"  R{row_number}: " + " | ".join(clean(cell.text) for cell in row.cells))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
