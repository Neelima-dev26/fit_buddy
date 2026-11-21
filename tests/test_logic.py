"""Run with:  python tests/test_logic.py   (no model or Gradio needed)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import safety, router, trackers, rag

fails = 0
def check(name, cond, detail=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if (detail and not cond) else ""))
    fails += 0 if cond else 1

# --- safety ---
for text, cat in [("I have chest pain when I run", "emergency"), ("I want to kill myself", "self_harm"),
                  ("I've been purging after meals", "eating_disorder"), ("how do I lose 15 pounds in a week", "extreme_diet"),
                  ("is a 800 calories a day diet ok", "extreme_diet"), ("I'm pregnant, can I do squats", "medical"),
                  ("I tore my ACL last year", "medical"), ("I sprained my ankle", "medical"), ("ate nothing today", "low_intake"), ("I haven't eaten since yesterday", "low_intake")]:
    got = safety.check(text)
    check(f"safety: {text!r} -> {cat}", (got[0] if got else None) == cat)
for text in ["ate biryani", "I skipped breakfast", "Suggest a 30 minute workout", "how many glasses of water should I drink", "lose 1 pound in a week is that ok",
             "I need a stretching routine", "Slept 6 hours, drank 2 glasses of water"]:
    check(f"safety: no flag for {text!r}", safety.check(text) is None)

# --- parsing / routing ---
p = trackers.parse_log("Slept 6.5 hours, drank 2 glasses of water")
check("log: sleep+water parsed", p == {"sleep": 6.5, "water": 2})
check("log: bottle = 2 glasses", trackers.parse_log("I drank a bottle of water").get("water") == 2)
check("log: habits", trackers.parse_log("I stretched and went for a walk").get("habits") == ["Stretch", "10-minute walk"])
for q in ["how many hours of sleep do I need", "Is 6 hours of sleep enough?", "should I drink 8 glasses of water", "how do I stretch my back"]:
    check(f"log: not a log -> {q!r}", trackers.parse_log(q) == {})
check("log: question after log kept", trackers.parse_log("slept 5 hours, is that enough?").get("sleep") == 5)
for text, intent in [("Suggest a workout", "session"), ("Meal ideas", "meal"), ("Weekly summary", "summary"),
                     ("Calculate my BMI", "bmi"), ("Give me sleep tips", "wellness"), ("slept 7 hours", "log"),
                     ("hello there", "greeting"), ("tell me a joke", "general"), ("hi", "greeting"), ("Hey!", "greeting"), ("thanks!", "thanks"), ("what can you do", "help"), ("help", "help"), ("what is a good breakfast", "meal")]:
    check(f"route: {text!r} -> {intent}", router.route(text) == intent)

# --- BMI ---
h, w = trackers.parse_height_weight("I'm 5'10 and 170 lbs")
check("bmi: parse ft/lb", abs(h - 177.8) < 0.1 and abs(w - 77.1) < 0.1)
h, w = trackers.parse_height_weight("170 cm, 65 kg")
check("bmi: parse metric", h == 170 and w == 65)
check("bmi: value", abs(trackers.compute_bmi(170, 65) - 22.49) < 0.01)
check("bmi: asks for missing info", "need a height" in trackers.bmi_reply(None, 70))

# --- state / summary ---
s = trackers.new_state()
trackers.apply_log(s, {"water": 3, "sleep": 7}, day="2026-11-20")
trackers.apply_log(s, {"water": 2, "habits": ["Stretch"]}, day="2026-11-20")
trackers.apply_log(s, {"sleep": 5}, day="2026-11-19")
check("state: water accumulates", s["water"]["2026-11-20"] == 5)
st = trackers.weekly_stats(s, day="2026-11-20")
check("summary: avg sleep", st["avg_sleep"] == 6 and st["days_sleep"] == 2)
check("summary: habits counted", st["habit_total"] == 1)
check("sidebar: water text", "5 of 8" in trackers.water_md(s, "2026-11-20"))

# --- retrieval (TF-IDF backend; embeddings are used when sentence-transformers is installed) ---
r = rag.Retriever(os.path.join(os.path.dirname(__file__), "..", "knowledge"), prefer_embeddings=False)
for q, expect in [("how do I do a proper squat", "squat"), ("dumbbell workout for beginners", "dumbbell"),
                  ("how much sleep do I need", "Sleep"), ("vegetarian breakfast ideas", "meal"),
                  ("is BMI accurate", "BMI")]:
    res = r.search(q)
    check(f"rag: {q!r} -> {expect}", bool(res) and any(expect.lower() in x["source"].lower() for x in res))
check("rag: irrelevant query returns nothing", r.search("quantum chromodynamics lagrangian") == [])
check("rag: off-topic phrasing returns nothing", r.search("tell me about quantum physics") == [])
import views
s2 = trackers.new_state()
for d in ("2026-11-18", "2026-11-19", "2026-11-20"):
    trackers.apply_log(s2, {"habits": ["Stretch"]}, day=d)
check("streak: 3 days", trackers.habit_streak(s2, "2026-11-20") == 3)
check("streak: broken by a gap", trackers.habit_streak(s2, "2026-11-22") == 0)
check("streak: counts from yesterday if today empty", trackers.habit_streak(s2, "2026-11-21") == 3)
trackers.apply_log(s2, {"water": 4, "sleep": 6.5}, day="2026-11-20")
card = views.today_card(s2, "2026-11-20")
check("views: today card has 3 rings", card.count("fb-arc") == 3 and ">4<" in card and "6.5h" in card)
check("views: today card renders when empty", "fb-ring" in views.today_card(trackers.new_state()))
import coach, userprofile
_st = trackers.new_state()
coach.sync(_st, userprofile.normalize(limits="<script>alert(1)</script> knee"))
check("views: user text is escaped in the plan tab", "&lt;script&gt;" in views.plan_week_html(_st) and "<script>alert" not in views.plan_week_html(_st))
check("views: plan card empty state", "Choose your preferences" in views.plan_card(trackers.new_state()))
check("views: progress has 4 charts", views.progress_html(s2, "2026-11-20").count("fb-chart") == 4)
check("views: empty state renders", "fb-chart" in views.progress_html(trackers.new_state()))
# --- mood ---
for text, mood in [("I'm stressed and sleeping badly", "Stressed"), ("I\u2019m feeling tired today", "Tired"), ("feeling great", "Great"),
                   ("slept 7 hours, I feel good", "Good")]:
    check(f"mood: {text!r} -> {mood}", trackers.parse_log(text).get("mood") == mood)
for text in ["I'm good at squats", "I'm low on time", "how do I feel better", "I'm ok with dumbbells"]:
    check(f"mood: not a mood -> {text!r}", "mood" not in trackers.parse_log(text))
check("mood: routes as log", router.route("I'm feeling stressed") == "log")
s3 = trackers.new_state()
for d, sl, mo in [("2026-11-18", 8, "Great"), ("2026-11-19", 5, "Tired"), ("2026-11-20", 7.5, "Good")]:
    trackers.apply_log(s3, {"sleep": sl, "mood": mo}, day=d)
ins = trackers.mood_insight(s3, "2026-11-20")
check("mood: sleep-mood insight", ins is not None and "4.5/5" in ins and "2.0/5" in ins)
check("mood: no insight without data", trackers.mood_insight(trackers.new_state()) is None)
check("mood: weekly average", abs(trackers.weekly_stats(s3, "2026-11-20")["avg_mood"] - 3.67) < 0.01)
# --- number words and phrases ---
for text, want in [("slept about seven hours", {"sleep": 7}), ("downed a couple of glasses of water", {"water": 2}),
                   ("had two bottles of water and a poha for breakfast", {"water": 4, "meal": "poha"}), ("drank six glasses of water", {"water": 6})]:
    got = trackers.parse_log(text)
    check(f"words: {text!r}", all(got.get(k) == v for k, v in want.items()), str(got))
import userprofile
check("words: 'forty-five minutes' and 'four times a week' are read", userprofile.overrides_from_text("a plan for four times a week, forty-five minutes").get("days") == 4
      and userprofile.overrides_from_text("a plan for four times a week, forty-five minutes").get("minutes") == 45)
for text, intent in [("can you map out my training week", "plan"), ("I want a gym schedule four times a week", "plan"), ("I only have fifteen minutes", "session"),
                     ("what can I cook tonight", "meal"), ("what should I eat all week", "mealplan"), ("set up my meals for the week", "mealplan"),
                     ("recipe for paneer bhurji", "recipe"), ("how to cook rajma", "recipe"), ("meal prep for the week", "mealplan"),
                     ("can I do cardio and weights on the same day?", "workout")]:
    check(f"route: {text!r} -> {intent}", router.route(text) == intent, router.route(text))
# --- typos ---
for text, want in [("slpet for 8 hours", {"sleep": 8}), ("sleept 7 hours", {"sleep": 7}), ("I drnk 2 glases of water", {}),
                   ("I drank 2 glases of water", {"water": 2}), ("im tird", {"mood": "Tired"})]:
    got = trackers.parse_log(text)
    check(f"typo: {text!r}", all(got.get(k) == v for k, v in want.items()))
check("typo: 'should I drink 8 glasses' still not a log", trackers.parse_log("should I drink 8 glasses of water") == {})
check("typo: ordinary words untouched", trackers.parse_log("I'll drink 8 glasses tomorrow") == {})
full = views.today_card({"water": {"2026-11-20": 8}, "sleep": {}, "habits": {}, "mood": {}, "plan": None}, "2026-11-20")
check("views: completed ring shows a check mark", "&#10003;" in full)
check("views: card shows the date", "Fri, Nov 20" in full)
# --- meal log ---
from datetime import datetime
for text, want in [("ate biryani", "biryani"), ("I ate rice and dal for lunch", "rice and dal"), ("had pasta for dinner", "pasta"),
                   ("ate a sandwich today", "sandwich"), ("Ate biryani, slept 7 hours", "biryani"),
                   ("for lunch I had a salad", "salad"), ("ate biryani and slept 7 hours", "biryani")]:
    check(f"meal: {text!r} -> {want}", trackers.parse_log(text).get("meal") == want)
for text in ["ate nothing today", "what should I eat", "had a great workout", "ate well", "how much should I have eaten?", "I had 2 glasses of water"]:
    check(f"meal: not a meal -> {text!r}", "meal" not in trackers.parse_log(text))
check("meal: combined log keeps sleep", trackers.parse_log("ate biryani, slept 7 hours").get("sleep") == 7)
check("meal: routes as log", router.route("ate biryani") == "log")
s6 = trackers.new_state()
trackers.apply_log(s6, {"meal": "<b>biryani</b>"}, now=datetime(2026, 11, 20, 13, 0))
check("meal: shown in the 24h log, HTML escaped", "&lt;b&gt;biryani" in views.progress_24h(s6, datetime(2026, 11, 20, 20, 0)))
check("meal: counted in last_24h", trackers.last_24h(s6, datetime(2026, 11, 20, 20, 0))["meals"] == ["<b>biryani</b>"])
# --- last 24 hours ---
from datetime import datetime
s4 = trackers.new_state()
trackers.apply_log(s4, {"water": 2}, now=datetime(2026, 11, 19, 21, 0))   # 23 h before "now": inside the window
trackers.apply_log(s4, {"water": 5}, now=datetime(2026, 11, 19, 17, 0))   # 27 h before: outside
trackers.apply_log(s4, {"sleep": 7.5, "mood": "Good"}, now=datetime(2026, 11, 20, 7, 30))
trackers.apply_log(s4, {"habits": ["Stretch"]}, now=datetime(2026, 11, 20, 8, 0))
now = datetime(2026, 11, 20, 20, 0)
w = trackers.last_24h(s4, now)
check("24h: only counts the last 24 hours", w["water"] == 2 and w["sleep"] == 7.5 and w["mood"] == "Good" and w["habits"] == ["Stretch"])
check("24h: events are time-ordered", [e["ts"] for e in w["events"]] == sorted(e["ts"] for e in w["events"]))
trackers.set_habits(s4, [])
check("24h: unticking removes its event", trackers.last_24h(s4, now)["habits"] == [])
page = views.progress_24h(s4, now)
check("24h view: shows entries and yesterday label", "Yesterday 9:00 PM" in page and "Sleep 7.5 hours" in page and "7:30 AM" in page)
check("24h view: empty state", "Nothing logged" in views.progress_24h(trackers.new_state(), now))
s5 = trackers.new_state(); s5["view"] = "24h"
check("view switch: 24h uses the log", "Log, newest first" in views.progress_html(s5))
s5["view"] = "7d"
check("view switch: 7d uses the charts", views.progress_html(s5).count("fb-chart") == 4)
check("events: mood radio logs once", trackers.set_mood(s5, "Good") is s5 and len([e for e in s5["events"] if e["kind"] == "mood"]) == 1)
# --- larger knowledge base ---
import pathlib
kb = pathlib.Path(os.path.join(os.path.dirname(__file__), "..", "knowledge"))
stems = {p.stem for p in kb.glob("*.md")}
check("kb: at least 150 notes", len(stems) >= 150)
check("kb: every note is tagged with a category", all(c["categories"] for c in r.chunks))
check("kb: every note produces at least one passage", all(any(c["stem"] == s for c in r.chunks) for s in stems))
check("kb: tags are only workout, meal, wellness, form, or general", {x for c in r.chunks for x in c["categories"]} <= {"workout", "meal", "wellness", "general", "form"})
check("kb: at least 80 notes have a summary and keywords", sum(1 for p in kb.glob("*.md") if "Summary:" in p.read_text() and "Keywords:" in p.read_text()) >= 80)
for q, expect in [("how do I start running", "Running"), ("gluten free ideas", "Gluten"), ("I have a nut allergy", "allerg"),
                  ("balance exercises over 50", "over 50"), ("workouts for teenagers", "teenagers"), ("breathing exercise for stress", "Breathing"),
                  ("I missed a week of workouts", "Restarting"), ("hotel room workout", "traveling"), ("how to read food labels", "label"),
                  ("walking plan for beginners", "walking"), ("how to do a 15 minute home workout", "15-minute"), ("sore knees low impact", "Low-impact"),
                  ("meal prep for the week", "Meal prep"), ("mexican food ideas", "Mexican"), ("what snacks are healthy", "snack"),
                  ("how do I do a proper squat", "squat"), ("how do I do a push-up", "push-up"), ("what is DOMS", "glossary"),
                  ("is intermittent fasting good", "fasting"), ("ramadan eating tips", "Ramadan"), ("south indian breakfast", "South Indian"),
                  ("how much sleep do teens need", "Sleep"), ("workout when I am tired", "tired"), ("exercise when sick with a cold", "sick"),
                  ("what is the talk test for effort", "effort"), ("do I need supplements", "Supplements")]:
    res = r.search(q, k=3)
    check(f"kb search: {q!r} -> {expect}", any(expect.lower() in x["source"].lower() or expect.lower() in x["text"].lower()[:200] for x in res))
# --- topic-restricted rotation ---
for cat, q in [("workout", "beginner workout plan exercises sets reps"), ("meal", "meal ideas breakfast lunch dinner snacks"),
               ("wellness", "tips habits sleep stress")]:
    res = r.search(q, k=8, category=cat)
    check(f"rag: category {cat} returns only {cat} notes", len(res) >= 3 and all(cat in r.chunks[x["id"]]["categories"] for x in res))
check("rag: get() returns passages by id", [p["id"] for p in r.get([3, 5])] == [3, 5])
# --- generic requests ignore the relevance cutoff ---
many = r.search("zzz", k=8, category="meal", min_score=0.0)
check("rag: min_score=0 always returns enough notes to rotate", len(many) == 8 and r.search("zzz", k=8, category="meal") == [])
# --- variety and tracker context ---
cands = [{"id": i, "source": f"doc{i}", "text": "x"} for i in range(5)]
st = trackers.new_state()
first = [p["id"] for p in __import__("importlib").import_module("app")._pick_passages(st, "meal", cands, True)] if False else None
ctx_state = trackers.new_state()
trackers.apply_log(ctx_state, {"sleep": 6, "water": 3, "mood": "Tired", "meal": "biryani"})
ctx = trackers.today_context(ctx_state)
check("context: summarizes today", "slept 6 hours" in ctx and "3 of 8 glasses" in ctx and "mood tired" in ctx and "ate biryani" in ctx)
check("context: empty when nothing logged", trackers.today_context(trackers.new_state()) == "")
# --- coaching style reaches the prompt ---
import llm
msgs = llm.build_messages("q", [], {"style": "Concise"}, [], "workout")
check("style: hint in prompt", "as brief as possible" in msgs[-1]["content"])
print(f"\n{fails} failure(s)")
sys.exit(1 if fails else 0)
