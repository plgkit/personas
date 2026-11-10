"""Judge every known user and store the winner."""

from __future__ import annotations

from datetime import datetime, timezone

from plgkit_personas.errors import PlgkitError
from plgkit_personas.judge import format_time, judge, parse_time, require_text
from plgkit_personas.rules import load_rules, normalize_rules
from plgkit_personas.store import (
    get_default_db,
    list_events,
    list_traits,
    list_user_ids,
    write_snapshot,
)


def calculate(*, db=None, now=None, user_id=None, rules=None, rules_path=None):
    """Write a snapshot for each user who has events or traits.

    Pass `user_id` to refresh one person, including someone with no rows yet.
    Returns counts of users, assigned personas, and unmatched users.
    """
    if db is None:
        db = get_default_db()
    if rules is None:
        rules = load_rules(rules_path)
    else:
        rules = normalize_rules(rules)
    moment = parse_time(now) if now is not None else datetime.now(timezone.utc)
    stamp = format_time(moment)
    if user_id is None:
        try:
            user_ids = list_user_ids(db)
        except Exception as exc:
            raise PlgkitError("Could not calculate personas. Run plgkit-personas migrate.") from exc
    else:
        user_ids = [require_text(user_id, "user_id")]
    assigned = 0
    for current in user_ids:
        try:
            events = list_events(db, current)
            traits = list_traits(db, current)
        except PlgkitError:
            raise
        except Exception as exc:
            raise PlgkitError("Could not calculate personas. Run plgkit-personas migrate.") from exc
        result = judge(current, events, traits, rules, now=stamp)
        try:
            write_snapshot(db, result)
        except Exception as exc:
            raise PlgkitError("Could not calculate personas. Run plgkit-personas migrate.") from exc
        if result["persona"]:
            assigned += 1
    users = len(user_ids)
    return {"users": users, "assigned": assigned, "unmatched": users - assigned}
