from __future__ import annotations

import re
from pathlib import Path


EVIDENCE = Path(__file__).resolve().parent / "evidence"
CASES = {
    "trigger-explicit-monologue.output.txt": (3, 3, 0),
    "trigger-implicit-story.output.txt": (3, 0, 3),
    "trigger-implicit-both.output.txt": (6, 3, 3),
}
FIELDS = ("形式", "主题", "创意说明", "完整文案", "预计时长")
INTERNAL_MARKERS = ("candidate_id", "product_facts_sha256", "internal_notes", "research_packet", "内部评分")
UNSUPPORTED_FACTS = ("参考价", "续航40", "限时", "仅剩", "赠品")


def main() -> int:
    for name, (total, monologues, stories) in CASES.items():
        text = (EVIDENCE / name).read_text(encoding="utf-8-sig")
        assert text.count("形式") == total, name
        assert all(text.count(field) == total for field in FIELDS), name
        assert len(re.findall(r"(?m)^\s*monologue\s*$|形式[：:]\s*monologue", text)) == monologues, name
        assert len(re.findall(r"(?m)^\s*story\s*$|形式[：:]\s*story", text)) == stories, name
        durations = [int(value) for value in re.findall(r"约\s*(\d+)\s*秒", text)]
        assert len(durations) == total, name
        assert all(25 <= value <= 35 for value in durations[:monologues]), name
        assert all(0 < value <= 90 for value in durations[monologues:]), name
        assert not any(marker.lower() in text.lower() for marker in INTERNAL_MARKERS), name
        assert not any(marker in text for marker in UNSUPPORTED_FACTS), name
        print(f"{name}: COUNT={total} MONOLOGUE={monologues} STORY={stories} DURATION=PASS PUBLIC_FIELDS_ONLY=PASS")

    missing = (EVIDENCE / "trigger-explicit-missing.output.txt").read_text(encoding="utf-8-sig").splitlines()
    expected = ["- 种类", "- 用途", "- 核心卖点", "- 目标顾客", "- 形式（仅接受 `monologue`、`story`、`both`）"]
    assert missing == expected, missing
    print("trigger-explicit-missing.output.txt: EXACT_MISSING_LIST=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
