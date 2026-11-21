"""Safety layer: code-level checks that run BEFORE the language model.

Small models can ignore prompt instructions, so red-flag topics are caught here
and answered with fixed, careful responses.
"""
import re

DISCLAIMER = "FitBuddy shares general information, not medical advice."

_SELF_HARM = [r"\bsuicid", r"kill myself", r"end my life", r"want to die", r"self[- ]?harm", r"hurt myself"]
_EMERGENCY = [r"chest (pain|pressure|tightness)", r"can'?t breathe", r"trouble breathing",
              r"short(ness)? of breath", r"\bfaint(ed|ing)?\b", r"passed out", r"heart attack",
              r"\bstroke\b", r"severe pain"]
_EATING = [r"\bpurg(e|ing)\b", r"\bbulimi", r"\banorexi", r"starv(e|ing) myself",
           r"make myself (throw up|vomit)", r"binge[- ]?eat"]
_LOW_INTAKE = [r"\b(ate|eaten) nothing", r"haven'?t (eaten|had anything to eat)", r"\bnot eating\b", r"can'?t eat\b",
               r"\bstopped eating\b", r"\bdon'?t (want to|feel like) eat"]
_MEDICAL = [r"\bpregnan", r"\bpostpartum", r"\bdiagnos", r"\bmedication", r"\binjur(y|ed|ies)\b",
            r"\b(sprain|sprained|strain|strained|fracture|fractured|tore|torn|acl|mcl|meniscus|herniat\w*|slipped disc|tendon|ligament)\b",
            r"\bdiabet", r"heart (condition|disease|problem)", r"high blood pressure|hypertension",
            r"\basthma\b", r"\bsurgery\b"]

SELF_HARM_MSG = ("I'm really sorry you're going through this. FitBuddy can't help with this, but you deserve "
                 "support right now. If you're in the US, you can call or text 988 (Suicide and Crisis Lifeline). "
                 "If you're elsewhere, please contact your local emergency number or a local crisis line. "
                 "If you might act on these thoughts, call emergency services now.")
EMERGENCY_MSG = ("That could be serious, and I can't assess it. If it's happening now or feels severe, stop "
                 "exercising and call your local emergency number. Otherwise, please talk to a doctor before "
                 "continuing with exercise.")
EATING_MSG = ("Thank you for telling me. I can't give food or exercise advice around this, and you deserve "
              "proper support. Please consider reaching out to a doctor or a mental health professional. In the "
              "US, the National Alliance for Eating Disorders has a helpline and resources at "
              "allianceforeatingdisorders.com. I'm happy to help with general sleep, stress, or movement topics "
              "whenever you'd like.")
LOW_INTAKE_MSG = ("Thanks for telling me. Regular meals support your energy and mood. If it's hard to eat, or this has "
                  "been going on for a while, it's worth talking to a doctor or a registered dietitian. Whenever you "
                  "feel ready, I'm happy to share simple, gentle meal ideas.")
EXTREME_MSG = ("I can't help with crash diets, very fast weight loss, or very low calorie targets, because they "
               "can be harmful. Gradual changes (regular movement, balanced meals, enough sleep) are safer. "
               "A doctor or registered dietitian can set personal goals with you. I'm glad to suggest general "
               "healthy meal ideas or a beginner workout instead.")
MEDICAL_MSG = ("That sounds like something to check with a doctor or physical therapist first, since the right "
               "exercise or food advice depends on your situation and I can't assess it. Once you have their "
               "go-ahead, I can share general beginner workout and wellness information.")


def _any(patterns, text):
    return any(re.search(p, text) for p in patterns)


def _extreme_diet(t):
    if re.search(r"crash diet|water fast|detox cleanse", t):
        return True
    m = re.search(r"lose\s+(\d+(?:\.\d+)?)\s*(pounds?|lbs?|kg|kilos?)\s*(?:in|within)\s*(a|one|\d+)\s*(day|days|week|weeks)", t)
    if m:
        amount = float(m.group(1))
        if m.group(2).startswith("kg") or m.group(2).startswith("kilo"):
            amount *= 2.2
        n = 1 if m.group(3) in ("a", "one") else float(m.group(3))
        weeks = n / 7 if m.group(4).startswith("day") else n
        if weeks > 0 and amount / weeks > 2:
            return True
    m = re.search(r"(\d{3,4})\s*calories?\s*(?:a|per|/)\s*day", t)
    if m and int(m.group(1)) < 1200:
        return True
    if re.search(r"(fast|fasting)\s+for\s+\d+\s+days", t):
        return True
    return False


def check(text):
    """Return (category, message) if a red flag is found, otherwise None."""
    t = (text or "").lower()
    if _any(_SELF_HARM, t):
        return "self_harm", SELF_HARM_MSG
    if _any(_EMERGENCY, t):
        return "emergency", EMERGENCY_MSG
    if _any(_EATING, t):
        return "eating_disorder", EATING_MSG
    if _extreme_diet(t):
        return "extreme_diet", EXTREME_MSG
    if _any(_LOW_INTAKE, t):
        return "low_intake", LOW_INTAKE_MSG
    if _any(_MEDICAL, t):
        return "medical", MEDICAL_MSG
    return None
