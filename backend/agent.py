"""
Follow-up Question Agent — 2-slot design, powered by OpenAI.

Entry point: `decide_questions(review_text_or_ctx, property_id) -> AgentDecision`

Slot 1 — COMMENT DEEP-DIVE
    LLM digs deeper into what the guest already wrote.

Slot 2 — INFORMATION GAP
    Data-driven: picks from the hotel's least-covered evidence labels
    (loaded from hotel_evidence_profiles.json + aspect_dictionary.json)
    to fill missing information.
"""
from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Union

from dotenv import load_dotenv
from openai import OpenAI

try:
    from .schema import AgentDecision, Aspect, Question, ResponseType, ReviewContext
    from .evidence_analysis import match_labels
except ImportError:
    from schema import AgentDecision, Aspect, Question, ResponseType, ReviewContext
    from evidence_analysis import match_labels

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MAX_QUESTIONS = 2
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"

ALLOWED_ASPECTS = [a.value for a in Aspect]
ALLOWED_RESPONSE_TYPES = [
    ResponseType.QUICK_TAP.value,
    ResponseType.MULTI_SELECT.value,
    ResponseType.FREE_TEXT.value,
    ResponseType.PRIVATE_TEXT.value,
]
ALLOWED_ROLES = ["comment_deepdive", "information_gap"]

# ── Data caches ──────────────────────────────────────────────────────────
_aspect_dict: dict | None = None
_evidence_profiles: dict | None = None


def _resolve_data_dir() -> Path:
    backend_dir = Path(__file__).resolve().parent
    candidates = [
        backend_dir.parent / "data",
        backend_dir / "data",
        Path.cwd() / "data",
    ]
    for c in candidates:
        if (c / "aspect_dictionary.json").exists():
            return c
    return backend_dir.parent / "data"


def _load_aspect_dictionary() -> dict:
    global _aspect_dict
    if _aspect_dict is not None:
        return _aspect_dict
    path = _resolve_data_dir() / "aspect_dictionary.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            _aspect_dict = json.load(f)
    except (OSError, json.JSONDecodeError):
        _aspect_dict = {}
    return _aspect_dict


def _load_evidence_profiles() -> dict:
    global _evidence_profiles
    if _evidence_profiles is not None:
        return _evidence_profiles
    path = _resolve_data_dir() / "hotel_evidence_profiles.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            _evidence_profiles = json.load(f)
    except (OSError, json.JSONDecodeError):
        _evidence_profiles = {}
    return _evidence_profiles


# ── Gap detection ────────────────────────────────────────────────────────

def _get_gap_aspects(
    property_id: str,
    review_mentioned: list[str],
    pick_n: int = 3,
) -> list[dict]:
    """
    Randomly sample `pick_n` aspects from the hotel's low-coverage pool,
    so different guests get asked about different gaps.

    Strategy:
      1. Collect all candidate aspects (excluding those the review covers).
      2. Split into two tiers:
         - Tier A: coverage <= 5%  (never mentioned or very rare)
         - Tier B: coverage 5-25% (low but not zero)
      3. Randomly sample from tier A first, then fill from tier B.
    """
    profiles = _load_evidence_profiles()
    aspect_dict = _load_aspect_dictionary()

    hotel = profiles.get(property_id, {})
    mentioned_set = set(review_mentioned)

    # Build aspect -> percentage map from hotel profile
    freq_map: dict[str, float] = {}
    for item in hotel.get("frequently_mentioned", []):
        freq_map[item["label"]] = item["percentage"]

    never_mentioned = set(hotel.get("never_mentioned", []))

    tier_a: list[dict] = []  # <= 5% coverage
    tier_b: list[dict] = []  # 5-25% coverage

    for aspect_key, info in aspect_dict.items():
        if aspect_key in mentioned_set:
            continue

        if aspect_key in never_mentioned:
            pct = 0.0
        elif aspect_key in freq_map:
            pct = freq_map[aspect_key]
        elif hotel:
            pct = 0.0
        else:
            pct = info.get("global_mention_count", 500) / 30.0

        entry = {
            "aspect": aspect_key,
            "label": info.get("label", aspect_key),
            "percentage": pct,
            "question_points": info.get("question_points", []),
        }

        if pct <= 5.0:
            tier_a.append(entry)
        elif pct <= 25.0:
            tier_b.append(entry)

    # Randomly sample: prioritize tier A, fill remainder from tier B
    random.shuffle(tier_a)
    random.shuffle(tier_b)
    pool = tier_a + tier_b
    return pool[:pick_n]


