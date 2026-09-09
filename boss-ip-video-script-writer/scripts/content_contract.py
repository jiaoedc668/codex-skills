from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

import history_manager
import select_topics


CURRENT_SCHEMA_VERSION = 5
DURATION_MODES = {"direct_dialogue_30": "30 秒稿", "light_story_60": "60 秒稿"}
FORBIDDEN_HUMAN_KEYS = {
    "evaluation",
    "direct_shoot",
    "minor_revision",
    "major_revision",
    "rejected",
    "shootable",
    "target_match",
    "quality_score",
}
FORBIDDEN_TIMING_KEYS = {
    "read_aloud_timing",
    "tts",
    "median_seconds",
    "spoken_chars",
    "estimated_seconds",
}

TOP_LEVEL_KEYS = {
    "schema_version",
    "candidate",
    "duration_mode",
    "research_evidence",
    "topic_decision",
    "conflict_blueprint",
    "persona_continuity",
    "script",
    "feedback_context",
}
CANDIDATE_KEYS = {
    "batch_id",
    "candidate_id",
    "position",
    "revision_id",
    "evaluation_status",
}
SCRIPT_KEYS = {
    "theme",
    "secondary_theme",
    "lines",
    "key_actions",
    "necessary_shots",
    "state_changes",
    "ending",
    "mode_contract",
}
TOPIC_DECISION_KEYS = {
    "pool_id",
    "topic_id",
    "priority_category",
    "concrete_event",
    "concrete_anchor",
    "audience_stake",
    "strongest_counterargument",
    "fage_choice",
    "fage_cost",
    "ending_consequence",
    "audience_response_space",
}
CONFLICT_BLUEPRINT_KEYS = {
    "immediate_wants",
    "strongest_counterargument",
    "fage_judgment",
    "turning_information",
}
ALLOWED_DIALOGUE_ACTS = {
    "request",
    "conceal",
    "refuse",
    "push_back",
    "save_face",
    "decide",
}
ALLOWED_STATE_CHANGE_KINDS = {"fact", "leverage", "choice", "relationship"}
ALLOWED_ENDING_KINDS = {
    "decision",
    "action",
    "relationship_change",
    "irreversible_consequence",
}
PRINCIPLE_VERSION_FIELDS = {
    "tension",
    "default_choice",
    "rejected_choice",
    "exceptions",
    "cost",
}
CONTINUITY_VERSION_FIELDS = {
    "claim",
    "scope",
    "allowed_reuse",
    "forbidden_expansion",
}
CONTINUITY_SCOPES = {"single_script", "reusable_low_risk"}
FORBIDDEN_BIOGRAPHY_PATTERNS = {
    "我女儿",
    "我儿子",
    "我妻子",
    "我老婆",
    "我当年负债",
    "我创业时",
}


@dataclass
class IntegrityResult:
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


def duration_label(mode: str) -> str:
    if mode not in DURATION_MODES:
        raise ValueError("duration_mode must be direct_dialogue_30 or light_story_60")
    return DURATION_MODES[mode]


def _clean(value: Any) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _require_mapping(
    parent: Mapping[str, Any], key: str, path: str, failures: list[str]
) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        failures.append(f"{path} must be an object")
        return {}
    return value


def _require_list(
    parent: Mapping[str, Any], key: str, path: str, failures: list[str]
) -> list[Any]:
    value = parent.get(key)
    if not isinstance(value, list) or not value:
        failures.append(f"{path} must be a non-empty list")
        return []
    return value


def _require_text(
    parent: Mapping[str, Any], key: str, path: str, failures: list[str]
) -> str:
    value = _clean(parent.get(key))
    if not value:
        failures.append(f"{path} must be non-empty text")
    return value


