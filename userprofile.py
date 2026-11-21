"""Turns the sidebar choices into one normalized profile that the planners use.

Design rule: every field has a visible effect. planner.explain() lists, field by field, what FitBuddy does with it.
Everything here is plain code (no model), so preferences work even when the language model is off.
"""
import hashlib
import json
import re

import safety

PROFILE_API = 1
GOALS = ["General fitness", "Strength", "Fat loss", "Endurance"]
LEVELS = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}
EQUIPMENT_CHOICES = ["Bodyweight only", "Dumbbells", "Resistance bands", "Gym access"]
CUISINE_CHOICES = ["Any", "Indian", "Mediterranean", "East Asian", "Latin American", "Middle Eastern", "Italian",
                   "Southeast Asian", "African / Caribbean", "American"]

_JOINTS = {
    "knee": r"\bknees?\b|patell", "back": r"\bback\b|spine|lumbar|\bdisc\b|sciatic", "shoulder": r"shoulder|rotator",
    "wrist": r"wrists?", "ankle": r"ankles?|achilles", "hip": r"\bhips?\b",
}
_DIETS = {
    "vegan": r"\bvegan\b", "vegetarian": r"vegetarian|veggie|\bno meat\b|meat[- ]free", "pescatarian": r"pescat?etarian",
    "jain": r"\bjain\b", "halal": r"\bhalal\b", "kosher": r"\bkosher\b",
}
_ALLERGENS = {
    "peanut": r"peanut|\bnuts?\b|groundnut", "tree_nut": r"tree nut|\bnuts?\b|almond|cashew|walnut|pistachio|hazelnut|pecan",
    "dairy": r"dairy|milk|lactose|cheese|paneer|yogh?urt|\bcurd", "gluten": r"gluten|wheat|celiac|coeliac",
    "egg": r"\beggs?\b", "fish": r"\bfish\b", "shellfish": r"shellfish|shrimp|prawn|crab|lobster",
    "soy": r"\bsoy|soya", "sesame": r"sesame",
}
_AVOID_LEAD = re.compile(r"(?:\bno\b|avoid|without|dislike|don'?t like|do not like|hate|allergic to|allergy to|"
                         r"can'?t eat|cannot eat|intolerant to)\s+([a-z][a-z /&'-]*)")
_NOT_LIST = {"i", "my", "love", "like", "prefer", "want", "eat", "enjoy", "also", "but"}
_STOPWORDS = {"the", "any", "all", "a", "an", "of", "and", "or", "foods", "food", "meat", "i", "my"}


def equipment_set(choices):
    """'Gym access' includes dumbbells and bands; bodyweight is always available."""
    s = {"bw"}
    for c in choices or []:
        if c == "Dumbbells":
            s.add("db")
        elif c == "Resistance bands":
            s.add("band")
        elif c == "Gym access":
            s |= {"db", "band", "gym"}
    return s


def parse_limits(text):
    """Return (joints, gentle_only, unmatched_text). Medical red flags switch to a gentle-only plan."""
    t = (text or "").lower().strip()
    joints = {j for j, pat in _JOINTS.items() if re.search(pat, t)}
    hit = safety.check(t) if t else None
    gentle = bool(hit and hit[0] in ("medical", "emergency"))
    unmatched = t if (t and not joints and not gentle) else ""
    return joints, gentle, unmatched


def parse_restrictions(text):
    """Return dict(diets, allergens, avoid, unmatched). Free-text 'no X' words become avoid-words."""
    t = (text or "").lower().strip()
    diets = {d for d, pat in _DIETS.items() if re.search(pat, t)}
    allergens = {a for a, pat in _ALLERGENS.items() if re.search(pat, t)}
    avoid, active = [], False
    for clause in re.split(r"[;.\n,]+", t):
        clause = clause.strip()
        m = _AVOID_LEAD.search(clause)
        if m:
            chunk, active = m.group(1), True
        elif active and clause and not (set(clause.split()) & _NOT_LIST):
            chunk = clause          # "no mushrooms, onions, cilantro" -> a list continuing after 'no'
        else:
            active = active and not clause
            continue
        for w in re.split(r"/|&|\band\b|\bor\b", chunk):
            w = w.strip(" -'")
            if not w or w in _STOPWORDS or len(w.split()) > 3:
                continue
            if any(re.search(p, w) for p in list(_DIETS.values()) + list(_ALLERGENS.values())):
                continue
            w = w[:-1] if w.endswith("s") and not w.endswith("ss") else w
            if w not in avoid:
                avoid.append(w)
    unmatched = t if (t and not diets and not allergens and not avoid) else ""
    return {"diets": diets, "allergens": allergens, "avoid": avoid, "unmatched": unmatched}