# ── Helpers ──────────────────────────────────────────────────────────────

def _extract_review_text(review_text_or_ctx: Union[str, ReviewContext]) -> str:
    if isinstance(review_text_or_ctx, ReviewContext):
        return (review_text_or_ctx.review_text_en or review_text_or_ctx.review_text).strip()
    return str(review_text_or_ctx).strip()


def _build_guest_rating_context(review_text_or_ctx: Union[str, ReviewContext]) -> str:
    if not isinstance(review_text_or_ctx, ReviewContext):
        return "Guest rating metadata unavailable."

    overall = (
        f"{review_text_or_ctx.overall_rating}/5"
        if review_text_or_ctx.overall_rating is not None
        else "not provided"
    )
    sub_ratings = review_text_or_ctx.sub_ratings or {}
    if not sub_ratings:
        return (
            f"Guest gave this property {overall} stars.\n"
            "Sub-ratings provided: none."
        )

    provided = []
    missing = []
    for aspect, value in sub_ratings.items():
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric > 0:
            provided.append(f"{aspect}={numeric:g}")
        else:
            missing.append(aspect)

    provided_text = ", ".join(provided) if provided else "none"
    missing_text = ", ".join(missing) if missing else "none"
    return (
        f"Guest gave this property {overall} stars.\n"
        f"Sub-ratings provided: {provided_text}.\n"
        f"Sub-ratings NOT provided (0 = missing): {missing_text}."
    )


# ── Prompt & schema ─────────────────────────────────────────────────────

def _build_response_schema() -> dict:
    return {
        "type": "json_schema",
        "name": "follow_up_questions",
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
                            "role": {"type": "string", "enum": ALLOWED_ROLES},
                            "aspect": {"type": "string", "enum": ALLOWED_ASPECTS},
                            "text_en": {"type": "string"},
                            "response_type": {
                                "type": "string",
                                "enum": ALLOWED_RESPONSE_TYPES,
                            },
                            "options": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "private": {"type": "boolean"},
                            "reason": {"type": "string"},
                        },
                        "required": [
                            "qid", "role", "aspect", "text_en",
                            "response_type", "options", "private", "reason",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["questions"],
            "additionalProperties": False,
        },
    }


