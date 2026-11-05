"""Tests for config export/import."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quadra import core


class ConfigBackupTests(unittest.TestCase):
    def test_export_import_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "backup.json"
            core.export_settings(path)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text())
            self.assertIsInstance(data, dict)
            imported = core.import_settings(path)
            self.assertEqual(imported["language"], core.DEFAULT_SETTINGS["language"])

    def test_import_rejects_non_object(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.json"
            path.write_text("[1,2,3]")
            with self.assertRaises(ValueError):
                core.import_settings(path)

    def test_import_ignores_unknown_keys(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.json"
            path.write_text(json.dumps({"unknown_key_xyz": 5, "language": "en"}))
            imported = core.import_settings(path)
            self.assertNotIn("unknown_key_xyz", imported)
            self.assertEqual(imported["language"], "en")


if __name__ == "__main__":
    unittest.main()
