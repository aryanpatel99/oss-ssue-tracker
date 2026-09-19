# LFX Mentorship Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ingest LFX Mentorship projects and high-frequency LFX GitHub repository issues into the tracker pipeline, adding a dedicated "LFX" filter and purple card styling to the dashboard.

**Architecture:** A hybrid model where `tracker/lfx_client.py` queries the official LFX Mentorship API (`https://api.mentorship.lfx.linuxfoundation.org/projects`) for active mentorship postings and student applications, while `tracker/github_client.py` scans top curated LFX repositories in `config.yaml` for newcomer/mentorship labels (`lfx-mentorship`, `good first issue`, `help wanted`). Both sources are unified in `main.py`, rendered in `index.html` with a dedicated "LFX" segmented control button and purple styling, and archived in daily markdown reports.

**Tech Stack:** Python 3.11+, PyYAML, `requests`, Tailwind CSS, Vanilla JS.

**Spec:** The LFX Mentorship audit conducted on 2026-09-19, discovering 1,301 LFX projects and 1,047 GitHub repositories, identifying top participating orgs (`hyperledger`, `wasmedge`, `kubeedge`, `volcano-sh`, `karmada-io`, `kubearmor`, etc.) and the hybrid integration architecture.

## Global Constraints

- Must preserve 100% backward compatibility for existing CNCF, ASWF, and Startup issue tracking.
- All LFX mentorship issues and project items must have `source: "LFX"`.
- Must handle null/empty fields from LFX API defensively (e.g. `mentors: null`, `apprenticeNeeds: null`, `repoLink: null`).
- In `index.html`, LFX UI elements must strictly follow the `better-ui` guidelines: concentric border radius math, `active:scale-[0.96]`, `font-mono` tabular counts, and purple accent tokens (`border-purple-400/20 bg-purple-500/10 text-purple-300`).
- TDD required: tests must be written and observed failing before writing implementation code.

## Review Focus

1. **LFX API null fields**: When `apprenticeNeeds` or `mentors` is `null`, `LFXClient` must not raise `TypeError` or `AttributeError`.
2. **LFX active term evaluation**: Projects where `acceptApplications` is `false` but an upcoming/active term has open application timestamps (`app_start <= now <= app_end`) must still be included.
3. **Repository normalization**: LFX API `repoLink` URLs with trailing slashes, `.git` suffixes, or mixed casing must normalize cleanly to `owner/repo`.
4. **Rate limiting and batching**: GitHub LFX queries must use batching and respect `_handle_rate_limit` without burning search limits.
5. **Dashboard filter synchronization**: The "LFX" filter button in `index.html` must correctly filter cards, update the active filter label, update visible count, and clear on search reset.

---

### Task 1: Add Curated LFX Repositories to `config.yaml`

**Files:**
- Modify: `config.yaml`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `config.yaml`
- Produces: `config["lfx_projects"]` list with `{repo: str, language: str}` entries for top 30+ LFX projects.

- [ ] **Step 1: Write failing test for LFX configuration**

```python
# tests/test_config.py
import os
import yaml
import pytest

def test_lfx_projects_in_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert "lfx_projects" in cfg
    projects = cfg["lfx_projects"]
    assert len(projects) >= 25
    repos = [p["repo"] for p in projects]
    assert "wasmedge/wasmedge" in repos
    assert "kubeedge/kubeedge" in repos
    assert "volcano-sh/volcano" in repos
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `AssertionError: assert 'lfx_projects' in cfg`

- [ ] **Step 3: Update `config.yaml` with curated LFX projects**

Add top high-frequency LFX repositories (`wasmedge`, `kubeedge`, `volcano-sh`, `karmada-io`, `kubearmor`, `openkruise`, `thanos-io`, `goharbor`, `kubescape`, `hyperledger/fabric`, etc.).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add config.yaml tests/test_config.py
git commit -m "feat(config): add top LFX mentorship repositories to config.yaml"
```

---

### Task 2: Implement `LFXClient` for Official Mentorship Projects

