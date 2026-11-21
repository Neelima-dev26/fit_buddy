"""FitBuddy: a fitness and wellness chatbot (Gradio + Hugging Face).

Flow per message: safety check -> intent router -> handler (code or RAG + LLM) -> update trackers.
"""
import os
import re
from datetime import date, datetime, timedelta

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")  # avoids a slow network check at startup


def log(msg):
    print(f"[FitBuddy] {msg}", flush=True)


log("Starting up. Loading libraries (the first start can take a minute)...")
import gradio as gr

import coach
import exercises
import llm
import meals
import planner
import rag
import recipes
import router
import safety
import trackers
import userprofile
import views

import sys

_REQUIRED = {
    "trackers": ["today_context", "last_24h", "parse_meal", "mood_insight", "habit_streak", "set_mood", "add_event"],
    "views": ["today_card", "plan_card", "progress_html", "progress_24h"],
    "rag": ["SEARCH_API"],
    "llm": ["stream_answer", "extract_log", "STYLE_HINTS"],
    "safety": ["LOW_INTAKE_MSG"],
    "router": ["route"],
}
_REQUIRED["llm"] = ["stream_answer", "extract_log", "STYLE_HINTS", "tidy", "TOKENS", "was_truncated", "LLM_API"]
_REQUIRED["router"] = ["route", "ROUTER_API"]
_REQUIRED.update({"userprofile": ["PROFILE_API"], "exercises": ["EXERCISES_API"], "planner": ["PLANNER_API"],
                  "meals": ["MEALS_API"], "coach": ["COACH_API"], "recipes": ["RECIPES_API"]})
_REQUIRED["views"] = ["today_card", "plan_card", "progress_html", "progress_24h", "plan_week_html", "meal_plan_html", "recipes_html", "exercises_html", "notes_html"]
_stale = [f"{m}.py" for m, names in _REQUIRED.items() if not all(hasattr(sys.modules[m], n) for n in names)]
for _mod, _name, _need in ((rag, "rag", 4), (router, "router", 5), (llm, "llm", 6), (meals, "meals", 2), (planner, "planner", 3),
                           (coach, "coach", 3), (exercises, "exercises", 2)):
    _ver = getattr(_mod, {"rag": "SEARCH_API", "router": "ROUTER_API", "llm": "LLM_API", "meals": "MEALS_API", "planner": "PLANNER_API",
                          "coach": "COACH_API", "exercises": "EXERCISES_API"}[_name], 0)
    if f"{_name}.py" not in _stale and _ver < _need:
        _stale.append(f"{_name}.py")
if _stale:
    raise SystemExit("\n[FitBuddy] These files are out of date: " + ", ".join(_stale) + ".\n"
                     "Copy ALL files from the latest FitBuddy_Code.zip into your project folder "
                     "(including the knowledge folder), then start the app again.\n")

log("Loading the knowledge base and search model (the first run downloads about 90 MB)...")
retriever = rag.Retriever("knowledge")
log(f"Search ready ({retriever.backend}, {len(retriever.chunks)} passages).")

WELCOME = ("Hi, I'm FitBuddy. Ask me about workouts, meal ideas, or wellness tips, or tell me about your day "
           "(for example \"slept 7 hours, drank 3 glasses of water, feeling good\") and I'll log it for you.")
GREETING = ("Hi! I'm FitBuddy. I can suggest a workout, share meal ideas or wellness tips, work out your BMI, "
            "and log your sleep, water, habits, and mood. What would you like to do?")
THANKS = "You're welcome! Anything else I can help with?"
HELP = ("Here's what I can do:\n\n- **Your plan:** say \"my weekly plan\" or \"3-day beginner plan with dumbbells\", then \"today's workout\"\n"
        "- **Adjust on the fly:** \"make it shorter\", \"I only have 15 minutes\", \"swap the lunges\", \"no equipment\"\n"
        "- **Meals:** \"meal plan for the week\", \"shopping list\", or \"vegetarian breakfast ideas\"\n"
        "- **Meal ideas and wellness tips:** try \"vegetarian breakfast ideas\" or \"tips for better sleep\"\n"
        "- **Tracking:** say \"slept 7 hours, drank 3 glasses of water\", \"I stretched\", \"ate biryani\", or \"I'm feeling tired\"\n"
        "- **Logging:** \"did my workout\" counts toward your week. BMI and weekly summary are also available.\n\n"
        "Fill in your profile on the left to get answers that fit you.")
CHAT_FALLBACK = ("Got it! I can build your workout, suggest meals (try **meal ideas**), or log your day. "
                 "What would you like to do?")
NOT_FOUND = ("I couldn't find that in my notes. I can help with workouts, meal ideas, wellness tips, BMI, and "
             "tracking sleep, water, habits, meals, and mood. Try \"Suggest a workout\".")
NOTES_INTRO = "The language model is switched off, so I can only show the most relevant note:"
SOURCE_ERROR = "I couldn't get an answer from the language model, so here is the most relevant note I have instead."
EQUIPMENT = ["Bodyweight only", "Dumbbells", "Resistance bands", "Gym access"]
STYLES = ["Friendly", "Concise", "Motivational", "Detailed"]
MOOD_REPLY = {
    "Great": "Love to hear it!",
    "Good": "Glad you're doing well.",
    "Okay": "Thanks for checking in.",
    "Tired": "Sounds like a low-energy day. An easy walk or an early night might help.",
    "Stressed": "That sounds tough. A few slow breaths or a short walk can help.",
}
QUICK = ["Suggest a workout", "Quick 10-minute workout", "My weekly plan", "Meal plan for the week",
         "I drank a glass of water", "Meal ideas", "Wellness tip", "Weekly summary"]

