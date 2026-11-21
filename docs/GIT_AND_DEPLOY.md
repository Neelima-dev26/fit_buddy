# Git repository, submission zip, and optional Hugging Face Space

## 1. Create the repository (GitHub or GitLab)
1. Create an empty repository named `fitbuddy` and add your instructor as a collaborator (or make it public). Put the link in the design document and the results paper.
2. Each member sets their own identity so the history shows who did what:
   `git config user.name "Your Name"` and `git config user.email "you@example.com"`

## 2. First push (from the project folder)
```
git init
git add .
git commit -m "FitBuddy: initial version"
git branch -M main
git remote add origin https://github.com/<user>/fitbuddy.git
git push -u origin main
```
`.gitignore` already excludes `venv/`, caches, and result files. Use short branches and clear commit messages for later changes
(for example `git switch -c knowledge-notes`), and keep a screenshot of the commit history for the results paper.

## 3. Make the submission zip
```
git archive --format=zip --output=FitBuddy_source.zip HEAD
```
This zips exactly what is in the repository (no `venv`). Check by unzipping it into a new folder, creating a new virtual environment,
running `pip install -r requirements.txt`, and running the four test files in `tests/`.

## 4. Optional: Hugging Face Space (free CPU)
1. Create an account, then New Space: SDK Gradio, hardware CPU basic, public or private.
2. Add the Space as a second remote and push:
   ```
   git remote add space https://huggingface.co/spaces/<user>/fitbuddy
   git push space main
   ```
   (Use a Hugging Face access token with write permission as the password.)
3. The header of `README.md` tells the Space how to start (`app_file: app.py`). If the build fails, set `sdk_version` to the Gradio version you
   tested locally (`pip show gradio`).
4. The first start downloads the models, so it takes several minutes. A free Space can be slow and goes to sleep when idle.
   If you skip the Space, say in the documents that the project runs locally.
