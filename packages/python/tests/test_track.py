"""track() stores events. calculate() writes the persona persona() reads."""

import json
import unittest
from pathlib import Path

from plgkit_personas import (
    PlgkitError,
    calculate,
    connect,
    identify,
    migrate,
    persona,
    persona_is,
    track,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads((ROOT / "spec" / "fixtures" / "cases.json").read_text(encoding="utf-8"))
NOW = "2026-11-10T15:00:00Z"
RULES = FIXTURE["rules"]


def memory_db():
    db = connect("sqlite:///:memory:")
    migrate(db)
    return db


class TrackTests(unittest.TestCase):
    def test_round_trip_matches_every_case(self):
        for case in FIXTURE["cases"]:
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
            if case["traits"]:
                identify(case["user_id"], case["traits"], db=db, now=case["calculated_at"])
            before = persona(case["user_id"], db=db)
            self.assertEqual(before["persona"], "")
            self.assertEqual(before["calculated_at"], "")
            rules = case.get("rules", RULES)
            summary = calculate(db=db, now=case["calculated_at"], user_id=case["user_id"], rules=rules)
            self.assertEqual(summary["users"], 1)
            result = persona(case["user_id"], db=db)
            self.assertEqual(result["persona"], case["persona"], case["name"])
            self.assertEqual(result["matched"], case["matched"], case["name"])
            self.assertEqual(result["reasons"], case["reasons"], case["name"])
            self.assertEqual(persona_is(case["user_id"], case["persona"] or "missing", db=db), bool(case["persona"]))

    def test_two_users_stay_apart(self):
        db = memory_db()
        self.addCleanup(db.close)
        track("avery", "picked_template", {"occurred_at": "2026-11-01T15:00:00Z"}, db=db, now=NOW)
        track("blake", "sent_invite", {"occurred_at": "2026-11-09T15:00:00Z"}, db=db, now=NOW)
        calculate(db=db, now=NOW, rules=RULES)
        self.assertEqual(persona("avery", db=db)["persona"], "blocked")
        self.assertEqual(persona("blake", db=db)["persona"], "champion")
        self.assertTrue(persona_is("blake", "champion", db=db))
        self.assertFalse(persona_is("avery", "champion", db=db))

    def test_identify_keeps_the_latest_value(self):
        db = memory_db()
        self.addCleanup(db.close)
        identify("ada", {"role": "member", "plan": "pro"}, db=db, now=NOW)
        identify("ada", {"role": "billing_admin"}, db=db, now=NOW)
        calculate(db=db, now=NOW, rules=RULES)
        self.assertEqual(persona("ada", db=db)["persona"], "billing_admin")

    def test_calculate_one_user(self):
        db = memory_db()
        self.addCleanup(db.close)
        identify("ada", {"role": "billing_admin"}, db=db, now=NOW)
        identify("pat", {"role": "member"}, db=db, now=NOW)
        summary = calculate(db=db, now=NOW, user_id="pat", rules=RULES)
        self.assertEqual(summary, {"users": 1, "assigned": 1, "unmatched": 0})
        self.assertEqual(persona("pat", db=db)["persona"], "member")
        self.assertEqual(persona("ada", db=db)["persona"], "")

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
        row = db.execute("SELECT metadata FROM plgkit_persona_events WHERE user_id = ?", ("jordan",)).fetchone()
        self.assertEqual(row[0], '{"page":"home"}')
        count = db.execute(
            "SELECT COUNT(*) FROM plgkit_persona_events WHERE user_id = ?", ("jordan",)
        ).fetchone()
        self.assertEqual(count[0], 1)

    def test_missing_occurred_at_uses_receipt_time(self):
        db = memory_db()
        self.addCleanup(db.close)
        track("jordan", "created_doc", db=db, now="2026-11-09T15:00:00Z")
        row = db.execute("SELECT occurred_at, received_at FROM plgkit_persona_events").fetchone()
        self.assertEqual(row[0], "2026-11-09T15:00:00.000000Z")
        self.assertEqual(row[0], row[1])

    def test_offset_is_stored_as_utc(self):
        db = memory_db()
        self.addCleanup(db.close)
        track("jordan", "created_doc", {"occurred_at": "2026-11-09T10:00:00-05:00"}, db=db, now=NOW)
        row = db.execute("SELECT occurred_at FROM plgkit_persona_events").fetchone()
        self.assertEqual(row[0], "2026-11-09T15:00:00.000000Z")

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
        with self.assertRaises(PlgkitError):
            identify("jordan", {}, db=db, now=NOW)
        with self.assertRaises(PlgkitError):
            identify("jordan", {"role": 1}, db=db, now=NOW)
        with self.assertRaises(PlgkitError):
            persona_is("jordan", "", db=db)
        count = db.execute("SELECT COUNT(*) FROM plgkit_persona_events").fetchone()
        self.assertEqual(count[0], 0)

    def test_persona_before_migrate_explains_the_next_step(self):
        db = connect("sqlite:///:memory:")
        self.addCleanup(db.close)
        with self.assertRaises(PlgkitError) as caught:
            persona("jordan", db=db)
        self.assertIn("migrate", str(caught.exception))

    def test_migrate_twice(self):
        db = connect("sqlite:///:memory:")
        self.addCleanup(db.close)
        migrate(db)
        migrate(db)
        self.assertTrue(track("jordan", "created_doc", db=db, now=NOW))
        identify("jordan", {"role": "member"}, db=db, now=NOW)


if __name__ == "__main__":
    unittest.main()
