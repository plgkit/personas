"""Action names to the three shared categories."""

from __future__ import annotations

from pathlib import Path

from plgkit_personas.errors import PlgkitError
from plgkit_personas.flat import read_flat

CATEGORIES = ("core_action", "invite_sent", "setup_step")


def default_mapping_path():
    candidate = Path.cwd() / "plgkit" / "personas" / "mapping.yml"
    if candidate.is_file():
        return candidate
    return None


def load_mapping(path=None):
    """Return `{action: category}`. A missing file maps nothing."""
    if path is None:
        path = default_mapping_path()
    if path is None:
        return {}
    return normalize_mapping(read_flat(path))


def normalize_mapping(mapping):
    if mapping is None:
        return {}
    if not isinstance(mapping, dict):
        raise PlgkitError("mapping must be an object of action to category.")
    cleaned = {}
    for action, category in mapping.items():
        if not isinstance(action, str) or action.strip() == "":
            raise PlgkitError("mapping actions must be non-empty strings.")
        if category not in CATEGORIES:
            names = ", ".join(CATEGORIES)
            raise PlgkitError(f"{action} maps to {category!r}. Use one of: {names}.")
        cleaned[action] = category
    return cleaned
