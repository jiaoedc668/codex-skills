#!/usr/bin/env python3
"""Rank a researched topic pool with heat as the largest score component."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


EVIDENCE_TIERS = {
    "official_hotlist",
    "archived_hotlist",
    "multiple_dated_reports",
    "single_dated_source",
    "no_current_signal",
}


def integer(value: Any, field: str, minimum: int = 0, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        suffix = f"..{maximum}" if maximum is not None else f" or greater"
        raise ValueError(f"{field} must be {minimum}{suffix}")
    return value


def heat_components(evidence: dict[str, Any]) -> dict[str, int]:
    if not isinstance(evidence, dict):
        raise ValueError("heat_evidence must be an object")
    freshness_days = integer(evidence.get("freshness_days"), "freshness_days")
    hotlist_minutes = integer(evidence.get("hotlist_minutes", 0), "hotlist_minutes")
    distinct_domains = integer(evidence.get("distinct_domains"), "distinct_domains")
    derivative_work_count = integer(
        evidence.get("derivative_work_count"), "derivative_work_count"
    )
    tier = str(evidence.get("evidence_tier", "")).strip()
    if tier not in EVIDENCE_TIERS:
        raise ValueError("evidence_tier is invalid")

    freshness = 25 if freshness_days <= 3 else 18 if freshness_days <= 7 else 10 if freshness_days <= 30 else 0
    if tier == "official_hotlist":
        platform = 35
    elif tier == "archived_hotlist":
        platform = 10 if hotlist_minutes <= 15 else 18 if hotlist_minutes <= 60 else 26 if hotlist_minutes <= 240 else 35
    elif tier == "multiple_dated_reports":
        platform = 15
    elif tier == "single_dated_source":
        platform = 8
    else:
        platform = 0
    spread = 25 if distinct_domains >= 3 else 18 if distinct_domains == 2 else 8 if distinct_domains == 1 else 0
    derivatives = 15 if derivative_work_count >= 2 else 8 if derivative_work_count == 1 else 0
    return {
        "freshness": freshness,
        "platform_signal": platform,
        "cross_platform_spread": spread,
        "derivative_density": derivatives,
    }


def heat_score(evidence: dict[str, Any]) -> int:
    return sum(heat_components(evidence).values())


def selection_score(
    heat: int,
    audience_conflict: int,
    fage_fit: int,
    shootability: int,
) -> float:
    for value, field in [
        (heat, "heat_score"),
        (audience_conflict, "audience_conflict_score"),
        (fage_fit, "fage_fit_score"),
        (shootability, "shootability_score"),
    ]:
        integer(value, field, 0, 100)
    return round(heat * 0.45 + audience_conflict * 0.20 + fage_fit * 0.20 + shootability * 0.15, 2)


def rank_pool(data: dict[str, Any]) -> dict[str, Any]:
    pool_id = str(data.get("pool_id", "")).strip()
    prospects = data.get("prospects")
    if not pool_id or not isinstance(prospects, list) or len(prospects) < 9:
        raise ValueError("pool_id and at least nine prospects are required")
    ids = [str(item.get("topic_id", "")).strip() for item in prospects if isinstance(item, dict)]
    if len(ids) != len(prospects) or any(not item for item in ids) or len(set(ids)) != len(ids):
        raise ValueError("prospect topic_id values must be unique and non-empty")

    rows: list[dict[str, Any]] = []
    for prospect in prospects:
        heat = heat_score(prospect.get("heat_evidence"))
        conflict = integer(prospect.get("audience_conflict_score"), "audience_conflict_score", 0, 100)
        fit = integer(prospect.get("fage_fit_score"), "fage_fit_score", 0, 100)
        shoot = integer(prospect.get("shootability_score"), "shootability_score", 0, 100)
        vetoes = prospect.get("veto_reasons", [])
        if not isinstance(vetoes, list) or any(not str(item).strip() for item in vetoes):
            raise ValueError("veto_reasons must be a list of non-empty strings")
        rows.append(
            {
                "topic_id": str(prospect["topic_id"]),
                "title": str(prospect.get("title", "")),
                "heat_evidence": prospect["heat_evidence"],
                "heat_components": heat_components(prospect["heat_evidence"]),
                "heat_score": heat,
                "audience_conflict_score": conflict,
                "fage_fit_score": fit,
                "shootability_score": shoot,
                "selection_score": selection_score(heat, conflict, fit, shoot),
                "veto_reasons": [str(item).strip() for item in vetoes],
            }
        )

    for heat_rank, row in enumerate(
        sorted(rows, key=lambda item: (-item["heat_score"], item["topic_id"])), 1
    ):
        row["heat_rank"] = heat_rank
    eligible = [row for row in rows if not row["veto_reasons"]]
    eligible.sort(key=lambda item: (-item["selection_score"], -item["heat_score"], item["topic_id"]))
    for final_rank, row in enumerate(eligible, 1):
        row["final_rank"] = final_rank
    vetoed = [row for row in rows if row["veto_reasons"]]
    vetoed.sort(key=lambda item: (item["heat_rank"], item["topic_id"]))
    return {
        "pool_id": pool_id,
        "pool_size": len(rows),
        "eligible_count": len(eligible),
        "weights": {
            "heat": 0.45,
            "audience_conflict": 0.20,
            "fage_fit": 0.20,
            "shootability": 0.15,
        },
        "ranked": eligible,
        "vetoed": vetoed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        output = rank_pool(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 2
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
