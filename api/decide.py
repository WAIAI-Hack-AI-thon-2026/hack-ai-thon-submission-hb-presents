"""
Vercel serverless function — POST /api/decide

Wraps decide_questions() from the backend package.
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from agent import decide_questions  # noqa: E402


_CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
}


class handler(BaseHTTPRequestHandler):

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(status)
        for k, v in _CORS_HEADERS.items():
            self.send_header(k, v)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            body = json.loads(raw) if raw else {}
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {'detail': f'Invalid JSON: {exc}'})
            return

        review_text = body.get('review_text', '').strip()
        if not review_text:
            self._send_json(400, {'detail': 'review_text cannot be empty'})
            return

        try:
            decision = decide_questions(review_text)
            self._send_json(200, {
                'questions': [
                    {
                        'qid':           q.qid,
                        'aspect':        q.aspect.value,
                        'text_en':       q.text_en,
                        'response_type': q.response_type.value,
                        'options':       q.options,
                        'priority':      q.priority,
                        'private':       q.private,
                    }
                    for q in decision.questions
                ],
                'rationale': decision.rationale,
                'skipped': [{'qid': s[0], 'reason': s[1]} for s in decision.skipped],
            })
        except Exception as exc:
            self._send_json(500, {'detail': str(exc)})

    def log_message(self, fmt, *args):
        pass
