"""Tests for the chat flow (follow-ups, adaptive hints, mood + request). Runs without Gradio or a model.
Run with:  python tests/test_app_logic.py"""
import os
import sys
from unittest.mock import MagicMock

os.environ["FITBUDDY_NO_LLM"] = "1"
os.environ["FITBUDDY_NO_EMBED"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.modules["gradio"] = MagicMock()   # the interface itself is not needed for these checks
import app, coach, llm, planner, router, trackers, userprofile   # noqa: E402

fails = 0
def check(name, cond, detail=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if (detail and not cond) else ""))
    fails += 0 if cond else 1

PREFS = dict(goal="General fitness", level="Beginner", equipment=["Dumbbells"], days=3, minutes=30, limits="", restrictions="",
             age="18-29", style="Friendly", cuisines=["Any"])

def chat(messages, state=None, **kw):
    """Send messages through respond(); kw overrides the sidebar preferences. Returns (state, history)."""
    state = state if state is not None else trackers.new_state()
    hist = []
    prefs = {**PREFS, **kw}
    for m in messages:
        for out in app.respond(m, hist, state, prefs["goal"], prefs["level"], prefs["equipment"], prefs["days"], prefs["minutes"],
                               prefs["limits"], prefs["restrictions"], prefs["age"], prefs["style"], prefs["cuisines"], None, None, []):
            assert len(out) == 11, len(out)
        hist = out[0]
    return state, hist

def sources(reply):
    return reply.split("Sources: ")[1].split("\n")[0].strip("_") if "Sources: " in reply else ""

# --- situation hints ---
check("hints: tired", "low energy" in app._situation_hints("easy workout, I'm tired", {}))
check("hints: minutes", "10 minutes" in app._situation_hints("quick 10-minute workout", {}))
check("hints: sore", "sore" in app._situation_hints("my legs are sore", {}))
check("hints: no equipment", "bodyweight" in app._situation_hints("hotel room workout", {}))
check("hints: limitation from profile", "sore knees" in app._situation_hints("suggest a workout", {"limits": "sore knees"}))
check("hints: nothing to add", app._situation_hints("meal ideas", {}) == "")

# --- follow-up detection ---
st = {"last_topic": {"intent": "workout", "query": "Suggest a workout", "ids": [1]}}
for text, want in [("make it shorter", True), ("swap the lunges", True), ("can you make that easier", True), ("how long should I rest", False), ("how much water should I drink", False), ("why is that", True),
                   ("Suggest a workout", False), ("Meal ideas", False), ("how do I do a squat", False)]:
    check(f"follow-up: {text!r} -> {want}", app._is_followup(text, st) == want)
check("follow-up: needs a previous answer", app._is_followup("make it shorter", {}) is False)
check("more: 'more ideas' recognized", bool(app._MORE.search("more ideas")) and bool(app._MORE.search("another one")))

# --- full flows ---
state, hist = chat(["Meal ideas", "more ideas", "another one"])
replies = [m["content"] for m in hist if m["role"] == "assistant" and "ideas that fit you" in m["content"]]
dish_lines = [ln for r in replies for ln in r.split("\n") if "**" in ln and "min" in ln]
check("flow: 'Meal ideas' gives 5 dishes, and 'more ideas' gives new ones", len(replies) == 3 and len(set(dish_lines)) >= 12, str(len(set(dish_lines))))
state, hist = chat(["Suggest a workout", "make it shorter"])
check("flow: 'make it shorter' adjusts today's session", state["last_topic"]["intent"] == "session" and "adjusted" in hist[-1]["content"].lower() or "shorter" in hist[-1]["content"].lower())
state, hist = chat(["I'm tired, give me an easy workout"])
check("flow: mood logged AND the workout request answered", "Logged" in hist[-1]["content"] and "Warm-up" in hist[-1]["content"])
check("flow: mood saved as Tired", list(state["mood"].values()) == ["Tired"])
state, hist = chat(["I'm feeling great"])
check("flow: a good mood alone is just acknowledged", "Love to hear it" in hist[-1]["content"] and "Sources" not in hist[-1]["content"])
state, hist = chat(["I'm stressed and sleeping badly"])
check("flow: low mood alone still offers tips", "tough" in hist[-1]["content"] and "Sources:" in hist[-1]["content"])
check("router: ignore_log skips logging", router.route("I'm tired, give me an easy workout", ignore_log=True) == "session")

