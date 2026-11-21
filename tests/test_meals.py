"""Property tests for the meal planner: restrictions must hold for EVERY combination. Run: python tests/test_meals.py"""
import itertools
import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import meals as M      # noqa: E402
import userprofile as P    # noqa: E402

fails = 0
def check(name, cond, detail=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if (detail and not cond) else ""))
    fails += 0 if cond else 1

ANIMAL = {"meat", "fish", "shellfish", "egg", "dairy", "honey"}
DIETS = ["", "vegetarian", "vegan", "pescatarian", "jain", "halal", "kosher"]
ALLERGEN_WORDS = ["", "nut allergy", "peanut allergy", "dairy free", "gluten free", "egg allergy", "fish allergy", "shellfish allergy",
                  "soy allergy", "sesame allergy", "dairy free, gluten free", "nut allergy, soy allergy, sesame allergy"]
AVOID = ["", "no mushrooms", "no onions", "hate cilantro", "no tomato, no rice", "avoid paneer"]
CUISINES = [["Any"], ["Indian"], ["Mediterranean", "Italian"], ["East Asian", "Southeast Asian"], ["Latin American"], ["African / Caribbean"]]

check("menu: every dish has a known ingredient list", all(d["ingredients"] for d in M.DISHES))
check("menu: at least 200 dishes covering all 4 meal types", len(M.DISHES) >= 200 and {d["type"] for d in M.DISHES} == set(M.MEAL_TYPES))

violations, empties, n = [], [], 0
for diet, allergy, avoid in itertools.product(DIETS, ALLERGEN_WORDS, AVOID):
    text = ", ".join(x for x in (diet, allergy, avoid) if x)
    p = P.normalize(restrictions=text)
    plan = M.build_plan(p, 3, date(2026, 11, 16))
    n += 1
    for day in plan["days"]:
        for t in M.MEAL_TYPES:
            d = day.get(t)
            if not d:
                continue
            a = d["attrs"]
            if "vegetarian" in p["diets"] and a & {"meat", "fish", "shellfish"}: violations.append((text, d["name"], "meat/fish"))
            if "vegan" in p["diets"] and a & ANIMAL: violations.append((text, d["name"], "animal product"))
            if "pescatarian" in p["diets"] and "meat" in a: violations.append((text, d["name"], "meat"))
            if "jain" in p["diets"] and a & {"meat", "fish", "shellfish", "egg", "root"}: violations.append((text, d["name"], "jain"))
            for al in p["allergens"]:
                if al in a: violations.append((text, d["name"], al))
            for w in p["avoid"]:
                if w in d["name"].lower() or any(w in i for i in d["ingredients"]): violations.append((text, d["name"], w))
    for t in M.MEAL_TYPES:
        if plan["sizes"][t] == 0:
            empties.append((text, t))
print(f"checked {n} restriction combinations x 7 days x 4 meals")
check("safety: no planned dish ever contains something you excluded", not violations, violations[:3])
check("coverage: extreme combinations that empty a meal type always come with a warning",
      all(any(t in w for w in M.build_plan(P.normalize(restrictions=txt), 3)["warnings"]) for txt, t in empties), empties[:3])
normal = [e for e in empties if "no tomato, no rice" not in e[0]]
check("coverage: every meal type keeps at least one dish for all realistic combinations", not normal, normal[:5])
sizes = {}
for diet, allergy in itertools.product(DIETS, ALLERGEN_WORDS):
    p = P.normalize(restrictions=", ".join(x for x in (diet, allergy) if x))
    for t in M.MEAL_TYPES:
        sizes[(diet, allergy, t)] = sum(1 for d in M.eligible(p) if d["type"] == t)
thin = sorted(((v, k) for k, v in sizes.items() if v < 3))[:6]
print("thinnest pools (dishes available):", thin)
check("coverage: no common restriction leaves fewer than 2 dishes in a meal type", all(v >= 2 for v in sizes.values()), thin)

# ---- behaviour ----
base = P.normalize()
a, b = M.build_plan(base, 1, date(2026, 11, 16)), M.build_plan(base, 1, date(2026, 11, 16))
check("determinism: same profile and seed give the same week", M.plan_markdown(a, date(2026, 11, 16)) == M.plan_markdown(b, date(2026, 11, 16)))
check("shuffle: a new seed gives a different week", M.plan_markdown(M.build_plan(base, 2, date(2026, 11, 16)), date(2026, 11, 16)) != M.plan_markdown(a, date(2026, 11, 16)))
for t in ("breakfast", "lunch", "dinner", "snack"):
    names = [d[t]["name"] for d in a["days"]]
    check(f"variety: no {t} repeats in an unrestricted week", len(set(names)) == 7)