_INTENT_QUERY = {
    "workout": "beginner workout plan exercises sets reps",
    "meal": "meal ideas breakfast lunch dinner snacks healthy eating",
    "wellness": "tips habits sleep stress",
}
_EQUIP_WORDS = {"Dumbbells": "dumbbell", "Resistance bands": "resistance band", "Bodyweight only": "bodyweight no equipment",
                "Gym access": "gym machines"}


def _expand_query(query, intent, equipment, restrictions=""):
    """Short plan-style requests like 'Suggest a workout' retrieve poorly, so add keywords for them.
    Specific questions ('how do I do a squat') are left alone. Returns (query, is_generic_request)."""
    q = query.lower()
    plan_like = intent == "meal" or len(q.split()) <= 4 or re.search(r"\b(plan|routine|workout|suggest|build|schedule|program|ideas?)\b", q)
    if not plan_like:
        return query, False
    extra = _INTENT_QUERY.get(intent, "")
    if intent == "workout":
        extra += " " + " ".join(_EQUIP_WORDS.get(e, "") for e in (equipment or []))
    if intent == "meal":
        extra += (" " + restrictions) * 2 if restrictions else ""  # e.g. "vegetarian" steers towards vegetarian ideas
    return f"{query} {extra}".strip(), True


def _pick_passages(state, intent, candidates, rotate):
    """For repeat requests ('Meal ideas' twice) prefer passages not shown yet; start over when all were shown."""
    if not rotate:
        return candidates[:3]
    seen = state.setdefault("seen", {}).setdefault(intent, [])
    fresh = [p for p in candidates if p["id"] not in seen]
    if not fresh:
        seen.clear()
        fresh = candidates
    return fresh[:3]


def _mark_seen(state, intent, passages):
    state.setdefault("seen", {}).setdefault(intent, []).extend(p["id"] for p in passages)


_FOLLOWUP = re.compile(r"^\s*(make|keep|swap|change|replace|shorter|longer|easier|harder|simpler|less|add|remove|without|instead)\b"
                       r"|\b(it|that|this|those|them)\b", re.I)
_MORE = re.compile(r"^\s*(more|another|different|other|again|something else|new)\b", re.I)


def _is_followup(message, state):
    """A short message that changes or asks about the previous answer ('make it shorter', 'swap the lunges')."""
    last = state.get("last_topic") or {}
    return last.get("intent") in ("workout", "meal", "wellness", "general") and len(message.split()) <= 9 and bool(_FOLLOWUP.search(message))


def _situation_hints(message, profile):
    """Turn cues like 'tired', 'sore', or '10 minutes' into instructions, like the 'adjust on the fly' in coaching apps."""
    t = message.lower()
    hints = []
    if re.search(r"\b(tired|exhausted|low[- ]energy|no energy|drained)\b", t):
        hints.append("They have low energy today: suggest a lighter, shorter, gentler option.")
    if re.search(r"\b(sore|stiff|achy)\b", t):
        hints.append("They are sore: suggest gentle, low-impact movement and recovery.")
    m = re.search(r"\b(\d{1,3})\s*[- ]?\s*(?:min|mins|minutes?)\b", t)
    if m:
        hints.append(f"Session length requested: {m.group(1)} minutes.")
    if re.search(r"\b(no equipment|bodyweight|hotel|travel|travelling|traveling)\b", t):
        hints.append("Use bodyweight-only exercises.")
    if re.search(r"\b(beginner|new to|never)\b", t):
        hints.append("Keep it very beginner friendly.")
    if (profile or {}).get("limits"):
        hints.append(f"Respect their limitation ({profile['limits']}): offer low-impact options and remind them to stop if it hurts.")
    return " ".join(hints)


_DISH_WORDS = re.compile(r"\b(breakfast|lunch|dinner|snack)s?\b")
_WANTS_DISHES = re.compile(r"\b(ideas?|suggest(ions)?|options|something|recipes?)\b|what (should|can|could) i (eat|cook|have|make)|"
                           r"^\s*(meal|breakfast|lunch|dinner|snack)s?\s*$|\bgive me\b|\bshow me\b", re.I)
_DETAIL = re.compile(r"\bdetails?\b|\bcues?\b|show (me )?everything|more detail|how do i do (these|them)")
_LLM_INTENTS = {"session": "session", "plan": "plan", "mealplan": "mealplan", "dishes": "meal", "recipe": "recipe",
                "workout_question": "workout", "wellness": "wellness", "summary": "summary", "chat": "chat"}


def _hour():
    return datetime.now().hour


_REPORT = re.compile(r"^\s*(?:(?:i|i'?ve|i'?m|just|today|so|and|then)\s+)*(?:did|had|went|ran|walked|swam|lifted|finished|completed|started|tried|got|made|"
                     r"cooked|skipped|missed|hit|crushed|smashed|squeezed|joined|took|played|danced|biked|hiked)\b", re.I)


def _is_report(message):
    """'I tried a new class and loved it': the user is telling us what they did, not asking a question."""
    t = message.strip()
    return "?" not in t and len(t.split()) <= 30 and bool(_REPORT.match(t))


def _is_statement(message):
    """A short remark such as 'love rice' (not a question and not a request)."""
    t = message.strip().lower()
    return "?" not in t and len(t.split()) <= 8 and not re.match(r"^(how|what|why|when|where|which|who|can|could|should|is|are|do|does|tell|explain|give|show)\b", t)


def _wants_dishes(message):
    t = message.lower()
    return not re.match(r"^\s*(how|why|is|are|does|do|can|could)\b", t) and bool(_WANTS_DISHES.search(t))


