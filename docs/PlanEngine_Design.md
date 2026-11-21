# FitBuddy plan engine: product, architecture, and test notes

## 1. Problem (product view)
Users set preferences (goal, experience, equipment, days per week, minutes, limitations, dietary needs, cuisines, age) and
expect them to matter. Before this change most of them were only pasted into the language model's prompt, so with the model
off (or with a small model) "gym access" and "4 days a week" changed nothing.

**Principle:** every preference must have a visible, explainable effect, and that effect must not depend on the language model.

## 2. Users and jobs to be done
| Persona | Need | Acceptance test |
|---|---|---|
| Beginner at home, dumbbells only | A week they can follow | 3 sessions, only dumbbell and bodyweight moves |
| Gym member, 4 days | A real split | Upper, lower, cardio, full body; machines first |
| Busy parent, 15 minutes | Something that fits today | "Only 15 minutes" gives about 15 minutes |
| Adult with sore knees | Safe swaps | No exercise tagged as stressing the knee, ever |
| Vegetarian student with a nut allergy | Meals that fit | No planned dish contains an excluded ingredient |
| Over 50 or under 18 | Age-appropriate plan | Balance work and low impact (50+); capped sets and supervision note (under 18) |

## 3. Preference contract
| Preference | Effect | Where it is shown |
|---|---|---|
| Goal | Rep ranges, rest, schedule, cardio finisher | My plan > "What FitBuddy does with your choices" |
| Experience | Sets (2 to 4) and exercise difficulty | same table |
| Equipment | Only exercises that use it; gym machines and dumbbells are picked first | same table and the plan |
| Days per week | Weekly layout (1 to 7 days, rest days spread out) | week cards |
| Minutes | Number of exercises fitted to the time (including warm-up and cool-down) | each session |
| Limitations | Joints are parsed (knee, back, shoulder, wrist, ankle, hip); stressing moves are skipped. Medical words give a gentle-only plan and a doctor warning | table and session notes |
| Dietary needs | Diets and allergens exclude dishes by ingredient; "no X" words exclude by name | Meals tab |
| Cuisines | Dishes from chosen cuisines are preferred | Meals tab |
| Age | Teen: set caps and supervision note. 50+: balance work, low impact | table |
| Coaching style | Wording of the model's replies (only effect that needs the model) | table says so |

## 4. Architecture
```
Sidebar -> userprofile.normalize() -> one normalized profile (+ signature)
                    |
        coach.sync() rebuilds only what changed
        /                      \
planner.py + exercises.py     meals.py (menu with ingredient lexicon)
(weekly plan, sessions,        (7-day plan, shopping list)
 4-week progression, adjust)
        \                      /
              coach.py (today's session, adjustments, "done" tracking)
                    |
   router.py -> app.respond() -> llm.py (phrases the result)  or  plain text if the model is off
```
Design decisions:
- **Code decides, the model phrases.** Structure (which exercise, how many sets, which dish) is deterministic and testable. The model
  only presents it ("use exactly this plan") or answers knowledge questions from the notes.
- **Works without the model.** All plan features return useful text with the language model switched off.
- **Always in sync.** A signature of the preferences is stored with each plan; any change rebuilds it automatically.
- **Requests do not overwrite the profile.** "A 3-day plan with dumbbells" builds a plan for that request; the saved preferences stay.
- **Honest limits.** Unrecognized limitations or dietary text is reported as not applied; allergen filtering is by ingredient list
  and always comes with a "check labels" note.

## 5. Safety rules
- Limitation text that mentions a medical word (injury, surgery, heart condition, pregnancy, and others) switches to walking and mobility only.
- Dietary exclusion is by ingredient attributes, never by the model. The tests check every diet, allergen, and "no X" combination.
- Under 18: sets capped at 3; adult supervision note. No calorie targets anywhere.

## 6. Tests (run all four)
- `tests/test_planner.py`: about 100,000 generated sessions over every goal, level, equipment set, time, limitation, and age. Rules checked:
  equipment, limited joints, level, teen set cap, time budget, at least two exercises, gentle plans; schedules for 1 to 7 days;
  progression over the 4-week cycle; on-the-fly adjustments.
- `tests/test_meals.py`: 504 restriction combinations x 7 days x 4 meals. No planned dish may contain an excluded ingredient.
- `tests/test_app_logic.py`: chat flows (plan, today's session, adjustments, tracking, meals).
- `tests/test_logic.py`: parsing, routing, tracking, search, and views.

## 7. Known limits (for the results paper)
- Exercise and meal data were written for this project and should be reviewed by a qualified trainer and dietitian.
- Preference parsing of free text is rule-based, so unusual phrasing may not be recognized (the app says so).
- The menu has about 80 dishes; very restrictive combinations may repeat dishes or leave a meal open (the app warns).
- Times shown use the computer's clock.

## 8. Measures to report
Share of preferences with a visible effect (10 of 10), test counts, plan generation time, and a user check that plans match
stated preferences. Compare models only on the wording of replies, since the structure is identical for every model.


## 9. Where the language model fits (answering "is this really an LLM project?")
The app is a hybrid. Rules are fast and safe for clear commands, and the language model handles everything people actually type.

| Step | Who does it | Why |
|---|---|---|
| Safety check (emergencies, medical, extreme diets) | Code, always first | Must never depend on a model |
| Understanding free-form messages ("wiped out after a rough night", "I only have a quarter of an hour") | **Language model** (JSON intent and slots, validated in code) | Rules cannot cover natural phrasing |
| Plans, sessions, meals, allergen filtering | Code (planner, meals, coach) | Reliable, testable, works with the model off |
| Answers to knowledge questions | **Language model + retrieval (RAG)** over 163 notes | Grounded in sources |
| Coaching voice: short intros, chat, recipe presentation, weekly insight | **Language model** | Personal and natural |
| Conversation memory and follow-ups ("make it shorter") | Model prompt plus coach state | Keeps context |

The model is consulted when the rules find nothing, or when the message is a short remark that the rules would file as a knowledge question.
Its output is validated (unknown intents, out-of-range numbers, and invalid moods are dropped), so a confused model cannot change anything.

### Evaluation to include in the results paper
`python eval/run_understanding_eval.py <model names>` scores three setups on 40 labeled messages: rules only, model only, and both together.
Important honesty note: the first 40 cases were used while developing the rules, so the rules-only score (85%) is optimistic.
Before reporting, write about 20 NEW messages that nobody has tested the rules on, add them to `eval/understanding_cases.json`, and report
those numbers separately. Optionally compare other open models on the same cases, and report latency per message.
