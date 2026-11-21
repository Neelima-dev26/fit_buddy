"""Score System Usability Scale (SUS) answers.

Usage:  python eval/score_sus.py eval/sus_template.csv
CSV columns: participant,q1,...,q10 (each 1 to 5). The two rows in the template are EXAMPLES: replace them with real answers.
Scoring (Brooke, 1996): odd items contribute (answer - 1), even items contribute (5 - answer); the sum is multiplied by 2.5 (0 to 100).
"""
import csv
import statistics
import sys


def sus_score(answers):
    """answers: list of ten integers from 1 to 5."""
    if len(answers) != 10 or any(not 1 <= a <= 5 for a in answers):
        raise ValueError("SUS needs ten answers between 1 and 5")
    return 2.5 * sum((a - 1) if i % 2 == 0 else (5 - a) for i, a in enumerate(answers))


def score_file(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((r["participant"], sus_score([int(r[f"q{i}"]) for i in range(1, 11)])))
    return rows


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "eval/sus_template.csv"
    scored = score_file(path)
    for name, s in scored:
        print(f"{name}: {s:.1f}")
    values = [s for _, s in scored]
    if values:
        sd = statistics.stdev(values) if len(values) > 1 else 0.0
        print(f"n = {len(values)}, mean = {statistics.mean(values):.1f}, SD = {sd:.1f}  (about 68 is a commonly cited average)")
