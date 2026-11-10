"""Open the database, run migrations, and read persona events.

The database address lives in an environment variable named by
`database_url_env` in config.yml. The address can contain a password, so it
is never written into config. A `postgres://` or `postgresql://` address uses
Postgres. If that variable is unset, we use a SQLite file,
`plgkit_events.sqlite`, in the current directory.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import threading
import uuid
from importlib.resources import files as resource_files
from pathlib import Path

from plgkit_personas.config import read_config
from plgkit_personas.errors import PlgkitError

DEFAULT_DATABASE_URL_ENV = "PLGKIT_DATABASE_URL"
DEFAULT_DATABASE_URL = "sqlite:///plgkit_events.sqlite"
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MIGRATION_NAME = re.compile(r"^(\d+)_.+\.sql$")

_lock = threading.RLock()
_default_db = None
_warned_default = False


def resolve_database_url(config_path=None, environ=None):
    """Return `(url, used_default)`.

    `used_default` is true when the env var was unset and the URL is the
    local SQLite file. SQLite and Postgres URLs are accepted. Other schemes
    raise PlgkitError. The error text never includes the URL, because it can
    contain a password.
    """
    env = os.environ if environ is None else environ
    name = _env_var_name(config_path)
    value = env.get(name, "")
    if not isinstance(value, str):
        value = ""
    value = value.strip()
    if not value:
        return DEFAULT_DATABASE_URL, True
    scheme = _scheme(value)
    if scheme in ("sqlite", "postgres", "postgresql"):
        return value, False
    raise PlgkitError(
        f"{name} uses the {scheme!r} scheme. "
        "plgkit-personas supports SQLite (sqlite:///plgkit_events.sqlite) and Postgres "
        "(postgres:// or postgresql://). "
        "Unset the variable to use the local SQLite file."
    )


def connect(url=None):
    """Open SQLite or Postgres. `url=None` reads config and the environment."""
    if url is None:
        url, used_default = resolve_database_url()
        if used_default:
            _warn_default(_env_var_name(None))
    scheme = _scheme(url)
    if scheme == "sqlite":
        return _connect_sqlite(url)
    if scheme in ("postgres", "postgresql"):
        return _connect_postgres(url)
    raise PlgkitError(
        f"Unsupported database scheme {scheme!r}. "
        "Use a SQLite URL or a Postgres URL (postgres:// or postgresql://)."
    )


def migrate(db=None, migrations_dir=None):
    """Create the persona events table. Safe to run again."""
    if db is None:
        db = get_default_db()
    sources = _migration_sources(migrations_dir)
    with _lock:
        db.execute(
            "CREATE TABLE IF NOT EXISTS plgkit_persona_schema_migrations "
            "(version TEXT PRIMARY KEY)"
        )
        applied = {
            row[0]
            for row in db.execute("SELECT version FROM plgkit_persona_schema_migrations")
        }
        for version, text in sources:
            if version in applied:
                continue
            statements = _sql_statements(text)
            db.execute("BEGIN")
            try:
                for statement in statements:
                    db.execute(statement)
                db.execute(
                    "INSERT INTO plgkit_persona_schema_migrations (version) VALUES (?)",
                    (version,),
                )
                db.execute("COMMIT")
            except Exception:
                try:
                    db.execute("ROLLBACK")
                except Exception:
                    pass
                raise PlgkitError(f"Migration {version} failed.")
    return db


def get_default_db():
    global _default_db
    with _lock:
        if _default_db is None:
            _default_db = connect(None)
        return _default_db


def set_default_db(db):
    """Tests and apps can pin the connection `track` and `persona` use."""
    global _default_db
    with _lock:
        _default_db = db


def insert_event(db, user_id, action, event_id, metadata, occurred_at, received_at):
    """Insert one row. Return false when this user already stored `event_id`."""
    with _lock:
        try:
            db.execute(
                "INSERT INTO plgkit_persona_events "
                "(id, user_id, action, event_id, metadata, occurred_at, received_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    user_id,
                    action,
                    event_id,
                    json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    occurred_at,
                    received_at,
                ),
            )
        except Exception as exc:
            if _is_unique_violation(exc):
                return False
            raise
        return True


def list_events(db, user_id):
    """Return stored events for one user, oldest first."""
    with _lock:
        try:
            rows = db.execute(
                "SELECT action, occurred_at FROM plgkit_persona_events "
                "WHERE user_id = ? ORDER BY occurred_at ASC, id ASC",
                (user_id,),
            ).fetchall()
        except Exception as exc:
            raise PlgkitError(
                "Could not read persona events. Run plgkit-personas migrate."
            ) from exc
    return [{"action": action, "occurred_at": occurred_at} for action, occurred_at in rows]


def upsert_trait(db, user_id, key, value, updated_at):
    with _lock:
        db.execute(
            "INSERT INTO plgkit_persona_traits (user_id, key, value, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, "
            "updated_at = excluded.updated_at",
            (user_id, key, value, updated_at),
        )


def list_traits(db, user_id):
    with _lock:
        rows = db.execute(
            "SELECT key, value FROM plgkit_persona_traits WHERE user_id = ? ORDER BY key ASC",
            (user_id,),
        ).fetchall()
    return {key: value for key, value in rows}


def list_user_ids(db):
    with _lock:
        rows = db.execute(
            "SELECT user_id FROM plgkit_persona_events "
            "UNION SELECT user_id FROM plgkit_persona_traits "
            "ORDER BY user_id ASC"
        ).fetchall()
    return [row[0] for row in rows]


def write_snapshot(db, result):
    payload = (
        result["user_id"],
        result["persona"],
        json.dumps(result["matched"], ensure_ascii=False, separators=(",", ":")),
        json.dumps(result["reasons"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        result["calculated_at"],
    )
    with _lock:
        db.execute(
            "INSERT INTO plgkit_persona_snapshots "
            "(user_id, persona, matched, reasons, calculated_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "persona = excluded.persona, matched = excluded.matched, "
            "reasons = excluded.reasons, calculated_at = excluded.calculated_at",
            payload,
        )


def read_snapshot(db, user_id):
    with _lock:
        row = db.execute(
            "SELECT user_id, persona, matched, reasons, calculated_at "
            "FROM plgkit_persona_snapshots WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "user_id": row[0],
        "persona": row[1],
        "matched": json.loads(row[2]),
        "reasons": json.loads(row[3]),
        "calculated_at": row[4],
    }


def _connect_sqlite(url):
    path = _sqlite_path(url)
    try:
        conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    except sqlite3.Error as exc:
        raise PlgkitError("Could not open the database.") from exc
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _connect_postgres(url):
    try:
        import psycopg
    except ImportError as exc:
        raise PlgkitError(
            "Postgres needs the psycopg package. Install it with: pip install psycopg"
        ) from exc
    try:
        conn = psycopg.connect(url, autocommit=True, connect_timeout=5)
    except Exception as exc:
        raise PlgkitError("Could not open the database.") from exc
    return _PostgresDB(conn)


class _PostgresDB:
    """Same execute() shape as sqlite3, with Postgres placeholders."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        if params:
            return self._conn.execute(sql.replace("?", "%s"), params)
        return self._conn.execute(sql)

    def close(self):
        self._conn.close()


