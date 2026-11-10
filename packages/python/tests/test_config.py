"""Config files, mapping files, and the database address."""

import os
import tempfile
import unittest
from pathlib import Path

from plgkit_personas import PlgkitError, resolve_database_url
from plgkit_personas.config import load_policy
from plgkit_personas.mapping import load_mapping


class ConfigTests(unittest.TestCase):
    def test_missing_files_use_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                self.assertEqual(load_mapping(), {})
                policy = load_policy()
            finally:
                os.chdir(previous)
        self.assertEqual(policy["lookback_days"], 14)
        self.assertEqual(policy["silence_days"], 7)

    def test_bad_policy_and_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            mapping = folder / "mapping.yml"
            config = folder / "config.yml"
            mapping.write_text("created_doc: nope\n", encoding="utf-8")
            with self.assertRaises(PlgkitError):
                load_mapping(mapping)
            mapping.write_text("created_doc: core_action\ncreated_doc: invite_sent\n", encoding="utf-8")
            with self.assertRaises(PlgkitError):
                load_mapping(mapping)
            config.write_text("silence_days: 14\nlookback_days: 14\n", encoding="utf-8")
            with self.assertRaises(PlgkitError):
                load_policy(config)
            config.write_text("lookback_days: 0\n", encoding="utf-8")
            with self.assertRaises(PlgkitError):
                load_policy(config)
            config.write_text("mystery: 1\n", encoding="utf-8")
            with self.assertRaises(PlgkitError):
                load_policy(config)

    def test_database_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            config = folder / "config.yml"
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

    def test_discovers_app_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "plgkit" / "personas"
            app.mkdir(parents=True)
            (app / "config.yml").write_text(
                "database_url_env: PERSONA_DB\nlookback_days: 10\nsilence_days: 3\n",
                encoding="utf-8",
            )
            (app / "mapping.yml").write_text("created_doc: core_action\n", encoding="utf-8")
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                policy = load_policy()
                mapping = load_mapping()
                url, used_default = resolve_database_url(environ={"PERSONA_DB": "sqlite:///:memory:"})
            finally:
                os.chdir(previous)
        self.assertEqual(policy["lookback_days"], 10)
        self.assertEqual(policy["silence_days"], 3)
        self.assertEqual(mapping, {"created_doc": "core_action"})
        self.assertEqual(url, "sqlite:///:memory:")
        self.assertFalse(used_default)


if __name__ == "__main__":
    unittest.main()