# --- preferences really drive plans (the original complaint: 'what does it do with gym access / 4 days?') ---
KNEE_MOVES = ("lunge", "leg press", "goblet", "step-up", "bodyweight squat", "split squat", "banded squat")
state, hist = chat(["my weekly plan"], days=4, equipment=["Gym access"], goal="General fitness")
plan = state["workout_plan"]
check("plan: 4 days a week gives 4 training days", sum(d["type"] != "REST" for d in plan["schedule"]) == 4)
check("plan: reply is a compact week table with rest days", hist[-1]["content"].count("| Rest ") == 3 and " Upper " in hist[-1]["content"] and "min" in hist[-1]["content"])
state, hist = chat(["Suggest a workout"], state=state, days=4, equipment=["Gym access"], limits="sore knees")
reply = hist[-1]["content"].lower()
# the planned strength sessions (not today's, which may be a rest or recovery day) must use the gym equipment
import planner as _planner
from datetime import date as _date
gym_text = " ".join(_planner.session_markdown(_planner.session_for(state["workout_plan"], i, _date(2026, 11, 16))).lower()
                    for i, d in enumerate(state["workout_plan"]["schedule"]) if d["type"] != "REST")
check("session: gym access uses machines", any(w in gym_text for w in ("machine", "cable", "lat pulldown", "leg curl", "dumbbell")))
check("session: sore knees removes knee-stressing moves", not any(w in reply for w in KNEE_MOVES), reply[:300])
check("session: the reply names which preferences it used", "built for" in reply and "gym access" in reply and "knee" in reply)
state, hist = chat(["Suggest a workout"], equipment=["Bodyweight only"], days=3, minutes=20)
check("session: bodyweight only uses no machines or dumbbells", not any(w in hist[-1]["content"].lower() for w in ("machine", "dumbbell", "cable", "band")))
s20 = coach.current_session(state)
check("session: 20 minutes fits about 20 minutes", s20 is None or s20["est"] <= 24)
state, hist = chat(["Give me a 3-day beginner plan with dumbbells"], days=5, equipment=["Gym access"])
check("plan: a request overrides the plan but not your saved profile", state["workout_plan"]["source"] == "chat"
      and sum(d["type"] != "REST" for d in state["workout_plan"]["schedule"]) == 3 and "unchanged" in hist[-1]["content"])
state, hist = chat(["hi"], state=state, days=2, equipment=["Gym access"])
check("plan: changing a preference rebuilds the plan", sum(d["type"] != "REST" for d in state["workout_plan"]["schedule"]) == 2 and state["workout_plan"]["source"] == "profile")
state, hist = chat(["my weekly plan"], days=3, limits="heart condition")
check("plan: a medical limitation gives a gentle plan with a doctor warning", "doctor" in hist[-1]["content"].lower()
      and all(d["type"] in ("CARDIO", "REC", "REST") for d in state["workout_plan"]["schedule"]))

# ---- adjusting on the fly ----
state, hist = chat(["Quick 10-minute workout"], minutes=40)
check("adjust: '10-minute workout' fits about 10 minutes", coach.current_session(state)["est"] <= 14)
state, hist = chat(["Suggest a workout", "only 15 minutes", "make it easier", "no equipment"], minutes=40, equipment=["Gym access"])
sess = coach.current_session(state)
check("adjust: changes compound (15 min, easier, no equipment)", sess["est"] <= 20 and all(b["id"] in {x["id"] for x in planner.X.EXERCISES if x["equip"] == "bw"} or b["unit"] == "text" for b in sess["blocks"]))
state, hist = chat(["Suggest a workout", "swap the press"], equipment=["Gym access"], days=7)
check("adjust: 'swap the press' reports what happened", "Swapped" in hist[-1]["content"] or "could not find" in hist[-1]["content"])
state, hist = chat(["Suggest a workout", "my legs are sore"], days=7)
check("adjust: sore turns it into recovery", coach.current_session(state)["type"] == "REC")
state, hist = chat(["Easy workout, low energy"], minutes=40)
check("adjust: low energy makes a shorter, lighter session", coach.current_session(state)["est"] < 40 and "adjusted" in hist[-1]["content"].lower())

