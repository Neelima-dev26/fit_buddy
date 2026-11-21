"""Compare candidate models on the same test questions.

Usage (from the project folder):
    python eval/run_eval.py Qwen/Qwen2.5-1.5B-Instruct   (add more model names to compare)
Writes eval/results.csv. Safety checks are code-level, so they are the same for every model;
the model-dependent scores are keyword coverage (a rough accuracy proxy), response time, and log extraction.
Keyword scoring is crude: also read the answers yourself and score them 1-5 for your report.
"""
import csv, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import llm, rag, router, safety, trackers

here = os.path.dirname(__file__)
questions = json.load(open(os.path.join(here, "questions.json")))
retriever = rag.Retriever(os.path.join(here, "..", "knowledge"))
rows = []

for model in sys.argv[1:] or [llm.MODEL_NAME]:
    if not llm.load(model):
        print(f"Could not load {model}: {llm.last_error()}")
        continue
    for item in questions:
        row = {"model": model, "type": item["type"], "question": item["q"], "answer": "", "score": "", "seconds": ""}
        if item["type"] == "unsafe":
            hit = safety.check(item["q"])
            row.update(answer=hit[1][:80] if hit else "NOT BLOCKED", score=1 if hit else 0)
        elif item["type"] == "log":
            start = time.time()
            parsed = llm.extract_log(item["q"])
            ok = parsed.get("sleep") == item["sleep"] and parsed.get("water") == item["water"]
            row.update(answer=json.dumps(parsed), score=1 if ok else 0, seconds=round(time.time() - start, 1))
        else:
            intent = router.route(item["q"])
            passages = retriever.search(item["q"], k=3)
            msgs = llm.build_messages(item["q"], passages, {}, [], intent)
            start = time.time()
            answer = llm.generate_once(msgs)
            hits = sum(k.lower() in answer.lower() for k in item["keywords"])
            row.update(answer=answer.replace("\n", " "), score=round(hits / len(item["keywords"]), 2), seconds=round(time.time() - start, 1))
        rows.append(row)
        print(model, "|", item["q"][:50], "|", row["score"], row["seconds"])

with open(os.path.join(here, "results.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["model", "type", "question", "answer", "score", "seconds"])
    w.writeheader()
    w.writerows(rows)
print("Saved eval/results.csv")
