import unittest
from datetime import datetime, timezone

from tracker.html_renderer import format_last_updated, generate_html_page

class TestHTMLRendererLFX(unittest.TestCase):
    def test_last_updated_in_ist_and_utc(self):
        timestamp = datetime(2026, 9, 19, 13, 4, tzinfo=timezone.utc)
        self.assertEqual(
            format_last_updated(timestamp),
            "6:34 PM IST · 1:04 PM UTC",
        )

    def test_lfx_rendered_in_html(self):
        issues = [
            {
                "id": "lfx_1",
                "source": "LFX",
                "repo": "wasmedge/wasmedge",
                "number": 101,
                "title": "Implement LFX Mentorship Wasm plugin",
                "url": "https://github.com/wasmedge/wasmedge/issues/101",
                "language": "C++",
                "labels": ["lfx-mentorship"],
                "created_at": "2026-09-18T12:00:00Z",
                "comments": 1,
                "opened": "1d ago"
            }
        ]
        html = generate_html_page(issues)
        self.assertIn('data-source="LFX"', html)
        self.assertIn('id="count-lfx"', html)
        self.assertIn('text-purple', html)
        self.assertIn('wasmedge/wasmedge', html)

if __name__ == "__main__":
    unittest.main()
