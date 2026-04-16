"""
Evidence Label Frequency Analysis

For each hotel, match reviews against evidence labels using keyword patterns,
then report:
  1. Per-hotel frequency of each label
  2. Labels never mentioned across all reviews
"""

import csv
import re
import json
from collections import defaultdict

# ── Evidence labels and their keyword patterns ──────────────────────────────
# Each label maps to a list of regex patterns (case-insensitive)
EVIDENCE_LABELS = {
    "accessibility": [
        r"no elevator", r"stairs only", r"hard with luggage", r"not wheelchair",
        r"wheelchair accessible", r"wheelchair", r"elevator", r"handicap",
        r"disabled", r"accessibility", r"accessible", r"mobility",
        r"stair", r"steps to climb", r"difficult.{0,20}(walk|move|access)",
        r"carry.{0,15}luggage", r"drag.{0,15}luggage",
    ],
    "transit_convenient": [
        r"near.{0,15}(train|metro|subway|bus|station|tram)",
        r"close to.{0,15}(train|metro|subway|bus|station|tram)",
        r"easy.{0,15}(airport|transit|transport)",
        r"walkable to.{0,15}(bus|train|metro|station)",
        r"train station", r"metro station", r"bus stop",
        r"airport.{0,15}(access|shuttle|close|near|easy)",
        r"public transport", r"transit", r"subway",
        r"shuttle", r"convenient.{0,15}transport",
    ],
    "noise": [
        r"\bquiet\b", r"\bpeaceful\b", r"\bnoisy\b", r"\bnoise\b",
        r"hear.{0,15}(footstep|elevator|street|traffic|neighbor|music|party)",
        r"street noise", r"elevator noise", r"thin wall",
        r"sound(proof|\s*proof)", r"\bloud\b", r"couldn.t sleep",
        r"too loud", r"heard everything", r"paper.{0,5}thin.{0,5}wall",
        r"silence", r"\bsilent\b", r"serene", r"tranquil",
    ],
    "parking": [
        r"\bparking\b", r"park.{0,5}(lot|garage|space|area|deck)",
        r"free parking", r"street parking", r"valet",
        r"no.{0,10}parking", r"expensive.{0,10}parking",
        r"ample parking", r"small.{0,10}lot",
        r"park.{0,5}(my|the|our).{0,5}car",
    ],
    "breakfast": [
        r"\bbreakfast\b", r"morning.{0,10}(meal|food|buffet)",
        r"continental breakfast", r"buffet breakfast",
        r"breakfast included", r"no breakfast",
        r"breakfast.{0,15}(good|great|excellent|amazing|terrible|bad|poor|disappoint)",
    ],
    "family_amenities": [
        r"\bpool\b", r"spacious room", r"kids.{0,10}(love|enjoy|happy)",
        r"sofa bed", r"baby crib", r"\bcrib\b", r"family.{0,10}(friend|room|suite)",
        r"child", r"children", r"kid.{0,3}friendly",
        r"play.{0,10}(area|ground|room)", r"waterslide", r"water slide",
        r"game room", r"arcade",
    ],
    "walkability": [
        r"walk.{0,15}(to|from).{0,15}(restaurant|shop|store|mall|market|bar|cafe)",
        r"walking distance", r"walkable", r"walk.{0,10}everywhere",
        r"(restaurant|shop|attraction|store|bar).{0,15}(nearby|close|near|next)",
        r"shopping nearby", r"attractions.{0,15}(walk|close|near)",
        r"steps? (from|to|away)", r"minute.{0,5}walk",
        r"on foot", r"stroll",
    ],
    "leisure_location": [
        r"beachfront", r"beach.{0,10}(view|access|close|near|front|walk)",
        r"near.{0,10}(waterfront|water|lake|river|harbor|harbour)",
        r"pool access", r"ocean view", r"sea view",
        r"waterfront", r"lakefront", r"lake view",
        r"resort.{0,10}(feel|style|like)", r"scenic",
        r"beautiful.{0,10}(view|scenery|landscape)",
    ],
    "safety_perception": [
        r"safe.{0,10}(area|neighborhood|neighbourhood|place|location|feel|walk)",
        r"felt safe", r"feel safe", r"very safe",
        r"sketchy", r"unsafe", r"not.{0,10}(safe|comfortable|secure)",
        r"dangerous", r"scary.{0,10}(area|neighborhood|neighbourhood|night)",
        r"comfortable.{0,15}walk.{0,10}(at|during).{0,5}night",
        r"safe\b",
    ],
    "cleanliness": [
        r"\bclean\b", r"\bdirty\b", r"\bfilthy\b", r"\bspotless\b",
        r"\bmold\b", r"\bmould\b", r"\bsmell\b", r"\bsmells\b",
        r"\bstain\b", r"\bstained\b", r"not.{0,10}clean",
        r"dust", r"hygien", r"sanit", r"gross", r"disgusting",
        r"immaculate", r"pristine", r"tidy", r"messy",
        r"hair.{0,10}(in|on).{0,10}(bed|shower|bath|tub|floor)",
        r"bug|cockroach|roach|bed.{0,3}bug|ant|insect",
    ],
    "staff_service": [
        r"friendly staff", r"helpful.{0,10}(staff|front desk|desk|reception|concierge)",
        r"rude.{0,10}(staff|service|front desk|reception|employee|worker)",
        r"unresponsive", r"went above and beyond", r"above and beyond",
        r"\bstaff\b", r"front desk", r"reception",
        r"concierge", r"service.{0,10}(great|excellent|amazing|terrible|bad|poor|good|awful|best|worst)",
        r"(great|excellent|amazing|terrible|bad|poor|good|awful|best|worst).{0,10}service",
        r"check.{0,3}in.{0,10}(smooth|easy|quick|slow|terrible|nightmare)",
        r"accommodating", r"attentive", r"polite", r"courteous",
        r"unprofessional", r"professional",
    ],
    "bed_comfort": [
        r"\bbed\b", r"\bbeds\b", r"\bmattress\b", r"\bpillow\b", r"\bpillows\b",
        r"\bcomfortable\b", r"\buncomfortable\b", r"\bcomfy\b",
        r"hard.{0,10}(bed|mattress)", r"soft.{0,10}(bed|mattress|pillow)",
        r"lumpy", r"firm.{0,10}(bed|mattress)", r"saggy",
        r"sleep.{0,10}(well|great|terrible|bad|good|poorly)",
        r"slept.{0,10}(well|great|terrible|bad|good|poorly)",
        r"couch", r"sofa.{0,5}bed", r"bedding", r"sheet", r"sheets",
        r"duvet", r"comforter", r"blanket",
    ],
    "bathroom_quality": [
        r"\bbathroom\b", r"\bshower\b", r"\btoilet\b", r"\bbathtub\b", r"\btub\b",
        r"water pressure", r"hot water", r"no hot water", r"cold water",
        r"shower head", r"showerhead", r"drain", r"clogged",
        r"towel", r"towels", r"bathroom.{0,15}(small|tiny|big|spacious|clean|dirty|nice|old|modern|updated)",
    ],
    "food_dining": [
        r"\brestaurant\b", r"\bdinner\b", r"\blunch\b", r"\bdining\b",
        r"\bfood\b", r"\bmeal\b", r"\bmeal\b", r"\bbuffet\b",
        r"room service", r"bar.{0,10}(food|menu|drink)",
        r"snack", r"coffee.{0,10}(shop|bar|good|bad|great)",
        r"on.?site.{0,10}(restaurant|dining|food)",
        r"vending", r"minibar", r"mini.bar",
    ],
    "check_in_out": [
        r"check.{0,3}in", r"check.{0,3}out",
        r"early check", r"late check",
        r"wait.{0,15}(check|line|lobby|front desk|queue)",
        r"long.{0,10}(wait|line|queue)",
        r"smooth.{0,10}(arrival|process)", r"seamless",
        r"key.{0,10}(card|didn|not work|problem)",
        r"express check",
    ],
    "value_price": [
        r"\bprice\b", r"\bpriced\b", r"\bexpensive\b", r"\bcheap\b",
        r"\boverpriced\b", r"\bover.priced\b",
        r"\bvalue\b", r"\bworth\b", r"\baffordable\b",
        r"\bcost\b", r"bang.{0,10}buck", r"money.{0,10}(worth|value|well spent)",
        r"good deal", r"great deal", r"rip.{0,3}off", r"budget",
        r"pay.{0,10}(too much|a lot|more)", r"reasonable.{0,10}price",
    ],
    "room_size": [
        r"small room", r"tiny room", r"\bspacious\b", r"huge room", r"big room",
        r"room.{0,10}(size|small|tiny|big|huge|large|spacious|cramped)",
        r"\bcozy\b", r"\bcramped\b", r"\btight\b.{0,10}(room|space)",
        r"enough (room|space)", r"not enough (room|space)",
        r"suite.{0,10}(large|big|spacious|roomy)",
        r"\broomy\b",
    ],
    "renovation_age": [
        r"\brenovate", r"\brenovation\b", r"\boutdated\b", r"\bold.{0,5}(hotel|room|building|property)",
        r"needs?.{0,10}updat", r"run.{0,3}down", r"\bworn\b",
        r"dated", r"remodel", r"refurbish", r"moderniz",
        r"new.{0,5}(renovation|remodel|refurbish|update)",
        r"showing.{0,10}(age|wear)", r"tired.{0,10}(look|room|hotel|decor)",
        r"needs?.{0,10}(work|repair|renovation|tlc|love)",
    ],
}

