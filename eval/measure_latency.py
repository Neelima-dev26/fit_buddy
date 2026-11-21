"""Measure how fast the language model is on THIS computer (research question RQ2).

Usage:  python eval/measure_latency.py Qwen/Qwen2.5-1.5B-Instruct   (add more model names to compare)
Reports, per model: load time, time to the first generated text, total time, and tokens per second, over several runs,
plus how long the deterministic plan card takes (it appears before the model finishes). Writes eval/latency_results.csv.
"""
import csv
import os
import statistics
import sys
import time
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import coach  # noqa: E402
import llm  # noqa: E402
import trackers  # noqa: E402
import userprofile  # noqa: E402

PROMPTS = [("session", "Suggest a workout"), ("dishes", "Meal ideas"), ("chat", "love rice"), ("general", "How do I do a proper squat?")]


def card_time_ms():
    """Time for code alone to build today's session card."""
    pn = userprofile.normalize(equipment=["Gym access"], days=7, minutes=30)
    state = trackers.new_state()
    coach.sync(state, pn)
    start = time.perf_counter()
    coach.start_or_adjust(state, [], date.today(), reset=True)
    return (time.perf_counter() - start) * 1000


def measure(model_name, runs=3, loader=None, streamer=None, counter=None):
    """Returns (load_seconds, rows). The loader, streamer, and counter can be replaced for testing."""
    loader = loader or llm.load
    streamer = streamer or llm.stream_answer
    counter = counter or (lambda text: len(llm._S["tok"](text).input_ids))
    start = time.perf_counter()
    if not loader(model_name):
        raise RuntimeError(f"could not load {model_name}: {llm.last_error()}")
    load_s = time.perf_counter() - start
    profile = {"goal": "General fitness", "level": "Beginner", "equipment": ["Dumbbells"], "days": 3, "minutes": 30, "style": "Friendly"}
    rows = []
    for _ in range(runs):
        for intent, text in PROMPTS:
            msgs = llm.build_messages(text, [], profile, [], intent, "")
            t0, first, last = time.perf_counter(), None, ""
            for last in streamer(msgs, max_new_tokens=llm.TOKENS.get(intent, 240)):
                if first is None:
                    first = time.perf_counter() - t0
            total = time.perf_counter() - t0
            tokens = counter(last) if last else 0
            rows.append({"model": model_name, "reply": intent, "first_s": round(first or total, 2), "total_s": round(total, 2),
                         "tokens": tokens, "tokens_per_s": round(tokens / total, 2) if total else 0})
    return load_s, rows


def summarize(rows):
    return {"median_first_s": statistics.median(r["first_s"] for r in rows), "median_total_s": statistics.median(r["total_s"] for r in rows),
            "median_tokens_per_s": statistics.median(r["tokens_per_s"] for r in rows)}


if __name__ == "__main__":
    models = sys.argv[1:] or [llm.MODEL_NAME]
    print(f"Deterministic plan card: {card_time_ms():.1f} ms (appears immediately)")
    out = []
    for name in models:
        try:
            load_s, rows = measure(name)
        except RuntimeError as e:
            print(e)
            continue
        print(f"{name}: load {load_s:.0f} s | {summarize(rows)}")
        out += rows
    if out:
        with open(os.path.join(os.path.dirname(__file__), "latency_results.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(out[0]))
            w.writeheader()
            w.writerows(out)
        print("Saved eval/latency_results.csv")
