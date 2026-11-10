"""The shared cases are the contract. Python has to match them."""

import json
import unittest
from pathlib import Path

from plgkit_personas import judge
from plgkit_personas.config import DEFAULT_POLICY, load_policy
from plgkit_personas.mapping import load_mapping

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads((ROOT / "spec" / "fixtures" / "cases.json").read_text(encoding="utf-8"))


class JudgeTests(unittest.TestCase):
    def test_defaults_match_the_fixture(self):
        self.assertEqual(DEFAULT_POLICY, FIXTURE["config"])

    def test_examples_match_the_fixture(self):
        examples = ROOT / "spec" / "examples"
        self.assertEqual(load_mapping(examples / "mapping.yml"), FIXTURE["mapping"])
        self.assertEqual(load_policy(examples / "config.yml"), FIXTURE["config"])

    def test_cases(self):
        self.assertGreaterEqual(len(FIXTURE["cases"]), 2)
        names = [case["name"] for case in FIXTURE["cases"]]
        self.assertIn("avery_blocked", names)
        self.assertIn("blake_champion", names)
        for case in FIXTURE["cases"]:
            result = judge(
                case["user_id"],
                case["events"],
                mapping=FIXTURE["mapping"],
                policy=FIXTURE["config"],
                now=case["calculated_at"],
            )
            self.assertEqual(result["user_id"], case["user_id"], case["name"])
            self.assertEqual(result["persona"], case["persona"], case["name"])
            self.assertEqual(result["matched"], case["matched"], case["name"])
            self.assertEqual(result["counts"], case["counts"], case["name"])
            self.assertEqual(result["reasons"], case["reasons"], case["name"])
            self.assertEqual(result["calculated_at"], case["calculated_at"], case["name"])
            self.assertLessEqual(len(result["reasons"]), 5, case["name"])

    def test_avery_and_blake_are_the_demo_pair(self):
        by_name = {case["name"]: case for case in FIXTURE["cases"]}
        self.assertEqual(by_name["avery_blocked"]["persona"], "blocked")
        self.assertEqual(by_name["blake_champion"]["persona"], "champion")
        self.assertIn("power_user", by_name["blake_champion"]["matched"])

    def test_lower_power_threshold_promotes_an_evaluator(self):
        jordan = next(case for case in FIXTURE["cases"] if case["name"] == "evaluator")
        policy = dict(FIXTURE["config"])
        policy["power_user_min"] = 2
        result = judge(
            jordan["user_id"],
            jordan["events"],
            mapping=FIXTURE["mapping"],
            policy=policy,
            now=jordan["calculated_at"],
        )
        self.assertEqual(result["persona"], "power_user")


if __name__ == "__main__":
    unittest.main()
