# Code Reference & Technical Guide

This document explains the **entire codebase** in detail, including languages used, what each function does, design decisions, and how data flows through the system.

---

## Technology Stack

| Technology | Purpose | Why |
|---|---|---|
| **Python 3.11+** | Primary language | Fast prototyping, rich libraries for web scraping and data processing |
| **requests** | HTTP client | Lightweight, simple API for fetching static pages |
| **BeautifulSoup** | HTML parsing | Reliable DOM parsing and XPath-like queries |
| **Playwright** | Browser automation | Renders JavaScript, handles interactive forms, reliable pagination |
| **pandas** | Data frame manipulation | CSV export, data analysis (used minimally for now) |
| **pytest** | Testing framework | Unit tests for parsing logic |
| **git** | Version control | Track code changes, collaborate |
| **GitHub Actions** | CI/CD & scheduling | Run tests on PR/push, run scraper on schedule, publish docs |

---

## Project Structure

```
job-scraper/
├── scraper.py                    # Main scraper script & CLI entry point
├── requirements.txt              # Python dependencies
├── run_scraper.ps1              # Windows PowerShell wrapper for daily runs
├── keywords.txt                 # Sample keywords file (one per line)
├── tests/
│   └── test_parse_job_detail.py # Unit tests for date/deadline parsing
├── data/                        # Generated CSV outputs & debug HTML
│   ├── jobs_YYYYMMDD.csv
│   ├── debug_before_search.html # HTML before search form submission (for debugging)
│   └── debug_after_search.html  # HTML after search form submission (for debugging)
├── docs/
│   ├── index.md                 # Documentation homepage
│   ├── README.md                # Doc index & FAQ
│   ├── ARCHITECTURE.md          # System design & flow diagrams
│   ├── USAGE.md                 # CLI examples & scheduling
│   ├── DEVELOPER.md             # Developer setup & contribution
│   ├── images/
│   │   └── architecture.svg     # Architecture flow diagram
├── .github/
│   ├── workflows/
│   │   ├── ci.yml               # Run tests on push/PR
│   │   ├── schedule.yml         # Run scraper daily, upload CSV artifact
│   │   └── pages.yml            # Publish docs/ to GitHub Pages
│   ├── PULL_REQUEST_TEMPLATE.md # PR template for contributors
│   ├── ISSUE_TEMPLATE.md        # Issue template
├── README.md                    # Project overview & quick start
├── CONTRIBUTING.md              # Contribution guidelines
├── CHANGELOG.md                 # Release notes
├── CODE_OF_CONDUCT.md           # Contributor code of conduct
└── LICENSE                      # MIT license
```

---

## Main Script: `scraper.py`

This is the primary Python file containing all scraping logic and CLI.

### Imports & Constants

```python
import re, csv, argparse
from datetime import datetime
import datetime as _datetime
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd

BASE_URL = "https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=joblisting"
JOB_ID_RE = re.compile(r"J\d{4}-\d{4}")
```

- **re**: Regular expressions for pattern matching (job IDs, dates, etc.)
- **csv**: CSV file writing
- **argparse**: CLI argument parsing
- **datetime**: Date/time operations
- **json**: Parse JSON-LD blocks for deadline extraction
- **requests**: Fetch pages via HTTP (lightweight)
- **BeautifulSoup**: Parse HTML and extract DOM elements
- **pandas**: Data frame operations (currently minimal, for CSV export)

**Constants**:
- `BASE_URL`: The CGI careers listing page
- `JOB_ID_RE`: Regex pattern matching job IDs like `J0126-0658`

---

### Function: `fetch_page(session, url)`

**Purpose**: Fetch a page from the web using the `requests` library.

```python
def fetch_page(session, url):
    resp = session.get(url, timeout=30, headers={"User-Agent": "job-scraper/0.1 ..."})
    resp.raise_for_status()
    return resp.text
```

**What it does**:
1. Sends an HTTP GET request to the URL using an existing session (for connection reuse).
2. Sets a 30-second timeout and a user-agent header (polite scraping).
3. Raises an exception if the response is an error (e.g., 404, 500).
4. Returns the raw HTML as a string.

**Why**: Simple, fast for static pages; doesn't need a full browser.

---

### Function: `parse_jobs_from_html(html)`

