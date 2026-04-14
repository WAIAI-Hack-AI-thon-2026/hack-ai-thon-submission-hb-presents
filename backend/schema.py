"""
Type definitions for the Follow-up Question Agent.

Shared dataclasses used across the agent, rules engine, and question bank.
Keep these DUMB and free of business logic.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ResponseType(str, Enum):
    QUICK_TAP = "quick_tap"          # single choice, 1 tap
    MULTI_SELECT = "multi_select"    # multiple checkboxes
    YES_NO = "yes_no"                # binary
    FREE_TEXT = "free_text"          # short text, optional
    PRIVATE_TEXT = "private_text"    # private channel (not shown publicly)
    VOICE = "voice"                  # stretch goal


class Aspect(str, Enum):
    BATHROOM = "bathroom"
    BILLING = "billing"
    SMELL = "smell"
    AMENITIES = "amenities"
    ELEVATOR = "elevator"
    NOISE = "noise"
    AC_HEAT = "ac_heat"
    PESTS = "pests"
    CHECKIN = "checkin"
    BED = "bed"
    VALUE = "value"
    LOCATION = "location"
    STAFF = "staff"
    CLEANLINESS = "cleanliness"
    FAMILY = "family"
    RENOVATION = "renovation"
    CATCH_ALL = "catch_all"


@dataclass
class Question:
    """A single follow-up question. Language-neutral; text is a key into i18n bundle."""
    qid: str                         # stable id (e.g. "q_bathroom_01")
    aspect: Aspect
    text_en: str                     # default English text; UI looks up localized variant
    response_type: ResponseType
    options: list[str] = field(default_factory=list)   # closed-form options (English)
    priority: float = 0.0            # gap_priority from aspect analysis
    private: bool = False            # goes to hotel only, not public review


@dataclass
class ReviewContext:
    """
    Everything the agent needs to decide what to ask.
    Populated by the backend from the booking + submitted review.
    """
    review_id: str
    property_id: str
    language: str = "en"             # BCP-47 code
    overall_rating: Optional[float] = None    # 1-5 stars if given
    sub_ratings: dict[str, Optional[float]] = field(default_factory=dict)
                                     # e.g. {"cleanliness": 5.0, "service": None, ...}
    review_text: str = ""            # raw text as submitted
    review_text_en: str = ""         # english translation (if applicable)
    aspects_mentioned: set[Aspect] = field(default_factory=set)
                                     # aspects already covered in the text
    stay_month: Optional[int] = None # 1-12, for seasonal triggers
    stay_nights: int = 1
    checkin_hour: Optional[int] = None     # 0-23
    is_first_time_guest: bool = False
    party_size: int = 1
    has_crib_request: bool = False
    is_street_facing_room: bool = False
    # Property-level signals pre-loaded from Description_PROC
    property_has_elevator: Optional[bool] = None
    property_age_years: Optional[int] = None


@dataclass
class AgentDecision:
    """Output of the agent — what to ask (or not)."""
    questions: list[Question]
    rationale: dict[str, str]        # qid -> human-readable reason (for auditability)
    skipped: list[tuple[str, str]]   # (qid, reason_for_skip) for transparency
