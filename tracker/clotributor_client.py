import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import requests

logger = logging.getLogger("cncf_tracker")


class ClotributorClient:
    """Client for Clotributor API (tracks CNCF issues with has_linked_prs status)."""

    BASE_URL = "https://clotributor.dev/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CNCF-Issue-Tracker/1.0",
            "Accept": "application/json",
        })

    def fetch_recent_issues(
        self,
        days_back: int = 7,
        require_no_linked_prs: bool = True,
        max_pages: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Fetches newcomer CNCF issues from Clotributor.
        Guarantees has_linked_prs == False when require_no_linked_prs is True.
        """
        since_time = datetime.now(timezone.utc) - timedelta(days=days_back)
        since_timestamp = int(since_time.timestamp())

        results = []
        seen_urls = set()

        for page in range(1, max_pages + 1):
            url = f"{self.BASE_URL}/issues/search"
            params = {
                "foundation": "cncf",
                "page": page,
                "limit": 50,
            }

            try:
                resp = self.session.get(url, params=params, timeout=12)
                if resp.status_code != 200:
                    logger.warning(f"Clotributor returned status {resp.status_code}")
                    break

                items = resp.json()
                if not items:
                    break

                for item in items:
                    # Filter by linked PRs
                    if require_no_linked_prs and item.get("has_linked_prs") is True:
                        continue

                    # Filter by published time
                    published_at = item.get("published_at", 0)
                    if published_at and published_at < since_timestamp:
                        continue

                    issue_url = item.get("url", "")
                    if not issue_url or issue_url in seen_urls:
                        continue
                    seen_urls.add(issue_url)

                    # Extract language
                    repo_info = item.get("repository", {})
                    languages = repo_info.get("languages", [])
                    primary_lang = languages[0] if languages else "Go"

                    # Convert timestamp to ISO string
                    created_iso = ""
                    if published_at:
                        created_iso = datetime.fromtimestamp(
                            published_at, tz=timezone.utc
                        ).strftime("%Y-%m-%dT%H:%M:%SZ")

                    repo_name = repo_info.get("name", "")
                    # Extract full repo name from url
                    parts = issue_url.split("/")
                    full_repo = f"{parts[3]}/{parts[4]}" if len(parts) >= 5 else repo_name

                    results.append({
                        "id": f"clotributor_{item.get('number')}_{full_repo}",
                        "source": "CNCF",
                        "repo": full_repo,
                        "number": item.get("number"),
                        "title": item.get("title", ""),
                        "url": issue_url,
                        "language": primary_lang,
                        "labels": item.get("labels", []),
                        "created_at": created_iso,
                        "comments": item.get("comments", 0),
                    })

            except requests.RequestException as e:
                logger.error(f"Failed to fetch from Clotributor: {e}")
                break

        logger.info(f"Clotributor returned {len(results)} qualifying CNCF issues (no PRs linked).")
        return results