# ---- tracking closes the loop ----
state, hist = chat(["Suggest a workout", "I did my workout"])
check("track: 'I did my workout' is counted this week", trackers.workouts_this_week(state) == 1 and "of" in hist[-1]["content"])
state, hist = chat(["I did my workout", "workout done"])
check("track: finishing twice in a day counts once", trackers.workouts_this_week(state) == 1 and len([e for e in state["events"] if e["kind"] == "workout"]) == 1)
check("track: the Today card shows workouts this week", "Workouts this week: 1 of" in app.views.today_card(state))
state, hist = chat(["hello"], state=state)
state2 = state
check("track: coach.mark_done works from a button too", coach.mark_done(trackers.new_state() if False else state2) and trackers.workouts_this_week(state2) == 1)

# ---- meals follow dietary needs ----
ANIMAL_WORDS = ("chicken", "salmon", "fish", "shrimp", "egg", "paneer", "cheese", "yogurt", "curd", "ghee", "tuna", "milk")
state, hist = chat(["meal plan for the week"], restrictions="vegan, nut allergy")
mp = state["meal_plan"]
dishes = [d[t] for d in mp["days"] for t in ("breakfast", "lunch", "dinner", "snack") if d.get(t)]
check("meals: vegan + nut allergy plan has no animal products or nuts", all(not (x["attrs"] & {"meat", "fish", "shellfish", "egg", "dairy", "honey", "peanut", "tree_nut"}) for x in dishes))
check("meals: the reply carries the allergy disclaimer", "cannot guarantee" in hist[-1]["content"])
first = mp["seed"]
state, hist = chat(["new meal plan please"], state=state, restrictions="vegan, nut allergy")
check("meals: 'new meal plan' reshuffles", state["meal_plan"]["seed"] == first + 1)
state, hist = chat(["shopping list"], state=state, restrictions="vegan, nut allergy")
check("meals: shopping list is shown", "Shopping list" in hist[-1]["content"] and "Produce" in hist[-1]["content"])
state, hist = chat(["meal plan"], restrictions="vegetarian")
check("meals: changing restrictions rebuilds the meal plan", state["pn"]["diets"] == ["vegetarian"])
check("meals: the meal tab shows restrictions applied", "vegetarian" in app.views.meal_plan_html(state))

# ---- the 'what does it do?' panel ----
state, hist = chat(["hi"], equipment=["Gym access"], days=4, limits="sore knees", restrictions="vegetarian, nut allergy")
page = app.views.plan_week_html(state)
check("panel: every preference is explained in the plan tab", all(w in page for w in ("Gym access", "sore knees", "vegetarian", "Days per week", "Machines and dumbbells")))


# ---- bigger, shorter, nicer replies ----
state, hist = chat(["Suggest a workout"], days=7, minutes=30)
check("format: a workout reply is a compact card (under 16 lines)", len([ln for ln in hist[-1]["content"].split("\n") if ln.strip()]) <= 16, hist[-1]["content"])
check("format: no coaching cues or rest times in the compact card", "(rest" not in hist[-1]["content"])
state, hist = chat(["Suggest a workout", "details"], days=7, minutes=30)
check("format: 'details' shows the full breakdown with times", "- **Warm-up (" in hist[-1]["content"] or "**Cool-down (" in hist[-1]["content"])
state, hist = chat(["Meal ideas"], restrictions="vegan, nut allergy")
shown = [ln for ln in hist[-1]["content"].split("\n") if "**" in ln and "min" in ln]
vegan_ok = {d["name"] for d in app.meals.eligible(userprofile.normalize(restrictions="vegan, nut allergy"))}
check("dishes: 'Meal ideas' shows 5 dishes that all fit vegan + nut allergy", len(shown) == 5 and all(any(n in ln for n in vegan_ok) for ln in shown), str(shown))
state, hist = chat(["breakfast ideas"])
check("dishes: 'breakfast ideas' shows only breakfasts", all(any(d["name"] in ln and d["type"] == "breakfast" for d in app.meals.DISHES) for ln in [l for l in hist[-1]["content"].split("\n") if "**" in l and "min" in l]))
state, hist = chat(["recipe for chicken biryani"], restrictions="vegetarian")
check("recipe: shows ingredients and method, and warns when the dish is excluded", "You need" in hist[-1]["content"] and "How:" in hist[-1]["content"] and "excluded" in hist[-1]["content"])
state, hist = chat(["how do I make dal"])
check("recipe: 'how do I make dal' finds a dal dish", "How:" in hist[-1]["content"] and "dal" in hist[-1]["content"].lower())
state, hist = chat(["meal prep for the week"], restrictions="vegetarian")
check("meal prep: gives a checklist built from the week's meals", "Meal prep checklist" in hist[-1]["content"] and "batch" in hist[-1]["content"].lower())
state, hist = chat(["love rice"])
check("chat: a statement the notes can't answer gets a friendly reply, not a dump", "Sources" not in hist[-1]["content"] and len(hist[-1]["content"]) < 300)

