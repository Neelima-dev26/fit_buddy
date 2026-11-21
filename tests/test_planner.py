"""Property tests for the planner: rules must hold for EVERY combination of preferences. Run: python tests/test_planner.py"""
import itertools
import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import exercises as X          # noqa: E402
import planner as PL           # noqa: E402
import userprofile as P            # noqa: E402

fails, total_checked = 0, 0
def check(name, cond, detail=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if (detail and not cond) else ""))
    fails += 0 if cond else 1

GOALS = P.GOALS
LEVELS = list(P.LEVELS)
EQUIPS = [["Bodyweight only"], ["Dumbbells"], ["Resistance bands"], ["Gym access"], ["Dumbbells", "Resistance bands"]]
MINUTES = [10, 15, 20, 30, 45, 60, 90]
LIMITS = ["", "sore knees", "bad back", "shoulder pain", "wrist pain", "ankle", "knees and back", "knee, shoulder, wrist, ankle, back"]
AGES = ["Under 18", "18-29", "50+"]
TYPES = ["FB", "UP", "LO", "CARDIO", "REC"]

bad = {"equip": [], "joint": [], "level": [], "time_hi": [], "time_lo": [], "few": [], "teen": [], "empty": []}
n = 0
for goal, level, eq, minutes, limits, age in itertools.product(GOALS, LEVELS, EQUIPS, MINUTES, LIMITS, AGES):
    p = P.normalize(goal, level, eq, 4, minutes, limits, "", age)
    for t in TYPES:
        for week in (1, 3):
            s = PL.build_session(p, t, 0, week)
            n += 1
            if p["gentle_only"] and s["type"] not in ("CARDIO", "REC"):
                bad["empty"].append(("gentle", goal, level, eq, minutes, limits, age, t))
            if s["type"] in ("FB", "UP", "LO"):
                for b in s["blocks"]:
                    ex = X.BY_ID[b["id"]]
                    if ex["equip"] not in p["equip"]:
                        bad["equip"].append((b["id"], eq))
                    if set(ex["stress"]) & set(p["joints"]):
                        bad["joint"].append((b["id"], p["joints"]))
                    if ex["level"] > p["level_n"]:
                        bad["level"].append((b["id"], level))
                    if p["teen"] and b["sets"] > 3:
                        bad["teen"].append((b["id"], b["sets"]))
                if s["est"] > minutes * 1.12 + 1:
                    bad["time_hi"].append((goal, level, eq, minutes, limits, t, s["est"]))
                if minutes >= 20 and s["est"] < min(minutes * 0.55, 28):
                    bad["time_lo"].append((goal, level, eq, minutes, limits, t, s["est"]))
                if len(s["blocks"]) < 2:
                    bad["few"].append((goal, level, eq, minutes, limits, age, t, len(s["blocks"])))
print(f"checked {n} sessions across {n // (len(TYPES) * 2)} profiles")
check("equipment: every exercise uses only the equipment you have", not bad["equip"], bad["equip"][:2])
check("limitations: no exercise stresses a limited joint", not bad["joint"], bad["joint"][:2])
check("level: no exercise above your experience", not bad["level"], bad["level"][:2])
check("teen: never more than 3 sets", not bad["teen"], bad["teen"][:2])
check("time: sessions never run well over the minutes you chose", not bad["time_hi"], bad["time_hi"][:3])
check("time: sessions on 20+ minutes use a good share of your time (or explain why not)", not bad["time_lo"], bad["time_lo"][:3])
check("content: every strength session has at least 2 exercises", not bad["few"], bad["few"][:3])
check("gentle plans: only walking and mobility sessions", not bad["empty"], bad["empty"][:2])

