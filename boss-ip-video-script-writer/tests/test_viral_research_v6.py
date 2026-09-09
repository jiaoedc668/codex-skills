from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import select_topics
from v5_fixtures import valid_topic_pool


def viral_sample(index: int) -> dict:
    return {
        "platform": "douyin",
        "title": f"测试用爆款视频{index}",
        "url": f"https://www.douyin.com/video/{7000000000000000000 + index}",
        "retrieved_at": "2026-09-08",
        "metric_scope": "single_video",
        "like_count": 100000 + index,
        "content_access": "transcript",
        "content_excerpt": "可读口播内容摘要，包含开场、理由和收尾。",
        "observed_mechanism": "首句抛出反常识判断，再用具体对照推进。",
        "adaptation_boundary": "只学抽象机制，不复制金句、连续台词或情节。",
    }


def valid_v6_pool() -> dict:
    pool = valid_topic_pool(with_unselected=True)
    pool["schema_version"] = 6
    pool["viral_expression_samples"] = [viral_sample(i) for i in range(1, 4)]
    for row in pool["prospects"]:
        case = row["production_case"]
        case["stakeholder_cost"] = case.pop("fage_cost")
    return pool


class ViralResearchV6Tests(unittest.TestCase):
    def test_three_readable_single_video_samples_at_100k_pass(self) -> None:
        result = select_topics.select_topics(valid_v6_pool())
        self.assertEqual(3, len(result["viral_expression_samples"]))

    def test_fewer_than_three_samples_is_rejected(self) -> None:
        pool = valid_v6_pool()
        pool["viral_expression_samples"] = pool["viral_expression_samples"][:2]
        with self.assertRaisesRegex(ValueError, "at least three"):
            select_topics.select_topics(pool)

    def test_account_total_or_below_100k_is_rejected(self) -> None:
        for mutation, message in (
            (lambda row: row.update(metric_scope="account_total"), "single_video"),
            (lambda row: row.update(like_count=99999), "100000"),
        ):
            with self.subTest(message=message):
                pool = valid_v6_pool()
                mutation(pool["viral_expression_samples"][0])
                with self.assertRaisesRegex(ValueError, message):
                    select_topics.select_topics(pool)

    def test_unreadable_or_duplicate_original_is_rejected(self) -> None:
        pool = valid_v6_pool()
        pool["viral_expression_samples"][0]["content_access"] = "title_only"
        with self.assertRaisesRegex(ValueError, "readable"):
            select_topics.select_topics(pool)

        pool = valid_v6_pool()
        pool["viral_expression_samples"][1]["url"] = pool[
            "viral_expression_samples"
        ][0]["url"]
        with self.assertRaisesRegex(ValueError, "unique"):
            select_topics.select_topics(pool)


if __name__ == "__main__":
    unittest.main()