**Files:**
- Create: `tracker/lfx_client.py`
- Test: `tests/test_lfx_client.py`

**Interfaces:**
- Consumes: LFX Mentorship API (`https://api.mentorship.lfx.linuxfoundation.org/projects`)
- Produces: `LFXClient.fetch_mentorship_projects(active_only=True) -> List[Dict[str, Any]]` where each dict matches the standard issue schema:
  `{"id": str, "source": "LFX", "company": str, "repo": str, "number": int, "title": str, "url": str, "language": str, "labels": List[str], "created_at": str, "comments": int}`

- [ ] **Step 1: Write failing tests for `LFXClient`**

```python
# tests/test_lfx_client.py
from unittest.mock import patch, MagicMock
import pytest
from tracker.lfx_client import LFXClient

def test_lfx_client_parsing():
    client = LFXClient()
    sample_response = {
        "projects": [
            {
                "projectId": "123",
                "name": "Jaeger Distributed Tracing Mentorship",
                "slug": "jaeger-tracing",
                "repoLink": "https://github.com/jaegertracing/jaeger",
                "acceptApplications": True,
                "createdOn": "2026-09-01 12:00:00 +0000",
                "apprenticeNeeds": {
                    "skills": ["Go", "Distributed Tracing"],
                    "mentors": [{"name": "Yuri Shkuro", "introduction": "Maintainer"}]
                },
                "programTerms": [
                    {
                        "name": "Fall 2026",
                        "active": "active",
                        "applicationStartDate": 1788220800,
                        "applicationEndDate": 1790812800
                    }
                ]
            }
        ],
        "nextPageKey": None
    }
    
    with patch.object(client.session, 'get') as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_response
        mock_get.return_value = mock_resp
        
        results = client.fetch_mentorship_projects(active_only=True)
        assert len(results) == 1
        item = results[0]
        assert item["source"] == "LFX"
        assert item["repo"] == "jaegertracing/jaeger"
        assert "Jaeger Distributed Tracing Mentorship" in item["title"]
        assert "Go" in item["labels"] or item["language"] == "Go"
        assert "https://mentorship.lfx.linuxfoundation.org/#/project/jaeger-tracing" in item["url"] or "jaegertracing/jaeger" in item["url"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_lfx_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tracker.lfx_client'`

- [ ] **Step 3: Implement `tracker/lfx_client.py`**

Implement `LFXClient` handling pagination, defensive null checks, term date checking, and schema normalization.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_lfx_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tracker/lfx_client.py tests/test_lfx_client.py
git commit -m "feat(tracker): implement LFXClient for querying official LFX Mentorship API"
```

---

### Task 3: Support LFX GitHub Search in `GitHubClient`

**Files:**
- Modify: `tracker/github_client.py`
- Test: `tests/test_github_client_lfx.py`

**Interfaces:**
- Consumes: `lfx_projects: List[Dict[str, Any]]`, `target_labels: List[str]`
- Produces: `GitHubClient.fetch_lfx_issues(lfx_projects, target_labels, days_back, batch_size) -> List[Dict[str, Any]]` with `source: "LFX"`.

- [ ] **Step 1: Write failing test for `fetch_lfx_issues`**

```python
# tests/test_github_client_lfx.py
from unittest.mock import patch, MagicMock
from tracker.github_client import GitHubClient

