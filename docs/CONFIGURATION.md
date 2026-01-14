# Configuration Guide

## Overview
The scraper can be configured via a `config.json` file or CLI arguments. The URL of the careers listing page is now configurable, allowing you to easily switch between different job sites.

## Configuration File (`config.json`)

The default `config.json` contains:
```json
{
  "careers_url": "https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=joblisting",
  "scraper_description": "CGI careers job scraper"
}
```

### Updating the URL

Edit `config.json` and change the `careers_url` value to your desired careers listing page:
```json
{
  "careers_url": "https://example-careers.com/job-listings",
  "scraper_description": "Example Company Careers Scraper"
}
```

## CLI Arguments

Override the config via command-line:
- `--url <URL>` — override the careers URL (takes precedence over config.json)
- `--config <path>` — specify a different config file (default: config.json)

### Examples

1. Use default config:
   ```powershell
   python scraper.py -k "Summer 2026" --use-playwright
   ```

2. Override URL via CLI:
   ```powershell
   python scraper.py --url "https://example-careers.com/listings" -k "2026" --use-playwright
   ```

3. Use a different config file:
   ```powershell
   python scraper.py --config my-custom-config.json -k "Summer 2026"
   ```

4. Combine all:
   ```powershell
   python scraper.py --config other-config.json --url "https://override-url.com" -k "keyword" --use-playwright --follow-details
   ```

## Priority Order

When determining the URL, the scraper uses this priority:
1. `--url` CLI argument (highest priority)
2. `careers_url` from config file
3. Hardcoded default (fallback)

## Setting Up Multiple Career Sites

You can create multiple config files and use them independently:

### `cgi-config.json`
```json
{
  "careers_url": "https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=joblisting",
  "scraper_description": "CGI careers scraper"
}
```

### `acme-config.json`
```json
{
  "careers_url": "https://acme-careers.example.com/job-listings",
  "scraper_description": "ACME careers scraper"
}
```

Then run:
```powershell
# Scrape CGI
python scraper.py --config cgi-config.json -k "Summer 2026" --use-playwright

# Scrape ACME
python scraper.py --config acme-config.json -k "2026" --use-playwright
```

## Scheduling Multiple Sites

Update `run_scraper.ps1` or create separate wrapper scripts for each site:

```powershell
# scrape-cgi.ps1
python scraper.py --config cgi-config.json --output "data/cgi_jobs_$(Get-Date -Format 'yyyyMMdd').csv" @kw_args --use-playwright

# scrape-acme.ps1
python scraper.py --config acme-config.json --output "data/acme_jobs_$(Get-Date -Format 'yyyyMMdd').csv" @kw_args --use-playwright
```

Schedule each in Windows Task Scheduler independently.
