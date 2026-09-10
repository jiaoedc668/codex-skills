from __future__ import annotations

import hashlib
import json
import re
from itertools import combinations
from typing import Any


REQUIRED_BRIEF_FIELDS = ("product_name", "category", "use", "selling_points", "target_customer", "format")
FORMATS = {"monologue", "story", "both"}
PUBLIC_CANDIDATE_FIELDS = ("format", "theme", "creative_note", "full_copy", "estimated_seconds")
POLITICAL_TERMS = ("总统", "选举", "政党", "政治运动", "国家领导人")


class ContractError(ValueError):
    pass


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return True


def validate_brief(brief: dict[str, Any]) -> list[str]:
    missing = [field for field in REQUIRED_BRIEF_FIELDS if not _present(brief.get(field))]
    fmt = brief.get("format")
    if _present(fmt) and fmt not in FORMATS:
        raise ContractError("format 必须是 monologue、story 或 both")
    return missing


def product_facts_sha256(brief: dict[str, Any]) -> str:
    facts = {
        "product_name": brief.get("product_name"),
        "category": brief.get("category"),
        "use": brief.get("use"),
        "selling_points": brief.get("selling_points"),
        "model": brief.get("model"),
        "must_include": brief.get("must_include", []),
        "banned_expressions": brief.get("banned_expressions", []),
    }
    raw = json.dumps(facts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalized_chars(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", value).lower()


def _char_ngrams(value: str, width: int = 3) -> set[str]:
    normalized = _normalized_chars(value)
    if len(normalized) < width:
        return {normalized} if normalized else set()
    return {normalized[index : index + width] for index in range(len(normalized) - width + 1)}


def _similarity(left: str, right: str) -> float:
    left_grams = _char_ngrams(left)
    right_grams = _char_ngrams(right)
    if not left_grams and not right_grams:
        return 1.0
    return len(left_grams & right_grams) / max(1, len(left_grams | right_grams))


def _validate_research(packet: dict[str, Any]) -> None:
    items = packet.get("research")
    if not isinstance(items, list) or len(items) < 3:
        raise ContractError("创作前研究必须至少 3 条")
    required = ("platform", "url", "published_at", "comparability_note", "performance_evidence", "learned")
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ContractError(f"research[{index}] 必须是对象")
        missing = [key for key in required if not _present(item.get(key))]
        if missing:
            raise ContractError(f"research[{index}] 缺少: {', '.join(missing)}")
    if not any(str(item.get("platform", "")).lower() == "douyin" for item in items):
        if not _present(packet.get("research_fallback_reason")):
            raise ContractError("没有抖音研究时必须记录替代来源原因")


def _validate_count_and_formats(fmt: str, candidates: list[dict[str, Any]]) -> None:
    expected_total = 6 if fmt == "both" else 3
    if len(candidates) != expected_total:
        raise ContractError(f"{fmt} 必须正好返回 {expected_total} 个候选")
    counts = {"monologue": 0, "story": 0}
    for item in candidates:
        item_format = item.get("format")
        if item_format not in counts:
            raise ContractError("候选 format 必须是 monologue 或 story")
        counts[item_format] += 1
    if fmt == "both" and counts != {"monologue": 3, "story": 3}:
        raise ContractError("both 必须包含 3 个 monologue 和 3 个 story")
    if fmt != "both" and counts[fmt] != 3:
        raise ContractError(f"{fmt} 必须正好包含 3 个同形式候选")


def validate_candidate_packet(packet: dict[str, Any]) -> list[dict[str, Any]]:
    brief = packet.get("brief")
    if not isinstance(brief, dict):
        raise ContractError("brief is required")
    missing = validate_brief(brief)
    if missing:
        raise ContractError("brief 缺少必填项: " + ", ".join(missing))
    if packet.get("product_facts_sha256") != product_facts_sha256(brief):
        raise ContractError("product facts hash 不匹配，产品事实映射可能被篡改")
    _validate_research(packet)

    candidates = packet.get("candidates")
    if not isinstance(candidates, list):
        raise ContractError("candidates must be a list")
    _validate_count_and_formats(brief["format"], candidates)
    supplied_points = set(brief["selling_points"])
    allowed_sources = supplied_points | {
        str(brief.get("product_name", "")),
        str(brief.get("category", "")),
        str(brief.get("use", "")),
        str(brief.get("model", "")),
    }
    banned = [str(item) for item in brief.get("banned_expressions", []) if _present(item)]

    for index, item in enumerate(candidates, 1):
        if not isinstance(item, dict):
            raise ContractError(f"candidate[{index}] must be an object")
        required = ("candidate_id",) + PUBLIC_CANDIDATE_FIELDS + ("main_selling_point", "fact_claims")
        missing_candidate = [key for key in required if not _present(item.get(key))]
        if missing_candidate:
            raise ContractError(f"candidate[{index}] 缺少: {', '.join(missing_candidate)}")
        seconds = item["estimated_seconds"]
        if not isinstance(seconds, (int, float)) or seconds <= 0:
            raise ContractError("预计时长必须是正数")
        if item["format"] == "monologue" and not 25 <= seconds <= 35:
            raise ContractError("monologue 预计时长必须在 25-35 秒")
        if item["format"] == "story" and seconds > 90:
            raise ContractError("story 预计时长不得超过 90 秒")
        used = item.get("used_selling_points")
        if not isinstance(used, list) or not used:
            raise ContractError("每个候选至少使用一个用户卖点")
        if any(point not in supplied_points for point in used):
            raise ContractError("候选使用了输入之外的卖点")
        if item.get("main_selling_point") not in used:
            raise ContractError("主卖点必须来自本候选已使用卖点")
        for claim in item.get("fact_claims", []):
            if not isinstance(claim, dict) or not _present(claim.get("claim")) or claim.get("source_text") not in allowed_sources:
                raise ContractError("产品事实声明必须映射到用户输入的产品事实")
        public_text = " ".join(str(item.get(key, "")) for key in ("theme", "creative_note", "full_copy"))
        if any(term in public_text for term in banned):
            raise ContractError("候选含用户禁用表达")
        if any(term in public_text for term in POLITICAL_TERMS):
            raise ContractError("候选不得使用政治题材")

    ids = [item["candidate_id"] for item in candidates]
    if len(ids) != len(set(ids)):
        raise ContractError("candidate_id 必须唯一")
    for left, right in combinations(candidates, 2):
        same_theme = _normalized_chars(left["theme"]) == _normalized_chars(right["theme"])
        too_similar = _similarity(left["full_copy"], right["full_copy"]) >= 0.72
        if same_theme or too_similar:
            raise ContractError("候选必须实质不同，不能同题换词")
    return candidates


def public_candidates(packet: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = validate_candidate_packet(packet)
    return [{field: item[field] for field in PUBLIC_CANDIDATE_FIELDS} for item in candidates]