def _log_from_understanding(u):
    """Turn the validated model output into the same dict the rule-based parser produces."""
    out = {}
    if u.get("water_glasses"):
        out["water"] = u["water_glasses"]
    if u.get("sleep_hours"):
        out["sleep"] = u["sleep_hours"]
    if u.get("mood"):
        out["mood"] = u["mood"]
    if u.get("meal"):
        out["meal"] = u["meal"]
    if u.get("workout_done"):
        out["workout"] = True
    return out


def _sources_line(passages):
    names = []
    for p in passages:
        if p["source"] not in names:
            names.append(p["source"])
    if not names:
        return ""
    shown = ", ".join(names[:3]) + (f" +{len(names) - 3} more" if len(names) > 3 else "")
    return "\n\n_Sources: " + shown + "_"


def _snippet(text, max_words=45, query=""):
    """Short readable excerpt of a passage. Prefers the sentences that share words with the user's message;
    otherwise starts from the beginning. The title prefix is dropped."""
    body = text.split(". ", 1)[1] if ". " in text[:90] else text
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
    wanted = set(rag._tokens(query))
    scored = [(len(wanted & set(rag._tokens(s))), i) for i, s in enumerate(sentences)]
    if wanted and any(sc for sc, _ in scored):
        picked, words = [], 0
        for sc, i in sorted(scored, key=lambda x: (-x[0], x[1])):
            if sc == 0 or (picked and words + len(sentences[i].split()) > max_words):
                continue
            picked.append(i)
            words += len(sentences[i].split())
        if picked:
            return " ".join(sentences[i] for i in sorted(picked))
    words = body.split()
    if len(words) <= max_words:
        return body
    cut = " ".join(words[:max_words])
    end = max(cut.rfind(". "), cut.rfind("; "))
    return cut[:end + 1] if end > 20 else cut + "..."


def _profile(goal, level, equipment, days, minutes, limits, restrictions, age, style, cuisines=None):
    return {"goal": goal, "level": level, "equipment": equipment, "days": days, "minutes": minutes,
            "limits": (limits or "").strip(), "restrictions": (restrictions or "").strip(), "age": age, "style": style,
            "cuisines": [c for c in (cuisines or []) if c != "Any"]}


def _notes_reply(passages, intent, reason="", query=""):
    """Plain excerpt shown when no model is available (or it failed). The reason helps with debugging."""
    if intent == "chat":
        return CHAT_FALLBACK
    if not passages:
        return NOT_FOUND
    if reason == "loading":
        intro = "The language model is still loading, so here is the most relevant note:"
    else:
        intro = NOTES_INTRO if llm.NO_LLM else SOURCE_ERROR + (f" ({reason})" if reason else "")
    return intro + "\n\n" + _snippet(passages[0]["text"], 95 if intent in ("workout", "meal") else 60, query)


def _log_reply(parsed, state, profile, pn=None):
    bits = []
    if "sleep" in parsed:
        bits.append(f"{parsed['sleep']:g} h sleep")
    if "water" in parsed:
        bits.append(f"{parsed['water']:g} glass{'es' if parsed['water'] != 1 else ''} of water")
    if "habits" in parsed:
        bits.append(", ".join(parsed["habits"]))
    if "mood" in parsed:
        bits.append(f"mood {parsed['mood'].lower()}")
    if "meal" in parsed:
        bits.append(f"meal ({parsed['meal']})")
    if "workout" in parsed:
        bits.append(f"workout done ({parsed['workout']})" if isinstance(parsed["workout"], str) and parsed["workout"] else "workout done")
    reply = "Logged: " + ", ".join(bits) + "."
    if "water" in parsed:
        reply += f" ({int(state['water'].get(trackers.today(), 0))} of {trackers.WATER_GOAL} today)"
    if "habits" in parsed:
        streak = trackers.habit_streak(state)
        reply += f" {streak}-day streak, keep it going!" if streak >= 2 else " Nice start!"
    if "sleep" in parsed:
        minimum = 8 if profile.get("age") == "Under 18" else 7
        reply += (f" That's under {minimum} hours, so maybe go easier today." if parsed["sleep"] < minimum
                  else " Great, that's a healthy amount.")
    if "mood" in parsed:
        reply += " " + MOOD_REPLY[parsed["mood"]]
    if "meal" in parsed:
        n = len(trackers.day_log(state)["meals"])
        reply += f" That is meal {n} today."
        ahead = meals.rest_of_day(state["meal_plan"], date.today().weekday(), _hour()) if state.get("meal_plan") else []
        if ahead:
            reply += ("\n\n**Next up today:**\n\n" + "\n\n".join(f"{meals.ICONS[t]} **{t.capitalize()}** - {d['name']} ({d['minutes']} min)"
                                                                      for t, d in ahead)
                      + "\n\nSay **meal ideas** for other options.")
    if "workout" in parsed:
        done, planned = coach.workouts_summary(state)
        reply += f" Nice work! That is {done} of {planned} planned workouts this week." if planned else " Nice work!"
    return reply


LOADING_NOTE = "_The language model is still loading, so this is the quick version. It gets friendlier once the model is ready._"


def _present(history, view, message, passages, llm_profile, intent, extra, prefix, fallback):
    """Stream an answer into the chat when the language model is ready; otherwise show the deterministic fallback straight away.
    Never waits for the model to load. Returns the passages that were actually shown."""
    history.append({"role": "assistant", "content": ""})
    yield view("", light=True)
    reason = ""
    if llm.available() and not llm.is_loaded():
        llm.start_loading()
        reason = "loading"
    if llm.available() and llm.is_loaded():
        msgs = llm.build_messages(message, passages, llm_profile, history[:-2], intent, extra)
        partial = ""
        try:
            for partial in llm.stream_answer(msgs, max_new_tokens=llm.TOKENS.get(intent, 240)):
                history[-1]["content"] = prefix + partial
                yield view("", light=True)
            partial = llm.tidy(partial, llm.was_truncated())
            history[-1]["content"] = prefix + partial + _sources_line(passages)
            return passages
        except Exception as e:
            log(f"Answer generation failed: {e}")
            reason = str(e)[:140]
    elif not reason:
        reason = (llm.last_error() or "")[:140]
    history[-1]["content"] = prefix + fallback(reason) + _sources_line(passages)
    return passages[:1]


