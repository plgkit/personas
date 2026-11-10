"""Postgres checks. They run when PLGKIT_TEST_DATABASE_URL is a postgres URL."""

import os
import unittest
import uuid

from plgkit_personas import calculate, connect, migrate, persona, track

TEST_URL = os.environ.get("PLGKIT_TEST_DATABASE_URL", "").strip()
NOW = "2026-11-10T15:00:00Z"
RULES = {
    "personas": [
        {
            "name": "champion",
            "priority": 1,
            "require_all": [
                {"count": {"action": "sent_invite", "at_least": 1, "within_days": 14}}
            ],
        }
    ]
}


def _postgres_url():
    return TEST_URL.startswith("postgres://") or TEST_URL.startswith("postgresql://")


@unittest.skipUnless(_postgres_url(), "set PLGKIT_TEST_DATABASE_URL to a postgres URL")
class PostgresTests(unittest.TestCase):
    def test_track_and_persona(self):
        user_id = "pg-" + uuid.uuid4().hex
        db = connect(TEST_URL)
        self.addCleanup(db.close)
        self.addCleanup(
            lambda: db.execute("DELETE FROM plgkit_persona_events WHERE user_id = ?", (user_id,))
        )
        self.addCleanup(
            lambda: db.execute("DELETE FROM plgkit_persona_snapshots WHERE user_id = ?", (user_id,))
        )
        migrate(db)
        migrate(db)
        self.assertTrue(
            track(user_id, "sent_invite", {"occurred_at": "2026-11-09T15:00:00Z", "event_id": user_id}, db=db, now=NOW)
        )
        self.assertFalse(
            track(user_id, "created_doc", {"occurred_at": "2026-11-09T16:00:00Z", "event_id": user_id}, db=db, now=NOW)
        )
        calculate(db=db, now=NOW, user_id=user_id, rules=RULES)
        result = persona(user_id, db=db)
        self.assertEqual(result["persona"], "champion")
        self.assertEqual(result["reasons"][0]["action"], "sent_invite")


if __name__ == "__main__":
    unittest.main()
