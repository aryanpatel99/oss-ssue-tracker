#!/usr/bin/env python3
"""
CNCF Daily Issue Tracker — Main Entry Point
Scans top CNCF repositories for beginner-friendly & mentorship issues and updates README / reports.
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timezone
import yaml

from tracker.github_client import GitHubClient
from tracker.renderer import MarkdownRenderer
from tracker.notifier import Notifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cncf_tracker")


def load_config(config_path: str) -> dict:
    """Loads configuration from YAML file."""
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(
        description="CNCF Daily Issue Tracker for LFX Mentorship applicants."
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (default: config.yaml)",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=None,
        help="Number of past hours to search (overrides config default)",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="GitHub Personal Access Token (defaults to GITHUB_TOKEN env)",
    )
    parser.add_argument(
        "--update-readme",
        action="store_true",
        help="Update root README.md with latest issues dashboard",
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        default=True,
        help="Save report to reports/YYYY-MM-DD.md (default: True)",
    )
    parser.add_argument(
        "--no-report",
        dest="save_report",
        action="store_false",
        help="Do not save markdown report file",
    )
    parser.add_argument(
        "--reports-dir",
        default="reports",
        help="Directory to store daily archive digests (default: reports)",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Dispatch notifications via configured webhooks (Discord/Slack/Telegram)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and display issues to stdout without writing files",
    )

    args = parser.parse_args()

    project_root = os.path.dirname(os.path.abspath(__file__))
    config_path = (
        args.config
        if os.path.isabs(args.config)
        else os.path.join(project_root, args.config)
    )

    # Load configuration
    config = load_config(config_path)
    settings = config.get("settings", {})
    categories = config.get("categories", [])
    target_labels = config.get("target_labels", [])

    hours = args.hours or settings.get("default_hours", 28)
    batch_size = settings.get("github_search_batch_size", 6)
    max_per_project = settings.get("max_issues_per_project", 5)

    logger.info(f"Starting CNCF issue collection (window: past {hours} hours)...")

    # Initialize GitHub client
    client = GitHubClient(token=args.token)
    issues = client.fetch_recent_issues(
        categories=categories,
        target_labels=target_labels,
        hours=hours,
        max_per_project=max_per_project,
        batch_size=batch_size,
    )

    # Initialize Renderer
    renderer = MarkdownRenderer(issues=issues, hours=hours)

    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN: Rendered Output Preview")
        print("=" * 60 + "\n")
        print(renderer.render_body())
        return

    project_root = os.path.dirname(os.path.abspath(__file__))

    # Save daily digest archive
    if args.save_report:
        reports_dir = (
            args.reports_dir
            if os.path.isabs(args.reports_dir)
            else os.path.join(project_root, args.reports_dir)
        )
        os.makedirs(reports_dir, exist_ok=True)
        report_filename = f"{renderer.date_str}.md"
        report_path = os.path.join(reports_dir, report_filename)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(renderer.render_daily_report())
        logger.info(f"Daily digest saved to: {report_path}")

    # Update README.md
    if args.update_readme:
        readme_path = os.path.join(project_root, "README.md")
        if os.path.exists(readme_path):
            updated = renderer.update_readme(readme_path)
            if updated:
                logger.info(f"Updated dashboard in {readme_path}")
            else:
                logger.warning(f"Failed to update {readme_path}")
        else:
            logger.warning(f"{readme_path} not found. Skipped updating README.")

    # Send notifications
    if args.notify:
        notifier = Notifier()
        notifier.notify(issues=issues, hours=hours)

    logger.info(f"Done! Processed {len(issues)} issues successfully.")


if __name__ == "__main__":
    main()
