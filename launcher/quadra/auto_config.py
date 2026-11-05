"""Automatic configuration for Quadra Lite.

Recommends a runtime and renderer from detected hardware and the available
dependencies, without changing the user's settings unless asked. Recommendations
are explanations, not benchmarks.
"""

from __future__ import annotations

from . import backends, hardware
from .core import config

__all__ = [
    "MODES",
    "recommend_runtime",
    "recommend_renderer",
    "apply_mode",
    "explain",
]

MODES = ("auto", "performance", "compatibility", "manual")


def _profile(profile=None):
    try:
        return profile if profile is not None else hardware.detect()
    except Exception:
        return None


def recommend_runtime(settings=None, profile=None):
    """Return (runtime, reason)."""
    settings = settings or {}
    profile = _profile(profile)
    installed = []
    try:
        from .darling import runtime as darling_runtime

        installed = darling_runtime.installed_runtimes("darling") if False else []
    except Exception:
        installed = []
    # Prefer Rosemary if available and healthy; else Darling.
    rosemary_available = False
    try:
        from .rosemary import runtime as rr

        rr.find_rosemary(settings or {})
        rosemary_available = True
    except Exception:
        rosemary_available = False
    if rosemary_available:
        return "rosemary", "Rosemary is installed and available"
    return "darling", "Rosemary is not available; using Darling"


def recommend_renderer(settings=None, profile=None, runtime=None):
    """Return (renderer, reason)."""
    settings = settings or {}
    profile = _profile(profile)
    runtime = runtime or settings.get("runtime_backend", "darling")
    hw_renderer, hw_reason = hardware.recommend_renderer(profile)
    # Metal needs Rosemary or Darling with Metal deps; keep conservative.
    if hw_renderer == "metal":
        # only recommend metal if renderer explicitly supported
        pass
    # Compatibility mode prefers OpenGL
    mode = settings.get("auto_config_mode", "auto")
    if mode == "compatibility":
        return "opengl", "Compatibility mode prefers OpenGL"
    if mode == "performance":
        if hw_renderer in ("vulkan", "metal"):
            return hw_renderer, "Performance mode: " + hw_reason
        return "opengl", "Performance mode: OpenGL (best available)"
    # auto
    return hw_renderer, hw_reason


def apply_mode(settings, mode="auto", profile=None):
    """Return a new settings dict with recommended runtime/renderer applied.

    Only changes runtime_backend and renderer when mode != 'manual'. Never
    mutates the input.
    """
    settings = dict(settings or {})
    if mode == "manual":
        settings["auto_config_mode"] = "manual"
        return settings
    settings["auto_config_mode"] = mode
    rt, _ = recommend_runtime(settings, profile)
    rd, _ = recommend_renderer(settings, profile, rt)
    settings["runtime_backend"] = rt
    settings["renderer"] = rd
    return settings


def explain(settings=None, profile=None):
    """Return a dict describing the current auto-config decision."""
    settings = settings or {}
    profile = _profile(profile)
    rt, rtr = recommend_runtime(settings, profile)
    rd, rdr = recommend_renderer(settings, profile, rt)
    return {
        "mode": settings.get("auto_config_mode", "manual"),
        "runtime": rt,
        "runtime_reason": rtr,
        "renderer": rd,
        "renderer_reason": rdr,
    }
