"""Load one user's events and judge them."""

from __future__ import annotations

from plgkit_personas.config import load_policy
from plgkit_personas.judge import judge, require_text
from plgkit_personas.mapping import load_mapping
from plgkit_personas.store import get_default_db, list_events


def persona(
    user_id,
    *,
    db=None,
    now=None,
    mapping=None,
    config=None,
    mapping_path=None,
    config_path=None,
):
    """Return the persona object for one user."""
    user_id = require_text(user_id, "user_id")
    if db is None:
        db = get_default_db()
    if mapping is None:
        mapping = load_mapping(mapping_path)
    if config is None:
        config = load_policy(config_path)
    events = list_events(db, user_id)
    return judge(user_id, events, mapping=mapping, policy=config, now=now)
