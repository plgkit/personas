"""Read a flat `key: value` file. Indentation is rejected."""

from __future__ import annotations

from pathlib import Path

from plgkit_personas.errors import PlgkitError


def read_flat(path):
    """Return `{key: value}` for one flat file. Values stay strings."""
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PlgkitError(f"Could not read {file_path}.") from exc
    found = {}
    for raw in text.splitlines():
        if raw.startswith((" ", "\t")):
            if raw.strip():
                raise PlgkitError(f"{file_path} must be a flat key: value file.")
            continue
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            raise PlgkitError(f"{file_path} must be a flat key: value file.")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key == "":
            raise PlgkitError(f"{file_path} has an empty key.")
        if value == "":
            raise PlgkitError(f"{key} in {file_path} needs a value.")
        if key in found:
            raise PlgkitError(f"{key} is set more than once in {file_path}.")
        found[key] = value
    return found
