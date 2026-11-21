"""HTML pieces for the interface (teal and navy theme). Only numbers and escaped text go into the HTML."""
import html
import math
from datetime import date, datetime, timedelta

import coach
import exercises
import meals
import planner
import trackers
import userprofile

CSS = """
:root {--fb-navy: #0f2742; --fb-teal: #14b8a6; --fb-teal-dark: #0f766e; --fb-sky: #38bdf8; --fb-indigo: #818cf8; --fb-amber: #f59e0b; --fb-coral: #fb7185; --fb-violet: #a78bfa;}
.gradio-container {max-width: 1180px !important; margin: 0 auto !important;}
.fb-flat {--block-padding: 0px; padding: 0 !important; background: transparent !important; border: none !important; box-shadow: none !important;}
.fb-flat .html-container, .fb-flat .prose, .fb-flat > .block {padding: 0 !important; margin: 0 !important; background: transparent !important; border: none !important; box-shadow: none !important; min-height: 0 !important;}
.fb-left {gap: 12px !important;}
.fb-input textarea {min-height: 44px;}
.fb-chip {border-radius: 999px !important;}
.fb-header {background: linear-gradient(120deg, #0f2742 0%, #0f5f73 58%, #14b8a6 100%); color: #fff; padding: 20px 24px; border-radius: 16px; margin: 0;}
.fb-header h1 {margin: 0; font-size: 28px; letter-spacing: -.01em; color: #fff;}
.fb-header p {margin: 4px 0 0; opacity: .92; font-size: 14px; color: #fff;}
.fb-pill {display: inline-block; margin-top: 10px; padding: 3px 12px; border-radius: 999px; background: rgba(255,255,255,.16); font-size: 12px; color: #fff;}
.fb-card {border: 1px solid var(--border-color-primary); background: var(--background-fill-secondary); border-radius: 14px; padding: 14px 16px; margin: 0;}
.fb-card-title {font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--body-text-color-subdued);}
.fb-sub {font-size: 12px; color: var(--body-text-color-subdued); margin-top: 6px;}
.fb-cardhead {display: flex; justify-content: space-between; align-items: baseline;}
.fb-date {font-size: 12px; color: var(--body-text-color-subdued);}
.fb-rings {display: table; table-layout: fixed; width: 100%; margin-top: 12px;}
.fb-ring {display: table-cell; text-align: center; vertical-align: top; padding: 0 4px;}
.fb-ring svg {width: 100%; max-width: 76px; height: auto; display: block; margin: 0 auto;}
.fb-track {fill: none; stroke: var(--border-color-primary); stroke-width: 9; opacity: .7;}
.fb-arc {fill: none; stroke-width: 9; stroke-linecap: round;}
.fb-ringtxt {font-size: 17px; font-weight: 700; fill: var(--body-text-color);}
.fb-ringtxt.done {fill: var(--fb-teal);}
.fb-ringlab {font-size: 12px; font-weight: 600; margin-top: 4px;}
.fb-ringsub {font-size: 10.5px; color: var(--body-text-color-subdued); white-space: nowrap;}
.fb-plan {font-size: 13px; line-height: 1.55; max-height: 190px; overflow-y: auto; margin-top: 8px;}
.fb-chart {display: flex; gap: 8px; align-items: flex-end; height: 150px; margin-top: 8px;}
.fb-col {flex: 1; display: flex; flex-direction: column; align-items: center; height: 100%;}
.fb-colbar {flex: 1; width: 100%; display: flex; align-items: flex-end;}
.fb-colfill {width: 100%; border-radius: 8px 8px 0 0; background: var(--fb-teal);}
.fb-colfill.sky {background: var(--fb-sky);}
.fb-colfill.indigo {background: var(--fb-indigo);}
.fb-colfill.amber {background: var(--fb-amber);}
.fb-val {font-size: 11px; height: 16px; color: var(--body-text-color-subdued);}
.fb-lab {font-size: 11px; margin-top: 4px; color: var(--body-text-color-subdued);}
.fb-stats {display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px;}
.fb-stat {flex: 1; min-width: 120px; border: 1px solid var(--border-color-primary); background: var(--background-fill-secondary); border-radius: 14px; padding: 10px 14px;}
.fb-stat b {display: block; font-size: 22px;}
.fb-stat small {color: var(--body-text-color-subdued);}
.fb-ev {padding: 7px 0; border-bottom: 1px solid var(--border-color-primary); font-size: 13px;}
.fb-ev:last-child {border-bottom: none;}
.fb-evtime {display: inline-block; width: 138px; white-space: nowrap; color: var(--body-text-color-subdued); font-size: 12px;}
.fb-evdot {display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 8px;}
.fb-table {width: 100%; border-collapse: collapse; font-size: 13px;}
.fb-table th, .fb-table td {text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border-color-primary); vertical-align: top;}
.fb-table th {font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--body-text-color-subdued);}
.fb-days {display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; margin: 8px 0;}
.fb-day {border: 1px solid var(--border-color-primary); background: var(--background-fill-secondary); border-radius: 12px; padding: 9px 11px; font-size: 13px;}
.fb-day.today {border-color: var(--fb-teal); box-shadow: 0 0 0 1px var(--fb-teal);}
.fb-day.rest {opacity: .65;}
.fb-day b {display: block; font-size: 12px; color: var(--body-text-color-subdued); text-transform: uppercase; letter-spacing: .05em;}
.fb-day summary {cursor: pointer; list-style: none;}
.fb-day ul {margin: 6px 0 0 16px; padding: 0; font-size: 12px;}
.fb-tick {color: var(--fb-teal); font-weight: 700;}
.fb-warn {border-left: 4px solid var(--fb-amber); padding: 8px 12px; margin: 8px 0; font-size: 13px; background: var(--background-fill-secondary); border-radius: 0 10px 10px 0;}
.fb-meals td:first-child {white-space: nowrap; font-weight: 600;}
.fb-grid {display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px; margin-top: 8px;}
.fb-item {border: 1px solid var(--border-color-primary); background: var(--background-fill-secondary); border-radius: 14px; padding: 12px 14px; font-size: 13px;}
.fb-item h4 {margin: 0 0 6px; font-size: 14px;}
.fb-item p {margin: 6px 0 0; line-height: 1.5;}
.fb-pills {display: flex; flex-wrap: wrap; gap: 5px;}
.fb-pill-s {font-size: 11px; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--border-color-primary); color: var(--body-text-color-subdued);}
.fb-pill-s.hot {border-color: var(--fb-teal); color: var(--fb-teal);}
.fb-count {font-size: 12px; color: var(--body-text-color-subdued); margin: 4px 2px;}
.fb-note summary {cursor: pointer; padding: 6px 0;}
.fb-note {border-bottom: 1px solid var(--border-color-primary); font-size: 13px;}
.fb-toast {border-left: 4px solid var(--fb-teal); background: var(--background-fill-secondary); padding: 8px 12px; margin: 6px 0; font-size: 13px; border-radius: 0 10px 10px 0;}
.fb-insight {border-left: 4px solid var(--fb-teal); padding: 8px 14px; margin-bottom: 10px; font-size: 13px; background: var(--background-fill-secondary); border-radius: 0 10px 10px 0;}
"""

