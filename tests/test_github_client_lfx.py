import unittest
from unittest.mock import patch, MagicMock
from tracker.github_client import GitHubClient

class TestGitHubClientLFX(unittest.TestCase):
    def test_fetch_lfx_issues(self):
        client = GitHubClient(token="fake-token")
        lfx_projects = [{"repo": "wasmedge/wasmedge", "language": "C++"}]
        target_labels = ["lfx-mentorship", "good first issue"]

        sample_issue = {
            "id": 999111,
            "number": 42,
            "title": "Add WasmEdge plugin hook",
            "html_url": "https://github.com/wasmedge/wasmedge/issues/42",
            "labels": [{"name": "lfx-mentorship"}, {"name": "good first issue"}],
            "created_at": "2026-09-18T10:00:00Z",
            "comments": 2
        }

        with patch.object(client, 'search_issues', return_value=[sample_issue]):
            issues = client.fetch_lfx_issues(lfx_projects, target_labels, days_back=7)
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0]["source"], "LFX")
            self.assertEqual(issues[0]["repo"], "wasmedge/wasmedge")
            self.assertEqual(issues[0]["number"], 42)

if __name__ == "__main__":
    unittest.main()
