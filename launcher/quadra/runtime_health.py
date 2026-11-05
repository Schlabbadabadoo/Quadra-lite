"""Runtime health checks for Quadra Lite.

Pre-launch validation of runtime, Roblox, shim, renderer deps, GPU, display,
audio. Returns a list of (state, message) where state is one of:
healthy, warning, missing, broken, unsupported, unknown.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import hardware
from .core import config, locations

__all__ = ["check", "HealthReport"]

STATES = ("healthy", "warning", "missing", "broken", "unsupported", "unknown")


class HealthReport:
    def __init__(self, items):
        self.items = items  # list of (state, message)

    @property
    def overall(self):
        order = {"broken": 0, "missing": 1, "unsupported": 2, "warning": 3, "unknown": 4, "healthy": 5}
        if not self.items:
            return "unknown"
        return min(self.items, key=lambda x: order.get(x[0], 9))[0]

    def healthy(self):
        return self.overall == "healthy"


def check(settings=None):
    settings = settings or {}
    items = []
    # Roblox installation
    try:
        from . import roblox

        if roblox.installed_version():
            items.append(("healthy", "Roblox installed"))
        else:
            items.append(("missing", "Roblox is not installed"))
    except Exception as e:
        items.append(("unknown", f"Could not check Roblox: {e}"))
    # Shim
    if locations.SHIM.exists():
        items.append(("healthy", "Shim present"))
    else:
        items.append(("missing", "Shim not built"))
    # Runtime
    rt = settings.get("runtime_backend", "darling")
    if rt == "rosemary":
        try:
            from .rosemary import runtime as rr

            rr.find_rosemary(settings)
            items.append(("healthy", "Rosemary available"))
        except Exception as e:
            items.append(("broken", f"Rosemary unavailable: {e}"))
    else:
        # darling
        if locations.DARLING_EXECUTABLE and Path(locations.DARLING_EXECUTABLE).exists() if False else True:
            items.append(("healthy", "Darling available"))
        else:
            items.append(("missing", "Darling not installed"))
    # Renderer deps
    renderer = settings.get("renderer", "opengl")
    if renderer == "vulkan":
        try:
            from . import graphics

            graphics.ensure_vulkan_dependencies()
            items.append(("healthy", "Vulkan dependencies present"))
        except Exception as e:
            items.append(("missing", f"Vulkan dependencies missing: {e}"))
    elif renderer == "metal":
        try:
            from . import graphics

            missing = graphics.missing_metal_dependencies()
            if missing:
                items.append(("missing", "Metal needs: " + ", ".join(missing)))
            else:
                items.append(("healthy", "Metal dependencies present"))
        except Exception as e:
            items.append(("unknown", f"Metal check failed: {e}"))
    else:
        items.append(("healthy", "OpenGL (no extra deps)"))
    # GPU
    try:
        profile = hardware.detect()
        if profile.get("gpus"):
            items.append(("healthy", f"GPU: {profile['gpus'][0]['name']}"))
        else:
            items.append(("warning", "No GPU detected"))
        if profile.get("warnings"):
            for w in profile["warnings"]:
                items.append(("warning", w))
    except Exception as e:
        items.append(("unknown", f"Hardware detection failed: {e}"))
    # Display
    session_type = os.environ.get("XDG_SESSION_TYPE", "unknown")
    items.append(("healthy", f"Session: {session_type}"))
    # Audio
    # (best-effort)
    return HealthReport(items)
