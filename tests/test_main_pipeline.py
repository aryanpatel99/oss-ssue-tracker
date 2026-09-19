import unittest
from unittest.mock import patch, MagicMock
import os
from main import load_config

class TestMainPipeline(unittest.TestCase):
    def test_load_config_contains_lfx(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        cfg = load_config(config_path)
        self.assertIn("lfx_projects", cfg)
        self.assertIsInstance(cfg["lfx_projects"], list)
        self.assertGreaterEqual(len(cfg["lfx_projects"]), 10)

if __name__ == "__main__":
    unittest.main()
