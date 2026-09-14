import os
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger("cncf_tracker")


class GitHubClient:
    """Client to query GitHub Search API for CNCF newcomer and mentorship issues."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "User-Agent": "CNCF-Daily-Issue-Tracker-LFX",
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            logger.info("GitHubClient initialized with authentication token.")
        else:
            logger.warning(
                "No GITHUB_TOKEN provided. Operating under strict unauthenticated rate limits (10 search req/min)."
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
            "per_page": 100,
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

    def fetch_recent_issues(
        self,
        categories: List[Dict[str, Any]],
        target_labels: List[str],
        hours: int = 28,
        max_per_project: int = 5,
        batch_size: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        Fetches issues opened in the last `hours` hours matching target labels.
        """
        since_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        since_iso = since_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Map repo -> metadata
        repo_metadata: Dict[str, Dict[str, Any]] = {}
        all_repos: List[str] = []

        for cat in categories:
            cat_name = cat.get("name", "Other")
            icon = cat.get("icon", "📦")
            for proj in cat.get("projects", []):
                repo = proj["repo"]
                all_repos.append(repo)
                repo_metadata[repo.lower()] = {
                    "repo": repo,
                    "category": cat_name,
                    "category_icon": icon,
                    "language": proj.get("language", "Unknown"),
                    "tier": proj.get("tier", "Incubating"),
                }

        # Deduplicate repos
        all_repos = list(dict.fromkeys(all_repos))
        logger.info(f"Monitoring {len(all_repos)} CNCF repositories across categories.")

        # Prepare label query part: label:"good first issue",label:"help wanted",...
        # In GitHub search: label:"good first issue","help wanted" matches any
        labels_query_str = " ".join([f'label:"{label}"' for label in target_labels[:5]])
        # We can also do a broad search or split by labels if needed

        collected_issues: Dict[str, Dict[str, Any]] = {}

        # Query in repo batches
        for i in range(0, len(all_repos), batch_size):
            repo_chunk = all_repos[i : i + batch_size]
            repo_filter = " ".join([f"repo:{r}" for r in repo_chunk])

            # Query: repo:a repo:b is:issue is:open created:>=TIMESTAMP
            query = f"{repo_filter} is:issue is:open created:>={since_iso}"
            logger.info(f"Querying batch {i // batch_size + 1}: {len(repo_chunk)} repos...")

            items = self.search_issues(query)

            # Filter issues by target newcomer/mentorship labels
            lower_target_labels = [l.lower() for l in target_labels]

            for item in items:
                # Check labels
                item_labels = [lbl.get("name", "") for lbl in item.get("labels", [])]
                item_labels_lower = [lbl.lower() for lbl in item_labels]

                # If the issue matches ANY newcomer label OR is in mentorship repo
                is_match = False
                matched_label = None

                for target_lbl in lower_target_labels:
                    for ilbl in item_labels_lower:
                        if target_lbl in ilbl:
                            is_match = True
                            matched_label = ilbl
                            break
                    if is_match:
                        break

                # Extract repo owner/name
                html_url = item.get("html_url", "")
                parts = html_url.split("/")
                if len(parts) >= 5:
                    repo_slug = f"{parts[3]}/{parts[4]}".lower()
                else:
                    repo_slug = ""

                # Special exception: all issues in cncf/mentoring are mentorship-related
                if repo_slug == "cncf/mentoring":
                    is_match = True

                if is_match:
                    issue_id = item["id"]
                    if issue_id not in collected_issues:
                        meta = repo_metadata.get(
                            repo_slug,
                            {
                                "repo": repo_slug,
                                "category": "Other",
                                "category_icon": "📦",
                                "language": "Unknown",
                                "tier": "CNCF",
                            },
                        )

                        collected_issues[issue_id] = {
                            "id": issue_id,
                            "number": item.get("number"),
                            "title": item.get("title"),
                            "url": html_url,
                            "repo": meta["repo"],
                            "category": meta["category"],
                            "category_icon": meta["category_icon"],
                            "language": meta["language"],
                            "tier": meta["tier"],
                            "labels": item_labels,
                            "created_at": item.get("created_at"),
                            "comments": item.get("comments", 0),
                            "author": item.get("user", {}).get("login", "unknown"),
                        }

            # Sleep slightly to respect rate limits
            time.sleep(1.8)

        # Global LFX mentorship search across all GitHub to catch untracked CNCF orgs!
        logger.info("Running global LFX mentorship issue search...")
        lfx_query = f'is:issue is:open created:>={since_iso} (label:"lfx-mentorship" OR label:"lfx")'
        lfx_items = self.search_issues(lfx_query)
        for item in lfx_items:
            issue_id = item["id"]
            if issue_id not in collected_issues:
                html_url = item.get("html_url", "")
                parts = html_url.split("/")
                repo_slug = f"{parts[3]}/{parts[4]}" if len(parts) >= 5 else "unknown"
                meta = repo_metadata.get(
                    repo_slug.lower(),
                    {
                        "repo": repo_slug,
                        "category": "LFX Mentorship Hub",
                        "category_icon": "🎓",
                        "language": "Multi",
                        "tier": "Mentorship",
                    },
                )
                collected_issues[issue_id] = {
                    "id": issue_id,
                    "number": item.get("number"),
                    "title": item.get("title"),
                    "url": html_url,
                    "repo": meta["repo"],
                    "category": meta["category"],
                    "category_icon": meta["category_icon"],
                    "language": meta["language"],
                    "tier": meta["tier"],
                    "labels": [lbl.get("name", "") for lbl in item.get("labels", [])],
                    "created_at": item.get("created_at"),
                    "comments": item.get("comments", 0),
                    "author": item.get("user", {}).get("login", "unknown"),
                }

        results = list(collected_issues.values())
        logger.info(f"Total matching newcomer & mentorship issues found: {len(results)}")
        return results
