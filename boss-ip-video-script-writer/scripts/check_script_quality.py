#!/usr/bin/env python3
"""Validate a complete boss-IP script for structure, persona, feedback state, and public-copy quality."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import semantic_review
from rank_topics import heat_score as calculate_heat_score
from rank_topics import selection_score as calculate_selection_score


HARD_PHRASES = [
    "说白了",
    "说穿了",
    "先说结论",
    "真正重要的是",
    "底层逻辑",
    "认知跃迁",
    "价值闭环",
    "内容矩阵",
    "全链路",
    "组合拳",
    "赶紧下单",
    "闭眼入",
]
GENERIC_HOOKS = [
    re.compile(r"发哥[，,]?我问你个事"),
    re.compile(r"你怎么看"),
    re.compile(r"很多人.{0,8}不知道"),
    re.compile(r"人到中年才明白"),
    re.compile(r"今天.{0,8}(?:聊|分享|介绍)"),
]
BIOGRAPHY_PATTERNS = [
    re.compile(r"我今年\d{2}岁"),
    re.compile(r"我(?:老婆|妻子|丈夫|老公|爱人|对象|儿子|女儿|孩子|父亲|母亲|爸|妈)(?:当年|以前|一直|就是|曾经|最近|现在)?"),
    re.compile(r"我(?:家|我们家|家里)(?:孩子|那位|老人|老伴)"),
    re.compile(r"我的(?:儿子|女儿|孩子|父亲|母亲|爸|妈|爱人|对象)"),
    re.compile(r"我创业\d+年"),
    re.compile(r"我(?:欠过|欠了|亏过|亏了|赚过|赚了).{0,12}(?:\d|万|亿)"),
    re.compile(r"我(?:背着|欠着).{0,12}(?:债|贷款)"),
    re.compile(r"我有.{0,6}(?:套房|家公司|员工)"),
    re.compile(r"我名下.{0,8}(?:房|车|公司)"),
]
UNIVERSAL_CONCLUSIONS = [
    "做人最重要的是良心",
    "做人最重要的是真诚",
    "人到中年才明白",
    "一切都要靠自己",
    "家和万事兴",
    "办法总比困难多",
    "坚持就会成功",
    "工具只是工具",
    "关键还是人",
    "所有关系都要相互理解",
    "人生没有太晚的开始",
    "边界也是智慧",
]
COMMERCIAL_PHRASES = ["下单", "直播间", "购物车", "优惠券", "千川"]
TECHNICAL_TERMS = ["现金流", "获客", "供应链", "转化", "复购", "投流", "私域", "商业模式"]
EMPTY_JARGON_TERMS = ["优化", "协同", "赋能", "抓手", "颗粒度", "机制"]
CONCRETE_REPLY_TOKENS = [
    "谁",
    "哪",
    "几点",
    "今天",
    "明天",
    "签",
    "删",
    "改",
    "写",
    "发",
    "打电话",
    "拿",
    "给我看",
]
PLACEHOLDERS = ["待补", "待定", "以后补", "TODO", "TBD", "占位"]
VAGUE_VALUES = {
    "有共鸣",
    "有价值",
    "有反差",
    "有悬念",
    "很吸引人",
    "真实亲切",
    "正向",
    "剧情推进",
    "冲突升级",
    "信息增加",
    "气氛变化",
    "继续",
}
ACTION_TOKENS = [
    "划掉",
    "签字",
    "改",
    "重排",
    "收回",
    "递回",
    "放下",
    "拿起",
    "关掉",
    "打开",
    "贴",
    "撕",
    "删除",
    "发送",
    "打电话",
    "起身",
    "换",
    "退",
    "陪",
    "顶",
    "试",
    "认账",
    "承认",
]
TOPIC_MODES = {"current_issue", "public_tension", "high_concept_scenario"}
HEAT_STATUSES = {"user_provided_signal", "dated_source", "evergreen_public_tension"}
RESEARCH_SCOPE_MODES = {"broad_pool", "category_focus"}
MACRO_THEMES = {
    "technology_and_work",
    "labor_and_power",
    "marriage_and_property",
    "eldercare_and_consumer_protection",
    "consumer_fairness",
    "housing_and_security",
    "privacy_and_platforms",
    "emotional_consumption",
    "age_and_opportunity",
    "family_roles",
}
STAKE_TAGS = {
    "职业去留",
    "身份体面",
    "公平责任",
    "隐私边界",
    "代际冲突",
    "技术替代",
    "信任破裂",
    "家庭权责",
    "公众评价",
    "规则冲突",
    "个人时间",
}
NARRATIVE_PATTERNS = {
    "result_first_flashback",
    "counter_reversal",
    "rule_escalation",
    "audience_knows",
    "early_wrong_choice",
    "dual_track_convergence",
    "realtime_pressure",
}
DIALOGUE_MODES = {
    "rapid_exchange",
    "deadpan_setback",
    "keyword_rebound",
    "prop_reveal",
}


@dataclass
class ValidationResult:
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    spoken_chars: int = 0
    segment_count: int = 0
    source_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.failures


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise SystemExit(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON at line {exc.lineno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise SystemExit("JSON root must be an object.")
    return data


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSONL at line {number}: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise SystemExit(f"JSONL line {number} must be an object.")
            rows.append(row)
    return rows


def clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def normalized(value: Any) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", clean(value)).lower()


def content_overlap(left: Any, right: Any) -> float:
    a = normalized(left).replace("发哥", "")
    b = normalized(right).replace("发哥", "")
    if not a or not b:
        return 0.0
    a_chars = set(a)
    return len(a_chars.intersection(set(b))) / len(a_chars)


def add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def required_mapping(data: dict[str, Any], key: str, result: ValidationResult) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        result.failures.append(f"Required object missing: {key}")
        return {}
    return value


def required_list(data: dict[str, Any], key: str, result: ValidationResult) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        result.failures.append(f"Required array missing: {key}")
        return []
    return value


def require_fields(obj: dict[str, Any], prefix: str, keys: list[str], result: ValidationResult) -> None:
    for key in keys:
        value = obj.get(key)
        if not clean(value):
            result.failures.append(f"{prefix}.{key} is required")
        elif any(token in clean(value) for token in PLACEHOLDERS):
            result.failures.append(f"{prefix}.{key} contains a placeholder")


def persona_field_value(persona: dict[str, Any], field_name: str) -> Any:
    if field_name in persona:
        return persona.get(field_name)
    legacy = persona.get("legacy_v2")
    if isinstance(legacy, dict):
        return legacy.get(field_name)
    return None


def persona_ids(persona: dict[str, Any], field_name: str) -> set[str]:
    values = persona_field_value(persona, field_name)
    if not isinstance(values, list):
        return set()
    return {
        clean(item.get("id"))
        for item in values
        if isinstance(item, dict) and clean(item.get("id"))
    }


def validate_persona_model(persona: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    identity = persona.get("identity")
    if not isinstance(identity, dict) or identity.get("fiction_status") != "授权虚构人设":
        failures.append("persona.identity.fiction_status must be 授权虚构人设")
    object_fields = {
        "authorized_fictional_behaviors": ["id", "behavior", "visible_proof", "limit"],
        "stable_expression": ["id", "pattern", "avoid"],
        "value_tradeoffs": ["id", "tension", "default_choice", "cost"],
        "visible_weaknesses": ["id", "weakness", "safe_payoff"],
        "comedy_relationships": ["id", "pair", "dynamic", "boundary"],
    }
    vague_terms = {"真实亲切", "正向", "有共鸣", "有反差", "轻松", "真实"}
    for field_name, required in object_fields.items():
        values = persona_field_value(persona, field_name)
        if not isinstance(values, list) or not values:
            failures.append(f"persona.{field_name} must be a non-empty array")
            continue
        ids: list[str] = []
        for index, item in enumerate(values, 1):
            if not isinstance(item, dict):
                failures.append(f"persona.{field_name}[{index}] must be an object")
                continue
            for key in required:
                value = clean(item.get(key))
                if not value:
                    failures.append(f"persona.{field_name}[{index}].{key} is required")
                elif value in vague_terms:
                    failures.append(
                        f"persona.{field_name}[{index}].{key} is too vague: {value}"
                    )
            if clean(item.get("id")):
                ids.append(clean(item.get("id")))
        if len(ids) != len(set(ids)):
            failures.append(f"persona.{field_name} contains duplicate ids")
    forbidden = persona.get("fact_forbidden")
    if not isinstance(forbidden, list) or not forbidden or any(not clean(x) for x in forbidden):
        failures.append("persona.fact_forbidden must be a non-empty concrete array")
    else:
        blob = "".join(clean(item) for item in forbidden)
        for concept in ["婚姻", "子女", "财富", "债务"]:
            if concept not in blob:
                failures.append(f"persona.fact_forbidden must cover {concept}")
    if not isinstance(persona_field_value(persona, "approved_continuity_claims"), list):
        failures.append("persona.approved_continuity_claims must be an array")
    return failures


def expected_feedback_context(rows: list[dict[str, Any]]) -> dict[str, Any]:
    recent = rows[-12:]
    keep: list[str] = []
    avoid: list[str] = []
    publications: list[dict[str, Any]] = []
    for row in recent:
        for item in row.get("preserve", []):
            value = clean(item)
            if value and value not in keep:
                keep.append(value)
        for item in row.get("avoid", []):
            value = clean(item)
            if value and value not in avoid:
                avoid.append(value)
        if row.get("event_type") == "publication_metrics":
            publications.append(
                {
                    "feedback_id": row.get("feedback_id"),
                    "source": row.get("source"),
                    "data_date": row.get("data_date"),
                    "metrics": row.get("metrics"),
                }
            )
    return {
        "latest_feedback_ids": [clean(row.get("feedback_id")) for row in recent],
        "keep": keep or ["无"],
        "avoid": avoid or ["无"],
        "publication_data": publications or "无用户提供的发布数据",
    }


def validate_feedback_context(
    context: dict[str, Any],
    result: ValidationResult,
    feedback_rows: list[dict[str, Any]] | None,
) -> None:
    read_at = clean(context.get("read_at"))
    ids = context.get("latest_feedback_ids")
    keep = context.get("keep")
    avoid = context.get("avoid")
    publication = context.get("publication_data")
    if not read_at:
        result.failures.append("candidate.feedback_context.read_at is required")
    if not isinstance(ids, list) or any(not clean(item) for item in ids):
        result.failures.append("candidate.feedback_context.latest_feedback_ids must be an array")
        ids = []
    for key, value in (("keep", keep), ("avoid", avoid)):
        if not isinstance(value, list) or not value or any(not clean(item) for item in value):
            result.failures.append(f"candidate.feedback_context.{key} must contain explicit values")
    if publication in {"", None}:
        result.failures.append("candidate.feedback_context.publication_data is required")
    if not ids:
        if keep != ["无"] or avoid != ["无"]:
            result.failures.append("no feedback ids requires keep and avoid to be exactly ['无']")
        if publication != "无用户提供的发布数据":
            result.failures.append("no feedback ids cannot claim publication data")
    if feedback_rows is not None:
        expected = expected_feedback_context(feedback_rows)
        actual = {
            "latest_feedback_ids": [clean(item) for item in ids],
            "keep": keep,
            "avoid": avoid,
            "publication_data": publication,
        }
        if actual != expected:
            result.failures.append(
                "candidate feedback context is stale or differs from the latest explicit ledger"
            )


def validate_topic_strategy(
    topic: dict[str, Any],
    public_text: str,
    sources: list[Any],
    feedback_context: dict[str, Any],
    result: ValidationResult,
) -> None:
    require_fields(
        topic,
        "topic_strategy",
        ["topic_mode", "macro_theme", "public_question", "opposing_positions", "stake_evidence", "escalation_event"],
        result,
    )
    mode = clean(topic.get("topic_mode"))
    if mode not in TOPIC_MODES:
        result.failures.append("topic_strategy.topic_mode is invalid")
    if clean(topic.get("macro_theme")) not in MACRO_THEMES:
        result.failures.append("topic_strategy.macro_theme is invalid")

    question = clean(topic.get("public_question"))
    if len(normalized(question)) < 10:
        result.failures.append("topic_strategy.public_question must be a concrete public choice")

    positions = topic.get("opposing_positions")
    if not isinstance(positions, list) or len(positions) != 2 or any(
        len(normalized(item)) < 6 for item in positions
    ):
        result.failures.append("topic_strategy.opposing_positions must contain exactly two concrete sides")
    elif normalized(positions[0]) == normalized(positions[1]) or (
        content_overlap(positions[0], positions[1]) >= 0.8
        and content_overlap(positions[1], positions[0]) >= 0.8
    ):
        result.failures.append("topic_strategy.opposing_positions must be genuinely different")

    stakes = topic.get("stake_evidence")
    if not isinstance(stakes, list) or not 2 <= len(stakes) <= 3:
        result.failures.append("topic_strategy.stake_evidence must contain 2-3 public risks")
    else:
        tags: list[str] = []
        for index, item in enumerate(stakes, 1):
            if not isinstance(item, dict):
                result.failures.append(f"topic_strategy.stake_evidence[{index}] must be an object")
                continue
            tag = clean(item.get("tag"))
            proof = clean(item.get("public_proof"))
            tags.append(tag)
            if tag not in STAKE_TAGS:
                result.failures.append(f"topic_strategy.stake_evidence[{index}].tag is invalid")
            if len(normalized(proof)) < 4:
                result.failures.append(f"topic_strategy.stake_evidence[{index}].public_proof is too vague")
            elif normalized(proof) not in normalized(public_text):
                result.failures.append(
                    f"topic_strategy.stake_evidence[{index}] is not visible in public copy"
                )
        if len(tags) != len(set(tags)):
            result.failures.append("topic_strategy.stake_evidence tags must be distinct")

    novelty = topic.get("novelty_break")
    if not isinstance(novelty, dict):
        result.failures.append("Required object missing: topic_strategy.novelty_break")
    else:
        require_fields(
            novelty,
            "topic_strategy.novelty_break",
            ["expected_pattern", "story_break"],
            result,
        )
        expected = clean(novelty.get("expected_pattern"))
        story_break = clean(novelty.get("story_break"))
        if min(len(normalized(expected)), len(normalized(story_break))) < 8:
            result.failures.append("topic_strategy.novelty_break must describe both old and new patterns")
        elif content_overlap(expected, story_break) >= 0.8 and content_overlap(story_break, expected) >= 0.8:
            result.failures.append("topic_strategy.story_break only repeats the expected pattern")
        if story_break and content_overlap(story_break, public_text) < 0.45:
            result.failures.append("topic_strategy.story_break is not evidenced by public copy")

    escalation = clean(topic.get("escalation_event"))
    if len(normalized(escalation)) < 8:
        result.failures.append("topic_strategy.escalation_event must exceed a routine daily setup")
    elif content_overlap(escalation, public_text) < 0.65:
        result.failures.append("topic_strategy.escalation_event is not evidenced by public copy")

    heat = topic.get("heat_basis")
    if not isinstance(heat, dict):
        result.failures.append("Required object missing: topic_strategy.heat_basis")
        return
    require_fields(heat, "topic_strategy.heat_basis", ["status", "source_ref", "claim"], result)
    status = clean(heat.get("status"))
    source_ref = clean(heat.get("source_ref"))
    claim = clean(heat.get("claim"))
    if status not in HEAT_STATUSES:
        result.failures.append("topic_strategy.heat_basis.status is invalid")
    if mode == "current_issue" and status not in {"user_provided_signal", "dated_source"}:
        result.failures.append("current_issue requires a user-provided or dated source")
    if status == "evergreen_public_tension" and claim != "不宣称当前热点":
        result.failures.append("evergreen public tension must not claim current heat")
    elif status == "user_provided_signal":
        feedback_ids = {
            clean(item) for item in feedback_context.get("latest_feedback_ids", []) if clean(item)
        }
        if source_ref not in feedback_ids:
            result.failures.append("user-provided heat basis must reference an explicit feedback id")
    elif status == "dated_source":
        matched = False
        for source in sources:
            if not isinstance(source, dict):
                continue
            locator = clean(source.get("locator"))
            title = clean(source.get("title"))
            source_date = clean(source.get("source_date"))
            if source_ref in {locator, title} and source_date and source_date != "未显示":
                matched = source.get("source_kind") in {"web", "user_provided"}
        if not matched:
            result.failures.append("dated heat basis must match a dated web or user-provided source")

    ranking = topic.get("selection_ranking")
    if not isinstance(ranking, dict):
        result.failures.append("Required object missing: topic_strategy.selection_ranking")
        return
    require_fields(
        ranking,
        "topic_strategy.selection_ranking",
        [
            "pool_id",
            "pool_size",
            "eligible_count",
            "heat_rank",
            "final_rank",
            "heat_evidence",
            "audience_conflict_score",
            "fage_fit_score",
            "shootability_score",
            "selection_score",
            "evidence_refs",
            "decision_note",
        ],
        result,
    )
    integers: dict[str, int] = {}
    for field_name in [
        "pool_size",
        "eligible_count",
        "heat_rank",
        "final_rank",
        "heat_score",
        "audience_conflict_score",
        "fage_fit_score",
        "shootability_score",
    ]:
        value = ranking.get(field_name)
        if isinstance(value, bool) or not isinstance(value, int):
            result.failures.append(f"topic_strategy.selection_ranking.{field_name} must be an integer")
        else:
            integers[field_name] = value
    pool_size = integers.get("pool_size", 0)
    eligible_count = integers.get("eligible_count", 0)
    heat_rank = integers.get("heat_rank", 0)
    final_rank = integers.get("final_rank", 0)
    if pool_size < 9:
        result.failures.append("topic selection ranking must compare at least nine researched topics")
    if eligible_count < 1 or eligible_count > pool_size:
        result.failures.append("topic selection eligible_count must be within the comparison pool")
    if heat_rank < 1 or heat_rank > pool_size:
        result.failures.append("topic selection heat_rank is outside the comparison pool")
    if final_rank < 1 or final_rank > eligible_count:
        result.failures.append("topic selection final_rank is outside the eligible pool")
    try:
        expected_heat = calculate_heat_score(ranking.get("heat_evidence"))
        if integers.get("heat_score") != expected_heat:
            result.failures.append("topic selection heat_score does not match its evidence")
        expected_selection = calculate_selection_score(
            expected_heat,
            ranking.get("audience_conflict_score"),
            ranking.get("fage_fit_score"),
            ranking.get("shootability_score"),
        )
        selection_value = ranking.get("selection_score")
        if isinstance(selection_value, bool) or not isinstance(selection_value, (int, float)):
            result.failures.append("topic selection selection_score must be numeric")
        elif abs(float(selection_value) - expected_selection) > 0.001:
            result.failures.append("topic selection selection_score does not match fixed weights")
    except ValueError as exc:
        result.failures.append(f"topic selection evidence is invalid: {exc}")
    evidence_refs = ranking.get("evidence_refs")
    source_refs = {
        clean(source.get(key))
        for source in sources
        if isinstance(source, dict)
        for key in ("locator", "title")
        if clean(source.get(key))
    }
    if not isinstance(evidence_refs, list) or not evidence_refs:
        result.failures.append("topic selection ranking requires at least one source reference")
    else:
        cleaned_refs = [clean(item) for item in evidence_refs]
        if any(not item or item not in source_refs for item in cleaned_refs):
            result.failures.append("topic selection evidence_refs must match research_sources")
        if mode == "current_issue" and source_ref not in cleaned_refs:
            result.failures.append("current issue heat source must be included in selection ranking evidence")
    decision_note = clean(ranking.get("decision_note"))
    if len(normalized(decision_note)) < 10 or decision_note in VAGUE_VALUES:
        result.failures.append("topic selection decision_note must explain the actual ranking tradeoff")


def validate_creative_adaptation(
    adaptation: Any,
    sources: list[Any],
    result: ValidationResult,
    required: bool,
) -> None:
    if not isinstance(adaptation, dict):
        if required:
            result.failures.append("selected/refined copy requires creative_adaptation")
        return
    require_fields(adaptation, "creative_adaptation", ["reviewed_works", "adoption_disclosure"], result)
    works = adaptation.get("reviewed_works")
    if not isinstance(works, list):
        result.failures.append("creative_adaptation.reviewed_works must be an array")
        return
    if required and len(works) < 2:
        result.failures.append("selected/refined copy must review at least two related works")
    source_locators = {
        clean(source.get("locator"))
        for source in sources
        if isinstance(source, dict) and source.get("source_kind") == "web"
    }
    adopted_titles: list[str] = []
    locators: list[str] = []
    for index, work in enumerate(works, 1):
        if not isinstance(work, dict):
            result.failures.append(f"creative_adaptation.reviewed_works[{index}] must be an object")
            continue
        require_fields(
            work,
            f"creative_adaptation.reviewed_works[{index}]",
            ["title", "locator", "decision", "observed_mechanism", "adopted_mechanism", "copyright_boundary"],
            result,
        )
        title = clean(work.get("title"))
        locator = clean(work.get("locator"))
        decision = clean(work.get("decision"))
        locators.append(locator)
        if not locator.startswith(("http://", "https://")) or locator not in source_locators:
            result.failures.append(
                f"creative_adaptation.reviewed_works[{index}].locator must match a web research source"
            )
        if decision not in {"adopted", "observe_only", "not_adopted"}:
            result.failures.append(f"creative_adaptation.reviewed_works[{index}].decision is invalid")
        observed = clean(work.get("observed_mechanism"))
        boundary = clean(work.get("copyright_boundary"))
        adopted = clean(work.get("adopted_mechanism"))
        if len(normalized(observed)) < 8 or len(normalized(boundary)) < 8:
            result.failures.append(
                f"creative_adaptation.reviewed_works[{index}] needs a concrete mechanism and boundary"
            )
        if decision == "adopted":
            adopted_titles.append(title)
            if len(normalized(adopted)) < 8:
                result.failures.append(
                    f"creative_adaptation.reviewed_works[{index}] must state the adopted mechanism"
                )
        elif adopted != "无":
            result.failures.append(
                f"creative_adaptation.reviewed_works[{index}] must use adopted_mechanism 无 when not adopted"
            )
    if len(locators) != len(set(locators)):
        result.failures.append("creative_adaptation reviewed work links must be distinct")
    disclosure = clean(adaptation.get("adoption_disclosure"))
    if adopted_titles and not any(title and title in disclosure for title in adopted_titles):
        result.failures.append("creative_adaptation disclosure must name at least one adopted work")
    if required and not adopted_titles and disclosure != "未采用具体作品机制":
        result.failures.append("creative_adaptation must clearly disclose that no work was adopted")


def validate_script(
    data: dict[str, Any],
    persona: dict[str, Any],
    feedback_rows: list[dict[str, Any]] | None = None,
    required_schema_version: int | None = None,
) -> ValidationResult:
    result = ValidationResult()
    result.failures.extend(validate_persona_model(persona))
    schema_version = data.get("schema_version")
    if schema_version not in {2, 3, 4}:
        result.failures.append("schema_version must be 2, 3, or 4")
    if required_schema_version is not None and schema_version != required_schema_version:
        result.failures.append(
            f"submission requires schema_version {required_schema_version}"
        )
    enforce_v4_submission = schema_version == 4 or required_schema_version == 4
    if enforce_v4_submission:
        result.failures.extend(semantic_review.validate_argument_engine(data))
        result.failures.extend(semantic_review.validate_semantic_review(data))
    craft_v3 = schema_version in {3, 4}

    candidate = required_mapping(data, "candidate", result)
    topic = required_mapping(data, "topic_strategy", result)
    workflow = required_mapping(data, "workflow", result)
    meta = required_mapping(data, "meta", result)
    signature = required_mapping(data, "content_signature", result)
    diagnostics = required_mapping(data, "creative_diagnostics", result)
    story = required_mapping(data, "story_blueprint", result)
    dialogue_design = required_mapping(data, "dialogue_design", result) if craft_v3 else {}
    evidence = required_mapping(data, "persona_evidence", result)
    hook = required_mapping(data, "primary_hook", result)
    cast = required_list(data, "cast", result)
    preparation = required_list(data, "preparation", result)
    segments = required_list(data, "segments", result)
    dialogue = required_list(data, "full_dialogue", result)
    notes = required_list(data, "shooting_notes", result)
    sources = required_list(data, "research_sources", result)
    claims = required_list(data, "continuity_claims", result)

    require_fields(
        candidate,
        "candidate",
        ["batch_id", "candidate_id", "position", "selection_status"],
        result,
    )
    axes = required_mapping(candidate, "difference_axes", result)
    require_fields(
        axes,
        "candidate.difference_axes",
        ["inciting_incident", "character_goal", "conflict_mechanism", "fage_payoff"],
        result,
    )
    context = required_mapping(candidate, "feedback_context", result)
    validate_feedback_context(context, result, feedback_rows)
    scope = required_mapping(candidate, "research_scope", result)
    require_fields(scope, "candidate.research_scope", ["mode", "focus_label", "basis"], result)
    scope_mode = clean(scope.get("mode"))
    focus_label = clean(scope.get("focus_label"))
    if scope_mode not in RESEARCH_SCOPE_MODES:
        result.failures.append("candidate.research_scope.mode is invalid")
    elif scope_mode == "broad_pool" and focus_label != "无":
        result.failures.append("broad_pool research scope must use focus_label 无")
    elif scope_mode == "category_focus" and focus_label == "无":
        result.failures.append("category_focus research scope requires a concrete focus_label")
    if candidate.get("selection_status") not in {"awaiting_selection", "selected"}:
        result.failures.append("candidate.selection_status must be awaiting_selection or selected")

    require_fields(workflow, "workflow", ["stage", "revision_id"], result)
    stage = clean(workflow.get("stage"))
    if stage not in {"candidate", "selected_draft", "refined", "copy_confirmed"}:
        result.failures.append("workflow.stage is invalid")
    if stage in {"selected_draft", "refined", "copy_confirmed"}:
        if candidate.get("selection_status") != "selected":
            result.failures.append("selected/refined stage requires an explicitly selected candidate")
        if clean(workflow.get("selected_candidate_id")) != clean(candidate.get("candidate_id")):
            result.failures.append("selected/refined stage candidate id must match the selected candidate")
    validate_creative_adaptation(
        data.get("creative_adaptation"),
        sources,
        result,
        stage in {"selected_draft", "refined", "copy_confirmed"},
    )
    confirmation = required_mapping(workflow, "copy_confirmation", result)
    confirmed = confirmation.get("confirmed")
    revision_id = clean(workflow.get("revision_id"))
    if confirmed is not False and confirmed is not True:
        result.failures.append("workflow.copy_confirmation.confirmed must be boolean")
    if stage == "copy_confirmed":
        if confirmed is not True:
            result.failures.append("copy_confirmed stage requires explicit confirmation")
        require_fields(
            confirmation,
            "workflow.copy_confirmation",
            ["confirmed_revision_id", "confirmed_at", "user_quote", "content_sha256"],
            result,
        )
        if clean(confirmation.get("confirmed_revision_id")) != revision_id:
            result.failures.append("confirmation revision must match current revision")
    elif confirmed or any(
        clean(confirmation.get(key))
        for key in ["confirmed_revision_id", "confirmed_at", "user_quote", "content_sha256"]
    ):
        result.failures.append("unconfirmed stages must keep confirmation fields empty")

    require_fields(
        meta,
        "meta",
        [
            "account_name",
            "generation_date",
            "platform",
            "estimated_duration",
            "scene",
            "format",
            "generation_mode",
            "topic_id",
            "filename_topic",
            "version",
        ],
        result,
    )
    if "抖音" not in clean(meta.get("platform")) or "千川" in clean(meta.get("platform")):
        result.failures.append("meta.platform must be Douyin organic content")
    if len(clean(meta.get("filename_topic"))) > 16:
        result.failures.append("meta.filename_topic must contain at most 16 characters")
    require_fields(
        data,
        "root",
        ["title", "cover_title", "content_positioning", "core_viewpoint", "research_summary"],
        result,
    )
    require_fields(
        signature,
        "content_signature",
        ["category", "premise", "conflict", "hook_mechanism", "plot_device", "ending_type", "key_line"],
        result,
    )
    diagnostic_fields = [
        "format_fit",
        "audience_resonance",
        "content_value",
        "cognitive_gap",
        "hook_topic",
        "hook_gap",
        "hook_credibility",
        "hook_payoff",
    ]
    require_fields(diagnostics, "creative_diagnostics", diagnostic_fields, result)
    for key in diagnostic_fields:
        if clean(diagnostics.get(key)) in VAGUE_VALUES:
            result.failures.append(f"creative_diagnostics.{key} is too vague")

    story_fields = [
        "one_sentence_story",
        "structure_mode",
        "fage_want",
        "counterparty_want",
        "why_now",
        "primary_comedy_engine",
        "core_choice",
        "choice_cost",
        "core_meaning",
        "plain_conclusion",
        "ending_change",
        "extra_beat_reason",
        "expected_effect",
    ]
    if craft_v3:
        story_fields.append("narrative_pattern")
    require_fields(story, "story_blueprint", story_fields, result)
    if normalized(story.get("fage_want")) == normalized(story.get("counterparty_want")):
        result.failures.append("story needs two distinct character wants")
    structure_mode = clean(story.get("structure_mode"))
    expected_count = {"three_part": 3, "four_part": 4, "five_part": 5}.get(structure_mode)
    if expected_count is None:
        result.failures.append("story_blueprint.structure_mode is invalid")
    elif len(segments) != expected_count:
        result.failures.append(f"{structure_mode} requires exactly {expected_count} segments")
    if structure_mode == "three_part":
        if clean(story.get("extra_beat_reason")) != "无" or clean(story.get("expected_effect")) != "无":
            result.failures.append("three_part must mark extra beat fields as 无")
    elif structure_mode in {"four_part", "five_part"}:
        if clean(story.get("extra_beat_reason")) == "无" or clean(story.get("expected_effect")) == "无":
            result.failures.append("extra beats need non-empty reasons and effects")
    if craft_v3:
        narrative_pattern = clean(story.get("narrative_pattern"))
        if narrative_pattern not in NARRATIVE_PATTERNS:
            result.failures.append("story_blueprint.narrative_pattern is invalid")
        require_fields(
            dialogue_design,
            "dialogue_design",
            ["mode", "anchor_word", "payoff_method", "jargon_resolution"],
            result,
        )
        if clean(dialogue_design.get("mode")) not in DIALOGUE_MODES:
            result.failures.append("dialogue_design.mode is invalid")

    evidence_fields = {
        "behavior_id": "authorized_fictional_behaviors",
        "expression_id": "stable_expression",
        "tradeoff_id": "value_tradeoffs",
        "weakness_id": "visible_weaknesses",
        "relationship_id": "comedy_relationships",
    }
    for key, persona_field in evidence_fields.items():
        value = clean(evidence.get(key))
        if not value:
            result.failures.append(f"persona_evidence.{key} is required")
        elif value not in persona_ids(persona, persona_field):
            result.failures.append(f"persona_evidence.{key} is not defined by the persona")
    require_fields(evidence, "persona_evidence", ["visible_action", "action_consequence"], result)
    for key in ["visible_action", "action_consequence"]:
        if clean(evidence.get(key)) in VAGUE_VALUES or len(normalized(evidence.get(key))) < 6:
            result.failures.append(f"persona_evidence.{key} must be concrete")

    require_fields(hook, "primary_hook", ["voiceover", "visual", "screen_text"], result)
    if "backup_hooks" in data:
        result.failures.append("backup_hooks is not allowed")
    for pattern in GENERIC_HOOKS:
        match = pattern.search(clean(hook.get("voiceover")))
        if match:
            result.failures.append(f"generic hook pattern: {match.group(0)}")

    if not cast:
        result.failures.append("cast must contain at least one role")
    if not preparation:
        result.failures.append("preparation must contain at least one item")
    if not notes:
        result.failures.append("shooting_notes must contain at least one item")
    if not 3 <= len(segments) <= 5:
        result.failures.append("segments must contain 3-5 blocks")
    result.segment_count = len(segments)

    stages: list[str] = []
    segment_dialogue: list[str] = []
    story_changes: list[str] = []
    visual_actions: list[str] = []
    for index, item in enumerate(segments, 1):
        if not isinstance(item, dict):
            result.failures.append(f"segments[{index}] must be an object")
            continue
        require_fields(
            item,
            f"segments[{index}]",
            ["time", "stage", "speaker", "dialogue", "visual_action", "story_change", "humor_function", "camera", "screen_audio"],
            result,
        )
        stages.append(clean(item.get("stage")))
        segment_dialogue.append(clean(item.get("dialogue")))
        visual_actions.append(clean(item.get("visual_action")))
        change = normalized(item.get("story_change"))
        if clean(item.get("story_change")) in VAGUE_VALUES:
            result.failures.append(f"segments[{index}].story_change is too vague")
        if change:
            story_changes.append(change)
    if stages:
        if stages[0] != "hook":
            result.failures.append("first segment stage must be hook")
        if stages[-1] != "ending":
            result.failures.append("last segment stage must be ending")
        if not set(stages[1:-1]).intersection(
            {"dialogue", "conflict", "development", "attempt", "turn"}
        ):
            result.failures.append("segments need a valid middle development stage")
    if len(story_changes) != len(set(story_changes)):
        result.failures.append("every segment needs a distinct story_change")

    labelled: list[str] = []
    lines: list[tuple[str, str]] = []
    for index, item in enumerate(dialogue, 1):
        if not isinstance(item, dict):
            result.failures.append(f"full_dialogue[{index}] must be an object")
            continue
        speaker = clean(item.get("speaker"))
        line = clean(item.get("line"))
        if not speaker or not line:
            result.failures.append(f"full_dialogue[{index}] requires speaker and line")
            continue
        if any(token in line for token in PLACEHOLDERS):
            result.failures.append(f"full_dialogue[{index}] contains a placeholder")
        labelled.append(f"{speaker}：{line}")
        lines.append((speaker, line))
    if normalized("".join(segment_dialogue)) != normalized("".join(labelled)):
        result.failures.append("full_dialogue differs from concatenated segment dialogue")

    spoken = "".join(line for _, line in lines)
    result.spoken_chars = len(normalized(spoken))
    if result.spoken_chars < 90:
        result.failures.append(f"about {result.spoken_chars} spoken characters; minimum is 90")
    elif result.spoken_chars < 110:
        result.warnings.append(f"about {result.spoken_chars} spoken characters; below the default 110")
    if result.spoken_chars > 150:
        result.warnings.append(f"about {result.spoken_chars} spoken characters; above the default 150")
    if result.spoken_chars > 200:
        result.failures.append(f"about {result.spoken_chars} spoken characters; maximum is 200")

    if craft_v3:
        if not 6 <= len(lines) <= 10:
            result.failures.append("schema v3 dialogue must contain 6-10 turns")
        for index, (_, line) in enumerate(lines, 1):
            if len(normalized(line)) > 32:
                result.failures.append(
                    f"full_dialogue[{index}] exceeds 32 effective characters"
                )
        for index in range(len(lines) - 2):
            if lines[index][0] == lines[index + 1][0] == lines[index + 2][0]:
                result.failures.append("one speaker cannot take three consecutive dialogue turns")
                break
        v3_fage_lines = [line for speaker, line in lines if "发哥" in speaker]
        short_fage_lines = [
            line for line in v3_fage_lines if 5 <= len(normalized(line)) <= 14
        ]
        if v3_fage_lines and len(short_fage_lines) * 2 < len(v3_fage_lines):
            result.failures.append("most 发哥 lines must contain 5-14 effective characters")
        for index, (_, line) in enumerate(lines):
            for term in EMPTY_JARGON_TERMS:
                if term not in line:
                    continue
                next_line = lines[index + 1][1] if index + 1 < len(lines) else ""
                if not any(token in next_line for token in CONCRETE_REPLY_TOKENS):
                    result.failures.append(
                        f"empty jargon must be grounded by the next line: {term}"
                    )

    # Explicit feedback can tighten forward-looking dialogue gates without
    # rewriting already evaluated historical candidates.
    avoid_blob = "".join(clean(item) for item in context.get("avoid", []))
    if "前一句明确点名工资预支单" in avoid_blob:
        for index, (_, line) in enumerate(lines):
            if not any(token in line for token in ("工资预支单", "预支单", "借款单")):
                continue
            later = "".join(text for _, text in lines[index + 1 :])
            leave_reveal = re.search(r"(批|签).{0,6}(一天|半天|两天|请)?假", later)
            separate_document = any(
                marker in later for marker in ("另拿", "另写", "换一张", "请假单", "请假申请")
            )
            if leave_reveal and not separate_document:
                result.failures.append(
                    "prop logic conflict: a money form becomes leave approval without a separate document"
                )
                break
    if "第三方等需要观众停顿解释" in avoid_blob:
        concrete_roles = (
            "律师",
            "法院",
            "银行",
            "医生",
            "警方",
            "市场监管",
            "平台客服",
            "评估师",
            "调解员",
        )
        for term in ("第三方", "相关部门", "专业机构"):
            if term in spoken and not any(role in spoken for role in concrete_roles):
                result.failures.append(
                    f"unexplained role jargon in public dialogue: {term}"
                )

    packet = semantic_review.build_public_review_packet(data)
    public_text = semantic_review.canonical_json(packet)
    topic_public_text = public_text
    validate_topic_strategy(topic, topic_public_text, sources, context, result)
    for phrase in HARD_PHRASES:
        if phrase in public_text:
            add_unique(result.failures, f"prohibited AI/marketing phrase: {phrase}")
    for phrase in COMMERCIAL_PHRASES:
        if phrase in public_text:
            add_unique(result.failures, f"commerce wording is out of scope: {phrase}")
    for phrase in TECHNICAL_TERMS:
        if phrase in public_text:
            add_unique(result.warnings, f"technical term needs plain-language handling: {phrase}")
    if "东来乐" in public_text:
        result.failures.append("brand exposure is not allowed in public copy")
    fage_claim_text = "\n".join(
        [
            clean(data.get("title")),
            clean(data.get("cover_title")),
            *[line for speaker, line in lines if "发哥" in speaker],
        ]
    )
    for pattern in BIOGRAPHY_PATTERNS:
        match = pattern.search(fage_claim_text)
        if match:
            add_unique(result.failures, f"unconfirmed biography claim: {match.group(0)}")

    conclusion_text = clean(story.get("plain_conclusion"))
    if segment_dialogue and normalized(conclusion_text) not in normalized(segment_dialogue[-1]):
        result.failures.append("plain_conclusion must appear in the ending segment")
    for phrase in UNIVERSAL_CONCLUSIONS:
        if phrase in conclusion_text:
            add_unique(result.failures, f"universal conclusion is not event-specific: {phrase}")

    visual_blob = "".join(visual_actions)
    visible_action = clean(evidence.get("visible_action"))
    action_hits = [token for token in ACTION_TOKENS if token in visible_action]
    if not action_hits:
        result.failures.append("persona visible_action lacks a testable action")
    elif not any(token in visual_blob for token in action_hits):
        result.failures.append("persona visible_action is not shown in segment visual_action")
    payoff_blob = (
        clean(story.get("core_choice"))
        + clean(axes.get("fage_payoff"))
        + clean(segment_dialogue[-1] if segment_dialogue else "")
    )
    if action_hits and content_overlap(visible_action, payoff_blob) < 0.45:
        result.failures.append("persona visible_action does not drive the public story payoff")
    if normalized(evidence.get("action_consequence")) != normalized(story.get("ending_change")):
        result.failures.append(
            "persona action_consequence must match the story ending_change"
        )
    fage_lines = [line for speaker, line in lines if "发哥" in speaker]
    other_lines = [line for speaker, line in lines if "发哥" not in speaker]
    if len(fage_lines) < 2 or len(other_lines) < 2:
        result.failures.append("dialogue needs at least two lines from 发哥 and the counterparty")
    if other_lines and all(
        len(normalized(line)) <= 18 and (line.endswith(("？", "?")) or any(q in line for q in ["为什么", "真的吗", "然后呢", "你怎么看"]))
        for line in other_lines
    ):
        result.failures.append("counterparty only prompts a lecture; give them a goal or action")
    if not any("发哥" in clean(item.get("speaker")) and any(token in clean(item.get("visual_action")) for token in ACTION_TOKENS) for item in segments if isinstance(item, dict)):
        result.failures.append("发哥 only talks; a visible action or decision is required")
    if craft_v3:
        mode = clean(dialogue_design.get("mode"))
        anchor_word = clean(dialogue_design.get("anchor_word"))
        if mode == "rapid_exchange":
            if len(lines) < 8 or any(len(normalized(line)) > 24 for _, line in lines):
                result.failures.append(
                    "rapid_exchange needs 8-10 turns with every line at most 24 characters"
                )
        elif mode == "deadpan_setback":
            if not any(mark in line for line in fage_lines for mark in ("……", "…", "...")):
                result.failures.append("deadpan_setback needs a visible pause in 发哥 dialogue")
        elif mode == "keyword_rebound":
            speakers_using_anchor = {
                "fage" if "发哥" in speaker else "other"
                for speaker, line in lines
                if anchor_word and anchor_word != "无" and anchor_word in line
            }
            if speakers_using_anchor != {"fage", "other"}:
                result.failures.append(
                    "keyword_rebound anchor must appear in lines from both sides"
                )
        elif mode == "prop_reveal":
            reveal_blob = visual_blob + "".join(clean(item.get("story_change")) for item in segments if isinstance(item, dict))
            if not any(token in reveal_blob for token in ("露出", "翻开", "标题", "名单", "屏幕", "申请", "单子")):
                result.failures.append("prop_reveal needs a visible object-information reveal")

    approved_values = persona_field_value(persona, "approved_continuity_claims") or []
    approved = {clean(item) for item in approved_values if clean(item)}
    for claim in claims:
        if clean(claim) not in approved:
            result.failures.append(f"unapproved continuity claim: {clean(claim)}")

    if not sources:
        result.failures.append("research_sources must contain at least one source")
    result.source_count = len(sources)
    for index, source in enumerate(sources, 1):
        if not isinstance(source, dict):
            result.failures.append(f"research_sources[{index}] must be an object")
            continue
        require_fields(
            source,
            f"research_sources[{index}]",
            ["source_kind", "title", "locator", "source_date", "retrieved_at", "metric_note", "borrowed_mechanism"],
            result,
        )
        if source.get("source_kind") not in {"local_history", "user_provided", "web"}:
            result.failures.append(f"research_sources[{index}].source_kind is invalid")
        if not isinstance(source.get("metrics_provided"), bool):
            result.failures.append(f"research_sources[{index}].metrics_provided must be boolean")
        if source.get("metrics_provided") and source.get("source_kind") != "user_provided":
            result.failures.append("publication metrics are allowed only from user-provided sources")

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--persona", required=True, type=Path)
    parser.add_argument("--feedback-ledger", type=Path)
    parser.add_argument("--require-schema-version", type=int, choices=(2, 3, 4))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_jsonl(args.feedback_ledger) if args.feedback_ledger else None
    result = validate_script(
        read_json(args.input),
        read_json(args.persona),
        rows,
        required_schema_version=args.require_schema_version,
    )
    print(
        f"Checked {result.segment_count} segments, {result.source_count} sources, "
        f"about {result.spoken_chars} spoken characters."
    )
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for failure in result.failures:
        print(f"FAIL: {failure}")
    print("RESULT: PASS" if result.ok else "RESULT: FAIL")
    return 0 if result.ok else 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
