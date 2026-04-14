"""
Demo: end-to-end agent run on three hand-picked reviews.

Run:
    cd backend
    python demo.py
"""
from __future__ import annotations
import json
from dataclasses import asdict

from schema import ReviewContext, Aspect
from agent import decide_questions


def _show(title: str, ctx: ReviewContext):
    print("=" * 72)
    print(title)
    print("-" * 72)
    print(f"Rating: {ctx.overall_rating}  |  Nights: {ctx.stay_nights}  |  Text: {ctx.review_text_en or ctx.review_text!r}")
    decision = decide_questions(ctx)
    print(f"\n>> {len(decision.questions)} question(s) chosen:")
    for q in decision.questions:
        print(f"  [{q.qid}] {q.text_en}")
        print(f"     type={q.response_type.value}  aspect={q.aspect.value}  priority={q.priority}")
        if q.options:
            print(f"     options: {q.options}")
        print(f"     why: {decision.rationale[q.qid]}")
    print()


# Scenario 1: angry low-rating guest with tiny review text.
# Expect: high-priority gap questions (bathroom, smell, billing) + private channel unlocked.
SCENARIO_1 = ReviewContext(
    review_id="r_0001",
    property_id="hotel_rome_01",
    overall_rating=2.0,
    review_text_en="Awful stay. Never again.",
    review_text="Awful stay. Never again.",
    sub_ratings={"roomcleanliness": None, "valueformoney": None, "roomamenitiesscore": None},
    stay_nights=2,
    stay_month=8,
    property_has_elevator=True,
    property_age_years=20,
    is_first_time_guest=True,
)

# Scenario 2: happy 5-star guest who wrote a lot about location but not staff.
# Expect: reserve last slot for staff "shout-out" question.
SCENARIO_2 = ReviewContext(
    review_id="r_0002",
    property_id="hotel_bangkok_07",
    overall_rating=5.0,
    review_text_en=(
        "Great location, 5 minutes walk from the main street. "
        "The room was clean and the bed was comfortable. "
        "Breakfast had good variety."
    ),
    review_text="...",
    aspects_mentioned={Aspect.LOCATION, Aspect.CLEANLINESS, Aspect.BED},
    sub_ratings={"convenienceoflocation": 5.0, "roomcleanliness": 5.0},
    stay_nights=3,
    stay_month=5,
    property_has_elevator=True,
    property_age_years=6,
)

# Scenario 3: mixed 3-star, family trip, summer month, older property.
# Expect: AC question (hot month), family-fit, renovation.
SCENARIO_3 = ReviewContext(
    review_id="r_0003",
    property_id="hotel_lisbon_03",
    overall_rating=3.5,
    review_text_en="Decent but dated. Room was small for the four of us.",
    review_text="Decent but dated. Room was small for the four of us.",
    sub_ratings={"roomcleanliness": 4.0},
    stay_nights=4,
    stay_month=7,
    party_size=4,
    has_crib_request=False,
    property_has_elevator=False,
    property_age_years=35,
    is_street_facing_room=True,
)


if __name__ == "__main__":
    _show("SCENARIO 1 — unhappy guest, short text", SCENARIO_1)
    _show("SCENARIO 2 — happy guest, rich text, mentions location/clean/bed", SCENARIO_2)
    _show("SCENARIO 3 — mixed, family, older property, summer", SCENARIO_3)
