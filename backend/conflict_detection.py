"""
Conflict Detection Engine

Scans review history per hotel to find contradictory or unresolved signals
on the same topic across time.  Outputs a per-hotel conflict index that the
agent consumes as Slot 3 ("conflict_resolution") context.

Lifecycle:
  1. detect_all_conflicts()  — batch offline, writes hotel_conflicts.json
  2. get_active_conflicts()  — called at request time by agent.py
  3. resolve_conflict()      — called when a guest answers Slot 3; marks resolved
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

try:
    from .evidence_analysis import EVIDENCE_LABELS
except ImportError:
    from evidence_analysis import EVIDENCE_LABELS

REFERENCE_DATE = date(2026, 4, 15)

# ── Sentiment cues (local window) ────────────────────────────────────────

POSITIVE_CUES = [
    "great", "excellent", "perfect", "amazing", "loved", "love", "good",
    "wonderful", "clean", "comfortable", "quiet", "friendly", "helpful",
    "beautiful", "recommend", "nice", "fantastic", "spacious", "modern",
    "spotless", "smooth", "warm", "delicious", "best", "improved", "fixed",
    "renovated", "updated", "new", "works", "working", "reopened", "open",
    "resolved", "better",
]

NEGATIVE_CUES = [
    "bad", "terrible", "awful", "dirty", "smelly", "moldy", "broken",
    "noisy", "loud", "old", "worn", "rude", "slow", "uncomfortable",
    "cold", "hot", "stuffy", "small", "cramped", "overpriced", "unhelpful",
    "disappointed", "disgusting", "poor", "horrible", "stained", "stink",
    "closed", "not working", "doesn't work", "didn't work", "out of order",
    "unavailable", "worst", "filthy", "gross", "under renovation",
    "chipping", "peeling", "leak", "clogged", "missing", "no ",
]

# ── Helpers ──────────────────────────────────────────────────────────────


def _parse_date(value: str) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%m/%d/%y").date()
    except ValueError:
        return None


def _snippet_sentiment(text: str, match_start: int, match_end: int,
                       window: int = 80) -> str:
    """Pos / neg / neutral within a character window around a regex match."""
    lo = max(0, match_start - window)
    hi = min(len(text), match_end + window)
    snippet = text[lo:hi].lower()

    pos = sum(1 for w in POSITIVE_CUES if w in snippet)
    neg = sum(1 for w in NEGATIVE_CUES if w in snippet)

    if neg > pos:
        return "neg"
    if pos > neg:
        return "pos"
    return "neutral"


def _detect_topic_mentions(text: str) -> list[dict]:
    """Return (label, sentiment, snippet) for each evidence label matched."""
    if not text:
        return []
    text_lower = text.lower()
    mentions: list[dict] = []
    for label, patterns in EVIDENCE_LABELS.items():
        for pattern in patterns:
            m = re.search(pattern, text_lower)
            if m:
                lo = max(0, m.start() - 50)
                hi = min(len(text), m.end() + 50)
                snippet = text[lo:hi].strip()
                sentiment = _snippet_sentiment(text, m.start(), m.end())
                mentions.append({
                    "label": label,
                    "sentiment": sentiment,
                    "snippet": snippet,
                })
                break  # one match per label
    return mentions


def _resolve_data_dir() -> Path:
    backend_dir = Path(__file__).resolve().parent
    candidates = [
        backend_dir.parent / "data",
        backend_dir / "data",
        Path.cwd() / "data",
    ]
    for c in candidates:
        if (c / "Reviews_PROC.csv").exists():
            return c
    return backend_dir.parent / "data"


# ── Core detection ───────────────────────────────────────────────────────

def _classify_conflict(
    negatives: list[dict],
    positives: list[dict],
) -> dict:
    """
    Given sorted neg/pos timelines for one (hotel, topic), return the
    highest-priority conflict record (or None if resolved).

    Status values:
      conflicting  — recent neg after a pos, or mixed recent signals
      persistent   — consistent neg, never contradicted by pos
      stale_issue  — old neg, no recent mention at all
      resolved     — neg followed by a more recent pos confirmation
    """
    latest_neg = negatives[-1]
    latest_pos = positives[-1] if positives else None

    neg_age = (REFERENCE_DATE - latest_neg["date"]).days
    pos_age = (REFERENCE_DATE - latest_pos["date"]).days if latest_pos else None

    if latest_pos and latest_pos["date"] > latest_neg["date"]:
        # Positive came AFTER the negative → resolved (or nearly)
        status = "resolved"
    elif latest_pos and latest_pos["date"] <= latest_neg["date"]:
        # Negative came AFTER positive → situation degraded
        status = "conflicting" if neg_age <= 365 else "stale_issue"
    else:
        # Only negatives exist
        status = "persistent" if neg_age <= 365 else "stale_issue"

    return {
        "status": status,
        "negative_snippet": latest_neg["snippet"],
        "negative_date": latest_neg["date"].isoformat(),
        "negative_age_days": neg_age,
        "positive_snippet": latest_pos["snippet"] if latest_pos else None,
        "positive_date": latest_pos["date"].isoformat() if latest_pos else None,
        "positive_age_days": pos_age,
        "total_negative_mentions": len(negatives),
        "total_positive_mentions": len(positives),
    }


def detect_all_conflicts(
    reviews_path: str | None = None,
    output_path: str | None = None,
) -> dict:
    """
    Batch job: scan all reviews, detect per-hotel topic conflicts,
    write hotel_conflicts.json.  Returns the full conflict dict.
    """
    data_dir = _resolve_data_dir()
    if reviews_path is None:
        reviews_path = str(data_dir / "Reviews_PROC.csv")
    if output_path is None:
        output_path = str(data_dir / "hotel_conflicts.json")

    # ── Load reviews grouped by hotel ────────────────────────────────
    reviews_by_hotel: dict[str, list[dict]] = defaultdict(list)
    with open(reviews_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = (row.get("eg_property_id") or "").strip()
            text = (row.get("review_text") or "").strip()
            review_date = _parse_date(row.get("acquisition_date", ""))
            if not pid or not text or not review_date:
                continue
            reviews_by_hotel[pid].append({"date": review_date, "text": text})

    for pid in reviews_by_hotel:
        reviews_by_hotel[pid].sort(key=lambda r: r["date"])

    # ── Build topic timelines & detect conflicts ─────────────────────
    all_conflicts: dict = {}

    for pid, reviews in reviews_by_hotel.items():
        topic_timeline: dict[str, list[dict]] = defaultdict(list)

        for review in reviews:
            for mention in _detect_topic_mentions(review["text"]):
                topic_timeline[mention["label"]].append({
                    "date": review["date"],
                    "sentiment": mention["sentiment"],
                    "snippet": mention["snippet"],
                })

        hotel_conflicts: list[dict] = []
        hotel_resolved: list[dict] = []

        for label, timeline in topic_timeline.items():
            timeline.sort(key=lambda x: x["date"])
            negatives = [t for t in timeline if t["sentiment"] == "neg"]
            if not negatives:
                continue  # no negative signal → nothing to conflict on
            positives = [t for t in timeline if t["sentiment"] == "pos"]

            record = _classify_conflict(negatives, positives)
            record["topic"] = label

            if record["status"] == "resolved":
                hotel_resolved.append(record)
            else:
                hotel_conflicts.append(record)

        if hotel_conflicts:
            priority = {"conflicting": 0, "persistent": 1, "stale_issue": 2}
            hotel_conflicts.sort(key=lambda c: priority.get(c["status"], 99))
            all_conflicts[pid] = {
                "conflicts": hotel_conflicts,
                "resolved": hotel_resolved,
            }

    # ── Write output ─────────────────────────────────────────────────
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_conflicts, f, indent=2, ensure_ascii=False)

    print(f"Conflict detection complete: {len(all_conflicts)} hotels with unresolved conflicts")
    for pid, data in all_conflicts.items():
        statuses = [c["status"] for c in data["conflicts"]]
        print(f"  {pid[:16]}... → {len(data['conflicts'])} unresolved, "
              f"{len(data['resolved'])} resolved  ({', '.join(statuses)})")

    return all_conflicts


# ── Runtime API (used by agent.py) ───────────────────────────────────────

_conflicts_cache: dict | None = None


def _load_conflicts() -> dict:
    global _conflicts_cache
    if _conflicts_cache is not None:
        return _conflicts_cache
    path = _resolve_data_dir() / "hotel_conflicts.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            _conflicts_cache = json.load(f)
    except (OSError, json.JSONDecodeError):
        _conflicts_cache = {}
    return _conflicts_cache


def get_active_conflicts(property_id: str, top_n: int = 1) -> list[dict]:
    """
    Return the top_n highest-priority unresolved conflicts for a property.
    Called by agent.py to decide whether to add Slot 3.
    """
    data = _load_conflicts()
    hotel = data.get(property_id, {})
    conflicts = hotel.get("conflicts", [])
    # Filter out any that have been manually resolved via resolve_conflict()
    active = [c for c in conflicts if c.get("status") != "resolved"]
    return active[:top_n]


def resolve_conflict(property_id: str, topic: str) -> bool:
    """
    Mark a conflict as resolved after a guest confirms the issue is fixed.
    Updates the JSON file in place.

    Returns True if the conflict was found and resolved.
    """
    global _conflicts_cache
    data = _load_conflicts()
    hotel = data.get(property_id)
    if not hotel:
        return False

    target = None
    remaining = []
    for c in hotel.get("conflicts", []):
        if c["topic"] == topic:
            target = c
        else:
            remaining.append(c)

    if not target:
        return False

    # Move to resolved list
    target["status"] = "resolved"
    target["resolved_date"] = REFERENCE_DATE.isoformat()
    hotel["conflicts"] = remaining
    hotel.setdefault("resolved", []).append(target)

    # Persist
    path = _resolve_data_dir() / "hotel_conflicts.json"
    with open(str(path), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    _conflicts_cache = data
    return True


# ── CLI entry point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    detect_all_conflicts()
