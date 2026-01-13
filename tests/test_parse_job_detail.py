import pytest
from scraper import parse_job_detail_html


def test_validthrough_iso():
    html = '<html><head><script type="application/ld+json">{"@context":"http://schema.org","@type":"JobPosting","validThrough":"2026-05-30"}</script></head><body></body></html>'
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
