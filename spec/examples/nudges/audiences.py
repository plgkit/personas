"""Audience checks a nudge can call.

Copy this file to plgkit/nudges/audiences.py. A message lists one of these
names under audience.require_all. persona() reads the events you already stored
with track(). The other four labels match neither function, so those users get
no line from these two messages.

    from audiences import audiences
    decide("home", {"user": {"id": user_id}}, messages, audiences=audiences)
"""

from pathlib import Path

from plgkit_personas import load_mapping, load_policy, persona


def bind(db=None, now=None, mapping=None, policy=None):
    """Return the two checks. Pass db and now when the clock or database is pinned."""

    def label(ctx):
        user_id = _user_id(ctx)
        if user_id == "":
            return "unknown"
        chosen_mapping = mapping
        chosen_policy = policy
        if chosen_mapping is None or chosen_policy is None:
            found_mapping, found_policy = _from_files()
            if chosen_mapping is None:
                chosen_mapping = found_mapping
            if chosen_policy is None:
                chosen_policy = found_policy
        result = persona(
            user_id,
            db=db,
            now=now,
            mapping=chosen_mapping,
            config=chosen_policy,
        )
        return result["persona"]

    return {
        "persona_is_blocked": lambda ctx: label(ctx) == "blocked",
        "persona_is_champion": lambda ctx: label(ctx) == "champion",
    }


# Live clock and the default database. This is what an app passes to decide().
audiences = bind()


def _user_id(ctx):
    if isinstance(ctx, dict):
        user = ctx.get("user")
    else:
        user = getattr(ctx, "user", None)
    if isinstance(user, dict):
        value = user.get("id", "")
    else:
        value = getattr(user, "id", "")
    if not isinstance(value, str):
        return ""
    return value


def _from_files():
    app = Path.cwd() / "plgkit" / "personas"
    sample = Path(__file__).resolve().parents[1]
    mapping_path = _first(app / "mapping.yml", sample / "mapping.yml")
    config_path = _first(app / "config.yml", sample / "config.yml")
    mapping = load_mapping(mapping_path) if mapping_path is not None else None
    policy = load_policy(config_path) if config_path is not None else None
    return mapping, policy


def _first(*paths):
    for path in paths:
        if path.is_file():
            return path
    return None
