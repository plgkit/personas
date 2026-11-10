"""Turn stored events into one persona. No database, no clock of its own."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from plgkit_personas.config import normalize_policy
from plgkit_personas.errors import PlgkitError
from plgkit_personas.mapping import CATEGORIES, normalize_mapping

REASON_LIMIT = 5
_SUPPORTS = {
    "champion": frozenset({"invite_sent"}),
    "power_user": frozenset({"core_action"}),
    "blocked": frozenset(CATEGORIES),
    "implementer": frozenset({"setup_step"}),
    "evaluator": frozenset(CATEGORIES),
    "unknown": frozenset(),
}


def judge(user_id, events, *, mapping, policy=None, now=None):
    """Return the persona object for one user.

    `events` is a list of `{action, occurred_at}`. `mapping` is
    `{action: category}`. `now` becomes `calculated_at`.
    """
    user_id = require_text(user_id, "user_id")
    moment = parse_time(now) if now is not None else datetime.now(timezone.utc)
    rules = normalize_policy(policy)
    categories = normalize_mapping(mapping)
    counted = _in_window(events, categories, moment, rules["lookback_days"])
    counts = {name: 0 for name in CATEGORIES}
    for event in counted:
        counts[event["category"]] += 1
    newest = counted[-1]["occurred_at"] if counted else None
    silence_at = moment - timedelta(days=rules["silence_days"])
    quiet = newest is not None and newest <= silence_at
    started = counts["setup_step"] >= 1 or counts["core_action"] >= 1
    matched = []
    if counts["invite_sent"] >= rules["champion_min"]:
        matched.append("champion")
    if counts["core_action"] >= rules["power_user_min"]:
        matched.append("power_user")
    if started and quiet:
        matched.append("blocked")
    if counts["setup_step"] >= rules["implementer_min"]:
        matched.append("implementer")
    if counted:
        matched.append("evaluator")
    persona_name = matched[0] if matched else "unknown"
    return {
        "user_id": user_id,
        "persona": persona_name,
        "reasons": _reasons(counted, persona_name),
        "counts": counts,
        "matched": matched,
        "calculated_at": format_time(moment),
    }


def parse_time(value):
    """Parse an ISO-8601 timestamp that names its timezone."""
    if not isinstance(value, str):
        raise PlgkitError("occurred_at must be an ISO-8601 timestamp with a timezone.")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise PlgkitError(
            "occurred_at must be an ISO-8601 timestamp with a timezone."
        ) from exc
    if parsed.tzinfo is None:
        raise PlgkitError("occurred_at must include a timezone, for example 2026-11-09T15:00:00Z.")
    return parsed.astimezone(timezone.utc)


def format_time(moment):
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def require_text(value, name):
    if not isinstance(value, str) or value.strip() == "":
        raise PlgkitError(f"{name} is required.")
    return value.strip()


def _in_window(events, mapping, moment, lookback_days):
    if events is None:
        events = []
    if not isinstance(events, list):
        raise PlgkitError("events must be a list.")
    start = moment - timedelta(days=lookback_days)
    counted = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise PlgkitError("each event must be an object.")
        action = event.get("action")
        if not isinstance(action, str) or action.strip() == "":
            raise PlgkitError("each event needs an action.")
        action = action.strip()
        category = mapping.get(action)
        if category not in CATEGORIES:
            continue
        occurred_at = parse_time(event.get("occurred_at"))
        if occurred_at < start or occurred_at > moment:
            continue
        counted.append(
            {
                "action": action,
                "category": category,
                "occurred_at": occurred_at,
                "seq": index,
            }
        )
    counted.sort(key=lambda item: (item["occurred_at"], item["action"], item["seq"]))
    return counted


def _reasons(counted, persona_name):
    supported = [event for event in counted if event["category"] in _SUPPORTS[persona_name]]
    supported.sort(key=lambda item: (item["occurred_at"], item["action"], item["seq"]), reverse=True)
    chosen = supported[:REASON_LIMIT]
    return [
        {
            "action": event["action"],
            "category": event["category"],
            "occurred_at": format_time(event["occurred_at"]),
        }
        for event in chosen
    ]