HEADER = (
    '<div class="fb-header"><h1>FitBuddy</h1>'
    "<p>Your calm, friendly fitness and wellness companion. Ask a question, or tell me about your day.</p>"
    '<span class="fb-pill">General information, not medical advice. Your data stays in this session.</span></div>'
)


def _card(title, body):
    return f'<div class="fb-card"><div class="fb-card-title">{title}</div>{body}</div>'


def _ring(pct, color, center, label, sub):
    c = 2 * math.pi * 34
    done = pct >= 1
    off = c * (1 - min(max(pct, 0), 1))
    text = "&#10003;" if done else center
    return (f'<div class="fb-ring"><svg viewBox="0 0 84 84" role="img" aria-label="{label} {sub}">'
            f'<circle class="fb-track" cx="42" cy="42" r="34"/>'
            f'<circle class="fb-arc" cx="42" cy="42" r="34" transform="rotate(-90 42 42)" '
            f'style="stroke:{color};stroke-dasharray:{c:.1f};stroke-dashoffset:{off:.1f}"/>'
            f'<text class="fb-ringtxt{" done" if done else ""}" x="42" y="48" text-anchor="middle">{text}</text></svg>'
            f'<div class="fb-ringlab">{label}</div><div class="fb-ringsub">{sub}</div></div>')


