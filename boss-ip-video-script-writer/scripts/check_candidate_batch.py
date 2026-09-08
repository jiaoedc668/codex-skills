#!/usr/bin/env python3
"""Validate exactly three complete candidate scripts as one genuinely different batch."""

from __future__ import annotations

import argparse
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from check_script_quality import read_json, read_jsonl, normalized, validate_script


AXES = ["inciting_incident", "character_goal", "conflict_mechanism", "fage_payoff"]


def ratio(left: Any, right: Any) -> float:
    a, b = normalized(left), normalized(right)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def dialogue_text(data: dict[str, Any]) -> str:
    items = data.get("full_dialogue", [])
    if not isinstance(items, list):
        return ""
    return "".join(str(item.get("line", "")) for item in items if isinstance(item, dict))


def public_axis_targets(data: dict[str, Any]) -> dict[str, str]:
    signature = data.get("content_signature", {})
    story = data.get("story_blueprint", {})
    hook = data.get("primary_hook", {})
    evidence = data.get("persona_evidence", {})
    segments = data.get("segments", [])
    middle = "".join(
        str(item.get("dialogue", ""))
        for item in segments[1:-1]
        if isinstance(item, dict)
    )
    ending_action = "".join(
        str(item.get("visual_action", ""))
        for item in segments[-1:]
        if isinstance(item, dict)
    )
    return {
        "inciting_incident": f"{signature.get('premise', '')}{hook.get('voiceover', '')}{hook.get('visual', '')}",
        "character_goal": f"{story.get('fage_want', '')}{story.get('counterparty_want', '')}",
        "conflict_mechanism": f"{signature.get('conflict', '')}{signature.get('plot_device', '')}{middle}",
        "fage_payoff": f"{evidence.get('visible_action', '')}{evidence.get('action_consequence', '')}{ending_action}",
    }


def axis_is_evidenced(description: Any, target: Any) -> bool:
    desc = normalized(description)
    body = normalized(target)
    if not desc or not body:
        return False
    if desc in body or body in desc:
        return True
    chars = set(desc)
    return len(chars.intersection(set(body))) / max(1, len(chars)) >= 0.45


