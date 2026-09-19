import unittest
from tracker.html_renderer import generate_html_page

class TestHTMLRendererLFX(unittest.TestCase):
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
