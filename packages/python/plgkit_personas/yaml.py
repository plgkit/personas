"""Read the small YAML shape used by personas.yml.

Maps, lists, nested maps, flow lists, and plain scalars. Full-line comments
are ignored. A repeated key is an error.
"""

from plgkit_personas.errors import PlgkitError


def parse_yaml(text):
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        lines.append(raw.replace("\t", "    "))
    if not lines:
        return {}
    value, index = _parse_block(lines, 0, 0)
    if index != len(lines):
        raise PlgkitError("Could not read personas.yml.")
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
            raise PlgkitError("Could not read personas.yml.")
        content = _content(lines[index])
        if content.startswith("- "):
            break
        key, value, index = _take_pair(lines, index, indent)
        _put(mapping, key, value)
    return mapping, index


def _parse_list(lines, index, indent):
    items = []
    while index < len(lines):
        if _indent(lines[index]) < indent:
            break
        if _indent(lines[index]) != indent:
            raise PlgkitError("Could not read personas.yml.")
        content = _content(lines[index])
        if not content.startswith("- "):
            break
        rest = content[2:].strip()
        index += 1
        if rest == "":
            if index < len(lines) and _indent(lines[index]) > indent:
                child, index = _parse_block(lines, index, _indent(lines[index]))
            else:
                child = None
            items.append(child)
            continue
        if _is_key(rest):
            key, _, raw_value = rest.partition(":")
            key = key.strip()
            raw_value = raw_value.strip()
            mapping = {}
            if raw_value == "":
                if index < len(lines) and _indent(lines[index]) > indent:
                    child, index = _parse_block(lines, index, _indent(lines[index]))
                else:
                    child = {}
                mapping[key] = child
            else:
                mapping[key] = _scalar(raw_value)
            if (
                index < len(lines)
                and _indent(lines[index]) > indent
                and not _content(lines[index]).startswith("- ")
            ):
                more, index = _parse_block(lines, index, _indent(lines[index]))
                if isinstance(more, dict):
                    for item_key, item_value in more.items():
                        _put(mapping, item_key, item_value)
            items.append(mapping)
            continue
        items.append(_scalar(rest))
    return items, index


def _take_pair(lines, index, indent):
    content = _content(lines[index])
    if not _is_key(content):
        raise PlgkitError("Could not read personas.yml.")
    key, _, raw_value = content.partition(":")
    key = key.strip()
    raw_value = raw_value.strip()
    index += 1
    if raw_value == "":
        if index < len(lines) and _indent(lines[index]) > indent:
            child, index = _parse_block(lines, index, _indent(lines[index]))
            return key, child, index
        return key, {}, index
    return key, _scalar(raw_value), index


def _put(mapping, key, value):
    if key in mapping:
        raise PlgkitError(f"Duplicate key: {key}.")
    mapping[key] = value


def _is_key(text):
    if text.startswith(("'", '"', "- ")):
        return False
    head, sep, _ = text.partition(":")
    return sep == ":" and head.strip() != ""


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _content(line):
    return line.strip()


def _scalar(value):
    flow = _flow_list(value)
    if flow is not None:
        return flow
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    if value == "true":
        return True
    if value == "false":
        return False
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    return value


def _flow_list(value):
    if not (value.startswith("[") and value.endswith("]")):
        return None
    inner = value[1:-1].strip()
    if inner == "":
        return []
    parts = []
    buf = []
    quote = ""
    for char in inner:
        if quote:
            buf.append(char)
            if char == quote:
                quote = ""
            continue
        if char in ("'", '"'):
            quote = char
            buf.append(char)
            continue
        if char == ",":
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(char)
    if quote:
        raise PlgkitError("Could not read personas.yml.")
    parts.append("".join(buf).strip())
    return [_scalar(part) for part in parts if part != ""]