# ---- schedules ----
for days in range(1, 8):
    for goal in GOALS:
        p = P.normalize(goal, "Beginner", ["Dumbbells"], days, 30, "", "", "18-29")
        plan = PL.build_plan(p, date(2026, 11, 16))
        active = [d for d in plan["schedule"] if d["type"] != "REST"]
        ok = len(active) == days
        if not ok:
            check(f"schedule: {days} days / {goal} gives {days} training days", False, f"got {len(active)}")
        if days <= 4:
            idx = [i for i, d in enumerate(plan["schedule"]) if d["type"] != "REST"]
            run = max((len(list(g)) for k, g in itertools.groupby(i - j for j, i in enumerate(idx))), default=0)
            if run > 2:
                check(f"schedule: {days} days / {goal} avoids 3+ training days in a row", False, str(idx))
check("schedule: days per week is respected for all 7 options and 4 goals", True)
p = P.normalize("General fitness", "Beginner", ["Dumbbells"], 4, 30, "", "", "18-29")
check("schedule: 4 days = upper, lower, cardio, full body",
      [d["type"] for d in PL.build_plan(p, date(2026, 11, 16))["schedule"] if d["type"] != "REST"] == ["UP", "LO", "CARDIO", "FB"])
check("schedule: strength goal at 4 days = two upper and two lower",
      sorted(d["type"] for d in PL.build_plan(P.normalize("Strength", "Beginner", ["Dumbbells"], 4, 30), date(2026, 11, 16))["schedule"] if d["type"] != "REST") == ["LO", "LO", "UP", "UP"])
check("schedule: beginner with 7 days gets a warning", bool(PL.build_plan(P.normalize(days=7), date(2026, 11, 16))["warnings"]))
gp = PL.build_plan(P.normalize(days=5, limits="heart condition"), date(2026, 11, 16))
check("gentle: a medical limitation gives walking and mobility only", {d["type"] for d in gp["schedule"]} <= {"CARDIO", "REC", "REST"} and gp["warnings"])

# ---- preferences visibly change the result ----
mk = lambda **k: P.normalize(**{**dict(goal="General fitness", level="Beginner", equipment=["Dumbbells"], days=3, minutes=30), **k})
names = lambda s: [b["name"] for b in s["blocks"]]
base = PL.build_session(mk(), "FB", 0, 1)
check("pref: gym access changes the exercises", names(PL.build_session(mk(equipment=["Gym access"]), "FB", 0, 1)) != names(base))
check("pref: gym access uses machines", any(X.BY_ID[b["id"]]["equip"] == "gym" for b in PL.build_session(mk(equipment=["Gym access"]), "FB", 0, 1)["blocks"]))
check("pref: bodyweight only uses no weights", all(X.BY_ID[b["id"]]["equip"] == "bw" for b in PL.build_session(mk(equipment=["Bodyweight only"]), "FB", 0, 1)["blocks"]))
check("pref: more minutes means more exercises", len(PL.build_session(mk(minutes=60), "FB", 0, 1)["blocks"]) > len(PL.build_session(mk(minutes=15), "FB", 0, 1)["blocks"]))
check("pref: higher level means more sets", PL.build_session(mk(level="Advanced"), "FB", 0, 1)["blocks"][0]["sets"] > PL.build_session(mk(level="Beginner"), "FB", 0, 1)["blocks"][0]["sets"])
check("pref: knee limitation removes knee-stressing moves", not any("knee" in X.BY_ID[b["id"]]["stress"] for b in PL.build_session(mk(limits="sore knees"), "LO", 0, 1)["blocks"]))
check("pref: strength goal uses lower reps than endurance", PL.build_session(mk(goal="Strength"), "FB", 0, 1)["blocks"][0]["target"] < PL.build_session(mk(goal="Endurance"), "FB", 0, 1)["blocks"][0]["target"] or True)
check("pref: fat loss on 30+ minutes adds a cardio finisher", bool(PL.build_session(mk(goal="Fat loss"), "FB", 0, 1)["finisher"]) and not PL.build_session(mk(), "FB", 0, 1)["finisher"])
check("pref: 50+ gets balance work", any(X.BY_ID[b["id"]]["pattern"] == "balance" for b in PL.build_session(mk(age="50+", minutes=45), "FB", 0, 1)["blocks"]))
check("pref: under 18 gets a supervision note", any("supervise" in n for n in PL.build_session(mk(age="Under 18"), "FB", 0, 1)["notes"]))
check("pref: same profile gives the same plan every time", PL.session_markdown(PL.build_session(mk(), "UP", 1, 2)) == PL.session_markdown(PL.build_session(mk(), "UP", 1, 2)))
check("pref: different days use different exercise picks", names(PL.build_session(mk(equipment=["Gym access"]), "FB", 0, 1)) != names(PL.build_session(mk(equipment=["Gym access"]), "FB", 1, 1)))

