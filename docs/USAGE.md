# Usage & Quickstart

## Environment
1. Create and activate a virtual environment (recommended):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate
   ```

2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

3. For Playwright mode (recommended for pagination):
   ```powershell
   pip install playwright
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

## Scheduling
- Windows: schedule `run_scraper.ps1` (already included) using Task Scheduler to run daily and save CSVs to `data/`.
- GitHub Actions: a sample workflow is provided to run the scraper on a schedule and upload artifacts (see `.github/workflows/schedule.yml`).

## Output
- CSV columns: `Position Title,Category,Duration,Key Programming & Technical Skills,Position ID,Deadline,City,Country`
- Files are saved in `data/` by default. Historical runs are retained by filename.

## Troubleshooting
- SSL / certificate errors with `requests`: use Playwright mode or configure your environment to trust the issuer (company-managed devices sometimes require installing root CA certificates).
- If Playwright fails on CI runner, ensure `playwright install` runs during the job and includes browser dependencies.