def today_card(state, day=None):
    day = day or trackers.today()
    water = state["water"].get(day, 0)
    sleep = state["sleep"].get(day)
    done = len(state["habits"].get(day, []))
    n_h = len(trackers.HABITS)
    rings = (
        _ring(water / trackers.WATER_GOAL, "var(--fb-sky)", f"{water:g}", "Water", f"of {trackers.WATER_GOAL} glasses")
        + _ring((sleep or 0) / 7, "var(--fb-indigo)", "--" if sleep is None else f"{sleep:g}h", "Sleep", "7+ hrs goal")
        + _ring(done / n_h, "var(--fb-teal)", f"{done}/{n_h}", "Habits", f"of {n_h} done")
    )
    when = date.fromisoformat(day).strftime("%a, %b %d")
    head = f'<div class="fb-cardhead"><div class="fb-card-title">Today at a glance</div><div class="fb-date">{when}</div></div>'
    wk_done, wk_plan = coach.workouts_summary(state, date.fromisoformat(day))
    line = f'<div class="fb-sub">Workouts this week: {wk_done} of {wk_plan}</div>' if wk_plan else ""
    eaten = trackers.day_log(state, day)["meals"]
    if eaten:
        shown = ", ".join(html.escape(x) for x in eaten[:3]) + (f" +{len(eaten) - 3} more" if len(eaten) > 3 else "")
        line += f'<div class="fb-sub">Meals logged today: {shown}</div>'
    return f'<div class="fb-card">{head}<div class="fb-rings">{rings}</div>{line}</div>'


def streak_note(state, day=None):
    n = trackers.habit_streak(state, day)
    text = f"{n}-day habit streak" if n else "No streak yet. Tick a habit to start one."
    return f'<div class="fb-sub" style="margin:0; padding:0 4px 6px;">{text}</div>'


def _session_list(s, limit=6):
    items = []
    for b in s["blocks"][:limit]:
        if b["unit"] == "text":
            items.append(f"<li>{html.escape(b['name'])}" + (f": {html.escape(b['target'])}" if b["target"] else "") + "</li>")
        else:
            unit = "" if b["unit"] == "secs" else " reps"
            items.append(f"<li>{html.escape(b['name'])} - {b['sets']} x {html.escape(b['target'])}{unit}</li>")
    return "<ul>" + "".join(items) + "</ul>"


def plan_card(state, today=None):
    """Sidebar card: today's session (as planned, or as adjusted today)."""
    today = today or date.today()
    if not state.get("workout_plan"):
        return _card("Today's plan", '<div class="fb-sub">Choose your preferences and your plan will appear here.</div>')
    s = coach.current_session(state, today)
    done = today.isoformat() in state.get("workouts_done", {})
    if s is None:
        return _card("Today's plan", '<div class="fb-plan"><b>Rest day.</b><br>An easy walk or some stretching is a great way to recover.</div>')
    tick = ' <span class="fb-tick">Done</span>' if done else ""
    body = (f'<div class="fb-plan"><b>{html.escape(s["title"])}</b> - about {s["est"]} min{tick}'
            f'{_session_list(s)}</div><div class="fb-sub">Ask me to make it shorter, easier, or swap a move.</div>')
    return _card("Today's plan", body)


