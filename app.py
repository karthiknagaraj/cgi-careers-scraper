from flask import Flask, render_template, request, jsonify
from scraper import scrape_jobs
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def api_search():
    body = request.get_json() or {}
    url = body.get('url')
    keyword = body.get('keyword')
    use_playwright = body.get('use_playwright', False)
    follow_details = body.get('follow_details', False)
    max_pages = int(body.get('max_pages', 1))

    keywords = [keyword] if keyword else None
    try:
        jobs = scrape_jobs(url=url, keywords=keywords, max_pages=max_pages, use_playwright=use_playwright, follow_details=follow_details)
        return jsonify({ 'ok': True, 'count': len(jobs), 'jobs': jobs })
    except Exception as e:
        logging.exception("Search failed")
        return jsonify({ 'ok': False, 'error': str(e) }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
