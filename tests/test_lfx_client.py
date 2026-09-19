import unittest
from unittest.mock import patch, MagicMock
from tracker.lfx_client import LFXClient

class TestLFXClient(unittest.TestCase):
    def test_lfx_client_parsing(self):
        client = LFXClient()
        sample_response = {
            "projects": [
                {
                    "projectId": "123",
                    "name": "Jaeger Distributed Tracing Mentorship",
                    "slug": "jaeger-tracing",
                    "repoLink": "https://github.com/jaegertracing/jaeger",
                    "acceptApplications": True,
                    "createdOn": "2026-09-01 12:00:00 +0000",
                    "apprenticeNeeds": {
                        "skills": ["Go", "Distributed Tracing"],
                        "mentors": [{"name": "Yuri Shkuro", "introduction": "Maintainer"}]
                    },
                    "programTerms": [
                        {
                            "name": "Fall 2026",
                            "active": "active",
                            "applicationStartDate": 1788220800,
                            "applicationEndDate": 1790812800
                        }
                    ]
                },
                {
                    "projectId": "456",
                    "name": "Old Closed Mentorship",
                    "slug": "old-closed",
                    "repoLink": "https://github.com/org/closed",
                    "acceptApplications": False,
                    "createdOn": "2022-01-01 12:00:00 +0000",
                    "apprenticeNeeds": None,
                    "programTerms": [
                        {
                            "name": "Past Term",
                            "active": "closed",
                            "applicationStartDate": 10000,
                            "applicationEndDate": 20000
                        }
                    ]
                }
            ],
            "nextPageKey": None
        }

        with patch.object(client.session, 'get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = sample_response
            mock_get.return_value = mock_resp

            results = client.fetch_mentorship_projects(active_only=True)
            self.assertEqual(len(results), 1)
            item = results[0]
            self.assertEqual(item["source"], "LFX")
            self.assertEqual(item["repo"], "jaegertracing/jaeger")
            self.assertIn("Jaeger Distributed Tracing Mentorship", item["title"])
            self.assertIn("Go", item["language"])
            self.assertIn("lfx-mentorship", item["labels"])
            self.assertIn("jaeger-tracing", item["url"])

    def test_lfx_client_defensive_nulls(self):
        client = LFXClient()
        sample_response = {
            "projects": [
                {
                    "projectId": "999",
                    "name": "Defensive Nulls Project",
                    "slug": None,
                    "repoLink": None,
                    "acceptApplications": True,
                    "createdOn": None,
                    "apprenticeNeeds": None,
                    "programTerms": None
                }
            ],
            "nextPageKey": None
        }

        with patch.object(client.session, 'get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = sample_response
            mock_get.return_value = mock_resp

            results = client.fetch_mentorship_projects(active_only=True)
            self.assertEqual(len(results), 1)
            item = results[0]
            self.assertEqual(item["source"], "LFX")
            self.assertEqual(item["repo"], "LFX-Mentorship")
            self.assertIn("Defensive Nulls Project", item["title"])

if __name__ == "__main__":
    unittest.main()