def plan_week_html(state, today=None):
    today = today or date.today()
    plan, pn = state.get("workout_plan"), state.get("pn")
    if not plan or not pn:
        return _card("Your plan", '<div class="fb-sub">Set your preferences on the left and your weekly plan will appear here.</div>')
    rows = "".join(f"<tr><td><b>{html.escape(a)}</b></td><td>{html.escape(b)}</td><td>{html.escape(c)}</td></tr>"
                   for a, b, c in planner.explain(pn))
    effects = _card("What FitBuddy does with your choices",
                    f'<table class="fb-table"><tr><th>Setting</th><th>You chose</th><th>What it changes</th></tr>{rows}</table>')
    week = planner.week_of(plan, today)
    done_days = state.get("workouts_done", {})
    monday = today - timedelta(days=today.weekday())
    cards = []
    for i in range(7):
        d = monday + timedelta(days=i)
        s = coach.current_session(state, d) if d == today else planner.session_for(plan, i, d)
        is_today = d == today
        tick = ' <span class="fb-tick">Done</span>' if d.isoformat() in done_days else ""
        if s is None:
            cards.append(f'<div class="fb-day rest{" today" if is_today else ""}"><b>{planner.DAY_NAMES[i]}</b>Rest day</div>')
        else:
            cards.append(f'<div class="fb-day{" today" if is_today else ""}"><details><summary><b>{planner.DAY_NAMES[i]}{tick}</b>'
                         f'{html.escape(s["title"])}<br><small>about {s["est"]} min</small></summary>{_session_list(s, 8)}</details></div>')
    wk_done, wk_plan = coach.workouts_summary(state, today)
    src = " (built from your chat request)" if plan.get("source") == "chat" else ""
    head = (f'<div class="fb-card-title">Your week{src}</div><div class="fb-sub">Week {week} of 4: {planner.WEEK_NAMES[week]}. '
            f'Workouts done this week: {wk_done} of {wk_plan}. Tap a day to see its exercises.</div>')
    warn = "".join(f'<div class="fb-warn">{html.escape(w)}</div>' for w in plan["warnings"])
    for txt in (pn.get("limits_unmatched"), pn.get("restrictions_unmatched")):
        if txt:
            warn += f'<div class="fb-warn">I could not match "{html.escape(txt)}" to anything specific, so it is only used as a gentle reminder.</div>'
    return effects + f'<div class="fb-card" style="margin-top:8px">{head}<div class="fb-days">{"".join(cards)}</div></div>' + warn


def _meal_prep_card(plan):
    pp = meals.prep_plan(plan)
    hours = max(1, round(pp["minutes"] / 30) / 2)
    items = "".join(f"<li>{html.escape(t.replace('**', ''))}</li>" for t in pp["tasks"])
    tips = "".join(f'<div class="fb-sub">{html.escape(t)}</div>' for t in pp["tips"])
    return _card(f"Meal prep checklist (about {hours:g} hours, once a week)", f'<ul style="margin:6px 0 0 16px;font-size:13px">{items}</ul>{tips}')


def meal_plan_html(state, today=None):
    today = today or date.today()
    plan, pn = state.get("meal_plan"), state.get("pn")
    if not plan or not pn:
        return _card("Meal plan", '<div class="fb-sub">Your meal plan will appear here once your preferences are set.</div>')
    rows = ""
    for i, day in enumerate(plan["days"]):
        cells = "".join(f"<td>{html.escape(day[t]['name']) if day.get(t) else '-'}</td>" for t in meals.MEAL_TYPES)
        mark = " (today)" if i == today.weekday() else ""
        rows += f"<tr><td>{meals.DAY_NAMES[i]}{mark}</td>{cells}</tr>"
    table = (f'<table class="fb-table fb-meals"><tr><th></th>' + "".join(f"<th>{t}</th>" for t in meals.MEAL_TYPES) + f"</tr>{rows}</table>")
    shop = ""
    for cat, items in meals.shopping_list(plan).items():
        shop += f"<p><b>{html.escape(cat.title())}:</b> " + ", ".join(f"{html.escape(i)}{f' ({n})' if n > 1 else ''}" for i, n in items) + "</p>"
    notes = "".join(f'<div class="fb-sub">{html.escape(n)}</div>' for n in plan["notes"])
    warn = "".join(f'<div class="fb-warn">{html.escape(w)}</div>' for w in plan["warnings"])
    cuis = ", ".join(pn["cuisines"])
    cm = plan.get("cuisine_match")
    match_note = f" {cm[0]} of {cm[1]} meals are from your chosen cuisines." if cm else ""
    return (_card("Your meal plan", f'<div class="fb-sub">Cuisines: {html.escape(cuis)}.{match_note} No calorie counting. Restrictions applied: '
                  f'{html.escape(", ".join([*pn["diets"], *[a.replace("_", " ") + "-free" for a in pn["allergens"]], *["no " + w for w in pn["avoid"]]]) or "none")}.</div>{table}')
            + warn + _meal_prep_card(plan)
            + _card("Shopping list for the week", shop or "<div class='fb-sub'>Nothing to list.</div>")
            + f'<div style="margin-top:8px">{notes}</div>')


