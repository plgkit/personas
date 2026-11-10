"""track() stores events. persona() reads them back."""

import json
import unittest
from pathlib import Path

from plgkit_personas import PlgkitError, connect, migrate, persona, track
from plgkit_personas.config import DEFAULT_POLICY

NOW = "2026-11-10T15:00:00Z"
MAPPING = {
    "created_doc": "core_action",
    "edited_doc": "core_action",
    "sent_invite": "invite_sent",
}


def memory_db():
    db = connect("sqlite:///:memory:")
    migrate(db)
    return db


class TrackTests(unittest.TestCase):
    def test_round_trip_matches_every_case(self):
        root = Path(__file__).resolve().parents[3]
        fixture = json.loads((root / "spec" / "fixtures" / "cases.json").read_text(encoding="utf-8"))
        for case in fixture["cases"]:
            db = memory_db()
            self.addCleanup(db.close)
            for event in case["events"]:
                stored = track(
                    case["user_id"],
                    event["action"],
                    {"occurred_at": event["occurred_at"]},
                    db=db,
                    now=case["calculated_at"],
                )
                self.assertTrue(stored, case["name"])
            result = persona(
                case["user_id"],
                db=db,
                now=case["calculated_at"],
                mapping=fixture["mapping"],
                config=fixture["config"],
            )
            self.assertEqual(result["persona"], case["persona"], case["name"])
            self.assertEqual(result["reasons"], case["reasons"], case["name"])
            self.assertEqual(result["counts"], case["counts"], case["name"])

    def test_two_users_stay_apart(self):
        db = memory_db()
        self.addCleanup(db.close)
        track("avery", "connected_slack", {"occurred_at": "2026-11-01T15:00:00Z"}, db=db, now=NOW)
        track("blake", "sent_invite", {"occurred_at": "2026-11-09T15:00:00Z"}, db=db, now=NOW)
        mapping = {"connected_slack": "setup_step", "sent_invite": "invite_sent"}
        avery = persona("avery", db=db, now=NOW, mapping=mapping, config=DEFAULT_POLICY)
        blake = persona("blake", db=db, now=NOW, mapping=mapping, config=DEFAULT_POLICY)
        self.assertEqual(avery["persona"], "blocked")
        self.assertEqual(blake["persona"], "champion")

    def test_duplicate_event_id_keeps_the_first_write(self):
        db = memory_db()
        self.addCleanup(db.close)
        first = {"occurred_at": "2026-11-09T15:00:00Z", "event_id": "once", "page": "home"}
        self.assertTrue(track("jordan", "created_doc", first, db=db, now=NOW))
        second = {"occurred_at": "2026-11-09T16:00:00Z", "event_id": "once", "page": "away"}
        self.assertFalse(track("jordan", "edited_doc", second, db=db, now=NOW))
        self.assertTrue(
            track("sam", "created_doc", {"occurred_at": "2026-11-09T15:00:00Z", "event_id": "once"}, db=db, now=NOW)
        )
        result = persona("jordan", db=db, now=NOW, mapping=MAPPING, config=DEFAULT_POLICY)
        self.assertEqual(result["counts"]["core_action"], 1)
        self.assertEqual(result["reasons"][0]["action"], "created_doc")
        self.assertEqual(result["reasons"][0]["occurred_at"], "2026-11-09T15:00:00.000000Z")
        row = db.execute("SELECT metadata FROM plgkit_persona_events WHERE user_id = ?", ("jordan",)).fetchone()
        self.assertEqual(row[0], '{"page":"home"}')

    def test_missing_occurred_at_uses_receipt_time(self):
        db = memory_db()
        self.addCleanup(db.close)
        track("jordan", "created_doc", db=db, now="2026-11-09T15:00:00Z")
        row = db.execute(
            "SELECT occurred_at, received_at FROM plgkit_persona_events"
        ).fetchone()
        self.assertEqual(row[0], "2026-11-09T15:00:00.000000Z")
        self.assertEqual(row[0], row[1])

    def test_offset_is_stored_as_utc(self):
        db = memory_db()
        self.addCleanup(db.close)
        track(
            "jordan",
            "created_doc",
            {"occurred_at": "2026-11-09T10:00:00-05:00"},
            db=db,
            now=NOW,
        )
        result = persona("jordan", db=db, now=NOW, mapping=MAPPING, config=DEFAULT_POLICY)
        self.assertEqual(result["reasons"][0]["occurred_at"], "2026-11-09T15:00:00.000000Z")

    def test_rejects_bad_calls_without_storing(self):
        db = memory_db()
        self.addCleanup(db.close)
        with self.assertRaises(PlgkitError):
            track("", "created_doc", db=db, now=NOW)
        with self.assertRaises(PlgkitError):
            track("jordan", "", db=db, now=NOW)
        with self.assertRaises(PlgkitError):
            track("jordan", "created_doc", ["nope"], db=db, now=NOW)
        with self.assertRaises(PlgkitError):
            track("jordan", "created_doc", {"occurred_at": "yesterday"}, db=db, now=NOW)
        with self.assertRaises(PlgkitError):
            track("jordan", "created_doc", {"occurred_at": "2026-11-09T15:00:00"}, db=db, now=NOW)
        count = db.execute("SELECT COUNT(*) FROM plgkit_persona_events").fetchone()
        self.assertEqual(count[0], 0)

    def test_persona_before_migrate_explains_the_next_step(self):
        db = connect("sqlite:///:memory:")
        self.addCleanup(db.close)
        with self.assertRaises(PlgkitError) as caught:
            persona("jordan", db=db, now=NOW, mapping=MAPPING, config=DEFAULT_POLICY)
        self.assertIn("migrate", str(caught.exception))

    def test_migrate_twice(self):
        db = connect("sqlite:///:memory:")
        self.addCleanup(db.close)
        migrate(db)
        migrate(db)
        self.assertTrue(track("jordan", "created_doc", db=db, now=NOW))


if __name__ == "__main__":
    unittest.main()
