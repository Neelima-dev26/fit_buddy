# Challenges, possible causes, and how the code runs

## Does the code run?
Yes, on the machines the group tested (Python 3.11, macOS). Requirements:
- Python 3.10 or newer (Gradio 5 needs it). Python 3.9 fails at `pip install` with "No matching distribution found for gradio".
- Internet for the first run (downloads about 3 GB for the language model and about 90 MB for the search model).
- Roughly 6 GB of free memory for the 1.5B model on a CPU (use the 0.5B model otherwise).
If the app does not start, the terminal prints lines starting with `[FitBuddy]` that say why (for example `COULD NOT LOAD MODEL ...`).

## Challenges
| # | Challenge | Likely cause | What we did |
|---|---|---|---|
| 1 | `pip install` failed: no matching Gradio | macOS system Python 3.9 | Installed Python 3.11 and a new virtual environment |
| 2 | "module has no attribute ..." and "unexpected keyword argument" | Updated files copied one at a time, so old and new files were mixed | Shipped whole-folder releases and a startup check that names out-of-date files |
| 3 | Chat stuck on "Warming up the model" | First message downloaded and loaded the model on the main thread; CPU generation is slow | Background loading, card-first replies, and a status line |
| 4 | App felt like a logger and sentence matcher | Most behavior was rules; the model was only used at the edges | Hybrid design: the model understands free-form messages (validated JSON) and writes the coach voice |
| 5 | Preferences such as gym access and days per week did nothing | They were only pasted into the prompt | Deterministic plan engine with an explanation table and property tests |
| 6 | Meal ideas repeated; chosen cuisines ignored | Relevance cutoff left few notes; priority lost by a shuffle; thin menu | Topic-restricted rotation, priority fix, 87 new dishes, depth tests |
| 7 | "Rebuild" button seemed to do nothing | Same inputs gave the same plan and no feedback | Variety setting plus a message after every button |
| 8 | Syntax error on Python 3.11 only | Developer machine used Python 3.12 (nested f-string quotes) | Added a scan for 3.11-incompatible syntax |
| 9 | Layout bugs (missing chat panel, misaligned cards, clipped rings) | Component placement and Gradio padding | Fixed from screenshots, iteration by iteration |
| 10 | Safety scope (calories, weight loss, medical) | Small models are unreliable with numbers and health advice | Code-level safety layer, no calorie or weight targets |

## Known limitations
See section "Limitations and Threats to Validity" of the design document.