# ---- the language model understands free-form messages (simulated model, real validation) ----
class FakeModel:
    """Stands in for the language model so the understanding and card paths can be tested without a download."""
    def __init__(self, table):
        self.table, self.saved = table, {}
    def __enter__(self):
        for n in ("available", "is_loaded", "load", "understand", "stream_answer", "was_truncated", "start_loading"):
            self.saved[n] = getattr(llm, n)
        llm.available, llm.is_loaded, llm.load, llm.start_loading = (lambda: True), (lambda: True), (lambda *a: True), (lambda *a: None)
        llm.understand = lambda m: llm.parse_understanding(self.table.get(m, ""))
        llm.stream_answer = lambda msgs, max_new_tokens=240, temperature=0.5: iter(["Nice one.", "Nice one. Here you go."])
        llm.was_truncated = lambda: False
        return self
    def __exit__(self, *a):
        for n, f in self.saved.items():
            setattr(llm, n, f)

J = lambda **k: __import__("json").dumps({"intent": "chat", "minutes": None, "mood": None, "water_glasses": None, "sleep_hours": None, "meal": None, "workout_done": False, **k})
table = {
    "love rice": J(intent="chat"),
    "wiped out after a rough night": J(intent="log", mood="Tired"),
    "had two bottles of water and a poha for breakfast": J(intent="log", water_glasses=4, meal="poha"),
    "I only have a quarter of an hour but want to move": J(intent="session", minutes=15),
    "what could I cook tonight": J(intent="dishes"),
    "nonsense": "garbage not json",
    "do something dangerous": J(intent="hack the planet"),
}
with FakeModel(table):
    state, hist = chat(["wiped out after a rough night"])
    check("model: 'wiped out after a rough night' is logged as a Tired mood", list(state["mood"].values()) == ["Tired"])
    state, hist = chat(["had two bottles of water and a poha for breakfast"])
    check("model: water and a meal are logged from one messy sentence", state["water"].get(trackers.today()) == 4 and any(e["value"] == "poha" for e in state["events"]))
    state, hist = chat(["I only have a quarter of an hour but want to move"], minutes=40)
    check("model: 'a quarter of an hour' becomes a 15-minute session", coach.current_session(state)["est"] <= 20)
    state, hist = chat(["what could I cook tonight"])
    check("model: 'what could I cook tonight' shows dish ideas", "ideas that fit you" in hist[-1]["content"])
    state, hist = chat(["love rice"])
    check("model: chat replies are written by the model", "Nice one" in hist[-1]["content"])
    state, hist = chat(["nonsense"])
    check("model: unparseable output falls back safely", hist[-1]["role"] == "assistant" and len(hist[-1]["content"]) > 0)
    state, hist = chat(["do something dangerous"])
    check("model: an unknown intent is ignored", state["mood"] == {} and state["water"] == {})
    state, hist = chat(["Suggest a workout"])
    check("model: a session reply is the model's sentence plus the exact card", hist[-1]["content"].startswith("Nice one") and "**Warm-up**" in hist[-1]["content"] or "Recover" in hist[-1]["content"])

# ---- the understanding evaluation harness works (with a simulated model) ----
import importlib.util
_spec = importlib.util.spec_from_file_location("ev", os.path.join(os.path.dirname(__file__), "..", "eval", "run_understanding_eval.py"))
ev = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ev)
base, rows = ev.evaluate(None)
check("eval: 40 labeled messages and a rules-only baseline", base["cases"] == 40 and 0.5 <= base["rules_only"] <= 1.0, str(base))
perfect = {c["m"]: c["c"] for c in ev.CASES}
rev = {v: k for k, v in ev.FROM_MODEL.items()}
oracle = lambda m: {"intent": rev[perfect[m]]}
summary, _ = ev.evaluate(oracle)
check("eval: a perfect model lifts the combined score above the rules, near 100%", summary["rules_plus_model"] >= 0.95 and summary["rules_plus_model"] > summary["rules_only"], str(summary))
summary, _ = ev.evaluate(lambda m: None)
check("eval: a model that fails changes nothing (falls back to the rules)", summary["rules_plus_model"] == summary["rules_only"])

