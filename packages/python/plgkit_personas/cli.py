"""`plgkit-personas migrate` creates the persona events table."""

import sys

from plgkit_personas.errors import PlgkitError
from plgkit_personas.store import migrate


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        _usage()
        raise SystemExit(0 if args else 1)
    if args[0] == "migrate":
        _migrate()
    else:
        print(f"Unknown command: {args[0]}", file=sys.stderr)
        _usage()
        raise SystemExit(1)


def _usage():
    print("Usage: plgkit-personas migrate", file=sys.stderr)


def _migrate():
    try:
        migrate()
    except PlgkitError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    print("Migrations are up to date.")
    raise SystemExit(0)