def _present_card(history, view, message, passages, llm_profile, intent, extra, prefix, card):
    """The exact card or table appears immediately. When the language model is ready, its short personal sentence is
    written above it while you read. If the model is still loading, you just get the card (plus a small note)."""
    history.append({"role": "assistant", "content": prefix + card + _sources_line(passages)})
    yield view("", light=True)
    if llm.available() and not llm.is_loaded():
        llm.start_loading()
        history[-1]["content"] += "\n\n" + LOADING_NOTE
        return passages
    if llm.available() and llm.is_loaded():
        msgs = llm.build_messages(message, passages, llm_profile, history[:-2], intent, extra)
        partial = ""
        try:
            for partial in llm.stream_answer(msgs, max_new_tokens=llm.TOKENS.get(intent, 130)):
                history[-1]["content"] = prefix + partial + "\n\n" + card + _sources_line(passages)
                yield view("", light=True)
            intro = llm.tidy(partial, llm.was_truncated())
            history[-1]["content"] = prefix + (intro + "\n\n" if intro else "") + card + _sources_line(passages)
        except Exception as e:
            log(f"Answer generation failed: {e}")
            history[-1]["content"] = prefix + card + _sources_line(passages)
    return passages


def _structured_fallback(body):
    return lambda reason: body + (f"\n\n(The language model could not be used: {reason})" if reason and not llm.NO_LLM else "")


