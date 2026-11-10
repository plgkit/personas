"""Postgres checks. They run when PLGKIT_TEST_DATABASE_URL is a postgres URL."""

import os
import unittest
import uuid

from plgkit_personas import connect, migrate, persona, track

TEST_URL = os.environ.get("PLGKIT_TEST_DATABASE_URL", "").strip()
NOW = "2026-11-10T15:00:00Z"
MAPPING = {"created_doc": "core_action", "sent_invite": "invite_sent"}
POLICY = {
    "lookback_days": 14,
    "silence_days": 7,
    "champion_min": 1,
    "power_user_min": 8,
    "implementer_min": 2,
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
        migrate(db)
        migrate(db)
        self.assertTrue(
            track(user_id, "sent_invite", {"occurred_at": "2026-11-09T15:00:00Z", "event_id": user_id}, db=db, now=NOW)
        )
        self.assertFalse(
            track(user_id, "created_doc", {"occurred_at": "2026-11-09T16:00:00Z", "event_id": user_id}, db=db, now=NOW)
        )
        result = persona(user_id, db=db, now=NOW, mapping=MAPPING, config=POLICY)
        self.assertEqual(result["persona"], "champion")
        self.assertEqual(result["counts"]["invite_sent"], 1)
        self.assertEqual(result["counts"]["core_action"], 0)


if __name__ == "__main__":
    unittest.main()
