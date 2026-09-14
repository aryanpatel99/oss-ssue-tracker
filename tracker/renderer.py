import os
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from dateutil import parser


def relative_time(iso_str: str) -> str:
    """Converts ISO timestamp to relative time (e.g., '3d ago')."""
    if not iso_str:
        return "-"
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
        return iso_str[:10] if iso_str else "-"


def clean_markdown_cell(text: str) -> str:
    """Escapes pipes and removes newlines for Markdown table cells."""
    if not text:
        return ""
    text = text.replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    text = text.replace("{{", "{ {").replace("}}", "} }").replace("{%", "{ %").replace("%}", "% }")
    if len(text) > 85:
        return text[:82] + "..."
    return text.strip()


def format_labels(labels: List[str]) -> str:
    """Formats issue labels into simple code spans."""
    priority_keywords = ["good first", "help wanted", "lfx", "mentorship", "easy", "bug", "enhancement"]
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
    """Renders unified issues table across CNCF and YC/OSS Startups."""

    def __init__(
        self,
        issues: List[Dict[str, Any]],
        days_back: Union[int, float] = 7,
        hours: Optional[int] = None,
    ):
        self.issues = issues
        self.days_back = days_back
        self.hours = hours
        self.now_utc = datetime.now(timezone.utc)
        self.date_str = self.now_utc.strftime("%Y-%m-%d")

    def render_body(self) -> str:
        """Renders pure issue table without emojis or filler text."""
        if not self.issues:
            if self.hours:
                window_desc = f"{self.hours} hours"
            elif isinstance(self.days_back, float) and self.days_back.is_integer():
                window_desc = f"{int(self.days_back)} days"
            else:
                window_desc = f"{self.days_back} days"
            return f"_No open issues without PRs found in the last {window_desc}._\n"

        lines = [
            "| Source | Project | Issue | Stack | Labels | Opened | Comments |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :---: |",
        ]

        # Sort issues by creation date descending
        sorted_issues = sorted(
            self.issues,
            key=lambda x: x.get("created_at", ""),
            reverse=True,
        )

        for iss in sorted_issues:
            source = iss.get("source", "OSS")
            repo = iss.get("repo", "")
            repo_link = f"[{repo}](https://github.com/{repo})"
            title = clean_markdown_cell(iss.get("title", ""))
            issue_link = f"[#{iss['number']} {title}]({iss['url']})"
            stack = iss.get("language", "-")
            labels = format_labels(iss.get("labels", []))
            opened = relative_time(iss.get("created_at", ""))
            comments = iss.get("comments", 0)
            comments_str = str(comments) if comments > 0 else "-"

            lines.append(
                f"| {source} | {repo_link} | {issue_link} | {stack} | {labels} | {opened} | {comments_str} |"
            )

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

    def render_html(self) -> str:
        """Renders complete standalone index.html page."""
        from .html_renderer import generate_html_page
        enriched_issues = []
        for iss in self.issues:
            iss_copy = dict(iss)
            if "opened" not in iss_copy:
                iss_copy["opened"] = relative_time(iss.get("created_at", ""))
            enriched_issues.append(iss_copy)
        return generate_html_page(
            enriched_issues,
            last_updated=self.now_utc.strftime("%Y-%m-%d %H:%M UTC")
        )

    def update_html(self, html_path: str) -> bool:
        """Updates or generates index.html page."""
        try:
            content = self.render_html()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False