def respond(message, history, state, goal, level, equipment, days, minutes, limits, restrictions, age, style, cuisines,
            height, weight, habits):
    message = (message or "").strip()
    history = list(history or [])

    def view(textbox="", light=False):
        if light:   # while text is streaming only the chat changes, so skip re-rendering the other panels
            return (history, state, gr.update(), gr.update(), textbox, gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update())
        return (history, state, views.today_card(state), gr.update(value=trackers.habits_today(state)), textbox,
                views.progress_html(state), views.streak_note(state), gr.update(value=trackers.mood_today(state)),
                views.plan_card(state), views.plan_week_html(state), views.meal_plan_html(state))

    if not message:
        yield view("")
        return

    profile = _profile(goal, level, equipment, days, minutes, limits, restrictions, age, style, cuisines)
    pn = userprofile.normalize(goal, level, equipment, days, minutes, limits, restrictions, age, style, cuisines)
    coach.sync(state, pn)   # plans always match the current preferences
    state["profile"] = profile
    history.append({"role": "user", "content": message})

    # 1. Safety check (code, before any model)
    hit = safety.check(message)
    if hit:
        history.append({"role": "assistant", "content": hit[1]})
        yield view("")
        return

    # 2. Route
    intent = router.route(message)
    if intent in ("workout", "general", "wellness") and trackers.reports_workout(message):
        intent = "log"   # "did a 45 minute dumbbell workout" is a log, not a question about workouts
    lead = ""  # text placed before an answer (e.g. a logged mood)
    llm_parsed, llm_minutes, llm_dishes = {}, None, False

    # 2b. The rules did not recognize it: let the language model work out what was meant (validated in code)
    if llm.available() and len(message.split()) <= 25 and (intent == "general" or (intent in ("workout", "meal", "wellness") and _is_statement(message))):
        u = None
        if llm.is_loaded():
            u = llm.understand(message)
        else:
            llm.start_loading()   # never wait: the rules and the notes answer until the model is ready
        if u:
            log(f"Model understood: {u['intent']}")
            if u["intent"] == "log":
                llm_parsed = _log_from_understanding(u)
                intent = "log" if llm_parsed else "chat"
            else:
                intent = _LLM_INTENTS[u["intent"]]
                llm_dishes = u["intent"] == "dishes"
                llm_minutes = u.get("minutes")

    # 3a. Logging
    parsed = llm_parsed or (trackers.parse_log(message) if intent == "log" else {})
    if not parsed and intent != "log" and trackers.looks_like_log(message) and llm.available() and llm.is_loaded():
        parsed = llm.extract_log(message)  # model fallback for messy sentences
    if parsed:
        if parsed.get("workout") is True:   # a plain "did my workout" means today's planned session
            s = coach.current_session(state)
            parsed["workout"] = s["title"] if s else "Workout"
        trackers.apply_log(state, parsed)
        reply = _log_reply(parsed, state, profile, pn)
        mood_only = set(parsed) == {"mood"}
        topic = router.route(message, ignore_log=True) if mood_only else "general"
        if mood_only and (topic in ("workout", "meal", "wellness", "session", "plan", "mealplan")
                          or trackers.MOOD_SCORE[parsed["mood"]] <= 2):
            # log the mood, then still answer what they asked (or offer gentle tips if they only shared a low mood)
            lead = reply + "\n\n"
            intent = topic if topic != "general" else "wellness"
        else:
            if llm.available() and any(k in parsed for k in ("meal", "mood", "workout")):
                extra = ("LOGGED: " + ", ".join(f"{k}={v}" for k, v in parsed.items()) + ". TODAY SO FAR: " + trackers.today_context(state)
                         + ". The details and what is next are shown below your reply.")
                yield from _present_card(history, view, message, [], profile, "logack", extra, "", reply)
            else:
                history.append({"role": "assistant", "content": reply})
            yield view("")
            return

    # 3a1. Looks like a sleep log we couldn't read, so ask instead of guessing
    if (intent not in ("log", "workout", "meal", "bmi", "summary", "session", "plan", "mealplan", "recall") and not parsed
            and re.search(r"\b\d+(\.\d+)?\s*(hours?|hrs?)\b", message.lower()) and "?" not in message):
        history.append({"role": "assistant", "content": "Did you want to log sleep? Try \"slept 8 hours\"."})
        yield view("")
        return

    # 3a2. Small talk (answered in code, no model needed)
    canned = {"greeting": GREETING, "thanks": THANKS, "help": HELP}.get(intent)
    if canned:
        history.append({"role": "assistant", "content": canned})
        yield view("")
        return

    # 3a3. "What did I eat today?": answered from your own log (personal memory, separate from the shared notes)
    if intent == "recall":
        yesterday = "yesterday" in message.lower()
        day = date.today() - timedelta(days=1 if yesterday else 0)
        history.append({"role": "assistant", "content": trackers.recall_markdown(state, day.isoformat(), "yesterday" if yesterday else "today")})
        yield view("")
        return

    # 3b. BMI (computed in code)
    if intent == "bmi":
        if age == "Under 18":
            reply = ("BMI for teens is interpreted with age and sex-specific charts, so it's best checked "
                     "with a doctor rather than a quick calculator.")
        else:
            h, w = trackers.parse_height_weight(message)
            h = h or (height if height else None)
            w = w or (weight if weight else None)
            reply = trackers.bmi_reply(h, w)
        history.append({"role": "assistant", "content": reply})
        yield view("")
        return

    # 3c. Plans, today's session, meals, and recipes: built by code from your preferences, then phrased by the model
    last = state.get("last_topic") or {}
    adjusting = (last.get("intent") == "session" and intent in ("general", "workout", "session") and len(message.split()) <= 9
                 and (_is_followup(message, state) or bool(coach.modes_from_message(message)) or bool(_DETAIL.search(message.lower()))))
    if adjusting:
        intent = "session"
    more_dishes = last.get("intent") == "dishes" and len(message.split()) <= 6 and bool(_MORE.search(message))
    if more_dishes:
        intent, message_for_dishes = "meal", last["query"]
    else:
        message_for_dishes = message
    want_dishes = intent == "meal" and (llm_dishes or more_dishes or _wants_dishes(message))
    if intent == "recipe":
        dish, allowed = meals.find_dish(message, pn)
        if dish is None:
            intent = "meal"   # no matching dish: answer from the notes instead
    if want_dishes:
        intent = "dishes"
    if intent in ("session", "plan", "mealplan", "dishes", "recipe"):
        passages, body, extra = [], "", ""
        if intent == "session":
            modes = coach.modes_from_message(message) + ([("short", llm_minutes)] if llm_minutes else [])
            detail = bool(_DETAIL.search(message.lower()))
            session, lead_txt, notes = coach.start_or_adjust(state, modes, reset=not adjusting)
            body = coach.session_reply(session, lead_txt, notes, pn, detail=detail)
            extra = ("TODAY'S SESSION CARD IS SHOWN SEPARATELY. Facts for your short reply: " + session["title"] + ", about " + str(session["est"])
                     + " min. WHY IT FITS: " + coach.why(pn, session) + ("\n" + lead_txt if lead_txt else ""))
            names = " ".join(b["name"] for b in session["blocks"][:3] if b["unit"] != "text")
            passages = retriever.search(names, k=2, category="form") if names else []
        elif intent == "plan":
            plan, ov = coach.plan_from_message(state, pn, message)
            body = "\U0001F4C5 **Your week**\n\n" + planner.week_markdown(plan) + "\n\n" + coach.why_short(plan["profile"])
            if ov:
                parts = [f"{ov['days']} days" if "days" in ov else "", f"{ov['minutes']} min" if "minutes" in ov else "",
                         ov.get("level", ""), ", ".join(ov.get("equipment", [])), ov.get("goal", "")]
                body += f"\n\nBuilt for this request ({', '.join(x for x in parts if x)}). Your saved profile is unchanged."
            body += "\n\nSay **today's workout** to see today's session."
            extra = "THE WEEK TABLE IS SHOWN SEPARATELY. Facts: " + coach.why(plan["profile"])
        elif intent == "mealplan":
            body, _ = coach.meal_reply(state, pn, message)
            extra = "THE MEAL INFORMATION IS SHOWN SEPARATELY. Facts: " + coach.why(pn).replace("Built from your choices", "Preferences")
        elif intent == "recipe":
            body = meals.recipe_markdown(dish, allowed)
            extra = "RECIPE (exact):\n" + body
        else:  # dishes
            mt = (_DISH_WORDS.search(message_for_dishes.lower()) or [None, None])[1]
            picks = meals.suggest(pn, mt, 5, seen=state.get("seen_dishes"), seed=state.get("meal_seed", 0))
            state["seen_dishes"] = (state.get("seen_dishes", []) + [d["name"] for d in picks])[-60:]
            if picks:
                body = (f"Here are {len(picks)} ideas that fit you:\n\n" + meals.suggestions_markdown(picks)
                        + "\n\nSay **recipe for** a dish to see how to make it, or **more ideas**.")
            else:
                body = "Nothing on my menu fits those restrictions yet. Try loosening one, or ask a dietitian for help."
            extra = "DISHES (shown separately): " + "; ".join(d["name"] for d in picks)
        ctx = trackers.today_context(state)
        if ctx:
            extra += f"\nTODAY SO FAR: {ctx}. Use it only if it helps."
        if intent in ("session", "plan", "mealplan", "dishes"):
            # the card or table is the deterministic part; the model adds a short, personal sentence above it
            yield from _present_card(history, view, message, passages, profile, intent, extra, lead, body)
        else:
            yield from _present(history, view, message, passages, profile, intent, extra, lead, _structured_fallback(body))
        state["last_topic"] = {"intent": "dishes" if intent == "dishes" else intent, "query": message_for_dishes, "ids": []}
        yield view("")
        return

    # 3d. Knowledge answers (workout questions, meal ideas, wellness, summary, general) from the notes
    extra = ""
    prefix = lead
    query = message
    if intent == "summary":
        stats = trackers.weekly_stats(state)
        prefix = trackers.format_stats(stats) + "\n\n"
        insight = trackers.mood_insight(state)
        if insight:
            prefix += insight + "\n\n"
        extra = "WEEKLY NUMBERS:\n" + trackers.format_stats(stats)
        query = "sleep hydration habits consistency tips"
    topical = intent in ("general", "workout", "meal", "wellness")
    want_more = (topical and (state.get("last_topic") or {}).get("intent") in ("workout", "meal", "wellness", "general")
                 and len(message.split()) <= 6 and bool(_MORE.search(message)))
    if want_more:  # "more ideas" / "another one": same topic, fresh notes
        intent, query = state["last_topic"]["intent"], state["last_topic"]["query"]
    followup = topical and not want_more and _is_followup(message, state)
    if followup:  # re-use the notes from the previous answer, plus anything new the message asks about
        last = state["last_topic"]
        intent = last["intent"] if intent == "general" else intent
        rotate = False
        passages = retriever.get(last["ids"]) + [p for p in retriever.search(message, k=2) if p["id"] not in last["ids"]]
        extra += "\nThe user wants to change your previous answer. Edit it as they ask and keep the same format."
    else:
        q_text, generic = _expand_query(query, intent, equipment, restrictions)
        rotate = generic and intent in ("meal", "workout", "wellness")
        found = retriever.search(q_text, k=12, category=intent, min_score=0.0) if rotate else retriever.search(q_text, k=3)
        passages = _pick_passages(state, intent, found, rotate)
    if intent == "general" and (not passages or _is_statement(message)):
        intent, passages = "chat", []   # a remark or nothing relevant in the notes: chat naturally instead of dumping a note
    if _is_report(message) and intent in ("workout", "meal", "wellness", "general"):
        intent, passages = "chat", []   # they are telling us what they did: reply as their coach, do not answer from the notes
        extra += ("\nThe user is telling you what they did. Reply as their coach in one or two sentences, in second person. "
                  "Never write as the user and never invent details about their activity.")
    ctx = trackers.today_context(state)
    if ctx:
        extra += (f"\nTODAY SO FAR: {ctx}. Use this only if it helps, don't just repeat it back, and never comment "
                  "on how much or what they ate.")
    hints = _situation_hints(message, profile)
    if hints:
        extra += "\nADJUST: " + hints
    if rotate:
        extra += "\nOffer different ideas from anything suggested earlier in this chat."

    shown = yield from _present(history, view, message, passages, profile, intent, extra, prefix,
                                lambda reason: _notes_reply(passages, intent, reason, message))
    if rotate and passages:
        _mark_seen(state, intent, shown)
    if not followup and passages and intent in ("workout", "meal", "wellness", "general"):
        state["last_topic"] = {"intent": intent, "query": query, "ids": [p["id"] for p in passages]}
    yield view("")


