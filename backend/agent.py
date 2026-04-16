"""
Follow-up Question Agent — 2-slot design, powered by OpenAI.

Entry point: `decide_questions(review_text_or_ctx, property_id) -> AgentDecision`

Slot 1 — COMMENT DEEP-DIVE
    LLM digs deeper into what the guest already wrote / their ratings.

Slot 2 — CONFLICT RESOLUTION  or  INFORMATION GAP  (mutually exclusive)
    If the hotel has active conflicts (contradictory / stale / persistent),
    Slot 2 asks about the conflict so it can be resolved.
    Otherwise, Slot 2 fills an information gap from the hotel's
    least-covered evidence labels.
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
    from .conflict_detection import get_active_conflicts
except ImportError:
    from schema import AgentDecision, Aspect, Question, ResponseType, ReviewContext
    from evidence_analysis import match_labels
    from conflict_detection import get_active_conflicts

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
ALLOWED_ROLES = ["comment_deepdive", "information_gap", "conflict_resolution"]

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


def _build_conflict_context(conflicts: list[dict]) -> str:
    """Format conflict records into a prompt section for Slot 3."""
    if not conflicts:
        return ""

    STATUS_DESC = {
        "conflicting": "Recent reviews DISAGREE — one says good, another says bad.",
        "persistent": "Multiple guests reported this issue and no one has confirmed it's fixed.",
        "stale_issue": "A past guest reported this issue long ago. No recent review mentions it — unknown if fixed.",
    }

    lines: list[str] = []
    for c in conflicts:
        desc = STATUS_DESC.get(c["status"], c["status"])
        neg_snip = c.get("negative_snippet", "")[:200]
        pos_snip = c.get("positive_snippet") or ""
        pos_snip = pos_snip[:200]

        block = (
            f"  Topic: **{c['topic']}**  |  Status: {c['status'].upper()}\n"
            f"  {desc}\n"
            f"  ⚠️ THE SPECIFIC ISSUE — extract the concrete detail from this snippet for your question:\n"
            f"  Negative review ({c.get('negative_date', '?')}, {c.get('negative_age_days', '?')} days ago):\n"
            f'    "{neg_snip}"\n'
        )
        if pos_snip:
            block += (
                f"  Contradicting positive review ({c.get('positive_date', '?')}, {c.get('positive_age_days', '?')} days ago):\n"
                f'    "{pos_snip}"\n'
            )
        lines.append(block)

    return "\n".join(lines)


def _build_prompt(
    review_text: str,
    gap_aspects: list[dict],
    guest_rating_context: str,
    conflicts: list[dict] | None = None,
) -> str:
    has_conflicts = bool(conflicts)

    has_review_text = bool(review_text.strip())

    # ── Slot 1: Comment deep-dive ──────────────────────────────────────
    if has_review_text:
        q1_section = """═══════════════════════════════════════════════════════
QUESTION 1 — COMMENT DEEP-DIVE  (role: "comment_deepdive")
═══════════════════════════════════════════════════════
Based on what the guest wrote AND their ratings, ask a follow-up that digs deeper.

Rules:
- If the guest mentions a specific problem, drill into the root cause or details.
  Example: guest says "noisy" → ask where the noise came from (street, neighbors, elevator, AC).
- If the guest mentions something positive, ask what specifically stood out.
  Example: guest says "great staff" → ask which interaction was most memorable.
- If the review is vague or very short (e.g. just "great" or "good"), USE THE RATINGS to guide your question:
  - If a sub-rating is notably LOW (1-2 stars), ask about that specific aspect: "You rated [aspect] quite low — what went wrong?"
  - If all ratings are HIGH, ask which aspect impressed them most, with concrete scenario-based options.
- If sub-ratings show a gap between overall and a specific category, probe that gap.
  Example: overall=4 but cleanliness=2 → ask what the cleanliness issue was.
- The aspect MUST match a topic the guest discussed OR a sub-rating category.
- Prefer `quick_tap` or `multi_select` with 4-6 concrete, scenario-based options."""
    else:
        q1_section = """═══════════════════════════════════════════════════════
QUESTION 1 — RATING-DRIVEN QUESTION  (role: "comment_deepdive")
═══════════════════════════════════════════════════════
The guest only gave ratings without writing a review. Use the RATINGS to drive your question.

Rules:
- CHECK the sub-ratings carefully. Your question strategy depends on what the ratings reveal:
  1. If ANY sub-rating is notably LOW (1-2 stars): ask specifically about that aspect.
     Example: staff=2 → "What happened with the staff that didn't meet expectations?" with options like "Rude behavior", "Slow service", "Unhelpful with requests", "Language barrier", "Other"
  2. If there's a GAP between overall and a sub-rating: probe the outlier.
     Example: overall=4 but noise=2 → "You rated noise quite low — where was the noise coming from?"
  3. If ALL ratings are HIGH (4-5 stars): ask which aspect stood out most.
     Example: "What made your stay so great?" with options covering the high-rated areas.
  4. If NO sub-ratings are provided (only overall): ask a broad "what stood out" question.
- Use `multi_select` with 4-6 concrete, scenario-based options.
- The question should feel natural and reference the rating insight without being robotic.
  Good: "You rated cleanliness quite low — what was the issue?"
  Bad:  "Your cleanliness sub-rating was 2/5, please elaborate." ← too robotic"""

    # ── Slot 2: Conflict resolution OR Information gap (mutually exclusive) ──
    if has_conflicts:
        conflict_context = _build_conflict_context(conflicts)
        q2_section = f"""═══════════════════════════════════════════════════════
