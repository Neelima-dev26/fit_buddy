"""Application layer: connects the profile, the planners, today's session, and what you have logged.

No Gradio and no language model here, so everything is easy to test. app.py calls these functions, and the
language model (when on) only phrases the results.
"""
import re
from datetime import date

import meals
import planner
import userprofile
import trackers

COACH_API = 3

_MODE_RULES = [
    ("bodyweight", r"no equipment|bodyweight|body weight|hotel|travel|at home with nothing"),
    ("tired", r"\b(tired|exhausted|low[- ]energy|no energy|drained)\b"),
    ("sore", r"\b(sore|stiff|achy)\b"),
    ("easier", r"\b(easy|easier|lighter|gentle|gentler|simpler|less intense)\b"),
    ("harder", r"\b(harder|tougher|more challenging|intense)\b"),
    ("longer", r"\b(longer|more time)\b"),
]
_SWAP = re.compile(r"\b(?:swap|replace|skip|without|drop|remove|instead of|no)\s+(?:the\s+|my\s+)?([a-z-]{3,})")
_NOT_EXERCISE = {"equipment", "time", "energy", "rest", "weights", "gym", "more", "extra", "problem"}


def sync(state, pn, force=False):
    """Make the saved plans match the current profile. Returns what was rebuilt."""
    state["pn"] = pn
    changed = []
    wp = state.get("workout_plan")
    if force or wp is None or wp["profile_sig"] != pn["sig"]:
        state["workout_plan"] = planner.build_plan(pn)
        state["today_ctx"] = None
        changed.append("workout plan")
    mp = state.get("meal_plan")
    if force or mp is None or mp["meal_sig"] != pn["meal_sig"]:
        state["meal_plan"] = meals.build_plan(pn, state.get("meal_seed", 0))
        changed.append("meal plan")
    return changed


def _fingerprint(plan, today=None):
    return "|".join(planner.session_markdown(s) if s else "rest" for s in planner.week_sessions(plan, today))


def rebuild(state, pn, today=None):
    """Rebuild the workout plan from your saved preferences with fresh exercise picks, and restart the 4-week cycle today.
    Returns (changed_exercises, message) so the screen can say honestly what happened."""
    today = today or date.today()
    old = state.get("workout_plan")
    variant = (old.get("variant", 0) + 1) if old else 0
    before = _fingerprint(old, today) if old else ""
    plan = planner.build_plan(pn, today, variant=variant)
    state["workout_plan"], state["today_ctx"] = plan, None
    changed = _fingerprint(plan, today) != before
    if changed:
        return True, "Rebuilt with fresh exercise picks. Week 1 of the 4-week cycle starts today."
    return False, ("Rebuilt, and week 1 starts today. Your equipment, experience, and limitations leave only one good option for "
                   "most moves, so the exercises stay the same. Add equipment or change your level to see more variety.")


def plan_from_message(state, pn, message, today=None):
    """'Give me a 4-day plan with dumbbells': build a plan for that request. Your saved profile is not changed."""
    ov = userprofile.overrides_from_text(message)
    p = userprofile.with_changes(pn, **ov) if ov else pn
    plan = planner.build_plan(p, today, source="chat" if ov else "profile")
    plan["profile_sig"] = pn["sig"]          # stays until you change the saved profile
    state["workout_plan"], state["today_ctx"] = plan, None
    return plan, ov


def modes_from_message(message):
    """Cues in a message ('tired', 'only 10 minutes', 'swap the lunges') as a list of (mode, value)."""
    t = userprofile.numwords_to_digits((message or "").lower())
    out = [(mode, None) for mode, pat in _MODE_RULES if re.search(pat, t)]
    m = re.search(r"\b(\d{1,3})\s*[- ]?\s*(?:min|mins|minutes?)\b", t)
    if m and 10 <= int(m.group(1)) <= 90:
        out.append(("short", int(m.group(1))))
    elif re.search(r"\b(shorter|quick|short|brief|less time)\b", t):
        out.append(("short", None))
    s = _SWAP.search(t)
    if s and s.group(1) not in _NOT_EXERCISE:
        out.append(("swap", s.group(1)))
    return out


def _week(plan, today):
    return planner.week_of(plan, today)


def start_or_adjust(state, modes, today=None, reset=False):
    """Create today's session (or compound changes onto it). Returns (session, lead_text, notes)."""
    today = today or date.today()
    plan = state["workout_plan"]
    p, idx = plan["profile"], today.weekday()
    ctx = state.get("today_ctx")
    if reset or not ctx or ctx["date"] != today.isoformat():
        typ, lead = plan["schedule"][idx]["type"], ""
        if typ == "REST":
            if modes:
                typ, lead = "FB", "Today is a rest day in your plan, but here is a session since you asked."
            else:
                typ, lead = "REC", "Today is a rest day in your plan. If you want to move anyway, here is a gentle option."
        ctx = {"date": today.isoformat(), "type": typ, "idx": idx, "mods": {}, "lead": lead}
    notes = []
    for mode, value in modes:
        if mode == "swap":
            sess = planner.build_session(p, ctx["type"], ctx["idx"], _week(plan, today), ctx["mods"], plan.get("variant", 0))
            ids = planner.find_blocks(sess, value or "")
            if ids:
                ctx["mods"] = planner.adjust_mods(p, ctx["mods"], "swap", ids)
            else:
                notes.append(f"I could not find \"{value}\" in today's session, so nothing was swapped.")
        else:
            ctx["mods"] = planner.adjust_mods(p, ctx["mods"], mode, value)
    state["today_ctx"] = ctx
    return planner.build_session(p, ctx["type"], ctx["idx"], _week(plan, today), ctx["mods"], plan.get("variant", 0)), ctx.get("lead", ""), notes