def on_habits(state, habits):
    trackers.set_habits(state, habits)
    return state, views.today_card(state), views.progress_html(state), views.streak_note(state)


def on_view(state, choice):
    state["view"] = "24h" if choice == "Last 24 hours" else "7d"
    return state, views.progress_html(state)


def on_mood(state, mood):
    trackers.set_mood(state, mood)
    return state, views.progress_html(state)


def export(state):
    return gr.update(value=trackers.export_log(state), visible=True)


# ---------- plan and meal panels: every preference change flows through coach.sync ----------
def _toast(text):
    return f'<div class="fb-toast">{text}</div>' if text else ""


def _panels(state, plan_msg=None, meal_msg=None):
    """Everything the plan and meal tabs show, plus a short message saying what just happened."""
    return (state, views.plan_card(state), views.plan_week_html(state), views.meal_plan_html(state),
            views.today_card(state), views.progress_html(state),
            _toast(plan_msg) if plan_msg is not None else gr.update(), _toast(meal_msg) if meal_msg is not None else gr.update())


def _pn(goal, level, equipment, days, minutes, limits, restrictions, age, style, cuisines):
    return userprofile.normalize(goal, level, equipment, days, minutes, limits, restrictions, age, style, cuisines)


def on_load(state, *prefs):
    coach.sync(state, _pn(*prefs))
    return _panels(state, "", "")


def on_profile(state, *prefs):
    changed = coach.sync(state, _pn(*prefs))
    return _panels(state, "Updated to match your preferences: " + ", ".join(changed) + "." if "workout plan" in changed else None,
                   "Meal plan updated to match your dietary needs and cuisines." if "meal plan" in changed else None)


def on_rebuild(state, *prefs):
    pn = _pn(*prefs)
    coach.sync(state, pn)
    _, msg = coach.rebuild(state, pn)
    return _panels(state, msg)


def on_done(state, *prefs):
    coach.sync(state, _pn(*prefs))
    if trackers.today() in state.get("workouts_done", {}):
        return _panels(state, "Today's workout is already marked as done.")
    title = coach.mark_done(state)
    done, planned = coach.workouts_summary(state)
    return _panels(state, f"Nice work! Marked \"{title}\" as done. That is {done} of {planned} workouts this week.")