def normalize(goal="General fitness", level="Beginner", equipment=None, days=3, minutes=30, limits="", restrictions="",
              age="18-29", style="Friendly", cuisines=None):
    """Clean up the sidebar values and add everything derived from them."""
    equipment = [e for e in EQUIPMENT_CHOICES if e in set(equipment or [])] or ["Bodyweight only"]   # stable order
    try:
        days = int(min(7, max(1, int(days or 3))))
        minutes = int(min(90, max(10, int(minutes or 30))))
    except (TypeError, ValueError):
        days, minutes = 3, 30
    joints, gentle, unmatched_lim = parse_limits(limits)
    r = parse_restrictions(restrictions)
    cuisines = [c for c in CUISINE_CHOICES if c in set(cuisines or [])] or ["Any"]   # stable order
    p = {
        "goal": goal if goal in GOALS else "General fitness",
        "level": level if level in LEVELS else "Beginner",
        "equipment": equipment, "equip": sorted(equipment_set(equipment)),
        "days": days, "minutes": minutes,
        "limits": (limits or "").strip(), "joints": sorted(joints), "gentle_only": gentle, "limits_unmatched": unmatched_lim,
        "restrictions": (restrictions or "").strip(), "diets": sorted(r["diets"]), "allergens": sorted(r["allergens"]),
        "avoid": r["avoid"], "restrictions_unmatched": r["unmatched"],
        "age": age or "18-29", "style": style or "Friendly", "cuisines": cuisines,
    }
    p["level_n"] = LEVELS[p["level"]]
    p["teen"] = p["age"] == "Under 18"
    p["senior"] = p["age"] == "50+"
    p["sig"] = _digest({k: v for k, v in p.items() if k not in ("style",)})
    p["meal_sig"] = _digest({k: p[k] for k in ("diets", "allergens", "avoid", "cuisines", "age")})
    return p


def _digest(obj):
    return hashlib.md5(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:10]


def with_changes(p, **changes):
    """A copy of a normalized profile with some fields replaced (used for 'this request only' overrides)."""
    return normalize(
        goal=changes.get("goal", p["goal"]), level=changes.get("level", p["level"]),
        equipment=changes.get("equipment", p["equipment"]), days=changes.get("days", p["days"]),
        minutes=changes.get("minutes", p["minutes"]), limits=changes.get("limits", p["limits"]),
        restrictions=changes.get("restrictions", p["restrictions"]), age=changes.get("age", p["age"]),
        style=changes.get("style", p["style"]), cuisines=changes.get("cuisines", p["cuisines"]))


_LEVEL_WORDS = {"beginner": "Beginner", "intermediate": "Intermediate", "advanced": "Advanced"}


def overrides_from_text(text):
    """Pull request-specific choices out of a message like '4-day plan with dumbbells for 40 minutes'."""
    t = numwords_to_digits((text or "").lower())
    out = {}
    m = re.search(r"\b([1-7])\s*[- ]?\s*day|\b([1-7])\s*(?:days|x|times)\s*(?:a|per|/|each)\s*week", t)
    if m:
        out["days"] = int(m.group(1) or m.group(2))
    m = re.search(r"\b(\d{2,3})\s*[- ]?\s*min", t)
    if m and 10 <= int(m.group(1)) <= 90:
        out["minutes"] = int(m.group(1))
    for w, lvl in _LEVEL_WORDS.items():
        if re.search(rf"\b{w}\b", t):
            out["level"] = lvl
    eq = []
    if re.search(r"\bgym\b", t):
        eq.append("Gym access")
    if re.search(r"dumbbell", t):
        eq.append("Dumbbells")
    if re.search(r"\bbands?\b", t):
        eq.append("Resistance bands")
    if eq:
        out["equipment"] = eq
    elif re.search(r"no equipment|bodyweight|body weight|at home with nothing", t):
        out["equipment"] = ["Bodyweight only"]
    if re.search(r"\bstrength|muscle|stronger", t):
        out["goal"] = "Strength"
    elif re.search(r"\bendurance|stamina|cardio plan", t):
        out["goal"] = "Endurance"
    return out


_NUMS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
         "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty-five": 45, "forty": 40, "fifty": 50, "sixty": 60, "ninety": 90}


def numwords_to_digits(text):
    """'seven hours', 'fifteen minutes', 'a couple of glasses', 'half an hour' -> digits, so the rules can read them."""
    t = re.sub(r"\b(?:a )?couple of\b", "2", text or "", flags=re.I)
    t = re.sub(r"\bquarter of an hour\b", "15 minutes", t, flags=re.I)
    t = re.sub(r"\bhalf an hour\b", "30 minutes", t, flags=re.I)
    return re.sub(r"\b(" + "|".join(sorted(_NUMS, key=len, reverse=True)) + r")\b", lambda m: str(_NUMS[m.group(1).lower()]), t, flags=re.I)
