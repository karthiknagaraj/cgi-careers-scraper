"""Prototype scraper for CGI careers job listing

- Uses requests + BeautifulSoup to fetch the listing page and parse job rows.
- Finds lines that include Position ID pattern (Jxxxx-xxxx) and splits fields by pipe delimiters.
- Applies a keyword filter (e.g., "Summer 2026") across the listing fields and writes CSV.
- Can be extended to follow detail pages or use Playwright for pagination.
"""

import re
import csv
import argparse
from datetime import datetime
import datetime as _datetime
import json
import logging
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd

BASE_URL = "https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=joblisting"
JOB_ID_RE = re.compile(r"J\d{4}-\d{4}")

def load_config(config_file='config.json'):
    """Load configuration from JSON file."""
    if not os.path.exists(config_file):
        return {}
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Failed to load config from {config_file}: {e}")
        return {}


def fetch_page(session, url):
    resp = session.get(url, timeout=30, headers={"User-Agent": "job-scraper/0.1 (https://github.com)"})
    resp.raise_for_status()
    return resp.text


def parse_jobs_from_html(html):
    """Return list of dicts with fields: Position ID, Position Title, Category, City, Country.

    Prefer parsing the results table when present; otherwise fall back to a loose text-based heuristic.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Try to parse the structured results table first (more reliable)
    table = soup.find('table', class_=lambda c: c and 'table-result-search' in c)
    jobs = []
    if table:
        for tr in table.select('tbody tr'):
            tds = tr.find_all('td')
            if not tds:
                continue
            pid = tds[0].get_text(strip=True)
            title = tds[1].get_text(strip=True) if len(tds) > 1 else ""
            category = tds[2].get_text(strip=True) if len(tds) > 2 else ""
            city = tds[3].get_text(strip=True) if len(tds) > 3 else ""
            country = tds[4].get_text(strip=True) if len(tds) > 4 else ""
            job = {
                "Position ID": pid,
                "Position Title": title,
                "Category": category,
                "City": city,
                "Country": country,
                "Duration": "",
                "Key Programming & Technical Skills": "",
                "Deadline": "",
            }
            jobs.append(job)
        return jobs

    # Fallback: loose text parsing for pages that use a pipe-delimited or inline format
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines:
        if JOB_ID_RE.search(line):
            # Normalize pipes to split fields; some lines already show '|'
            parts = [p.strip() for p in line.split("|") if p.strip()]
            # Expected layout (observed): ID | Title | Category | City | Country
            if len(parts) >= 2 and JOB_ID_RE.match(parts[0]):
                job = {
                    "Position ID": parts[0],
                    "Position Title": parts[1] if len(parts) > 1 else "",
                    "Category": parts[2] if len(parts) > 2 else "",
                    "City": parts[3] if len(parts) > 3 else "",
                    "Country": parts[4] if len(parts) > 4 else "",
                    # Placeholder fields for the richer table you showed
                    "Duration": "",
                    "Key Programming & Technical Skills": "",
                    "Deadline": "",
                }
                jobs.append(job)
    return jobs


def filter_jobs(jobs, keywords=None, match_mode='any', use_regex=False):
    """Filter list of job dicts by keywords.

    - keywords: list of strings to match (OR regex patterns when use_regex=True)
    - match_mode: 'any' (OR) or 'all' (AND)
    - use_regex: treat each keyword as a regex pattern (case-insensitive)
    """
    if not keywords:
        return jobs
    import re
    patterns = []
    if use_regex:
        patterns = [re.compile(k, re.IGNORECASE) for k in keywords]
    else:
        keywords_l = [k.lower() for k in keywords]

    filtered = []
    for j in jobs:
        hay = " ".join([str(v) for v in j.values()])
        if use_regex:
            matches = [bool(p.search(hay)) for p in patterns]
        else:
            hay_l = hay.lower()
            matches = [kw in hay_l for kw in keywords_l]

        if match_mode == 'any' and any(matches):
            filtered.append(j)
        elif match_mode == 'all' and all(matches):
            filtered.append(j)
    return filtered


def save_csv(jobs, path):
    # Ensure column order as requested
    cols = [
        "Position Title",
        "Category",
        "Duration",
        "Key Programming & Technical Skills",
        "Position ID",
        "Deadline",
        "City",
        "Country",
    ]
    df = pd.DataFrame(jobs)
    # Reorder and fill missing
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]
    df.to_csv(path, index=False)


import logging
from urllib.parse import urljoin

try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def fetch_with_playwright(max_pages=50, keyword=None, follow_details=False, base_url=None):
    """Use Playwright to paginate through listing pages and return extracted jobs.
    This renders JS and calls the page's gotopage(n) function when available.

    Parameters:
    - base_url: optional base URL to navigate to (defaults to global BASE_URL)
    """
    if sync_playwright is None:
        raise RuntimeError("Playwright is not installed. Install with `pip install playwright` and run `playwright install`.")

    jobs = []

    base = base_url or BASE_URL

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base)
        # Wait for initial content
        page.wait_for_load_state("networkidle")

        # If a search keyword is provided, try to input it and click the Search button
        if keyword:
            logging.info(f"Submitting search with keyword: {keyword}")
            # Save initial HTML for debugging
            try:
                with open('data/debug_before_search.html', 'w', encoding='utf-8') as f:
                    f.write(page.content())
                logging.info('Wrote data/debug_before_search.html')
            except Exception as e:
                logging.warning(f"Failed to write debug_before_search: {e}")

            submitted = False
            # Try common selectors
            try:
                # name/id based
                for sel in ["input[name*='keyword']", "input[id*='keyword']", "input[placeholder*='Keyword']", "input[type='search']"]:
                    try:
                        if page.query_selector(sel):
                            page.fill(sel, keyword)
                            submitted = True
                            logging.info(f'Filled input using selector {sel}')
                            break
                    except Exception:
                        continue

                # If not found via simple selectors, try locating label text 'Keyword'
                if not submitted:
                    try:
                        lbl = page.locator('label', has_text='Keyword').first
                        if lbl:
                            inp = lbl.locator('xpath=following::input[1]')
                            if inp:
                                inp.fill(keyword)
                                submitted = True
                                logging.info('Filled input using label-based lookup')
                    except Exception:
                        pass

                # Click a button with text 'Search' or input[type=submit]
                if submitted:
                    clicked = False
                    for bsel in ["button:has-text('Search')", "input[type='submit']", "a:has-text('Search')"]:
                        try:
                            b = page.query_selector(bsel)
                            if b:
                                b.click()
                                clicked = True
                                logging.info(f'Clicked button using selector {bsel}')
                                break
                        except Exception:
                            continue

                    if not clicked:
                        # Try pressing Enter in the input
                        try:
                            page.keyboard.press('Enter')
                            clicked = True
                            logging.info('Pressed Enter to submit search')
                        except Exception:
                            pass

                if submitted:
                    page.wait_for_load_state("networkidle")
                    try:
                        with open('data/debug_after_search.html', 'w', encoding='utf-8') as f:
                            f.write(page.content())
                        logging.info('Wrote data/debug_after_search.html')
                    except Exception as e:
                        logging.warning(f"Failed to write debug_after_search: {e}")
                    logging.info("Search submitted and results loaded (or network idle).")
                else:
                    logging.info("Could not find a search input to submit keyword; continuing without search.")
            except Exception as e:
                logging.warning(f"Exception while attempting to submit search keyword: {e}")

        for pnum in range(1, max_pages + 1):
            logging.info(f"Rendering page {pnum}")
            if pnum > 1:
                # Try calling the site's gotopage function if present
                try:
                    page.evaluate(f"if(window.gotopage) gotopage({pnum});")
                    page.wait_for_load_state("networkidle")
                except Exception:
                    # Fallback: try clicking 'NEXT' link
                    try:
                        next_a = page.query_selector('a[href^="javascript:gotopage("]')
                        if next_a:
                            next_a.click()
                            page.wait_for_load_state("networkidle")
                    except Exception:
                        logging.info("Could not navigate to next page using gotopage; stopping pagination.")
                        break

            html = page.content()
            # Try extracting jobs directly from the rendered DOM using Playwright locators (more reliable)
            page_jobs = []
            try:
                rows = page.locator('table.views-table.table-result-search tbody tr')
                count = rows.count()
                for i in range(count):
                    try:
                        tds = rows.nth(i).locator('td')
                        pid = tds.nth(0).inner_text().strip() if tds.count() > 0 else ''
                        title = tds.nth(1).inner_text().strip() if tds.count() > 1 else ''
                        category = tds.nth(2).inner_text().strip() if tds.count() > 2 else ''
                        city = tds.nth(3).inner_text().strip() if tds.count() > 3 else ''
                        country = tds.nth(4).inner_text().strip() if tds.count() > 4 else ''
                        # attempt to capture the detail link if present
                        href = ''
                        try:
                            a = rows.nth(i).locator('td a').nth(0)
                            href = a.get_attribute('href') or ''
                        except Exception:
                            href = ''
                        detail_href = urljoin(base, href) if href else ''
                        job = {
                            "Position ID": pid,
                            "Position Title": title,
                            "Category": category,
                            "City": city,
                            "Country": country,
                            "Duration": "",
                            "Key Programming & Technical Skills": "",
                            "Deadline": "",
                            "_detail_href": detail_href,
                        }
                        page_jobs.append(job)
                    except Exception as e:
                        logging.debug(f"Failed extracting row {i}: {e}")
            except Exception:
                # Fallback to HTML parsing
                page_jobs = parse_jobs_from_html(html)

            logging.info(f"Found {len(page_jobs)} jobs on page {pnum}")

            # If follow_details is enabled, open each job detail page (in a new page) and extract fields
            if follow_details and page_jobs:
                for j in page_jobs:
                    href = j.get('_detail_href') or ''
                    if not href:
                        # fallback to regex search
                        href = find_detail_link_in_html(html, j.get('Position ID','')) or ''
                    if not href:
                        continue
                    try:
                        detail_page = browser.new_page()
                        detail_page.goto(href)
                        detail_page.wait_for_load_state('networkidle')
                        detail_html = detail_page.content()
                        d = parse_job_detail_html(detail_html)
                        j.update(d)
                        detail_page.close()
                        logging.info(f"Fetched details for {j.get('Position ID')}")
                    except Exception as e:
                        logging.warning(f"Failed to fetch detail for {j.get('Position ID')}: {e}")

            # remove internal helper fields before further processing
            for j in page_jobs:
                if '_detail_href' in j:
                    j.pop('_detail_href', None)


            jobs.extend(page_jobs)

            # Stop if there's no next page control (simple heuristic)
            if "Page" in html and "NEXT" not in html and pnum > 1:
                break

    return jobs


def find_detail_link_in_html(html, position_id):
    # Search for hrefs that contain the position id
    m = re.search(r'href=["\']([^"\']*%s[^"\']*)["\']' % re.escape(position_id), html, flags=re.IGNORECASE)
    if m:
        href = m.group(1)
        return urljoin(BASE_URL, href)
    return None


def fetch_detail_page(url):
    session = requests.Session()
    resp = session.get(url, timeout=30, headers={"User-Agent": "job-scraper/0.1 (https://github.com)"})
    resp.raise_for_status()
    return resp.text


def parse_job_detail_html(html):
    """Robust parsing of detail page to extract Duration, Skills, Deadline.

    Improvements:
    - Ignore script/style content (JSON blobs are often inside <script> tags).
    - Prefer labeled text in visible DOM nodes (strong, p, li, headings).
    - Extract compact matches (e.g., '4 months') and normalize deadline to YYYY-MM-DD when possible.
    """
    soup = BeautifulSoup(html, "html.parser")

    # helper: get visible text nodes only (exclude script/style)
    visible_texts = []
    for t in soup.find_all(string=True):
        if t.parent.name in ('script', 'style'):
            continue
        s = t.strip()
        if s:
            visible_texts.append((t, s))
    full_visible_text = "\n".join(s for (_, s) in visible_texts)

    # helper: parse date-like string into ISO YYYY-MM-DD when possible
    def parse_date_string(s):
        s = s.strip().replace('st','').replace('nd','').replace('rd','').replace('th','')
        # try common formats like 'January 30, 2026' or '30 January 2026' or 'Jan 30 2026'
        import datetime
        # try regex to capture day/month/year
        m = re.search(r"(\d{1,2})\s*(?:st|nd|rd|th|,)??\s*(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)[\s,]+(\d{4})", s, re.I)
        if m:
            day = int(m.group(1))
            mon = m.group(2)
            year = int(m.group(3))
            try:
                dt = datetime.datetime.strptime(f"{day} {mon} {year}", "%d %B %Y")
            except Exception:
                try:
                    dt = datetime.datetime.strptime(f"{day} {mon} {year}", "%d %b %Y")
                except Exception:
                    return s
            return dt.date().isoformat()
        m2 = re.search(r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s*(\d{1,2})[\s,]+(\d{4})", s, re.I)
        if m2:
            mon = m2.group(1)
            day = int(m2.group(2))
            year = int(m2.group(3))
            import datetime
            try:
                dt = datetime.datetime.strptime(f"{day} {mon} {year}", "%d %B %Y")
            except Exception:
                try:
                    dt = datetime.datetime.strptime(f"{day} {mon} {year}", "%d %b %Y")
                except Exception:
                    return s
            return dt.date().isoformat()
        return s

    # Duration: look in meta title first for patterns like '(4 months)'
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
        # search visible text for 'X months'
        m = re.search(r"\b(\d+)\s*months?\b", full_visible_text, re.I)
        if m:
            duration = f"{m.group(1)} months"

    # Deadline: prefer JSON-LD 'validThrough' (application/ld+json) when available
    deadline = ''
    try:
        for script in soup.find_all('script', type='application/ld+json'):
            txt = script.string or script.get_text() or ''
            if not txt:
                continue
            parsed_json = None
            try:
                parsed_json = json.loads(txt)
            except Exception:
                # attempt to extract the first JSON object within the script block
                mjs = re.search(r"\{[\s\S]*\}", txt)
                if mjs:
                    try:
                        parsed_json = json.loads(mjs.group(0))
                    except Exception:
                        parsed_json = None
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
            if parsed_json:
                vt = _find_valid(parsed_json)
                if vt:
                    s = str(vt).strip()
                    # Normalize common ISO/time formats to YYYY-MM-DD when possible
                    try:
                        # Handle trailing Z timezone indicator by converting to +00:00
                        s2 = s[:-1] + '+00:00' if s.endswith('Z') else s
                        dt = _datetime.datetime.fromisoformat(s2)
                        deadline = dt.date().isoformat()
                        break
                    except Exception:
                        # fallback regex for YYYY-MM-DD or YYYY-MM
                        m1 = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
                        if m1:
                            deadline = f"{m1.group(1)}-{m1.group(2)}-{m1.group(3)}"
                            break
                        m2 = re.match(r"(\d{4})-(\d{2})", s)
                        if m2:
                            # default to first day of month for month-only values
                            deadline = f"{m2.group(1)}-{m2.group(2)}-01"
                            break
                        # as last resort, try the visible-text parser
    except Exception:
        # parsing errors shouldn't block fallbacks below
        deadline = deadline or ''

    # only use visible-text heuristics if JSON-LD didn't provide a date
    if not deadline:
        # look for explicit labels in visible_texts
        for (node, txt) in visible_texts:
            if re.search(r"application deadline|application closing|closing date|closing|deadline", txt, re.I):
                # try to find date in the same string or following siblings
                s = txt
                # search within a small window around this node in the full text
                try:
                    # get a substring of the full visible text containing this txt
                    idx = full_visible_text.find(txt)
                    window = full_visible_text[max(0, idx-200): idx+200]
                except Exception:
                    window = txt
                date_re = re.compile(r"\b(?:\d{1,2}\s*(?:st|nd|rd|th)?\s+)?(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)[\s,]+\d{4}\b", re.I)
                # normalize ordinals and non-breaking spaces before regex
                window_norm = window.replace('\xa0',' ').replace('\u00a0',' ')
                window_norm = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", window_norm, flags=re.I)
                m = date_re.search(window_norm)
                if m:
                    deadline = parse_date_string(m.group(0))
                    break
        if not deadline:
            # fallback: search for date in visible text and choose the one that matches a 'deadline' label nearby
            date_re = re.compile(r"\b(?:\d{1,2}\s*(?:st|nd|rd|th)?\s+)?(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)[\s,]+\d{4}\b", re.I)
            m = date_re.search(full_visible_text)
            if m:
                # return first reasonable date found
                deadline = parse_date_string(m.group(0))

    # Skills: prefer lists under headings; limit length
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

    if not skills:
        # fallback: small window around skill-like lines in visible text
        lines = [s for (_, s) in visible_texts]
        for i, ln in enumerate(lines):
            if re.search(r"skill|technical|programming|experience|required", ln, re.I):
                window = ' ; '.join(lines[max(0,i-1):min(len(lines), i+4)])
                skills = window
                break

    # final formatting: ensure concise outputs
    if duration:
        duration = duration.strip()
        if len(duration) > 100:
            # clip to the first match of months
            m = re.search(r"\b(\d+\s*months?)\b", duration, re.I)
            duration = (m.group(1) if m else duration[:100]).strip()
    if deadline:
        deadline = deadline.strip()

    if skills and len(skills) > 2000:
        skills = skills[:2000] + '...'

    return {
        "Duration": duration,
        "Key Programming & Technical Skills": skills,
        "Deadline": deadline,
    }


def scrape_jobs(url=None, keywords=None, match_mode='any', use_regex=False, max_pages=1, use_playwright=False, follow_details=False):
    """Programmatic scraping API: return list of job dicts matching the filters.

    Parameters:
    - url: override base URL for this invocation (string)
    - keywords: list of keywords to filter (list of strings)
    - match_mode: 'any' or 'all'
    - use_regex: treat keywords as regex
    - max_pages: max pages to paginate
    - use_playwright: render JS and paginate with Playwright
    - follow_details: follow detail pages to enrich fields

    Returns: list of job dicts
    """
    base = url or BASE_URL
    all_jobs = []
    if use_playwright:
        logging.info("Using Playwright to scrape pages (JS rendered)")
        try:
            search_kw = None
            if keywords:
                search_kw = " ".join(keywords)
            all_jobs = fetch_with_playwright(max_pages=max_pages, keyword=search_kw, follow_details=follow_details, base_url=base)
        except Exception as e:
            logging.error(f"Playwright mode failed: {e}")
            return []
    else:
        session = requests.Session()
        for p in range(1, max_pages + 1):
            page_url = base
            if p > 1:
                page_url = f"{base}&pagenum={p}"
            logging.info(f"Fetching {page_url}")
            try:
                html = fetch_page(session, page_url)
            except Exception as e:
                logging.error(f"Failed to fetch page {p}: {e}")
                break
            jobs = parse_jobs_from_html(html)
            logging.info(f"Found {len(jobs)} jobs on page {p}")
            all_jobs.extend(jobs)
            if not jobs:
                break

    filtered = filter_jobs(all_jobs, keywords=keywords, match_mode=match_mode, use_regex=use_regex)
    logging.info(f"Total jobs found: {len(all_jobs)}; after filter (keywords={keywords}, mode={match_mode}): {len(filtered)}")
    return filtered


def run(output_path, keywords=None, match_mode='any', use_regex=False, max_pages=1, use_playwright=False, follow_details=False):
    # Backwards-compatible wrapper that saves to CSV
    jobs = scrape_jobs(keywords=keywords, match_mode=match_mode, use_regex=use_regex, max_pages=max_pages, use_playwright=use_playwright, follow_details=follow_details)
    save_csv(jobs, output_path)
    logging.info(f"Saved {len(jobs)} rows to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=f"data/jobs_{datetime.now().strftime('%Y%m%d')}.csv")
    parser.add_argument('-k', '--keyword', action='append', help='repeatable keyword filter (substring match)')
    parser.add_argument('--keywords-file', help='path to newline-separated keywords (use # for comments)')
    parser.add_argument('--match-mode', choices=['any', 'all'], default='any', help="'any' (OR) or 'all' (AND) when multiple keywords supplied")
    parser.add_argument('--regex', action='store_true', help='treat keywords as regular expressions (case-insensitive)')
    parser.add_argument("--max-pages", type=int, default=50, help="max pages to try when paginating")
    parser.add_argument("--use-playwright", action="store_true", help="Use Playwright for JS-rendered pagination")
    parser.add_argument("--follow-details", action="store_true", help="Follow detail pages to extract Duration/Skills/Deadline (slower)")
    parser.add_argument("--url", help="Override the careers listing URL from config.json")
    parser.add_argument("--config", default="config.json", help="Path to config.json file")
    args = parser.parse_args()
    
    # Load config and determine the URL
    config = load_config(args.config)
    BASE_URL = args.url or config.get('careers_url') or BASE_URL

    # Load keywords from file and/or repeatable -k flags
    keywords = []
    if args.keywords_file:
        try:
            with open(args.keywords_file, 'r', encoding='utf-8') as f:
                for ln in f:
                    ln = ln.strip()
                    if ln and not ln.startswith('#'):
                        keywords.append(ln)
        except Exception as e:
            logging.error(f"Failed to read keywords file {args.keywords_file}: {e}")

    if args.keyword:
        keywords.extend(args.keyword)

    if not keywords:
        # default keyword for backward compatibility
        keywords = ["Summer 2026"]

    run(args.output, keywords=keywords, match_mode=args.match_mode, use_regex=args.regex, max_pages=args.max_pages, use_playwright=args.use_playwright, follow_details=args.follow_details)
