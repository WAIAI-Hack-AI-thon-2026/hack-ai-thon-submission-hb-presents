"""
FastAPI server — Follow-up Question Agent (OpenAI-powered).

Run:
    cd backend
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from .agent import decide_questions
except ImportError:
    from agent import decide_questions


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
    propertyId: int = 0
    city: str = ""
    country: str = ""
    rating: float | None = None
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

    try:
        decision = decide_questions(text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "questions": [
            {
                "id":      q.qid,
                "text":    q.text_en,
                "options": q.options,
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
