"""Vercel read-only API. Builtin Python only, no DB key or model computation."""
import hashlib
import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from datetime import date, datetime
from zoneinfo import ZoneInfo

SNAPSHOT = Path(__file__).resolve().parents[1]/'public/data/dashboard.json'


def query(data, params):
    if data.get('schema_version') != '1.0' or data.get('execution_enabled') is not False:
        raise ValueError('unsafe_snapshot')
    day = params.get('date', [datetime.now(ZoneInfo('Europe/Istanbul')).date().isoformat()])[0]
    date.fromisoformat(day)
    fixture_id = params.get('fixture', [None])[0]
    if fixture_id:
        match = next((f for f in data['fixtures']+data['history'] if f['id'] == fixture_id), None)
        return (200, match) if match else (404, {'error': 'fixture_not_found'})
    result = dict(data)
    # A stored date is not enough to call an unverified fixture a published daily match.
    result['fixtures'] = [f for f in data['fixtures'] if f.get('mode') == 'prematch'
        and f.get('kickoff_at') and datetime.fromisoformat(f['kickoff_at']).astimezone(ZoneInfo('Europe/Istanbul')).date().isoformat() == day]
    result['selected_date'] = day
    result['daily_status'] = 'available' if result['fixtures'] else 'insufficient_data'
    return 200, result


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            raw = SNAPSHOT.read_bytes()
            status, data = query(json.loads(raw), parse_qs(urlsplit(self.path).query))
        except (ValueError, TypeError, KeyError):
            status, data = 400, {'error': 'invalid_request_or_snapshot'}
        except OSError:
            status, data = 503, {'error': 'published_data_unavailable'}
        body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('ETag', '"'+hashlib.sha256(body).hexdigest()+'"')
        self.end_headers(); self.wfile.write(body)
