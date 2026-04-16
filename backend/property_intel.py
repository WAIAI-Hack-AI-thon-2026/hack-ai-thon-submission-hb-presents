from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path

REFERENCE_DATE = date(2026, 4, 15)

RATING_DIMENSIONS = [
    "overall",
    "roomcleanliness",
    "service",
    "roomcomfort",
    "hotelcondition",
    "roomquality",
    "convenienceoflocation",
    "neighborhoodsatisfaction",
    "valueformoney",
    "roomamenitiesscore",
    "communication",
    "ecofriendliness",
    "checkin",
    "onlinelisting",
    "location",
]

TOPIC_KEYWORDS = {
    "pool": ["pool", "piscina", "piscine", "schwimmbad"],
    "spa": ["spa", "wellness", "sauna", "hammam"],
    "breakfast": ["breakfast", "desayuno", "colazione", "fruhstuck", "frühstück", "petit dejeuner", "petit déjeuner"],
    "parking": ["parking", "park", "parcheggio", "estacionamiento", "parkplatz"],
    "fitness": ["fitness", "gym", "workout", "salle de sport", "palestra"],
    "wifi": ["wifi", "wi-fi", "internet"],
    "elevator": ["elevator", "lift", "ascensor", "ascenseur", "aufzug", "elevador"],
    "renovation": ["renovation", "renovated", "refurbished", "remodeled", "renovacion", "renovación", "ristruttur", "renovierung"],
}

CLAIM_TOPIC_KEYWORDS = {
    "pool": TOPIC_KEYWORDS["pool"],
    "spa": TOPIC_KEYWORDS["spa"],
    "fitness_equipment": TOPIC_KEYWORDS["fitness"],
    "breakfast": TOPIC_KEYWORDS["breakfast"],
    "bar": ["bar", "cocktail", "pub"],
    "restaurant": ["restaurant", "dining", "ristorante", "restaurante"],
    "kids_pool": ["kids pool", "children pool", "childrens pool", "children's pool", "baby pool"],
    "kitchen": ["kitchen", "kitchenette", "cocina", "cucina"],
    "laundry": ["laundry", "washer", "dryer", "lavanderia", "lavandería", "lavatrice"],
    "barbecue": ["barbecue", "bbq", "grill"],
}

_reviews_cache: dict[str, list[dict]] = {}
_descriptions_cache: dict[str, dict] = {}
_data_loaded = False


def _normalize_text(value: str) -> str:
    return (value or "").strip().lower()


def _parse_date(value: str) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%m/%d/%y").date()
    except ValueError:
        return None


def _parse_rating_json(value: str) -> dict[str, float]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            return {}
        clean: dict[str, float] = {}
        for key, score in parsed.items():
            try:
                clean[str(key)] = float(score)
            except (TypeError, ValueError):
                continue
        return clean
    except (json.JSONDecodeError, TypeError):
        return {}


def _parse_json_array(value: str) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            return []
        return [str(item).strip() for item in parsed if str(item).strip()]
    except (json.JSONDecodeError, TypeError):
        return []


def _resolve_data_dir() -> Path | None:
    backend_dir = Path(__file__).resolve().parent
    candidates = [
        backend_dir.parent / "data",
        backend_dir / "data",
        Path.cwd() / "data",
    ]
    for candidate in candidates:
        reviews_file = candidate / "Reviews_PROC.csv"
        descriptions_file = candidate / "Description_PROC.csv"
        if reviews_file.exists() and descriptions_file.exists():
            return candidate
    return None


def _load_data_if_needed() -> None:
    global _data_loaded
    if _data_loaded:
        return

    _reviews_cache.clear()
    _descriptions_cache.clear()

    data_dir = _resolve_data_dir()
    if not data_dir:
        _data_loaded = True
        return

    reviews_path = data_dir / "Reviews_PROC.csv"
    descriptions_path = data_dir / "Description_PROC.csv"

    try:
        with reviews_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                property_id = (row.get("eg_property_id") or "").strip()
                if not property_id:
                    continue
                _reviews_cache.setdefault(property_id, []).append(
                    {
                        "date": _parse_date(row.get("acquisition_date", "")),
                        "rating": _parse_rating_json(row.get("rating", "")),
                        "review_text": _normalize_text(row.get("review_text", "")),
                    }
                )
    except OSError:
        pass

    try:
        with descriptions_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                property_id = (row.get("eg_property_id") or "").strip()
                if not property_id:
                    continue
                _descriptions_cache[property_id] = row
    except OSError:
        pass

    _data_loaded = True


