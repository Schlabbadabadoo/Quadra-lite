"""Quadra Lite's user directories."""

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=3)
def user_directory(kind):
    defaults = {
        "CONFIG": Path.home() / ".config",
        "CACHE": Path.home() / ".cache",
        "DATA": Path.home() / ".local" / "share",
    }
    base = Path(os.environ.get(f"XDG_{kind}_HOME", defaults[kind]))
    return base / "quadralite"
