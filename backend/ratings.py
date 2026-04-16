from __future__ import annotations

import json

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


def _coerce_rating_value(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if numeric > 0 else None


def normalize_sub_ratings(raw_ratings: dict[object, object]) -> dict[str, float | None]:
    normalized: dict[str, float | None] = {}
    for dimension in RATING_DIMENSIONS:
        normalized[dimension] = None

    for key, value in raw_ratings.items():
        normalized[str(key)] = _coerce_rating_value(value)

    return normalized


def parse_rating_payload(payload: float | str | dict | None) -> tuple[float | None, dict[str, float | None]]:
    overall_rating: float | None = None
    parsed_map: dict[object, object] = {}

    if isinstance(payload, (int, float)):
        overall_rating = float(payload) if float(payload) > 0 else None
        parsed_map["overall"] = overall_rating
        return overall_rating, normalize_sub_ratings(parsed_map)

    if isinstance(payload, str):
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return None, normalize_sub_ratings({})
        if isinstance(decoded, dict):
            parsed_map = decoded
    elif isinstance(payload, dict):
        parsed_map = payload

    normalized = normalize_sub_ratings(parsed_map)
    overall_rating = normalized.get("overall")
    return overall_rating, normalized
