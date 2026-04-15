"""
Vercel serverless function — POST /api/decide

Wraps decide_questions() from the backend package.
No external dependencies required (stdlib only).
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Make the backend package importable when running as a Vercel function.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from schema import ReviewContext, Aspect   # noqa: E402
from agent import decide_questions         # noqa: E402


_CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
}


def _decision_to_dict(decision):
    return {
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
    }


def _build_context(body: dict) -> ReviewContext:
    valid_aspects = {a.value for a in Aspect}
    return ReviewContext(
        review_id=body.get('review_id', 'r_demo'),
        property_id=body.get('property_id', 'hotel_demo'),
        language=body.get('language', 'en'),
        overall_rating=body.get('overall_rating'),
        sub_ratings=body.get('sub_ratings', {}),
        review_text=body.get('review_text', ''),
        review_text_en=body.get('review_text_en', ''),
        aspects_mentioned={
            Aspect(a)
            for a in body.get('aspects_mentioned', [])
            if a in valid_aspects
        },
        stay_month=body.get('stay_month'),
        stay_nights=body.get('stay_nights', 1),
        checkin_hour=body.get('checkin_hour'),
        is_first_time_guest=body.get('is_first_time_guest', False),
        party_size=body.get('party_size', 1),
        has_crib_request=body.get('has_crib_request', False),
        is_street_facing_room=body.get('is_street_facing_room', False),
        property_has_elevator=body.get('property_has_elevator'),
        property_age_years=body.get('property_age_years'),
    )


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

        try:
            ctx = _build_context(body)
            decision = decide_questions(ctx)
            self._send_json(200, _decision_to_dict(decision))
        except Exception as exc:
            self._send_json(500, {'detail': str(exc)})

    def log_message(self, fmt, *args):  # silence default access log noise
        pass
