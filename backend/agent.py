"""
The Follow-up Question Agent — powered by OpenAI.

Entry point: `decide_questions(review_text_or_ctx) -> AgentDecision`.

The model generates follow-up questions directly instead of selecting from a
fixed question bank. We still keep lightweight routing rules:
    1. If the review mentions a concrete problem, drill into that problem.
    2. If the review is broad/vague, use common hotel topics as prompts.
"""
from __future__ import annotations

import json
import os
import re
from typing import Union

from dotenv import load_dotenv
from openai import OpenAI

try:
    from .schema import AgentDecision, Aspect, Question, ResponseType, ReviewContext
except ImportError:
    from schema import AgentDecision, Aspect, Question, ResponseType, ReviewContext


load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


MAX_QUESTIONS = 3
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"

HIGH_FREQUENCY_HOTEL_TOPICS = [
    {"aspect": "bathroom", "label": "Bathroom condition"},
    {"aspect": "cleanliness", "label": "Room cleanliness"},
    {"aspect": "noise", "label": "Noise at night"},
    {"aspect": "ac_heat", "label": "AC / heating"},
    {"aspect": "staff", "label": "Staff helpfulness"},
    {"aspect": "checkin", "label": "Check-in / check-out"},
    {"aspect": "billing", "label": "Unexpected fees / billing"},
    {"aspect": "bed", "label": "Bed comfort"},
    {"aspect": "smell", "label": "Bad smell"},
    {"aspect": "renovation", "label": "Worn / broken fixtures"},
]

ISSUE_KEYWORDS = {
    "cleanliness": ["dirty", "unclean", "stain", "dust", "hair", "filthy", "gross", "messy"],
    "bathroom": ["bathroom", "shower", "toilet", "sink", "drain", "tub"],
    "noise": ["noise", "noisy", "loud", "street", "construction", "hallway", "neighbor"],
    "ac_heat": ["ac", "air conditioning", "heating", "heater", "temperature", "cold", "hot"],
    "staff": ["staff", "service", "front desk", "reception", "rude", "helpful"],
    "billing": ["charge", "charged", "fee", "bill", "deposit", "refund", "price"],
    "bed": ["bed", "mattress", "pillow", "linens", "sleep"],
    "checkin": ["check in", "check-in", "checkout", "check out", "wait", "line"],
    "smell": ["smell", "odor", "odour", "musty", "smoke", "sewage"],
    "renovation": ["dated", "old", "worn", "broken", "repair", "maintenance"],
    "amenities": ["wifi", "wi-fi", "tv", "hairdryer", "kettle", "minibar", "outlet", "light"],
    "family": ["kids", "children", "family", "crib", "stroller"],
    "location": ["location", "walk", "nearby", "distance", "area"],
}

VAGUE_NEGATIVE_PATTERNS = [
    "bad", "awful", "terrible", "horrible", "never again", "disappointed", "worst", "not good",
]

VAGUE_POSITIVE_PATTERNS = [
    "good", "great", "nice", "amazing", "loved it", "perfect", "excellent",
]

NEGATIVE_DETAIL_TERMS = [
    "not working", "broken", "dirty", "smelled", "noisy", "loud", "issue",
    "problem", "leak", "stuck", "failed", "unusable",
]

ALLOWED_ASPECTS = [aspect.value for aspect in Aspect]
ALLOWED_RESPONSE_TYPES = [
    ResponseType.QUICK_TAP.value,
    ResponseType.MULTI_SELECT.value,
    ResponseType.FREE_TEXT.value,
    ResponseType.PRIVATE_TEXT.value,
]


def _extract_review_text(review_text_or_ctx: Union[str, ReviewContext]) -> str:
    if isinstance(review_text_or_ctx, ReviewContext):
        return (review_text_or_ctx.review_text_en or review_text_or_ctx.review_text).strip()
    return str(review_text_or_ctx).strip()


def _contains_keyword(text: str, keyword: str) -> bool:
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return re.search(pattern, text) is not None


def _build_review_context(review_text: str) -> dict:
    normalized = review_text.lower()
    matched_aspects = []
    for aspect, keywords in ISSUE_KEYWORDS.items():
        hits = [keyword for keyword in keywords if _contains_keyword(normalized, keyword)]
        if hits:
            matched_aspects.append({"aspect": aspect, "evidence": hits[:3]})

    vague_negative = (
        len(review_text.split()) <= 8
        and any(pattern in normalized for pattern in VAGUE_NEGATIVE_PATTERNS)
    )
    vague_positive = (
        len(review_text.split()) <= 8
        and any(pattern in normalized for pattern in VAGUE_POSITIVE_PATTERNS)
    )
    has_specific_negative_detail = any(term in normalized for term in NEGATIVE_DETAIL_TERMS)
    broad_review = (vague_negative or vague_positive) and not matched_aspects

    return {
        "review_length_words": len(review_text.split()),
        "matched_aspects": matched_aspects,
        "has_specific_negative_detail": has_specific_negative_detail,
        "vague_negative": vague_negative,
        "vague_positive": vague_positive,
        "broad_review": broad_review,
        "high_frequency_hotel_topics": HIGH_FREQUENCY_HOTEL_TOPICS,
        "notable_terms": re.findall(r"\b[a-zA-Z]{4,}\b", normalized)[:12],
    }


