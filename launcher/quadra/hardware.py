"""Central, lightweight hardware detection for Quadra Lite.

Everything here is read-only and best-effort: missing files, missing
utilities and unreadable values never raise; they leave the corresponding
field as ``None``/``"unknown"``. Results are cached so that repeated calls
from the UI or the launch path do not re-run subprocesses, and ``refresh()``
invalidates the cache.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

__all__ = [
    "HardwareProfile",
    "detect",
    "refresh",
    "recommend_renderer",
    "format_bytes",
]


# ---------------------------------------------------------------------------
# caching
# ---------------------------------------------------------------------------

_CACHE = None
_CACHE_LOCK = None


def _lock():
    global _CACHE_LOCK
    if _CACHE_LOCK is None:
        import threading

        _CACHE_LOCK = threading.Lock()
    return _CACHE_LOCK


def refresh():
    """Invalidate the cached hardware profile."""
    global _CACHE
    with _lock():
        _CACHE = None


def detect(force=False):
    """Return the cached hardware profile, detecting on first call."""
    global _CACHE
    with _lock():
        if _CACHE is None or force:
            _CACHE = _detect_all()
        return _CACHE


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _read(path, limit=4096):
    try:
        with Path(path).open() as source:
            return source.read(limit).strip()
    except (OSError, UnicodeError):
        return ""


def _run(argv, timeout=2):
    """Run a command, returning stdout or '' on any failure."""
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError, ValueError):
        return ""


def format_bytes(value):
    if not value:
        return "unknown"
    value = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} PiB"


# ---------------------------------------------------------------------------
# CPU
# ---------------------------------------------------------------------------


def _detect_cpu():
    info = {
        "name": "unknown",
        "architecture": platform.machine() or "unknown",
        "cores": None,
        "threads": None,
        "max_freq_mhz": None,
        "capabilities": [],
    }
    try:
        info["threads"] = os.cpu_count()
    except Exception:
        pass
    # /proc/cpuinfo
    text = _read("/proc/cpuinfo")
    if text:
        names = re.findall(r"^model name\s*:\s*(.+)$", text, re.M)
        if names:
            info["name"] = names[0].strip()
        cores = re.findall(r"^cpu cores\s*:\s*(\d+)$", text, re.M)
        if cores:
            try:
                info["cores"] = int(cores[0])
            except ValueError:
                pass
        flags = re.search(r"^flags\s*:\s*(.+)$", text, re.M)
        if flags:
            fl = flags.group(1).split()
            interesting = {
                "sse", "sse2", "sse4_1", "sse4_2", "avx", "avx2",
                "avx512f", "aes", "fma", "popcnt",
            }
            info["capabilities"] = sorted(set(fl) & interesting)
        freqs = re.findall(r"^cpu MHz\s*:\s*([\d.]+)$", text, re.M)
        if freqs:
            try:
                info["max_freq_mhz"] = round(max(float(f) for f in freqs))
            except ValueError:
                pass
    # fallback arch name from uname
    if info["name"] == "unknown":
        info["name"] = platform.processor() or "unknown"
    # core count fallback via nproc
    if info["cores"] is None:
        out = _run(["nproc"])
        if out.isdigit():
            info["cores"] = int(out)
    return info


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------


def _detect_memory():
    info = {"total_bytes": None, "available_bytes": None}
    text = _read("/proc/meminfo")
    if text:
        m = re.search(r"^MemTotal:\s*(\d+)\s*kB", text, re.M)
        if m:
            info["total_bytes"] = int(m.group(1)) * 1024
        m = re.search(r"^MemAvailable:\s*(\d+)\s*kB", text, re.M)
        if m:
            info["available_bytes"] = int(m.group(1)) * 1024
    return info


# ---------------------------------------------------------------------------
# GPU
# ---------------------------------------------------------------------------


def _vendor_name(vendor_id):
    return {0x10DE: "NVIDIA", 0x1002: "AMD", 0x8086: "Intel"}.get(vendor_id, "GPU")


def _detect_gpus():
    gpus = []
    try:
        nodes = sorted(Path("/sys/class/drm").iterdir())
    except OSError:
        nodes = []
    adapters = {}
    for node in nodes:
        if not re.fullmatch(r"card\d+", node.name):
            continue
        device = node / "device"
        props = {}
        for line in _read(device / "uevent").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                props[k] = v
        address = props.get("PCI_SLOT_NAME", "")
        try:
            vendor = int(_read(device / "vendor"), 16)
            product = int(_read(device / "device"), 16)
            cls = int(_read(device / "class"), 16) >> 16
        except (OSError, ValueError):
            continue
        if cls != 3:
            continue
        driver = ""
        try:
            driver = (device / "driver").resolve(strict=True).name
        except (OSError, RuntimeError):
            driver = ""
        adapter = adapters.setdefault(
            address,
            {
                "pci": address,
                "vendor_id": vendor,
                "product_id": product,
                "vendor": _vendor_name(vendor),
                "driver": driver,
                "name": "",
                "vram_bytes": None,
                "integrated": vendor in (0x8086,) or vendor == 0x1002,  # heuristic
            },
        )
        # NVIDIA name from proc
        if vendor == 0x10DE:
            model = _read(Path("/proc/driver/nvidia/gpus") / address / "information")
            m = re.search(r"^Model:\s*(.+)$", model, re.M)
            if m:
                adapter["name"] = m.group(1).strip()
        # AMD/Intel name from lspci if available
        if not adapter["name"]:
            # try sysfs label
            label = _read(device / "label")
            if label:
                adapter["name"] = label
    # lspci friendly names
    lspci = shutil.which("lspci")
    names = {}
    if lspci:
        out = _run([lspci, "-D", "-mm"], timeout=2)
        for line in out.splitlines():
            parts = _shlex_split(line)
            if len(parts) >= 4 and parts[0] in adapters:
                names[parts[0]] = f"{parts[2]} {parts[3]}"
    for address, adapter in adapters.items():
        if not adapter["name"]:
            adapter["name"] = names.get(address) or f"{adapter['vendor']} {adapter['product_id']:04x}"
        # VRAM from DRM
        mem_total = _read(Path("/sys/class/drm") / _card_for(address) / "device" / "mem_info_vram_total") if False else ""
        # Simpler: search /sys/class/drm/card*/device for matching pci
        for card_dir in Path("/sys/class/drm").glob("card*"):
            try:
                dev = card_dir / "device"
                if (dev / "uevent").is_file():
                    ue = _read(dev / "uevent")
                    if address and address in ue:
                        mt = _read(dev / "mem_info_vram_total")
                        if mt.isdigit():
                            adapter["vram_bytes"] = int(mt)
            except OSError:
                pass
        # NVIDIA vram via nvidia-smi
        if adapter["vendor"] == "NVIDIA" and adapter["vram_bytes"] is None:
            out = _run(
                ["nvidia-smi", "--query-gpu=pci.bus_id,memory.total", "--format=csv,noheader,nounits"],
                timeout=2,
            )
            for line in out.splitlines():
                cols = [c.strip() for c in line.split(",")]
                if len(cols) == 2 and cols[0].lower().endswith(address.lower().split(":")[-1] if ":" in address else address):
                    try:
                        adapter["vram_bytes"] = int(cols[1]) * 1024 * 1024
                    except ValueError:
                        pass
        gpus.append(adapter)
    # Mark integrated heuristic: Intel/AMD APUs are integrated; NVIDIA discrete.
    for g in gpus:
        if g["vendor"] == "NVIDIA":
            g["integrated"] = False
        elif g["vendor"] in ("AMD", "Intel"):
            # treat as integrated unless vram present (discrete AMD)
            g["integrated"] = g["vram_bytes"] is None
    return gpus


def _shlex_split(line):
    import shlex

    try:
        return shlex.split(line)
    except ValueError:
        return line.split()


def _card_for(address):
    return "card0"


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


def _detect_display():
    info = {"width": None, "height": None, "refresh_hz": None, "scale": None}
    # Try xrandr
    xrandr = shutil.which("xrandr")
    if xrandr:
        out = _run([xrandr], timeout=2)
        for line in out.splitlines():
            m = re.search(r"(\d+)x(\d+)\s+([\d.]+)\*?", line)
            if m and "*" in line:
                try:
                    info["width"] = int(m.group(1))
                    info["height"] = int(m.group(2))
                    info["refresh_hz"] = float(m.group(3))
                except ValueError:
                    pass
                break
    # Wayland: try wlr-randr or loginctl? fallback to env
    if info["width"] is None:
        # Try reading from /sys/class/drm for connected modes
        for card in Path("/sys/class/drm").glob("card*-*/modes"):
            try:
                modes = card.read_text().split()
                if modes:
                    w, h = modes[0].split("x")
                    info["width"] = int(w)
                    info["height"] = int(h)
                    break
            except (OSError, ValueError):
                pass
    # scale from env
    scale = os.environ.get("GDK_SCALE") or os.environ.get("QT_SCALE_FACTOR")
    if scale:
        try:
            info["scale"] = float(scale)
        except ValueError:
            pass
    return info


# ---------------------------------------------------------------------------
# Graphics capabilities
# ---------------------------------------------------------------------------


def _detect_graphics():
    info = {
        "opengl_version": None,
        "vulkan_available": False,
        "vulkan_devices": [],
        "zink_available": False,
        "metal_available": False,
    }
    # OpenGL
    glxinfo = shutil.which("glxinfo")
    if glxinfo:
        out = _run([glxinfo], timeout=3)
        m = re.search(r"OpenGL version string:\s*(.+)", out)
        if m:
            info["opengl_version"] = m.group(1).strip()
    # Vulkan
    vulkaninfo = shutil.which("vulkaninfo")
    if vulkaninfo:
        out = _run([vulkaninfo, "--summary"], timeout=4)
        if out:
            info["vulkan_available"] = True
            for line in out.splitlines():
                m = re.search(r"deviceName\s*=\s*(.+)", line)
                if m:
                    info["vulkan_devices"].append(m.group(1).strip())
    # zink: check if zink driver present
    for p in ("/usr/lib/x86_64-linux-gnu/libGLX_mesa.so.0", "/usr/lib/libvulkan.so"):
        pass
    # heuristic: zink available if vulkan available and mesa
    info["zink_available"] = info["vulkan_available"] and shutil.which("glxinfo") is not None
    return info


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------


def _detect_system():
    info = {
        "distro": "unknown",
        "kernel": platform.release(),
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
        "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
        "architecture": platform.machine(),
    }
    # distro
    try:
        if Path("/etc/os-release").is_file():
            for line in Path("/etc/os-release").read_text().splitlines():
                if line.startswith("PRETTY_NAME="):
                    info["distro"] = line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return info


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class HardwareProfile:
    """Lightweight container for detected hardware."""

    def __init__(self, data):
        self.data = data

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)

    def to_dict(self):
        return self.data


def _detect_all():
    cpu = _detect_cpu()
    gpus = _detect_gpus()
    memory = _detect_memory()
    display = _detect_display()
    graphics = _detect_graphics()
    system = _detect_system()
    selected = None
    if gpus:
        # prefer discrete (non-integrated) if available
        discrete = [g for g in gpus if not g.get("integrated")]
        selected = (discrete or gpus)[0]["name"]
    warnings = []
    if not gpus:
        warnings.append("No GPU detected")
    if graphics["vulkan_available"] is False:
        warnings.append("Vulkan not available")
    if memory["total_bytes"] and memory["total_bytes"] < 4 * 1024**3:
        warnings.append("Low system memory (<4 GiB)")
    return {
        "cpu": cpu,
        "gpus": gpus,
        "selected_gpu": selected,
        "memory": memory,
        "display": display,
        "graphics": graphics,
        "system": system,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def recommend_renderer(profile=None):
    """Return (renderer, reason) based on detected capabilities."""
    profile = profile or detect()
    g = profile["graphics"]
    gpus = profile["gpus"]
    if g.get("metal_available"):
        return "metal", "Metal (Quadra M2VK) available"
    if g.get("vulkan_available") and g.get("vulkan_devices"):
        return "vulkan", "Vulkan available"
    if g.get("opengl_version"):
        return "opengl", "OpenGL available"
    return "opengl", "No advanced graphics detected; using OpenGL"


def recommend_gpu(profile=None):
    profile = profile or detect()
    gpus = profile["gpus"]
    if not gpus:
        return None
    discrete = [g for g in gpus if not g.get("integrated")]
    return (discrete or gpus)[0]["name"]
