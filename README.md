# Job scraper

This project scrapes CGI careers job listings, filters by keywords (e.g., "Summer 2026"), and saves results as CSV files that match the target columns (Position Title, Category, Duration, Key Programming & Technical Skills, Position ID, Deadline).

## Highlights
- Supports both static (requests + BeautifulSoup) and JS-rendered (Playwright) scraping modes.
- Follows detail pages (optional) to extract Duration, Skills, and a normalized `Deadline` (prefers JSON-LD `validThrough`).
- Includes unit tests, CI workflows, and a scheduled GitHub Action to run the scraper daily and upload CSV artifacts.

## Quickstart (Windows)
1. Create and activate a virtualenv (recommended):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. (Optional) If you plan to use Playwright for pagination: install browsers
   ```powershell
   playwright install
   ```

## Running the scraper
- Single-page requests mode (no JS rendering):
  ```powershell
  python scraper.py --output data/jobs_YYYYMMDD.csv -k "Summer 2026" --max-pages 1
  ```

- Playwright mode (renders JS and paginates):
  ```powershell
  python scraper.py --output data/jobs_YYYYMMDD.csv --keywords-file keywords.txt --use-playwright --follow-details --max-pages 50
  ```

## Tests & CI
- Unit tests use `pytest` (`tests/`).
- CI workflow (`.github/workflows/ci.yml`) runs tests on push/PR.

## Scheduling
- Windows: schedule `run_scraper.ps1` in Task Scheduler to run daily.
- GitHub Actions: sample scheduler (`.github/workflows/schedule.yml`) runs the scraper daily and uploads CSV artifacts.

## Contributing
See `CONTRIBUTING.md` for PR and testing guidelines.

## License
MIT
