"""Match one user against the personas in personas.yml. No database."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from plgkit_personas.errors import PlgkitError
from plgkit_personas.rules import normalize_rules

REASON_LIMIT = 5


def judge(user_id, events, traits=None, rules=None, *, now=None):
    """Return the winning persona for one user at `now`.

    `events` is a list of `{action, occurred_at}`. `traits` is `{key: value}`.
    `rules` is the personas.yml object. The winner is the matching persona
    with the lowest priority. No match leaves `persona` empty.
    """
    user_id = require_text(user_id, "user_id")
    moment = parse_time(now) if now is not None else datetime.now(timezone.utc)
    rules = normalize_rules(rules if rules is not None else {"groups": {}, "personas": []})
    stored_traits = _traits(traits)
    prepared = _prepare_events(events)
    ordered = sorted(rules["personas"], key=lambda item: (item["priority"], item["order"]))
    matched = []
    winner = None
    for persona in ordered:
        if _matches(persona, prepared, stored_traits, moment):
            matched.append(persona["name"])
            if winner is None:
                winner = persona
    return {
        "user_id": user_id,
        "persona": "" if winner is None else winner["name"],
        "matched": matched,
        "reasons": [] if winner is None else _reasons(winner, prepared, stored_traits, moment),
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


def _matches(persona, events, traits, moment):
    for condition in persona["require_all"]:
        if not _holds(condition, events, traits, moment):
            return False
    if persona["require_one_of"]:
        if not any(_holds(condition, events, traits, moment) for condition in persona["require_one_of"]):
            return False
    for condition in persona["exclude"]:
        if _holds(condition, events, traits, moment):
            return False
    return True


def _holds(condition, events, traits, moment):
    if condition["kind"] == "trait":
        return traits.get(condition["key"]) == condition["equals"]
    matched = _counted(condition, events, moment)
    count = len(matched)
    if count < condition["at_least"]:
        return False
    if condition["at_most"] is not None and count > condition["at_most"]:
        return False
    return True


def _counted(condition, events, moment):
    start = moment - timedelta(days=condition["within_days"])
    actions = set(condition["actions"])
    return [
        event
        for event in events
        if event["action"] in actions and start <= event["occurred_at"] <= moment
    ]


def _reasons(persona, events, traits, moment):
    supporting = []
    for condition in list(persona["require_all"]) + list(persona["require_one_of"]):
        if _holds(condition, events, traits, moment):
            supporting.append(condition)
    seen = set()
    chosen = []
    for condition in supporting:
        if condition["kind"] != "count":
            continue
        for event in _counted(condition, events, moment):
            key = (event["occurred_at"], event["action"], event["seq"])
            if key in seen:
                continue
            seen.add(key)
            chosen.append(event)
    chosen.sort(key=lambda item: (item["occurred_at"], item["action"], item["seq"]), reverse=True)
    reasons = [
        {
            "kind": "event",
            "action": event["action"],
            "occurred_at": format_time(event["occurred_at"]),
        }
        for event in chosen
    ]
    for condition in supporting:
        if condition["kind"] == "trait":
            reasons.append(
                {"kind": "trait", "key": condition["key"], "equals": condition["equals"]}
            )
    return reasons[:REASON_LIMIT]


def _prepare_events(events):
    if events is None:
        events = []
    if not isinstance(events, list):
        raise PlgkitError("events must be a list.")
    prepared = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise PlgkitError("each event must be an object.")
        action = event.get("action")
        if not isinstance(action, str) or action.strip() == "":
            raise PlgkitError("each event needs an action.")
        prepared.append(
            {
                "action": action.strip(),
                "occurred_at": parse_time(event.get("occurred_at")),
                "seq": index,
            }
        )
    return prepared


def _traits(traits):
    if traits is None:
        return {}
    if not isinstance(traits, dict):
        raise PlgkitError("traits must be an object of strings.")
    cleaned = {}
    for key, value in traits.items():
        if not isinstance(key, str) or key.strip() == "":
            raise PlgkitError("trait keys must be non-empty strings.")
        if not isinstance(value, str):
            raise PlgkitError("trait values must be strings.")
        cleaned[key.strip()] = value
    return cleaned