**Purpose**: Extract job listings from the HTML (either from a results table or fallback to text parsing).

```python
def parse_jobs_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    
    # Try to parse the structured results table first
    table = soup.find('table', class_=lambda c: c and 'table-result-search' in c)
    jobs = []
    if table:
        for tr in table.select('tbody tr'):
            tds = tr.find_all('td')
            # Extract: Position ID, Title, Category, City, Country
            pid = tds[0].get_text(strip=True)
            # ... more extraction
            job = { "Position ID": pid, ... }
            jobs.append(job)
        return jobs
    
    # Fallback: loose text parsing
    # ...
```

**What it does**:
1. Uses BeautifulSoup to parse the HTML into a DOM tree.
2. Searches for a table with class containing `'table-result-search'` (the results table).
3. If found, iterates over `<tbody>` rows and extracts columns:
   - `Position ID` (column 0)
   - `Position Title` (column 1)
   - `Category` (column 2)
   - `City` (column 3)
   - `Country` (column 4)
4. Initializes placeholder empty fields for `Duration`, `Key Programming & Technical Skills`, and `Deadline` (filled later).
5. **Fallback**: If no table is found, parses the text line-by-line, looking for job ID patterns and pipe delimiters.

**Why**: Prefers structured table parsing (more reliable), but includes a fallback for non-table HTML formats.

---

### Function: `filter_jobs(jobs, keywords=None, match_mode='any', use_regex=False)`

**Purpose**: Filter job listings by keywords (substring or regex match).

```python
def filter_jobs(jobs, keywords=None, match_mode='any', use_regex=False):
    if not keywords:
        return jobs
    
    filtered = []
    for job in jobs:
        job_str = ' '.join(job.values())
        match = False
        
        for kw in keywords:
            if use_regex:
                if re.search(kw, job_str, re.IGNORECASE):
                    match = True
                    break
            else:
                if kw.lower() in job_str.lower():
                    match = True
                    break
        
        if match_mode == 'all':
            # All keywords must match
            match = all(...)
        elif match:
            filtered.append(job)
    
    return filtered
```

**What it does**:
1. If no keywords provided, returns all jobs unfiltered.
2. For each job, concatenates all fields into a single string.
3. For each keyword:
   - If `use_regex=True`: treats keyword as a regex and searches case-insensitively.
   - Otherwise: does a case-insensitive substring search.
4. **Match mode**:
   - `'any'` (default): include job if ANY keyword matches (OR logic).
   - `'all'`: include job only if ALL keywords match (AND logic).
5. Returns filtered list.

**Why**: Allows flexible filtering (e.g., `"Summer 2026"` and `"Toronto"` with match-mode=all).

---

### Function: `save_csv(jobs, path)`

**Purpose**: Write filtered jobs to a CSV file.

```python
def save_csv(jobs, path):
    df = pd.DataFrame(jobs)
    df.to_csv(path, index=False)
```

**What it does**:
1. Creates a pandas DataFrame from the list of job dicts.
2. Writes the DataFrame to CSV (one column per job field, one row per job).

**Output columns**: `Position Title,Category,Duration,Key Programming & Technical Skills,Position ID,Deadline,City,Country`

**Why**: Simple, human-readable output for reports and downstream processing.

---

### Function: `fetch_with_playwright(max_pages, keyword, follow_details)`

**Purpose**: Use Playwright to render the page (JS), submit search, paginate, and optionally follow detail pages.

```python
def fetch_with_playwright(max_pages, keyword, follow_details):
    from playwright.sync_api import sync_playwright
    
    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(BASE_URL)
        page.wait_for_load_state('networkidle')
        
        # Submit search form if keyword provided
        if keyword:
            # Find search input by label
            input_elem = page.locator("input[type='text']")
            input_elem.fill(keyword)
            page.locator("input[type='submit']").click()
            page.wait_for_load_state('networkidle')
        
        # Extract jobs from each page
        for pnum in range(1, max_pages + 1):
            html = page.content()
            page_jobs = parse_jobs_from_html(html)
            
            # If follow_details enabled, fetch each job's detail page
            if follow_details and page_jobs:
                for j in page_jobs:
                    href = j.get('_detail_href', '')
                    if href:
                        detail_page = browser.new_page()
                        detail_page.goto(href)
                        detail_page.wait_for_load_state('networkidle')
                        detail_html = detail_page.content()
                        d = parse_job_detail_html(detail_html)
                        j.update(d)
                        detail_page.close()
            
            jobs.extend(page_jobs)
            
            # Paginate to next page
            # ...
        
        browser.close()
    
    return jobs
```

