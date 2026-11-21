# How to fill in the highlighted spots of the results paper and slides

Run these two commands (the app does not need to be open). The first run downloads the model, so allow time.

1. Understanding accuracy (Table 3, slide 15):
   `python eval/run_understanding_eval.py Qwen/Qwen2.5-1.5B-Instruct`
   It prints `model_only` and `rules_plus_model` as fractions. Multiply by 40 for "correct of 40" and by 100 for the percentage.
   (`rules_only` should show 0.85, which is already in the paper.)

2. Response time (Table 4, slide 15):
   `python eval/measure_latency.py Qwen/Qwen2.5-1.5B-Instruct`
   Use "Deterministic plan card" for the plan card (ms), `median_first_s`, `median_total_s`, and `median_tokens_per_s`.

3. Test machine: your laptop model, processor, and memory (Apple menu > About This Mac).

4. Summary paragraph (3 or 4 sentences): say whether the model understood messages the rules missed (compare the CSV in
   `eval/understanding_results.csv`), and how long a user waits for the model's sentence versus the plan card.

5. Group dynamic: who did what, how often you met, which tools you used, and one positive thing about working together.
