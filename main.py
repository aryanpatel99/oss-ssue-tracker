#!/usr/bin/env python3
"""
CNCF & YC Startup Issue Tracker
Scans CNCF projects and high-growth YC open-source startups for open issues
with active discussions, unassigned status, and no linked pull requests.
"""

import os
import sys
import argparse
import logging
import yaml

from tracker.github_client import GitHubClient
from tracker.clotributor_client import ClotributorClient
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
        description="Tracks CNCF and YC open source startup issues with active discussions and no PRs."
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (default: config.yaml)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Lookback window in days (overrides config days_back)",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=None,
        help="Lookback window in hours (overrides --days and config days_back)",
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
        help="Update root README.md with latest issues table",
    )
    parser.add_argument(
        "--update-html",
        action="store_true",
        default=True,
        help="Update root index.html with interactive issue dashboard (default: True)",
    )
    parser.add_argument(
        "--no-html",
        dest="update_html",
        action="store_false",
        help="Do not update index.html",
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
        help="Dispatch notifications via configured webhooks",
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
    cncf_projects = config.get("cncf_projects", [])
    startup_projects = config.get("startup_projects", [])
    target_labels = config.get("target_labels", [])

    if args.hours is not None:
        hours_back = args.hours
        days_back = args.hours / 24.0
    elif args.days is not None:
        hours_back = int(args.days * 24)
        days_back = float(args.days)
    else:
        cfg_days = settings.get("days_back", 7)
        days_back = float(cfg_days)
        hours_back = int(cfg_days * 24)
    min_comments = settings.get("min_comments", 1)
    max_comments = settings.get("max_comments", 6)
    require_unassigned = settings.get("require_unassigned", True)
    require_no_linked_prs = settings.get("require_no_linked_prs", True)
    batch_size = settings.get("github_search_batch_size", 5)

    all_issues = []
    seen_urls = set()

    # 1. Fetch CNCF issues from Clotributor (verified has_linked_prs: false)
    logger.info("Fetching CNCF issues from Clotributor API (no linked PRs)...")
    clotributor = ClotributorClient()
    clotributor_issues = clotributor.fetch_recent_issues(
        days_back=days_back,
        require_no_linked_prs=require_no_linked_prs,
    )
    for iss in clotributor_issues:
        url = iss.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            all_issues.append(iss)

    # 2. Fetch YC & Emerging Startup issues from GitHub API
    logger.info("Fetching YC & Emerging Open-Source Startup issues from GitHub...")
    github_client = GitHubClient(token=args.token)
    startup_issues = github_client.fetch_startup_issues(
        startup_projects=startup_projects,
        days_back=days_back,
        min_comments=min_comments,
        max_comments=max_comments,
        require_unassigned=require_unassigned,
        require_no_linked_prs=require_no_linked_prs,
        batch_size=batch_size,
    )
    for iss in startup_issues:
        url = iss.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            all_issues.append(iss)

    # 3. Supplement with direct CNCF GitHub search
    logger.info("Checking direct CNCF repositories on GitHub...")
    cncf_gh_issues = github_client.fetch_cncf_issues(
        cncf_projects=cncf_projects,
        target_labels=target_labels,
        days_back=days_back,
        batch_size=batch_size,
    )
    for iss in cncf_gh_issues:
        url = iss.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            all_issues.append(iss)

    logger.info(f"Total deduplicated issues found across all sources: {len(all_issues)}")

    # Initialize Renderer
    renderer = MarkdownRenderer(issues=all_issues, days_back=days_back, hours=args.hours)

    if args.dry_run:
        print("\n" + "=" * 60)
        print("Rendered Issues Table Preview")
        print("=" * 60 + "\n")
        print(renderer.render_body())
        return

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
                logger.info(f"Updated issues table in {readme_path}")
            else:
                logger.warning(f"Failed to update {readme_path}")
        else:
            logger.warning(f"{readme_path} not found. Skipped updating README.")

    # Update index.html
    if args.update_html:
        html_path = os.path.join(project_root, "index.html")
        if renderer.update_html(html_path):
            logger.info(f"Updated interactive HTML dashboard in {html_path}")
        else:
            logger.warning(f"Failed to update {html_path}")

    # Send notifications
    if args.notify:
        notifier = Notifier()
        notifier.notify(issues=all_issues, hours=hours_back)

    logger.info(f"Completed! Processed {len(all_issues)} issues.")


if __name__ == "__main__":
    main()
