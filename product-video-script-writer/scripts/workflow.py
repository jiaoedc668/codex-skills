from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LEDGERS = {
    "products": "product-catalog.jsonl",
    "used": "used-ideas.jsonl",
    "rejected": "rejection-pool.jsonl",
    "feedback": "feedback-ledger.jsonl",
    "shared_preferences": "shared-creative-preferences.jsonl",
    "publishing": "publishing-data.jsonl",
}
QUOTE_REQUIRED_TYPES = {
    "product_registered", "candidate_selection", "copy_revision", "copy_confirmation",
    "candidate_rejection", "creative_preference", "publishing_data",
}
REJECTION_REASONS = {"topic", "structure", "expression", "one_off"}


class EventError(ValueError):
    pass


class WorkflowError(ValueError):
    pass


def copy_sha256(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _new_event(event_type: str, product_id: str, user_quote: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "event_id": f"evt-{uuid.uuid4()}",
        "event_type": event_type,
        "occurred_at": _now(),
        "product_id": product_id,
        "user_quote": user_quote,
        "payload": payload,
    }


class Workspace:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        config = self.root / "workspace.json"
        if not config.exists():
            config.write_text(
                json.dumps({"schema_version": 1, "workspace_id": f"ws-{uuid.uuid4()}"}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    def _path(self, ledger: str) -> Path:
        if ledger not in LEDGERS:
            raise EventError(f"未知 ledger: {ledger}")
        return self.root / LEDGERS[ledger]

    def read_events(self, ledger: str) -> list[dict[str, Any]]:
        path = self._path(ledger)
        if not path.exists():
            return []
        events: list[dict[str, Any]] = []
        seen: set[str] = set()
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise EventError(f"{path.name}:{line_number} 是损坏事件: {exc.msg}") from exc
            if not isinstance(event, dict):
                raise EventError(f"{path.name}:{line_number} 是损坏事件: 事件必须是对象")
            event_id = event.get("event_id")
            if not isinstance(event_id, str) or not event_id:
                raise EventError(f"{path.name}:{line_number} 是损坏事件: 缺少 event_id")
            if event_id in seen:
                raise EventError(f"重复 event_id: {event_id}")
            seen.add(event_id)
            events.append(event)
        return events

    def _all_ids(self) -> set[str]:
        ids: set[str] = set()
        for ledger in LEDGERS:
            for event in self.read_events(ledger):
                event_id = event["event_id"]
                if event_id in ids:
                    raise EventError(f"重复 event_id: {event_id}")
                ids.add(event_id)
        return ids

    def append_event(self, ledger: str, event: dict[str, Any]) -> dict[str, Any]:
        required = ("schema_version", "event_id", "event_type", "occurred_at", "product_id", "payload")
        missing = [key for key in required if key not in event]
        if missing:
            raise EventError("事件缺少字段: " + ", ".join(missing))
        if not isinstance(event["payload"], dict):
            raise EventError("payload 必须是对象")
        if event["event_type"] in QUOTE_REQUIRED_TYPES and not str(event.get("user_quote") or "").strip():
            raise EventError("该事件必须保留用户原话")
        if event["event_id"] in self._all_ids():
            raise EventError(f"重复 event_id: {event['event_id']}")
        self.initialize()
        with self._path(ledger).open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event

    def register_product(self, brief: dict[str, Any], user_quote: str) -> dict[str, Any]:
        product_id = str(brief.get("product_id") or "").strip()
        if not product_id:
            raise WorkflowError("product_id is required")
        return self.append_event("products", _new_event("product_registered", product_id, user_quote, {"brief": brief}))

    def events_for_product(self, ledger: str, product_id: str) -> list[dict[str, Any]]:
        return [event for event in self.read_events(ledger) if event.get("product_id") == product_id]

    def record_selection(self, product_id: str, candidate_id: str, copy_text: str, user_quote: str) -> dict[str, Any]:
        return self.append_event("feedback", _new_event("candidate_selection", product_id, user_quote, {
            "candidate_id": candidate_id, "copy_sha256": copy_sha256(copy_text), "copy_text": copy_text,
        }))

    def record_revision(self, product_id: str, copy_text: str, user_quote: str) -> dict[str, Any]:
        return self.append_event("feedback", _new_event("copy_revision", product_id, user_quote, {
            "copy_sha256": copy_sha256(copy_text), "copy_text": copy_text, "invalidates_prior_confirmation": True,
        }))

    def record_confirmation(self, product_id: str, copy_text: str, user_quote: str) -> dict[str, Any]:
        return self.append_event("feedback", _new_event("copy_confirmation", product_id, user_quote, {
            "copy_sha256": copy_sha256(copy_text), "copy_text": copy_text,
        }))

    def can_generate_word(self, product_id: str, current_copy: str) -> bool:
        current_hash = copy_sha256(current_copy)
        events = self.events_for_product("feedback", product_id)
        selected = False
        latest_copy_index = -1
        latest_copy_hash = None
        latest_confirmation_index = -1
        for index, event in enumerate(events):
            payload = event.get("payload", {})
            if event.get("event_type") == "candidate_selection":
                selected = True
                latest_copy_index = index
                latest_copy_hash = payload.get("copy_sha256")
            elif event.get("event_type") == "copy_revision":
                latest_copy_index = index
                latest_copy_hash = payload.get("copy_sha256")
            elif event.get("event_type") == "copy_confirmation" and payload.get("copy_sha256") == current_hash:
                latest_confirmation_index = index
        return selected and latest_copy_hash == current_hash and latest_confirmation_index > latest_copy_index

    def record_rejection(self, product_id: str, candidate_id: str, user_quote: str, reason_category: str | None = None) -> dict[str, Any]:
        if reason_category is not None and reason_category not in REJECTION_REASONS:
            raise WorkflowError("reason_category 必须是 topic、structure、expression 或 one_off")
        return self.append_event("rejected", _new_event("candidate_rejection", product_id, user_quote, {
            "candidate_id": candidate_id,
            "reason_category": reason_category,
            "scope": "categorized" if reason_category else "similarity_only",
        }))

    def record_publish_data(self, product_id: str, candidate_id: str, user_quote: str, views_24h: int | None, views_7d: int | None, recent_10_median: int | float | None) -> dict[str, Any]:
        return self.append_event("publishing", _new_event("publishing_data", product_id, user_quote, {
            "candidate_id": candidate_id,
            "views_24h": views_24h,
            "views_7d": views_7d,
            "recent_10_median": recent_10_median,
        }))

    def record_shared_preference(self, product_id: str, source_skill: str, preference: str, user_quote: str) -> dict[str, Any]:
        return self.append_event("shared_preferences", _new_event("creative_preference", product_id, user_quote, {
            "source_skill": source_skill, "preference": preference,
        }))

    def read_shared_preferences(self) -> list[dict[str, Any]]:
        return self.read_events("shared_preferences")
