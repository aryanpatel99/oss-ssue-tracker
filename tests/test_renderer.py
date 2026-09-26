import tempfile
import unittest
from pathlib import Path

from tracker.renderer import MarkdownRenderer


class TestMarkdownRenderer(unittest.TestCase):
    def test_update_readme_preserves_backslashes_from_issue_title(self):
        issue = {
            "source": "Test",
            "repo": "example/project",
            "number": 1,
            "title": r"Windows path C:\Users\example",
            "url": "https://github.com/example/project/issues/1",
            "language": "Python",
            "labels": [],
            "created_at": "2026-09-26T00:00:00Z",
            "comments": 0,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = Path(temp_dir) / "README.md"
            readme_path.write_text(
                "<!-- CNCF_TRACKER_START -->\nold\n<!-- CNCF_TRACKER_END -->\n",
                encoding="utf-8",
            )

            MarkdownRenderer([issue]).update_readme(str(readme_path))

            self.assertIn(issue["title"], readme_path.read_text(encoding="utf-8"))
