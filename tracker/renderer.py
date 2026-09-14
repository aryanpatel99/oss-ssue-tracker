import os
import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from dateutil import parser


def relative_time(iso_str: str) -> str:
    """Converts ISO timestamp to relative time (e.g., '3h ago')."""
    try:
        dt = parser.isoparse(iso_str)
        now = datetime.now(timezone.utc)
        diff = now - dt

        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "just now"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"
    except Exception:
        return iso_str[:10] if iso_str else ""


def clean_markdown_cell(text: str) -> str:
    """Escapes pipes and removes newlines for Markdown table cells."""
    if not text:
        return ""
    text = text.replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    if len(text) > 90:
        return text[:87] + "..."
    return text.strip()


def format_labels(labels: List[str]) -> str:
    """Formats issue labels into simple code spans."""
    priority_keywords = ["good first", "help wanted", "lfx", "mentorship", "easy"]
    sorted_labels = sorted(
        labels,
        key=lambda l: any(k in l.lower() for k in priority_keywords),
        reverse=True,
    )
    formatted = [f"`{clean_markdown_cell(l)}`" for l in sorted_labels[:3]]
    if len(labels) > 3:
        formatted.append(f"+{len(labels) - 3}")
    return " ".join(formatted) if formatted else "-"


class MarkdownRenderer:
    """Renders issue tables with zero extra fluff or emojis."""

    def __init__(self, issues: List[Dict[str, Any]], hours: int = 28):
        self.issues = issues
        self.hours = hours
        self.now_utc = datetime.now(timezone.utc)
        self.date_str = self.now_utc.strftime("%Y-%m-%d")

    def render_body(self) -> str:
        """Renders pure issue table without emojis or filler text."""
        if not self.issues:
            return f"_No new issues in the last {self.hours} hours._\n"

        lines = [
            "| Project | Issue | Stack | Labels | Opened |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        # Sort issues by creation time descending
        sorted_issues = sorted(
            self.issues,
            key=lambda x: x.get("created_at", ""),
            reverse=True,
        )

        for iss in sorted_issues:
            repo_link = f"[{iss['repo']}](https://github.com/{iss['repo']})"
            title = clean_markdown_cell(iss["title"])
            issue_link = f"[#{iss['number']} {title}]({iss['url']})"
            stack = iss.get("language", "-")
            labels = format_labels(iss.get("labels", []))
            opened = relative_time(iss.get("created_at", ""))

            lines.append(f"| {repo_link} | {issue_link} | {stack} | {labels} | {opened} |")

        return "\n".join(lines) + "\n"

    def render_daily_report(self) -> str:
        """Renders a minimal daily report."""
        return f"# Issues - {self.date_str}\n\n{self.render_body()}"

    def update_readme(self, readme_path: str) -> bool:
        """Updates the README.md content between marker tags."""
        start_marker = "<!-- CNCF_TRACKER_START -->"
        end_marker = "<!-- CNCF_TRACKER_END -->"

        if not os.path.exists(readme_path):
            return False

        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        if start_marker not in content or end_marker not in content:
            content += f"\n\n{start_marker}\n{end_marker}\n"

        replacement = f"{start_marker}\n\n{self.render_body()}\n{end_marker}"
        pattern = re.compile(f"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.DOTALL)
        new_content = pattern.sub(replacement, content)

        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return True
