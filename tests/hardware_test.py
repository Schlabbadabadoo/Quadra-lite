"""Tests for launcher/quadra/hardware.py."""
import os
import subprocess
import unittest
from unittest.mock import patch, MagicMock

from quadra import hardware


class HardwareTests(unittest.TestCase):
    def setUp(self):
        hardware.refresh()

    def test_detect_returns_dict(self):
        profile = hardware.detect()
        self.assertIsInstance(profile, dict)
        self.assertIn("cpu", profile)
        self.assertIn("gpus", profile)
        self.assertIn("memory", profile)
        self.assertIn("display", profile)
        self.assertIn("graphics", profile)
        self.assertIn("system", profile)
        self.assertIn("warnings", profile)

    def test_cpu_has_expected_keys(self):
        cpu = hardware.detect()["cpu"]
        for k in ("name", "architecture", "cores", "threads", "max_freq_mhz", "capabilities"):
            self.assertIn(k, cpu)

    def test_memory_format(self):
        self.assertEqual(hardware.format_bytes(0), "unknown")
        self.assertIn("MiB", hardware.format_bytes(1024 * 1024))

    def test_cache_returns_same_object(self):
        a = hardware.detect()
        b = hardware.detect()
        self.assertIs(a, b)

    def test_refresh_invalidates_cache(self):
        a = hardware.detect()
        hardware.refresh()
        b = hardware.detect()
        self.assertIsNot(a, b)

    def test_recommend_renderer_returns_tuple(self):
        r, reason = hardware.recommend_renderer()
        self.assertIn(r, ("opengl", "vulkan", "metal"))
        self.assertIsInstance(reason, str)

    def test_missing_utilities_do_not_crash(self):
        with patch("shutil.which", return_value=None):
            hardware.refresh()
            profile = hardware.detect()
            self.assertIsInstance(profile, dict)

    def test_detect_cpu_with_proc_cpuinfo(self):
        fake = "model name\t: Test CPU\ncpu cores\t: 4\nflags\t\t: sse avx2 foo\n"
        with patch("builtins.open", side_effect=lambda p, *a, **k: __import__("io").StringIO(fake) if "cpuinfo" in str(p) else open(p, *a, **k)):
            pass
        # simpler: patch _read
        with patch.object(hardware, "_read", return_value=fake):
            cpu = hardware._detect_cpu()
            self.assertEqual(cpu["name"], "Test CPU")
            self.assertEqual(cpu["cores"], 4)
            self.assertIn("sse", cpu["capabilities"])
            self.assertIn("avx2", cpu["capabilities"])

    def test_detect_memory(self):
        fake = "MemTotal:       8000000 kB\nMemAvailable:   4000000 kB\n"
        with patch.object(hardware, "_read", return_value=fake):
            mem = hardware._detect_memory()
            self.assertEqual(mem["total_bytes"], 8000000 * 1024)
            self.assertEqual(mem["available_bytes"], 4000000 * 1024)

    def test_subprocess_timeout_handled(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="x", timeout=1)):
            out = hardware._run(["x"])
            self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
