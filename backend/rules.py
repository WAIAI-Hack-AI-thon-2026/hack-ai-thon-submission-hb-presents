"""
Rules engine: aspect detection + lightweight sentiment scoring.

This is the "fast path" that runs BEFORE any LLM call. It scans the review
text (in English or translated-to-English) with regex patterns derived from
the empirical aspect analysis (see /docgen/aspect_summary.csv).

Why regex first:
  1. Deterministic, testable, cheap. We can unit-test the hell out of it.
  2. Gives the LLM a shorter prompt later (just: "here are the aspects
     already covered, do not re-ask").
  3. Works offline for the demo.

The LLM can later replace / augment this (see agent.py for the hook point).
"""
from __future__ import annotations
import re
from typing import Iterable

from schema import Aspect, ReviewContext


# -------------------- Patterns --------------------
# Keep these intentionally simple and high-precision. False negatives (missing
# an aspect) are fine -- the agent just asks a follow-up. False positives
# (claiming we covered an aspect we didn't) are expensive -- we'd skip a
# needed question. So err on the side of specificity.

ASPECT_PATTERNS: dict[Aspect, list[str]] = {
    Aspect.BATHROOM:   [r"\bbathroom\b", r"\bshower\b", r"\btoilet\b", r"\btub\b", r"\bsink\b", r"\bdrain(age)?\b"],
    Aspect.BILLING:    [r"\bbill(ing|ed)?\b", r"\bdeposit\b", r"\bcharg(e|ed|es)\b", r"\brefund\b",
                        r"\bextra fee\b", r"\bcity tax\b", r"\bresort fee\b"],
    Aspect.SMELL:      [r"\bsmell(s|ed|ing|y)?\b", r"\bodou?r\b", r"\bstink\b", r"\bmust(y)?\b", r"\bmoldy?\b"],
    Aspect.AMENITIES:  [r"\bwi[- ]?fi\b", r"\bhair ?dryer\b", r"\bkettle\b", r"\bmini ?bar\b",
                        r"\btv\b", r"\bamenit(y|ies)\b"],
    Aspect.ELEVATOR:   [r"\belevator\b", r"\blift\b", r"\bstairs?\b"],
    Aspect.NOISE:      [r"\bnois(e|y)\b", r"\bloud\b", r"\bquiet\b", r"\bsound\b"],
    Aspect.AC_HEAT:    [r"\bair[- ]?conditioni(ng|ner)?\b", r"\bA\.?C\.?\b", r"\bheat(er|ing)?\b", r"\btemperature\b"],
    Aspect.PESTS:      [r"\bbed ?bugs?\b", r"\bcockroach(es)?\b", r"\broaches?\b", r"\bbugs?\b",
                        r"\bfleas?\b", r"\bmites?\b", r"\bants?\b"],
    Aspect.CHECKIN:    [r"\bcheck[- ]?in\b", r"\bcheck[- ]?out\b", r"\breception\b", r"\bfront desk\b"],
    Aspect.BED:        [r"\bbed\b", r"\bmattress\b", r"\bpillow(s)?\b", r"\bsheets?\b", r"\blinen(s)?\b"],
    Aspect.VALUE:      [r"\bvalue\b", r"\bprice\b", r"\bcost\b", r"\bexpensive\b", r"\boverpriced\b", r"\bcheap\b"],
    Aspect.LOCATION:   [r"\blocation\b", r"\blocated\b", r"\bneighbou?rhood\b", r"\bcentral\b", r"\bnear(by)?\b",
                        r"\bwalking distance\b"],
    Aspect.STAFF:      [r"\bstaff\b", r"\bemployees?\b", r"\bconcierge\b", r"\bhousekeeping\b",
                        r"\bmanager\b", r"\bwaiter\b", r"\breceptionist\b"],
    Aspect.CLEANLINESS:[r"\bclean(liness)?\b", r"\bdirty\b", r"\bspotless\b", r"\bdust(y)?\b", r"\bstain(s|ed)?\b"],
    Aspect.FAMILY:     [r"\bkids?\b", r"\bchild(ren)?\b", r"\bfamil(y|ies)\b", r"\bcrib\b", r"\btoddler\b"],
    Aspect.RENOVATION: [r"\brenovat(ed|ion|ing)\b", r"\bremodel(ed|ing|led)?\b", r"\bold\b", r"\bworn\b",
                        r"\bdated\b", r"\brefurbish(ed|ment)?\b"],
}

