"""Policy numbers from plgkit/personas/config.yml."""

from __future__ import annotations

from pathlib import Path

from plgkit_personas.errors import PlgkitError
from plgkit_personas.flat import read_flat

DEFAULT_POLICY = {
    "lookback_days": 14,
    "silence_days": 7,
    "champion_min": 1,
    "power_user_min": 8,
    "implementer_min": 2,
}

POLICY_KEYS = tuple(DEFAULT_POLICY)
_FILE_KEYS = POLICY_KEYS + ("database_url_env",)


def default_config_path():
    candidate = Path.cwd() / "plgkit" / "personas" / "config.yml"
    if candidate.is_file():
        return candidate
    return None


def load_policy(path=None):
    """Return the five policy numbers. A missing file uses the defaults."""
    if path is None:
        path = default_config_path()
    if path is None:
        return normalize_policy(None)
    raw = read_flat(path)
    unknown = [key for key in raw if key not in _FILE_KEYS]
    if unknown:
        names = ", ".join(sorted(unknown))
        raise PlgkitError(f"Unknown config key: {names}.")
    values = {}
    for key in POLICY_KEYS:
        if key in raw:
            values[key] = raw[key]
    return normalize_policy(values)


def normalize_policy(policy):
    """Fill defaults and reject a window where quiet can never be seen."""
    merged = dict(DEFAULT_POLICY)
    if policy is None:
        policy = {}
    if not isinstance(policy, dict):
        raise PlgkitError("config must be an object of policy numbers.")
    unknown = [key for key in policy if key not in DEFAULT_POLICY]
    if unknown:
        names = ", ".join(sorted(str(key) for key in unknown))
        raise PlgkitError(f"Unknown config key: {names}.")
    for key in POLICY_KEYS:
        if key in policy:
            merged[key] = _positive_int(key, policy[key])
    if merged["silence_days"] >= merged["lookback_days"]:
        raise PlgkitError("silence_days must be smaller than lookback_days.")
    return merged


def _positive_int(key, value):
    if isinstance(value, str):
        if not value.isdigit():
            raise PlgkitError(f"{key} must be a whole number of 1 or more.")
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int):
        raise PlgkitError(f"{key} must be a whole number of 1 or more.")
    if value < 1:
        raise PlgkitError(f"{key} must be a whole number of 1 or more.")
    return value
