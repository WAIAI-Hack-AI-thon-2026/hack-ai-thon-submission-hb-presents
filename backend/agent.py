"""
The Follow-up Question Agent.

Entry point: `decide_questions(ctx: ReviewContext) -> AgentDecision`.

Pipeline (see design doc for the decision tree):
    1. Enrich context  (rules.enrich_context)
    2. Collect eligible questions (question_bank.eligible_questions)
    3. Deduplicate by aspect  (one question per aspect max)
    4. Rank by priority, adjusted by review signals (rating, language, etc.)
    5. Cap at MAX_QUESTIONS, reserving one "positive" slot if rating >= 4
    6. Build rationale + skipped list for auditability
    7. (Future) Pass to LLM for wording polish / localization

The agent is intentionally deterministic right now. The LLM is a POLISH step,
not a DECISION step. This keeps the behavior testable and removes a class of
prompt-injection / hallucination bugs.
"""
from __future__ import annotations
from typing import Optional

from schema import AgentDecision, Aspect, Question, ReviewContext, ResponseType
from question_bank import BANK, BankEntry
from rules import enrich_context, classify_sentiment


# -------------------- Configuration --------------------
MAX_QUESTIONS = 3                 # UI slot cap -- mobile users won't tolerate more
POSITIVE_RATING_THRESHOLD = 4.0   # >= this gets a "what went well" slot
LOW_RATING_THRESHOLD = 3.0        # <= this unlocks the private-channel question

POSITIVE_ASPECTS = {Aspect.STAFF}  # aspects we bias toward for positive guests


# -------------------- Core --------------------
def decide_questions(ctx: ReviewContext) -> AgentDecision:
    """Return at most MAX_QUESTIONS follow-up questions for this review."""
    ctx = enrich_context(ctx)

    eligible: list[BankEntry] = [e for e in BANK if e.trigger(ctx)]
    skipped: list[tuple[str, str]] = [
        (e.question.qid, "trigger did not fire") for e in BANK if not e.trigger(ctx)
    ]

    # Deduplicate: keep highest-priority question per aspect
    by_aspect: dict[Aspect, BankEntry] = {}
    for entry in eligible:
        current = by_aspect.get(entry.question.aspect)
        if current is None or entry.question.priority > current.question.priority:
            if current is not None:
                skipped.append((current.question.qid, f"outranked by {entry.question.qid} for aspect {entry.question.aspect.value}"))
            by_aspect[entry.question.aspect] = entry
        else:
            skipped.append((entry.question.qid, f"outranked by {current.question.qid} for aspect {entry.question.aspect.value}"))
    eligible = list(by_aspect.values())

    # Rank
    eligible.sort(key=lambda e: _score(e, ctx), reverse=True)

    # Select with "positive-slot" reservation
    chosen: list[BankEntry] = []
    positive_slot_used = False
    rating = ctx.overall_rating or 0

    for entry in eligible:
        if len(chosen) >= MAX_QUESTIONS:
            skipped.append((entry.question.qid, f"slot full ({MAX_QUESTIONS})"))
            continue

        # If guest is happy, keep a slot open for a positive question
        slots_left = MAX_QUESTIONS - len(chosen)
        is_positive = entry.question.aspect in POSITIVE_ASPECTS
        if (
            rating >= POSITIVE_RATING_THRESHOLD
            and not positive_slot_used
            and slots_left == 1
            and not is_positive
        ):
            skipped.append((entry.question.qid, "reserving last slot for positive-guest question"))
            continue

        chosen.append(entry)
        if is_positive:
            positive_slot_used = True

    rationale = {e.question.qid: _rationale(e, ctx) for e in chosen}

    return AgentDecision(
        questions=[e.question for e in chosen],
        rationale=rationale,
        skipped=skipped,
    )


# -------------------- Scoring --------------------
def _score(entry: BankEntry, ctx: ReviewContext) -> float:
    """
    Priority boosted / discounted by live signals.

    Multipliers are hand-tuned defaults; in production these become config.
    """
    p = entry.question.priority
    text = (ctx.review_text_en or ctx.review_text or "").strip()

    # Boost if the guest wrote almost nothing -- follow-ups are more valuable.
    if len(text) < 40:
        p *= 1.2

    # Boost low-rating reviews so we dig in.
    if ctx.overall_rating is not None and ctx.overall_rating <= LOW_RATING_THRESHOLD:
        p *= 1.3

    # Strongly demote the catch-all so it only surfaces when nothing else fits.
    if entry.question.aspect == Aspect.CATCH_ALL:
        p *= 0.1

    # Private questions only unlock for low ratings
    if entry.question.private and (ctx.overall_rating or 5) > LOW_RATING_THRESHOLD:
        p *= 0.0

    return p


def _rationale(entry: BankEntry, ctx: ReviewContext) -> str:
    """Human-readable reason -- shown in logs / admin tools, NOT to the guest."""
    q = entry.question
    pieces = [f"aspect={q.aspect.value}", f"priority={q.priority}"]
    if q.aspect not in ctx.aspects_mentioned:
        pieces.append("aspect not covered in text")
    if ctx.overall_rating is not None:
        pieces.append(f"rating={ctx.overall_rating}")
    sent = classify_sentiment(ctx.review_text_en or ctx.review_text)
    pieces.append(f"sentiment={sent}")
    return "; ".join(pieces)


# -------------------- Optional LLM polish hook --------------------
def polish_with_llm(decision: AgentDecision, ctx: ReviewContext, llm_client=None) -> AgentDecision:
    """
    Stretch goal: run the chosen questions through an LLM for:
      - translation to the guest's language
      - gentler / property-specific wording
      - removing questions the LLM judges redundant given the full review

    Keep this separate from decide_questions() so the tests stay deterministic.
    """
    if llm_client is None:
        return decision  # no-op in the default path

    # Pseudocode for the team:
    # prompt = build_polish_prompt(decision.questions, ctx)
    # response = llm_client.complete(prompt, response_format="json")
    # return AgentDecision(
    #     questions=response["questions"],
    #     rationale={**decision.rationale, **{q["qid"]: "llm-polished" for q in response["questions"]}},
    #     skipped=decision.skipped + response.get("dropped", []),
    # )
    return decision