_ADJUST_TEXT = {"easier": "Made today's session easier.", "short": "Shortened today's session.", "tired": "A lighter session for a low-energy day.",
                "bodyweight": "Switched today's session to bodyweight only."}


def on_adjust(mode, value, state, *prefs):
    coach.sync(state, _pn(*prefs))
    session, _, _ = coach.start_or_adjust(state, [(mode, value)])
    return _panels(state, f"{_ADJUST_TEXT.get(mode, 'Updated today.')} It is now about {session['est']} minutes. See Today's plan on the left.")


def on_new_meals(state, *prefs):
    pn = _pn(*prefs)
    coach.sync(state, pn)
    state["meal_seed"] = state.get("meal_seed", 0) + 1
    state["meal_plan"] = meals.build_plan(pn, state["meal_seed"])
    return _panels(state, None, f"New meal plan ready (shuffle {state['meal_seed']}).")


def _make_chatbot():
    welcome = [{"role": "assistant", "content": WELCOME}]
    for extra in (dict(type="messages", autoscroll=True, layout="bubble"),
                  dict(type="messages", autoscroll=True), dict(type="messages"), dict()):
        try:
            return gr.Chatbot(value=welcome, height=440, show_label=False, **extra)
        except TypeError:
            continue


def _on(component, event, *args, **kwargs):
    """Attach an event if this Gradio version has it (sliders use release, text boxes use blur)."""
    handler = getattr(component, event, None) or component.change
    return handler(*args, **kwargs)


