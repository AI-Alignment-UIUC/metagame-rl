"""The day's schedule (log #240, Evan's row 55): windows that borrow the GPU from the ar/ loop.

At each window's time it creates ar/PAUSE, waits until no ar/ experiment is running (the loop finishes its current one
and ends its session; ar/drive.py starts no new one while paused), launches the window's jobs one after another through
`loop.py launch` (so each is registered and checked), waits for each to end, and removes ar/PAUSE so the loop resumes.
Detached and one instance; its log is runs/dayplan/log.txt and its state runs/dayplan/status.json.

Run:  .venv/Scripts/pythonw.exe notes/scripts/dayplan.py runs/dayplan/plan.json
Plan: {"windows": [{"at": "2026-10-24 19:00", "name": "probes", "jobs": [{"launch": [<loop.py launch args>],
       "timeout_min": 40}, ...]}, ...]}     Stop: create runs/dayplan/STOP (the current job finishes; ar/PAUSE is removed).
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import loop                                              # noqa: E402

DIR = ROOT / "runs" / "dayplan"
PAUSE = ROOT / "ar" / "PAUSE"
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")


def log(msg):
    DIR.mkdir(parents=True, exist_ok=True)
    with open(DIR / "log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")


def ar_busy() -> bool:
    """An ar/ experiment (fixed.py or train.py) is running."""
    return any(re.search(r"ar[\\/](fixed|train)\.py", cmd or "") for _, _, cmd in loop.processes().values())


def run_job(job: dict) -> str:
    r = subprocess.run([PY, str(ROOT / "notes" / "scripts" / "loop.py"), "launch", *job["launch"]], cwd=ROOT,
                       capture_output=True, text=True)
    m = re.search(r": pid (\d+)", r.stdout)
    if not m:
        return f"not launched: {(r.stdout + r.stderr).strip()[-300:]}"
    pid, name = int(m.group(1)), job["launch"][0]
    ctime = loop.creation_time(pid)
    t0 = time.time()
    while loop.alive(pid, ctime):
        if time.time() - t0 > job.get("timeout_min", 40) * 60:
            loop.stop_file(loop.registry(mark=False)[name]).write_text("stop: dayplan timeout\n")
            log(f"{name}: timeout, STOP written")
            while loop.alive(pid, ctime) and time.time() - t0 < (job.get("timeout_min", 40) + 15) * 60:
                time.sleep(30)
            break
        time.sleep(30)
    return f"ended after {(time.time() - t0) / 60:.0f} min"


def main(plan_path: str):
    me = DIR / "pid"
    if me.exists() and loop.alive(int(me.read_text().split()[0])):
        return
    DIR.mkdir(parents=True, exist_ok=True)
    me.write_text(str(__import__("os").getpid()))
    status = json.loads((DIR / "status.json").read_text()) if (DIR / "status.json").exists() else {"windows": []}
    done = {w["name"] for w in status["windows"]}
    while not (DIR / "STOP").exists():
        # the plan is re-read every minute, so later windows can be filled in or moved while earlier ones run
        try:
            plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
            good = plan
        except (OSError, ValueError) as e:                  # a half-saved or broken edit: keep the last good plan
            if "good" not in locals():
                raise
            log(f"plan.json unreadable ({e}); keeping the last good plan")
            plan = good
        pending = sorted((w for w in plan["windows"] if w["name"] not in done), key=lambda w: w["at"])
        if not pending:
            break
        w = pending[0]
        if datetime.now() < datetime.strptime(w["at"], "%Y-%m-%d %H:%M"):
            time.sleep(60)
            continue
        log(f"window {w['name']}: pausing ar/")
        PAUSE.write_text(f"dayplan window {w['name']}" + "\n")
        t0 = time.time()
        while ar_busy() and time.time() - t0 < 20 * 60:
            time.sleep(20)
        log(f"window {w['name']}: ar/ idle after {(time.time() - t0) / 60:.0f} min")
        results = []
        for job in w["jobs"]:
            if (DIR / "STOP").exists():
                break
            log(f"{job['launch'][0]}: launching")
            res = run_job(job)
            log(f"{job['launch'][0]}: {res}")
            results.append({"job": job["launch"][0], "result": res})
        PAUSE.unlink(missing_ok=True)
        log(f"window {w['name']}: done, ar/ resumed")
        done.add(w["name"])
        status["windows"].append({"name": w["name"], "jobs": results, "ended": f"{datetime.now():%Y-%m-%d %H:%M}"})
        (DIR / "status.json").write_text(json.dumps(status, indent=1))
    PAUSE.unlink(missing_ok=True)
    me.unlink(missing_ok=True)
    log("plan finished")


if __name__ == "__main__":
    main(sys.argv[1])