def _env_var_name(config_path):
    path = config_path
    if path is None:
        path = default_config_file()
    if path is None:
        return DEFAULT_DATABASE_URL_ENV
    try:
        raw = read_config(path)
    except PlgkitError:
        raise
    name = raw.get("database_url_env", DEFAULT_DATABASE_URL_ENV)
    if not _ENV_NAME.fullmatch(name):
        raise PlgkitError(
            "database_url_env in config.yml must be the name of an environment "
            "variable, not the database address. The address can contain a "
            "password, so put it in the environment. "
            "Example: database_url_env: PLGKIT_DATABASE_URL"
        )
    return name


def default_config_file():
    candidate = Path.cwd() / "plgkit" / "personas" / "config.yml"
    if candidate.is_file():
        return candidate
    return None


def _scheme(url):
    if not isinstance(url, str) or not url:
        return "unknown"
    if url.startswith("sqlite:"):
        return "sqlite"
    if "://" in url:
        return url.split("://", 1)[0].lower()
    return "unknown"


def _sqlite_path(url):
    if not isinstance(url, str) or not url.startswith("sqlite:"):
        raise PlgkitError(
            "The SQLite URL must look like sqlite:///plgkit_events.sqlite "
            "or sqlite:///:memory:."
        )
    if url in ("sqlite:///:memory:", "sqlite::memory:"):
        return ":memory:"
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise PlgkitError(
            "The SQLite URL must look like sqlite:///plgkit_events.sqlite "
            "or sqlite:///:memory:."
        )
    return url[len(prefix):]


def _migration_sources(migrations_dir):
    directory = migrations_dir
    if directory is None:
        directory = os.environ.get("PLGKIT_PERSONA_MIGRATIONS_DIR", "").strip() or None
    if directory:
        return [
            (version, path.read_text(encoding="utf-8"))
            for version, path in _migration_files(Path(directory))
        ]
    root = resource_files("plgkit_personas").joinpath("migrations")
    found = []
    try:
        entries = list(root.iterdir())
    except FileNotFoundError as exc:
        raise PlgkitError(
            "The plgkit_personas package is missing its migration files. Rebuild the package."
        ) from exc
    for item in entries:
        match = _MIGRATION_NAME.match(item.name)
        if not match:
            continue
        found.append((match.group(1), item.read_text(encoding="utf-8")))
    found.sort(key=lambda item: int(item[0]))
    if not found:
        raise PlgkitError(
            "The plgkit_personas package is missing its migration files. Rebuild the package."
        )
    return found


def _migration_files(directory):
    if not directory.is_dir():
        raise PlgkitError(f"Migrations folder does not exist: {directory}")
    found = []
    for path in directory.glob("*.sql"):
        match = _MIGRATION_NAME.match(path.name)
        if match:
            found.append((match.group(1), path))
    found.sort(key=lambda item: int(item[0]))
    if not found:
        raise PlgkitError(f"No migration files in {directory}.")
    return found


def _sql_statements(text):
    lines = []
    for line in text.splitlines():
        if "--" in line:
            line = line[: line.index("--")]
        lines.append(line)
    return [part.strip() for part in "\n".join(lines).split(";") if part.strip()]


def _is_unique_violation(exc):
    if isinstance(exc, sqlite3.IntegrityError):
        return "unique" in str(exc).lower()
    return type(exc).__name__ == "UniqueViolation"


def _warn_default(name):
    global _warned_default
    with _lock:
        if _warned_default:
            return
        _warned_default = True
    print(
        f"{name} is unset. Using a SQLite file at plgkit_events.sqlite "
        "in the current directory.",
        file=sys.stderr,
    )
