-- Latest trait values and the persona row written by calculate.
-- Traits keep the last value for each key. They have no history.
-- A snapshot is one row per user. persona is empty when no rule matches.
-- matched and reasons are JSON text.

CREATE TABLE IF NOT EXISTS plgkit_persona_traits (
    user_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
);

CREATE TABLE IF NOT EXISTS plgkit_persona_snapshots (
    user_id TEXT NOT NULL PRIMARY KEY,
    persona TEXT NOT NULL,
    matched TEXT NOT NULL,
    reasons TEXT NOT NULL,
    calculated_at TEXT NOT NULL
);
