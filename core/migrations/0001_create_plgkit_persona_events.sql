-- Product events used to judge a persona.
-- Rows are only added. Later changes get a new numbered file; `plgkit-personas migrate` applies new files.
-- This file runs on SQLite and Postgres. metadata is JSON stored as text.
-- occurred_at and received_at are UTC, stored as text.
-- event_id is optional. The same user_id and event_id is stored once.
-- A missing event_id is stored as NULL. Many rows may omit it.

CREATE TABLE IF NOT EXISTS plgkit_persona_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    event_id TEXT,
    metadata TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    received_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS plgkit_persona_events_user_time
    ON plgkit_persona_events (user_id, occurred_at);

CREATE UNIQUE INDEX IF NOT EXISTS plgkit_persona_events_user_event
    ON plgkit_persona_events (user_id, event_id);