# ---- the buttons really do something, and say what they did ----
def prefs(**kw):
    p = {**PREFS, **kw}
    return (p["goal"], p["level"], p["equipment"], p["days"], p["minutes"], p["limits"], p["restrictions"], p["age"], p["style"], p["cuisines"])

st = trackers.new_state()
out = app.on_load(st, *prefs(equipment=["Gym access"], days=4))
check("buttons: every handler returns the 8 outputs the screen expects", len(out) == 8)
before = coach._fingerprint(st["workout_plan"])
out = app.on_rebuild(st, *prefs(equipment=["Gym access"], days=4))
after = coach._fingerprint(st["workout_plan"])
check("rebuild: with a gym there are alternatives, so the exercises change", before != after and st["workout_plan"]["variant"] == 1)
check("rebuild: it tells you what happened", "fresh exercise picks" in str(out[6]) and "Week 1" in str(out[6]))
out2 = app.on_rebuild(st, *prefs(equipment=["Gym access"], days=4))
check("rebuild: pressing again keeps changing the picks", coach._fingerprint(st["workout_plan"]) != after)
st2 = trackers.new_state()
app.on_load(st2, *prefs(equipment=["Bodyweight only"], limits="sore knees, bad back, wrists", days=3))
out = app.on_rebuild(st2, *prefs(equipment=["Bodyweight only"], limits="sore knees, bad back, wrists", days=3))
check("rebuild: when nothing can change it says so honestly instead of staying silent", "stay the same" in str(out[6]) or "fresh exercise picks" in str(out[6]), str(out[6]))
out = app.on_done(st, *prefs(equipment=["Gym access"], days=7))
check("done: marks the workout and reports the weekly count", "Nice work" in str(out[6]) and trackers.workouts_this_week(st) == 1)
out = app.on_done(st, *prefs(equipment=["Gym access"], days=7))
check("done: pressing twice says it is already done", "already" in str(out[6]) and trackers.workouts_this_week(st) == 1)
out = app.on_adjust("short", 15, st, *prefs(equipment=["Gym access"], days=7))
check("adjust buttons: say what changed and the new length", "15" in str(out[6]) or "minutes" in str(out[6]))
sess = coach.current_session(st)
check("adjust buttons: the session really is shorter", sess["est"] <= 20)
seed = st.get("meal_seed", 0)
out = app.on_new_meals(st, *prefs(equipment=["Gym access"], days=7))
check("meal shuffle: new plan and a message in the Meals tab", st["meal_seed"] == seed + 1 and "shuffle" in str(out[7]))
out = app.on_profile(st, *prefs(equipment=["Dumbbells"], days=2))
check("profile change: the plan rebuilds and says so", sum(d["type"] != "REST" for d in st["workout_plan"]["schedule"]) == 2 and "Updated" in str(out[6]))
out = app.on_profile(st, *prefs(equipment=["Dumbbells"], days=2))
check("profile change: no change means no message", "Updated" not in str(out[6]))


