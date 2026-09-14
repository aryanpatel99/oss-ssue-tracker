import os
import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from dateutil import parser


def relative_time(iso_str: str) -> str:
    """Converts ISO timestamp to human-friendly relative time (e.g., '3h ago')."""
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
        return iso_str[:10] if iso_str else "recent"


def clean_markdown_cell(text: str) -> str:
    """Escapes pipes and removes newlines for GitHub markdown table cells."""
    if not text:
        return ""
    text = text.replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    # Truncate if exceedingly long
    if len(text) > 85:
        return text[:82] + "..."
    return text


def format_labels(labels: List[str]) -> str:
    """Formats issue labels into clean code blocks or badges."""
    # Prioritize interesting labels
    priority_keywords = ["good first", "help wanted", "lfx", "mentorship", "easy", "documentation"]
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
    """Renders issue collections into daily digests and updates repository README."""

    def __init__(self, issues: List[Dict[str, Any]], hours: int = 28):
        self.issues = issues
        self.hours = hours
        self.now_utc = datetime.now(timezone.utc)
        self.date_str = self.now_utc.strftime("%Y-%m-%d")
        self.timestamp_str = self.now_utc.strftime("%Y-%m-%d %H:%M UTC")

    def build_summary_stats(self) -> str:
        """Generates summary metrics breakdown."""
        total = len(self.issues)
        languages: Dict[str, int] = {}
        tiers: Dict[str, int] = {}

        for iss in self.issues:
            lang = iss.get("language", "Other")
            tier = iss.get("tier", "Other")
            languages[lang] = languages.get(lang, 0) + 1
            tiers[tier] = tiers.get(tier, 0) + 1

        lang_str = " • ".join([f"**{lang}**: {count}" for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True)])
        tier_str = " • ".join([f"**{tier}**: {count}" for tier, count in sorted(tiers.items(), key=lambda x: x[1], reverse=True)])

        lines = [
            f"> 🕒 **Last updated**: `{self.timestamp_str}` (looking back {self.hours} hours)",
            f"> 🎯 **Total newcomer & mentorship issues found**: `{total}`",
        ]
        if languages:
            lines.append(f"> 💻 **Languages**: {lang_str}")
        if tiers:
            lines.append(f"> 🏛️ **CNCF Tiers**: {tier_str}")

        return "\n".join(lines)

    def render_issues_table(self, issues_list: List[Dict[str, Any]]) -> str:
        """Renders an issue list into a Markdown table."""
        if not issues_list:
            return "_No new issues matching beginner/mentorship criteria in this window._\n"

        lines = [
            "| Project | Issue Title | Stack | Labels | Opened | Comments |",
            "| :--- | :--- | :---: | :--- | :---: | :---: |",
        ]

        for iss in issues_list:
            repo_link = f"[{iss['repo']}](https://github.com/{iss['repo']})"
            title_escaped = clean_markdown_cell(iss['title'])
            issue_link = f"[#{iss['number']} {title_escaped}]({iss['url']})"
            lang_badge = f"`{iss['language']}`"
            labels_str = format_labels(iss['labels'])
            opened_str = relative_time(iss['created_at'])
            comments_str = f"💬 {iss['comments']}" if iss['comments'] > 0 else "-"

            lines.append(
                f"| {repo_link} | {issue_link} | {lang_badge} | {labels_str} | {opened_str} | {comments_str} |"
            )

        return "\n".join(lines) + "\n"

    def render_body(self) -> str:
        """Renders the core issue dashboard grouped by category."""
        lines = []
        lines.append(self.build_summary_stats())
        lines.append("\n---\n")

        if not self.issues:
            lines.append("### 😴 Quiet Day in Cloud Native\n")
            lines.append(
                "No newly created issues with newcomer/mentorship labels were detected in the tracked projects over the last "
                f"{self.hours} hours. Check past archives in the `reports/` folder!\n"
            )
            return "\n".join(lines)

        # Group by category
        categories: Dict[str, Dict[str, Any]] = {}
        for iss in self.issues:
            cat_name = iss.get("category", "General")
            if cat_name not in categories:
                categories[cat_name] = {
                    "icon": iss.get("category_icon", "📦"),
                    "issues": [],
                }
            categories[cat_name]["issues"].append(iss)

        # Render each category
        for cat_name, cat_data in categories.items():
            lines.append(f"### {cat_data['icon']} {cat_name} ({len(cat_data['issues'])})\n")
            lines.append(self.render_issues_table(cat_data["issues"]))
            lines.append("")

        return "\n".join(lines)

    def render_daily_report(self) -> str:
        """Renders the standalone daily digest file."""
        content = [
            f"# 📅 CNCF Daily Issue Digest — {self.date_str}\n",
            self.render_body(),
            "\n---",
            "*Generated automatically by [CNCF Issue Tracker for LFX Mentorship](https://github.com).* \n",
        ]
        return "\n".join(content)

    def update_readme(self, readme_path: str) -> bool:
        """Updates the README.md content between marker tags."""
        start_marker = "<!-- CNCF_TRACKER_START -->"
        end_marker = "<!-- CNCF_TRACKER_END -->"

        if not os.path.exists(readme_path):
            return False

        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        if start_marker not in content or end_marker not in content:
            # Append markers at the bottom if missing
            content += f"\n\n{start_marker}\n{end_marker}\n"

        replacement = f"{start_marker}\n\n{self.render_body()}\n{end_marker}"
        pattern = re.compile(f"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.DOTALL)
        new_content = pattern.sub(replacement, content)

        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return True
