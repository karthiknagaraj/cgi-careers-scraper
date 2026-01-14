from scraper import scrape_jobs


def test_scrape_jobs_with_mock_html(monkeypatch):
    # monkeypatch fetch_page to return a small HTML snippet containing a table
    sample_html = '''
    <html><body>
    <table class="table-result-search"><tbody>
    <tr><td>J0001-0001</td><td>Test Job</td><td>Engineering</td><td>Toronto</td><td>Canada</td></tr>
    </tbody></table>
    </body></html>
    '''

    class DummySession:
        def get(self, url, timeout=30, headers=None):
            class R:
                def raise_for_status(self):
                    pass
                @property
                def text(self):
                    return sample_html
            return R()

    # monkeypatch requests.Session to return our dummy session
    import requests
    monkeypatch.setattr(requests, 'Session', lambda: DummySession())

    jobs = scrape_jobs(url='https://example.local', keywords=['Test'], max_pages=1)
    assert len(jobs) == 1
    assert jobs[0]['Position ID'] == 'J0001-0001'
    assert 'Test Job' in jobs[0]['Position Title']
