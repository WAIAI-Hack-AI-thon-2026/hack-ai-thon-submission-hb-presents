"""
Vercel serverless function — POST /api/submit-followups

Input:  { propertyId, questions, answers }
Output: { updated, answeredQuestionCount, updatedLabels, profile }
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from agent import invalidate_evidence_profile_cache  # noqa: E402
from evidence_profiles import update_hotel_evidence_profile  # noqa: E402

_CORS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
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

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length) or b'{}')
        except Exception as exc:
            _send(self, 400, {'error': str(exc)})
            return

        property_id = str(body.get('propertyId', '') or '').strip()
        if not property_id:
            _send(self, 400, {'error': 'propertyId is required'})
            return

        try:
            result = update_hotel_evidence_profile(
                property_id=property_id,
                questions=body.get('questions') or [],
                answers=body.get('answers') or {},
            )
            invalidate_evidence_profile_cache()
            _send(self, 200, result)
        except Exception as exc:
            _send(self, 500, {'error': str(exc)})

    def log_message(self, fmt, *args):
        pass
