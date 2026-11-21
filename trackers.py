"""Deterministic tracking logic: water, sleep, habits, BMI, weekly summary, log parsing.

All maths and parsing happens here in plain Python (small language models are
unreliable at arithmetic). Data lives in the per-session state dict only.
"""
import json
import re
import tempfile
from datetime import date, datetime, timedelta

import userprofile

HABITS = ["Stretch", "10-minute walk", "Wind down by 10 pm"]
WATER_GOAL = 8  # glasses; a common rule of thumb, individual needs vary

_HABIT_PATTERNS = {
    "Stretch": r"\b(stretched|(did|finished|completed)\s+(my\s+|some\s+|a\s+)?stretch\w*)",
    "10-minute walk": r"\b(walked|went\s+(for\s+)?a\s+walk|took\s+a\s+walk|(did|finished|completed)\s+(my\s+|a\s+)?(10[- ]minute\s+)?walk)",
    "Wind down by 10 pm": r"\b(wound\s+down|(did|finished|completed)\s+(my\s+)?wind[- ]?down)",
}
_WORD_NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
MOODS = ["Great", "Good", "Okay", "Tired", "Stressed"]
MOOD_SCORE = {"Great": 5, "Good": 4, "Okay": 3, "Tired": 2, "Stressed": 1}
_MOOD_WORDS = {
    "great": "Great", "amazing": "Great", "awesome": "Great", "fantastic": "Great", "energized": "Great", "energised": "Great",
    "good": "Good", "happy": "Good", "well": "Good", "fine": "Good",
    "okay": "Okay", "ok": "Okay", "meh": "Okay", "alright": "Okay",
    "tired": "Tired", "exhausted": "Tired", "drained": "Tired", "low": "Tired", "sad": "Tired", "down": "Tired",
    "stressed": "Stressed", "anxious": "Stressed", "overwhelmed": "Stressed", "worried": "Stressed",
    "burned out": "Stressed", "burnt out": "Stressed",
}
_MOOD_RE = re.compile(
    r"\b(?:i feel|i'm feeling|i am feeling|i'm|i am|im|feeling|i felt|mood is|mood:)\s+"
    r"(?:so |really |pretty |very |a bit |kind of |super |quite |just )?("
    + "|".join(sorted((re.escape(w) for w in _MOOD_WORDS), key=len, reverse=True))
    + r")\b(?!\s+(?:with|to|if|for|about|doing|at|in|on|of|from)\b)")
_QUESTION_START = re.compile(r"^\s*(how|what|why|should|can|could|is|are|do|does|when|which|will|would)\b")


def today():
    return date.today().isoformat()


def new_state():
    return {"profile": {}, "water": {}, "sleep": {}, "habits": {}, "mood": {}, "plan": None, "events": [], "view": "7d", "seen": {},
            "pn": None, "workout_plan": None, "meal_plan": None, "today_ctx": None, "meal_seed": 0, "workouts_done": {}}


# ---------- parsing ----------
_KEYWORDS = ["slept", "drank", "glasses", "stretched", "walked", "tired", "stressed", "feeling", "exhausted", "anxious"]
_TYPOS = {"sleept": "slept", "slep": "slept", "sleapt": "slept", "slelpt": "slept", "slpt": "slept",
          "glases": "glasses", "glasess": "glasses", "glsses": "glasses", "hurs": "hours", "hous": "hours",
          "hourse": "hours", "drnk": "drank", "dranc": "drank", "tird": "tired", "stressd": "stressed"}


def _fix_word(w):
    """Repair common typos: a short list of known misspellings, plus swapped letters ('slpet' -> 'slept')."""
    if w in _TYPOS:
        return _TYPOS[w]
    if len(w) >= 5:
        for k in _KEYWORDS:
            if w != k and len(w) == len(k) and w[0] == k[0] and sorted(w) == sorted(k):
                return k
    return w


