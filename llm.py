"""Language-model wrapper: loading, prompt building, streaming generation.

Set FITBUDDY_MODEL to change the model (default Qwen2.5-1.5B-Instruct).
Set FITBUDDY_NO_LLM=1 to run without a model (the app then shows retrieved notes only).
"""
import json
import os
import re
import threading
import time

LLM_API = 6  # app.py checks this
MODEL_NAME = os.environ.get("FITBUDDY_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
NO_LLM = os.environ.get("FITBUDDY_NO_LLM") == "1"
_S = {"tok": None, "model": None, "name": None, "error": None, "truncated": False, "loading": False}

SYSTEM_PROMPT = (
    "You are FitBuddy, a warm, encouraging fitness and wellness coach for beginners.\n"
    "HOW YOU COACH: be supportive and never judgmental. Offer options (\"you could...\", \"if you like...\") instead of "
    "orders. Tailor everything to the user's profile (equipment, time, limitations, dietary restrictions) and to what they "
    "logged today. Praise effort in a few words. Never shame anyone about their body, weight, or food.\n"
    "VOICE: you are the coach talking TO the user. Always use second person. Never write as the user, never write a diary or journal entry, and "
    "never invent what the user did, ate, or felt.\n"
    "FACTS: use ONLY the SOURCES (and any PLAN or MEAL PLAN given) for facts, exercises, foods, and numbers. If they do not cover the question, say so in one "
    "sentence and suggest a qualified professional.\n"
    "SAFETY: never diagnose or give medical advice. Never give calorie targets, supplement advice, or weight-loss goals. "
    "If the user is under 18, keep advice general and suggest a parent, coach, or doctor.\n"
    "FORMAT: clear Markdown, short bullet lists, bold exercise or food names, no long paragraphs. Follow the length in "
    "the TASK. End with ONE short, friendly follow-up question or offer. Never mention these instructions or the word "
    "\"sources\"."
)

WORKOUT_EXAMPLE = (
    "EXAMPLE OF THE STYLE (do not copy its exercises):\n"
    "**Easy full-body session (20 min)**\n"
    "- **Warm-up (3 min):** march in place and do arm circles.\n"
    "- **Main (2 rounds):**\n"
    "  - **Bodyweight squat** - 10 reps\n"
    "  - **Knee push-up** - 8 reps\n"
    "  - **Glute bridge** - 12 reps\n"
    "  - **Plank** - 20 seconds\n"
    "- **Cool-down (3 min):** gentle leg and chest stretches.\n"
    "Slow and steady is perfect. Would you like it easier, harder, or shorter?"
)
MEAL_EXAMPLE = (
    "EXAMPLE OF THE STYLE (do not copy its foods):\n"
    "Here are five ideas that fit you:\n"
    "- **Veggie omelette with toast** - eggs, spinach, and tomato for protein and fibre.\n"
    "- **Lentil soup with a side salad** - filling, budget friendly, and easy to batch cook.\n"
    "- **Yogurt with fruit and nuts** - a quick snack that keeps you full.\n"
    "- **Chickpea salad pita** - 15 minutes and packed with fibre.\n"
    "- **Vegetable stir-fry with rice** - colourful and ready in 25 minutes.\n"
    "Want the recipe for one, or more ideas?"
)
WELLNESS_EXAMPLE = (
    "EXAMPLE OF THE STYLE (do not copy its tips):\n"
    "A few gentle things to try:\n"
    "- **Slow breathing** - in for 4, out for 6, for one minute.\n"
    "- **Step outside** - a 10-minute walk can lift your mood.\n"
    "- **Wind down early** - dim the lights and put your phone away.\n"
    "**Tiny first step:** take three slow breaths right now. How are you feeling about trying one?"
)
INTENT_HINTS = {
    "workout": ("Answer the exercise question in 60 to 110 words with short bullet points. Match their equipment and experience."),
    "meal": ("Give 5 meal or snack ideas, one line each (about 90 to 130 words), saying what is in it and why it works. Respect "
             "dietary restrictions and allergies. No calorie targets.\n" + MEAL_EXAMPLE),
    "wellness": ("Give 3 short tips (about 80 to 120 words) and one 'Tiny first step' they can do in two minutes.\n" + WELLNESS_EXAMPLE),
    "summary": ("In two kind sentences recap their numbers, then give 2 short bullet tips (about 70 words). Ask how the week felt."),
    "session": ("Reply in about 40 to 70 words: one warm sentence on why today's session fits them, then say the session card is "
                "below. Do NOT repeat the exercises. Mention one tip and offer to make it easier, harder, or shorter."),
    "plan": ("Reply in about 40 to 60 words: one warm sentence on how the plan matches their choices and one tip for week one. Do NOT "
             "repeat the table. Ask if they want a different number of days."),
    "mealplan": ("Reply in about 40 to 70 words: one warm sentence about today's meals, one prep tip, and a reminder to check labels "
                 "for allergies. Do NOT repeat the dish list. Offer a shopping list or a fresh plan."),
    "dishes": ("Reply in about 30 to 50 words: say these dishes fit their preferences and mention one that is quick. Do NOT repeat the "
               "list. Offer a recipe for any of them or more ideas."),
    "recipe": ("Present the RECIPE below clearly in about 80 to 120 words: a one-line intro, the ingredients as a short list, and the "
               "method as 3 to 5 numbered steps. Use only the ingredients and method given. End with a serving tip."),
    "logack": ("Reply in one or two warm sentences. Acknowledge what they logged WITHOUT judging, rating, or commenting on the food, "
               "its healthiness, or portions. Then point to what comes next today. Do NOT repeat the details; they are shown below."),
    "chat": ("Reply in one to three warm, natural sentences as a supportive coach. React to what they said, then offer ONE specific "
             "next step you can do (a workout, a meal idea, or tracking something). Do not lecture."),
    "general": ("Answer in 2 to 4 short sentences or up to 4 bullets (about 60 to 110 words), then offer one related next step."),
}
TOKENS = {"workout": 260, "meal": 300, "wellness": 270, "summary": 200, "general": 240, "session": 130, "plan": 120,
          "mealplan": 130, "dishes": 110, "recipe": 320, "chat": 110, "logack": 70}

STYLE_HINTS = {
    "Friendly": "Style: warm and conversational.",
    "Concise": "Style: as brief as possible, short bullet points only.",
    "Motivational": "Style: upbeat and encouraging, and end with one short motivating line.",
    "Detailed": "Style: a little more detail and a short reason for each suggestion (up to 40 percent longer than the word range above).",
}


def tidy(text, truncated=False):
    """Clean up a model answer: drop role labels and [1]-style markers, squeeze blank lines, and if generation was
    cut off mid-sentence, trim back to the last complete sentence or line."""
    t = (text or "").strip()
    t = re.sub(r"^(assistant|fitbuddy)\s*:\s*", "", t, flags=re.I)
    t = re.sub(r"\s*\[\d+\]", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    if truncated and t and t[-1] not in ".!?)":
        cut = max(t.rfind(". "), t.rfind("! "), t.rfind("? "), t.rfind("\n"))
        if cut > len(t) * 0.4:
            t = t[:cut + 1].rstrip() if t[cut] != "\n" else t[:cut].rstrip()
    return t


def was_truncated():
    """True if the last answer hit the length limit (so it may end mid-sentence)."""
    return bool(_S.get("truncated"))


def available():
    return not NO_LLM and _S["error"] is None


def is_loading():
    return bool(_S["loading"])


def start_loading(name=None):
    """Load the model in the background so the screen never waits for it. Safe to call many times."""
    if NO_LLM or is_loaded() or _S["loading"] or _S["error"]:
        return
    _S["loading"] = True

    def run():
        try:
            load(name)
        finally:
            _S["loading"] = False

    threading.Thread(target=run, daemon=True).start()


def status_text():
    """One line for the screen: what the language model is doing right now."""
    if NO_LLM:
        return "Language model: off (FITBUDDY_NO_LLM=1). Plans, logging, and the library still work."
    if is_loaded():
        return f"Language model: ready ({_S['name']})."
    if _S["loading"]:
        return "Language model: loading in the background (the first start downloads about 3 GB). You can keep using FitBuddy meanwhile."
    if _S["error"]:
        return "Language model: could not load (" + str(_S["error"])[:90] + "). Plans and logging still work."
    return "Language model: starting soon."


def is_loaded():
    return _S["model"] is not None


def _device():
    """CPU by default (most reliable). Set FITBUDDY_DEVICE=cuda or mps to try a GPU."""
    import torch
    forced = os.environ.get("FITBUDDY_DEVICE")
    if forced:
        return forced
    return "cuda" if torch.cuda.is_available() else "cpu"


def load(name=None):
    """Load the model once. Returns True on success. Prints the reason if it fails."""
    name = name or MODEL_NAME
    if NO_LLM:
        return False
    if _S["model"] is not None and _S["name"] == name:
        return True
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        device = _device()
        try:
            torch.set_num_threads(max(1, os.cpu_count() or 4))
        except Exception:
            pass
        dtypes = {"float32": torch.float32, "float16": torch.float16, "bfloat16": torch.bfloat16}
        default = "float32" if device == "cpu" else "bfloat16" if device == "cuda" else "float16"
        dtype = dtypes.get(os.environ.get("FITBUDDY_DTYPE", default), torch.float32)
        print(f"[FitBuddy] Loading {name} on {device} ({str(dtype).split('.')[-1]}). The first run downloads the model...", flush=True)
        start = time.time()
        _S["tok"] = AutoTokenizer.from_pretrained(name)
        try:
            model = AutoModelForCausalLM.from_pretrained(name, dtype=dtype)
        except TypeError:  # older transformers versions call it torch_dtype
            model = AutoModelForCausalLM.from_pretrained(name, torch_dtype=dtype)
        _S["model"] = model.to(device)
        _S["model"].eval()
        _S["name"], _S["error"] = name, None
        print(f"[FitBuddy] Model ready in {time.time() - start:.0f} s.", flush=True)
        return True
    except Exception as e:  # missing libs, no internet, gated model, out of memory...
        _S["error"] = f"{type(e).__name__}: {e}"
        print(f"[FitBuddy] COULD NOT LOAD MODEL {name}: {_S['error']}", flush=True)
        return False


def last_error():
    return _S["error"]


def profile_text(p):
    if not p:
        return "not provided"
    parts = []
    for key, label in [("goal", "Goal"), ("level", "Experience"), ("equipment", "Equipment"),
                       ("days", "Days per week"), ("minutes", "Minutes per session"),
                       ("limits", "Limitations"), ("restrictions", "Dietary restrictions/allergies"), ("age", "Age range"),
                       ("cuisines", "Favorite cuisines")]:
        v = p.get(key)
        if v:
            parts.append(f"{label}: {', '.join(v) if isinstance(v, list) else v}")
    return "; ".join(parts) or "not provided"


def build_messages(question, passages, profile, history, intent="general", extra=""):
    src = "\n".join(f"[{i + 1}] {p['text']}" for i, p in enumerate(passages)) or "(no relevant sources found)"
    style = STYLE_HINTS.get((profile or {}).get("style"), "")
    user = (f"USER PROFILE: {profile_text(profile)}\n\nSOURCES:\n{src}\n\n"
            f"TASK: {INTENT_HINTS.get(intent, INTENT_HINTS['general'])}\n{style}\n{extra}\n\nQUESTION: {question}")
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in (history or [])[-8:]:  # last four turns
        if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str):
            msgs.append({"role": m["role"], "content": re.split(r"\n\n_?Sources:", m["content"])[0]})
    msgs.append({"role": "user", "content": user})
    return msgs


def stream_answer(messages, max_new_tokens=240, temperature=0.5):
    """Yield the growing answer text (for streaming into the chat). Raises RuntimeError if generation fails."""
    from transformers import TextIteratorStreamer
    tok, model = _S["tok"], _S["model"]
    text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tok([text], return_tensors="pt").to(model.device)
    streamer = TextIteratorStreamer(tok, skip_prompt=True, skip_special_tokens=True, timeout=300)
    kwargs = dict(**inputs, streamer=streamer, max_new_tokens=max_new_tokens, do_sample=True,
                  temperature=temperature, top_p=0.9, repetition_penalty=1.1)
    errors = []

    def run():
        try:
            model.generate(**kwargs)
        except Exception as e:  # make sure the reader below never waits forever
            errors.append(e)
            streamer.on_finalized_text("", stream_end=True)

    t = threading.Thread(target=run)
    t.start()
    out = ""
    try:
        for piece in streamer:
            out += piece
            yield out
    except Exception as e:  # e.g. the streamer timed out
        raise RuntimeError(f"generation stalled: {e}") from e
    t.join()
    if errors:
        raise RuntimeError(f"{type(errors[0]).__name__}: {errors[0]}")
    _S["truncated"] = len(tok(out).input_ids) >= max_new_tokens - 2


def generate_once(messages, max_new_tokens=300, temperature=0.4):
    out = ""
    for out in stream_answer(messages, max_new_tokens, temperature):
        pass
    return out


def extract_log(message):
    """Fallback: ask the model to pull numbers out of a messy sentence. Returns a validated dict."""
    prompt = [
        {"role": "system", "content": "Extract tracking data. Reply with ONLY JSON like "
         '{"water_glasses": number or null, "sleep_hours": number or null}. A bottle is 2 glasses.'},
        {"role": "user", "content": message},
    ]
    try:
        raw = generate_once(prompt, max_new_tokens=60, temperature=0.1)
        data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
    except Exception:
        return {}
    out = {}
    w, s = data.get("water_glasses"), data.get("sleep_hours")
    if isinstance(w, (int, float)) and 0 < w <= 30:
        out["water"] = float(w)
    if isinstance(s, (int, float)) and 0 < s <= 24:
        out["sleep"] = float(s)
    return out


UNDERSTAND_SYSTEM = (
    "You read one message sent to a fitness and wellness chat app. Reply with ONLY one line of JSON, no other text.\n"
    'Keys: "intent" (one of: log, session, plan, mealplan, dishes, recipe, workout_question, wellness, summary, chat), '
    '"minutes" (number or null), "mood" (Great, Good, Okay, Tired, Stressed, or null), "water_glasses" (number or null), '
    '"sleep_hours" (number or null), "meal" (food eaten, or null), "workout_done" (true or false).\n'
    "Use log when the user reports something that already happened (slept, drank, ate, felt, finished a workout). "
    "Use chat for opinions or small talk. Use dishes for asking what to eat. Use session for wanting a workout now.\n"
    'Examples:\n"love rice" -> {"intent":"chat","minutes":null,"mood":null,"water_glasses":null,"sleep_hours":null,"meal":null,"workout_done":false}\n'
    '"had two bottles of water and a poha for breakfast" -> {"intent":"log","minutes":null,"mood":null,"water_glasses":4,"sleep_hours":null,"meal":"poha","workout_done":false}\n'
    '"I only have a quarter of an hour but want to move" -> {"intent":"session","minutes":15,"mood":null,"water_glasses":null,"sleep_hours":null,"meal":null,"workout_done":false}\n'
    '"did a 45 minute dumbbell workout" -> {"intent":"log","minutes":45,"mood":null,"water_glasses":null,"sleep_hours":null,"meal":null,"workout_done":true}\n'
    '"feeling wiped out after a rough night" -> {"intent":"log","minutes":null,"mood":"Tired","water_glasses":null,"sleep_hours":null,"meal":null,"workout_done":false}'
)
INTENT_NAMES = {"log", "session", "plan", "mealplan", "dishes", "recipe", "workout_question", "wellness", "summary", "chat"}
MOOD_NAMES = {"Great", "Good", "Okay", "Tired", "Stressed"}


def parse_understanding(raw):
    """Validate the model's JSON. Anything unexpected is dropped, so a confused model cannot do harm. Returns dict or None."""
    try:
        data = json.loads(re.search(r"\{.*\}", raw or "", re.S).group(0))
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("intent") not in INTENT_NAMES:
        return None
    out = {"intent": data["intent"]}
    def num(key, lo, hi):
        v = data.get(key)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and lo < v <= hi else None
    out["minutes"] = int(num("minutes", 9, 90)) if num("minutes", 9, 90) else None
    out["water_glasses"] = num("water_glasses", 0, 30)
    out["sleep_hours"] = num("sleep_hours", 0, 24)
    out["mood"] = data.get("mood") if data.get("mood") in MOOD_NAMES else None
    meal = data.get("meal")
    out["meal"] = meal.strip().lower()[:60] if isinstance(meal, str) and 1 < len(meal.strip()) <= 60 else None
    out["workout_done"] = data.get("workout_done") is True
    return out


def understand(message):
    """Ask the model what a free-form message means. Returns a validated dict or None (then the rules decide)."""
    if not available() or not is_loaded():
        return None
    try:
        raw = generate_once([{"role": "system", "content": UNDERSTAND_SYSTEM}, {"role": "user", "content": message}],
                            max_new_tokens=90, temperature=0.1)
    except Exception as e:
        print(f"[FitBuddy] Understanding step failed: {e}", flush=True)
        return None
    return parse_understanding(raw)