def validate_batch(
    scripts: list[dict[str, Any]],
    persona: dict[str, Any],
    feedback_rows: list[dict[str, Any]] | None = None,
    required_schema_version: int | None = None,
) -> list[str]:
    failures: list[str] = []
    if len(scripts) != 3:
        return ["candidate batch must contain exactly 3 complete scripts"]

    batches: list[str] = []
    candidate_ids: list[str] = []
    positions: list[Any] = []
    axis_values: dict[str, list[str]] = {key: [] for key in AXES}
    feedback_contexts: list[Any] = []
    research_scopes: list[Any] = []
    public_questions: list[str] = []
    macro_themes: list[str] = []
    stake_sets: list[tuple[str, ...]] = []
    ranking_pool_ids: list[str] = []
    final_ranks: list[Any] = []
    selection_scores: list[Any] = []
    schema_versions: list[Any] = []
    narrative_patterns: list[str] = []
    dialogue_modes: list[str] = []
    early_action_flags: list[bool] = []
    audience_takeaways: list[str] = []
    fage_responsibilities: list[str] = []

    for index, data in enumerate(scripts, 1):
        result = validate_script(
            data,
            persona,
            feedback_rows,
            required_schema_version=required_schema_version,
        )
        for failure in result.failures:
            failures.append(f"candidate[{index}]: {failure}")
        candidate = data.get("candidate", {})
        schema_versions.append(data.get("schema_version"))
        argument = data.get("argument_engine", {})
        audience_takeaways.append(normalized(argument.get("audience_takeaway")))
        fage_responsibilities.append(normalized(argument.get("fage_entanglement")))
        story = data.get("story_blueprint", {})
        design = data.get("dialogue_design", {})
        narrative_patterns.append(normalized(story.get("narrative_pattern")))
        dialogue_modes.append(normalized(design.get("mode")))
        segments = data.get("segments", [])
        early_action_flags.append(
            any(
                "发哥" in str(item.get("speaker", ""))
                and any(token in str(item.get("visual_action", "")) for token in ("划掉", "签字", "改", "收回", "拿起", "关掉", "打开", "撕", "删除", "发送", "打电话", "起身", "换", "退", "陪", "顶", "试", "认账", "承认"))
                for item in segments[:-1]
                if isinstance(item, dict)
            )
        )
        axes = candidate.get("difference_axes", {}) if isinstance(candidate, dict) else {}
        batches.append(str(candidate.get("batch_id", "")))
        candidate_ids.append(str(candidate.get("candidate_id", "")))
        positions.append(candidate.get("position"))
        feedback_contexts.append(candidate.get("feedback_context"))
        research_scopes.append(candidate.get("research_scope"))
        topic = data.get("topic_strategy", {})
        public_questions.append(normalized(topic.get("public_question")))
        macro_themes.append(str(topic.get("macro_theme", "")))
        ranking = topic.get("selection_ranking", {}) if isinstance(topic, dict) else {}
        ranking_pool_ids.append(str(ranking.get("pool_id", "")))
        final_ranks.append(ranking.get("final_rank"))
        selection_scores.append(ranking.get("selection_score"))
        stakes = topic.get("stake_evidence", []) if isinstance(topic, dict) else []
        stake_sets.append(
            tuple(
                sorted(
                    normalized(item.get("tag"))
                    for item in stakes
                    if isinstance(item, dict) and normalized(item.get("tag"))
                )
            )
        )
        targets = public_axis_targets(data)
        for axis in AXES:
            value = str(axes.get(axis, ""))
            axis_values[axis].append(normalized(value))
            if not axis_is_evidenced(value, targets[axis]):
                failures.append(
                    f"candidate[{index}].difference_axes.{axis} is not evidenced by public copy/action"
                )

    if len(set(batches)) != 1 or not batches[0]:
        failures.append("all candidates must share one non-empty batch_id")
    if len(set(candidate_ids)) != 3 or any(not item for item in candidate_ids):
        failures.append("candidate_id values must be three unique non-empty ids")
    if sorted(positions) != [1, 2, 3]:
        failures.append("candidate positions must be exactly 1, 2, and 3")
    if any(
        data.get("candidate", {}).get("selection_status") != "awaiting_selection"
        for data in scripts
    ):
        failures.append("new candidate batches must remain awaiting_selection")
    if any(context != feedback_contexts[0] for context in feedback_contexts[1:]):
        failures.append("all three candidates must use the same latest feedback context")
    if any(scope != research_scopes[0] for scope in research_scopes[1:]):
        failures.append("all three candidates must use the same research scope")
    elif isinstance(research_scopes[0], dict):
        scope_mode = str(research_scopes[0].get("mode", ""))
        distinct_macro_themes = len(set(macro_themes))
        if scope_mode == "broad_pool" and distinct_macro_themes != 3:
            failures.append("broad_pool requires three distinct macro themes")
        elif scope_mode == "category_focus" and distinct_macro_themes < 2:
            failures.append("category_focus requires at least two distinct macro themes")
    if len(set(public_questions)) != 3 or any(not item for item in public_questions):
        failures.append("three candidates must use three distinct public questions")
    if len(set(stake_sets)) < 2:
        failures.append("three candidates must not repeat one identical public-risk combination")
    enforce_v4_submission = required_schema_version == 4 or any(
        version == 4 for version in schema_versions
    )
    if enforce_v4_submission:
        if schema_versions != [4, 4, 4]:
            failures.append("v4 submission requires schema_version 4 for all candidates")
        for index, data in enumerate(scripts, 1):
            review = data.get("semantic_review", {})
            aggregate = review.get("aggregate", {}) if isinstance(review, dict) else {}
            if not isinstance(aggregate, dict) or aggregate.get("all_pass") is not True:
                failures.append(f"candidate[{index}] semantic review aggregate must pass")
            if not isinstance(aggregate, dict) or aggregate.get("target_match") is not True:
                failures.append(f"candidate[{index}] semantic review target must match")
        if any(not item for item in audience_takeaways) or len(
            set(audience_takeaways)
        ) != 3:
            failures.append("v4 batch requires three distinct audience takeaways")
        if any(not item for item in fage_responsibilities) or len(
            set(fage_responsibilities)
        ) < 2:
            failures.append(
                "v4 batch requires at least two distinct fage responsibility positions"
            )
    has_v3 = any(version == 3 for version in schema_versions)
    has_craft_schema = any(version in {3, 4} for version in schema_versions)
    if has_craft_schema:
        if has_v3 and not enforce_v4_submission and schema_versions != [3, 3, 3]:
            failures.append("a new craft batch must use schema_version 3 for all candidates")
        if len(set(narrative_patterns)) != 3 or any(not item for item in narrative_patterns):
            failures.append("schema v3/v4 batch requires three distinct narrative patterns")
        if len(set(dialogue_modes)) != 3 or any(not item for item in dialogue_modes):
            failures.append("schema v3/v4 batch requires three distinct dialogue modes")
        if narrative_patterns.count("resultfirstflashback") > 1:
            failures.append("schema v3/v4 batch allows at most one result-first flashback")
        if not any(early_action_flags):
            failures.append(
                "schema v3/v4 batch needs 发哥 decisive action before the ending "
                "in at least one candidate"
            )
    if len(set(ranking_pool_ids)) != 1 or not ranking_pool_ids[0]:
        failures.append("all candidates must come from one non-empty ranked topic pool")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in final_ranks):
        failures.append("candidate batch must contain final topic ranks 1, 2, and 3")
    elif sorted(final_ranks) != [1, 2, 3]:
        found_ranks = ", ".join(str(item) for item in sorted(final_ranks))
        failures.append(
            "candidate batch must contain final topic ranks 1, 2, and 3; "
            f"found {found_ranks}; rerank after an explicit veto instead of "
            "silently skipping rank 3"
        )
    elif all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in selection_scores):
        ranked_scores = [score for _, score in sorted(zip(final_ranks, selection_scores))]
        if ranked_scores != sorted(ranked_scores, reverse=True):
            failures.append("final topic ranks must follow descending selection_score")

    fully_distinct = 0
    for axis, values in axis_values.items():
        unique = len(set(values))
        if unique == 3:
            fully_distinct += 1
        if unique == 1:
            failures.append(f"difference axis is identical across all candidates: {axis}")
    if fully_distinct < 3:
        failures.append("at least three of four difference axes must be pairwise distinct")

    viewpoints = [str(data.get("core_viewpoint", "")) for data in scripts]
    viewpoint_pairs = [
        ratio(viewpoints[0], viewpoints[1]),
        ratio(viewpoints[0], viewpoints[2]),
        ratio(viewpoints[1], viewpoints[2]),
    ]
    devices = [
        normalized(data.get("content_signature", {}).get("plot_device"))
        for data in scripts
    ]
    if min(viewpoint_pairs) >= 0.62 and len(set(devices)) == 1:
        failures.append("three scripts repeat one viewpoint and conflict device with cosmetic changes")

    dialogues = [dialogue_text(data) for data in scripts]
    dialogue_pairs = [
        ratio(dialogues[0], dialogues[1]),
        ratio(dialogues[0], dialogues[2]),
        ratio(dialogues[1], dialogues[2]),
    ]
    if min(dialogue_pairs) >= 0.62:
        failures.append("three public dialogue scripts are too similar")

    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", required=True, type=Path)
    parser.add_argument("--persona", required=True, type=Path)
    parser.add_argument("--feedback-ledger", type=Path)
    parser.add_argument("--require-schema-version", type=int, choices=[2, 3, 4])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scripts = [read_json(path) for path in args.inputs]
    persona = read_json(args.persona)
    rows = read_jsonl(args.feedback_ledger) if args.feedback_ledger else None
    failures = validate_batch(
        scripts,
        persona,
        rows,
        required_schema_version=args.require_schema_version,
    )
    print(f"Checked candidate files: {len(scripts)}")
    for failure in failures:
        print(f"FAIL: {failure}")
    print("RESULT: PASS" if not failures else "RESULT: FAIL")
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
