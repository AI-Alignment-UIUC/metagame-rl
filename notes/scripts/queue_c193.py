"""C193's driver (runs/probe/C193-lists-swap-depth/record.md): each stage script in turn through loop.py launch --kind probe, a
refused launch retried every 2 minutes (row 73's holds are the launcher's), the next stage only after the last has ended.
    .venv/Scripts/python notes/scripts/queue_c193.py pilot-gate pilot-cells
    .venv/Scripts/python notes/scripts/queue_c193.py --after s1-search-plus s2-greedy s2-search-minus s2-search-plus
    .venv/Scripts/python notes/scripts/queue_c193.py --cand C194 --dir runs/probe/C194-lists-swap-horizon2 pilot-gate
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import queue_c90 as Q                                    # noqa: E402

D = ROOT / "runs" / "probe" / "C193-lists-swap-depth"
Q.D = D


CAND = "C193"
GPU = []                                                 # --cpu: a CPU-only probe (loop.py --gpu-gb 0)


def stage(s):
    kind, resume = "probe", None
    if s.startswith("pilot:"):                             # C189: a training stage takes a slot
        kind, s = "pilot", s[6:]
    if s.startswith("resume:"):                            # #1122: resume:NAME:script relaunches registered run NAME with --resume (a continuation)
        _, resume, s = s.split(":", 2)
    name = resume or f"{CAND}-{s}"
    while not Q.alive(name):
        if name in Q.reg() and not resume:
            Q.log(f"{name} already registered and not alive: taken as ended"); return
        r = subprocess.run([Q.PY, "notes/scripts/loop.py", "launch", name, *(["--resume"] if resume else []), "--candidate", CAND, "--record", str((D / "record.md").relative_to(ROOT).as_posix()),
                            "--run", D.relative_to(ROOT).as_posix(), "--kind", kind, "--start", "other", *(GPU if kind == "probe" else []), "--", "sh", f"{D.relative_to(ROOT).as_posix()}/{s}.sh"],
                           cwd=ROOT, capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        Q.log(f"launch {name}: {out[-300:]}")
        if "refused" not in out:
            time.sleep(30)
            break
        time.sleep(120)
    while Q.alive(name):
        time.sleep(30)
    Q.log(f"{name} ended")


if __name__ == "__main__":
    args = sys.argv[1:]
    after = None
    if "--cpu" in args:
        GPU, args = ["--gpu-gb", "0"], [x for x in args if x != "--cpu"]
    if args[:1] == ["--cand"]:                      # C194: another record's stages, in its own folder
        CAND, D, args = args[1], ROOT / args[3], args[4:]
        Q.D = D
    after_reg, after_alive, after_file = None, [], None
    if args[:1] == ["--after-file"]:                # C202 Amendment 1: wait until this file exists (a run's snapshot)
        after_file, args = ROOT / args[1], args[2:]
    if args[:1] == ["--after-alive"]:               # #1044: wait until each of these runs has been seen running (a priority order)
        after_alive, args = args[1].split(","), args[2:]
    if args[:1] == ["--after-reg"]:                 # C199: wait only for that stage to be registered (launched), not to end
        after_reg, args = args[1], args[2:]
    if args[:1] == ["--after"]:                     # wait for another stage to be registered and ended first
        after, args = (args[1] if args[1][:1] == "C" and "-" in args[1] else f"{CAND}-{args[1]}"), args[2:]   # C196: another record's stage by full name
    Q.log(f"{CAND} driver start: " + " ".join(args) + (f" after {after}" if after else "") + (f" after registration of {after_reg}" if after_reg else ""))
    while after and not (after in Q.reg() and not Q.alive(after)):
        time.sleep(60)
    while after_reg and after_reg not in Q.reg():
        time.sleep(60)
    while after_file and not after_file.exists():
        time.sleep(60)
    seen = set()
    while after_alive and seen != set(after_alive):
        seen |= {n for n in after_alive if Q.alive(n)}
        if seen != set(after_alive):
            time.sleep(60)
    for s in args:
        stage(s)
    Q.log("C193 driver end")
