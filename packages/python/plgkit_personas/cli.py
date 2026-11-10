"""`plgkit-personas migrate` and `plgkit-personas calculate`."""

import sys

from plgkit_personas.calculate import calculate
from plgkit_personas.errors import PlgkitError
from plgkit_personas.store import migrate


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        _usage()
        raise SystemExit(0 if args else 1)
    if args[0] == "migrate":
        if len(args) != 1:
            _usage()
            raise SystemExit(1)
        _migrate()
    if args[0] == "calculate":
        _calculate(args[1:])
    print(f"Unknown command: {args[0]}", file=sys.stderr)
    _usage()
    raise SystemExit(1)


def _usage():
    print("Usage: plgkit-personas migrate", file=sys.stderr)
    print("       plgkit-personas calculate [--user ID] [--now TIMESTAMP]", file=sys.stderr)


def _migrate():
    try:
        migrate()
    except PlgkitError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    print("Migrations are up to date.")
    raise SystemExit(0)


def _calculate(args):
    user_id = None
    now = None
    index = 0
    while index < len(args):
        flag = args[index]
        if flag in ("--user", "--now") and index + 1 < len(args):
            if flag == "--user":
                user_id = args[index + 1]
            else:
                now = args[index + 1]
            index += 2
            continue
        _usage()
        raise SystemExit(1)
    try:
        result = calculate(user_id=user_id, now=now)
    except PlgkitError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    print(
        f"Calculated {result['users']} users. "
        f"{result['assigned']} assigned. "
        f"{result['unmatched']} unmatched."
    )
    raise SystemExit(0)