def test_fetch_lfx_issues():
    client = GitHubClient(token="fake-token")
    lfx_projects = [{"repo": "wasmedge/wasmedge", "language": "C++"}]
    target_labels = ["lfx-mentorship", "good first issue"]
    
    sample_issue = {
        "id": 999111,
        "number": 42,
        "title": "Add WasmEdge plugin hook",
        "html_url": "https://github.com/wasmedge/wasmedge/issues/42",
        "labels": [{"name": "lfx-mentorship"}, {"name": "good first issue"}],
        "created_at": "2026-09-18T10:00:00Z",
        "comments": 2
    }
    
    with patch.object(client, 'search_issues', return_value=[sample_issue]):
        issues = client.fetch_lfx_issues(lfx_projects, target_labels, days_back=7)
        assert len(issues) == 1
        assert issues[0]["source"] == "LFX"
        assert issues[0]["repo"] == "wasmedge/wasmedge"
        assert issues[0]["number"] == 42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_github_client_lfx.py -v`
Expected: FAIL with `AttributeError: 'GitHubClient' object has no attribute 'fetch_lfx_issues'`

- [ ] **Step 3: Implement `fetch_lfx_issues` in `tracker/github_client.py`**

Add `fetch_lfx_issues` delegating to `fetch_foundation_issues` with `source="LFX"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_github_client_lfx.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tracker/github_client.py tests/test_github_client_lfx.py
git commit -m "feat(tracker): add fetch_lfx_issues to GitHubClient"
```

---

### Task 4: Integrate LFX Pipeline into `main.py`

**Files:**
- Modify: `main.py`
- Test: `tests/test_main_pipeline.py`

**Interfaces:**
- Consumes: `config.yaml`, `LFXClient`, `GitHubClient`
- Produces: Aggregated and deduplicated `all_issues` containing LFX mentorship entries.

- [ ] **Step 1: Write test verifying pipeline inclusion of LFX**

```python
# tests/test_main_pipeline.py
from unittest.mock import patch, MagicMock
from main import load_config

def test_load_config_contains_lfx():
    cfg = load_config("config.yaml")
    assert "lfx_projects" in cfg
```

- [ ] **Step 2: Run test to verify**

Run: `pytest tests/test_main_pipeline.py -v`
Expected: PASS

- [ ] **Step 3: Update `main.py` to invoke LFX Client and GitHub LFX Search**

Wire `LFXClient` and `github_client.fetch_lfx_issues` into `main.py`, adding log messages and deduplication.

- [ ] **Step 4: Verify with dry-run test**

Run: `python main.py --dry-run`
Expected: Execution finishes cleanly with LFX sources logged.

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_main_pipeline.py
git commit -m "feat(pipeline): integrate LFX Mentorship API and GitHub search into main.py"
```

---

### Task 5: Add LFX Filter, Styling, and Badges to `index.html` and `html_renderer.py`

**Files:**
- Modify: `tracker/html_renderer.py`
- Modify: `index.html`
- Test: `tests/test_html_renderer_lfx.py`

**Interfaces:**
- Consumes: List of issues including `source: "LFX"`
- Produces: HTML with:
  - Segmented control button for `LFX` (`data-source="LFX"`, id `count-lfx`)
  - Purple badge styling: `border-purple-400/20 bg-purple-500/10 text-purple-300`, dot `bg-purple-400`
  - JavaScript state filtering for `currentSource === 'LFX'`

- [ ] **Step 1: Write failing test for LFX UI elements**

```python
# tests/test_html_renderer_lfx.py
from tracker.html_renderer import generate_html_page

def test_lfx_rendered_in_html():
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
    assert 'data-source="LFX"' in html
    assert 'count-lfx' in html
    assert 'text-purple' in html
    assert 'wasmedge/wasmedge' in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_html_renderer_lfx.py -v`
Expected: FAIL with `assert 'data-source="LFX"' in html`

- [ ] **Step 3: Update `tracker/html_renderer.py`**

Add LFX segmented control button, count element, purple badge/dot styling, hover glow, and JavaScript filter handlers. Regenerate `index.html`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_html_renderer_lfx.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tracker/html_renderer.py index.html tests/test_html_renderer_lfx.py
git commit -m "feat(ui): add LFX Mentorship filter, counters, and purple card styling to dashboard"
```

---

### Task 6: Full Suite Verification & Final Sanity Check

**Files:**
- Test: All tests in `tests/`

- [ ] **Step 1: Run the complete test suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: Run pipeline to generate updated index.html and README.md**

Run: `python main.py --update-readme --update-html`
Expected: Reports, README, and index.html updated with deduplicated issues.

- [ ] **Step 3: Verify git status is clean**

Run: `git status`
Expected: Clean working tree.
