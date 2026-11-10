"""The database variable name in plgkit/personas/config.yml."""

from __future__ import annotations

from pathlib import Path

from plgkit_personas.errors import PlgkitError
from plgkit_personas.flat import read_flat

ALLOWED_KEYS = ("database_url_env",)


def default_config_path():
    candidate = Path.cwd() / "plgkit" / "personas" / "config.yml"
    if candidate.is_file():
        return candidate
    return None


def read_config(path):
    """Return the flat config. Only database_url_env is allowed."""
    raw = read_flat(path)
    unknown = [key for key in raw if key not in ALLOWED_KEYS]
    if unknown:
        names = ", ".join(sorted(unknown))
        raise PlgkitError(f"Unknown config key: {names}.")
    return raw