# ---- logs mean something: next-up, recall, today card, and the model's reply ----
app._hour = lambda: 12
state, hist = chat(["I ate a burger"], restrictions="vegetarian")
check("log: a meal reply says which meal of the day it was and what is planned next", "meal 1 today" in hist[-1]["content"] and "Next up today" in hist[-1]["content"] and "Dinner" in hist[-1]["content"])
check("log: it never comments on the food", not any(w in hist[-1]["content"].lower() for w in ("unhealthy", "healthy", "junk", "calorie", "bad", "guilt")))
app._hour = lambda: 22
state, hist = chat(["ate rice"])
check("log: late at night nothing more is planned, so no next-up list", "Next up" not in hist[-1]["content"])
app._hour = lambda: 12
import meals as _m
plan_ = _m.build_plan(userprofile.normalize(), 0)
check("next-up: before 11 shows lunch, dinner, snack", [t for t, _ in _m.rest_of_day(plan_, 0, 9)] == ["lunch", "dinner", "snack"])
check("next-up: midday shows dinner and snack", [t for t, _ in _m.rest_of_day(plan_, 0, 12)] == ["dinner", "snack"])
check("next-up: late evening shows nothing", _m.rest_of_day(plan_, 0, 22) == [])
state, hist = chat(["ate rice", "I ate a burger", "what did I eat today"])
check("recall: 'what did I eat today' lists what you logged", "burger" in hist[-1]["content"] and "rice" in hist[-1]["content"] and "Meals" in hist[-1]["content"])
state, hist = chat(["slept 7 hours, drank 3 glasses of water", "ate rice", "recap"])
check("recall: it also recalls water and sleep", "Water" in hist[-1]["content"] and "Sleep" in hist[-1]["content"])
state, hist = chat(["what did I eat yesterday"])
check("recall: an empty day says so kindly", "Nothing logged" in hist[-1]["content"])
check("today card: shows the meals you logged", "Meals logged today: rice" in app.views.today_card(chat(["ate rice"])[0]))
check("summary: weekly numbers count your meals", "2 meals logged" in trackers.format_stats(trackers.weekly_stats(chat(["ate rice", "ate pasta"])[0])))
calls = []
with FakeModel({}):
    orig = llm.stream_answer
    llm.stream_answer = lambda *a, **k: (calls.append(1), iter(["Thanks for logging that.", "Thanks for logging that. Dinner is next."]))[1]
    state, hist = chat(["I ate a burger"])
    check("model: a meal log gets a short model-written acknowledgement above the log card", hist[-1]["content"].startswith("Thanks for logging") and "Logged: meal (burger)" in hist[-1]["content"])
    n = len(calls)
    state, hist = chat(["drank 2 glasses of water"])
    check("model: a plain water log does not call the model (fast)", len(calls) == n and "Logged" in hist[-1]["content"])
    llm.stream_answer = orig


# ---- the screen never waits for the model ----
class LoadingModel:
    """A model that is available but still loading: any attempt to use it would be a bug."""
    def __enter__(self):
        self.saved = {n: getattr(llm, n) for n in ("available", "is_loaded", "start_loading", "stream_answer", "understand", "load")}
        self.started, self.used = [], []
        llm.available, llm.is_loaded = (lambda: True), (lambda: False)
        llm.start_loading = lambda *a: self.started.append(1)
        llm.stream_answer = lambda *a, **k: self.used.append("stream") or iter([""])
        llm.understand = lambda m: self.used.append("understand")
        llm.load = lambda *a: self.used.append("load") or False
        return self
    def __exit__(self, *a):
        for n, f in self.saved.items():
            setattr(llm, n, f)

def first_frames(message, **kw):
    state, hist, frames = trackers.new_state(), [], []
    prefs_ = {**PREFS, **kw}
    for out in app.respond(message, hist, state, prefs_["goal"], prefs_["level"], prefs_["equipment"], prefs_["days"], prefs_["minutes"],
                           prefs_["limits"], prefs_["restrictions"], prefs_["age"], prefs_["style"], prefs_["cuisines"], None, None, []):
        frames.append([m["content"] for m in out[0] if m["role"] == "assistant"][-1])
    return frames

with LoadingModel() as lm:
    frames = first_frames("Suggest a workout", days=7)
    check("loading: 'Suggest a workout' shows the card in the very first frame", any(w in frames[0] for w in ("Warm-up", "Cool-down", "Cardio", "Recovery")), frames[0][:120])
    check("loading: it never calls or waits for the model", lm.used == [] and lm.started, str(lm.used))
    check("loading: a small note explains the model is still loading", "still loading" in frames[-1])
    frames = first_frames("Meal ideas")
    check("loading: meal ideas also appear immediately", "ideas that fit you" in frames[0] and "still loading" in frames[-1])
    frames = first_frames("how do I do a squat")
    check("loading: a knowledge answer appears at once from the notes", len(frames[-1]) > 40 and "still loading" in frames[-1], frames[-1][:100])
    lm.used.clear()
    frames = first_frames("love rice")
    check("loading: a casual remark gets a quick friendly reply, with no waiting", lm.used == [] and len(frames[-1]) > 10, str(lm.used))
    lm.used.clear()
    frames = first_frames("I ate a burger")
    check("loading: logging works instantly while the model loads", "Logged: meal (burger)" in frames[0] and lm.used == [])

with FakeModel({}):
    frames = first_frames("Suggest a workout", days=7)
    card_first = next(f for f in frames if f)
    check("ready: the card is on screen first, and the model's sentence is added above it", any(w in card_first for w in ("Warm-up", "Cool-down", "Cardio", "Recovery"))
          and frames[-1].startswith("Nice one"))
check("status: the screen can say what the model is doing", all(isinstance(llm.status_text(), str) and "Language model" in llm.status_text() for _ in (0,)))


