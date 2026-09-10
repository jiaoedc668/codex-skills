from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


POOL_KEYS = {
    "schema_version",
    "pool_id",
    "requested_candidate_count",
    "prospects",
    "pairwise_decisions",
    "selected_topic_ids",
}
PROSPECT_KEYS = {
    "topic_id",
    "title",
    "topic_kind",
    "priority_category",
    "research_evidence",
    "production_case",
    "veto_reasons",
}
PRODUCTION_CASE_KEYS = {
    "audience_stake",
    "concrete_event",
    "concrete_anchor",
    "strongest_counterargument",
    "fage_choice",
    "fage_cost",
    "ending_consequence",
    "audience_response_space",
}
PAIRWISE_KEYS = {
    "left_topic_id",
    "right_topic_id",
    "preferred_topic_id",
    "evidence_reason",
    "production_reason",
}
SOURCE_KEYS = {"title", "url", "source_date", "retrieved_at", "supports", "limits"}
FORBIDDEN_RANK_KEYS = {"score", "weights", "rank", "shootability_score"}
SOURCE_LIST_KEYS = {
    "sources",
    "fact_sources",
    "heat_signals",
    "recurrence_sources",
    "high_interaction_sources",
}
VIRAL_SAMPLE_KEYS = {
    "platform",
    "title",
    "url",
    "retrieved_at",
    "metric_scope",
    "like_count",
    "content_access",
    "content_excerpt",
    "observed_mechanism",
    "adaptation_boundary",
}
READABLE_CONTENT_ACCESS = {"full_text", "captions", "transcript"}


