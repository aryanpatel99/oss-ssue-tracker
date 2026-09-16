import os
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Union
import requests

logger = logging.getLogger("cncf_tracker")


class GitHubClient:
    """Client to query GitHub Search API for CNCF and YC/OSS startup issues."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "User-Agent": "CNCF-Startup-Issue-Tracker",
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            logger.info("GitHubClient initialized with authentication token.")
        else:
            logger.warning(
                "No GITHUB_TOKEN provided. Operating under unauthenticated rate limits (10 search req/min)."
            )

    def _handle_rate_limit(self, response: requests.Response) -> None:
        """Inspect headers and wait if rate limit is reached."""
        remaining = response.headers.get("x-ratelimit-remaining")
        reset_time = response.headers.get("x-ratelimit-reset")

        if remaining is not None and int(remaining) == 0:
            if reset_time:
                wait_seconds = max(int(reset_time) - int(time.time()) + 2, 5)
                logger.warning(
                    f"Rate limit reached. Waiting {wait_seconds} seconds until reset..."
                )
                time.sleep(wait_seconds)

    def search_issues(self, query: str) -> List[Dict[str, Any]]:
        """Executes a search query against GitHub Search API."""
        url = f"{self.BASE_URL}/search/issues"
        params = {
            "q": query,
            "sort": "created",
            "order": "desc",
            "per_page": 50,
        }

        try:
            resp = self.session.get(url, params=params, timeout=15)
            self._handle_rate_limit(resp)

            if resp.status_code == 200:
                data = resp.json()
                return data.get("items", [])
            elif resp.status_code == 403:
                logger.error(f"GitHub API 403 Forbidden: {resp.text}")
                return []
            elif resp.status_code == 422:
                logger.error(f"GitHub API 422 Unprocessable Query: {query} -> {resp.text}")
                return []
            else:
                logger.error(f"GitHub API returned {resp.status_code}: {resp.text}")
                return []
        except requests.RequestException as e:
            logger.error(f"Network error querying GitHub API: {e}")
            return []

    def has_linked_pr(self, owner: str, repo: str, issue_number: int) -> bool:
        """
        Checks whether any pull request is already linked/cross-referenced to this issue.
        Uses GitHub Timeline API if authenticated.
        """
        if not self.token:
            return False  # Avoid burning unauthenticated rate limits on timeline calls

        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{issue_number}/timeline"
        try:
            resp = self.session.get(url, timeout=10)
            self._handle_rate_limit(resp)
            if resp.status_code == 200:
                events = resp.json()
                for ev in events:
                    # Look for cross-referenced pull requests
                    if ev.get("event") == "cross-referenced":
                        source = ev.get("source", {})
                        issue = source.get("issue", {})
                        if issue.get("pull_request") is not None:
                            return True
            return False
        except Exception:
            return False

    def fetch_startup_issues(
        self,
        startup_projects: List[Dict[str, Any]],
        days_back: Union[int, float] = 7,
        min_comments: int = 1,
        max_comments: int = 6,
        require_unassigned: bool = True,
        require_no_linked_prs: bool = True,
        batch_size: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Fetches issues from YC / OSS startups with active discussion (1-6 comments),
        unassigned, and without an open PR.
        """
        since_time = datetime.now(timezone.utc) - timedelta(days=days_back)
        since_iso = since_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        repo_metadata = {
            proj["repo"].lower(): {
                "company": proj.get("company", proj["repo"]),
                "language": proj.get("language", "Unknown"),
            }
            for proj in startup_projects
        }

        all_repos = [p["repo"] for p in startup_projects]
        collected = []
        seen_urls = set()

        assignee_filter = "no:assignee " if require_unassigned else ""
        comments_filter = f"comments:{min_comments}..{max_comments} "

        window_display = (
            f"{int(days_back * 24)}h"
            if (isinstance(days_back, float) and not days_back.is_integer()) or days_back < 1
            else f"{int(days_back)}d"
        )
        logger.info(
            f"Querying {len(all_repos)} YC/OSS startups (past {window_display}, {min_comments}-{max_comments} comments, unassigned)..."
        )

        for i in range(0, len(all_repos), batch_size):
            chunk = all_repos[i : i + batch_size]
            repo_filter = " ".join([f"repo:{r}" for r in chunk])

            # Query: repo:a repo:b is:issue is:open no:assignee comments:1..6 created:>=ISO
            query = (
                f"{repo_filter} is:issue is:open {assignee_filter}{comments_filter}created:>={since_iso}"
            )
            items = self.search_issues(query)

            for item in items:
                # Ensure it's not a PR
                if item.get("pull_request") is not None:
                    continue

                html_url = item.get("html_url", "")
                if not html_url or html_url in seen_urls:
                    continue

                # Ensure unassigned
                if require_unassigned and item.get("assignees"):
                    continue

                parts = html_url.split("/")
                if len(parts) < 5:
                    continue
                owner = parts[3]
                repo_name = parts[4]
                full_repo = f"{owner}/{repo_name}"

                issue_num = item.get("number")

                # Check if a PR is already linked
                if require_no_linked_prs and self.token:
                    if self.has_linked_pr(owner, repo_name, issue_num):
                        continue

                seen_urls.add(html_url)
                meta = repo_metadata.get(
                    full_repo.lower(),
                    {"company": full_repo, "language": "Multi"},
                )

                item_labels = [lbl.get("name", "") for lbl in item.get("labels", [])]

                collected.append({
                    "id": item["id"],
                    "source": "Startup",
                    "company": meta["company"],
                    "repo": full_repo,
                    "number": issue_num,
                    "title": item.get("title", ""),
                    "url": html_url,
                    "language": meta["language"],
                    "labels": item_labels,
                    "created_at": item.get("created_at"),
                    "comments": item.get("comments", 0),
                })

            time.sleep(1.5)

        logger.info(f"Found {len(collected)} qualifying YC/startup issues with active discussions.")
        return collected

    def fetch_foundation_issues(
        self,
        projects: List[Dict[str, Any]],
        target_labels: List[str],
        source: str = "CNCF",
        default_language: str = "Go",
        days_back: Union[int, float] = 7,
        batch_size: int = 6,
    ) -> List[Dict[str, Any]]:
        """Fetches newcomer & mentorship issues from foundation repos (CNCF, ASWF, etc.) via GitHub API."""
        since_time = datetime.now(timezone.utc) - timedelta(days=days_back)
        since_iso = since_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        repo_metadata = {
            p["repo"].lower(): {
                "repo": p["repo"],
                "language": p.get("language", default_language),
            }
            for p in projects
        }

        all_repos = [p["repo"] for p in projects]
        collected = []
        seen_urls = set()

        lower_target_labels = [l.lower() for l in target_labels]

        for i in range(0, len(all_repos), batch_size):
            chunk = all_repos[i : i + batch_size]
            repo_filter = " ".join([f"repo:{r}" for r in chunk])
            query = f"{repo_filter} is:issue is:open created:>={since_iso}"

            items = self.search_issues(query)
            for item in items:
                if item.get("pull_request") is not None:
                    continue

                html_url = item.get("html_url", "")
                if not html_url or html_url in seen_urls:
                    continue

                item_labels = [lbl.get("name", "") for lbl in item.get("labels", [])]
                item_labels_lower = [lbl.lower() for lbl in item_labels]

                # Match labels
                is_match = False
                for target_lbl in lower_target_labels:
                    if any(target_lbl in ilbl for ilbl in item_labels_lower):
                        is_match = True
                        break

                parts = html_url.split("/")
                full_repo = f"{parts[3]}/{parts[4]}" if len(parts) >= 5 else ""

                if full_repo.lower() in ("cncf/mentoring", "academysoftwarefoundation/tac"):
                    is_match = True

                if is_match:
                    seen_urls.add(html_url)
                    meta = repo_metadata.get(
                        full_repo.lower(),
                        {"repo": full_repo, "language": default_language},
                    )
                    collected.append({
                        "id": item["id"],
                        "source": source,
                        "company": full_repo,
                        "repo": full_repo,
                        "number": item.get("number"),
                        "title": item.get("title", ""),
                        "url": html_url,
                        "language": meta["language"],
                        "labels": item_labels,
                        "created_at": item.get("created_at"),
                        "comments": item.get("comments", 0),
                    })

            time.sleep(1.5)

        return collected

    def fetch_cncf_issues(
        self,
        cncf_projects: List[Dict[str, Any]],
        target_labels: List[str],
        days_back: Union[int, float] = 7,
        batch_size: int = 6,
    ) -> List[Dict[str, Any]]:
        """Fetches newcomer & mentorship issues from CNCF repos via GitHub API."""
        return self.fetch_foundation_issues(
            projects=cncf_projects,
            target_labels=target_labels,
            source="CNCF",
            default_language="Go",
            days_back=days_back,
            batch_size=batch_size,
        )

    def fetch_aswf_issues(
        self,
        aswf_projects: List[Dict[str, Any]],
        target_labels: List[str],
        days_back: Union[int, float] = 7,
        batch_size: int = 6,
    ) -> List[Dict[str, Any]]:
        """Fetches newcomer & mentorship issues from ASWF repos via GitHub API."""
        return self.fetch_foundation_issues(
            projects=aswf_projects,
            target_labels=target_labels,
            source="ASWF",
            default_language="C++",
            days_back=days_back,
            batch_size=batch_size,
        )
