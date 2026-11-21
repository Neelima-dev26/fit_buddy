"""Intent router: simple rules first (fast, predictable). Falls back to 'general'."""
import re
import trackers
import userprofile

_RULES = [
    ("greeting", r"^\s*(hi|hello|hey|hiya|yo|good (morning|afternoon|evening))( there| buddy| fitbuddy)?\b[\s!.,?]*$"),
    ("thanks", r"^\s*(thanks|thank you|thx|ty)\b[\w\s!.,]*$"),
    ("help", r"what can you do|how does this work|who are you|what are you|^\s*help\s*[!?.]*$|how do i use"),
    ("summary", r"weekly summary|week summary|summary of my week|how('| i)?s my week|how was my week|my week so far|weekly recap"),
    ("bmi", r"\bbmi\b|body mass index"),
    ("recall", r"what (did|have|had) i (eat|eaten|ate|drink|drank|log|logged|do|done|had)\b|what i (ate|drank|logged)|\bmy log\b|"
               r"show my (log|day)|today'?s log|\brecap\b|what have i had"),
    ("recipe", r"\brecipes?\b|\bhow (do i|to|can i|would i) (make|cook|prepare)\b"),
    ("mealplan", r"meal\s*(plan|planner|prep)|batch cook|prep (my|the) (meals|week)|plan my meals|meals? for the (week|month)|"
                 r"what should i (eat|cook)[^?]*\bweek\b|set up my meals|weekly meals|\b(7|seven)[- ]day (meal|menu)|what should i (eat|cook) (this|next) week|"
                 r"shopping list|grocery list|groceries"),
    ("plan", r"\b(my|weekly|week|training|workout|exercise|fitness)\s+(plan|schedule|routine)\b|plan my week|"
             r"\b(map|lay|set)\s+(out|up)\b[^?]*\b(workouts?|training|week|schedule|routine)\b|\b(plan|schedule) my (workouts?|training)\b|"
             r"\b(plan|routine|schedule|program)\b[^?]*\b[1-7]\s*(?:days?|times)\b|"
             r"\b[1-7]\s*[- ]?\s*(?:days?|times)\b[^?]*\b(plan|routine|schedule|program)\b|\b(build|create|make|give|suggest)\b[^?]*\b(plan|schedule|routine)\b"),
    ("session", r"\b(only|just) (have|got)\b[^?]*\bminutes?\b|\bsomething (quick|short|easy|light)\b[^?]*\b(do|move|train|exercise)\b|"
                r"\b(suggest|give|show|make|need|want|do)\b[^?]*\b(workout|session)\b|"
                r"^\s*(a\s+|an\s+)?(quick|easy|short|light|gentle|full[- ]body|upper[- ]body|lower[- ]body|home|gym)\b[^?]*\b(workout|session)\b|"
                r"\b(workout|session)\s+(for\s+)?today\b|what should i do today|what'?s (my )?(workout|session|plan) today|"
                r"what (workout|exercise)s? (should|can) i do|today'?s (workout|session|plan)"),
    ("meal", r"\b(meal|meals|breakfast|lunch|dinner|snack|snacks|recipe|recipes|food|eat|eating|cook|cooking|hungry|nutrition|protein|diet)\b"),
    ("workout", r"\b(workout|workouts|exercise|exercises|routine|training|plan|squat|push-?ups?|plank|lunges?|cardio|stretch|stretching|gym|lift|lifting|run|running|walk|walking)\b"),
    ("wellness", r"\b(sleep|stress|stressed|relax|tired|energy|mood|habit|habits|hydrat\w*|water|wellness|tips?|motivation|motivated)\b"),
]


ROUTER_API = 5  # app.py checks this


def route(text, ignore_log=False):
    """Return one of: log, greeting, thanks, help, summary, bmi, recipe, mealplan, plan, session, meal, workout, wellness, general."""
    if not ignore_log and trackers.parse_log(text):
        return "log"
    t = userprofile.numwords_to_digits((text or "").lower())
    asking = bool(re.match(r"^\s*(how|why|is|are|does|can i|could i|what is|what's a|what are|what does)\b", t))
    for intent, pattern in _RULES:
        if intent in ("plan", "session") and asking and "what should i do today" not in t:
            continue
        if re.search(pattern, t):
            return intent
    return "general"
