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

    def test_fewer_than_three_samples_is_allowed(self) -> None:
        pool = valid_v6_pool()
        for count in (0, 1, 2):
            pool["viral_expression_samples"] = [viral_sample(i) for i in range(count)]
            self.assertEqual(count, len(select_topics.select_topics(pool)["viral_expression_samples"]))

    def test_evergreen_without_external_evidence_survives_authoring(self) -> None:
        import create_candidate
        import content_contract
        from test_dual_format_v6 import candidate_v6
        from v5_fixtures import valid_persona
        pool = valid_v6_pool()
        pool["viral_expression_samples"] = []
        for row in pool["prospects"]:
            row["topic_kind"] = "evergreen"
            row["research_evidence"] = {}
        draft = candidate_v6()
        brief = create_candidate.prepare(pool, "topic-1", core_viewpoint=draft["script"]["core_viewpoint"])
        candidate = create_candidate.assemble(brief, draft, valid_persona(), [])
        self.assertEqual([], content_contract.validate_candidate(candidate, valid_persona(), []).failures)
        self.assertEqual([], candidate["research_evidence"]["viral_expression_samples"])

    def test_current_issue_still_requires_heat_evidence_without_samples(self) -> None:
        pool = valid_v6_pool()
        pool["viral_expression_samples"] = []
        pool["prospects"][0]["research_evidence"]["heat_signals"] = []
        with self.assertRaisesRegex(ValueError, "heat signal"):
            select_topics.select_topics(pool)

    def test_fact_or_explicit_research_requires_sources_in_pool_and_candidate(self) -> None:
        import content_contract
        from test_dual_format_v6 import candidate_v6
        from v5_fixtures import valid_persona, valid_source
        pool = valid_v6_pool()
        pool["viral_expression_samples"] = []
        row = pool["prospects"][0]
        row["topic_kind"] = "evergreen"
        row["research_evidence"] = {"research_required": True}
        with self.assertRaisesRegex(ValueError, "required research"):
            select_topics.select_topics(pool)
        candidate = candidate_v6()
        candidate["research_evidence"] = {
            "topic_kind": "evergreen", "research_required": True,
            "viral_expression_samples": [],
        }
        self.assertTrue(any("required research" in f for f in content_contract.validate_candidate(candidate, valid_persona(), []).failures))
        row["research_evidence"]["fact_sources"] = [valid_source("2026-01-01")]
        select_topics.select_topics(pool)
        candidate["research_evidence"].update(row["research_evidence"])
        self.assertEqual([], content_contract.validate_candidate(candidate, valid_persona(), []).failures)

    def test_optional_research_cannot_hide_malformed_evidence(self) -> None:
        for evidence in (
            {"sources": [{"url": "invented"}]},
            {"recurrence_sources": [{"url": "invented"}]},
            {"heat_signals": "not a list"},
            {"research_required": "false"},
        ):
            with self.subTest(evidence=evidence):
                pool = valid_v6_pool()
                pool["viral_expression_samples"] = []
                pool["prospects"][0].update(topic_kind="evergreen", research_evidence=evidence)
                with self.assertRaises(ValueError):
                    select_topics.select_topics(pool)

    def test_even_one_optional_sample_must_be_readable_and_verified_shape(self) -> None:
        for change in ({"like_count": True}, {"url": "search-only"}, {"content_excerpt": ""}, {"content_access": "unavailable"}):
            with self.subTest(change=change):
                pool = valid_v6_pool()
                pool["viral_expression_samples"] = [viral_sample(1)]
                pool["viral_expression_samples"][0].update(change)
                with self.assertRaises(ValueError):
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
