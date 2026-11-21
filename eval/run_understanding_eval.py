"""Measures how well each approach understands free-form messages: rules only, language model only, and both together.

Usage:  python eval/run_understanding_eval.py Qwen/Qwen2.5-1.5B-Instruct   (add more model names to compare)
Writes eval/understanding_results.csv. With no model names it reports the rules-only baseline.
"""
import csv, json, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import llm, router

HERE = os.path.dirname(__file__)
CASES = json.load(open(os.path.join(HERE, "understanding_cases.json")))
FROM_RULES = {"log": "log", "session": "session", "plan": "plan", "mealplan": "mealplan", "recipe": "recipe", "meal": "dishes",
              "workout": "workout", "wellness": "wellness", "summary": "summary", "general": "chat", "greeting": "chat",
              "thanks": "chat", "help": "chat", "bmi": "chat"}
FROM_MODEL = {"log": "log", "session": "session", "plan": "plan", "mealplan": "mealplan", "recipe": "recipe", "dishes": "dishes",
              "workout_question": "workout", "wellness": "wellness", "summary": "summary", "chat": "chat"}


def _is_statement(message):
    t = message.strip().lower()
    return "?" not in t and len(t.split()) <= 8 and not re.match(r"^(how|what|why|when|where|which|who|can|could|should|is|are|do|does|tell|explain|give|show)\b", t)


def rules_category(message):
    r = router.route(message)
    if r == "general":   # the app answers questions from the notes and chats about remarks
        return "chat" if _is_statement(message) else "workout"
    return FROM_RULES.get(r, "chat")


def evaluate(understand=None, cases=CASES):
    """Returns (summary, rows). `understand(message)` should return the validated dict from llm.understand, or None."""
    rows = []
    for c in cases:
        rules = rules_category(c["m"])
        pred = hybrid = None
        if understand:
            u = understand(c["m"])
            pred = FROM_MODEL.get(u["intent"]) if u else None
            r = router.route(c["m"])
            consulted = r == "general" or (r in ("workout", "meal", "wellness") and _is_statement(c["m"]))   # as in the app
            hybrid = (pred or rules) if consulted else rules
        rows.append({"message": c["m"], "expected": c["c"], "rules": rules, "model_pred": pred, "hybrid": hybrid})
    n = len(rows)
    acc = lambda key: round(sum(r[key] == r["expected"] for r in rows) / n, 3)
    summary = {"cases": n, "rules_only": acc("rules")}
    if understand:
        summary.update({"model_only": acc("model_pred"), "rules_plus_model": acc("hybrid")})
    return summary, rows


if __name__ == "__main__":
    out = []
    summary, rows = evaluate(None)
    print("Rules only:", summary)
    for name in sys.argv[1:]:
        if not llm.load(name):
            print(f"Could not load {name}: {llm.last_error()}")
            continue
        summary, rows = evaluate(llm.understand)
        print(name, summary)
        out += [{"model": name, **r} for r in rows]
    if out:
        with open(os.path.join(HERE, "understanding_results.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["model", "message", "expected", "rules", "model_pred", "hybrid"])
            w.writeheader()
            w.writerows(out)
        print("Saved eval/understanding_results.csv")