def _clean(value: Any) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _require_list(value: Any, field: str, allow_empty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (not allow_empty and not value):
        qualifier = "a list" if allow_empty else "a non-empty list"
        raise ValueError(f"{field} must be {qualifier}")
    return value


def _require_text(mapping: Mapping[str, Any], key: str, field: str) -> str:
    value = _clean(mapping.get(key))
    if not value:
        raise ValueError(f"{field} must be non-empty text")
    return value


def _parse_date(value: Any, field: str) -> date:
    text = _clean(value)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc


def _forbidden_rank_paths(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text in FORBIDDEN_RANK_KEYS or key_text.endswith("_score"):
                found.append(child_path)
            found.extend(_forbidden_rank_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_rank_paths(child, f"{path}[{index}]"))
    return found


def validate_source(source: Any) -> dict[str, Any]:
    value = _require_mapping(source, "source")
    missing = sorted(SOURCE_KEYS - set(value))
    if missing:
        raise ValueError(f"source missing required fields: {missing}")
    for key in ("title", "supports", "limits"):
        _require_text(value, key, f"source.{key}")
    url = _require_text(value, "url", "source.url")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source.url must be an HTTP(S) URL")
    _parse_date(value.get("source_date"), "source.source_date")
    _parse_date(value.get("retrieved_at"), "source.retrieved_at")
    return deepcopy(dict(value))


def validate_viral_expression_samples(value: Any) -> list[dict[str, Any]]:
    rows = _require_list(value, "viral_expression_samples", allow_empty=True)
    validated: list[dict[str, Any]] = []
    urls: set[str] = set()
    for index, raw in enumerate(rows):
        sample = _require_mapping(raw, f"viral_expression_samples[{index}]")
        if set(sample) != VIRAL_SAMPLE_KEYS:
            missing = sorted(VIRAL_SAMPLE_KEYS - set(sample))
            unexpected = sorted(set(sample) - VIRAL_SAMPLE_KEYS)
            raise ValueError(
                f"viral_expression_samples[{index}] keys differ; "
                f"missing={missing}; unexpected={unexpected}"
            )
        for key in (
            "platform",
            "title",
            "content_excerpt",
            "observed_mechanism",
            "adaptation_boundary",
        ):
            _require_text(sample, key, f"viral_expression_samples[{index}].{key}")
        url = _require_text(sample, "url", f"viral_expression_samples[{index}].url")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"viral_expression_samples[{index}].url must be HTTP(S)")
        if url in urls:
            raise ValueError("viral_expression_samples URLs must be unique originals")
        urls.add(url)
        _parse_date(
            sample.get("retrieved_at"),
            f"viral_expression_samples[{index}].retrieved_at",
        )
        if sample.get("metric_scope") != "single_video":
            raise ValueError(
                f"viral_expression_samples[{index}].metric_scope must be single_video"
            )
        likes = sample.get("like_count")
        if isinstance(likes, bool) or not isinstance(likes, int) or likes < 100000:
            raise ValueError(
                f"viral_expression_samples[{index}].like_count must be at least 100000"
            )
        if sample.get("content_access") not in READABLE_CONTENT_ACCESS:
            raise ValueError(
                f"viral_expression_samples[{index}] requires readable full_text, captions, or transcript"
            )
        validated.append(deepcopy(dict(sample)))
    return validated


def _validate_source_list(
    evidence: Mapping[str, Any], key: str, allow_empty: bool = False
) -> list[dict[str, Any]]:
    rows = _require_list(evidence.get(key), f"research_evidence.{key}", allow_empty)
    validated: list[dict[str, Any]] = []
    for index, source in enumerate(rows):
        try:
            validated.append(validate_source(source))
        except ValueError as exc:
            raise ValueError(f"research_evidence.{key}[{index}]: {exc}") from exc
    return validated


def validate_research_evidence(kind: str, evidence: Any, *, creative_first: bool = False) -> dict[str, Any]:
    value = _require_mapping(evidence, "research_evidence")
    if kind not in {"current_issue", "evergreen"}:
        raise ValueError("topic_kind must be current_issue or evergreen")

    if creative_first:
        required = value.get("research_required", False)
        if not isinstance(required, bool):
            raise ValueError("research_evidence.research_required must be a boolean")
        for key in SOURCE_LIST_KEYS & set(value):
            _validate_source_list(value, key, allow_empty=True)
        if required and not (value.get("sources") or value.get("fact_sources")):
            raise ValueError("required research needs non-empty sources or fact_sources")
        # Fiction needs no platform proof; all supplied sources remain validated.
        if kind == "evergreen":
            return deepcopy(dict(value))

    for key in SOURCE_LIST_KEYS & set(value):
        if creative_first:
            continue
        if key in {"heat_signals", "recurrence_sources", "high_interaction_sources"}:
            continue
        _validate_source_list(value, key, allow_empty=False)

    if kind == "current_issue":
        if not isinstance(value.get("heat_signals"), list) or not value.get(
            "heat_signals"
        ):
            raise ValueError("current issue requires at least one recent heat signal")
        signals = _validate_source_list(value, "heat_signals")
        for signal in signals:
            source_date = _parse_date(signal["source_date"], "heat signal source_date")
            retrieved_at = _parse_date(signal["retrieved_at"], "heat signal retrieved_at")
            age = (retrieved_at - source_date).days
            if age < 0 or age > 7:
                raise ValueError(
                    "current issue recent heat signal must be within seven days of retrieval"
                )
    else:
        recurrence = value.get("recurrence_sources")
        interaction = value.get("high_interaction_sources")
        if not isinstance(recurrence, list) or len(recurrence) < 2:
            raise ValueError("evergreen evidence requires at least two recurrence sources")
        if not isinstance(interaction, list) or not interaction:
            raise ValueError("evergreen evidence requires a high-interaction source")
        recurrence_sources = _validate_source_list(value, "recurrence_sources")
        dates = sorted(
            _parse_date(source["source_date"], "recurrence source_date")
            for source in recurrence_sources
        )
        if (dates[-1] - dates[0]).days < 90:
            raise ValueError("evergreen recurrence sources must span at least ninety days")
        interaction_sources = _validate_source_list(value, "high_interaction_sources")
        for source in interaction_sources:
            if not _clean(source.get("visible_interaction")):
                raise ValueError(
                    "evergreen high-interaction source requires visible_interaction"
                )
    return deepcopy(dict(value))


def _validate_production_case(value: Any, topic_id: str) -> None:
    production_case = _require_mapping(value, f"prospect {topic_id}.production_case")
    missing = sorted(PRODUCTION_CASE_KEYS - set(production_case))
    if missing:
        raise ValueError(f"prospect {topic_id}.production_case missing fields: {missing}")
    for key in PRODUCTION_CASE_KEYS:
        _require_text(
            production_case,
            key,
            f"prospect {topic_id}.production_case.{key}",
        )


def _validate_prospects(prospects: list[Any], *, creative_first: bool = False) -> tuple[list[dict[str, Any]], set[str]]:
    validated: list[dict[str, Any]] = []
    topic_ids: set[str] = set()
    for index, raw_prospect in enumerate(prospects):
        prospect = _require_mapping(raw_prospect, f"prospects[{index}]")
        missing = sorted(PROSPECT_KEYS - set(prospect))
        if missing:
            raise ValueError(f"prospects[{index}] missing fields: {missing}")
        topic_id = _require_text(prospect, "topic_id", f"prospects[{index}].topic_id")
        if topic_id in topic_ids:
            raise ValueError("prospect topic_id values must be unique and non-empty")
        topic_ids.add(topic_id)
        _require_text(prospect, "title", f"prospect {topic_id}.title")
        kind = _require_text(prospect, "topic_kind", f"prospect {topic_id}.topic_kind")
        _require_text(
            prospect,
            "priority_category",
            f"prospect {topic_id}.priority_category",
        )
        validate_research_evidence(kind, prospect.get("research_evidence"), creative_first=creative_first)
        _validate_production_case(prospect.get("production_case"), topic_id)
        vetoes = _require_list(
            prospect.get("veto_reasons"),
            f"prospect {topic_id}.veto_reasons",
            allow_empty=True,
        )
        if any(not _clean(item) for item in vetoes):
            raise ValueError(
                f"prospect {topic_id}.veto_reasons must contain only non-empty text"
            )
        validated.append(deepcopy(dict(prospect)))
    return validated, topic_ids


def _validate_pairwise_decisions(
    raw_decisions: Any,
    eligible_ids: set[str],
    selected_ids: set[str],
) -> list[dict[str, Any]]:
    decisions = _require_list(raw_decisions, "pairwise_decisions", allow_empty=True)
    seen: set[tuple[str, str]] = set()
    validated: list[dict[str, Any]] = []
    for index, raw_decision in enumerate(decisions):
        decision = _require_mapping(raw_decision, f"pairwise_decisions[{index}]")
        missing = sorted(PAIRWISE_KEYS - set(decision))
        if missing:
            raise ValueError(f"pairwise_decisions[{index}] missing fields: {missing}")
        left = _require_text(
            decision, "left_topic_id", f"pairwise_decisions[{index}].left_topic_id"
        )
        right = _require_text(
            decision, "right_topic_id", f"pairwise_decisions[{index}].right_topic_id"
        )
        preferred = _require_text(
            decision,
            "preferred_topic_id",
            f"pairwise_decisions[{index}].preferred_topic_id",
        )
        _require_text(
            decision,
            "evidence_reason",
            f"pairwise_decisions[{index}].evidence_reason",
        )
        _require_text(
            decision,
            "production_reason",
            f"pairwise_decisions[{index}].production_reason",
        )
        if left == right:
            raise ValueError("pairwise decision must compare two different topics")
        if left not in eligible_ids or right not in eligible_ids:
            raise ValueError("pairwise decision may compare only non-vetoed topics")
        if preferred not in {left, right}:
            raise ValueError("preferred_topic_id must be one of the compared topics")
        pair = tuple(sorted((left, right)))
        if pair in seen:
            raise ValueError(f"duplicate pairwise decision for {pair[0]} versus {pair[1]}")
        seen.add(pair)
        selected_in_pair = {left, right} & selected_ids
        if len(selected_in_pair) == 1 and preferred not in selected_in_pair:
            raise ValueError(
                f"selected topic must be preferred over unselected topic in {left} versus {right}"
            )
        validated.append(deepcopy(dict(decision)))

    required_pairs = {
        tuple(sorted((selected, other)))
        for selected in selected_ids
        for other in eligible_ids
        if selected != other
    }
    missing_pairs = sorted(required_pairs - seen)
    if missing_pairs:
        left, right = missing_pairs[0]
        raise ValueError(f"missing pairwise decision for {left} versus {right}")
    return validated


def select_topics(pool: Any, *, _creative_first: bool = False) -> dict[str, Any]:
    value = _require_mapping(pool, "topic pool")
    if value.get("schema_version") == 6:
        expected_v6_keys = POOL_KEYS | {"viral_expression_samples"}
        if set(value) != expected_v6_keys:
            missing = sorted(expected_v6_keys - set(value))
            unexpected = sorted(set(value) - expected_v6_keys)
            raise ValueError(
                f"topic pool keys must match v6; missing={missing}; unexpected={unexpected}"
            )
        viral_samples = validate_viral_expression_samples(
            value.get("viral_expression_samples")
        )
        adapted = deepcopy(dict(value))
        adapted.pop("viral_expression_samples")
        adapted["schema_version"] = 5
        prospects = adapted.get("prospects")
        if not isinstance(prospects, list):
            raise ValueError("prospects must be an array")
        for row in prospects:
            case = row.get("production_case") if isinstance(row, Mapping) else None
            if not isinstance(case, dict) or "fage_cost" in case:
                raise ValueError("v6 production_case uses stakeholder_cost, not fage_cost")
            cost = case.pop("stakeholder_cost", None)
            if not isinstance(cost, str) or not cost.strip():
                raise ValueError("v6 stakeholder_cost must be non-empty")
            case["fage_cost"] = cost
        result = select_topics(adapted, _creative_first=True)
        for row in result["selected"] + result["vetoed"]:
            case = row["production_case"]
            case["stakeholder_cost"] = case.pop("fage_cost")
        result["viral_expression_samples"] = viral_samples
        return result
    forbidden = sorted(_forbidden_rank_paths(value))
    if forbidden:
        raise ValueError(
            "score and rank fields are forbidden: " + ", ".join(forbidden)
        )
    actual_keys = set(value)
    if actual_keys != POOL_KEYS:
        missing = sorted(POOL_KEYS - actual_keys)
        unexpected = sorted(actual_keys - POOL_KEYS)
        raise ValueError(
            f"topic pool keys must match v5; missing={missing}; unexpected={unexpected}"
        )
    if value.get("schema_version") != 5:
        raise ValueError("topic pool schema_version must be 5")
    pool_id = _require_text(value, "pool_id", "pool_id")
    requested = value.get("requested_candidate_count")
    if isinstance(requested, bool) or not isinstance(requested, int) or requested < 1:
        raise ValueError("requested_candidate_count must be a positive integer")

    prospects, topic_ids = _validate_prospects(
        _require_list(value.get("prospects"), "prospects"), creative_first=_creative_first
    )
    eligible = [item for item in prospects if not item["veto_reasons"]]
    eligible_ids = {item["topic_id"] for item in eligible}
    if len(eligible) < requested:
        raise ValueError(
            "topic pool must contain at least requested_candidate_count non-vetoed topics"
        )

    selected_values = _require_list(value.get("selected_topic_ids"), "selected_topic_ids")
    selected = [_clean(item) for item in selected_values]
    if any(not item for item in selected) or len(set(selected)) != len(selected):
        raise ValueError("selected_topic_ids must be unique and non-empty")
    if len(selected) != requested:
        raise ValueError("selected_topic_ids must contain requested_candidate_count topics")
    unknown = [item for item in selected if item not in topic_ids]
    if unknown:
        raise ValueError(f"selected_topic_ids contain unknown topics: {unknown}")
    vetoed_selected = [item for item in selected if item not in eligible_ids]
    if vetoed_selected:
        raise ValueError(f"selected topics cannot be vetoed: {vetoed_selected}")
    selected_ids = set(selected)

    comparisons = _validate_pairwise_decisions(
        value.get("pairwise_decisions"), eligible_ids, selected_ids
    )
    prospect_by_id = {item["topic_id"]: item for item in prospects}
    return {
        "pool_id": pool_id,
        "selected": [deepcopy(prospect_by_id[topic_id]) for topic_id in selected],
        "vetoed": [deepcopy(item) for item in prospects if item["veto_reasons"]],
        "comparisons": comparisons,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate v5 topic evidence and recorded pairwise decisions."
    )
    parser.add_argument("--input", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with args.input.open("r", encoding="utf-8-sig") as handle:
            pool = json.load(handle)
        result = select_topics(pool)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