_MEAL_END = r"(?=\s*(?:[.,;!?\n]|$|\band\s+(?:slept|drank|stretched|walked|feeling|i\s)))"
_MEAL_PATTERNS = [
    re.compile(r"\b(?:ate|eaten)\s+(.+?)" + _MEAL_END),
    re.compile(r"\bhad\s+(.+?)\s+for\s+(?:breakfast|lunch|dinner|brunch|a snack|snack)\b"),
    re.compile(r"\bfor\s+(?:breakfast|lunch|dinner|brunch)\s+(?:i\s+)?(?:had|ate)\s+(.+?)" + _MEAL_END),
]
_MEAL_TAIL = re.compile(r"\s+(?:for\s+(?:breakfast|lunch|dinner|brunch|a snack|snack)|today|tonight|earlier|yesterday|this\s+(?:morning|afternoon|evening))\s*$")
_NOT_FOOD = {"well", "nothing", "a lot", "too much", "healthy", "badly", "out", "late", "early", "something", "not much",
             "very little", "barely anything", "little", "less", "more", "it", "that", "this"}


def parse_meal(text):
    """Return the food named in 'ate biryani' / 'had pasta for dinner', or None. No calories, no judgement."""
    t = (text or "").replace("\u2019", "'").lower().strip()
    if not t or _QUESTION_START.match(t) or t.endswith("?"):
        return None
    for pat in _MEAL_PATTERNS:
        m = pat.search(t)
        if m:
            food = _MEAL_TAIL.sub("", m.group(1).strip())
            if re.search(r"\b(water|glass(?:es)?|cups?|bottles?)\b", food):   # "two bottles of water and a poha": keep only the food
                parts = [x for x in re.split(r"\s+and\s+|,\s*", food) if x and not re.search(r"\b(water|glass(?:es)?|cups?|bottles?)\b", x)]
                food = " and ".join(parts)
            food = re.sub(r"^(?:some|a|an|the|my)\s+", "", food).strip(" -")
            if (not food or food in _NOT_FOOD or len(food) > 60 or re.search(r"\b(nothing|workout|exercise|sleep|slept)\b", food)):
                continue
            return food
    return None


def _clauses(text):
    text = text.replace("\u2019", "'")
    parts = re.split(r"[!?;,\n]+|\.(?=\s|$)|\band\b|\bbut\b|\bthen\b", text, flags=re.I)
    clauses = []
    for p in parts:
        p = userprofile.numwords_to_digits(re.sub(r"[a-z']+", lambda m: _fix_word(m.group(0)), p.strip().lower()))
        if p and not _QUESTION_START.match(p):
            clauses.append(p)
    return clauses


def parse_log(text):
    """Find sleep, water, and habit entries in a natural-language sentence.
    Returns a dict that only contains the keys that were found."""
    found = {}
    habits = []
    for c in _clauses(text or ""):
        if re.search(r"\b(slept|sleep)\b", c):
            m = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b", c)
            if m and 0 < float(m.group(1)) <= 24:
                found["sleep"] = float(m.group(1))
        m = re.search(
            r"\b(?:drank|had|downed|finished|logged?|add(?:ed)?)\s+(?:about |around |roughly |another |an additional |only |just )?"
            r"(\d+(?:\.\d+)?|an?|one|two|three|four|five|six|seven|eight)\s*(glass(?:es)?|cups?|bottles?|liters?|litres?|l)\b", c)
        if m:
            raw = m.group(1)
            n = float(raw) if raw[0].isdigit() else _WORD_NUM[raw]
            unit = m.group(2)
            per = 1
            if unit.startswith("bottle"):
                per = 2
            elif unit.startswith(("liter", "litre")) or unit == "l":
                per = 4
            glasses = n * per
            if 0 < glasses <= 30:
                found["water"] = found.get("water", 0) + glasses
        detailed = None if "?" in (text or "") else reports_workout(c)
        if detailed:
            found["workout"] = detailed
        elif re.search(r"\b(did|finished|completed|done with|just did|smashed|crushed)\s+(my\s+|the\s+|today'?s\s+|a\s+)?(workout|session|training|exercise)\b"
                     r"|\b(workout|session)\s+(is\s+)?(done|complete|finished)\b|\b(worked out|exercised|trained)\b", c):
            found["workout"] = True
        m = _MOOD_RE.search(c)
        if m:
            found["mood"] = _MOOD_WORDS[m.group(1)]
        for name, pat in _HABIT_PATTERNS.items():
            if re.search(pat, c) and name not in habits:
                habits.append(name)
    if habits:
        found["habits"] = habits
    meal = parse_meal(text)
    if meal:
        found["meal"] = meal
    return found


