# Web UI

This small Flask app provides a user-friendly interface to run ad-hoc scrapes and view results.

## Run

1. Activate virtualenv and install dependencies:

   ```powershell
   .\.venv\Scripts\Activate
   pip install -r requirements.txt
   playwright install
   ```

2. Run the Flask app:

   ```powershell
   python app.py
   ```

3. Open http://localhost:5000 in your browser.

## What it supports
- Enter a careers URL and a single keyword
- Optionally enable Playwright rendering and follow details
- Results appear as a table and show Position ID, Title, Category, Duration, Skills, Deadline, City, Country

## Notes
- The UI does not persist settings; it calls the programmatic `scrape_jobs()` function.
- For production or multi-user use, consider adding a job queue (RQ/Celery) and authentication.
