"""The shared cases are the contract. Python has to match them."""

import json
import unittest
from pathlib import Path

from plgkit_personas import PlgkitError, judge, load_rules, normalize_rules

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads((ROOT / "spec" / "fixtures" / "cases.json").read_text(encoding="utf-8"))


class JudgeTests(unittest.TestCase):
    def test_example_file_matches_the_fixture(self):
        loaded = load_rules(ROOT / "spec" / "examples" / "personas.yml")
        self.assertEqual(loaded, normalize_rules(FIXTURE["rules"]))

    def test_cases(self):
        names = [case["name"] for case in FIXTURE["cases"]]
        self.assertIn("developer_member", names)
        self.assertIn("avery_blocked", names)
        self.assertIn("blake_champion", names)
        for case in FIXTURE["cases"]:
            rules = case.get("rules", FIXTURE["rules"])
            result = judge(
                case["user_id"],
                case["events"],
                case["traits"],
                rules,
                now=case["calculated_at"],
            )
            self.assertEqual(result["user_id"], case["user_id"], case["name"])
            self.assertEqual(result["persona"], case["persona"], case["name"])
            self.assertEqual(result["matched"], case["matched"], case["name"])
            self.assertEqual(result["reasons"], case["reasons"], case["name"])
            self.assertEqual(result["calculated_at"], case["calculated_at"], case["name"])

    def test_six_events_keep_the_five_newest(self):
        rules = {
            "personas": [
                {
                    "name": "busy",
                    "priority": 1,
                    "require_all": [
                        {"count": {"action": "app_opened", "at_least": 1, "within_days": 14}}
                    ],
                }
            ]
        }
        events = [
            {"action": "app_opened", "occurred_at": f"2026-11-0{day}T15:00:00Z"}
            for day in range(4, 10)
        ]
        result = judge("busy", events, {}, rules, now="2026-11-10T15:00:00Z")
        self.assertEqual(len(result["reasons"]), 5)
        self.assertEqual(result["reasons"][0]["occurred_at"], "2026-11-09T15:00:00.000000Z")
        self.assertEqual(result["reasons"][-1]["occurred_at"], "2026-11-05T15:00:00.000000Z")

    def test_bad_rules(self):
        with self.assertRaises(PlgkitError):
            normalize_rules({"personas": [{"name": "a", "require_all": []}]})
        with self.assertRaises(PlgkitError):
            normalize_rules(
                {
                    "groups": {"app_use": ["app_opened"]},
                    "personas": [
                        {"name": "a", "priority": 1},
                        {"name": "a", "priority": 2},
                    ],
                }
            )
        with self.assertRaises(PlgkitError):
            normalize_rules(
                {
                    "personas": [
                        {
                            "name": "a",
                            "priority": 1,
                            "require_all": [
                                {"count": {"group": "missing", "at_least": 1, "within_days": 1}}
                            ],
                        }
                    ]
                }
            )
        with self.assertRaises(PlgkitError):
            normalize_rules(
                {
                    "personas": [
                        {
                            "name": "a",
                            "priority": 1,
                            "require_all": [
                                {
                                    "count": {
                                        "action": "app_opened",
                                        "at_least": 3,
                                        "at_most": 1,
                                        "within_days": 1,
                                    }
                                }
                            ],
                        }
                    ]
                }
            )
        with self.assertRaises(PlgkitError):
            normalize_rules({"mystery": 1})


if __name__ == "__main__":
    unittest.main()