_ACT = (r"(?:workout|work-out|session|training|exercises?|run|jog|swim|cycling|cycle|bike ride|ride|hike|yoga|pilates|gym|weights?|"
        r"dumb+e?ll?s?|kettlebells?|cardio|hiit|class|legs?|arms?|chest|back|core|abs|shoulders?|upper body|lower body|full body)")
_DONE = (r"(?:did(?!\s+(?:you|i|we|they|he|she|it)\b)|done|finished|completed|just did|got in|squeezed in|knocked out|smashed|crushed|hit|"
         r"went (?:for|to|on))")
_REPORT_RE = re.compile(rf"\b{_DONE}\b(?:\s+[\w'-]+){{0,6}}?\s+{_ACT}\b")
_NOT_DONE_RE = re.compile(r"\b(not|never|haven'?t|hasn'?t|didn'?t|won'?t|can'?t|cannot|want to|going to|gonna|plan to|planning to|about to|will|"
                          r"should|need to|would like to)\b|n't\b")
_MINUTES_RE = re.compile(r"(\d+(?:\.\d+)?)\s*-?\s*(hours?|hrs?|minutes?|mins?)\b")
_LABELS = [("dumb", "dumbbell workout"), ("kettlebell", "kettlebell workout"), ("weight", "weights workout"), ("hiit", "HIIT workout"),
           ("cardio", "cardio workout"), ("jog", "jog"), ("run", "run"), ("swim", "swim"), ("cycl", "cycling session"), ("bike", "bike ride"),
           ("hike", "hike"), ("yoga", "yoga session"), ("pilates", "pilates session"), ("upper body", "upper body workout"),
           ("lower body", "lower body workout"), ("full body", "full body workout"), ("legs", "legs workout"), ("leg ", "legs workout"),
           ("arms", "arms workout"), ("chest", "chest workout"), ("shoulder", "shoulders workout"), ("core", "core workout"),
           ("abs", "abs workout"), ("gym", "gym session")]


def reports_workout(message):
    """Detects 'did a 45 minute dumbbell workout' style reports (not questions, plans, or negations).
    Returns None, True (a plain 'did my workout'), or a short title such as '45 min dumbbell workout'."""
    c = (message or "").lower().replace("dumbell", "dumbbell").replace("dumbel", "dumbbell")
    if "?" in c:
        return None
    for m in _REPORT_RE.finditer(c):
        before = c[max(0, m.start() - 25):m.start()]
        if _NOT_DONE_RE.search(before) or _NOT_DONE_RE.search(m.group(0)):
            continue
        label = next((name for key, name in _LABELS if key in c), None)
        minutes = None
        mm = _MINUTES_RE.search(c)
        if mm:
            minutes = round(float(mm.group(1)) * (60 if mm.group(2).startswith(("h", "hr")) else 1))
        elif re.search(r"\bhalf an hour\b", c):
            minutes = 30
        elif re.search(r"\ban hour\b", c):
            minutes = 60
        if not label and not minutes:
            return True
        label = label or "workout"
        return f"{minutes} min {label}" if minutes else label
    return None


def looks_like_log(text):
    """True if the text mentions logging-type words (used to decide on a model fallback)."""
    return bool(re.search(r"\b(slept|drank|glasses|hours of sleep|stretched|walked)\b", (text or "").lower())) \
        and not (text or "").strip().endswith("?")


# ---------- timestamped events (power the "last 24 hours" view) ----------
def _stamp(day=None, now=None):
    if now is not None:
        return now
    return datetime.fromisoformat(day + "T12:00") if day else datetime.now()


