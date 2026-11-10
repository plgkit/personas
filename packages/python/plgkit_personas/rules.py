"""Personas you define, and the conditions that match them."""

from __future__ import annotations

from pathlib import Path

from plgkit_personas.errors import PlgkitError
from plgkit_personas.yaml import parse_yaml

_PERSONA_KEYS = {"name", "priority", "require_all", "require_one_of", "exclude"}
_COUNT_KEYS = {"action", "actions", "group", "at_least", "at_most", "within_days"}
_TRAIT_KEYS = {"key", "equals"}


def default_rules_path():
    candidate = Path.cwd() / "plgkit" / "personas" / "personas.yml"
    if candidate.is_file():
        return candidate
    return None


def load_rules(path=None):
    """Read personas.yml. A missing file defines no personas."""
    if path is None:
        path = default_rules_path()
    if path is None:
        return normalize_rules({"groups": {}, "personas": []})
    text = Path(path).read_text(encoding="utf-8")
    try:
        raw = parse_yaml(text)
    except PlgkitError:
        raise
    except OSError as exc:
        raise PlgkitError("Could not read personas.yml.") from exc
    return normalize_rules(raw)


def normalize_rules(raw):
    """Check the file shape and fill omitted audience lists."""
    if _already_normalized(raw):
        return raw
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise PlgkitError("personas.yml must be a mapping.")
    unknown = [key for key in raw if key not in ("groups", "personas")]
    if unknown:
        names = ", ".join(sorted(str(key) for key in unknown))
        raise PlgkitError(f"Unknown rules key: {names}.")
    groups = _groups(raw.get("groups"))
    personas_raw = raw.get("personas", [])
    if personas_raw is None:
        personas_raw = []
    if not isinstance(personas_raw, list):
        raise PlgkitError("personas must be a list.")
    names = set()
    personas = []
    for index, item in enumerate(personas_raw):
        persona = _persona(item, groups)
        if persona["name"] in names:
            raise PlgkitError(f"Duplicate persona: {persona['name']}.")
        names.add(persona["name"])
        persona["order"] = index
        personas.append(persona)
    return {"groups": groups, "personas": personas}


def _already_normalized(raw):
    if not isinstance(raw, dict):
        return False
    personas = raw.get("personas")
    if not isinstance(personas, list) or not personas:
        return False
    first = personas[0]
    return isinstance(first, dict) and "order" in first


def _groups(raw):
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise PlgkitError("groups must be a mapping of name to actions.")
    groups = {}
    for name, actions in raw.items():
        if not isinstance(name, str) or name.strip() == "":
            raise PlgkitError("group names must be non-empty strings.")
        name = name.strip()
        if not isinstance(actions, list) or not actions:
            raise PlgkitError(f"{name} needs a list of actions.")
        cleaned = []
        for action in actions:
            if not isinstance(action, str) or action.strip() == "":
                raise PlgkitError(f"{name} actions must be non-empty strings.")
            cleaned.append(action.strip())
        groups[name] = cleaned
    return groups


def _persona(item, groups):
    if not isinstance(item, dict):
        raise PlgkitError("each persona must be a mapping.")
    unknown = [key for key in item if key not in _PERSONA_KEYS]
    if unknown:
        names = ", ".join(sorted(str(key) for key in unknown))
        raise PlgkitError(f"Unknown persona key: {names}.")
    name = item.get("name")
    if not isinstance(name, str) or name.strip() == "":
        raise PlgkitError("persona name is required.")
    if "priority" not in item:
        raise PlgkitError(f"{name} needs a priority.")
    return {
        "name": name.strip(),
        "priority": _whole_number("priority", item.get("priority"), minimum=None),
        "require_all": _conditions(item.get("require_all"), "require_all", groups, name),
        "require_one_of": _conditions(item.get("require_one_of"), "require_one_of", groups, name),
        "exclude": _conditions(item.get("exclude"), "exclude", groups, name),
    }


