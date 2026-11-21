"""Shows what the search returns and the scores, to debug repeated or missing results.

Usage:  python debug_search.py "Meal ideas" meal
        python debug_search.py "how do I do a squat"
"""
import sys
import rag

query = sys.argv[1] if len(sys.argv) > 1 else "Meal ideas"
category = sys.argv[2] if len(sys.argv) > 2 else None
r = rag.Retriever("knowledge")
print(f"backend={r.backend}  passages={len(r.chunks)}  relevance cutoff={r.threshold}")
print(f"\nWith the cutoff (specific questions use this):")
for x in r.search(query, k=10, category=category):
    print(f"  {x['score']:.2f}  {x['source']}")
print(f"\nWithout the cutoff (generic requests like 'Meal ideas' use this):")
for x in r.search(query, k=10, category=category, min_score=0.0):
    print(f"  {x['score']:.2f}  {x['source']}")