# Word-level sentiment cues. Kept small on purpose -- this is NOT a real
# sentiment model, it's a tripwire. A proper implementation would use a
# multilingual transformer; that's out of scope for the hackathon demo.
POSITIVE_CUES = {
    "great", "excellent", "perfect", "amazing", "loved", "love", "good",
    "wonderful", "clean", "comfortable", "quiet", "friendly", "kind",
    "helpful", "beautiful", "recommend", "nice", "fantastic", "spacious",
    "modern", "spotless", "smooth", "warm", "delicious",
}
NEGATIVE_CUES = {
    "bad", "terrible", "awful", "dirty", "smelly", "moldy", "broken",
    "noisy", "loud", "old", "worn", "rude", "slow", "uncomfortable",
    "cold", "hot", "stuffy", "small", "cramped", "overpriced", "unhelpful",
    "disappointed", "disgusting", "poor", "horrible", "stained", "stink",
    "not clean", "didn't work", "doesn't work",
}


# -------------------- Detection --------------------
def detect_aspects(text: str) -> set[Aspect]:
    """Return the set of aspects explicitly mentioned in `text`."""
    if not text:
        return set()
    low = text.lower()
    hits: set[Aspect] = set()
    for aspect, patterns in ASPECT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, low):
                hits.add(aspect)
                break
    return hits


def classify_sentiment(text: str) -> str:
    """
    Very rough signal: 'pos' | 'neg' | 'mixed' | 'neutral'.

    This is only used by the agent to decide things like "reward positive
    guests with a staff-shoutout question". It is NOT shown to the user.
    """
    if not text:
        return "neutral"
    low = text.lower()
    pos = sum(1 for w in POSITIVE_CUES if w in low)
    neg = sum(1 for w in NEGATIVE_CUES if w in low)
    if pos == 0 and neg == 0:
        return "neutral"
    if neg == 0:
        return "pos"
    if pos == 0:
        return "neg"
    return "mixed" if abs(pos - neg) <= 1 else ("pos" if pos > neg else "neg")


def enrich_context(ctx: ReviewContext) -> ReviewContext:
    """
    Populate `ctx.aspects_mentioned` from text if the caller hasn't done it.
    Safe to call multiple times (idempotent union).
    """
    text = ctx.review_text_en or ctx.review_text or ""
    detected = detect_aspects(text)
    ctx.aspects_mentioned = set(ctx.aspects_mentioned) | detected
    return ctx


# -------------------- Aspect × sentiment (for future use) --------------------
def aspect_sentiment_windows(text: str, window: int = 40) -> dict[Aspect, str]:
    """
    For each detected aspect, look at a character window around the match
    and decide if the mention is positive or negative. Used for the
    'aspect already covered positively -> don't re-ask' logic.
    """
    if not text:
        return {}
    low = text.lower()
    out: dict[Aspect, str] = {}
    for aspect, patterns in ASPECT_PATTERNS.items():
        for pat in patterns:
            for m in re.finditer(pat, low):
                lo = max(0, m.start() - window)
                hi = min(len(low), m.end() + window)
                snippet = low[lo:hi]
                pos = sum(1 for w in POSITIVE_CUES if w in snippet)
                neg = sum(1 for w in NEGATIVE_CUES if w in snippet)
                if neg > pos:
                    out[aspect] = "neg"
                elif pos > neg:
                    out[aspect] = "pos"
                else:
                    out.setdefault(aspect, "neutral")
                break
    return out