def add_event(state, kind, value, day=None, now=None):
    events = state.setdefault("events", [])
    events.append({"ts": _stamp(day, now).isoformat(timespec="minutes"), "kind": kind, "value": value})
    del events[:-500]


def last_24h(state, now=None):
    now = now or datetime.now()
    cutoff = now - timedelta(hours=24)
    evs = sorted((e for e in state.get("events", []) if cutoff <= datetime.fromisoformat(e["ts"]) <= now),
                 key=lambda e: e["ts"])
    return {
        "water": sum(e["value"] for e in evs if e["kind"] == "water"),
        "sleep": next((e["value"] for e in reversed(evs) if e["kind"] == "sleep"), None),
        "mood": next((e["value"] for e in reversed(evs) if e["kind"] == "mood"), None),
        "habits": sorted({e["value"] for e in evs if e["kind"] == "habit"}),
        "meals": [e["value"] for e in evs if e["kind"] == "meal"],
        "events": evs,
    }


# ---------- state updates ----------
def apply_log(state, parsed, day=None, now=None):
    day = day or today()
    stamp_day = day if (now is None and day != today()) else None
    if "water" in parsed:
        state["water"][day] = state["water"].get(day, 0) + parsed["water"]
        add_event(state, "water", parsed["water"], stamp_day, now)
    if "sleep" in parsed:
        state["sleep"][day] = parsed["sleep"]
        add_event(state, "sleep", parsed["sleep"], stamp_day, now)
    if "mood" in parsed:
        state["mood"][day] = parsed["mood"]
        add_event(state, "mood", parsed["mood"], stamp_day, now)
    if "meal" in parsed:
        add_event(state, "meal", parsed["meal"], stamp_day, now)
    if "workout" in parsed:
        title = parsed["workout"] if isinstance(parsed["workout"], str) else "Workout"
        if day not in state.setdefault("workouts_done", {}):
            add_event(state, "workout", title, stamp_day, now)
        state["workouts_done"][day] = title
    if "habits" in parsed:
        done = set(state["habits"].get(day, []))
        for h in parsed["habits"]:
            if h not in done:
                add_event(state, "habit", h, stamp_day, now)
        done.update(parsed["habits"])
        state["habits"][day] = sorted(done)
    return state


def set_habits(state, checked, day=None, now=None):
    day = day or today()
    stamp_day = day if (now is None and day != today()) else None
    new = sorted(h for h in (checked or []) if h in HABITS)
    old = set(state["habits"].get(day, []))
    for h in new:
        if h not in old:
            add_event(state, "habit", h, stamp_day, now)
    for h in old - set(new):  # unticked: remove its most recent event
        for i in range(len(state.get("events", [])) - 1, -1, -1):
            e = state["events"][i]
            if e["kind"] == "habit" and e["value"] == h:
                del state["events"][i]
                break
    state["habits"][day] = new
    return state


def set_mood(state, mood, day=None):
    if mood in MOOD_SCORE and state["mood"].get(day or today()) != mood:
        state["mood"][day or today()] = mood
        add_event(state, "mood", mood, day if day and day != today() else None)
    return state


def mood_today(state, day=None):
    return state["mood"].get(day or today())


def mood_insight(state, day=None):
    """Plain-code pattern: average mood after 7+ hours of sleep vs shorter sleep (last 14 days)."""
    hi, lo = [], []
    for d in _last_days(14, day):
        m, s = state["mood"].get(d), state["sleep"].get(d)
        if m and s is not None:
            (hi if s >= 7 else lo).append(MOOD_SCORE[m])
    if hi and lo:
        return (f"On days you slept 7+ hours, your mood averaged {sum(hi) / len(hi):.1f}/5, compared with "
                f"{sum(lo) / len(lo):.1f}/5 after shorter nights ({len(hi) + len(lo)} days of data, so treat it as a rough pattern).")
    return None


