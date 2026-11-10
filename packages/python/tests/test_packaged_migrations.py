"""The installed package ships the SQL. It does not look up the repo."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[3]
CORE = REPO / "core" / "migrations"
PACKAGE_SQL = ROOT / "plgkit_personas" / "migrations"


class PackagedMigrationTests(unittest.TestCase):
    def test_package_sql_matches_core(self):
        core_files = sorted(path.name for path in CORE.glob("*.sql"))
        package_files = sorted(path.name for path in PACKAGE_SQL.glob("*.sql"))
        self.assertEqual(package_files, core_files)
        self.assertTrue(core_files)
        for name in core_files:
            self.assertEqual((PACKAGE_SQL / name).read_bytes(), (CORE / name).read_bytes())

    def test_wheel_migrates_away_from_the_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            wheel_dir = tmp_path / "wheels"
            wheel_dir.mkdir()
            built = subprocess.run(
                [sys.executable, "setup.py", "bdist_wheel", "-d", str(wheel_dir)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if built.returncode != 0:
                self.fail(built.stdout + "\n" + built.stderr)
            wheels = list(wheel_dir.glob("*.whl"))
            self.assertEqual(len(wheels), 1, wheels)
            extract = tmp_path / "pkg"
            with zipfile.ZipFile(wheels[0]) as archive:
                archive.extractall(extract)
            shipped = extract / "plgkit_personas" / "migrations"
            shipped_files = sorted(path.name for path in shipped.glob("*.sql"))
            core_files = sorted(path.name for path in CORE.glob("*.sql"))
            self.assertEqual(shipped_files, core_files)
            for name in core_files:
                self.assertEqual((shipped / name).read_bytes(), (CORE / name).read_bytes())

            env = os.environ.copy()
            env["PYTHONPATH"] = str(extract)
            env.pop("PLGKIT_PERSONA_MIGRATIONS_DIR", None)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import plgkit_personas\n"
                        "db = plgkit_personas.connect('sqlite:///:memory:')\n"
                        "plgkit_personas.migrate(db)\n"
                        "row = db.execute(\"SELECT name FROM sqlite_master "
                        "WHERE type='table' AND name='plgkit_persona_events'\").fetchone()\n"
                        "assert row, 'table missing'\n"
                    ),
                ],
                cwd=extract,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                self.fail(completed.stdout + "\n" + completed.stderr)

    def tearDown(self):
        shutil.rmtree(ROOT / "build", ignore_errors=True)
        shutil.rmtree(ROOT / "dist", ignore_errors=True)
        for path in ROOT.glob("*.egg-info"):
            shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