def build_ui():
    blank = trackers.new_state()
    theme = gr.themes.Soft(primary_hue="teal", secondary_hue="blue", neutral_hue="slate")
    with gr.Blocks(theme=theme, css=views.CSS, title="FitBuddy") as demo:
        state = gr.State(trackers.new_state())
        gr.HTML(views.HEADER, elem_classes=["fb-flat"])
        model_status = gr.HTML(views.model_status_html(llm.status_text()), elem_classes=["fb-flat"])
        if hasattr(gr, "Timer"):   # refresh the status line every few seconds while the model loads
            timer = gr.Timer(4)
            timer.tick(lambda: views.model_status_html(llm.status_text()), None, model_status)
        with gr.Row():
            with gr.Column(scale=1, min_width=290, elem_classes=["fb-left"]):
                today = gr.HTML(views.today_card(blank), elem_classes=["fb-flat"])
                with gr.Group():
                    habits = gr.CheckboxGroup(trackers.HABITS, value=[], label="Habits today")
                    streak = gr.HTML(views.streak_note(blank), elem_classes=["fb-flat"])
                mood = gr.Radio(trackers.MOODS, value=None, label="How are you feeling today?")
                plan = gr.HTML(views.plan_card(blank), elem_classes=["fb-flat"])
                with gr.Accordion("Your preferences (they build your plan)", open=True):
                    goal = gr.Dropdown(userprofile.GOALS, value="General fitness", label="Goal")
                    level = gr.Dropdown(list(userprofile.LEVELS), value="Beginner", label="Experience")
                    equipment = gr.CheckboxGroup(userprofile.EQUIPMENT_CHOICES, value=["Bodyweight only"], label="Equipment")
                    days = gr.Slider(1, 7, value=3, step=1, label="Days per week")
                    minutes = gr.Slider(10, 90, value=30, step=5, label="Minutes per session")
                    limits = gr.Textbox(label="Limitations (optional)", placeholder="e.g. sore knees, bad back", lines=1)
                    restrictions = gr.Textbox(label="Dietary needs (optional)",
                                              placeholder="e.g. vegetarian, nut allergy, no mushrooms", lines=1)
                    cuisines = gr.CheckboxGroup(userprofile.CUISINE_CHOICES, value=["Any"], label="Cuisines you like")
                    age = gr.Dropdown(["Under 18", "18-29", "30-49", "50+"], value="18-29", label="Age range")
                    style = gr.Dropdown(STYLES, value="Friendly", label="Coaching style")
                    build_btn = gr.Button("Rebuild my plan", variant="primary")
                with gr.Accordion("Optional: BMI inputs", open=False):
                    height = gr.Number(label="Height (cm)", value=None)
                    weight = gr.Number(label="Weight (kg)", value=None)
                dl_btn = gr.Button("Download my log")
                dl_file = gr.File(label="Your log", interactive=False, visible=False)
            with gr.Column(scale=3):
                with gr.Tabs():
                    with gr.Tab("Chat"):
                        chat = _make_chatbot()
                        with gr.Row():
                            quick = [gr.Button(t, size="sm", elem_classes=["fb-chip"]) for t in QUICK[:4]]
                        with gr.Row():
                            quick += [gr.Button(t, size="sm", elem_classes=["fb-chip"]) for t in QUICK[4:]]
                        with gr.Row(equal_height=True):
                            msg = gr.Textbox(placeholder="Ask a question or log your day, e.g. slept 7 hours, feeling good",
                                             show_label=False, container=False, lines=1, scale=6, elem_classes=["fb-input"])
                            send = gr.Button("Send", variant="primary", scale=1, min_width=90)
                    with gr.Tab("My plan"):
                        with gr.Row():
                            done_btn = gr.Button("Mark today's workout done", variant="primary", size="sm")
                            easier_btn = gr.Button("Make today easier", size="sm")
                            short_btn = gr.Button("Only 15 minutes", size="sm")
                            tired_btn = gr.Button("I'm tired today", size="sm")
                            bw_btn = gr.Button("No equipment today", size="sm")
                        plan_status = gr.HTML("", elem_classes=["fb-flat"])
                        plan_week = gr.HTML(views.plan_week_html(blank), elem_classes=["fb-flat"])
                    with gr.Tab("Meals"):
                        new_meals_btn = gr.Button("Shuffle my meal plan", size="sm")
                        meal_status = gr.HTML("", elem_classes=["fb-flat"])
                        meal_week = gr.HTML(views.meal_plan_html(blank), elem_classes=["fb-flat"])
                    with gr.Tab("Library"):
                        gr.HTML(views.library_counts(retriever.chunks), elem_classes=["fb-flat"])
                        with gr.Tabs():
                            with gr.Tab("Recipes"):
                                with gr.Row():
                                    r_type = gr.Dropdown(["All", "Breakfast", "Lunch", "Dinner", "Snack"], value="All", label="Meal")
                                    r_cuis = gr.Dropdown(["All"] + userprofile.CUISINE_CHOICES[1:] + ["Any"], value="All", label="Cuisine")
                                    r_diet = gr.Dropdown(["Any"] + list(views.DIET_FILTERS), value="Any", label="Diet or allergy")
                                    r_text = gr.Textbox(label="Search", placeholder="e.g. dal, tofu, quick", lines=1)
                                r_html = gr.HTML(views.recipes_html(), elem_classes=["fb-flat"])
                            with gr.Tab("Exercises"):
                                with gr.Row():
                                    e_pat = gr.Dropdown(["All"] + list(views.PATTERN_NAMES.values()), value="All", label="Muscles")
                                    e_eq = gr.Dropdown(["All"] + list(views.EQUIP_NAMES.values()), value="All", label="Equipment")
                                    e_lvl = gr.Dropdown(["All"] + list(views.LEVEL_NAMES.values()), value="All", label="Level")
                                    e_text = gr.Textbox(label="Search", placeholder="e.g. knee, press", lines=1)
                                e_html = gr.HTML(views.exercises_html(), elem_classes=["fb-flat"])
                            with gr.Tab("Notes"):
                                with gr.Row():
                                    n_cat = gr.Dropdown(["All", "Workout", "Form", "Meal", "Wellness", "General"], value="All", label="Topic")
                                    n_text = gr.Textbox(label="Search", placeholder="e.g. sleep, protein", lines=1)
                                n_html = gr.HTML(views.notes_html(retriever.chunks), elem_classes=["fb-flat"])
                    with gr.Tab("Progress"):
                        view_mode = gr.Radio(["Last 7 days", "Last 24 hours"], value="Last 7 days", show_label=False)
                        progress = gr.HTML(views.progress_html(blank), elem_classes=["fb-flat"])

        inputs = [msg, chat, state, goal, level, equipment, days, minutes, limits, restrictions, age, style, cuisines,
                  height, weight, habits]
        outputs = [chat, state, today, habits, msg, progress, streak, mood, plan, plan_week, meal_week]
        msg.submit(respond, inputs, outputs)
        send.click(respond, inputs, outputs)
        for b in quick:
            b.click(lambda t=b.value: t, None, msg).then(respond, inputs, outputs)
        habits.input(on_habits, [state, habits], [state, today, progress, streak])
        mood.input(on_mood, [state, mood], [state, progress])
        view_mode.input(on_view, [state, view_mode], [state, progress])
        dl_btn.click(export, state, dl_file)

        # library filters
        rec_in = [r_type, r_cuis, r_diet, r_text]
        for comp in (r_type, r_cuis, r_diet):
            comp.change(views.recipes_html, rec_in, r_html)
        r_text.submit(views.recipes_html, rec_in, r_html)
        _on(r_text, "blur", views.recipes_html, rec_in, r_html)
        ex_in = [e_pat, e_eq, e_lvl, e_text]
        for comp in (e_pat, e_eq, e_lvl):
            comp.change(views.exercises_html, ex_in, e_html)
        e_text.submit(views.exercises_html, ex_in, e_html)
        _on(e_text, "blur", views.exercises_html, ex_in, e_html)
        note_fn = lambda cat, q: views.notes_html(retriever.chunks, cat, q)
        n_cat.change(note_fn, [n_cat, n_text], n_html)
        n_text.submit(note_fn, [n_cat, n_text], n_html)
        _on(n_text, "blur", note_fn, [n_cat, n_text], n_html)

        # preferences -> plans: every change rebuilds what depends on it, and the page loads with a plan ready
        prefs = [goal, level, equipment, days, minutes, limits, restrictions, age, style, cuisines]
        panels = [state, plan, plan_week, meal_week, today, progress, plan_status, meal_status]
        for comp in (goal, level, equipment, age, cuisines):
            comp.change(on_profile, [state] + prefs, panels)
        for comp in (days, minutes):
            _on(comp, "release", on_profile, [state] + prefs, panels)
        for comp in (limits, restrictions):
            _on(comp, "blur", on_profile, [state] + prefs, panels)
        build_btn.click(on_rebuild, [state] + prefs, panels)
        done_btn.click(on_done, [state] + prefs, panels)
        easier_btn.click(lambda st, *p: on_adjust("easier", None, st, *p), [state] + prefs, panels)
        short_btn.click(lambda st, *p: on_adjust("short", 15, st, *p), [state] + prefs, panels)
        tired_btn.click(lambda st, *p: on_adjust("tired", None, st, *p), [state] + prefs, panels)
        bw_btn.click(lambda st, *p: on_adjust("bodyweight", None, st, *p), [state] + prefs, panels)
        new_meals_btn.click(on_new_meals, [state] + prefs, panels)
        demo.load(on_load, [state] + prefs, panels)
    return demo


demo = build_ui()

if __name__ == "__main__":
    if not llm.NO_LLM:
        log("Loading the language model in the background. The first start downloads about 3 GB; FitBuddy works meanwhile.")
        llm.start_loading()
    log("Interface built. Launching... open the address below if your browser doesn't open by itself.")
    demo.queue().launch(inbrowser=True, show_error=True)
