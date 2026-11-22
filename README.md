---
title: FitBuddy
emoji: 💪
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 5.50.0
app_file: app.py
pinned: false
short_description: A conversational fitness and wellness coach
---

# FitBuddy: a conversational fitness and wellness coach

FitBuddy is a Human-Computer Interaction group project. You tell it your preferences, describe your day in ordinary
sentences, and ask questions. It returns personalized workout and meal plans, recipes, and answers grounded in a small
curated knowledge base, and it tracks water, sleep, mood, habits, workouts, and meals. It runs on a laptop CPU with free,
open-source tools only (no paid APIs). It gives general information and is **not medical advice**.

- Code: https://github.com/Neelima-dev26/fit_buddy
- Hosted demo (free CPU, so the model's replies are slow): https://huggingface.co/spaces/NeelimaTech/fitbuddy

## What it does
- **Plans from your preferences:** goal, experience, equipment, days per week, minutes, limitations, dietary needs, cuisines, age band, and coaching style change a weekly workout plan and a 7-day meal plan. A table on the *My plan* tab shows what each choice changed.
- **Chat logging:** "slept 7 hours, drank 3 glasses of water", "ate rice", "did a 45 minute dumbbell workout". It tolerates typos and number words, and "what did I eat today?" recalls your log.
- **Grounded answers:** questions are answered from 163 notes using retrieval-augmented generation (RAG), with sources shown.
- **Library, recipes, and meal prep:** browse 221 dishes (with methods) across 9 cuisines, 55 exercises, and the notes; get recipes, a shopping list, and a meal prep checklist.
- **Safe by design:** a code-level safety check runs before any model. FitBuddy does not count calories or set weight goals.
- **Always responsive:** plan cards appear immediately; the language model's short personal sentence is added when it is ready.

## Quick start (local)
Requirements: Python 3.10 or newer (tested on 3.11), about 6 GB of free memory for the default model, and internet on the first run.

```
git clone https://github.com/Neelima-dev26/fit_buddy.git
cd fit_buddy
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```
Open the address printed in the terminal (normally http://127.0.0.1:7860).

The first start downloads the search model (about 90 MB) and the language model (about 3 GB), which can take several minutes.
FitBuddy works while the model loads, and the status line under the header shows its state. Later starts load the model in seconds.

### Settings (environment variables)
| Setting | Effect |
|---|---|
| `FITBUDDY_MODEL=Qwen/Qwen2.5-0.5B-Instruct` | Use another model. The default is `Qwen/Qwen2.5-1.5B-Instruct`. The 0.5B model is faster and needs less memory. Other models were not tested by the group; some (for example Llama) need license acceptance and `huggingface-cli login`. |
| `FITBUDDY_NO_LLM=1` | Run without a language model (plans, logging, and the library still work; answers show the retrieved notes). |
| `FITBUDDY_NO_EMBED=1` | Use keyword search instead of embeddings. |
| `FITBUDDY_DEVICE=cpu` / `mps` / `cuda` | Choose the device. The default is the CPU; on a Space it is always the CPU. |
| `FITBUDDY_DTYPE=float32` / `bfloat16` / `float16` | Choose the number format (default float32 on CPU). |

On Windows, set a variable with `set NAME=value` before `python app.py`.

## Hugging Face Space
The repository is ready to run as a Gradio Space (the header of this file configures it). Create a Space with the **Gradio** SDK and **CPU basic**
hardware (free), then push this repository. Set `sdk_version` in the header to the Gradio version you tested (5.50.0). If a Space has ZeroGPU hardware,
`app.py` includes an unused `@spaces.GPU` marker so that it still starts, and it keeps the model on the CPU. The first start downloads the models,
and a free Space is slow and sleeps when idle. Step by step: `docs/GIT_AND_DEPLOY.md`.

## How it works
Every message follows the same path. The principle is: **code decides, the language model understands and phrases.**
1. **Safety check** (`safety.py`): code screens for emergencies, self-harm, eating-disorder language, extreme diets, very low intake, and medical conditions. A match returns a fixed referral reply and the model never sees the message.
2. **Intent** (`router.py`): ordered rules recognize clear commands. When the rules find nothing, the language model returns a small structured answer, which `llm.py` validates (known intents, valid moods, number ranges) before anything is saved.
3. **Logging** (`trackers.py`): sleep, water, mood, habits, workouts, and meal names are parsed from the sentence and stored for the session.
4. **Tools:** the plan engine (`userprofile.py`, `exercises.py`, `planner.py`, `coach.py`), the meal planner (`meals.py`, `recipes.py`), and notes search (`rag.py`) build the answer.
5. **Language model** (`llm.py`): writes a short coaching sentence above the exact plan card, or answers a knowledge question from the retrieved notes (default Qwen2.5-1.5B-Instruct, loaded in the background).
6. **Interface** (`app.py`, `views.py`): a Gradio app with Chat, My plan, Meals, Library, and Progress tabs, a sidebar for preferences, and a status line.

## Project structure
```
fit_buddy/
├── app.py                  Gradio interface and the per-message flow
├── safety.py               code-level safety checks (run before any model)
├── router.py               rule-based intent router
├── llm.py                  language model: loading, prompts, streaming, validated understanding
├── rag.py                  retrieval over knowledge/ (embeddings with a TF-IDF fallback)
├── trackers.py             logging, parsing, BMI, weekly summary, recall
├── userprofile.py          turns the sidebar into one normalized profile
├── exercises.py            the exercise library (55 exercises)
├── planner.py              weekly workout plans, daily sessions, adjustments
├── meals.py                the menu (221 dishes), restrictions, week plans, shopping list
├── recipes.py              a short cooking method for every dish
├── coach.py                connects the profile, planners, and today's log
├── views.py                HTML cards, tables, and the theme
├── debug_search.py         shows what the search returns, for debugging
├── requirements.txt        Python libraries
├── CREDITS.md              sources, reused material, and AI assistance
├── knowledge/              163 Markdown notes (the knowledge base)
├── tests/                  automated tests (5 files)
├── eval/                   evaluation and measurement tools
└── docs/                   design notes and project documents
```

| File | What it contains |
|---|---|
| `app.py` | Builds the Gradio interface, runs the per-message flow (safety, intent, logging, tools, model), the buttons, and the startup checks. |
| `safety.py` | Six red-flag categories with fixed referral replies; parses quantities such as "pounds per week". |
| `router.py` | Ordered regular-expression rules that map a message to an intent. |
| `llm.py` | Model loading (background thread), prompts and token budgets, streaming, and the validated JSON understanding step. |
| `rag.py` | Reads `knowledge/`, embeds passages with all-MiniLM-L6-v2, retrieves the best ones, rotates through unseen notes. |
| `trackers.py` | Session state, log parsing (typos, number words, workout reports), meal recall, habits, streaks, BMI, weekly stats. |
| `userprofile.py` | Normalizes preferences into equipment, limited joints, diets, allergens, and cuisines. |
| `exercises.py` | Exercise data: movement pattern, equipment, level, stressed joints, cues, easier and harder versions. |
| `planner.py` | Builds week layouts and sessions that fit the equipment, time, level, age, and limitations, with a 4-week progression. |
| `meals.py` | Dishes described by ingredients; filters by diet, allergens, and cuisines; builds the week, prep checklist, and shopping list. |
| `recipes.py` | Cooking methods for every dish. |
| `coach.py` | Today's session, one-tap adjustments (shorter, easier, no equipment), and rebuilding plans when preferences change. |
| `views.py` | HTML for the rings, cards, tables, and the Library; escapes all text. |
| `debug_search.py` | `python debug_search.py "your question"` prints the retrieved notes and scores. |
| `knowledge/*.md` | Notes with `Category`, `Keywords`, and `Summary` headers (categories: workout, form, meal, wellness, general). |
| `tests/test_logic.py` | Safety, parsing, routing, BMI, trackers, and retrieval (no model needed). |
| `tests/test_planner.py` | Property tests over about 100,000 generated workout sessions. |
| `tests/test_meals.py` | 504 diet and allergy combinations, cuisine priority, and menu depth. |
| `tests/test_app_logic.py` | Chat flows, buttons, logging, recall, and loading behavior with a stand-in model. |
| `tests/test_tools.py` | Scoring and timing tools, and Hugging Face Space startup. |
| `eval/run_understanding_eval.py`, `eval/understanding_cases.json` | Accuracy of intent understanding on 40 labeled messages (rules only, model only, both). |
| `eval/measure_latency.py` | Times the plan card, the model's first words, and its full reply on your computer. |
| `eval/run_eval.py`, `eval/questions.json` | Compares models on retrieval questions. |
| `eval/score_sus.py`, `eval/sus_template.csv` | Optional: scores System Usability Scale questionnaires (the template rows are examples). |
| `docs/CHALLENGES.md` | Challenges met while building, with likely causes and fixes. |
| `docs/GIT_AND_DEPLOY.md` | Repository, submission zip, and Hugging Face Space steps. |
| `docs/PlanEngine_Design.md` | Design notes for the plan engine, safety rules, and tests. |
| `docs/UserTest_Protocol.md` | Optional usability test script. |

## Tests
Run these from the project folder. Each prints `0 failure(s)` when everything passes. None needs a model download.
```
python tests/test_logic.py
python tests/test_planner.py      # about a minute
python tests/test_meals.py
python tests/test_app_logic.py
python tests/test_tools.py
```

## Evaluation tools
```
python eval/run_understanding_eval.py Qwen/Qwen2.5-1.5B-Instruct   # intent accuracy on 40 messages
python eval/measure_latency.py Qwen/Qwen2.5-1.5B-Instruct          # speed on this computer
```
Run without a model name, `eval/run_understanding_eval.py` reports the rules-only score. The 40 messages were used to tune the rules, so that score is optimistic.

## Adding notes to the knowledge base
Each note is a Markdown file in `knowledge/`:
```
# How to do a squat: form guide
Category: form
Keywords: squat, goblet squat, legs, glutes, knees
Summary: One sentence that says what the note is about.

The note text, one or two short paragraphs (about 80 to 150 words).
```
`Category` is one or more of `workout`, `form`, `meal`, `wellness`, or `general`. Restart the app after adding notes, and use `python debug_search.py "your question"` to see what the search returns.

## Safety, privacy, and limits
- General information only. No calorie targets, supplement advice, or weight-loss goals. Medical words give a gentle plan and a referral.
- Ingredient filtering cannot guarantee allergen safety, so the app tells users to check labels.
- Data stays in the browser session (no accounts); "Download my log" exports it as JSON.
- The notes, dishes, and exercises were written for this project from public guidance (see `CREDITS.md`) and have not been reviewed by a trainer or dietitian.
- A 1.5-billion-parameter model on a CPU is slow (a reply took a median of 14 seconds on an Apple M2 Max). Understanding covers English only.

## Troubleshooting
| Problem | Fix |
|---|---|
| `pip install` says "No matching distribution found for gradio" | Python is older than 3.10. Create the environment with Python 3.10 or newer. |
| The app opens on port 7861 or 7862 | An older copy is still running. Stop it (`pkill -f app.py` on macOS or Linux). |
| The first reply is slow, or the status line says "loading" | The model is downloading (about 3 GB). Plans and logging work meanwhile. |
| Replies say "From my notes" or "language model is switched off" | `FITBUDDY_NO_LLM=1` is set. Remove it. |
| "module has no attribute ..." or a startup message naming out-of-date files | Old and new files are mixed. Use one complete copy of the repository. |
| Out of memory | Use `FITBUDDY_MODEL=Qwen/Qwen2.5-0.5B-Instruct`. |
| Space: "No @spaces.GPU function detected" | The Space has ZeroGPU hardware. Push the latest `app.py`, which adds the marker. |
| Space: "TypeError: argument of type 'bool' is not iterable" | Set `sdk_version` in the header of this file to the tested Gradio version (5.50.0). |

## Credits and AI assistance
See `CREDITS.md` for reused material, models, and how an AI assistant was used. The Hugging Face and Gradio chatbot pattern in the KDnuggets tutorial
linked in the assignment was the starting idea; the safety layer, router, planners, trackers, and tests are original to this project.
