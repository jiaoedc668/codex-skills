from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PROTECTED_FILE = Path("老板IP内容库") / "选题台账.jsonl"
PROTECTED_DIRECTORIES = (
    Path("老板IP内容库") / "草稿",
    Path("boss-ip-video-script-writer") / "output",
    Path("已有成品"),
)


def _resolved_path(root: Path, path: Path | str) -> Path:
    value = Path(path)
    return value.resolve() if value.is_absolute() else (root / value).resolve()


def _allowed_run(root: Path, allowed_run_dir: Path | str) -> Path:
    allowed = _resolved_path(root, allowed_run_dir)
    drafts = (root / "老板IP内容库" / "草稿").resolve()
    if allowed == drafts or not allowed.is_relative_to(drafts):
        raise ValueError("allowed run directory must be a child of 老板IP内容库/草稿")
    return allowed


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_protected(
    root: Path | str, allowed_run_dir: Path | str
) -> dict[str, str]:
    root_path = Path(root).resolve()
    allowed = _allowed_run(root_path, allowed_run_dir)
    files: set[Path] = set()

    protected_file = root_path / PROTECTED_FILE
    if protected_file.is_file():
        files.add(protected_file)

    for relative_directory in PROTECTED_DIRECTORIES:
        directory = root_path / relative_directory
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved == allowed or resolved.is_relative_to(allowed):
                continue
            if not resolved.is_relative_to(root_path):
                raise ValueError(f"protected path escapes repository root: {path}")
            files.add(path)

    return {
        path.relative_to(root_path).as_posix(): _sha256(path)
        for path in sorted(files, key=lambda item: item.relative_to(root_path).as_posix())
    }


def compare_snapshot(
    expected: dict[str, str], actual: dict[str, str]
) -> list[str]:
    failures: list[str] = []
    expected_paths = set(expected)
    actual_paths = set(actual)
    for path in sorted(expected_paths & actual_paths):
        if expected[path] != actual[path]:
            failures.append(f"changed: {path}")
    for path in sorted(expected_paths - actual_paths):
        failures.append(f"missing: {path}")
    for path in sorted(actual_paths - expected_paths):
        failures.append(f"added: {path}")
    return failures


def _relative_allowed(root: Path, allowed_run_dir: Path | str) -> str:
    allowed = _allowed_run(root, allowed_run_dir)
    return allowed.relative_to(root).as_posix()


def _write_snapshot(
    root: Path, allowed_run_dir: Path | str, output: Path
) -> int:
    allowed = _allowed_run(root, allowed_run_dir)
    output_path = _resolved_path(root, output)
    if not output_path.is_relative_to(allowed):
        raise ValueError("snapshot output must be inside the allowed run directory")
    payload = {
        "schema_version": 1,
        "hash_algorithm": "sha256",
        "allowed_run_dir": allowed.relative_to(root).as_posix(),
        "protected_files": snapshot_protected(root, allowed),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(output_path)
    print("INTEGRITY PASS: protected baseline written")
    return 0


def _verify_snapshot(
    root: Path, allowed_run_dir: Path | str, snapshot_path: Path
) -> int:
    source = _resolved_path(root, snapshot_path)
    with source.open("r", encoding="utf-8-sig") as handle:
        payload: Any = json.load(handle)
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("snapshot must use schema_version 1")
    if payload.get("hash_algorithm") != "sha256":
        raise ValueError("snapshot hash_algorithm must be sha256")
    current_allowed = _relative_allowed(root, allowed_run_dir)
    if payload.get("allowed_run_dir") != current_allowed:
        raise ValueError("snapshot allowed_run_dir does not match current run directory")
    expected = payload.get("protected_files")
    if not isinstance(expected, dict) or any(
        not isinstance(path, str) or not isinstance(digest, str)
        for path, digest in expected.items()
    ):
        raise ValueError("snapshot protected_files must be a path-to-hash object")
    actual = snapshot_protected(root, allowed_run_dir)
    failures = compare_snapshot(expected, actual)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print("INTEGRITY FAIL")
        return 2
    print("INTEGRITY PASS: protected files unchanged")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hash and verify protected project files.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--root", type=Path, required=True)
    snapshot.add_argument("--allowed-run-dir", type=Path, required=True)
    snapshot.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument("--allowed-run-dir", type=Path, required=True)
    verify.add_argument("--snapshot", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "snapshot":
            return _write_snapshot(root, args.allowed_run_dir, args.output)
        return _verify_snapshot(root, args.allowed_run_dir, args.snapshot)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        print("INTEGRITY FAIL")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