**What it does**:
1. Launches Chromium via Playwright (renders JS).
2. Navigates to the base URL.
3. If a keyword is provided:
   - Finds the search input field by label lookup.
   - Fills it with the keyword.
   - Clicks the submit button.
   - Waits for the page to settle (networkidle).
4. For each page (up to `max_pages`):
   - Extracts the rendered HTML.
   - Calls `parse_jobs_from_html` to get job rows.
   - If `follow_details=True`: for each job, opens its detail page in a new browser tab, fetches detail HTML, and calls `parse_job_detail_html` to extract Duration/Skills/Deadline.
   - Appends jobs to the results list.
5. Handles pagination (clicks "NEXT" button if present).
6. Closes the browser and returns all collected jobs.

**Why**: 
- Required when pages use JavaScript to render content.
- Allows programmatic form submission and pagination.
- More robust than static requests.

---

### Function: `parse_job_detail_html(html)`

**Purpose**: Extract Duration, Skills, and Deadline from a job detail page HTML.

**Key sections**:

#### 1. Extract `validThrough` from JSON-LD

```python
# Deadline: prefer JSON-LD 'validThrough' (application/ld+json) when available
deadline = ''
try:
    for script in soup.find_all('script', type='application/ld+json'):
        txt = script.string or script.get_text() or ''
        if not txt:
            continue
        parsed_json = json.loads(txt)
        
        def _find_valid(o):
            if isinstance(o, dict):
                if 'validThrough' in o and o.get('validThrough'):
                    return o.get('validThrough')
                for v in o.values():
                    r = _find_valid(v)
                    if r:
                        return r
            elif isinstance(o, list):
                for it in o:
                    r = _find_valid(it)
                    if r:
                        return r
            return None
        
        vt = _find_valid(parsed_json)
        if vt:
            s = str(vt).strip()
            # Normalize to ISO date (YYYY-MM-DD)
            dt = _datetime.datetime.fromisoformat(s)
            deadline = dt.date().isoformat()
```

**What it does**:
1. Finds all `<script type="application/ld+json">` blocks (structured data for job postings).
2. Parses the JSON.
3. Recursively searches for a `validThrough` field (the deadline date).
4. If found, normalizes it to ISO format (YYYY-MM-DD):
   - Handles `YYYY-MM-DD` format.
   - Handles `YYYY-MM-DDThh:mm:ssZ` (ISO with time and timezone) by converting to date only.
   - Handles `YYYY-MM` by defaulting to the first of the month (YYYY-MM-01).

#### 2. Extract Duration

```python
duration = ''
try:
    title_tag = soup.find('meta', property='og:title') or soup.find('title')
    title_text = (title_tag.get('content') if title_tag and title_tag.get('content') else (title_tag.get_text() if title_tag else ''))
    m = re.search(r"\((\d+\s*months?)\)", title_text, re.I)
    if m:
        duration = m.group(1)
except Exception:
    duration = ''

if not duration:
    m = re.search(r"\b(\d+)\s*months?\b", full_visible_text, re.I)
    if m:
        duration = f"{m.group(1)} months"
```

**What it does**:
1. Looks in the page title (meta or `<title>`) for a pattern like `(4 months)`.
2. If not found, searches the full visible text for any numeric month pattern (e.g., "8 months").
3. Returns the first match found or empty string.

#### 3. Extract Skills

```python
skills = ''
for htag in ['h1','h2','h3','strong','b']:
    for el in soup.find_all(htag):
        txt = el.get_text().strip()
        if re.search(r"skill|technical|programming|requirements|required", txt, re.I):
            ul = el.find_next('ul')
            if ul:
                lis = [li.get_text(separator=' ').strip() for li in ul.find_all('li')]
                skills = ' ; '.join(lis)
                break
            p = el.find_next('p')
            if p:
                skills = p.get_text(separator=' ').strip()
                break
    if skills:
        break
```

