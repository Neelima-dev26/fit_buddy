# User test protocol (OPTIONAL: not required by the assignment)

Use this only if your group wants usability evidence. Skipping it is fine; the documents do not depend on it.

Purpose: collect usability evidence (RQ3) for the results paper. Use about 5 participants (classmates are fine). Do not collect names or
personal health information. Tell participants that taking part is voluntary, the test is about the app and not about them, and they may stop anytime.

## Setup
- Start the app with the language model running (status line says "ready"). Record the model name, laptop, and whether the model was ready.
- Participant uses the app; the observer notes time per task, errors, and comments. Do not help unless they are stuck for more than 1 minute.

## Tasks (success criteria)
| # | Task | Success when |
|---|---|---|
| 1 | Set your preferences (equipment, days, minutes) and find your weekly plan | They open My plan and name one day's session |
| 2 | Ask for today's workout, then shorten it to 15 minutes | A 15-minute session is shown |
| 3 | Log "slept 7 hours and drank 2 glasses of water" and "ate rice", then ask what you ate today | The recall shows rice |
| 4 | Ask for meal ideas, then ask for a recipe for one of them | A recipe with method is shown |
| 5 | Ask a fitness question, for example "how do I do a proper squat?" | An answer with sources appears |
| 6 | In the Library tab, find a vegetarian dinner | They name one dish |

## After the tasks
Ask the 10 System Usability Scale statements (1 = strongly disagree, 5 = strongly agree) and record the answers in `eval/sus_template.csv`:
1. I think that I would like to use this system frequently.
2. I found the system unnecessarily complex.
3. I thought the system was easy to use.
4. I think that I would need the support of a technical person to be able to use this system.
5. I found the various functions in this system were well integrated.
6. I thought there was too much inconsistency in this system.
7. I would imagine that most people would learn to use this system very quickly.
8. I found the system very cumbersome to use.
9. I felt very confident using the system.
10. I needed to learn a lot of things before I could get going with this system.

Then ask two open questions: "What was most useful?" and "What was confusing or missing?" Write the answers down for the results paper.

## Scoring
`python eval/score_sus.py eval/sus_template.csv` prints each score (0 to 100), the mean, and the standard deviation.
Report task completion (tasks passed out of 6 per participant) and median time per task as well.
