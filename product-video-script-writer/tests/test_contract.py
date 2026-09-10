from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = TEST_ROOT.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(TEST_ROOT))

from fixtures import brief, packet

from contract import ContractError, public_candidates, validate_brief, validate_candidate_packet


class BriefContractTests(unittest.TestCase):
    def test_missing_required_inputs_are_returned_once_in_contract_order(self):
        missing = validate_brief({"product_name": "测试产品", "format": "monologue"})
        self.assertEqual(missing, ["category", "use", "selling_points", "target_customer"])

    def test_all_three_input_modes_are_accepted(self):
        for fmt in ("monologue", "story", "both"):
            with self.subTest(fmt=fmt):
                self.assertEqual(validate_brief(brief(fmt)), [])

    def test_unknown_input_mode_is_rejected(self):
        with self.assertRaisesRegex(ContractError, "format"):
            validate_brief(brief("ad"))


class CandidateContractTests(unittest.TestCase):
    def test_candidate_counts_are_exactly_three_three_and_six(self):
        for fmt, expected in (("monologue", 3), ("story", 3), ("both", 6)):
            with self.subTest(fmt=fmt):
                self.assertEqual(len(validate_candidate_packet(packet(fmt))), expected)

    def test_candidate_public_view_contains_only_allowed_fields(self):
        visible = public_candidates(packet("monologue"))
        self.assertEqual(
            set(visible[0]),
            {"format", "theme", "creative_note", "full_copy", "estimated_seconds"},
        )
        self.assertNotIn("internal_notes", visible[0])

    def test_substantially_similar_candidates_are_rejected(self):
        value = packet("monologue")
        value["candidates"][1]["full_copy"] = value["candidates"][0]["full_copy"]
        value["candidates"][1]["theme"] = value["candidates"][0]["theme"]
        with self.assertRaisesRegex(ContractError, "实质不同"):
            validate_candidate_packet(value)

    def test_unmapped_product_claim_is_rejected(self):
        value = packet("monologue")
        value["candidates"][0]["fact_claims"].append({"claim": "续航 40 分钟", "source_text": "续航 40 分钟"})
        with self.assertRaisesRegex(ContractError, "产品事实"):
            validate_candidate_packet(value)

    def test_tampered_product_fact_mapping_is_rejected(self):
        value = packet("monologue")
        value["brief"]["selling_points"][0] = "续航 40 分钟"
        with self.assertRaisesRegex(ContractError, "facts hash"):
            validate_candidate_packet(value)

    def test_research_requires_at_least_three_sources(self):
        value = packet("story")
        value["research"] = value["research"][:2]
        with self.assertRaisesRegex(ContractError, "至少 3"):
            validate_candidate_packet(value)

    def test_each_research_item_requires_recency_comparability_and_performance_evidence(self):
        for missing_key in ("published_at", "comparability_note", "performance_evidence"):
            with self.subTest(missing_key=missing_key):
                value = packet("story")
                del value["research"][0][missing_key]
                with self.assertRaisesRegex(ContractError, missing_key):
                    validate_candidate_packet(value)

    def test_non_douyin_research_requires_fallback_reason(self):
        value = packet("story")
        for item in value["research"]:
            item["platform"] = "xiaohongshu"
        with self.assertRaisesRegex(ContractError, "替代来源"):
            validate_candidate_packet(value)
        value["research_fallback_reason"] = "抖音不可达，改用用户提供的小红书参考"
        self.assertEqual(len(validate_candidate_packet(value)), 3)

    def test_monologue_duration_must_be_25_to_35_seconds(self):
        value = packet("monologue")
        value["candidates"][0]["estimated_seconds"] = 36
        with self.assertRaisesRegex(ContractError, "25-35"):
            validate_candidate_packet(value)

    def test_story_duration_must_not_exceed_90_seconds(self):
        value = packet("story")
        value["candidates"][0]["estimated_seconds"] = 91
        with self.assertRaisesRegex(ContractError, "90"):
            validate_candidate_packet(value)

    def test_each_candidate_uses_at_least_one_supplied_selling_point(self):
        value = packet("monologue")
        value["candidates"][0]["used_selling_points"] = []
        with self.assertRaisesRegex(ContractError, "卖点"):
            validate_candidate_packet(value)

    def test_banned_expressions_are_rejected(self):
        value = packet("monologue")
        value["candidates"][0]["full_copy"] += " 全网第一。"
        with self.assertRaisesRegex(ContractError, "禁用表达"):
            validate_candidate_packet(value)

    def test_political_subject_is_rejected(self):
        value = packet("story")
        value["candidates"][0]["theme"] = "总统办公室清洁"
        with self.assertRaisesRegex(ContractError, "政治"):
            validate_candidate_packet(value)


if __name__ == "__main__":
    unittest.main()
