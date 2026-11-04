"""Quadra Lite's user directories."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quadra import paths


class UserDirectoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        paths.user_directory.cache_clear()
        self.addCleanup(paths.user_directory.cache_clear)

    def test_each_kind_lives_under_quadralite(self):
        with patch.dict(
            os.environ,
            XDG_CONFIG_HOME=str(self.base / 'config'),
            XDG_CACHE_HOME=str(self.base / 'cache'),
            XDG_DATA_HOME=str(self.base / 'data'),
        ):
            for kind, folder in (
                ('CONFIG', 'config'),
                ('CACHE', 'cache'),
                ('DATA', 'data'),
            ):
                self.assertEqual(
                    paths.user_directory(kind), self.base / folder / 'quadralite'
                )

    def test_xdg_variables_are_honoured(self):
        with patch.dict(os.environ, XDG_CONFIG_HOME=str(self.base)):
            self.assertEqual(paths.user_directory('CONFIG'), self.base / 'quadralite')