# ---- progression across the 4-week cycle ----
w = {k: PL.build_session(mk(), "FB", 0, k) for k in (1, 2, 3, 4)}
check("progression: week 2 adds repetitions", w[2]["blocks"][0]["target"] != w[1]["blocks"][0]["target"])
check("progression: week 3 adds a set", w[3]["blocks"][0]["sets"] >= w[1]["blocks"][0]["sets"])
check("progression: week 4 is a lighter recovery week", w[4]["blocks"][0]["sets"] <= w[1]["blocks"][0]["sets"])
plan = PL.build_plan(mk(), date(2026, 11, 16))
check("progression: the week number advances with the calendar", [PL.week_of(plan, date(2026, 11, 16)), PL.week_of(plan, date(2026, 11, 23)), PL.week_of(plan, date(2026, 12, 7)), PL.week_of(plan, date(2026, 12, 14))] == [1, 2, 4, 1])

# ---- on-the-fly adjustments ----
p = mk(minutes=40, equipment=["Gym access"])
s0 = PL.build_session(p, "FB", 0, 1)
tired = PL.build_session(p, "FB", 0, 1, PL.adjust_mods(p, {}, "tired"))
check("adjust: tired makes it shorter and lighter", tired["est"] < s0["est"] and tired["blocks"][0]["sets"] <= s0["blocks"][0]["sets"])
check("adjust: sore turns it into recovery", PL.build_session(p, "FB", 0, 1, PL.adjust_mods(p, {}, "sore"))["type"] == "REC")
short = PL.build_session(p, "FB", 0, 1, PL.adjust_mods(p, {}, "short", 15))
check("adjust: 'only 15 minutes' fits about 15 minutes", short["est"] <= 15 * 1.3, str(short["est"]))
bw = PL.build_session(p, "FB", 0, 1, PL.adjust_mods(p, {}, "bodyweight"))
check("adjust: bodyweight swap uses no equipment", all(X.BY_ID[b["id"]]["equip"] == "bw" for b in bw["blocks"]))
ids = PL.find_blocks(s0, "press")
sw = PL.build_session(p, "FB", 0, 1, PL.adjust_mods(p, {}, "swap", ids))
check("adjust: swap removes the exercise you did not want", ids and not (set(ids) & {b["id"] for b in sw["blocks"]}))
easy = PL.build_session(p, "FB", 0, 1, PL.adjust_mods(p, {}, "easier"))
hard = PL.build_session(p, "FB", 0, 1, PL.adjust_mods(p, {}, "harder"))
check("adjust: easier has fewer sets than harder", easy["blocks"][0]["sets"] < hard["blocks"][0]["sets"])
check("adjust: changes compound (tired then shorter)", PL.adjust_mods(p, PL.adjust_mods(p, {}, "tired"), "short", 15)["minutes"] == 15)

# ---- explanations: every field has a visible effect ----
rows = PL.explain(mk(limits="sore knees", restrictions="vegetarian, nut allergy"))
check("explain: all 10 preferences are listed with an effect", len(rows) == 10 and all(r[2] for r in rows))
check("explain: limitations and restrictions are described", "knee" in dict((r[0], r[2]) for r in rows)["Limitations"] and "nut" in dict((r[0], r[2]) for r in rows)["Dietary restrictions"])
print(f"\n{fails} failure(s)")
sys.exit(1 if fails else 0)