# ---- "did a 45 minutes dumbell workout" must be a log, never a question answered from the notes ----
for good in ["did a 45 minutes dumbell workout", "I did a 45 minute dumbbell workout", "finished a 30 min run", "just did legs at the gym",
             "completed 45 minutes of dumbbells", "went for a 20 minute jog", "hit the gym for an hour", "crushed a HIIT class"]:
    check(f"workout report is recognized: {good!r}", bool(trackers.reports_workout(good)))
for bad in ["how do I do a dumbbell workout", "what is a good 45 minute workout", "did you finish the workout?", "I didn't do my workout",
            "I want to do a 45 minute workout", "should I finish my workout", "going to do a workout later", "I haven't finished my workout", "suggest a workout"]:
    check(f"not a report: {bad!r}", not trackers.reports_workout(bad))
check("titles carry the minutes and the type", trackers.reports_workout("did a 45 minutes dumbell workout") == "45 min dumbbell workout")
state, hist = chat(["did a 45 minutes dumbell workout"])
check("report: it is logged with what you actually did", "Logged:" in hist[-1]["content"] and "45 min dumbbell workout" in hist[-1]["content"])
check("report: it is not answered from the notes", "Sources" not in hist[-1]["content"] and "Today, I completed" not in hist[-1]["content"])
check("report: it counts as today's workout", trackers.workouts_this_week(state) == 1 and "45 min dumbbell workout" in str(state["workouts_done"].values()))
with FakeModel({"did a 45 minutes dumbell workout": {"intent": "workout_question", "minutes": None, "mood": None, "water_glasses": None,
                                                   "sleep_hours": None, "meal": None, "workout_done": False}}):
    state, hist = chat(["did a 45 minutes dumbell workout"])
    check("report: logged even if the model misreads it as a question", "Logged:" in hist[-1]["content"] and trackers.workouts_this_week(state) == 1)
with FakeModel({}):
    state, hist = chat(["I tried a new yoga class and loved it"])
    check("report: a statement about what you did is never answered from the notes", "Sources" not in hist[-1]["content"])
check("prompt: the coach never writes as the user", "Never write as the user" in llm.SYSTEM_PROMPT)
check("prompt: the understanding step has a workout-report example", "45 minute dumbbell workout" in llm.UNDERSTAND_SYSTEM)

# ---- library ----
state, hist = chat(["hi"])
check("library: counts reflect the real size", f"{len(app.meals.DISHES)} dishes" in app.views.library_counts(app.retriever.chunks) and f"{len(app.exercises.EXERCISES)} exercises" in app.views.library_counts(app.retriever.chunks))
veg = app.views.recipes_html("All", "All", "Vegan", "")
check("library: the vegan filter shows no animal products", not any(w in veg.lower() for w in ("chicken", "salmon", "paneer", "yogurt", "egg ", "cheese")), "")
check("library: recipes show methods", "Simmer" in app.views.recipes_html("Dinner", "Indian", "Any", "chana") or "Simmer" in app.views.recipes_html("All", "All", "Any", "dal"))
check("library: exercises filter by equipment", app.views.exercises_html("All", "Gym machine", "All", "").count("fb-item") == len([e for e in app.exercises.EXERCISES if e["equip"] == "gym"]))
check("library: notes can be searched", "sleep" in app.views.notes_html(app.retriever.chunks, "All", "sleep").lower())

# --- answer cleanup and token budgets ---
check("tidy: removes role labels and [1] markers", llm.tidy("Assistant: Try squats [1].") == "Try squats.")
check("tidy: trims a cut-off sentence", llm.tidy("Do squats. Then do lunges. Then plan to rest and also dr", truncated=True).endswith("lunges."))
check("tidy: keeps complete bullet lists", llm.tidy("- **Plank** - 20 seconds", truncated=False) == "- **Plank** - 20 seconds")
check("tokens: workout gets the biggest budget", llm.TOKENS["workout"] > llm.TOKENS["general"])
msgs = llm.build_messages("q", [{"text": "Note."}], {"style": "Friendly"}, [], "meal", "ADJUST: x")
check("prompt: persona, format example, and hints all present",
      "warm, encouraging" in msgs[0]["content"] and "EXAMPLE OF THE STYLE" in msgs[-1]["content"] and "ADJUST: x" in msgs[-1]["content"])
print(f"\n{fails} failure(s)")
sys.exit(1 if fails else 0)
