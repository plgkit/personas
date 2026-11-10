"""The terminal demo prints two users and two nudges."""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "spec" / "examples" / "demo" / "script" / "demo"


class DemoTests(unittest.TestCase):
    def test_avery_and_blake(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(completed.stdout, self.expected())

    def test_node_and_go(self):
        for backend in ("node", "go"):
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--backend", backend],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout, self.expected(), backend)

    def expected(self):
        return (
            "Avery    blocked      Want help with the step you stopped on?\n"
            "Blake    champion     Bring in the person you invited.\n"
        )


if __name__ == "__main__":
    unittest.main()
