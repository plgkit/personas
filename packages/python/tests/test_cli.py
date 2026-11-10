"""plgkit-personas migrate creates the table."""

import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_migrate(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "events.sqlite"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT)
            env["PLGKIT_DATABASE_URL"] = "sqlite:///" + database.as_posix()
            env.pop("PLGKIT_PERSONA_MIGRATIONS_DIR", None)
            for _ in range(2):
                completed = subprocess.run(
                    [sys.executable, "-m", "plgkit_personas", "migrate"],
                    cwd=tmp,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("Migrations are up to date.", completed.stdout)
            with sqlite3.connect(database) as conn:
                row = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'plgkit_persona_events'"
                ).fetchone()
            self.assertIsNotNone(row)

    def test_usage(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        help_run = subprocess.run(
            [sys.executable, "-m", "plgkit_personas", "--help"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(help_run.returncode, 0)
        self.assertIn("plgkit-personas migrate", help_run.stderr)
        bare = subprocess.run(
            [sys.executable, "-m", "plgkit_personas"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(bare.returncode, 1)
        unknown = subprocess.run(
            [sys.executable, "-m", "plgkit_personas", "nope"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(unknown.returncode, 1)


if __name__ == "__main__":
    unittest.main()
