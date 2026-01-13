# Developer Guide

## Project layout

- `scraper.py` — main CLI and scraping logic
- `requirements.txt` — Python dependencies
- `run_scraper.ps1` — Windows helper script to run the scraper (reads `keywords.txt`)
- `data/` — generated CSV outputs and debug HTML saved during runs
- `tests/` — unit tests (pytest)

## Key functions
- `fetch_with_playwright` — perform search with Playwright, handle pagination, extract rows
- `parse_jobs_from_html` — parse listing table when rendered
- `parse_job_detail_html` — extract duration, skills, and deadline (now prefers JSON-LD `validThrough`)

## Adding tests
- Create tests in `tests/` and use `pytest`:
  ```powershell
  python -m pytest -q
  ```

## CI / PRs
- Pull requests should include tests for new parsing behavior.
- The sample CI workflow (`.github/workflows/ci.yml`) runs unit tests on push/PR.

## Contribution checklist
- Add unit tests for new functionality
- Update `README.md` and `docs/` with consumer-facing changes
- Follow the repository's style (PEP8)
