"""Config files and the database address."""

import os
import tempfile
import unittest
from pathlib import Path

from plgkit_personas import PlgkitError, resolve_database_url
from plgkit_personas.config import read_config


class ConfigTests(unittest.TestCase):
    def test_database_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.yml"
            config.write_text("database_url_env: PERSONA_DB\n", encoding="utf-8")
            url, used_default = resolve_database_url(
                config_path=config,
                environ={"PERSONA_DB": "sqlite:///events.sqlite"},
            )
            self.assertEqual(url, "sqlite:///events.sqlite")
            self.assertFalse(used_default)
            url, used_default = resolve_database_url(config_path=config, environ={})
            self.assertTrue(used_default)
            self.assertEqual(url, "sqlite:///plgkit_events.sqlite")
            config.write_text("database_url_env: 1bad\n", encoding="utf-8")
            with self.assertRaises(PlgkitError):
                resolve_database_url(config_path=config, environ={})
            config.write_text("database_url_env: PERSONA_DB\n", encoding="utf-8")
            with self.assertRaises(PlgkitError) as caught:
                resolve_database_url(
                    config_path=config,
                    environ={"PERSONA_DB": "mysql://user:secret@localhost/db"},
                )
            self.assertNotIn("secret", str(caught.exception))
            self.assertIn("mysql", str(caught.exception))

    def test_unknown_config_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.yml"
            config.write_text("lookback_days: 14\n", encoding="utf-8")
            with self.assertRaises(PlgkitError):
                read_config(config)

    def test_discovers_app_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "plgkit" / "personas"
            app.mkdir(parents=True)
            (app / "config.yml").write_text("database_url_env: PERSONA_DB\n", encoding="utf-8")
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                url, _ = resolve_database_url(environ={"PERSONA_DB": "sqlite:///from-app.sqlite"})
            finally:
                os.chdir(previous)
        self.assertEqual(url, "sqlite:///from-app.sqlite")


if __name__ == "__main__":
    unittest.main()
