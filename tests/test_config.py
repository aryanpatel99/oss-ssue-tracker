import os
import unittest
import yaml

class TestConfig(unittest.TestCase):
    def test_lfx_projects_in_config(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self.assertIn("lfx_projects", cfg)
        projects = cfg["lfx_projects"]
        self.assertGreaterEqual(len(projects), 25)
        repos = [p["repo"] for p in projects]
        self.assertIn("wasmedge/wasmedge", repos)
        self.assertIn("kubeedge/kubeedge", repos)
        self.assertIn("volcano-sh/volcano", repos)

if __name__ == "__main__":
    unittest.main()
