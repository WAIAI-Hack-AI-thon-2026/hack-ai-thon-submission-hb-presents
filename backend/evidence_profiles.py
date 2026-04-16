from __future__ import annotations

import json
from pathlib import Path

try:
    from .evidence_analysis import EVIDENCE_LABELS
except ImportError:
    from evidence_analysis import EVIDENCE_LABELS


FALLBACK_QID_TO_LABEL = {
    "q_bathroom": "bathroom_quality",
    "q_billing": "value_price",
}


def _resolve_data_dir() -> Path:
    backend_dir = Path(__file__).resolve().parent
    candidates = [
        backend_dir.parent / "data",
        backend_dir / "data",
        Path.cwd() / "data",
    ]
    for candidate in candidates:
        if (candidate / "hotel_evidence_profiles.json").exists():
            return candidate
    return backend_dir.parent / "data"


def _profiles_path() -> Path:
    return _resolve_data_dir() / "hotel_evidence_profiles.json"


def _has_answer(value: object) -> bool:
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        selected = value.get("selected")
        other_text = str(value.get("other_text") or "").strip()
        if isinstance(selected, list):
            return len(selected) > 0 or bool(other_text)
        return bool(selected) or bool(other_text)
    return bool(str(value or "").strip())


def _normalize_label(aspect: object, qid: str = "") -> str | None:
    label = str(aspect or "").strip()
    if not label:
        label = FALLBACK_QID_TO_LABEL.get(qid, "")
    return label if label in EVIDENCE_LABELS else None


def _default_profile() -> dict:
    return {
        "location": "",
        "star_rating": "",
        "overall_rating_avg": None,
        "overall_rating_count": 0,
        "total_reviews": 0,
        "reviews_with_text": 0,
        "frequently_mentioned": [],
        "never_mentioned": sorted(EVIDENCE_LABELS.keys()),
    }


def update_hotel_rating_profile(
    property_id: str,
    rating_payload: dict | None,
) -> dict:
    pid = (property_id or "").strip()
    if not pid:
        raise ValueError("property_id is required")

    overall = None
    if isinstance(rating_payload, dict):
        try:
            numeric = float(rating_payload.get("overall"))
            if numeric > 0:
                overall = numeric
        except (TypeError, ValueError):
            overall = None

    if overall is None:
        return {
            "updated": False,
            "reason": "no overall rating provided",
            "propertyId": pid,
        }

    path = _profiles_path()
    with path.open("r", encoding="utf-8") as handle:
        profiles = json.load(handle)

    profile = profiles.setdefault(pid, _default_profile())
    current_count = int(profile.get("overall_rating_count", 0) or 0)

    current_avg_raw = profile.get("overall_rating_avg")
    try:
        current_avg = float(current_avg_raw) if current_avg_raw is not None else 0.0
    except (TypeError, ValueError):
        current_avg = 0.0

    next_count = current_count + 1
    next_avg = round(((current_avg * current_count) + overall) / next_count, 1)

    profile["overall_rating_count"] = next_count
    profile["overall_rating_avg"] = next_avg

    with path.open("w", encoding="utf-8") as handle:
        json.dump(profiles, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    return {
        "updated": True,
        "propertyId": pid,
        "overallRating": overall,
        "overall_rating_avg": next_avg,
        "overall_rating_count": next_count,
        "profile": profile,
    }


def update_hotel_evidence_profile(
    property_id: str,
    questions: list[dict] | None,
    answers: dict | None,
) -> dict:
    pid = (property_id or "").strip()
    if not pid:
        raise ValueError("property_id is required")

    question_map = {}
    for question in questions or []:
        qid = str(question.get("id") or question.get("qid") or "").strip()
        if qid:
            question_map[qid] = question

    answered_qids: list[str] = []
    answered_labels: set[str] = set()
    for qid, value in (answers or {}).items():
        if not _has_answer(value):
            continue
        answered_qids.append(str(qid))
        question = question_map.get(str(qid), {})
        label = _normalize_label(question.get("aspect"), str(qid))
        if label:
            answered_labels.add(label)

    if not answered_qids:
        return {
            "updated": False,
            "reason": "no answered follow-up questions",
            "propertyId": pid,
            "answeredQuestionCount": 0,
            "updatedLabels": [],
        }

    path = _profiles_path()
    with path.open("r", encoding="utf-8") as handle:
        profiles = json.load(handle)

    profile = profiles.setdefault(pid, _default_profile())
    counts = {label: 0 for label in EVIDENCE_LABELS}
    for row in profile.get("frequently_mentioned", []):
        label = str(row.get("label") or "").strip()
        if label in counts:
            try:
                counts[label] = int(row.get("count", 0))
            except (TypeError, ValueError):
                counts[label] = 0

    profile["total_reviews"] = int(profile.get("total_reviews", 0) or 0) + 1
    profile["reviews_with_text"] = int(profile.get("reviews_with_text", 0) or 0) + 1

    for label in answered_labels:
        counts[label] += 1

    denominator = max(int(profile["reviews_with_text"]), 1)
    frequently_mentioned = []
    for label, count in counts.items():
        if count <= 0:
            continue
        frequently_mentioned.append(
            {
                "label": label,
                "count": count,
                "percentage": round((count / denominator) * 100, 1),
            }
        )
    frequently_mentioned.sort(key=lambda item: (-item["count"], item["label"]))

    profile["frequently_mentioned"] = frequently_mentioned
    profile["never_mentioned"] = sorted([label for label, count in counts.items() if count <= 0])

    with path.open("w", encoding="utf-8") as handle:
        json.dump(profiles, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    return {
        "updated": True,
        "propertyId": pid,
        "answeredQuestionCount": len(answered_qids),
        "updatedLabels": sorted(answered_labels),
        "profile": profile,
    }