def _chart(title, values, maxv, labels, color=""):
    cols = ""
    for v, lab in zip(values, labels):
        h = 0 if not v else max(5, min(v / maxv, 1) * 100)
        cols += (f'<div class="fb-col"><div class="fb-val">{"" if v is None else f"{v:g}"}</div>'
                 f'<div class="fb-colbar"><div class="fb-colfill {color}" style="height:{h:.0f}%"></div></div>'
                 f'<div class="fb-lab">{lab}</div></div>')
    return _card(title, f'<div class="fb-chart">{cols}</div>')


_EV_COLOR = {"water": "var(--fb-sky)", "sleep": "var(--fb-indigo)", "mood": "var(--fb-amber)", "habit": "var(--fb-teal)", "meal": "var(--fb-coral)", "workout": "var(--fb-violet)"}


def _ev_text(e):
    k, val = e["kind"], e["value"]
    if k == "water":
        return f"Water +{val:g} glass{'es' if val != 1 else ''}"
    if k == "sleep":
        return f"Sleep {val:g} hours"
    if k == "mood":
        return f"Mood: {html.escape(str(val))}"
    if k == "meal":
        return f"Meal: {html.escape(str(val))}"
    if k == "workout":
        return f"Workout done: {html.escape(str(val))}"
    return f"Habit done: {html.escape(str(val))}"


def progress_24h(state, now=None):
    now = now or datetime.now()
    s = trackers.last_24h(state, now)
    n_h = len(trackers.HABITS)
    water = f"{s['water']:g}"
    sleep = "--" if s["sleep"] is None else f"{s['sleep']:g}h"
    mood = html.escape(s["mood"]) if s["mood"] else "--"
    habits = f"{len(s['habits'])}/{n_h}"
    meals_n = str(len(s["meals"]))
    workouts_n = str(sum(1 for e in s["events"] if e["kind"] == "workout"))
    stats = ('<div class="fb-stats">'
             f'<div class="fb-stat"><b>{water}</b><small>glasses of water</small></div>'
             f'<div class="fb-stat"><b>{sleep}</b><small>sleep logged</small></div>'
             f'<div class="fb-stat"><b>{mood}</b><small>latest mood</small></div>'
             f'<div class="fb-stat"><b>{habits}</b><small>habits done</small></div>'
             f'<div class="fb-stat"><b>{meals_n}</b><small>meals logged</small></div>'
             f'<div class="fb-stat"><b>{workouts_n}</b><small>workouts done</small></div></div>')
    rows = ""
    for e in reversed(s["events"]):
        ts = datetime.fromisoformat(e["ts"])
        when = ts.strftime("%I:%M %p").lstrip("0")
        if ts.date() != now.date():
            when = "Yesterday " + when
        rows += (f'<div class="fb-ev"><span class="fb-evtime">{when}</span>'
                 f'<span class="fb-evdot" style="background:{_EV_COLOR[e["kind"]]}"></span>{_ev_text(e)}</div>')
    body = rows or '<div class="fb-sub">Nothing logged in the last 24 hours yet. Try "slept 7 hours, drank 2 glasses".</div>'
    return stats + _card("Log, newest first", body)


def progress_html(state, day=None):
    if state.get("view") == "24h" and day is None:
        return progress_24h(state)
    return progress_week(state, day)


