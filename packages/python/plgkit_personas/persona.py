"""Read the persona row written by calculate."""

from __future__ import annotations

from plgkit_personas.errors import PlgkitError
from plgkit_personas.judge import require_text
from plgkit_personas.store import get_default_db, read_snapshot


def persona(user_id, *, db=None):
    """Return the stored persona. An empty label means calculate has not run, or no rule matched."""
    user_id = require_text(user_id, "user_id")
    if db is None:
        db = get_default_db()
    try:
        row = read_snapshot(db, user_id)
    except PlgkitError:
        raise
    except Exception as exc:
        raise PlgkitError("Could not read the persona. Run plgkit-personas migrate.") from exc
    if row is None:
        return {
            "user_id": user_id,
            "persona": "",
            "matched": [],
            "reasons": [],
            "calculated_at": "",
        }
    return row


def persona_is(user_id, name, *, db=None):
    """True when the stored winner is `name`."""
    name = require_text(name, "persona")
    return persona(user_id, db=db)["persona"] == name
