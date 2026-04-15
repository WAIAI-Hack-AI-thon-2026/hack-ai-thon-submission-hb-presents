"""
FastAPI server — Follow-up Question Agent.

Run:
    cd backend
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from schema import ReviewContext, Aspect, AgentDecision
from agent import decide_questions


app = FastAPI(
    title="Ask What Matters — Agent API",
    description="Follow-up question agent for hotel reviews.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------- Pydantic request / response models --------------------

class ReviewInput(BaseModel):
    review_id: str = "r_demo"
    property_id: str = "hotel_demo"
    language: str = "en"
    overall_rating: Optional[float] = None
    sub_ratings: dict[str, Optional[float]] = {}
    review_text: str = ""
    review_text_en: str = ""
    aspects_mentioned: list[str] = []
    stay_month: Optional[int] = None
    stay_nights: int = 1
    checkin_hour: Optional[int] = None
    is_first_time_guest: bool = False
    party_size: int = 1
    has_crib_request: bool = False
    is_street_facing_room: bool = False
    property_has_elevator: Optional[bool] = None
    property_age_years: Optional[int] = None

    model_config = {"json_schema_extra": {"examples": [
        {
            "review_id": "r_0001",
            "property_id": "hotel_rome_01",
            "overall_rating": 2.0,
            "review_text": "Awful stay. Never again.",
            "review_text_en": "Awful stay. Never again.",
            "sub_ratings": {"roomcleanliness": None, "roomamenitiesscore": None},
            "stay_nights": 2,
            "stay_month": 8,
            "property_has_elevator": True,
            "property_age_years": 20,
        }
    ]}}


def _decision_to_dict(decision: AgentDecision) -> dict:
    return {
        "questions": [
            {
                "qid": q.qid,
                "aspect": q.aspect.value,
                "text_en": q.text_en,
                "response_type": q.response_type.value,
                "options": q.options,
                "priority": q.priority,
                "private": q.private,
            }
            for q in decision.questions
        ],
        "rationale": decision.rationale,
        "skipped": [{"qid": s[0], "reason": s[1]} for s in decision.skipped],
    }


# -------------------- Routes --------------------

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/decide")
def decide(body: ReviewInput):
    """
    Given a submitted review + booking context, return up to 3 follow-up questions.
    """
    valid_aspects = {a.value for a in Aspect}
    ctx = ReviewContext(
        review_id=body.review_id,
        property_id=body.property_id,
        language=body.language,
        overall_rating=body.overall_rating,
        sub_ratings=body.sub_ratings,
        review_text=body.review_text,
        review_text_en=body.review_text_en,
        aspects_mentioned={
            Aspect(a) for a in body.aspects_mentioned if a in valid_aspects
        },
        stay_month=body.stay_month,
        stay_nights=body.stay_nights,
        checkin_hour=body.checkin_hour,
        is_first_time_guest=body.is_first_time_guest,
        party_size=body.party_size,
        has_crib_request=body.has_crib_request,
        is_street_facing_room=body.is_street_facing_room,
        property_has_elevator=body.property_has_elevator,
        property_age_years=body.property_age_years,
    )
    try:
        decision = decide_questions(ctx)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _decision_to_dict(decision)