def _recursive_key_paths(value: Any, path: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            found.append((key_text, child_path))
            found.extend(_recursive_key_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            found.extend(_recursive_key_paths(child, child_path))
    return found


def _format_key_difference(actual: set[str], expected: set[str]) -> str:
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    return f"top-level keys must be exactly the v5 contract; missing={missing}; unexpected={unexpected}"


def _validate_versioned_persona_collection(
    persona: Mapping[str, Any],
    field_name: str,
    payload_fields: set[str],
    failures: list[str],
    *,
    allow_empty: bool,
) -> None:
    records = persona.get(field_name)
    if not isinstance(records, list) or (not allow_empty and not records):
        requirement = "an array" if allow_empty else "a non-empty array"
        failures.append(f"persona.{field_name} must be {requirement}")
        return

    seen_ids: set[str] = set()
    for record_index, record in enumerate(records):
        path = f"persona.{field_name}[{record_index}]"
        if not isinstance(record, Mapping):
            failures.append(f"{path} must be an object")
            continue
        record_id = _require_text(record, "id", f"{path}.id", failures)
        if record_id in seen_ids:
            failures.append(f"persona.{field_name} contains duplicate id {record_id}")
        elif record_id:
            seen_ids.add(record_id)

        status = record.get("status")
        if status not in {"active", "retired"}:
            failures.append(f"{path}.status must be active or retired")
        active_version = record.get("active_version")
        if (
            isinstance(active_version, bool)
            or not isinstance(active_version, int)
            or active_version < 1
        ):
            failures.append(f"{path}.active_version must be a positive integer")

        versions = record.get("versions")
        if not isinstance(versions, list) or not versions:
            failures.append(f"{path}.versions must be a non-empty array")
            continue
        version_numbers: list[int] = []
        for version_index, version in enumerate(versions):
            version_path = f"{path}.versions[{version_index}]"
            if not isinstance(version, Mapping):
                failures.append(f"{version_path} must be an object")
                continue
            number = version.get("version")
            if isinstance(number, bool) or not isinstance(number, int) or number < 1:
                failures.append(f"{version_path}.version must be a positive integer")
            else:
                version_numbers.append(number)
            for key in sorted(payload_fields | {"source_candidate_id", "reason"}):
                if key == "exceptions":
                    exceptions = version.get(key)
                    if not isinstance(exceptions, list) or any(
                        not _clean(item) for item in exceptions
                    ):
                        failures.append(f"{version_path}.exceptions must be an array of text")
                else:
                    _require_text(version, key, f"{version_path}.{key}", failures)
            if field_name == "fictional_continuity":
                scope = version.get("scope")
                if scope not in CONTINUITY_SCOPES:
                    failures.append(
                        f"{version_path}.scope must be single_script or reusable_low_risk"
                    )

        expected_versions = list(range(1, len(versions) + 1))
        if version_numbers != expected_versions:
            failures.append(
                f"{path}.versions must be append-only consecutive versions starting at 1"
            )
        if isinstance(active_version, int) and not isinstance(active_version, bool):
            if active_version not in version_numbers:
                failures.append(f"{path}.active_version points to an unknown version")
            elif version_numbers and active_version != version_numbers[-1]:
                failures.append(f"{path}.active_version must point to the latest version")

        retirement_history = record.get("retirement_history", [])
        if not isinstance(retirement_history, list):
            failures.append(f"{path}.retirement_history must be an array")
        else:
            for history_index, history in enumerate(retirement_history):
                history_path = f"{path}.retirement_history[{history_index}]"
                if not isinstance(history, Mapping):
                    failures.append(f"{history_path} must be an object")
                    continue
                _require_text(
                    history,
                    "source_candidate_id",
                    f"{history_path}.source_candidate_id",
                    failures,
                )
                _require_text(history, "reason", f"{history_path}.reason", failures)
                retired_version = history.get("retired_version")
                if retired_version not in version_numbers:
                    failures.append(
                        f"{history_path}.retired_version must reference an existing version"
                    )
        if status == "retired" and not retirement_history:
            failures.append(f"{path} is retired but has no retirement_history")


def validate_persona_model(persona: Any) -> list[str]:
    failures: list[str] = []
    if not isinstance(persona, Mapping):
        return ["persona must be an object"]
    if persona.get("schema_version") != 3:
        failures.append("persona.schema_version must be 3")
    identity = persona.get("identity")
    if not isinstance(identity, Mapping):
        failures.append("persona.identity must be an object")
    elif identity.get("fiction_status") != "授权虚构人设":
        failures.append("persona.identity.fiction_status must be 授权虚构人设")

    _validate_versioned_persona_collection(
        persona,
        "viewpoint_principles",
        PRINCIPLE_VERSION_FIELDS,
        failures,
        allow_empty=False,
    )
    _validate_versioned_persona_collection(
        persona,
        "fictional_continuity",
        CONTINUITY_VERSION_FIELDS,
        failures,
        allow_empty=True,
    )

    patterns = persona.get("forbidden_biography_patterns")
    categories = persona.get("fact_forbidden")
    has_patterns = isinstance(patterns, list) and bool(patterns) and all(
        _clean(item) for item in patterns
    )
    has_categories = isinstance(categories, list) and bool(categories) and all(
        _clean(item) for item in categories
    )
    if not has_patterns and not has_categories:
        failures.append(
            "persona must define forbidden_biography_patterns or fact_forbidden"
        )
    return failures


def _versioned_records_by_id(
    persona: Mapping[str, Any], field_name: str
) -> dict[str, Mapping[str, Any]]:
    records = persona.get(field_name)
    if not isinstance(records, list):
        return {}
    return {
        _clean(record.get("id")): record
        for record in records
        if isinstance(record, Mapping) and _clean(record.get("id"))
    }


def _validate_persona_reference(
    reference: Mapping[str, Any],
    persona: Mapping[str, Any],
    failures: list[str],
) -> None:
    principle_id = _require_text(
        reference, "principle_id", "persona_continuity.principle_id", failures
    )
    principle_version = reference.get("principle_version")
    if isinstance(principle_version, bool) or not isinstance(principle_version, int):
        failures.append("persona_continuity.principle_version must be an integer")
    use_mode = reference.get("use_mode")
    if use_mode not in {"follow", "exception", "revise"}:
        failures.append(
            "persona_continuity.use_mode must be follow, exception, or revise"
        )
    _require_text(
        reference,
        "use_explanation",
        "persona_continuity.use_explanation",
        failures,
    )

    principles = _versioned_records_by_id(persona, "viewpoint_principles")
    principle = principles.get(principle_id)
    if principle_id and principle is None:
        failures.append(f"unknown principle id {principle_id}")
    elif principle is not None and isinstance(principle_version, int):
        versions = {
            version.get("version")
            for version in principle.get("versions", [])
            if isinstance(version, Mapping)
        }
        if principle_version not in versions:
            failures.append(
                f"unknown principle version {principle_id}@{principle_version}"
            )
        elif principle_version != principle.get("active_version"):
            failures.append(
                f"stale principle version {principle_id}@{principle_version}"
            )
        if principle.get("status") != "active":
            failures.append(f"retired principle reference {principle_id}")

    continuity_refs = reference.get("continuity_refs")
    if not isinstance(continuity_refs, list):
        failures.append("persona_continuity.continuity_refs must be an array")
        return
    continuity = _versioned_records_by_id(persona, "fictional_continuity")
    for index, item in enumerate(continuity_refs):
        path = f"persona_continuity.continuity_refs[{index}]"
        if not isinstance(item, Mapping):
            failures.append(f"{path} must be an object")
            continue
        continuity_id = _require_text(item, "continuity_id", f"{path}.continuity_id", failures)
        continuity_version = item.get("continuity_version")
        if isinstance(continuity_version, bool) or not isinstance(continuity_version, int):
            failures.append(f"{path}.continuity_version must be an integer")
            continue
        record = continuity.get(continuity_id)
        if record is None:
            failures.append(f"unknown continuity id {continuity_id}")
            continue
        versions = {
            version.get("version")
            for version in record.get("versions", [])
            if isinstance(version, Mapping)
        }
        if continuity_version not in versions:
            failures.append(
                f"unknown continuity version {continuity_id}@{continuity_version}"
            )
        elif continuity_version != record.get("active_version"):
            failures.append(
                f"stale continuity version {continuity_id}@{continuity_version}"
            )
        if record.get("status") != "active":
            failures.append(f"retired continuity reference {continuity_id}")


def _all_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        texts: list[str] = []
        for child in value.values():
            texts.extend(_all_text(child))
        return texts
    if isinstance(value, list):
        texts = []
        for child in value:
            texts.extend(_all_text(child))
        return texts
    return []


def _validate_forbidden_biography(
    script: Mapping[str, Any],
    persona: Mapping[str, Any],
    failures: list[str],
) -> None:
    patterns = set(FORBIDDEN_BIOGRAPHY_PATTERNS)
    configured = persona.get("forbidden_biography_patterns")
    if isinstance(configured, list):
        patterns.update(_clean(item) for item in configured if _clean(item))
    for text in _all_text(script):
        match = next((pattern for pattern in sorted(patterns) if pattern in text), None)
        if match:
            failures.append(f"forbidden biography pattern in script: {match}")
            return


def _validate_candidate_identity(
    candidate: Mapping[str, Any], failures: list[str]
) -> None:
    actual_keys = set(candidate)
    if actual_keys != CANDIDATE_KEYS:
        missing = sorted(CANDIDATE_KEYS - actual_keys)
        unexpected = sorted(actual_keys - CANDIDATE_KEYS)
        failures.append(
            "candidate keys must be exactly the v5 contract; "
            f"missing={missing}; unexpected={unexpected}"
        )
    for key in ("batch_id", "candidate_id", "revision_id"):
        _require_text(candidate, key, f"candidate.{key}", failures)
    position = candidate.get("position")
    if isinstance(position, bool) or not isinstance(position, int) or position < 1:
        failures.append("candidate.position must be a positive integer")
    if candidate.get("evaluation_status") != "awaiting_user_evaluation":
        failures.append(
            "candidate.evaluation_status must be awaiting_user_evaluation"
        )


def _validate_research_evidence(
    evidence: Mapping[str, Any], failures: list[str]
) -> None:
    topic_kind = _clean(evidence.get("topic_kind"))
    try:
        select_topics.validate_research_evidence(topic_kind, evidence)
    except ValueError as exc:
        failures.append(f"research_evidence invalid: {exc}")


def _validate_topic_decision_shape(
    decision: Mapping[str, Any], failures: list[str]
) -> None:
    actual_keys = set(decision)
    if actual_keys != TOPIC_DECISION_KEYS:
        missing = sorted(TOPIC_DECISION_KEYS - actual_keys)
        unexpected = sorted(actual_keys - TOPIC_DECISION_KEYS)
        failures.append(
            "topic_decision keys must be exact; "
            f"missing={missing}; unexpected={unexpected}"
        )
    for key in sorted(TOPIC_DECISION_KEYS):
        _require_text(decision, key, f"topic_decision.{key}", failures)


def _validate_conflict_blueprint(
    blueprint: Mapping[str, Any], failures: list[str]
) -> None:
    actual_keys = set(blueprint)
    if actual_keys != CONFLICT_BLUEPRINT_KEYS:
        missing = sorted(CONFLICT_BLUEPRINT_KEYS - actual_keys)
        unexpected = sorted(actual_keys - CONFLICT_BLUEPRINT_KEYS)
        failures.append(
            "conflict_blueprint keys must be exact; "
            f"missing={missing}; unexpected={unexpected}"
        )

    wants = blueprint.get("immediate_wants")
    parties: list[str] = []
    if not isinstance(wants, list) or len(wants) != 2:
        failures.append(
            "conflict_blueprint.immediate_wants must contain exactly two parties "
            "including 发哥 and one counterparty"
        )
    else:
        for index, want in enumerate(wants):
            path = f"conflict_blueprint.immediate_wants[{index}]"
            if not isinstance(want, Mapping):
                failures.append(f"{path} must be an object")
                continue
            party = _require_text(want, "party", f"{path}.party", failures)
            _require_text(want, "want", f"{path}.want", failures)
            _require_list(want, "line_ids", f"{path}.line_ids", failures)
            if party:
                parties.append(party)
        if len(set(parties)) != 2 or parties.count("发哥") != 1:
            failures.append(
                "conflict_blueprint.immediate_wants must contain exactly two parties "
                "including 发哥 and one counterparty"
            )

    counterargument = _require_mapping(
        blueprint,
        "strongest_counterargument",
        "conflict_blueprint.strongest_counterargument",
        failures,
    )
    counter_speaker = _require_text(
        counterargument,
        "speaker",
        "conflict_blueprint.strongest_counterargument.speaker",
        failures,
    )
    _require_text(
        counterargument,
        "argument",
        "conflict_blueprint.strongest_counterargument.argument",
        failures,
    )
    _require_list(
        counterargument,
        "line_ids",
        "conflict_blueprint.strongest_counterargument.line_ids",
        failures,
    )
    if "发哥" in counter_speaker:
        failures.append("strongest counterargument speaker must not be 发哥")
    if counterargument.get("survives_after_judgment") is not True:
        failures.append("counterargument must survive fage judgment")

    judgment = _require_mapping(
        blueprint,
        "fage_judgment",
        "conflict_blueprint.fage_judgment",
        failures,
    )
    for key in ("decision", "rejected_option", "cost"):
        _require_text(
            judgment, key, f"conflict_blueprint.fage_judgment.{key}", failures
        )
    _require_list(
        judgment,
        "line_ids",
        "conflict_blueprint.fage_judgment.line_ids",
        failures,
    )

    turning = _require_mapping(
        blueprint,
        "turning_information",
        "conflict_blueprint.turning_information",
        failures,
    )
    for key in ("new_information", "before_action", "after_action"):
        _require_text(
            turning,
            key,
            f"conflict_blueprint.turning_information.{key}",
            failures,
        )
    _require_list(
        turning,
        "line_ids",
        "conflict_blueprint.turning_information.line_ids",
        failures,
    )


def _validate_script_shape(
    script: Mapping[str, Any], failures: list[str]
) -> tuple[set[str], set[str]]:
    missing = SCRIPT_KEYS - set(script)
    if missing:
        failures.append(f"script missing required keys: {sorted(missing)}")
    _require_text(script, "theme", "script.theme", failures)
    _require_text(script, "secondary_theme", "script.secondary_theme", failures)

    line_ids: set[str] = set()
    lines = _require_list(script, "lines", "script.lines", failures)
    for index, item in enumerate(lines):
        path = f"script.lines[{index}]"
        if not isinstance(item, Mapping):
            failures.append(f"{path} must be an object")
            continue
        line_id = _require_text(item, "line_id", f"{path}.line_id", failures)
        _require_text(item, "speaker", f"{path}.speaker", failures)
        _require_text(item, "text", f"{path}.text", failures)
        dialogue_act = _require_text(
            item, "dialogue_act", f"{path}.dialogue_act", failures
        )
        if dialogue_act and dialogue_act not in ALLOWED_DIALOGUE_ACTS:
            failures.append(
                f"{path}.dialogue_act must be one of {sorted(ALLOWED_DIALOGUE_ACTS)}"
            )
        if line_id in line_ids:
            failures.append(f"duplicate dialogue line_id {line_id}")
        elif line_id:
            line_ids.add(line_id)

    action_ids: set[str] = set()
    actions = _require_list(script, "key_actions", "script.key_actions", failures)
    for index, item in enumerate(actions):
        path = f"script.key_actions[{index}]"
        if not isinstance(item, Mapping):
            failures.append(f"{path} must be an object")
            continue
        action_id = _require_text(item, "action_id", f"{path}.action_id", failures)
        _require_text(item, "after_line_id", f"{path}.after_line_id", failures)
        _require_text(item, "action", f"{path}.action", failures)
        _require_text(item, "consequence", f"{path}.consequence", failures)
        if action_id in action_ids:
            failures.append(f"duplicate key action_id {action_id}")
        elif action_id:
            action_ids.add(action_id)

    shots = _require_list(script, "necessary_shots", "script.necessary_shots", failures)
    for index, item in enumerate(shots):
        if not _clean(item):
            failures.append(f"script.necessary_shots[{index}] must be non-empty text")

    changes = _require_list(script, "state_changes", "script.state_changes", failures)
    for index, item in enumerate(changes):
        path = f"script.state_changes[{index}]"
        if not isinstance(item, Mapping):
            failures.append(f"{path} must be an object")
            continue
        _require_text(item, "after_line_id", f"{path}.after_line_id", failures)
        _require_list(item, "line_ids", f"{path}.line_ids", failures)
        kind = _require_text(item, "kind", f"{path}.kind", failures)
        if kind and kind not in ALLOWED_STATE_CHANGE_KINDS:
            failures.append(
                f"state change kind at {path} must be one of "
                f"{sorted(ALLOWED_STATE_CHANGE_KINDS)}"
            )
        _require_text(item, "before", f"{path}.before", failures)
        _require_text(item, "after", f"{path}.after", failures)

    ending = _require_mapping(script, "ending", "script.ending", failures)
    for key in ("after_line_id", "kind", "consequence"):
        _require_text(ending, key, f"script.ending.{key}", failures)
    ending_kind = _clean(ending.get("kind"))
    if ending_kind and ending_kind not in ALLOWED_ENDING_KINDS:
        failures.append(
            f"ending kind must be one of {sorted(ALLOWED_ENDING_KINDS)}"
        )
    mode_contract = _require_mapping(
        script, "mode_contract", "script.mode_contract", failures
    )
    _require_text(
        mode_contract,
        "turning_evidence_line_id",
        "script.mode_contract.turning_evidence_line_id",
        failures,
    )
    _require_text(
        mode_contract,
        "result_action_id",
        "script.mode_contract.result_action_id",
        failures,
    )
    return line_ids, action_ids


def _collect_references(
    value: Any,
    path: str,
    line_references: list[tuple[str, str]],
    action_references: list[tuple[str, str]],
    failures: list[str],
) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key == "line_ids":
                if not isinstance(child, list) or not child:
                    failures.append(f"{child_path} must be a non-empty list")
                else:
                    for reference in child:
                        if _clean(reference):
                            line_references.append((_clean(reference), child_path))
                        else:
                            failures.append(f"{child_path} contains an empty line reference")
            elif key in {"after_line_id", "turning_evidence_line_id"}:
                if _clean(child):
                    line_references.append((_clean(child), child_path))
            elif key == "result_action_id" and _clean(child):
                action_references.append((_clean(child), child_path))
            _collect_references(
                child,
                child_path,
                line_references,
                action_references,
                failures,
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _collect_references(
                child,
                f"{path}[{index}]",
                line_references,
                action_references,
                failures,
            )


def _validate_references(
    conflict_blueprint: Mapping[str, Any],
    script: Mapping[str, Any],
    line_ids: set[str],
    action_ids: set[str],
    failures: list[str],
) -> None:
    line_references: list[tuple[str, str]] = []
    action_references: list[tuple[str, str]] = []
    _collect_references(
        conflict_blueprint,
        "conflict_blueprint",
        line_references,
        action_references,
        failures,
    )
    _collect_references(
        {key: value for key, value in script.items() if key != "lines"},
        "script",
        line_references,
        action_references,
        failures,
    )
    for reference, path in line_references:
        if reference not in line_ids:
            failures.append(f"unknown line reference {reference} at {path}")
    for reference, path in action_references:
        if reference not in action_ids:
            failures.append(f"unknown action reference {reference} at {path}")


def _script_line_order(script: Mapping[str, Any]) -> list[str]:
    lines = script.get("lines")
    if not isinstance(lines, list):
        return []
    return [
        _clean(line.get("line_id"))
        for line in lines
        if isinstance(line, Mapping) and _clean(line.get("line_id"))
    ]


def _validate_state_change_coverage(
    script: Mapping[str, Any], line_order: list[str], failures: list[str]
) -> None:
    changes = script.get("state_changes")
    if not isinstance(changes, list) or not line_order:
        return
    cursor = 0
    valid = True
    for change in changes:
        if not isinstance(change, Mapping):
            valid = False
            continue
        group = change.get("line_ids")
        if not isinstance(group, list):
            valid = False
            continue
        normalized_group = [_clean(item) for item in group]
        if len(normalized_group) not in {2, 3}:
            valid = False
        expected = line_order[cursor : cursor + len(normalized_group)]
        if normalized_group != expected:
            valid = False
        if not normalized_group or _clean(change.get("after_line_id")) != normalized_group[-1]:
            valid = False
        cursor += len(normalized_group)
    if cursor != len(line_order):
        valid = False
    if not valid:
        failures.append(
            "script.state_changes must cover every two or three lines in order, "
            "with after_line_id on the final covered line"
        )


def _validate_ending_and_mode(
    mode: Any,
    script: Mapping[str, Any],
    line_order: list[str],
    failures: list[str],
) -> None:
    ending = script.get("ending")
    mode_contract = script.get("mode_contract")
    actions = script.get("key_actions")
    if not isinstance(ending, Mapping) or not isinstance(mode_contract, Mapping):
        return
    action_rows = actions if isinstance(actions, list) else []
    action_by_id = {
        _clean(action.get("action_id")): action
        for action in action_rows
        if isinstance(action, Mapping) and _clean(action.get("action_id"))
    }
    if not _clean(ending.get("consequence")):
        failures.append("ending consequence must be non-empty")
    ending_line = _clean(ending.get("after_line_id"))
    if line_order and ending_line != line_order[-1]:
        failures.append("ending must occur after the final dialogue line")

    result_action_id = _clean(mode_contract.get("result_action_id"))
    result_action = action_by_id.get(result_action_id)
    if result_action is not None and _clean(result_action.get("after_line_id")) != ending_line:
        failures.append("ending must reference the result action and its consequence")

    if mode == "direct_dialogue_30":
        if (
            script.get("secondary_theme") != "无"
            or mode_contract.get("dilemma_count") != 1
            or mode_contract.get("judgment_count") != 1
        ):
            failures.append(
                "direct dialogue must contain one dilemma and one judgment "
                "with no second theme"
            )
    elif mode == "light_story_60":
        turning_id = _clean(mode_contract.get("turning_evidence_line_id"))
        try:
            turning_index = line_order.index(turning_id)
        except ValueError:
            turning_index = -1
        result_line = _clean(result_action.get("after_line_id")) if result_action else ""
        try:
            result_index = line_order.index(result_line)
        except ValueError:
            result_index = -1
        if (
            turning_index < 2
            or turning_index > len(line_order) - 2
            or result_index <= turning_index
        ):
            failures.append(
                "light story middle turning evidence must change a later action"
            )


def derive_causal_skeleton(
    candidate: Mapping[str, Any],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], str]:
    script = candidate.get("script")
    if not isinstance(script, Mapping):
        return ((), (), (), "")
    lines = script.get("lines")
    changes = script.get("state_changes")
    ending = script.get("ending")
    line_rows = lines if isinstance(lines, list) else []
    change_rows = changes if isinstance(changes, list) else []
    speaker_roles = tuple(
        "fage" if "发哥" in _clean(line.get("speaker")) else "counterparty"
        for line in line_rows
        if isinstance(line, Mapping)
    )
    dialogue_acts = tuple(
        _clean(line.get("dialogue_act"))
        for line in line_rows
        if isinstance(line, Mapping)
    )
    state_kinds = tuple(
        _clean(change.get("kind"))
        for change in change_rows
        if isinstance(change, Mapping)
    )
    ending_kind = _clean(ending.get("kind")) if isinstance(ending, Mapping) else ""
    return speaker_roles, dialogue_acts, state_kinds, ending_kind


def validate_candidate(
    data: Any, persona: Any, feedback_rows: list[dict[str, Any]]
) -> IntegrityResult:
    if isinstance(data, Mapping) and data.get("schema_version") == 6:
        from dual_format_contract import validate_candidate as validate_v6
        return validate_v6(data, persona, feedback_rows)
    failures: list[str] = []
    if not isinstance(data, Mapping):
        return IntegrityResult(failures=["candidate document must be an object"])

    actual_top_level = set(data)
    if actual_top_level != TOP_LEVEL_KEYS:
        failures.append(_format_key_difference(actual_top_level, TOP_LEVEL_KEYS))
    if data.get("schema_version") != CURRENT_SCHEMA_VERSION:
        failures.append("schema_version must be 5")

    key_paths = _recursive_key_paths(data)
    human_paths = sorted(path for key, path in key_paths if key in FORBIDDEN_HUMAN_KEYS)
    timing_paths = sorted(path for key, path in key_paths if key in FORBIDDEN_TIMING_KEYS)
    if human_paths:
        failures.append(
            "human evaluation fields are forbidden in candidate input: "
            + ", ".join(human_paths)
        )
    if timing_paths:
        failures.append(
            "timing fields are forbidden in candidate input: "
            + ", ".join(timing_paths)
        )

    candidate = _require_mapping(data, "candidate", "candidate", failures)
    _validate_candidate_identity(candidate, failures)
    research_evidence: Mapping[str, Any] = {}
    topic_decision: Mapping[str, Any] = {}
    persona_continuity: Mapping[str, Any] = {}
    for key in (
        "research_evidence",
        "topic_decision",
        "persona_continuity",
    ):
        value = _require_mapping(data, key, key, failures)
        if key == "research_evidence":
            research_evidence = value
        elif key == "topic_decision":
            topic_decision = value
        elif key == "persona_continuity":
            persona_continuity = value
    conflict_blueprint = _require_mapping(
        data, "conflict_blueprint", "conflict_blueprint", failures
    )
    script = _require_mapping(data, "script", "script", failures)
    feedback_context = _require_mapping(
        data, "feedback_context", "feedback_context", failures
    )
    if not isinstance(persona, Mapping):
        failures.append("persona must be an object")
        persona_mapping: Mapping[str, Any] = {}
    else:
        persona_mapping = persona
        failures.extend(validate_persona_model(persona_mapping))
        _validate_persona_reference(persona_continuity, persona_mapping, failures)

    _validate_research_evidence(research_evidence, failures)
    _validate_topic_decision_shape(topic_decision, failures)
    _validate_conflict_blueprint(conflict_blueprint, failures)

    mode = data.get("duration_mode")
    try:
        duration_label(mode)
    except (TypeError, ValueError):
        failures.append(
            "duration_mode must be direct_dialogue_30 or light_story_60"
        )

    expected_feedback = history_manager.feedback_context(feedback_rows)
    if dict(feedback_context) != expected_feedback:
        failures.append("feedback_context differs from current explicit ledger")

    line_ids, action_ids = _validate_script_shape(script, failures)
    line_order = _script_line_order(script)
    _validate_state_change_coverage(script, line_order, failures)
    _validate_ending_and_mode(mode, script, line_order, failures)
    if persona_mapping:
        _validate_forbidden_biography(script, persona_mapping, failures)
    _validate_references(
        conflict_blueprint,
        script,
        line_ids,
        action_ids,
        failures,
    )
    return IntegrityResult(failures=failures)


def validate_batch(
    candidates: Any,
    persona: Any,
    feedback_rows: list[dict[str, Any]],
    topic_pool: Any,
) -> list[str]:
    failures: list[str] = []
    if not isinstance(candidates, list):
        return ["candidate batch must contain exactly 3 complete scripts"]
    requested_count = 3
    if (candidates and all(isinstance(c, Mapping) and c.get("schema_version") == 6 for c in candidates)
            and isinstance(topic_pool, Mapping) and topic_pool.get("schema_version") == 6):
        requested_count = topic_pool.get("requested_candidate_count", 3)
        if isinstance(requested_count, bool) or not isinstance(requested_count, int) or requested_count < 1:
            failures.append("requested_candidate_count must be a positive integer")
            requested_count = 3
    if len(candidates) != requested_count:
        failures.append(f"candidate batch must contain exactly {requested_count} complete scripts")

    candidate_rows = [item for item in candidates if isinstance(item, Mapping)]
    if len(candidate_rows) != len(candidates):
        failures.append("every candidate batch item must be a complete script object")
    for index, candidate in enumerate(candidates, 1):
        result = validate_candidate(candidate, persona, feedback_rows)
        failures.extend(
            f"candidate {index}: {failure}" for failure in result.failures
        )

    identities = [
        candidate.get("candidate", {})
        for candidate in candidate_rows
        if isinstance(candidate.get("candidate"), Mapping)
    ]
    candidate_ids = [_clean(identity.get("candidate_id")) for identity in identities]
    if (
        len(candidate_ids) != len(candidates)
        or any(not candidate_id for candidate_id in candidate_ids)
        or len(set(candidate_ids)) != len(candidate_ids)
    ):
        failures.append("candidate batch requires unique candidate IDs")

    positions = [identity.get("position") for identity in identities]
    if sorted(position for position in positions if isinstance(position, int) and not isinstance(position, bool)) != list(range(1, requested_count + 1)):
        failures.append("candidate batch positions must be exactly positions 1, 2, and 3" if requested_count == 3 else f"candidate batch positions must be exactly positions 1 through {requested_count}")

    batch_ids = {_clean(identity.get("batch_id")) for identity in identities}
    if len(batch_ids) != 1 or "" in batch_ids:
        failures.append("candidate batch must use one batch ID")

    schemas = {candidate.get("schema_version") for candidate in candidate_rows}
    if len(schemas) > 1:
        failures.append("candidate batch must use one schema version")
    if schemas == {6}:
        formats = {_clean(candidate.get("format")) for candidate in candidate_rows}
        if len(formats) != 1:
            failures.append("candidate batch must use one format")
        if not isinstance(topic_pool, Mapping) or topic_pool.get("schema_version") != 6:
            failures.append("v6 batch requires v6 selection pool")
    modes = {_clean(candidate.get("duration_mode")) for candidate in candidate_rows}
    if len(modes) != 1:
        failures.append("candidate batch must use one duration_mode")

    feedback_contexts = [candidate.get("feedback_context") for candidate in candidate_rows]
    if feedback_contexts and any(
        context != feedback_contexts[0] for context in feedback_contexts[1:]
    ):
        failures.append("candidate batch must use identical feedback context")

    selected_result: dict[str, Any] | None = None
    try:
        selected_result = select_topics.select_topics(topic_pool)
    except ValueError as exc:
        failures.append(f"topic pool invalid: {exc}")
    if selected_result is not None:
        selected_rows = selected_result["selected"]
        selected_by_id = {row["topic_id"]: row for row in selected_rows}
        decisions = [
            candidate.get("topic_decision", {})
            for candidate in candidate_rows
            if isinstance(candidate.get("topic_decision"), Mapping)
        ]
        candidate_topic_ids = [_clean(decision.get("topic_id")) for decision in decisions]
        if (
            len(candidate_topic_ids) != len(candidates)
            or len(set(candidate_topic_ids)) != len(candidate_topic_ids)
            or set(candidate_topic_ids) != set(selected_by_id)
        ):
            failures.append("candidate batch topic IDs must equal the selected topic set")
        for decision in decisions:
            topic_id = _clean(decision.get("topic_id"))
            selected = selected_by_id.get(topic_id)
            if selected is None:
                continue
            expected_values = {
                "pool_id": selected_result["pool_id"],
                "topic_id": topic_id,
                "priority_category": selected["priority_category"],
                **selected["production_case"],
            }
            if any(decision.get(key) != value for key, value in expected_values.items()):
                failures.append(
                    f"candidate {topic_id} topic decision must match selected topic"
                )

    if len(candidate_rows) == 3:
        skeletons = [derive_causal_skeleton(candidate) for candidate in candidate_rows]
        if len(set(skeletons)) == 1:
            failures.append("all three candidates use the same causal skeleton")
    return failures


def build_public_candidate(data: Mapping[str, Any]) -> dict[str, Any]:
    if data.get("schema_version") == 6:
        from dual_format_contract import public_candidate
        return public_candidate(data)
    script = data["script"]
    return {
        "duration_label": duration_label(data["duration_mode"]),
        "theme": script["theme"],
        "dialogue": [
            {"speaker": line["speaker"], "text": line["text"]}
            for line in script["lines"]
        ],
        "key_actions": deepcopy(script["key_actions"]),
        "necessary_shots": deepcopy(script["necessary_shots"]),
    }
