"""
Vercel serverless function — POST /api/analyze

Input:  { propertyId, city, country, rating, reviewText }
Output: { questions: [{ id, text, options }] }

Wraps the deterministic backend agent (decide_questions).
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from schema import ReviewContext, Aspect   # noqa: E402
from agent import decide_questions         # noqa: E402

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

        try:
            ctx = ReviewContext(
                review_id=f"r_{body.get('propertyId', 0)}",
                property_id=str(body.get('propertyId', 'unknown')),
                overall_rating=body.get('rating'),
                review_text=body.get('reviewText', ''),
                review_text_en=body.get('reviewText', ''),
                sub_ratings={},
                stay_nights=2,
            )
            decision = decide_questions(ctx)
            questions = [
                {'id': q.qid, 'text': q.text_en, 'options': q.options}
                for q in decision.questions
            ]
            _send(self, 200, {'questions': questions})
        except Exception as exc:
            _send(self, 500, {'error': str(exc)})

    def log_message(self, fmt, *args):
        pass
