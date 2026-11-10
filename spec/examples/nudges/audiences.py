"""Audience checks a nudge can call.

Copy this file to plgkit/nudges/audiences.py. Each function calls persona_is
with the persona name from personas.yml. Add one function when you add a message.

    from audiences import audiences
    decide("home", {"user": {"id": user_id}}, messages, audiences=audiences)
"""

from plgkit_personas import persona_is


def bind(db=None):
    """Return the checks for the sample messages. Pass db when the database is pinned."""

    def check(name):
        def audience(ctx):
            user_id = _user_id(ctx)
            if user_id == "":
                return False
            return persona_is(user_id, name, db=db)

        return audience

    return {
        "persona_is_blocked": check("blocked"),
        "persona_is_champion": check("champion"),
    }


# The default database. This is what an app passes to decide().
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
