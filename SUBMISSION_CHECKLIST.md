# Submission checklist

## 1. Proposal (1 to 2 pages)
- [ ] Final version submitted and approved.

## 2. Design document (3 to 5 pages, APA)
- [ ] Group names, department, course, instructor, and date filled in on the title page.
- [ ] Repository link added; AI-assistance statement confirmed against course policy.
- [ ] References checked against the original sources (pages, DOIs, titles).

## 3. Source code (instructor-accessible Git repository plus a zip)
- [ ] Repository created, instructor added (see `docs/GIT_AND_DEPLOY.md`), history shows every member.
- [ ] `FitBuddy_source.zip` made with `git archive` and tested from a fresh folder.
- [ ] `CREDITS.md` completed (AI-assistance paragraph).
- [ ] `docs/CHALLENGES.md` included (note that the code runs, and the challenges with likely causes).
- [ ] All five test files end with "0 failure(s)".

## 4. Results paper (5 to 7 pages, APA)
- [ ] Measurements collected: `python eval/run_understanding_eval.py Qwen/Qwen2.5-1.5B-Instruct` and `python eval/measure_latency.py Qwen/Qwen2.5-1.5B-Instruct`.
- [ ] (Optional, not required) user test: `docs/UserTest_Protocol.md`.
- [ ] Table values and every [bracket] filled in, including the group dynamic section.
- [ ] (Optional) about 20 new messages added to `eval/understanding_cases.json` and reported separately.

## 5. Presentation (at most 20 slides)
- [ ] Group names, results numbers, and a screenshot or short demo added.
- [ ] Rehearsed to the time limit.
