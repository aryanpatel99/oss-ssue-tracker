# CNCF, ASWF & OSS Startup Issue Tracker

## What this project does
Automated tracker that discovers open, unassigned, discussion-active issues across CNCF/ASWF foundations, LFX Mentorship, GSoC organizations, and YC/OSS startups. Renders an `index.html` dashboard and daily markdown reports. Runs via GitHub Actions cron every 2 hours.

## Architecture
- `main.py` — pipeline orchestrator; loads config, calls clients, renders output
- `config.yaml` — all tracked repos, labels, and settings
- `tracker/clotributor_client.py` — fetches CNCF/ASWF issues from Clotributor API
- `tracker/github_client.py` — GitHub Search API client for all source types
- `tracker/lfx_client.py` — LFX Mentorship API client
- `tracker/html_renderer.py` — generates the `index.html` dashboard
- `tracker/renderer.py` — markdown report renderer
- `tracker/notifier.py` — Discord/Slack/Telegram webhook notifications
- `.github/workflows/daily_tracker.yml` — CI cron job

## Key patterns
- Issues are deduplicated by URL across all sources using `seen_urls` set
- GitHub Search queries are batched (`github_search_batch_size` repos per query)
- Startup issues use `-linked:pr` in the search query for PR filtering
- CNCF/ASWF issues use Clotributor's `has_linked_prs` field
- LFX projects are discovered from the Mentorship API, then GitHub issues are fetched separately
- Each source has its own lookback window (`cncf_days_back`, `lfx_days_back`, etc.)

## How to run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GITHUB_TOKEN=ghp_...
python main.py --dry-run          # preview without writing files
python main.py                    # full run: update index.html + save report
```

## Testing
```bash
python -m pytest tests/
```

## Adding a new source
1. Add repos to `config.yaml` under a new section (e.g., `gsoc_projects`)
2. Add a lookback setting in `settings:` (e.g., `gsoc_days_back: 14`)
3. Add a fetch step in `main.py` following the existing pattern
4. Add the source label (e.g., "GSoC") to issue dicts so the dashboard can filter by it