def _coverage_tier(coverage_ratio: float) -> str:
    if coverage_ratio < 0.10:
        return "critical"
    if coverage_ratio < 0.50:
        return "gap"
    return "saturated"


def _contains_any_keyword(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def get_property_intel(property_id: str) -> dict:
    _load_data_if_needed()

    pid = (property_id or "").strip()
    if not pid:
        return {}

    property_reviews = _reviews_cache.get(pid, [])
    property_description = _descriptions_cache.get(pid)
    if not property_reviews and not property_description:
        return {}

    total_reviews = len(property_reviews)

    # Part A — coverage gaps.
    coverage_rows: list[dict] = []
    if total_reviews > 0:
        for dimension in RATING_DIMENSIONS:
            if dimension == "overall":
                continue
            non_zero_count = 0
            for review in property_reviews:
                score = review.get("rating", {}).get(dimension, 0.0)
                try:
                    if float(score) > 0:
                        non_zero_count += 1
                except (TypeError, ValueError):
                    continue
            ratio = non_zero_count / total_reviews
            coverage_rows.append(
                {
                    "dimension": dimension,
                    "coverage_ratio": ratio,
                    "coverage_pct": round(ratio * 100, 1),
                    "non_zero_reviews": non_zero_count,
                    "total_reviews": total_reviews,
                    "tier": _coverage_tier(ratio),
                }
            )
        coverage_rows.sort(key=lambda item: item["coverage_ratio"])
    coverage_gaps = coverage_rows[:5]

    # Part B — staleness.
    recent_6m = 0
    six_to_twelve_m = 0
    over_12m = 0
    latest_topic_days: dict[str, int | None] = {}
    for topic in TOPIC_KEYWORDS:
        latest_topic_days[topic] = None

    for review in property_reviews:
        review_date = review.get("date")
        if review_date:
            age_days = (REFERENCE_DATE - review_date).days
            if age_days <= 183:
                recent_6m += 1
            elif age_days <= 365:
                six_to_twelve_m += 1
            else:
                over_12m += 1

            review_text = review.get("review_text", "")
            for topic, keywords in TOPIC_KEYWORDS.items():
                if _contains_any_keyword(review_text, keywords):
                    previous = latest_topic_days[topic]
                    if previous is None or age_days < previous:
                        latest_topic_days[topic] = age_days

    stale_topics = []
    for topic, days in latest_topic_days.items():
        if days is None:
            stale_topics.append({"topic": topic, "last_mentioned_days_ago": None, "status": "never"})
        elif days > 365:
            stale_topics.append({"topic": topic, "last_mentioned_days_ago": days, "status": "stale"})

    # Part C — unverified listing claims.
    claimed_amenities: list[str] = []
    unverified_claims: list[str] = []
    if property_description:
        popular_amenities = {
            amenity.strip().lower()
            for amenity in _parse_json_array(property_description.get("popular_amenities_list", ""))
        }
        for amenity in CLAIM_TOPIC_KEYWORDS:
            if amenity in popular_amenities:
                claimed_amenities.append(amenity)

        recent_review_texts = []
        for review in property_reviews:
            review_date = review.get("date")
            if not review_date:
                continue
            age_days = (REFERENCE_DATE - review_date).days
            if age_days <= 365:
                recent_review_texts.append(review.get("review_text", ""))

        for amenity in claimed_amenities:
            keywords = CLAIM_TOPIC_KEYWORDS.get(amenity, [])
            mentioned = any(_contains_any_keyword(text, keywords) for text in recent_review_texts)
            if not mentioned:
                unverified_claims.append(amenity)

    # Part D — metadata.
    guest_rating_avg = None
    if property_description:
        try:
            guest_rating_avg = float(property_description.get("guestrating_avg_expedia", ""))
        except (TypeError, ValueError):
            guest_rating_avg = None

    metadata = {
        "property_id": pid,
        "city": (property_description or {}).get("city") or None,
        "country": (property_description or {}).get("country") or None,
        "star_rating": (property_description or {}).get("star_rating") or None,
        "guest_rating_avg": guest_rating_avg,
        "total_reviews": total_reviews,
    }

    return {
        "coverage_gaps": coverage_gaps,
        "coverage_overview": coverage_rows,
        "staleness": {
            "reference_date": REFERENCE_DATE.isoformat(),
            "review_recency_buckets": {
                "last_6_months": recent_6m,
                "months_6_to_12": six_to_twelve_m,
                "over_12_months": over_12m,
            },
            "stale_topics": stale_topics,
        },
        "unverified_claims": {
            "claimed_amenities": claimed_amenities,
            "unverified": unverified_claims,
        },
        "metadata": metadata,
    }
