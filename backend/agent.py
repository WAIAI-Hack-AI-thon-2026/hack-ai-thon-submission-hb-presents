"""
The Follow-up Question Agent — powered by OpenAI.

Entry point: `decide_questions(review_text_or_ctx) -> AgentDecision`.

Pipeline:
    1. Send the review text to OpenAI with the question bank as context
    2. The model analyzes what aspects are missing / need clarification
    3. Returns up to 3 targeted follow-up questions in structured JSON
    4. Parse the response into AgentDecision
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

HOTEL_REVIEW_HOTSPOTS = [
    "Bathroom condition",
    "Room cleanliness",
    "Noise at night",
    "AC / heating",
    "Staff helpfulness",
]

UNDEREXPLORED_ASPECTS = [
    "Check-in delay",
    "Unexpected fees",
    "Bed comfort",
    "Bad smell",
    "Worn / broken fixtures",
]

COMMON_HOTEL_ISSUES = [
    "Room cleanliness",
    "Bathroom condition",
    "Noise at night",
    "AC / heating",
    "Staff helpfulness",
    "Unexpected fees",
    "Bed comfort",
    "Check-in delay",
    "Bad smell",
    "Worn / broken fixtures",
]

ISSUE_KEYWORDS = {
    "cleanliness": ["dirty", "unclean", "stain", "dust", "hair", "filthy", "gross", "messy"],
    "bathroom": ["bathroom", "shower", "toilet", "sink", "drain", "tub"],
    "noise": ["noise", "noisy", "loud", "couldn't sleep", "street", "construction"],
    "ac_heat": ["ac", "air conditioning", "heating", "heater", "temperature", "hot", "cold"],
    "staff": ["staff", "service", "front desk", "reception", "rude", "helpful"],
    "billing": ["charge", "charged", "fee", "bill", "deposit", "refund", "price"],
    "bed": ["bed", "mattress", "pillow", "linens", "sleep"],
    "checkin": ["check in", "check-in", "checkout", "check out", "wait", "line"],
    "smell": ["smell", "odor", "odour", "musty", "smoke", "sewage"],
    "renovation": ["dated", "old", "worn", "broken", "repair", "maintenance"],
}

VAGUE_NEGATIVE_PATTERNS = [
    "bad", "awful", "terrible", "horrible", "never again", "disappointed", "worst", "not good",
]

VAGUE_POSITIVE_PATTERNS = [
    "good", "great", "nice", "amazing", "loved it", "perfect", "excellent",
]

NEGATIVE_DETAIL_TERMS = [
    "not working", "broken", "bad", "dirty", "smelled", "smell", "noisy", "loud",
    "issue", "problem", "leak", "stuck", "worst", "terrible", "awful", "failed",
]

ASPECT_TO_QIDS = {
    "bathroom": ["q_bathroom_01", "q_cleanliness_01"],
    "billing": ["q_billing_01", "q_value_01"],
    "smell": ["q_smell_01", "q_cleanliness_01"],
    "amenities": ["q_amenities_01"],
    "noise": ["q_noise_01", "q_bed_01"],
    "ac_heat": ["q_ac_01", "q_noise_01"],
    "checkin": ["q_checkin_01", "q_staff_01"],
    "bed": ["q_bed_01"],
    "staff": ["q_staff_01", "q_checkin_01"],
    "cleanliness": ["q_cleanliness_01", "q_bathroom_01"],
    "family": ["q_family_01"],
    "renovation": ["q_renovation_01"],
}

POSITIVE_DETAIL_QIDS = [
    "q_positive_detail_01",
    "q_staff_01",
    "q_value_01",
    "q_bed_01",
    "q_amenities_01",
    "q_checkin_01",
]

NEGATIVE_FALLBACK_QIDS = [
    "q_issue_drilldown_01",
    "q_cleanliness_01",
    "q_bathroom_01",
    "q_noise_01",
    "q_ac_01",
    "q_checkin_01",
    "q_billing_01",
    "q_bed_01",
    "q_smell_01",
    "q_renovation_01",
]

# All available question templates the model can pick from
QUESTION_TEMPLATES = [
    {
        "qid": "q_bathroom_01",
        "aspect": "bathroom",
        "text_en": "What was the main bathroom issue you noticed?",
        "response_type": "quick_tap",
        "options": ["No issue", "Not clean", "Drainage / plumbing issue", "Weak water pressure", "Something broken", "Other"],
        "description": "Use to pinpoint the exact bathroom problem instead of asking broadly",
    },
    {
        "qid": "q_billing_01",
        "aspect": "billing",
        "text_en": "Which billing issue fits best?",
        "response_type": "quick_tap",
        "options": ["No billing issue", "Deposit still held", "Unexpected fee", "Rate didn't match booking", "Refund delay", "Other"],
        "description": "Use when pricing or charges may be part of the complaint",
    },
    {
        "qid": "q_smell_01",
        "aspect": "smell",
        "text_en": "What kind of smell did you notice most?",
        "response_type": "quick_tap",
        "options": ["No issue", "Smoke", "Musty / damp", "Sewage / drain", "Chemical (cleaning)", "Other"],
        "description": "Use when cleanliness or room discomfort may be smell-related",
    },
    {
        "qid": "q_amenities_01",
        "aspect": "amenities",
        "text_en": "Which in-room amenity caused trouble?",
        "response_type": "multi_select",
        "options": ["No amenity issue", "Hairdryer", "TV", "Wi-Fi device", "Kettle / minibar", "Lighting / outlets", "Other"],
        "description": "Use to narrow the problem to a specific amenity",
    },
    {
        "qid": "q_noise_01",
        "aspect": "noise",
        "text_en": "Where was the noise coming from most?",
        "response_type": "quick_tap",
        "options": ["No major noise", "Street traffic", "Other rooms / hallway", "Hotel bar / events", "Construction", "AC / ventilation", "Other"],
        "description": "Use to isolate the main noise source",
    },
    {
        "qid": "q_ac_01",
        "aspect": "ac_heat",
        "text_en": "What was the main AC / heating issue?",
        "response_type": "quick_tap",
        "options": ["No issue", "Wouldn't cool", "Wouldn't heat", "Too loud", "Broken / unresponsive", "Controls unclear", "Other"],
        "description": "Use when temperature comfort or HVAC is part of the experience",
    },
    {
        "qid": "q_checkin_01",
        "aspect": "checkin",
        "text_en": "What went wrong during check-in or check-out?",
        "response_type": "quick_tap",
        "options": ["No issue", "Long wait", "Room not ready", "Staff not helpful", "Reservation issue", "Billing issue", "Other"],
        "description": "Use to narrow the arrival or departure pain point",
    },
    {
        "qid": "q_bed_01",
        "aspect": "bed",
        "text_en": "Which bed-related issue best matches your stay?",
        "response_type": "quick_tap",
        "options": ["No bed issue", "Too soft", "Too hard", "Pillow issue", "Bed too small / creaky", "Linens not clean", "Other"],
        "description": "Use to pinpoint the sleep-comfort problem",
    },
    {
        "qid": "q_staff_01",
        "aspect": "staff",
        "text_en": "How would you describe the staff interaction?",
        "response_type": "quick_tap",
        "options": ["Especially helpful", "Friendly but routine", "Slow response", "Not helpful", "Rude", "Other"],
        "description": "Use to capture service quality with minimal typing",
    },
    {
        "qid": "q_value_01",
        "aspect": "value",
        "text_en": "How did the stay compare with the price you paid?",
        "response_type": "quick_tap",
        "options": ["Better than expected", "Fair for price", "Overpriced for what I got", "Unexpected fees hurt value"],
        "description": "Use when the guest's value perception needs clarification",
    },
    {
        "qid": "q_cleanliness_01",
        "aspect": "cleanliness",
        "text_en": "What cleanliness issue stood out most?",
        "response_type": "quick_tap",
        "options": ["No cleanliness issue", "Hair / dust", "Stained linens / towels", "Bathroom not clean", "Trash left behind", "Other"],
        "description": "Use to turn a vague cleanliness concern into a specific issue",
    },
    {
        "qid": "q_family_01",
        "aspect": "family",
        "text_en": "What family-related issue affected the stay most?",
        "response_type": "quick_tap",
        "options": ["No family issue", "Room too small", "No crib / extra bed", "Kid amenities missing", "Layout not family-friendly", "Other"],
        "description": "Use when group or family travel is implied",
    },
    {
        "qid": "q_renovation_01",
        "aspect": "renovation",
        "text_en": "What looked most worn or in need of repair?",
        "response_type": "quick_tap",
        "options": ["Nothing stood out", "Furniture dated", "Carpet / walls worn", "Bathroom fixtures broken", "Electrical / lighting issue", "Other"],
        "description": "Use when the guest hints that the property feels old or poorly maintained",
    },
    {
        "qid": "q_pests_01",
        "aspect": "pests",
        "text_en": "Which serious hygiene issue should the property review privately?",
        "response_type": "multi_select",
        "options": ["Saw pests", "Mold / mildew", "Strong sewage smell", "Stained linens / towels", "Bathroom not sanitized", "Other"],
        "description": "Private channel for severe hygiene issues, with options first",
        "private": True,
    },
    {
        "qid": "q_issue_drilldown_01",
        "aspect": "catch_all",
        "text_en": "Which part of the stay needs the most improvement?",
        "response_type": "quick_tap",
        "options": COMMON_HOTEL_ISSUES + ["Other"],
        "description": "Use for vague reviews; rely on common hotel complaint clusters instead of a broad free-text catch-all",
    },
    {
        "qid": "q_positive_detail_01",
        "aspect": "catch_all",
        "text_en": "Which part of the stay stood out most in a good way?",
        "response_type": "quick_tap",
        "options": HOTEL_REVIEW_HOTSPOTS + UNDEREXPLORED_ASPECTS + ["Other"],
        "description": "Use for broad positive reviews to turn generic praise into a concrete strength",
    },
]


RESPONSE_SCHEMA = {
    "type": "json_schema",
    "name": "follow_up_question_selection",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "selected_qids": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [template["qid"] for template in QUESTION_TEMPLATES],
                },
            },
            "rationales": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "qid": {
                            "type": "string",
                            "enum": [template["qid"] for template in QUESTION_TEMPLATES],
                        },
                        "reason": {"type": "string"},
                    },
                    "required": ["qid", "reason"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["selected_qids", "rationales"],
        "additionalProperties": False,
    },
}


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
    prioritized_qids = []
    for item in matched_aspects:
        prioritized_qids.extend(ASPECT_TO_QIDS.get(item["aspect"], []))
    prioritized_qids = list(dict.fromkeys(prioritized_qids))[:MAX_QUESTIONS]

    emphasis_terms = re.findall(r"\b[a-zA-Z]{4,}\b", normalized)
    return {
        "review_length_words": len(review_text.split()),
        "matched_aspects": matched_aspects,
        "has_specific_negative_detail": has_specific_negative_detail,
        "broad_review": broad_review,
        "vague_negative": vague_negative,
        "vague_positive": vague_positive,
        "hotel_review_hotspots": HOTEL_REVIEW_HOTSPOTS,
        "underexplored_aspects": UNDEREXPLORED_ASPECTS,
        "prioritized_qids_from_detected_aspects": prioritized_qids,
        "common_hotel_issues": COMMON_HOTEL_ISSUES,
        "notable_terms": emphasis_terms[:12],
    }


def _select_allowed_qids(review_context: dict) -> tuple[list[str], str]:
    prioritized_qids = review_context.get("prioritized_qids_from_detected_aspects", [])
    if prioritized_qids:
        allowed_qids = list(dict.fromkeys(
            prioritized_qids
            + ["q_issue_drilldown_01", "q_pests_01"]
        ))
        return allowed_qids, "specific_issue"

    if review_context.get("vague_positive"):
        return POSITIVE_DETAIL_QIDS, "vague_positive"

    if review_context.get("vague_negative"):
        return NEGATIVE_FALLBACK_QIDS, "vague_negative"

    return [template["qid"] for template in QUESTION_TEMPLATES], "general"


def _build_response_schema(allowed_qids: list[str]) -> dict:
    return {
        "type": "json_schema",
        "name": "follow_up_question_selection",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "selected_qids": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": allowed_qids,
                    },
                },
                "rationales": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "qid": {
                                "type": "string",
                                "enum": allowed_qids,
                            },
                            "reason": {"type": "string"},
                        },
                        "required": ["qid", "reason"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["selected_qids", "rationales"],
            "additionalProperties": False,
        },
    }


def _build_prompt(review_text: str, review_context: dict, allowed_templates: list[dict], routing_mode: str) -> str:
    templates_json = json.dumps(allowed_templates, indent=2)
    context_json = json.dumps(review_context, indent=2)
    routing_notes = {
        "specific_issue": "The guest already named a specific problem area. Stay tightly focused on that area and adjacent clarification only.",
        "vague_positive": "The guest gave broad praise. Ask only positive-detail or missing-aspect questions that make the praise concrete.",
        "vague_negative": "The guest gave a broad negative review. Ask only high-frequency negative aspect questions to identify the main pain point.",
        "general": "Use your normal judgment across the allowed templates.",
    }
    return f"""You are a hotel review analysis agent. A guest just submitted a review. Your job is to pick the most relevant follow-up questions to ask them.

