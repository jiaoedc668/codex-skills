from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from contract import ContractError, validate_candidate_packet
from fixtures import packet
from workflow import EventError, Workspace


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="product-video-reverse-") as temp:
        workspace = Workspace(Path(temp) / "workspace")
        copy_text = packet()["candidates"][0]["full_copy"]
        workspace.register_product(packet()["brief"], "用户原话：登记测试产品")
        workspace.record_selection("test-cleaner-x1", "m1", copy_text, "用户原话：选择第一条")
        workspace.record_confirmation("test-cleaner-x1", copy_text, "用户原话：当前全文确认")

        feedback = workspace._path("feedback")
        confirmed_lines = feedback.read_text(encoding="utf-8").splitlines()
        feedback.write_text(confirmed_lines[0] + "\n", encoding="utf-8")
        print(f"CONFIRMATION_REMOVED_ALLOWED={workspace.can_generate_word('test-cleaner-x1', copy_text)}")
        feedback.write_text("\n".join(confirmed_lines) + "\n", encoding="utf-8")
        print(f"CONFIRMATION_RESTORED_ALLOWED={workspace.can_generate_word('test-cleaner-x1', copy_text)}")

        tampered = copy.deepcopy(packet())
        tampered["brief"]["selling_points"].append("未登记卖点")
        try:
            validate_candidate_packet(tampered)
        except ContractError as exc:
            print(f"FACTS_TAMPER_REJECTED={exc}")
        else:
            raise AssertionError("tampered facts were accepted")
        validate_candidate_packet(packet())
        print("FACTS_RESTORED=PASS")

        invalid = {
            "schema_version": 1,
            "event_id": "evt-missing-quote",
            "event_type": "creative_preference",
            "occurred_at": "2026-09-08T00:00:00+08:00",
            "product_id": "test-cleaner-x1",
            "user_quote": "",
            "payload": {"source_skill": "product-video-script-writer", "preference": "偏好先给冲突"},
        }
        try:
            workspace.append_event("shared_preferences", invalid)
        except EventError as exc:
            print(f"MISSING_QUOTE_REJECTED={exc}")
        else:
            raise AssertionError("missing quote was accepted")
        workspace.record_shared_preference(
            "test-cleaner-x1",
            "product-video-script-writer",
            "偏好先给冲突",
            "用户原话：我喜欢一上来就有冲突",
        )
        print("VALID_QUOTE_RESTORED=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
