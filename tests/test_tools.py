"""Tests for the measurement tools used to collect the results. Run: python tests/test_tools.py"""
import importlib.util
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

fails = 0
def check(name, cond, detail=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if (detail and not cond) else ""))
    fails += 0 if cond else 1

def load(path):
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], os.path.join(HERE, "..", path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

sus = load("eval/score_sus.py")
check("sus: all neutral answers score 50", sus.sus_score([3] * 10) == 50)
check("sus: best possible answers score 100", sus.sus_score([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == 100)
check("sus: worst possible answers score 0", sus.sus_score([1, 5, 1, 5, 1, 5, 1, 5, 1, 5]) == 0)
check("sus: a documented example", sus.sus_score([4, 2, 4, 1, 4, 2, 5, 2, 4, 2]) == 80.0)
try:
    sus.sus_score([3] * 9)
    check("sus: wrong number of answers is rejected", False)
except ValueError:
    check("sus: wrong number of answers is rejected", True)
try:
    sus.sus_score([6] + [3] * 9)
    check("sus: out-of-range answer is rejected", False)
except ValueError:
    check("sus: out-of-range answer is rejected", True)
rows = sus.score_file(os.path.join(HERE, "..", "eval", "sus_template.csv"))
check("sus: the template file can be scored", len(rows) == 2 and all(0 <= s <= 100 for _, s in rows))

lat = load("eval/measure_latency.py")
check("latency: the plan card is built by code in well under a second", lat.card_time_ms() < 1000)
def fake_stream(msgs, max_new_tokens=240, temperature=0.5):
    for i in range(1, 4):
        yield "word " * i
rows_, = [lat.measure("fake", runs=2, loader=lambda n: True, streamer=fake_stream, counter=lambda t: len(t.split()))[1]]
check("latency: measures every reply type for each run", len(rows_) == 2 * len(lat.PROMPTS))
check("latency: reports first-text time, total time, and speed", all({"first_s", "total_s", "tokens", "tokens_per_s"} <= set(r) for r in rows_))
s = lat.summarize(rows_)
check("latency: the summary has medians", all(k in s for k in ("median_first_s", "median_total_s", "median_tokens_per_s")))
try:
    lat.measure("broken", loader=lambda n: False)
    check("latency: a model that cannot load is reported", False)
except RuntimeError:
    check("latency: a model that cannot load is reported", True)

# ---- Hugging Face Space startup: CPU device is forced, and a missing "spaces" package is harmless ----
import subprocess
code = ("import os; os.environ['SPACE_ID']='user/fitbuddy'; os.environ['FITBUDDY_NO_LLM']='1'; os.environ['FITBUDDY_NO_EMBED']='1'; "
        "import sys, types; g=types.ModuleType('gradio'); "
        "from unittest.mock import MagicMock; sys.modules['gradio']=MagicMock(); "
        "import app; print('DEVICE=' + os.environ.get('FITBUDDY_DEVICE','')); print('OK')")
r = subprocess.run([sys.executable, "-c", code], cwd=os.path.join(HERE, ".."), capture_output=True, text=True)
check("space: on Hugging Face the app starts even without the spaces package", "OK" in r.stdout, r.stderr[-300:])
check("space: the device is forced to cpu there", "DEVICE=cpu" in r.stdout, r.stdout[-200:])
code2 = code.replace("os.environ['SPACE_ID']='user/fitbuddy'; ", "")
r2 = subprocess.run([sys.executable, "-c", code2], cwd=os.path.join(HERE, ".."), capture_output=True, text=True)
check("space: on a laptop nothing changes (no forced device)", "DEVICE=\n" in r2.stdout or "DEVICE=" in r2.stdout and "DEVICE=cpu" not in r2.stdout, r2.stdout[-200:])
print(f"\n{fails} failure(s)")
sys.exit(1 if fails else 0)
