"""Store the latest value of each trait. Traits have no history."""

from __future__ import annotations

from datetime import datetime, timezone

from plgkit_personas.errors import PlgkitError
from plgkit_personas.judge import format_time, parse_time, require_text
from plgkit_personas.store import get_default_db, upsert_trait


def identify(user_id, traits, *, db=None, now=None):
    """Save trait values for one user. The last value of each key wins."""
    user_id = require_text(user_id, "user_id")
    if not isinstance(traits, dict) or not traits:
        raise PlgkitError("traits must be an object of strings.")
    moment = parse_time(now) if now is not None else datetime.now(timezone.utc)
    cleaned = []
    for key, value in traits.items():
        if not isinstance(key, str) or key.strip() == "":
            raise PlgkitError("trait keys must be non-empty strings.")
        if not isinstance(value, str):
            raise PlgkitError("trait values must be strings.")
        cleaned.append((key.strip(), value))
    if db is None:
        db = get_default_db()
    try:
        for key, value in cleaned:
            upsert_trait(db, user_id, key, value, format_time(moment))
    except PlgkitError:
        raise
    except Exception as exc:
        raise PlgkitError("Could not store traits. Run plgkit-personas migrate.") from exc
