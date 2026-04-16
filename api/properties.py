"""
Vercel serverless function — GET /api/properties
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from evidence_profiles import load_property_intel  # noqa: E402

_CORS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
}


def _send(h, status, payload):
    body = json.dumps(payload).encode()
    h.send_response(status)
    for k, v in _CORS.items():
        h.send_header(k, v)
    h.send_header('Content-Length', str(len(body)))
    h.end_headers()
    h.wfile.write(body)


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _CORS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        try:
            _send(self, 200, {'properties': load_property_intel()})
        except Exception as exc:
            _send(self, 500, {'error': str(exc)})

    def log_message(self, fmt, *args):
        pass
