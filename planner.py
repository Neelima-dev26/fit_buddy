"""Workout planner: turns a normalized profile (userprofile.py) into a weekly plan and daily sessions.

Pure code, no model: days per week, minutes, equipment, level, goal, limitations, and age all change the result.
The language model only explains or coaches around what this module decides.
"""
from datetime import date, timedelta

import exercises as X

PLANNER_API = 3
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEK_NAMES = {1: "Build", 2: "Build a little more", 3: "Push a little", 4: "Recover"}
TYPE_TITLES = {"FB": "Full-body strength", "UP": "Upper body", "LO": "Lower body", "CARDIO": "Cardio",
               "REC": "Recovery and mobility", "REST": "Rest day"}
PATTERNS = {
    "FB": ["squat", "push", "pull", "hinge", "core", "lunge", "vpush", "calf", "arms", "balance", "carry"],
    "UP": ["push", "pull", "vpush", "arms", "core", "pull", "push"],
    "LO": ["squat", "hinge", "lunge", "calf", "core", "balance", "hinge", "carry"],
}
WARMUP = {
    "FB": ["March in place (1 min)", "Arm and hip circles (1 min)", "5 slow sit-to-stands"],
    "UP": ["Arm circles (30 s)", "Shoulder rolls (30 s)", "Cat-cow x 6", "5 wall push-ups"],
    "LO": ["March in place (1 min)", "Leg swings x 10 each side", "5 slow sit-to-stands", "Glute bridges x 8"],
}
COOLDOWN = {
    "FB": "Gentle quad, hamstring, and chest stretches (20 to 30 s each)",
    "UP": "Chest, shoulder, and triceps stretches (20 to 30 s each)",
    "LO": "Quad, hamstring, calf, and hip stretches (20 to 30 s each)",
}
REC_MOVES = ["Cat-cow x 8", "Child's pose (30 s)", "Hip flexor stretch (30 s each side)", "Hamstring stretch (30 s each side)",
             "Doorway chest stretch (30 s)", "Upper-back rotation x 8 each side", "Calf stretch (30 s each side)"]
GOAL_EFFECT = {
    "General fitness": "balanced sessions, 8 to 12 repetitions",
    "Strength": "heavier work with 6 to 10 repetitions (8 to 12 with bodyweight or bands) and longer rests",
    "Fat loss": "circuit-style strength with short rests, 10 to 15 repetitions, and a 5-minute cardio finisher on longer sessions",
    "Endurance": "more cardio days and lighter, higher-repetition strength (12 to 15)",
}
LEVEL_EFFECT = {1: "2 sets per exercise and the simplest versions of each move",
                2: "3 sets per exercise and moves with a bit more challenge",
                3: "3 to 4 sets per exercise and the hardest versions that fit your equipment"}


# ---------- schedule ----------
def _types_for(days, goal):
    base = {
        1: {2: "FB"}, 2: {0: "FB", 3: "FB"}, 3: {0: "FB", 2: "FB", 4: "FB"},
        4: {0: "UP", 1: "LO", 3: "CARDIO", 5: "FB"},
        5: {0: "UP", 1: "LO", 3: "CARDIO", 4: "FB", 5: "REC"},
        6: {0: "UP", 1: "LO", 2: "CARDIO", 3: "UP", 4: "LO", 5: "REC"},
        7: {0: "UP", 1: "LO", 2: "CARDIO", 3: "UP", 4: "LO", 5: "CARDIO", 6: "REC"},
    }[days]
    if goal == "Strength" and days == 4:
        base = {0: "UP", 1: "LO", 3: "UP", 4: "LO"}
    if goal in ("Endurance", "Fat loss"):
        if days == 3:
            base = {0: "FB", 2: "CARDIO", 4: "FB"}
        elif days == 4:
            base = {0: "FB", 1: "CARDIO", 3: "FB", 5: "CARDIO"}
    return base


def schedule_names(days, goal):
    t = _types_for(days, goal)
    return [TYPE_TITLES[t[i]] for i in sorted(t)]


