# Documentation Index

Welcome — this documentation provides everything you need to understand, run, and contribute to the `cgi-careers-scraper` project.

Table of contents
- [Overview](README.md#overview)
- [Architecture](ARCHITECTURE.md)
- [Usage & Quickstart](USAGE.md)
- [Developer Guide](DEVELOPER.md)
- [Contributing](../CONTRIBUTING.md)
- [Changelog](../CHANGELOG.md)
- [FAQ / Troubleshooting](#faq--troubleshooting)

## Overview
This project scrapes CGI careers job listings and exports a CSV matching a target schema used for internal reports and automation.

## Quick links
- Architecture: `docs/ARCHITECTURE.md`
- Usage & CLI examples: `docs/USAGE.md`
- Developer setup: `docs/DEVELOPER.md`

## FAQ / Troubleshooting
Q: Some `Deadline` fields were empty — why?
A: The scraper prefers JSON-LD `validThrough` values. If the detail page lacks JSON-LD, we fall back to visible-text heuristics. We added robust parsing and tests to minimize empty deadlines.

Q: Is Playwright required?
A: No. `requests` + `BeautifulSoup` works on the listing pages when JS isn't required, but Playwright is recommended for reliable pagination and search submission.

If you need further help, open an issue in the repo and tag it with "help wanted".
