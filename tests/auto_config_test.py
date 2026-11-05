"""Tests for auto_config and runtime_health."""
import unittest
from unittest.mock import patch

from quadra import auto_config, runtime_health


class AutoConfigTests(unittest.TestCase):
    def test_modes_contains_expected(self):
        self.assertIn("auto", auto_config.MODES)
        self.assertIn("manual", auto_config.MODES)

    def test_recommend_runtime_returns_tuple(self):
        rt, reason = auto_config.recommend_runtime({})
        self.assertIn(rt, ("rosemary", "darling"))
        self.assertIsInstance(reason, str)

    def test_recommend_renderer_returns_tuple(self):
        rd, reason = auto_config.recommend_renderer({})
        self.assertIn(rd, ("opengl", "vulkan", "metal"))
        self.assertIsInstance(reason, str)

    def test_apply_mode_manual_preserves(self):
        s = {"renderer": "vulkan", "runtime_backend": "darling"}
        out = auto_config.apply_mode(s, "manual")
        self.assertEqual(out["renderer"], "vulkan")
        self.assertEqual(out["auto_config_mode"], "manual")

    def test_apply_mode_auto_sets(self):
        out = auto_config.apply_mode({}, "auto")
        self.assertIn(out["runtime_backend"], ("rosemary", "darling"))
        self.assertIn(out["renderer"], ("opengl", "vulkan", "metal"))
        self.assertEqual(out["auto_config_mode"], "auto")

    def test_explain_returns_dict(self):
        d = auto_config.explain({})
        self.assertIn("mode", d)
        self.assertIn("runtime", d)
        self.assertIn("renderer", d)

    def test_does_not_mutate_input(self):
        s = {"renderer": "vulkan"}
        auto_config.apply_mode(s, "auto")
        self.assertEqual(s["renderer"], "vulkan")


class RuntimeHealthTests(unittest.TestCase):
    def test_check_returns_report(self):
        report = runtime_health.check({})
        self.assertIsInstance(report, runtime_health.HealthReport)
        self.assertIn(report.overall, runtime_health.STATES)

    def test_health_report_items(self):
        report = runtime_health.check({})
        self.assertTrue(len(report.items) > 0)

    def test_healthy_property(self):
        report = runtime_health.HealthReport([("healthy", "ok")])
        self.assertTrue(report.healthy())
        report2 = runtime_health.HealthReport([("broken", "x")])
        self.assertFalse(report2.healthy())


if __name__ == "__main__":
    unittest.main()