def day_log(state, day=None):
    """Everything logged on one day (your personal memory, kept apart from the shared knowledge notes)."""
    day = day or today()
    return {"water": state["water"].get(day), "sleep": state["sleep"].get(day), "mood": state["mood"].get(day),
            "habits": state["habits"].get(day, []), "workout": state.get("workouts_done", {}).get(day),
            "meals": [e["value"] for e in state.get("events", []) if e["kind"] == "meal" and e["ts"].startswith(day)]}


def recall_markdown(state, day=None, label="today"):
    d = day_log(state, day)
    lines = []
    if d["meals"]:
        lines.append("\U0001F37D\uFE0F **Meals:** " + ", ".join(d["meals"]))
    if d["water"] is not None:
        lines.append(f"\U0001F4A7 **Water:** {d['water']:g} of {WATER_GOAL} glasses")
    if d["sleep"] is not None:
        lines.append(f"\U0001F634 **Sleep:** {d['sleep']:g} hours")
    if d["mood"]:
        lines.append(f"\U0001F642 **Mood:** {d['mood'].lower()}")
    if d["habits"]:
        lines.append("\u2705 **Habits:** " + ", ".join(d["habits"]))
    if d["workout"]:
        lines.append(f"\U0001F3CB\uFE0F **Workout:** {d['workout']}")
    if not lines:
        return f"Nothing logged for {label} yet. Try \"slept 7 hours\", \"ate rice\", or \"drank 2 glasses of water\"."
    return ("**Your day so far**" if label == "today" else f"**{label.capitalize()}**") + "\n\n" + "\n\n".join(lines)


def workouts_this_week(state, day=None):
    """Number of days this calendar week (Mon to Sun) with a workout marked done."""
    d = date.fromisoformat(day) if day else date.today()
    monday = d - timedelta(days=d.weekday())
    done = state.get("workouts_done", {})
    return sum(1 for i in range(7) if (monday + timedelta(days=i)).isoformat() in done)


def today_context(state, day=None):
    """One line describing today's tracking, so answers can be tailored (empty if nothing is logged)."""
    day = day or today()
    bits = []
    if day in state["sleep"]:
        bits.append(f"slept {state['sleep'][day]:g} hours")
    if day in state["water"]:
        bits.append(f"{state['water'][day]:g} of {WATER_GOAL} glasses of water")
    if state["mood"].get(day):
        bits.append("mood " + state["mood"][day].lower())
    if state["habits"].get(day):
        bits.append(f"{len(state['habits'][day])} of {len(HABITS)} habits done")
    meals = [e["value"] for e in state.get("events", []) if e["kind"] == "meal" and e["ts"].startswith(day)]
    if meals:
        bits.append("ate " + ", ".join(meals))
    if day in state.get("workouts_done", {}):
        bits.append("already did a workout")
    return "; ".join(bits)


def habit_streak(state, day=None):
    """Consecutive days (ending today, or yesterday if today is empty) with at least one habit done."""
    d = date.fromisoformat(day) if day else date.today()
    if not state["habits"].get(d.isoformat()):
        d -= timedelta(days=1)
    n = 0
    while state["habits"].get(d.isoformat()):
        n += 1
        d -= timedelta(days=1)
    return n


def habits_today(state, day=None):
    return list(state["habits"].get(day or today(), []))


# ---------- sidebar text ----------
def _fmt(x):
    return f"{x:g}"


def water_md(state, day=None):
    n = state["water"].get(day or today(), 0)
    filled = int(min(n, WATER_GOAL))
    bar = "\u2588" * filled + "\u2591" * (WATER_GOAL - filled)
    return f"**Water today**\n\n`{bar}`\n\n{_fmt(n)} of {WATER_GOAL} glasses"


def sleep_md(state, day=None):
    day = day or today()
    last = state["sleep"].get(day)
    recent = [state["sleep"][d] for d in _last_days(7, day) if d in state["sleep"]]
    line1 = f"Last logged: {_fmt(last)} hours" if last is not None else "Nothing logged today"
    line2 = f"7-day average: {sum(recent) / len(recent):.1f} hours" if recent else "7-day average: no data yet"
    return f"**Sleep**\n\n{line1}\n\n{line2}"


