"""Read the two sample nudge files.

The personas packages do not depend on a YAML library. These files are small,
so this reader only handles the shape we ship: nested maps, one list of names,
and plain strings.
"""

from pathlib import Path


def load_messages(directory):
    folder = Path(directory)
    return [load_message(path) for path in sorted(folder.glob("*.yml"))]


def load_message(path):
    path = Path(path)
    data = parse_yaml(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must be a mapping.")
    data["id"] = path.name[:-4] if path.name.endswith(".yml") else path.name
    return data


def parse_yaml(text):
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        lines.append(raw.replace("\t", "    "))
    value, index = _parse_block(lines, 0, 0)
    if index != len(lines):
        raise ValueError("Could not read the nudge file.")
    return value


def _parse_block(lines, index, indent):
    if index >= len(lines):
        return {}, index
    if _content(lines[index]).startswith("- "):
        return _parse_list(lines, index, indent)
    mapping = {}
    while index < len(lines):
        if _indent(lines[index]) < indent:
            break
        if _indent(lines[index]) != indent:
            raise ValueError(lines[index])
        content = _content(lines[index])
        if content.startswith("- "):
            break
        key, sep, rest = content.partition(":")
        if sep != ":" or key.strip() == "":
            raise ValueError(lines[index])
        index += 1
        rest = rest.strip()
        if rest == "":
            if index < len(lines) and _indent(lines[index]) > indent:
                child, index = _parse_block(lines, index, _indent(lines[index]))
            else:
                child = {}
            mapping[key.strip()] = child
        else:
            mapping[key.strip()] = _scalar(rest)
    return mapping, index


def _parse_list(lines, index, indent):
    items = []
    while index < len(lines):
        if _indent(lines[index]) < indent:
            break
        if _indent(lines[index]) != indent:
            raise ValueError(lines[index])
        content = _content(lines[index])
        if not content.startswith("- "):
            break
        items.append(_scalar(content[2:].strip()))
        index += 1
    return items, index


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _content(line):
    return line.strip()


def _scalar(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    if value == "true":
        return True
    if value == "false":
        return False
    if value.isdigit():
        return int(value)
    return value
