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
1. Check your local Gradio version: `pip show gradio`. In `README.md`, set `sdk_version:` in the header to that exact version
   (the project was tested with 5.50.0). Leave `python_version` unset: the Space runs fine on its default Python 3.10. Commit the change.
2. On huggingface.co: profile > New Space. Name `fitbuddy`, SDK Gradio, hardware **CPU basic (free)**, Public. Do not pick ZeroGPU: a free
   account cannot change it later. If a Space does have ZeroGPU, `app.py` already contains the marker function that lets it start.
3. Create an access token with **write** permission: profile > Settings > Access Tokens > New token.
4. Push your code to the Space (the new Space starts with a README, so overwrite it):
   ```
   git remote add space https://huggingface.co/spaces/<your-hf-username>/fitbuddy
   git push space main --force
   ```
   Username: your Hugging Face username. Password: the token.
5. Open the Space's **Logs** tab. The build installs the libraries (several minutes), then the app downloads the model on first start.
6. The free CPU is slower than a laptop. If replies take a minute or more, open Space **Settings > Variables and secrets > New variable**,
   name `FITBUDDY_MODEL`, value `Qwen/Qwen2.5-0.5B-Instruct`, then restart the Space. Say in your documents which model the Space uses.
7. A free Space sleeps when idle, and the first visit afterward takes a while to wake it.
If the build fails, read the last lines of the Logs tab. Common causes: `sdk_version` not matching Gradio, or the build running out of time.
If you skip the Space, say in the documents that the project runs locally.