def _build_prompt(
    review_text: str,
    gap_aspects: list[dict],
    guest_rating_context: str,
) -> str:
    # Format gap aspects for the prompt
    gap_lines: list[str] = []
    for i, gap in enumerate(gap_aspects, 1):
        points = "\n".join(f"      - {p}" for p in gap["question_points"])
        gap_lines.append(
            f"  {i}. **{gap['label']}** (aspect key: `{gap['aspect']}`, "
            f"current coverage: {gap['percentage']:.1f}%)\n"
            f"    Possible question angles:\n{points}"
        )
    gap_context = "\n\n".join(gap_lines) if gap_lines else "  No specific gaps identified — use your best judgment."

    return f"""You are a hotel review follow-up agent.
Generate exactly 2 follow-up questions for the guest who just submitted a review.

═══════════════════════════════════════════════════════
QUESTION 1 — COMMENT DEEP-DIVE  (role: "comment_deepdive")
═══════════════════════════════════════════════════════
Based on what the guest wrote, ask a follow-up that digs deeper or extends their experience.

Rules:
- If the guest mentions a specific problem, drill into the root cause or details.
  Example: guest says "noisy" → ask where the noise came from (street, neighbors, elevator, AC).
- If the guest mentions something positive, ask what specifically stood out.
  Example: guest says "great staff" → ask which interaction was most memorable.
- If the review is vague or very short, ask a clarifying question about what stood out most.
- The aspect MUST match a topic the guest actually discussed.
- Prefer `quick_tap` or `multi_select` with 4-6 concrete, scenario-based options.

═══════════════════════════════════════════════════════
QUESTION 2 — INFORMATION GAP  (role: "information_gap")
═══════════════════════════════════════════════════════
This hotel has LOW coverage on certain topics — previous guests rarely or never mentioned them.
Ask a question about ONE of the gap aspects below to collect new information.

Gap aspects (lowest coverage first — prioritize the top ones):

{gap_context}

Rules for Q2:
- Pick ONE aspect from the gap list above.
- Use "Possible question angles" as inspiration — turn one into a natural, scenario-based question.
- The question should feel relevant and not random. Connect it to the guest's stay context when possible.
  Example: if the guest stayed with family, a "family_amenities" gap question feels natural.
- Do NOT repeat anything the guest already covered in their review.
- If the gap aspect has 0% coverage, this is the highest priority — the hotel has ZERO data on this topic.

═══════════════════════════════════════════════════════
OUTPUT RULES
═══════════════════════════════════════════════════════
1. Return exactly 2 questions: Q1 with role "comment_deepdive", Q2 with role "information_gap".
2. Use `quick_tap` for single-choice, `multi_select` when multiple answers apply, `free_text` only when options would be too limiting.
3. Provide 4-6 concrete options for quick_tap/multi_select. Include "Other" only when it genuinely helps.
4. Each question must use one of these aspects: {", ".join(ALLOWED_ASPECTS)}.
5. Each question needs a short `reason` explaining why you asked it.
6. Use qids: "q_deepdive_01" for Q1, "q_gap_01" for Q2.
7. Make questions concise, friendly, and actionable. Avoid generic phrases like "Anything else?"
8. Set `private` to true only for sensitive issues (hygiene, safety, pests).

═══════════════════════════════════════════════════════
GUEST INPUT
═══════════════════════════════════════════════════════

Review text:
"{review_text}"

{guest_rating_context}

Return JSON only."""


# ── Entry point ──────────────────────────────────────────────────────────

def decide_questions(
    review_text_or_ctx: Union[str, ReviewContext],
    property_id: str | None = None,
) -> AgentDecision:
    review_text = _extract_review_text(review_text_or_ctx)
    if not review_text:
        raise ValueError("review_text cannot be empty")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Add it to backend/.env or deployment env vars."
        )

    # Resolve property ID
    resolved_pid = (property_id or "").strip() or None
    if not resolved_pid and isinstance(review_text_or_ctx, ReviewContext):
        resolved_pid = (review_text_or_ctx.property_id or "").strip() or None

    # Detect which aspects the review already covers (via evidence_analysis patterns)
    review_mentioned = match_labels(review_text)

    # Find this hotel's lowest-coverage aspects, excluding already-mentioned ones
    gap_aspects = _get_gap_aspects(resolved_pid or "", review_mentioned)

    # Build context
    guest_rating_context = _build_guest_rating_context(review_text_or_ctx)

    # Build prompt and call OpenAI
    prompt = _build_prompt(review_text, gap_aspects, guest_rating_context)

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
        max_output_tokens=1200,
        text={"format": _build_response_schema()},
    )

    parsed = json.loads(response.output_text.strip())
    generated = parsed.get("questions", [])[:MAX_QUESTIONS]

    questions: list[Question] = []
    rationale: dict[str, str] = {}
    for idx, item in enumerate(generated, 1):
        qid = item["qid"]
        rationale[qid] = item.get("reason", "")
        questions.append(
            Question(
                qid=qid,
                aspect=Aspect(item["aspect"]),
                text_en=item["text_en"],
                response_type=ResponseType(item["response_type"]),
                role=item.get("role", ""),
                options=item.get("options", []),
                priority=float(idx),
                private=item.get("private", False),
            )
        )

    skipped: list[tuple[str, str]] = []
    if not questions:
        skipped.append(("generation", "model did not return any questions"))

    return AgentDecision(
        questions=questions,
        rationale=rationale,
        skipped=skipped,
    )