ind = M.build_plan(P.normalize(cuisines=["Indian"]), 1, date(2026, 11, 16))
check("cuisine: Indian preference makes most dinners Indian", sum(d["dinner"]["cuisine"] == "Indian" for d in ind["days"]) >= 4)
check("protein: lunch or dinner is protein-rich every day", all("protein" in d["lunch"]["tags"] or "protein" in d["dinner"]["tags"] for d in a["days"]))
nothing = M.build_plan(P.normalize(restrictions="vegan, no tomato, no rice, no beans, no tofu, no dal, no lentils, no chickpea, no oat, no banana, no apple, no potato, no corn, no spinach, no berries, no avocado, no mango, no cucumber, no carrot, no peanut"), 1)
check("empty pool: a warning appears instead of a crash", bool(nothing["warnings"]))
check("notes: an unknown avoid-word is reported honestly", any("zebra" in n for n in M.build_plan(P.normalize(restrictions="no zebra"), 1)["notes"]))
check("notes: unrecognized restriction text is reported", any("keto lifestyle" in n for n in M.build_plan(P.normalize(restrictions="keto lifestyle"), 1)["notes"]))
check("notes: allergy disclaimer is always present", all("cannot guarantee" in " ".join(M.build_plan(P.normalize(restrictions=r), 1)["notes"]) for r in ["", "vegan", "nut allergy"]))
sl = M.shopping_list(a)
check("shopping list: covers every ingredient used in the week", {i for items in sl.values() for i, _ in items} == {i for day in a["days"] for t in M.MEAL_TYPES for i in day[t]["ingredients"]})
check("shopping list: categories are valid", set(sl) <= {"produce", "protein", "dairy & eggs", "grains & bread", "pantry"})

# ---- cuisines are honored (a user picked three cuisines and saw Indian and American dishes) ----
CUIS = ["Indian", "Mediterranean", "East Asian", "Latin American", "Middle Eastern", "Italian", "Southeast Asian", "African / Caribbean", "American"]
thin = [(c, t) for c in CUIS for t in M.MEAL_TYPES if sum(1 for d in M.DISHES if d["cuisine"] == c and d["type"] == t) < 4]
check("menu depth: every cuisine has at least 4 dishes in every meal type", not thin, thin)
egg_thin = [(c, t) for c in CUIS for t in M.MEAL_TYPES if sum(1 for d in M.eligible(P.normalize(restrictions="egg allergy")) if d["cuisine"] == c and d["type"] == t) < 3]
check("menu depth: even egg-free, every cuisine has at least 3 dishes per meal type", not egg_thin, egg_thin)
bad = []
for prefs_ in ([c] for c in CUIS):
    for restr in ("", "egg allergy", "vegetarian", "vegan", "gluten free"):
        p_ = P.normalize(restrictions=restr, cuisines=prefs_)
        plan_ = M.build_plan(p_, 2, date(2026, 11, 16))
        pool_ = M.eligible(p_)
        for t in M.MEAL_TYPES:
            liked = [d for d in pool_ if d["type"] == t and (d["cuisine"] in prefs_ or d["cuisine"] == "Any")]
            got = sum(1 for day in plan_["days"] if day.get(t) and (day[t]["cuisine"] in prefs_ or day[t]["cuisine"] == "Any"))
            if got < min(7, len(liked)):
                bad.append((prefs_, restr, t, got, len(liked)))
check("cuisines: chosen cuisines are used first, as many slots as the menu allows", not bad, bad[:3])
p3 = P.normalize(restrictions="egg allergy", cuisines=["East Asian", "Middle Eastern", "African / Caribbean"])
plan3 = M.build_plan(p3, 0, date(2026, 11, 16))
check("cuisines: the reported case (egg-free, 3 cuisines) gives a plan fully in those cuisines", plan3["cuisine_match"] == (28, 28), str(plan3["cuisine_match"]))
check("cuisines: that plan has no dishes from other cuisines (neutral \"Any\" dishes are allowed)", all(d[t]["cuisine"] in p3["cuisines"] + ["Any"] for d in plan3["days"] for t in M.MEAL_TYPES))
check("cuisines: no warning when the menu is deep enough", not plan3["warnings"], plan3["warnings"])
one = M.build_plan(P.normalize(cuisines=["East Asian"]), 0, date(2026, 11, 16))
check("cuisines: with one cuisine it reports how many meals match", one["cuisine_match"] and one["cuisine_match"][0] >= 20, str(one["cuisine_match"]))
check("cuisines: no two days in a row have the same dish", all(one["days"][i][t] is not one["days"][i + 1][t] for i in range(6) for t in M.MEAL_TYPES))
print(f"\n{fails} failure(s)")
sys.exit(1 if fails else 0)