def current_session(state, today=None):
    """Today's session as it currently stands (planned, or as adjusted today). None on a rest day or without a plan."""
    today = today or date.today()
    plan = state.get("workout_plan")
    if not plan:
        return None
    ctx = state.get("today_ctx")
    if ctx and ctx["date"] == today.isoformat():
        return planner.build_session(plan["profile"], ctx["type"], ctx["idx"], _week(plan, today), ctx["mods"], plan.get("variant", 0))
    return planner.session_for(plan, today.weekday(), today)


def mark_done(state, today=None):
    today = today or date.today()
    s = current_session(state, today)
    title = s["title"] if s else "Workout"
    trackers.apply_log(state, {"workout": title}, day=today.isoformat())
    return title


def workouts_summary(state, today=None):
    """(done this week, planned this week)"""
    today = today or date.today()
    plan = state.get("workout_plan")
    planned = sum(1 for d in plan["schedule"] if d["type"] != "REST") if plan else 0
    return trackers.workouts_this_week(state, today.isoformat()), planned


def why(pn, session=None):
    """One plain sentence naming the preferences behind a plan."""
    bits = [f"{pn['days']} days a week", f"about {pn['minutes']} minutes"]
    eq = [e.lower() for e in pn["equipment"]]
    bits.append(", ".join(eq))
    bits.append(f"{pn['level'].lower()} level")
    bits.append(f"a {pn['goal'].lower()} goal")
    out = "Built from your choices: " + ", ".join(bits) + "."
    if pn["joints"]:
        out += f" Moves that stress your {', '.join(pn['joints'])} are skipped."
    if pn["gentle_only"]:
        out += " Because of what you mentioned under limitations, it is gentle only. Please check with a doctor first."
    return out


def why_short(pn):
    """A short 'built for' line."""
    bits = [f"{pn['days']} days a week", f"{pn['minutes']} min", ", ".join(e.lower() for e in pn["equipment"]), pn["level"].lower()]
    if pn["joints"]:
        bits.append(f"protecting your {', '.join(pn['joints'])}")
    if pn["gentle_only"]:
        bits.append("gentle only, check with a doctor first")
    return "_Built for: " + " \u00b7 ".join(bits) + "_"


def session_reply(session, lead="", notes=(), pn=None, detail=False):
    parts = [lead] if lead else []
    parts.append(planner.session_markdown(session, detail=detail))
    parts.extend(notes)
    if pn:
        parts.append(why_short(pn))
    word = next((k for k in ("press", "row", "squat", "lunge", "curl", "raise", "bridge", "pushdown", "plank", "fly", "pulldown", "extension")
                 for b in session["blocks"] if k in b["name"].lower()), None)
    swap = f", **swap the {word}**," if word else ","
    parts.append(f"Say **shorter**{swap} **easier**, or **details**.".replace(",,", ","))
    return "\n\n".join(p for p in parts if p)


# ---------- meals ----------
def shopping_markdown(plan):
    lines = []
    for cat, items in meals.shopping_list(plan).items():
        lines.append(f"- **{cat.title()}:** " + ", ".join(f"{i} ({n})" if n > 1 else i for i, n in items))
    return "\n".join(lines)


def meal_reply(state, pn, message, today=None):
    """Returns (markdown, plan). Handles: new plan, shopping list, meal prep, the week table, or today's meals."""
    today = today or date.today()
    t = (message or "").lower()
    if re.search(r"\b(new|another|different|shuffle|refresh|regenerate)\b", t):
        state["meal_seed"] = state.get("meal_seed", 0) + 1
        state["meal_plan"] = meals.build_plan(pn, state["meal_seed"], today)
    if not state.get("meal_plan"):
        state["meal_plan"] = meals.build_plan(pn, state.get("meal_seed", 0), today)
    plan = state["meal_plan"]
    if re.search(r"shopping|grocery|groceries", t):
        body = "\U0001F6D2 **Shopping list for the week** (meals in brackets)\n\n" + shopping_markdown(plan)
    elif re.search(r"\bprep\b", t):
        body = meals.prep_markdown(plan)
    elif re.search(r"\b(week|weekly|7|seven)\b", t):
        body = "\U0001F4C5 **Your week of meals**\n\n" + meals.week_table_markdown(plan, today) + "\n\nSnacks, recipes, and the shopping list are in the **Meals** tab."
    else:
        body = "**Today's meals**\n\n" + meals.day_markdown(plan, today.weekday()) + "\n\nSay **meal plan for the week**, **meal prep**, or **shopping list** for more."
    extra = list(plan["warnings"]) + [n for n in plan["notes"] if "did not recognize" in n]
    if extra:
        body += "\n\n" + " ".join(extra)
    body += "\n\n_I filter dishes by ingredients, but I cannot guarantee allergen safety. Always check labels._"
    return body, plan
