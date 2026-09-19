import logging
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger("cncf_tracker")


class LFXClient:
    """Client for the official LFX Mentorship API (https://api.mentorship.lfx.linuxfoundation.org)."""

    BASE_URL = "https://api.mentorship.lfx.linuxfoundation.org/projects"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CNCF-Issue-Tracker/1.0",
            "Accept": "application/json",
        })

    def _is_project_active(self, project: Dict[str, Any], now_timestamp: int) -> bool:
        """Determines whether an LFX project is actively accepting mentees/applications."""
        if project.get("acceptApplications") is True:
            return True

        terms = project.get("programTerms") or []
        for term in terms:
            if not isinstance(term, dict):
                continue
            if term.get("active") == "active":
                return True

            app_start = term.get("applicationStartDate")
            app_end = term.get("applicationEndDate")
            if app_start and app_end:
                if app_start <= now_timestamp <= app_end:
                    return True

        return False

    def _normalize_repo(self, repo_link: Optional[str]) -> str:
        """Extracts owner/repo from a repository URL."""
        if not repo_link:
            return "LFX-Mentorship"

        cleaned = repo_link.strip().rstrip("/")
        if cleaned.endswith(".git"):
            cleaned = cleaned[:-4]

        parts = cleaned.split("/")
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"
        return cleaned

    def fetch_mentorship_projects(
        self,
        active_only: bool = True,
        max_pages: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Fetches mentorship projects from the LFX Mentorship API.
        Returns standardized issue dictionaries matching the tracker schema.
        """
        now_utc = datetime.now(timezone.utc)
        now_timestamp = int(now_utc.timestamp())

        results = []
        next_key = None

        for page in range(1, max_pages + 1):
            params = {"limit": 50}
            if next_key:
                params["nextPageKey"] = next_key

            try:
                resp = self.session.get(self.BASE_URL, params=params, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"LFX API returned status {resp.status_code}")
                    break

                data = resp.json()
                projects = data.get("projects", [])
                if not projects:
                    break

                for proj in projects:
                    if not isinstance(proj, dict):
                        continue

                    if active_only and not self._is_project_active(proj, now_timestamp):
                        continue

                    project_id = proj.get("projectId") or "lfx_unknown"
                    name = proj.get("name") or "Unnamed Mentorship Project"
                    slug = proj.get("slug")
                    repo_link = proj.get("repoLink") or ""
                    clean_repo = self._normalize_repo(repo_link)

                    apprentice_needs = proj.get("apprenticeNeeds") or {}
                    skills = apprentice_needs.get("skills") or []
                    mentors = apprentice_needs.get("mentors") or []

                    primary_lang = skills[0] if skills else "Multi"

                    labels = ["lfx-mentorship", "mentorship"]
                    for s in skills[:3]:
                        if s not in labels:
                            labels.append(s)

                    url = (
                        f"https://mentorship.lfx.linuxfoundation.org/#/project/{slug}"
                        if slug
                        else repo_link or "https://mentorship.lfx.linuxfoundation.org"
                    )

                    created_on = proj.get("createdOn") or now_utc.strftime("%Y-%m-%d %H:%M:%S +0000")
                    created_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
                    try:
                        # Attempt to parse '2026-09-01 12:00:00 +0000'
                        dt = datetime.strptime(created_on[:19], "%Y-%m-%d %H:%M:%S")
                        created_iso = dt.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    except Exception:
                        pass

                    results.append({
                        "id": f"lfx_{project_id}",
                        "source": "LFX",
                        "company": "Linux Foundation",
                        "repo": clean_repo,
                        "number": len(results) + 1,
                        "title": f"[Mentorship] {name}",
                        "url": url,
                        "language": primary_lang,
                        "labels": labels,
                        "created_at": created_iso,
                        "comments": len(mentors),
                    })

                next_key = data.get("nextPageKey")
                if not next_key:
                    break

            except Exception as e:
                logger.error(f"Error querying LFX API: {e}")
                break

        logger.info(f"LFXClient fetched {len(results)} mentorship projects (active_only={active_only}).")
        return results