**What it does**:
1. Searches headings and bold text for keywords like "skill", "technical", "programming", "requirements".
2. If found, looks for the next `<ul>` list element and extracts all list items (joined by `' ; '`).
3. Fallback: if no list found, extracts the next paragraph (`<p>`) as skills text.

**Why**: Focuses on structured content rather than entire page text (avoids noise from JSON/script blocks).

---

### Function: `run(output_path, keywords, match_mode, use_regex, max_pages, use_playwright, follow_details)`

**Purpose**: Main orchestration function that ties everything together.

```python
def run(output_path, keywords=None, match_mode='any', use_regex=False, max_pages=1, use_playwright=False, follow_details=False):
    all_jobs = []
    
    if use_playwright:
        logging.info("Using Playwright to scrape pages (JS rendered)")
        search_kw = " ".join(keywords) if keywords else None
        all_jobs = fetch_with_playwright(max_pages=max_pages, keyword=search_kw, follow_details=follow_details)
    else:
        session = requests.Session()
        for p in range(1, max_pages + 1):
            url = BASE_URL
            if p > 1:
                url = f"{BASE_URL}&pagenum={p}"
            html = fetch_page(session, url)
            jobs = parse_jobs_from_html(html)
            all_jobs.extend(jobs)
            if not jobs:
                break
    
    filtered = filter_jobs(all_jobs, keywords=keywords, match_mode=match_mode, use_regex=use_regex)
    logging.info(f"Total jobs found: {len(all_jobs)}; after filter: {len(filtered)}")
    
    save_csv(filtered, output_path)
    logging.info(f"Saved {len(filtered)} rows to {output_path}")
```

**What it does**:
1. If `use_playwright=True`: calls `fetch_with_playwright` to render and scrape with browser.
2. Otherwise: uses requests to fetch static pages, iterating through pages and calling `parse_jobs_from_html`.
3. Applies keyword filter using `filter_jobs`.
4. Saves results to CSV.
5. Logs summary statistics.

---

### CLI Entry Point

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=f"data/jobs_{datetime.now().strftime('%Y%m%d')}.csv")
    parser.add_argument('-k', '--keyword', action='append', help='repeatable keyword filter')
    parser.add_argument('--keywords-file', help='path to newline-separated keywords')
    parser.add_argument('--match-mode', choices=['any', 'all'], default='any')
    parser.add_argument('--regex', action='store_true', help='treat keywords as regex')
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--use-playwright", action="store_true")
    parser.add_argument("--follow-details", action="store_true")
    args = parser.parse_args()
    
    keywords = []
    if args.keywords_file:
        with open(args.keywords_file, 'r') as f:
            for ln in f:
                ln = ln.strip()
                if ln and not ln.startswith('#'):
                    keywords.append(ln)
    
    if args.keyword:
        keywords.extend(args.keyword)
    
    if not keywords:
        keywords = ["Summer 2026"]
    
    run(args.output, keywords=keywords, match_mode=args.match_mode, use_regex=args.regex, 
        max_pages=args.max_pages, use_playwright=args.use_playwright, follow_details=args.follow_details)
```

**What it does**:
1. Parses command-line arguments (output path, keywords, flags, etc.).
2. Loads keywords from a file (if provided) and/or repeatable `-k` flags.
3. Defaults to `["Summer 2026"]` if no keywords are provided.
4. Calls `run()` with the parsed arguments.

---

## Test File: `tests/test_parse_job_detail.py`

```python
import pytest
from scraper import parse_job_detail_html

def test_validthrough_iso():
    html = '<script type="application/ld+json">{"validThrough":"2026-05-30"}</script>'
    d = parse_job_detail_html(html)
    assert d['Deadline'] == '2026-05-30'

def test_validthrough_with_time_z():
    html = '<script type="application/ld+json">{"validThrough":"2026-01-30T23:59:59Z"}</script>'
    d = parse_job_detail_html(html)
    assert d['Deadline'] == '2026-01-30'

def test_validthrough_year_month():
    html = '<script type="application/ld+json">{"validThrough":"2026-05"}</script>'
    d = parse_job_detail_html(html)
    assert d['Deadline'] == '2026-05-01'
```

**What it does**:
- Tests the date parsing logic for JSON-LD `validThrough` fields.
- Verifies ISO dates, ISO dates with time/timezone, and year-month formats are parsed correctly.
- Run with: `python -m pytest -q`

---

## Supporting Scripts

### `run_scraper.ps1` (PowerShell wrapper)

```powershell
$venv_path = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venv_path) {
    & $venv_path
} else {
    Write-Host "venv not found; ensure Python packages are installed"
}