def week_of(plan, today=None):
    today = today or date.today()
    start = date.fromisoformat(plan["created"])
    return (max(0, (today - start).days) // 7) % 4 + 1


# ---------- building blocks ----------
def _sets(p, lvl, week, mods):
    base = {1: 2, 2: 3, 3: 3}[lvl]
    if lvl == 3 and p["goal"] == "Strength":
        base = 4
    base += 1 if week == 3 else -1 if (week == 4 and base >= 3) else 0   # recovery week trims sets, never below 2
    base += mods.get("sets_delta", 0)
    cap = 3 if (p["teen"] or lvl == 1) else 4
    return max(1, min(cap, base))


def _reps(goal, tier, week):
    lo, hi = {"Strength": (6, 10), "Endurance": (12, 15), "Fat loss": (10, 15)}.get(goal, (8, 12))
    if goal == "Strength" and tier in ("bw", "band"):
        lo, hi = 8, 12
    bump = {1: 0, 2: 1, 3: 2, 4: 0}[week]
    return lo + bump, hi + bump


def _choose(pattern, p, lvl, equip, joints, no_impact, used, exclude, rot):
    cands = [e for e in X.EXERCISES
             if e["pattern"] == pattern and e["equip"] in equip and e["level"] <= lvl and e["id"] not in used
             and e["id"] not in exclude and not (e["stress"] & joints) and not (e["impact"] and no_impact)]
    if not cands:
        return None
    cands.sort(key=lambda e: (X.EQUIP_RANK[e["equip"]], -e["level"], e["id"]))
    return cands[rot % min(len(cands), 3)]


def _block(ex, p, lvl, sets, rest, week):
    if ex["unit"] == "secs":
        secs = 20 + 10 * (lvl - 1) + 5 * {1: 0, 2: 1, 3: 2, 4: 0}[week]
        target, per_set = f"{secs} s", (secs + 5 + rest) / 60
    else:
        lo, hi = _reps(p["goal"], ex["equip"], week)
        target, per_set = f"{lo}-{hi}", (45 + rest) / 60
    return {"id": ex["id"], "name": ex["name"], "sets": sets, "target": target, "unit": ex["unit"], "rest": rest,
            "cue": ex["cue"], "minutes": round(sets * per_set + 0.5, 1)}


def _notes(p, week, mods, extra=()):
    notes = [f"Week {week} of 4: {WEEK_NAMES[week]}."]
    if p["joints"]:
        notes.append(f"Skipped moves that stress your {', '.join(p['joints'])}.")
    if p["teen"]:
        notes.append("Ask a coach or an adult to supervise anything heavy.")
    if p["senior"]:
        notes.append("Balance work is included. Keep a wall or sturdy chair nearby.")
    if p["limits_unmatched"]:
        notes.append(f"You mentioned \"{p['limits_unmatched']}\". Go gently and stop if anything hurts.")
    notes.extend(extra)
    return notes


def _mod_notes(mods):
    out = []
    if mods.get("reason"):
        out.append(mods["reason"])
    if mods.get("exclude"):
        out.append("Swapped as you asked.")
    return out


# ---------- sessions ----------
def build_session(p, day_type, day_idx=0, week=1, mods=None, variant=0):
    mods = mods or {}
    minutes = max(10, min(90, int(mods.get("minutes") or p["minutes"])))
    if mods.get("recovery"):
        day_type = "REC"
    if p["gentle_only"] and day_type not in ("REC", "CARDIO"):
        day_type = "CARDIO"
    if day_type == "CARDIO":
        return _cardio(p, minutes, week, mods)
    if day_type == "REC":
        return _recovery(p, minutes, week, mods)
    return _strength(p, day_type, minutes, day_idx + variant, week, mods)


def _strength(p, day_type, minutes, day_idx, week, mods):
    warm = 2 if minutes <= 15 else 3 if minutes <= 25 else 4 if minutes <= 45 else 5
    cool = 2 if minutes <= 25 else 3 if minutes <= 45 else 4
    finisher = 5 if (p["goal"] == "Fat loss" and minutes >= 30) else 0
    budget = minutes - warm - cool - finisher
    lvl = max(1, min(3, p["level_n"] + mods.get("level_delta", 0)))
    sets = _sets(p, lvl, week, mods)
    if minutes <= 15:
        sets = min(sets, 2)
    rest = 30 if minutes <= 15 else {"Strength": 75, "Endurance": 45, "Fat loss": 45}.get(p["goal"], 60)
    while sets > 2 and 2 * (sets * (45 + rest) / 60 + 0.5) > budget * 1.05:   # keep room for at least two exercises
        sets -= 1
    equip = set(mods.get("equip") or p["equip"])
    joints = set(p["joints"])
    no_impact = bool(mods.get("no_impact") or p["senior"] or joints & {"knee", "ankle", "hip"})
    exclude = set(mods.get("exclude") or [])
    patterns = list(PATTERNS[day_type])
    if p["senior"]:
        patterns.insert(min(4, len(patterns)), "balance")
    blocks, used, total = [], set(), 0.0
    for slot, pattern in enumerate(patterns):
        ex = _choose(pattern, p, lvl, equip, joints, no_impact, used, exclude, day_idx + slot)
        if not ex:
            continue
        b = _block(ex, p, lvl, sets, rest, week)
        if blocks and total + b["minutes"] > budget * 1.05:
            continue
        if len(blocks) >= 7:
            break
        blocks.append(b)
        used.add(ex["id"])
        total += b["minutes"]
    leftover = budget - total
    extra = min(15, int(leftover)) if leftover >= 6 else 0
    fin_min = (finisher + extra) if (finisher or extra) else 0
    fin_min = min(15, fin_min)
    est = round(warm + cool + total + fin_min)
    notes = _mod_notes(mods)
    if est < minutes * 0.75:
        notes.append(f"Your {minutes}-minute target is longer than this session needs at your level. Add an easy walk if you have the time.")
    return {
        "type": day_type, "title": TYPE_TITLES[day_type] + (" (adjusted)" if mods else ""), "minutes": minutes,
        "est": est, "week": week, "warm_min": warm, "cool_min": cool,
        "warmup": WARMUP[day_type], "blocks": blocks, "cooldown": COOLDOWN[day_type],
        "finisher": f"{fin_min} min of easy-to-moderate cardio you enjoy, such as brisk walking, step jacks, or cycling" if fin_min else "",
        "fin_min": fin_min, "notes": _notes(p, week, mods, notes),
    }


def _cardio(p, minutes, week, mods):
    warm = 5 if minutes >= 25 else 3
    cool = 3 if minutes >= 25 else 2
    main = max(5, minutes - warm - cool)
    low = bool(set(p["joints"]) & {"knee", "ankle", "hip", "back"}) or p["senior"] or p["gentle_only"] or mods.get("no_impact")
    lvl = max(1, min(3, p["level_n"] + mods.get("level_delta", 0)))
    gym = "gym" in (mods.get("equip") or p["equip"])
    activity = ("Stationary bike, rower, elliptical, or treadmill walk" if gym else
                "Brisk walk (or cycling or swimming if you prefer)")
    if low or lvl == 1 or p["gentle_only"]:
        detail = f"{main} min steady, at a pace where you can talk but not sing"
        if week == 3 and not p["gentle_only"]:
            detail += ", with 5 short pickups of 30 s a little faster"
    elif p["goal"] == "Endurance":
        detail = f"{main} min steady at a comfortable pace, finishing with 3 x 1 min a little faster"
    elif lvl == 2:
        detail = f"{max(1, main // 3)} rounds of 1 min brisk or jogging + 2 min easy"
    else:
        detail = f"{max(1, main // 4)} rounds of 2 min hard + 2 min easy"
    return {
        "type": "CARDIO", "title": TYPE_TITLES["CARDIO"] + (" (adjusted)" if mods else ""), "minutes": minutes,
        "est": minutes, "week": week, "warm_min": warm, "cool_min": cool, "warmup": ["Easy walking pace (3 to 5 min)"],
        "blocks": [{"id": "cardio", "name": activity, "sets": 1, "target": detail, "unit": "text", "rest": 0,
                    "cue": "Hard efforts should feel challenging but controlled.", "minutes": main}],
        "cooldown": "Easy walk and light calf and hamstring stretches", "finisher": "",
        "notes": _notes(p, week, mods, ["Gentle cardio only." if p["gentle_only"] else "Low-impact options are used because of your joints, age, or request."
                                         if low else ""] + _mod_notes(mods)),
    }


def _recovery(p, minutes, week, mods):
    n = min(len(REC_MOVES), max(3, round(minutes / 1.8)))        # each stretch or mobility move takes about 1.5 minutes
    walk = max(0, int(minutes - n * 1.5 - 1))
    blocks = [{"id": f"rec{i}", "name": m, "sets": 1, "target": "", "unit": "text", "rest": 0, "cue": "", "minutes": 1.5}
              for i, m in enumerate(REC_MOVES[:n])]
    if walk >= 3:
        blocks.append({"id": "walk", "name": "Easy walk", "sets": 1, "target": f"{walk} min at a relaxed pace",
                       "unit": "text", "rest": 0, "cue": "", "minutes": walk})
    else:
        walk = 0
    return {
        "type": "REC", "title": TYPE_TITLES["REC"] + (" (adjusted)" if mods else ""), "minutes": minutes,
        "est": round(n * 1.5 + walk + 1), "week": week, "warm_min": 0, "cool_min": 1, "warmup": [], "blocks": blocks,
        "cooldown": "Slow breathing (1 min)", "finisher": "", "notes": _notes(p, week, mods, _mod_notes(mods)),
    }


# ---------- plan ----------
def build_plan(p, today=None, source="profile", variant=0):
    today = today or date.today()
    if p["gentle_only"]:
        types = {i: ("CARDIO" if k % 2 == 0 else "REC") for k, i in enumerate([0, 2, 4, 5, 6][:min(p["days"], 5)])}
    else:
        types = _types_for(p["days"], p["goal"])
    warnings = []
    if p["gentle_only"]:
        warnings.append("You mentioned something that may need a doctor's input, so your plan is gentle walking and mobility only. "
                        "Please check with a doctor before adding strength or harder exercise.")
    if p["days"] >= 6 and p["level_n"] == 1 and not p["gentle_only"]:
        warnings.append("Training 6 to 7 days a week is a lot for a beginner. Keep sessions easy and rest whenever you need to.")
    return {"created": today.isoformat(), "profile": p, "profile_sig": p["sig"], "source": source, "variant": variant,
            "schedule": [{"day": DAY_NAMES[i], "type": types.get(i, "REST")} for i in range(7)], "warnings": warnings}


def session_for(plan, idx, today=None, mods=None):
    """Build the session for weekday idx (0=Mon), or None on a rest day."""
    t = plan["schedule"][idx]["type"]
    if t == "REST":
        return None
    return build_session(plan["profile"], t, idx, week_of(plan, today), mods, plan.get("variant", 0))


def week_sessions(plan, today=None):
    return [session_for(plan, i, today) for i in range(7)]


def adjust_mods(p, mods, mode, value=None):
    """Compound a change onto the current modifiers. modes: tired, sore, short, longer, bodyweight, easier, harder, swap."""
    m = dict(mods or {})
    base = int(m.get("minutes") or p["minutes"])
    if mode == "tired":
        m.update(sets_delta=m.get("sets_delta", 0) - 1, no_impact=True, minutes=max(10, round(base * 0.7 / 5) * 5),
                 reason="A lighter version because you have low energy today.")
    elif mode == "sore":
        m.update(recovery=True, minutes=max(10, round(base * 0.8 / 5) * 5), reason="Gentle recovery because you are sore.")
    elif mode == "short":
        m.update(minutes=max(10, int(value or round(base * 0.7 / 5) * 5)), reason=f"Shortened to about {max(10, int(value or round(base * 0.7 / 5) * 5))} minutes.")
    elif mode == "longer":
        m.update(minutes=min(90, int(value or round(base * 1.3 / 5) * 5)), reason="A bit longer, as you asked.")
    elif mode == "bodyweight":
        m.update(equip=["bw"], reason="Bodyweight-only version.")
    elif mode == "easier":
        m.update(level_delta=max(-2, m.get("level_delta", 0) - 1), sets_delta=m.get("sets_delta", 0) - 1, reason="An easier version.")
    elif mode == "harder":
        m.update(level_delta=min(2, m.get("level_delta", 0) + 1), sets_delta=m.get("sets_delta", 0) + 1, reason="A harder version.")
    elif mode == "swap" and value:
        m["exclude"] = sorted(set(m.get("exclude", [])) | set(value))
    return m


def find_blocks(session, fragment):
    """Exercise ids in a session whose name contains the fragment (for 'swap the lunges')."""
    frag = fragment.lower().rstrip("s")
    return [b["id"] for b in session["blocks"] if frag and frag in b["name"].lower()]


# ---------- text ----------
ICON = {"FB": "\U0001F3CB\uFE0F", "UP": "\U0001F3CB\uFE0F", "LO": "\U0001F9B5", "CARDIO": "\U0001F6B6", "REC": "\U0001F9D8"}
SHORT = {"FB": "Full body", "UP": "Upper", "LO": "Lower", "CARDIO": "Cardio", "REC": "Recover", "REST": "Rest"}


def _plain(text):
    return text.split(" (")[0].rstrip(".").lower()


def session_markdown(s, heading=None, detail=False):
    """Compact card for chat. detail=True adds coaching cues and rest times."""
    if detail:
        return session_detail(s, heading)
    head = f"{ICON.get(s['type'], ICON['FB'])} **{heading or s['title']}** \u00b7 about {s['est']} min \u00b7 week {s['week']} of 4"
    parts = [head]
    if s["type"] in ("CARDIO", "REC"):
        parts.append("\n".join(f"- {b['name']}" + (f": {b['target']}" if b["target"] else "") for b in s["blocks"]))
        parts.append(f"**Cool-down:** {_plain(s['cooldown'])}")
    else:
        if s["warmup"]:
            parts.append(f"**Warm-up** ({s['warm_min']} min): " + ", ".join(_plain(w) for w in s["warmup"]))
        parts.append("\n".join(f"{i}. **{b['name']}** \u2014 {b['sets']} \u00d7 {b['target']}" for i, b in enumerate(s["blocks"], 1)))
        if s.get("finisher"):
            parts.append(f"**Finisher** ({s.get('fin_min', 5)} min): easy cardio such as brisk walking, step jacks, or cycling")
        parts.append(f"**Cool-down** ({s['cool_min']} min): {_plain(s['cooldown'])}")
    notes = [n for n in s["notes"] if n and not n.startswith("Week ")]
    if notes:
        parts.append("\U0001F4A1 " + " ".join(notes))
    return "\n\n".join(parts)


def session_detail(s, heading=None):
    lines = [f"**{heading or s['title']} - about {s['est']} min**"]
    if s["warmup"]:
        lines.append(f"- **Warm-up ({s['warm_min']} min):** " + "; ".join(s["warmup"]) + ".")
    if s["type"] in ("CARDIO", "REC"):
        for b in s["blocks"]:
            lines.append(f"- **{b['name']}**" + (f": {b['target']}" if b["target"] else ""))
    else:
        lines.append("- **Main:**")
        for b in s["blocks"]:
            unit = "" if b["unit"] == "secs" else " reps"
            lines.append(f"  - **{b['name']}** - {b['sets']} x {b['target']}{unit} (rest {b['rest']} s). {b['cue']}")
    if s.get("finisher"):
        lines.append(f"- **Finisher ({s.get('fin_min', 5)} min):** {s['finisher']}.")
    lines.append(f"- **Cool-down ({s['cool_min']} min):** {s['cooldown']}.")
    notes = [n for n in s["notes"] if n]
    if notes:
        lines.append("\n" + " ".join(notes))
    return "\n".join(lines)


def week_markdown(plan, today=None):
    """One compact table for the week."""
    today = today or date.today()
    head = "| " + " | ".join(f"**{n}**" if i == today.weekday() else n for i, n in enumerate(DAY_NAMES)) + " |"
    mins = [week_sessions_est(plan, i, today) for i in range(7)]
    rows = [head, "|" + "---|" * 7,
            "| " + " | ".join(SHORT[d["type"]] for d in plan["schedule"]) + " |",
            "| " + " | ".join(f"{m} min" if m else "-" for m in mins) + " |"]
    out = "\n".join(rows)
    if plan["warnings"]:
        out += "\n\n\u26A0\uFE0F " + " ".join(plan["warnings"])
    return out


def week_sessions_est(plan, idx, today):
    s = session_for(plan, idx, today)
    return s["est"] if s else 0


def explain(p, plan=None):
    """Rows of (setting, your choice, what FitBuddy does with it). Shown in the app so no preference is a mystery."""
    rows = []
    rows.append(("Goal", p["goal"], GOAL_EFFECT[p["goal"]]))
    rows.append(("Experience", p["level"], LEVEL_EFFECT[p["level_n"]]))
    names = {"bw": "bodyweight moves", "db": "dumbbells", "band": "resistance bands", "gym": "gym machines"}
    have = [names[k] for k in ("gym", "db", "band", "bw") if k in p["equip"]]
    rows.append(("Equipment", ", ".join(p["equipment"]),
                 "Uses " + ", ".join(have) + (". Machines and dumbbells are picked first." if "gym" in p["equip"] else ".")))
    rows.append(("Days per week", str(p["days"]), "Weekly layout: " + ", ".join(schedule_names(p["days"], p["goal"])) + ", with the other days as rest."
                 if not p["gentle_only"] else "Gentle walking and mobility days only (see limitations)."))
    rows.append(("Minutes per session", str(p["minutes"]), "Sessions are built to fit about this time, including warm-up and cool-down."))
    if p["gentle_only"]:
        lim = "A medical word was detected, so the plan is gentle walking and mobility only. Please check with a doctor first."
    elif p["joints"]:
        lim = f"Skips exercises that stress your {', '.join(p['joints'])} and picks gentler swaps. Stop if anything hurts."
    elif p["limits_unmatched"]:
        lim = "I could not match this to a joint, so it is only a reminder to go gently."
    else:
        lim = "None entered."
    rows.append(("Limitations", p["limits"] or "none", lim))
    age = ("Sets are capped, impact is limited, and heavy lifting needs supervision." if p["teen"] else
           "Adds balance work, avoids high-impact moves, and keeps cardio low-impact." if p["senior"] else "Standard adult plan.")
    rows.append(("Age range", p["age"], age))
    parts = [*p["diets"], *[a.replace("_", " ") + "-free" for a in p["allergens"]], *["no " + w for w in p["avoid"]]]
    meals = ("Meal plans exclude: " + ", ".join(parts) + "." if parts else
             ("Not recognized, so no filtering was applied. Try words like vegetarian, vegan, nut allergy, or no mushrooms." if p["restrictions_unmatched"]
              else "No filtering."))
    rows.append(("Dietary restrictions", p["restrictions"] or "none", meals))
    rows.append(("Cuisines", ", ".join(p["cuisines"]), "Meal plans favor these cuisines." if p["cuisines"] != ["Any"] else "Meals from any cuisine."))
    rows.append(("Coaching style", p["style"], "Changes how the AI coach words its replies (needs the language model)."))
    return rows