def _conditions(raw, field, groups, persona_name):
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise PlgkitError(f"{persona_name} {field} must be a list.")
    return [_condition(item, groups, persona_name) for item in raw]


def _condition(item, groups, persona_name):
    if not isinstance(item, dict) or len(item) != 1:
        raise PlgkitError(f"{persona_name} conditions must be a count or a trait.")
    kind, body = next(iter(item.items()))
    if kind == "count":
        return _count(body, groups, persona_name)
    if kind == "trait":
        return _trait(body, persona_name)
    raise PlgkitError(f"{persona_name} conditions must be a count or a trait.")


def _count(body, groups, persona_name):
    if not isinstance(body, dict):
        raise PlgkitError(f"{persona_name} count must be a mapping.")
    unknown = [key for key in body if key not in _COUNT_KEYS]
    if unknown:
        names = ", ".join(sorted(str(key) for key in unknown))
        raise PlgkitError(f"Unknown count key: {names}.")
    choices = [key for key in ("action", "actions", "group") if key in body and body.get(key) is not None]
    if len(choices) != 1:
        raise PlgkitError(f"{persona_name} count needs one of action, actions, or group.")
    if "action" in choices:
        action = body.get("action")
        if not isinstance(action, str) or action.strip() == "":
            raise PlgkitError(f"{persona_name} action must be a non-empty string.")
        actions = [action.strip()]
    elif "actions" in choices:
        actions = body.get("actions")
        if not isinstance(actions, list) or not actions:
            raise PlgkitError(f"{persona_name} actions must be a list.")
        cleaned = []
        for action in actions:
            if not isinstance(action, str) or action.strip() == "":
                raise PlgkitError(f"{persona_name} actions must be non-empty strings.")
            cleaned.append(action.strip())
        actions = cleaned
    else:
        group = body.get("group")
        if not isinstance(group, str) or group.strip() == "":
            raise PlgkitError(f"{persona_name} group must be a non-empty string.")
        group = group.strip()
        if group not in groups:
            raise PlgkitError(f"Unknown group: {group}.")
        actions = list(groups[group])
    if "at_least" not in body:
        raise PlgkitError(f"{persona_name} count needs at_least.")
    at_least = _whole_number("at_least", body.get("at_least"), minimum=0)
    at_most = None
    if "at_most" in body and body.get("at_most") is not None:
        at_most = _whole_number("at_most", body.get("at_most"), minimum=0)
        if at_most < at_least:
            raise PlgkitError("at_most must be at least at_least.")
    if "within_days" not in body:
        raise PlgkitError(f"{persona_name} count needs within_days.")
    return {
        "kind": "count",
        "actions": actions,
        "at_least": at_least,
        "at_most": at_most,
        "within_days": _whole_number("within_days", body.get("within_days"), minimum=1),
    }


def _trait(body, persona_name):
    if not isinstance(body, dict):
        raise PlgkitError(f"{persona_name} trait must be a mapping.")
    unknown = [key for key in body if key not in _TRAIT_KEYS]
    if unknown:
        names = ", ".join(sorted(str(key) for key in unknown))
        raise PlgkitError(f"Unknown trait key: {names}.")
    key = body.get("key")
    if not isinstance(key, str) or key.strip() == "":
        raise PlgkitError(f"{persona_name} trait key is required.")
    if "equals" not in body or not isinstance(body.get("equals"), str):
        raise PlgkitError(f"{persona_name} trait equals must be a string.")
    return {"kind": "trait", "key": key.strip(), "equals": body.get("equals")}


def _whole_number(name, value, minimum):
    if isinstance(value, str) and _digits(value):
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int):
        raise PlgkitError(f"{name} must be a whole number.")
    if minimum is not None and value < minimum:
        if minimum == 1:
            raise PlgkitError(f"{name} must be a whole number of 1 or more.")
        raise PlgkitError(f"{name} must be a whole number of 0 or more.")
    return value


def _digits(value):
    if value.startswith("-"):
        return value[1:].isdigit() and value != "-"
    return value.isdigit()