QUESTION 2 — CONFLICT RESOLUTION  (role: "conflict_resolution")
═══════════════════════════════════════════════════════
Past reviews for this hotel contain CONTRADICTORY or UNRESOLVED signals on the topic(s) below.
Ask the current guest about the SPECIFIC issue so we can resolve the conflict.

{conflict_context}

Rules for Q2:
- The question MUST reference the SPECIFIC scenario from the snippets above, NOT the generic topic category.
  Good: "A previous guest mentioned the upper pool was closed due to a broken pump. Was the pool available during your stay?"
  Good: "Some past guests reported mold in the bathroom. Did you notice any issues with bathroom cleanliness?"
  Good: "A guest mentioned no fridges in the rooms. Was there a fridge in your room?"
  Bad:  "How was the cleanliness during your stay?"  ← TOO VAGUE, do not do this
  Bad:  "How were the family amenities?"  ← TOO VAGUE, do not do this
- Extract the concrete detail from the negative_snippet (broken pump, mold, missing fridge, etc.) and ask about that specific thing.
- Frame neutrally — do NOT assume the issue still exists or is fixed.
- Use `quick_tap` with options specific to the scenario, e.g.: "Pool was open and working", "Pool was still closed/broken", "Didn't use the pool".
  Do NOT use generic options like "Working fine" / "Still an issue".
- Include the conflict topic as the `aspect`.
- DEDUPLICATION: If Q1 already covers the same aspect as the conflict, pick a different conflict from the list. If no non-overlapping conflict exists, fall back to an information_gap question instead.
- The `reason` field MUST mention the specific issue from past reviews (not just "contradictory signals")."""

        output_rules = f"""═══════════════════════════════════════════════════════
OUTPUT RULES
═══════════════════════════════════════════════════════
1. Return exactly 2 questions: Q1 with role "comment_deepdive", Q2 with role "conflict_resolution".
2. Use `quick_tap` for single-choice, `multi_select` when multiple answers apply, `free_text` only when options would be too limiting.
3. Provide 4-6 concrete, scenario-specific options for quick_tap/multi_select. Include "Other" only when it genuinely helps.
4. Each question must use one of these aspects: {", ".join(ALLOWED_ASPECTS)}.
5. Each question needs a short `reason` explaining why you asked it.
6. Use qids: "q_deepdive_01" for Q1, "q_conflict_01" for Q2.
7. Make questions concise, friendly, and actionable. Avoid generic phrases like "Anything else?" or "How was X during your stay?"
8. Set `private` to true only for sensitive issues (hygiene, safety, pests)."""
    else:
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

        q2_section = f"""═══════════════════════════════════════════════════════
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
- If the gap aspect has 0% coverage, this is the highest priority — the hotel has ZERO data on this topic."""

        output_rules = f"""═══════════════════════════════════════════════════════
OUTPUT RULES
═══════════════════════════════════════════════════════
1. Return exactly 2 questions: Q1 with role "comment_deepdive", Q2 with role "information_gap".
2. Use `quick_tap` for single-choice, `multi_select` when multiple answers apply, `free_text` only when options would be too limiting.
3. Provide 4-6 concrete options for quick_tap/multi_select. Include "Other" only when it genuinely helps.
4. Each question must use one of these aspects: {", ".join(ALLOWED_ASPECTS)}.
5. Each question needs a short `reason` explaining why you asked it.
6. Use qids: "q_deepdive_01" for Q1, "q_gap_01" for Q2.
7. Make questions concise, friendly, and actionable. Avoid generic phrases like "Anything else?"
8. Set `private` to true only for sensitive issues (hygiene, safety, pests)."""

    review_or_rating = f'"{review_text}"' if has_review_text else "(No review text — guest only submitted a rating.)"

    return f"""You are a hotel review follow-up agent.
Generate exactly 2 follow-up questions for the guest who just submitted a review.

{q1_section}

{q2_section}

{output_rules}

═══════════════════════════════════════════════════════
GUEST INPUT
═══════════════════════════════════════════════════════

Review text:
{review_or_rating}

{guest_rating_context}

Return JSON only."""


# ── Entry point ──────────────────────────────────────────────────────────

def decide_questions(
    review_text_or_ctx: Union[str, ReviewContext],
    property_id: str | None = None,
) -> AgentDecision:
    review_text = _extract_review_text(review_text_or_ctx)

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Add it to backend/.env or deployment env vars."
        )

    # Resolve property ID
    resolved_pid = (property_id or "").strip() or None
    if not resolved_pid and isinstance(review_text_or_ctx, ReviewContext):
        resolved_pid = (review_text_or_ctx.property_id or "").strip() or None

    # Detect which aspects the review already covers (via evidence_analysis patterns)
    review_mentioned = match_labels(review_text) if review_text.strip() else []

    # Check for unresolved conflicts on this property
    conflicts: list[dict] = []
    if resolved_pid:
        try:
            conflicts = get_active_conflicts(resolved_pid, top_n=1)
        except Exception:
            conflicts = []

    # Slot 2: conflict takes priority; only load gaps when no conflicts
    gap_aspects: list[dict] = []
    if not conflicts:
        gap_aspects = _get_gap_aspects(resolved_pid or "", review_mentioned)

    # Build context
    guest_rating_context = _build_guest_rating_context(review_text_or_ctx)

    # Build prompt and call OpenAI
    prompt = _build_prompt(review_text, gap_aspects, guest_rating_context, conflicts)

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