# ---------- BMI ----------
def parse_height_weight(text):
    """Return (height_cm, weight_kg); either may be None."""
    t = (text or "").lower()
    h = w = None
    m = re.search(r"(\d)\s*(?:'|ft|feet|foot)\s*(\d{1,2})?", t)
    if m:
        h = (int(m.group(1)) * 12 + int(m.group(2) or 0)) * 2.54
    else:
        m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*cm\b", t)
        if m:
            h = float(m.group(1))
        else:
            m = re.search(r"\b(\d\.\d{1,2})\s*m\b", t)
            if m:
                h = float(m.group(1)) * 100
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|kilograms?|kilos?|lbs?|pounds?)\b", t)
    if m:
        w = float(m.group(1)) * (1 if m.group(2).startswith(("kg", "kilo")) else 0.45359237)
    return h, w


def compute_bmi(height_cm, weight_kg):
    m = height_cm / 100
    return weight_kg / (m * m)


def bmi_category(bmi):
    if bmi < 18.5:
        return "below the typical range"
    if bmi < 25:
        return "in the typical range"
    if bmi < 30:
        return "above the typical range"
    return "well above the typical range"


def bmi_reply(height_cm, weight_kg):
    if not height_cm or not weight_kg or not (100 <= height_cm <= 250) or not (25 <= weight_kg <= 300):
        return ("To calculate BMI I need a height and a weight, for example \"I'm 5'8 and 150 lbs\" or "
                "\"170 cm, 65 kg\". You can also fill them in under the optional BMI section in the sidebar.")
    bmi = compute_bmi(height_cm, weight_kg)
    return (f"Your BMI is **{bmi:.1f}**, {bmi_category(bmi)} for adults (18.5 to 24.9). "
            "It's only a rough screening number that ignores muscle mass, so don't treat it as a goal or a diagnosis.")


# ---------- weekly summary ----------
def _last_days(n, day=None):
    end = date.fromisoformat(day) if day else date.today()
    return [(end - timedelta(days=i)).isoformat() for i in range(n)]


def weekly_stats(state, day=None):
    days = _last_days(7, day)
    water = [state["water"][d] for d in days if d in state["water"]]
    sleep = [state["sleep"][d] for d in days if d in state["sleep"]]
    habit_days = [d for d in days if state["habits"].get(d)]
    habit_total = sum(len(state["habits"].get(d, [])) for d in days)
    mood = [MOOD_SCORE[state["mood"][d]] for d in days if d in state["mood"]]
    meals_n = sum(1 for e in state.get("events", []) if e["kind"] == "meal" and e["ts"][:10] in days)
    return {
        "avg_mood": sum(mood) / len(mood) if mood else None, "days_mood": len(mood), "meals": meals_n,
        "days_water": len(water), "avg_water": sum(water) / len(water) if water else None,
        "days_sleep": len(sleep), "avg_sleep": sum(sleep) / len(sleep) if sleep else None,
        "days_habits": len(habit_days), "habit_total": habit_total,
        "habit_possible": 7 * len(HABITS),
    }


def format_stats(s):
    water = f"{s['avg_water']:.1f} glasses/day" if s["avg_water"] is not None else "no data"
    sleep = f"{s['avg_sleep']:.1f} h/night" if s["avg_sleep"] is not None else "no data"
    out = f"**Last 7 days:** water {water} \u00b7 sleep {sleep} \u00b7 habits {s['habit_total']}/{s['habit_possible']}"
    if s.get("avg_mood") is not None:
        out += f" \u00b7 mood {s['avg_mood']:.1f}/5"
    if s.get("meals"):
        out += f" \u00b7 {s['meals']} meals logged"
    return out


def export_log(state):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", prefix="fitbuddy_log_", delete=False)
    json.dump({"water": state["water"], "sleep": state["sleep"], "habits": state["habits"], "mood": state["mood"], "workouts": state.get("workouts_done", {}), "events": state.get("events", [])}, f, indent=2)
    f.close()
    return f.name
