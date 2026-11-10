"""Audience checks follow the persona label. They do not import nudges."""

import importlib.util
import json
import unittest
from pathlib import Path

from plgkit_personas import connect, migrate, track

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads((ROOT / "spec" / "fixtures" / "cases.json").read_text(encoding="utf-8"))
NUDGES = ROOT / "spec" / "examples" / "nudges"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AudienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audiences = load_module("persona_audiences", NUDGES / "audiences.py")
        cls.messages = load_module("persona_messages", NUDGES / "messages.py")

    def test_message_bodies(self):
        loaded = self.messages.load_messages(NUDGES / "messages")
        bodies = {item["id"]: item["render_props"]["body"] for item in loaded}
        self.assertEqual(
            bodies,
            {
                "20261110150400-home-blocked-help": "Want help with the step you stopped on?",
                "20261110150401-home-champion-invite": "Bring in the person you invited.",
            },
        )
        self.assertEqual(
            loaded[0]["audience"]["require_all"],
            ["persona_is_blocked"],
        )
        self.assertEqual(
            loaded[1]["audience"]["require_all"],
            ["persona_is_champion"],
        )

    def test_checks_follow_the_label(self):
        for case in FIXTURE["cases"]:
            db = connect("sqlite:///:memory:")
            migrate(db)
            now = case["calculated_at"]
            for event in case["events"]:
                stored = track(
                    case["user_id"],
                    event["action"],
                    {"occurred_at": event["occurred_at"]},
                    db=db,
                    now=now,
                )
                self.assertTrue(stored, case["name"])
            checks = self.audiences.bind(
                db=db,
                now=now,
                mapping=FIXTURE["mapping"],
                policy=FIXTURE["config"],
            )
            ctx = {"user": {"id": case["user_id"]}}
            self.assertEqual(checks["persona_is_blocked"](ctx), case["persona"] == "blocked", case["name"])
            self.assertEqual(checks["persona_is_champion"](ctx), case["persona"] == "champion", case["name"])

    def test_attribute_context_and_sample_files(self):
        case = next(item for item in FIXTURE["cases"] if item["name"] == "avery_blocked")
        db = connect("sqlite:///:memory:")
        migrate(db)
        now = case["calculated_at"]
        for event in case["events"]:
            track(case["user_id"], event["action"], {"occurred_at": event["occurred_at"]}, db=db, now=now)
        checks = self.audiences.bind(db=db, now=now)

        class User:
            id = "avery"

        class Context:
            user = User()

        self.assertTrue(checks["persona_is_blocked"](Context()))
        self.assertFalse(checks["persona_is_champion"](Context()))
        self.assertFalse(checks["persona_is_blocked"]({}))
        self.assertFalse(checks["persona_is_champion"]({}))


if __name__ == "__main__":
    unittest.main()