def _routing_mode(review_context: dict) -> str:
    if review_context["matched_aspects"] and review_context["has_specific_negative_detail"]:
        return "specific_issue"
    if review_context["vague_positive"]:
        return "vague_positive"
    if review_context["vague_negative"]:
        return "vague_negative"
    return "general"


def _build_response_schema() -> dict:
    return {
        "type": "json_schema",
        "name": "generated_follow_up_questions",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "qid": {"type": "string"},
                            "aspect": {"type": "string", "enum": ALLOWED_ASPECTS},
                            "text_en": {"type": "string"},
                            "response_type": {"type": "string", "enum": ALLOWED_RESPONSE_TYPES},
                            "options": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "private": {"type": "boolean"},
                            "reason": {"type": "string"},
                        },
                        "required": [
                            "qid",
                            "aspect",
                            "text_en",
                            "response_type",
                            "options",
                            "private",
                            "reason",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["questions"],
            "additionalProperties": False,
        },
    }


def _build_prompt(review_text: str, review_context: dict, routing_mode: str) -> str:
    context_json = json.dumps(review_context, indent=2)
    routing_notes = {
        "specific_issue": (
            "The guest clearly mentioned a specific problem area. Ask follow-ups that dig deeper into that same issue."
        ),
        "vague_positive": (
            "The guest gave broad praise. Ask for concrete detail using common hotel topics so we learn what went well."
        ),
        "vague_negative": (
            "The guest gave a broad negative review. Ask concrete questions using high-frequency hotel problem topics."
        ),
        "general": (
            "Use the review content and common hotel topics to ask the most useful clarifying questions."
        ),
    }

    return f"""You are a hotel review follow-up agent.

Your job is to generate up to {MAX_QUESTIONS} follow-up questions that help the hotel understand the guest better.

## Guest Review
"{review_text}"

## Review Analysis Context
{context_json}

## Routing Mode
{routing_mode}

## Routing Rule
{routing_notes[routing_mode]}

## Core Logic
1. If the guest clearly complains about a specific thing, deeply investigate that same thing.
2. For example, if the guest says the noise was bad, ask whether it came from the street, neighboring rooms, ventilation, or something else.
3. If the review is vague, use common high-frequency hotel topics as entry points.
4. When the review is broad positive, ask what specifically stood out in a good way.
5. When the review is broad negative, ask what specific issue caused the bad experience.
6. Prefer questions with selectable options to reduce typing.
7. Only use free text when options would be too limiting.
8. Make every question concrete and actionable. Avoid generic prompts like "Anything else?"
9. Do not repeat what the guest already made fully clear unless you are drilling deeper into the source of the issue.
10. If you use options, include "Other" only when it genuinely helps.

## Output Requirements
1. Return at most {MAX_QUESTIONS} questions.
2. Generate the actual question text yourself. Do not rely on a fixed bank.
3. Use `quick_tap` for single-choice options, `multi_select` when multiple causes may apply, `free_text` only when needed, and `private_text` only for sensitive hygiene/safety issues.
4. Use one of these aspects exactly: {", ".join(ALLOWED_ASPECTS)}.
5. Each question must include a short `reason` describing why you asked it.
6. Use stable generated qids like `q_generated_01`, `q_generated_02`.

## Response Format
Return JSON with this shape:
{{
  "questions": [
    {{
      "qid": "q_generated_01",
      "aspect": "noise",
      "text_en": "Where was the noise coming from most?",
      "response_type": "quick_tap",
      "options": ["Street traffic", "Neighboring room", "Hallway", "Ventilation / AC", "Other"],
      "private": false,
      "reason": "The guest complained about noise but did not say what caused it."
    }}
  ]
}}

Return only JSON."""


def decide_questions(review_text_or_ctx: Union[str, ReviewContext]) -> AgentDecision:
    review_text = _extract_review_text(review_text_or_ctx)
    if not review_text:
        raise ValueError("review_text cannot be empty")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Add it to backend/.env for local runs or your deployment env vars."
        )

    review_context = _build_review_context(review_text)
    routing_mode = _routing_mode(review_context)

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": _build_prompt(review_text, review_context, routing_mode),
                    }
                ],
            }
        ],
        max_output_tokens=1400,
        text={"format": _build_response_schema()},
    )

    parsed = json.loads(response.output_text.strip())
    generated_questions = parsed.get("questions", [])[:MAX_QUESTIONS]

    questions = []
    rationale = {}
    for index, item in enumerate(generated_questions, start=1):
        qid = item["qid"]
        rationale[qid] = item["reason"]
        questions.append(
            Question(
                qid=qid,
                aspect=Aspect(item["aspect"]),
                text_en=item["text_en"],
                response_type=ResponseType(item["response_type"]),
                options=item.get("options", []),
                priority=float(index),
                private=item.get("private", False),
            )
        )

    skipped = []
    if not questions:
        skipped.append(("generation", "model did not return any follow-up questions"))

    return AgentDecision(
        questions=questions,
        rationale=rationale,
        skipped=skipped,
    )