def progress_week(state, day=None):
    end = date.fromisoformat(day) if day else date.today()
    days = [(end - timedelta(days=i)) for i in range(6, -1, -1)]
    iso = [d.isoformat() for d in days]
    labels = [d.strftime("%a") for d in days]
    s = trackers.weekly_stats(state, day)
    avg_w = f"{s['avg_water']:.1f}" if s["avg_water"] is not None else "--"
    avg_s = f"{s['avg_sleep']:.1f}" if s["avg_sleep"] is not None else "--"
    avg_m = f"{s['avg_mood']:.1f}" if s["avg_mood"] is not None else "--"
    stats = (f'<div class="fb-stats">'
             f'<div class="fb-stat"><b>{avg_w}</b><small>avg glasses of water</small></div>'
             f'<div class="fb-stat"><b>{avg_s}</b><small>avg hours of sleep</small></div>'
             f'<div class="fb-stat"><b>{avg_m}</b><small>avg mood (out of 5)</small></div>'
             f'<div class="fb-stat"><b>{trackers.habit_streak(state, day)}</b><small>day habit streak</small></div>'
             f'<div class="fb-stat"><b>{trackers.workouts_this_week(state, day)}</b><small>workouts this week</small></div></div>')
    insight = trackers.mood_insight(state, day)
    insight_html = f'<div class="fb-insight">{html.escape(insight)}</div>' if insight else ""
    water = [state["water"].get(d) for d in iso]
    sleep = [state["sleep"].get(d) for d in iso]
    habits = [len(state["habits"].get(d, [])) or None for d in iso]
    mood = [trackers.MOOD_SCORE.get(state["mood"].get(d)) for d in iso]
    return (stats + insight_html
            + _chart("Water (glasses per day)", water, max([trackers.WATER_GOAL] + [w for w in water if w]), labels, "sky")
            + _chart("Sleep (hours per night)", sleep, max([9] + [x for x in sleep if x]), labels, "indigo")
            + _chart("Mood (1 stressed to 5 great)", mood, 5, labels, "amber")
            + _chart("Habits completed per day", habits, len(trackers.HABITS), labels))


# ---------- library: browse everything the app knows ----------
DIET_FILTERS = {"Vegetarian": "vegetarian", "Vegan": "vegan", "Pescatarian": "pescatarian", "Jain": "jain", "Gluten-free": "gluten free",
                "Dairy-free": "dairy free", "Nut-free": "nut allergy", "Egg-free": "egg allergy"}
PATTERN_NAMES = {"squat": "Legs (squat)", "hinge": "Glutes and hamstrings", "lunge": "Legs (lunge)", "push": "Chest and push",
                 "vpush": "Shoulders", "pull": "Back and pull", "arms": "Arms", "core": "Core", "calf": "Calves",
                 "balance": "Balance", "carry": "Carry"}
EQUIP_NAMES = {"bw": "Bodyweight", "db": "Dumbbells", "band": "Bands", "gym": "Gym machine"}
LEVEL_NAMES = {1: "Beginner", 2: "Intermediate", 3: "Advanced"}


def _pill(text, hot=False):
    return f'<span class="fb-pill-s{" hot" if hot else ""}">{html.escape(str(text))}</span>'


def _matches(text, query):
    words = [w for w in (query or "").lower().split() if w]
    t = text.lower()
    return all(w in t for w in words)


def library_counts(chunks):
    notes = len({c["stem"] for c in chunks})
    return f'<div class="fb-count">{notes} notes \u00b7 {len(meals.DISHES)} dishes \u00b7 {len(exercises.EXERCISES)} exercises</div>'


