---
title: FitBuddy
emoji: 💪
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 5.50.0
python_version: "3.11"
app_file: app.py
pinned: false
---

# FitBuddy: a fitness and wellness chatbot

Human-Computer Interaction group project. FitBuddy answers beginner fitness, meal, and wellness questions using
retrieval augmented generation (RAG) over a small knowledge base, and tracks water, sleep, and habits from
natural-language messages. It shares general information only and is not medical advice.

## How it works
1. `safety.py` screens each message for red flags (emergencies, medical conditions, extreme diets) in code, before any model.
2. `router.py` picks an intent (log, BMI, summary, workout, meal, wellness, general) using simple rules.
3. `trackers.py` handles logging, BMI, and the weekly summary in plain Python.
4. `rag.py` retrieves the top passages from `knowledge/` (sentence-transformers embeddings, with a TF-IDF fallback).
5. `llm.py` builds the prompt and streams an answer from a small open model (default Qwen2.5-1.5B-Instruct).

## Run locally
```
pip install -r requirements.txt
python app.py
```
The first run downloads the models from Hugging Face (about 3 GB for the language model). Useful settings:
- `FITBUDDY_MODEL=meta-llama/Llama-3.2-1B-Instruct` to try another model (not tested by the group; Llama needs license acceptance and `huggingface-cli login`).
- `FITBUDDY_NO_LLM=1` to run without a language model (shows the retrieved notes only; good for testing the interface).

## Deploy on Hugging Face Spaces
Create a Space (SDK: Gradio, free CPU), then upload these files or push them with Git. Set `sdk_version` above to the
Gradio version you tested with. The first reply after a cold start is slow.

## Tests and evaluation
- `python tests/test_logic.py` tests safety, parsing, routing, BMI, trackers, and retrieval (no model needed).
- `python eval/run_eval.py <model names>` compares models on `eval/questions.json` and writes `eval/results.csv`.

## Credits and notes
- The knowledge base in `knowledge/` (163 short notes on workouts, exercise form, meals from many cuisines, allergies and special diets, sleep, stress, habits, and more) was written for this project from general public-health guidance (U.S. Physical
  Activity Guidelines, WHO 2020 guidelines, MyPlate). The group should review, expand, and cite it.
- App structure follows common Hugging Face + Gradio chatbot tutorials (e.g. the KDnuggets guide linked in the assignment);
  the RAG pipeline, safety layer, router, and trackers are original to this project.


## Adding notes to the knowledge base
Each note is a Markdown file in `knowledge/`. The first lines look like this:

```
# How to do a squat: form guide
Category: form
Keywords: squat, goblet squat, legs, glutes, knees
Summary: One sentence that says what the note is about.

The note text, one or two short paragraphs (about 80 to 150 words).
```
- `Category` is one or more of `workout` (plans and routines), `form` (how to do one exercise), `meal` (meal ideas),
  `wellness` (sleep, stress, habits, mood), or `general` (facts, FAQs, glossaries). Generic requests such as the
  "Suggest a workout" and "Meal ideas" buttons rotate through the matching category.
- `Keywords` and `Summary` help the search find the note. Write the note in your own words and credit your sources.
- Restart the app after adding notes. `python debug_search.py "your question"` shows what the search returns.

## How answers are written
Every answer uses the same recipe: the safety check runs first, then the search finds the best notes (for follow-ups
like "make it shorter" it re-uses the notes from the previous answer), and the language model writes the reply using a
coaching prompt with a format for each type of request (workout, meal, wellness, summary, general), your profile, what
you have logged today, and cues such as "tired", "sore", or "10 minutes". Design ideas were informed by AI coaching
apps (for example Google Health Coach and the Stanford Bloom research prototype): supportive and non-judgmental,
offering choices, adjusting on the fly, and short, clear replies.


## Plan engine (preferences that really do something)
Your sidebar choices build a weekly workout plan and a 7-day meal plan by code, even when the language model is off.
See `docs/PlanEngine_Design.md` for the product requirements, architecture, safety rules, and tests.
- `userprofile.py` turns the sidebar into rules (equipment, limited joints, diets, allergens).
- `exercises.py` and `planner.py` build weekly plans, daily sessions, 4-week progression, and on-the-fly adjustments.
- `meals.py` filters a menu by ingredients and builds the week and a shopping list.
- `coach.py` connects them to today's session and what you have logged.

Run all tests: `python tests/test_logic.py`, `python tests/test_planner.py`, `python tests/test_meals.py`, and `python tests/test_app_logic.py`.


## Library, recipes, and meal prep
- The **Library** tab lets you browse all 221 dishes (with methods) across 9 cuisines, 55 exercises (with cues and easier or harder versions), and 163 notes.
- "Meal ideas" shows 5 dishes from the whole menu that fit your dietary needs. "recipe for dal" shows ingredients and a method.
- "meal prep" builds a batch-cooking checklist from your week of meals.

## Language understanding
When the rules do not recognize a message, the language model reads it and returns structured data (what it means, mood, water, sleep, meal),
which code validates before anything is saved. See `docs/PlanEngine_Design.md` section 9 and `eval/run_understanding_eval.py`.


## Project documents
- `SUBMISSION_CHECKLIST.md`: what to hand in. `CREDITS.md`: sources and credits. `docs/CHALLENGES.md`: challenges and likely causes.
- `docs/GIT_AND_DEPLOY.md`: repository, submission zip, and optional Hugging Face Space. `docs/PlanEngine_Design.md`: design notes.
- `docs/UserTest_Protocol.md`, `eval/score_sus.py`, `eval/measure_latency.py`, `eval/run_understanding_eval.py`, `eval/run_eval.py`: tools for collecting the results.