def load_reviews(path: str) -> list[dict]:
    """Load reviews CSV and return list of dicts with property_id and text."""
    reviews = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("review_text") or "").strip()
            reviews.append({
                "property_id": row["eg_property_id"],
                "text": text,
            })
    return reviews


def load_hotel_cities(path: str) -> dict[str, str]:
    """Load description CSV and return property_id -> city mapping."""
    mapping = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["eg_property_id"]
            city = row.get("city", "Unknown")
            country = row.get("country", "")
            mapping[pid] = f"{city}, {country}".strip(", ")
    return mapping


def match_labels(text: str) -> list[str]:
    """Return list of evidence labels that match the given review text."""
    if not text:
        return []
    text_lower = text.lower()
    matched = []
    for label, patterns in EVIDENCE_LABELS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                matched.append(label)
                break  # one match per label is enough
    return matched


def analyze(reviews_path: str, descriptions_path: str):
    reviews = load_reviews(reviews_path)
    hotel_cities = load_hotel_cities(descriptions_path)

    all_labels = list(EVIDENCE_LABELS.keys())
    hotel_ids = sorted(set(r["property_id"] for r in reviews))

    # per-hotel label frequency
    freq = {pid: defaultdict(int) for pid in hotel_ids}
    # per-hotel total reviews (with text)
    total_reviews = defaultdict(int)
    total_all = defaultdict(int)

    for r in reviews:
        pid = r["property_id"]
        total_all[pid] += 1
        if not r["text"]:
            continue
        total_reviews[pid] += 1
        labels = match_labels(r["text"])
        for lbl in labels:
            freq[pid][lbl] += 1

    # ── Print results ───────────────────────────────────────────────────
    print("=" * 100)
    print("EVIDENCE LABEL FREQUENCY ANALYSIS")
    print("=" * 100)
    print(f"\nTotal hotels: {len(hotel_ids)}")
    print(f"Total reviews: {len(reviews)}")
    print(f"Reviews with text: {sum(total_reviews.values())}")

    # Per-hotel table
    for pid in hotel_ids:
        city = hotel_cities.get(pid, "Unknown")
        print(f"\n{'─' * 80}")
        print(f"Hotel: {pid[:16]}...  |  Location: {city}")
        print(f"Total reviews: {total_all[pid]}  |  Reviews with text: {total_reviews[pid]}")
        print(f"{'─' * 80}")
        print(f"  {'Label':<25} {'Count':>6}  {'% of reviews w/ text':>20}")
        print(f"  {'─' * 55}")
        for lbl in all_labels:
            count = freq[pid].get(lbl, 0)
            pct = (count / total_reviews[pid] * 100) if total_reviews[pid] > 0 else 0
            marker = "" if count > 0 else "  (never mentioned)"
            print(f"  {lbl:<25} {count:>6}  {pct:>19.1f}%{marker}")

    # ── Global summary ──────────────────────────────────────────────────
    print(f"\n{'=' * 80}")
    print("GLOBAL SUMMARY: Labels across ALL hotels")
    print(f"{'=' * 80}")
    global_freq = defaultdict(int)
    for pid in hotel_ids:
        for lbl in all_labels:
            global_freq[lbl] += freq[pid].get(lbl, 0)

    print(f"\n  {'Label':<25} {'Total mentions':>15}")
    print(f"  {'─' * 45}")
    for lbl in sorted(all_labels, key=lambda x: -global_freq[x]):
        print(f"  {lbl:<25} {global_freq[lbl]:>15}")

    # ── Never mentioned per hotel ───────────────────────────────────────
    print(f"\n{'=' * 80}")
    print("LABELS NEVER MENTIONED (per hotel)")
    print(f"{'=' * 80}")
    for pid in hotel_ids:
        city = hotel_cities.get(pid, "Unknown")
        never = [lbl for lbl in all_labels if freq[pid].get(lbl, 0) == 0]
        if never:
            print(f"\n  {pid[:16]}... ({city}):")
            print(f"    {', '.join(never)}")

    # ── Globally never mentioned ────────────────────────────────────────
    global_never = [lbl for lbl in all_labels if global_freq[lbl] == 0]
    print(f"\n{'=' * 80}")
    if global_never:
        print(f"Labels NEVER mentioned in ANY review across all hotels:")
        for lbl in global_never:
            print(f"  - {lbl}")
    else:
        print("All labels were mentioned at least once across the dataset.")
    print(f"{'=' * 80}")

    # ── Export as JSON for downstream use ────────────────────────────────
    result = {
        "hotel_count": len(hotel_ids),
        "total_reviews": len(reviews),
        "hotels": {}
    }
    for pid in hotel_ids:
        city = hotel_cities.get(pid, "Unknown")
        result["hotels"][pid] = {
            "location": city,
            "total_reviews": total_all[pid],
            "reviews_with_text": total_reviews[pid],
            "label_frequency": {lbl: freq[pid].get(lbl, 0) for lbl in all_labels},
        }
    result["global_frequency"] = dict(global_freq)
    result["globally_never_mentioned"] = global_never

    out_path = "data/evidence_label_analysis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nJSON results saved to: {out_path}")


if __name__ == "__main__":
    analyze("data/Reviews_PROC.csv", "data/Description_PROC.csv")
