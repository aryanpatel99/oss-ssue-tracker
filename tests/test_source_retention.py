import os
import unittest
import yaml
from main import load_config

class TestSourceRetention(unittest.TestCase):
    def test_source_retention_settings_in_config(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        cfg = load_config(config_path)
        settings = cfg.get("settings", {})
        
        self.assertIn("cncf_days_back", settings)
        self.assertIn("aswf_days_back", settings)
        self.assertIn("lfx_days_back", settings)
        self.assertIn("startup_days_back", settings)
        
        self.assertEqual(settings["cncf_days_back"], 14)
        self.assertEqual(settings["aswf_days_back"], 14)
        self.assertEqual(settings["lfx_days_back"], 30)
        self.assertEqual(settings["startup_days_back"], 7)

    def test_source_days_back_resolution(self):
        from main import resolve_source_days_back
        settings = {
            "days_back": 7,
            "cncf_days_back": 14,
            "aswf_days_back": 14,
            "lfx_days_back": 30,
            "startup_days_back": 7,
        }
        # When no override
        resolved = resolve_source_days_back(settings, override_days=None, override_hours=None)
        self.assertEqual(resolved["cncf"], 14.0)
        self.assertEqual(resolved["aswf"], 14.0)
        self.assertEqual(resolved["lfx"], 30.0)
        self.assertEqual(resolved["startup"], 7.0)

        # When override_days is passed
        resolved_days = resolve_source_days_back(settings, override_days=5, override_hours=None)
        self.assertEqual(resolved_days["cncf"], 5.0)
        self.assertEqual(resolved_days["lfx"], 5.0)

        # When override_hours is passed
        resolved_hours = resolve_source_days_back(settings, override_days=None, override_hours=48)
        self.assertEqual(resolved_hours["cncf"], 2.0)
        self.assertEqual(resolved_hours["lfx"], 2.0)


if __name__ == "__main__":
    unittest.main()