$keywords = if (Test-Path "keywords.txt") { 
    Get-Content keywords.txt | Where-Object { $_ -and -not $_.StartsWith("#") }
} else { 
    @("Summer 2026") 
}

$kw_args = @()
foreach ($kw in $keywords) {
    $kw_args += "-k", $kw
}

python scraper.py --output "data/jobs_$(Get-Date -Format 'yyyyMMdd').csv" @kw_args --use-playwright --follow-details
```

**What it does**:
- Activates the Python virtual environment.
- Reads `keywords.txt` (ignoring comments and empty lines).
- Builds CLI arguments for multi-keyword support.
- Runs the scraper with Playwright and detail following.
- Saves output to `data/jobs_YYYYMMDD.csv`.

**Use case**: Schedule this script in Windows Task Scheduler for daily automated runs.

---

## Data Flow Diagram

```
User runs scraper.py with CLI args
    ↓
parse_args() → extract keywords, max_pages, flags
    ↓
run() function
    ├─ If --use-playwright:
    │  └─ fetch_with_playwright()
    │     ├─ Launch Chromium browser
    │     ├─ Navigate to CGI careers page
    │     ├─ Submit search form (if keyword provided)
    │     ├─ For each page (up to max_pages):
    │     │  ├─ parse_jobs_from_html()
    │     │  │  └─ Extract job rows from <table> or text
    │     │  └─ If --follow-details:
    │     │     └─ For each job:
    │     │        ├─ Open detail page
    │     │        ├─ parse_job_detail_html()
    │     │        │  ├─ Extract validThrough from JSON-LD
    │     │        │  ├─ Extract Duration regex
    │     │        │  └─ Extract Skills from headings/text
    │     │        └─ Update job dict
    │     └─ Return all jobs
    └─ Else (requests mode):
       ├─ For each page:
       │  ├─ fetch_page() → requests.get()
       │  ├─ parse_jobs_from_html()
       │  └─ Append to results
       └─ Return all jobs
    ↓
filter_jobs() → apply keyword filters (any/all/regex)
    ↓
save_csv() → write to data/jobs_YYYYMMDD.csv
    ↓
Done; output CSV ready for analysis
```

---

## Key Design Decisions & Why

| Decision | Why |
|---|---|
| Prefer JSON-LD `validThrough` over visible text | JSON-LD is machine-readable, normalized, and less ambiguous than parsing visible text |
| Optional `--follow-details` | Detail pages are slow; users can choose speed over completeness |
| Playwright optional (fallback to requests) | Playwright requires browser download; requests is faster for static pages |
| Filter after scraping (not before) | Capture all data, then filter locally; reduces load on site; enables re-filtering without re-scraping |
| CSV output only | Simple, universal format; works in spreadsheets, databases, scripting languages |
| Unit tests for parsing only | High-value tests (parsing is error-prone); full integration tests (network calls) would be slow and brittle |

---

## Common Debugging Tips

1. **Check debug HTML files**: After a Playwright run, inspect `data/debug_before_search.html` and `data/debug_after_search.html` to see what the browser sees before/after search submission.

2. **Enable logging**: The script uses Python's `logging` module; add `logging.basicConfig(level=logging.DEBUG)` to see detailed logs.

3. **Run with `--max-pages 1`**: For testing, limit to 1 page to get results faster.

4. **Use `--regex`**: If keyword matching isn't working as expected, try `--regex` to debug the pattern.

5. **Test a single job detail**: Manually fetch a job detail page URL and run `parse_job_detail_html()` on the HTML to debug parsing logic.

---

## Summary

The scraper is a **Python CLI tool** that:
- Fetches job listings from CGI careers pages (via requests or Playwright).
- Parses structured table rows and extracts job metadata.
- Optionally follows detail pages to extract Duration, Skills, and Deadline.
- Prefers JSON-LD `validThrough` for reliable deadline extraction.
- Filters results by keywords (substring, regex, any/all logic).
- Outputs CSV files suitable for reports and downstream automation.

All code is contained in `scraper.py` (~600 lines); supporting scripts and tests are minimal and focused.
