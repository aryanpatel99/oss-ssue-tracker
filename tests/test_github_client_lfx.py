import unittest
from unittest.mock import call, patch, MagicMock
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

    def test_startup_search_excludes_issues_linked_to_pull_requests(self):
        client = GitHubClient(token="fake-token")
        captured_queries = []

        def capture_query(query):
            captured_queries.append(query)
            return []

        with patch.object(client, "search_issues", side_effect=capture_query), patch(
            "tracker.github_client.time.sleep"
        ):
            client.fetch_startup_issues(
                startup_projects=[{"repo": "example/project"}],
                require_no_linked_prs=True,
            )

        self.assertEqual(len(captured_queries), 1)
        self.assertIn("-linked:pr", captured_queries[0])

    def test_search_retries_secondary_rate_limit_then_returns_items(self):
        class Response:
            def __init__(self, status_code, payload, headers=None, text=""):
                self.status_code = status_code
                self._payload = payload
                self.headers = headers or {}
                self.text = text

            def json(self):
                return self._payload

        client = GitHubClient(token="fake-token")
        client.session.get = MagicMock(side_effect=[
            Response(
                403,
                {},
                headers={"retry-after": "1"},
                text="You have exceeded a secondary rate limit.",
            ),
            Response(200, {"items": [{"id": 1}]}),
        ])

        with patch("tracker.github_client.time.sleep") as sleep:
            items = client.search_issues("repo:example/project is:issue")

        self.assertEqual(items, [{"id": 1}])
        self.assertEqual(client.session.get.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_search_stops_remaining_requests_after_secondary_limit_retries_fail(self):
        class Response:
            status_code = 403
            headers = {}
            text = "You have exceeded a secondary rate limit."

        client = GitHubClient(token="fake-token")
        client.session.get = MagicMock(side_effect=[Response()] * 4)

        with patch("tracker.github_client.time.sleep") as sleep:
            self.assertEqual(client.search_issues("repo:example/project is:issue"), [])
            self.assertEqual(client.search_issues("repo:example/other is:issue"), [])

        self.assertEqual(client.session.get.call_count, 4)
        self.assertEqual(sleep.call_args_list, [call(60), call(120), call(240)])

    def test_secondary_retry_uses_rate_limit_reset_when_primary_bucket_is_empty(self):
        class Response:
            headers = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "112"}

        with patch("tracker.github_client.time.time", return_value=100):
            delay = GitHubClient._secondary_retry_delay(Response(), attempt=0)

        self.assertEqual(delay, 14)

if __name__ == "__main__":
    unittest.main()
