"""Save one product event."""

from __future__ import annotations

import json

from plgkit_personas.errors import PlgkitError
from plgkit_personas.judge import format_time, parse_time, require_text
from plgkit_personas.store import get_default_db, insert_event


def track(user_id, action, metadata=None, *, db=None, now=None):
    """Store one event. Return false when `event_id` was already stored."""
    user_id = require_text(user_id, "user_id")
    action = require_text(action, "action")
    received = parse_time(now) if now is not None else _now()
    body, event_id, occurred = _metadata(metadata, received)
    if db is None:
        db = get_default_db()
    try:
        return insert_event(
            db,
            user_id,
            action,
            event_id,
            body,
            format_time(occurred),
            format_time(received),
        )
    except PlgkitError:
        raise
    except Exception as exc:
        raise PlgkitError("Could not store the event. Run plgkit-personas migrate.") from exc


def _metadata(metadata, received):
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise PlgkitError("metadata must be an object.")
    try:
        encoded = json.dumps(
            metadata,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise PlgkitError("metadata must be JSON.") from exc
    body = json.loads(encoded)
    occurred_at = body.pop("occurred_at", None)
    event_id = body.pop("event_id", None)
    if occurred_at is None:
        occurred = received
    else:
        if not isinstance(occurred_at, str):
            raise PlgkitError("occurred_at must be an ISO-8601 timestamp with a timezone.")
        occurred = parse_time(occurred_at)
    if event_id is None:
        return body, None, occurred
    if not isinstance(event_id, str):
        raise PlgkitError("event_id must be a string.")
    event_id = event_id.strip()
    if event_id == "":
        return body, None, occurred
    return body, event_id, occurred


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
