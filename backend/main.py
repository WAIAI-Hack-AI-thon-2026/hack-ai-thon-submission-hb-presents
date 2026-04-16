"""
FastAPI server — Follow-up Question Agent (OpenAI-powered).

Run:
    cd backend
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import json

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from .agent import decide_questions
    from .schema import ReviewContext
except ImportError:
    from agent import decide_questions
    from schema import ReviewContext


app = FastAPI(
    title="Ask What Matters — Agent API",
    description="OpenAI-powered follow-up question agent for hotel reviews.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReviewInput(BaseModel):
    review_text: str = ""


class AnalyzeInput(BaseModel):
    """Frontend payload from the Ask What Matters UI."""
    propertyId: str = ""
    city: str = ""
    country: str = ""
    rating: float | str | dict | None = None
    reviewText: str = ""


class QuestionOut(BaseModel):
    qid: str
    aspect: str
    text_en: str
    response_type: str
    options: list[str]
    priority: float
    private: bool


class DecisionOut(BaseModel):
    questions: list[QuestionOut]
    rationale: dict[str, str]
    skipped: list[dict[str, str]]


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


@app.post("/api/analyze")
def analyze(body: AnalyzeInput):
    """
    Called by the React frontend.
    Accepts { propertyId, city, country, rating, reviewText }
    Returns  { questions: [{ id, text, options }] }
    """
    text = body.reviewText.strip()
    if not text:
        raise HTTPException(status_code=400, detail="reviewText cannot be empty")

    overall_rating: float | None = None
    sub_ratings: dict[str, float] = {}
    if isinstance(body.rating, (int, float)):
        overall_rating = float(body.rating)
    elif isinstance(body.rating, str):
        try:
            parsed_rating = json.loads(body.rating)
            if isinstance(parsed_rating, dict):
                for key, value in parsed_rating.items():
                    try:
                        sub_ratings[str(key)] = float(value)
                    except (TypeError, ValueError):
                        continue
                if "overall" in sub_ratings and sub_ratings["overall"] > 0:
                    overall_rating = sub_ratings["overall"]
        except json.JSONDecodeError:
            overall_rating = None
    elif isinstance(body.rating, dict):
        for key, value in body.rating.items():
            try:
                sub_ratings[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
        if "overall" in sub_ratings and sub_ratings["overall"] > 0:
            overall_rating = sub_ratings["overall"]

    review_ctx = ReviewContext(
        review_id=f"r_{body.propertyId or 'unknown'}",
        property_id=body.propertyId or "unknown",
        overall_rating=overall_rating,
        review_text=text,
        review_text_en=text,
        sub_ratings=sub_ratings,
        stay_nights=2,
    )

    try:
        decision = decide_questions(review_ctx, property_id=body.propertyId or None)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "questions": [
            {
                "id":      q.qid,
                "text":    q.text_en,
                "options": q.options,
                "reasoning": decision.rationale.get(q.qid, ""),
            }
            for q in decision.questions
        ]
    }


@app.post("/api/decide")
def decide(body: ReviewInput):
    """
    Given a review text, use OpenAI to decide which follow-up questions to ask.
    """
    if not body.review_text.strip():
        raise HTTPException(status_code=400, detail="review_text cannot be empty")

    try:
        decision = decide_questions(body.review_text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

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