## Guest's Review:
"{review_text}"

## Review Analysis Context:
{context_json}

## Routing Mode:
{routing_mode}

## Routing Rule:
{routing_notes[routing_mode]}

## Available Question Templates:
{templates_json}

## Instructions:
1. Analyze the review to understand what aspects the guest mentioned and what's missing
2. Pick up to {MAX_QUESTIONS} questions that would provide the most valuable additional feedback
3. You may select ONLY from the Available Question Templates shown above
4. DO NOT ask about things the guest already clearly addressed in their review unless you are drilling into the exact failure mode
5. Prioritize concrete drill-down questions about the exact pain point, not broad satisfaction questions
6. Prefer questions with options over free-text so the guest can answer quickly
7. Only use "Other" style questions when the predefined options still leave meaningful ambiguity
8. Avoid generic catch-all wording; every selected question should point to a concrete area

## Response Format:
Return a JSON object with exactly this structure:
{{
  "selected_qids": ["q_xxx", "q_yyy", "q_zzz"],
  "rationales": [
    {{"qid": "q_xxx", "reason": "brief reason why this question is relevant"}},
    {{"qid": "q_yyy", "reason": "brief reason"}},
    {{"qid": "q_zzz", "reason": "brief reason"}}
  ]
}}

Return ONLY the JSON, no other text."""


def decide_questions(review_text_or_ctx: Union[str, ReviewContext]) -> AgentDecision:
    """Use OpenAI to analyze the review and pick follow-up questions."""
    review_text = _extract_review_text(review_text_or_ctx)
    if not review_text:
        raise ValueError("review_text cannot be empty")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Add it to backend/.env for local runs or your deployment env vars."
        )

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    review_context = _build_review_context(review_text)
    allowed_qids, routing_mode = _select_allowed_qids(review_context)
    allowed_templates = [
        template for template in QUESTION_TEMPLATES if template["qid"] in allowed_qids
    ]
    response_schema = _build_response_schema(allowed_qids)

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": _build_prompt(
                            review_text,
                            review_context,
                            allowed_templates,
                            routing_mode,
                        ),
                    }
                ],
            }
        ],
        max_output_tokens=1024,
        text={"format": response_schema},
    )

    response_text = response.output_text.strip()
    parsed = json.loads(response_text)

    selected_qids = parsed.get("selected_qids", [])
    rationale = {
        item["qid"]: item["reason"]
        for item in parsed.get("rationales", [])
        if item.get("qid") and item.get("reason")
    }

    # Build Question objects from templates
    template_map = {t["qid"]: t for t in QUESTION_TEMPLATES}
    questions = []
    for qid in selected_qids[:MAX_QUESTIONS]:
        tmpl = template_map.get(qid)
        if not tmpl:
            continue
        questions.append(Question(
            qid=tmpl["qid"],
            aspect=Aspect(tmpl["aspect"]),
            text_en=tmpl["text_en"],
            response_type=ResponseType(tmpl["response_type"]),
            options=tmpl.get("options", []),
            priority=len(questions) + 1,
            private=tmpl.get("private", False),
        ))

    # Build skipped list
    skipped = []
    for tmpl in QUESTION_TEMPLATES:
        if tmpl["qid"] not in selected_qids:
            reason = rationale.get(tmpl["qid"], "not selected by agent")
            skipped.append((tmpl["qid"], reason))

    return AgentDecision(
        questions=questions,
        rationale=rationale,
        skipped=skipped,
    )
