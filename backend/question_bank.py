"""
The Question Bank.

Each entry is a Question plus its trigger function. Triggers are pure functions
(ReviewContext -> bool) so they are easy to unit-test.

Priority comes from the empirical aspect analysis:
  gap_priority = neg_rate * sqrt(mentions)

Edit this file to add/remove questions or tune triggers.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

from schema import Aspect, Question, ReviewContext, ResponseType


# -------------------- Trigger helpers --------------------
def text_missing_or_short(ctx: ReviewContext, min_chars: int = 40) -> bool:
    return len((ctx.review_text_en or ctx.review_text).strip()) < min_chars


def aspect_not_in_text(ctx: ReviewContext, aspect: Aspect) -> bool:
    return aspect not in ctx.aspects_mentioned


def subrating_missing(ctx: ReviewContext, field: str) -> bool:
    return ctx.sub_ratings.get(field) is None


def hot_or_cold_month(ctx: ReviewContext) -> bool:
    return ctx.stay_month in {7, 8, 12, 1, 2}


# -------------------- Question registrations --------------------
@dataclass
class BankEntry:
    question: Question
    trigger: Callable[[ReviewContext], bool]


BANK: list[BankEntry] = [

    # --- Top-priority gaps (from aspect analysis) ---

    BankEntry(
        question=Question(
            qid="q_bathroom_01",
            aspect=Aspect.BATHROOM,
            text_en="How was the bathroom during your stay?",
            response_type=ResponseType.QUICK_TAP,
            options=[
                "Great",
                "Small but fine",
                "Cleanliness issue",
                "Drainage / plumbing issue",
                "Something broken",
            ],
            priority=8.84,
        ),
        trigger=lambda c: (
            subrating_missing(c, "roomcleanliness")
            and aspect_not_in_text(c, Aspect.BATHROOM)
        ),
    ),

    BankEntry(
        question=Question(
            qid="q_billing_01",
            aspect=Aspect.BILLING,
            text_en="Were there any surprises on your bill or deposit?",
            response_type=ResponseType.QUICK_TAP,
            options=[
                "No, everything clear",
                "Deposit still held",
                "Extra fee I didn't expect",
                "Other",
            ],
            priority=5.08,
        ),
        trigger=lambda c: aspect_not_in_text(c, Aspect.BILLING),
    ),

    BankEntry(
        question=Question(
            qid="q_smell_01",
            aspect=Aspect.SMELL,
            text_en="Did the room or common areas have any noticeable smell?",
            response_type=ResponseType.QUICK_TAP,
            options=[
                "No issue",
                "Smoke",
                "Musty / damp",
                "Sewage / drain",
                "Chemical (cleaning)",
                "Other",
            ],
            priority=4.93,
        ),
        trigger=lambda c: text_missing_or_short(c) and aspect_not_in_text(c, Aspect.SMELL),
    ),

    BankEntry(
        question=Question(
            qid="q_amenities_01",
            aspect=Aspect.AMENITIES,
            text_en="Did all the in-room amenities work as expected?",
            response_type=ResponseType.MULTI_SELECT,
            options=[
                "All worked",
                "Hairdryer",
                "AC / heating",
                "TV",
                "Kettle / minibar",
                "Wi-Fi device",
                "Other",
            ],
            priority=4.68,
        ),
        trigger=lambda c: subrating_missing(c, "roomamenitiesscore"),
    ),

    BankEntry(
        question=Question(
            qid="q_elevator_01",
            aspect=Aspect.ELEVATOR,
            text_en="How was moving luggage to your room?",
            response_type=ResponseType.QUICK_TAP,
            options=[
                "Easy, elevator all the way",
                "Some stairs but OK",
                "Had to carry luggage up stairs",
                "No help was offered",
            ],
            priority=4.26,
        ),
        trigger=lambda c: (
            c.property_has_elevator is True
            and (c.overall_rating or 5) < 4
            and aspect_not_in_text(c, Aspect.ELEVATOR)
        ),
    ),

    BankEntry(
        question=Question(
            qid="q_noise_01",
            aspect=Aspect.NOISE,
            text_en="How was the noise level?",
            response_type=ResponseType.QUICK_TAP,
            options=[
                "Perfectly quiet",
                "Some street noise",
                "Noise from other rooms",
                "Noise from hotel bar / events",
                "Construction",
            ],
            priority=3.04,
        ),
        trigger=lambda c: (
            (c.is_street_facing_room or c.stay_nights >= 2)
            and aspect_not_in_text(c, Aspect.NOISE)
        ),
    ),

    BankEntry(
        question=Question(
            qid="q_ac_01",
            aspect=Aspect.AC_HEAT,
            text_en="Did the room temperature control work for you?",
            response_type=ResponseType.QUICK_TAP,
            options=[
                "Worked great",
                "Took a while to cool / heat",
                "Broken / unresponsive",
                "Controls unclear",
            ],
            priority=2.73,
        ),
        trigger=lambda c: hot_or_cold_month(c) and aspect_not_in_text(c, Aspect.AC_HEAT),
    ),

    BankEntry(
        question=Question(
            qid="q_pests_01",
            aspect=Aspect.PESTS,
            text_en="Anything about cleanliness you'd flag to the hotel privately?",
            response_type=ResponseType.PRIVATE_TEXT,
            options=[],
            priority=2.49,
            private=True,
        ),
        # Always available but only surfaced if overall rating is low OR text has a hint.
        trigger=lambda c: (c.overall_rating or 5) <= 3,
    ),

    BankEntry(
        question=Question(
            qid="q_checkin_01",
            aspect=Aspect.CHECKIN,
            text_en="How was your check-in / check-out experience?",
            response_type=ResponseType.QUICK_TAP,
            options=[
                "Smooth",
                "Long wait",
                "Room not ready",
                "Staff not helpful",
                "Billing issue",
            ],
            priority=1.99,
        ),
        trigger=lambda c: (
            subrating_missing(c, "checkin")
            and (
                (c.checkin_hour is not None and (c.checkin_hour < 15 or c.checkin_hour > 17))
                or aspect_not_in_text(c, Aspect.CHECKIN)
            )
        ),
    ),

    BankEntry(
        question=Question(
            qid="q_bed_01",
            aspect=Aspect.BED,
            text_en="How was your bed?",
            response_type=ResponseType.QUICK_TAP,
            options=[
                "Great",
                "Too soft",
                "Too hard",
                "Pillow issue",
                "Bed creaked / small",
                "Linens not clean",
            ],
            priority=2.99,
        ),
        trigger=lambda c: (c.overall_rating or 5) <= 3 and aspect_not_in_text(c, Aspect.BED),
    ),

    BankEntry(
        question=Question(
            qid="q_value_01",
            aspect=Aspect.VALUE,
            text_en="Did the stay match the price you paid?",
            response_type=ResponseType.QUICK_TAP,
            options=[
                "Better than expected",
                "Fair for price",
                "Overpriced for what I got",
                "Unexpected fees hurt value",
            ],
            priority=1.92,
        ),
        trigger=lambda c: subrating_missing(c, "valueformoney") and c.stay_nights >= 3,
    ),

    BankEntry(
        question=Question(
            qid="q_location_01",
            aspect=Aspect.LOCATION,
            text_en="Was getting to the hotel as easy as you expected?",
            response_type=ResponseType.QUICK_TAP,
            options=[
                "Easier than expected",
                "As expected",
                "Hard to find",
                "Bad neighborhood at night",
            ],
            priority=1.80,
        ),
        trigger=lambda c: c.is_first_time_guest and subrating_missing(c, "convenienceoflocation"),
    ),

    BankEntry(
        question=Question(
            qid="q_staff_01",
            aspect=Aspect.STAFF,
            text_en="Was there a staff member who made your stay better?",
            response_type=ResponseType.FREE_TEXT,
            options=[],
            priority=2.05,
        ),
        # Reward positive guests: only fires when rating is 4+ AND staff was praised.
        trigger=lambda c: (c.overall_rating or 0) >= 4,
    ),

    BankEntry(
        question=Question(
            qid="q_family_01",
            aspect=Aspect.FAMILY,
            text_en="How well did the hotel work for your family?",
            response_type=ResponseType.QUICK_TAP,
            options=[
                "Perfectly",
                "Room too small",
                "No crib / extra bed",
                "Kid amenities missing",
            ],
            priority=1.40,
        ),
        trigger=lambda c: c.party_size > 2 or c.has_crib_request,
    ),

    BankEntry(
        question=Question(
            qid="q_renovation_01",
            aspect=Aspect.RENOVATION,
            text_en="Did any part of the room look worn or in need of repair?",
            response_type=ResponseType.QUICK_TAP,
            options=[
                "No",
                "Furniture dated but fine",
                "Carpet / walls worn",
                "Fixtures broken",
            ],
            priority=3.34,
        ),
        trigger=lambda c: (c.property_age_years or 0) >= 15
                          and aspect_not_in_text(c, Aspect.RENOVATION),
    ),

    BankEntry(
        question=Question(
            qid="q_catchall_01",
            aspect=Aspect.CATCH_ALL,
            text_en="Anything else we can help the property improve?",
            response_type=ResponseType.VOICE,  # stretch: voice-first, falls back to text
            options=[],
            priority=0.5,
        ),
        # Always eligible, but the agent will typically not choose it unless
        # there are already 2 other questions queued and the slot is free.
        trigger=lambda c: True,
    ),
]


def eligible_questions(ctx: ReviewContext) -> list[Question]:
    """Return all questions whose trigger fires for this review context."""
    return [e.question for e in BANK if e.trigger(ctx)]