def recipes_html(meal_type="All", cuisine="All", diet="Any", query="", limit=60):
    p = userprofile.normalize(restrictions=DIET_FILTERS.get(diet, ""))
    allowed = {d["name"] for d in meals.eligible(p)} if diet in DIET_FILTERS else None
    out = []
    for d in meals.DISHES:
        if meal_type not in ("All", "") and d["type"] != meal_type.lower():
            continue
        if cuisine not in ("All", "") and d["cuisine"] != cuisine:
            continue
        if allowed is not None and d["name"] not in allowed:
            continue
        if not _matches(d["name"] + " " + " ".join(d["ingredients"]) + " " + " ".join(d["tags"]), query):
            continue
        out.append(d)
    cards = []
    for d in out[:limit]:
        ing = ", ".join(i for i in d["ingredients"] if i != "spices") + (" + spices" if "spices" in d["ingredients"] else "")
        tags = "".join(_pill(t, True) for t in sorted(d["tags"]) if t in ("protein", "quick", "batch"))
        cards.append(f'<div class="fb-item"><h4>{html.escape(d["name"])}</h4><div class="fb-pills">{_pill(d["type"])}{_pill(d["cuisine"])}'
                     f'{_pill(str(d["minutes"]) + " min")}{tags}</div><p><b>You need:</b> {html.escape(ing)}</p>'
                     f'<p>{html.escape(d["method"])}</p></div>')
    more = f" (showing the first {limit})" if len(out) > limit else ""
    note = '<div class="fb-count">Filters use ingredient lists. Always check labels for allergies.</div>' if allowed is not None else ""
    return f'<div class="fb-count">{len(out)} of {len(meals.DISHES)} dishes{more}</div>{note}<div class="fb-grid">{"".join(cards) or "<p>No dishes match.</p>"}</div>'


def exercises_html(pattern="All", equipment="All", level="All", query=""):
    eq_key = {v: k for k, v in EQUIP_NAMES.items()}.get(equipment)
    pat_key = {v: k for k, v in PATTERN_NAMES.items()}.get(pattern)
    lvl_key = {v: k for k, v in LEVEL_NAMES.items()}.get(level)
    out = [e for e in exercises.EXERCISES
           if (not pat_key or e["pattern"] == pat_key) and (not eq_key or e["equip"] == eq_key)
           and (not lvl_key or e["level"] == lvl_key) and _matches(e["name"] + " " + e["cue"], query)]
    cards = []
    for e in out:
        easier = exercises.BY_ID[e["easier"]]["name"] if e["easier"] else ""
        harder = exercises.BY_ID[e["harder"]]["name"] if e["harder"] else ""
        stress = f'<p><b>Stresses:</b> {html.escape(", ".join(sorted(e["stress"])))}</p>' if e["stress"] else ""
        prog = (f'<p><b>Easier:</b> {html.escape(easier)}</p>' if easier else "") + (f'<p><b>Harder:</b> {html.escape(harder)}</p>' if harder else "")
        cards.append(f'<div class="fb-item"><h4>{html.escape(e["name"])}</h4><div class="fb-pills">{_pill(PATTERN_NAMES[e["pattern"]])}'
                     f'{_pill(EQUIP_NAMES[e["equip"]], True)}{_pill(LEVEL_NAMES[e["level"]])}</div><p>{html.escape(e["cue"])}</p>{prog}{stress}</div>')
    return f'<div class="fb-count">{len(out)} of {len(exercises.EXERCISES)} exercises</div><div class="fb-grid">{"".join(cards) or "<p>No exercises match.</p>"}</div>'


def notes_html(chunks, category="All", query=""):
    notes = {}
    for c in chunks:
        n = notes.setdefault(c["stem"], {"title": c["source"], "cats": c["categories"], "text": []})
        n["text"].append(c["text"])
    rows = []
    for stem, n in sorted(notes.items(), key=lambda kv: kv[1]["title"].lower()):
        body = " ".join(n["text"])
        if category not in ("All", "") and category.lower() not in n["cats"]:
            continue
        if not _matches(n["title"] + " " + body, query):
            continue
        text = body.split(". ", 1)[1] if ". " in body[:100] else body
        rows.append(f'<details class="fb-note"><summary><b>{html.escape(n["title"])}</b> {"".join(_pill(c) for c in sorted(n["cats"]))}</summary>'
                    f'<p>{html.escape(text)}</p></details>')
    return f'<div class="fb-count">{len(rows)} of {len(notes)} notes</div>{"".join(rows) or "<p>No notes match.</p>"}'


def model_status_html(text):
    return f'<div class="fb-count" style="margin:2px 4px">{html.escape(text)}</div>'
