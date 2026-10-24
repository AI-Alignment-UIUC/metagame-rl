"""Screens (log #128): metagame runs started outside the lab, in parallel, detached so they outlive the session, each on
its own share of the machine. A screen is the lab's main-line recipe (rl/lab.py main_args in runs/lab/lab.json) plus its
own flags, usually forked from a main-line state; it is watched by notes/scripts/screen_watch.py and stopped by hand
(its STOP file) as soon as its trajectory stalls, not run to a fixed schedule.

  .venv/Scripts/python notes/scripts/screen.py start scr-judge --fork runs/lab/main/seg_0460.pt --until 490 \
      --share 0.26 --threads 5 --workers 4 -- --judge-explore 0
  .venv/Scripts/python notes/scripts/screen.py stop scr-judge
  .venv/Scripts/python notes/scripts/screen.py list

Runs live in runs/screens/<name>/ (stdout.log, log.jsonl, checkpoint.pt, population_it*.pt every --keep iterations).
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCREENS = ROOT / "runs" / "screens"
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")


def main_args() -> dict:
    return json.load(open(ROOT / "runs" / "lab" / "lab.json", encoding="utf-8"))["main_args"]


def flatten(d: dict) -> list:
    out = []
    for k, v in d.items():
        if v is True:
            out.append(k)
        elif v is not False and v is not None:
            out += [k, str(v)]
    return out


def start(a, extra):
    run = SCREENS / a.name
    run.mkdir(parents=True, exist_ok=True)
    base = {**main_args(), "--micro-batch": 256, "--save-every": a.keep}
    args = [PY, "-m", "rl.metagame", "--run", str(run.relative_to(ROOT)), "--iters", str(a.until),
            "--workers", str(a.workers), "--stop-file", str(run / "STOP"), *flatten(base)]
    if (run / "checkpoint.pt").exists():
        args.append("--resume")
    elif a.fork:
        args += ["--fork-from", a.fork]
    elif a.init:
        args += ["--init-from", a.init]
    args += extra
    (run / "STOP").unlink(missing_ok=True)
    env = {**os.environ, "RL_GPU_SHARE": str(a.share), "RL_CPU_THREADS": str(a.threads)}
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_BREAKAWAY_FROM_JOB
    with open(run / "stdout.log", "a") as out:
        out.write("# " + " ".join(args) + "\n")
        out.flush()
        p = subprocess.Popen(args, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                             creationflags=flags)
    meta = {"name": a.name, "pid": p.pid, "args": args[3:], "share": a.share, "threads": a.threads,
            "hypothesis": a.hypothesis}
    with open(run / "screen.jsonl", "a") as f:
        f.write(json.dumps(meta) + "\n")
    print(f"{a.name}: pid {p.pid}")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    extra = []
    if "--" in argv:
        i = argv.index("--")
        argv, extra = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["start", "stop", "list"])
    ap.add_argument("name", nargs="?")
    ap.add_argument("--fork", default="", help="a metagame checkpoint to fork (its whole state)")
    ap.add_argument("--init", default="", help="a pilot checkpoint for a new population (no fork)")
    ap.add_argument("--until", type=int, default=490, help="the iteration to stop at (absolute)")
    ap.add_argument("--share", type=float, default=0.26, help="RL_GPU_SHARE")
    ap.add_argument("--threads", type=int, default=5, help="RL_CPU_THREADS")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--keep", type=int, default=10, help="save population_it*.pt every this many iterations")
    ap.add_argument("--hypothesis", default="")
    a = ap.parse_args(argv)
    if a.cmd == "start":
        start(a, extra)
    elif a.cmd == "stop":
        (SCREENS / a.name / "STOP").write_text("stop\n")
        print(f"{a.name}: STOP written; it ends after its current iteration")
    else:
        for run in sorted(SCREENS.glob("*")):
            rows = (run / "log.jsonl").read_text().splitlines() if (run / "log.jsonl").exists() else []
            last = json.loads(rows[-1]) if rows else {}
            q = last.get("shape_quartiles", {})
            med = "/".join(f"{q[k][1]:.0f}" for k in ("pokemon", "trainer", "energy")) if q else "-"
            print(f"{run.name:32s} it {last.get('iter', '-')!s:>4}  median {med}  stop={'yes' if (run / 'STOP').exists() else 'no'}")


if __name__ == "__main__":
    main()
