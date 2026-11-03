"""C182's queue (runs/probe/C182-trainer-table-drafting/record.md): arm D, the plain mean Trainer table at kappa 1 on the drafter's Trainer picks (init, turnover's wide decks, proposals), W's recipe otherwise, seeds 48 and 49 side by side, to iteration 44 first. queue_c171's supervisor: stage reads every 15 iterations to this folder's stages.jsonl, G3 probes, the wall kill. Stops: errors, Pokemon slide, median Trainers at or under 15 at 3 reads. G1 watch off (NO_G1_WATCH), as W s49's was. The record's stop at 29, median Trainers at or below W's at both seeds, is read by hand.
  .venv/Scripts/python notes/scripts/queue_c182.py [--chains-only]
"""
import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
sys.path.insert(0, str(ROOT))
import queue_c90 as Q                                    # noqa: E402
import queue_c168 as Q168                                # noqa: E402
import queue_c171 as QC                                  # noqa: E402

D = ROOT / "runs" / "probe" / "C182-trainer-table-drafting"
Q.D = D
QC.D = D
RECORD = "runs/probe/C182-trainer-table-drafting/record.md"
TABLE = "runs/probe/C182-trainer-table-drafting/table.json"
ARMS = [("C182-D-s48", "D", 48), ("C182-D-s49", "D", 49)]
QC.ARMS = ARMS
ITERS = 45


def make_table():
    r = json.loads((ROOT / "runs/probe/C181-table-practice/ranks.json").read_text(encoding="utf-8"))
    a, b = r["48"]["coefficients"], r["49"]["coefficients"]
    (ROOT / TABLE).write_text(json.dumps({n: (a[n] + b[n]) / 2 for n in sorted(set(a) & set(b))}, indent=1), encoding="utf-8")


def make_screens():
    out = {}
    for name, _, seed in ARMS:
        run = ROOT / "runs" / "screens" / name
        run.mkdir(parents=True, exist_ok=True)
        (run / "NO_G1_WATCH").write_text("C182's record: the G1 watch prints and doesn't stop this run\n", encoding="utf-8")
        flag = f" --table {TABLE} --table-kappa 1 --table-scope trainers --save-first"
        note = " with the plain mean Trainer table at kappa 1, init, turnover and proposals"
        (run / "chain.sh").write_text(Q168.CHAIN.format(name=name, seed=seed, iters=ITERS, flag=flag, note=note).replace("runs/probe/C168-long-fresh-turnover/record.md", RECORD), encoding="utf-8", newline="\n")
        out[name] = Q.Screen(name, "C182", RECORD, run, "prevention", "fresh", ["--components", "trainer-table"] + (["--replicate-of", "C182-D-s48"] if seed == 49 else []))
    return out


def main():
    make_table()
    screens = make_screens()
    if "--chains-only" in sys.argv:
        print("chains written:", list(screens))
        return
    Q.log("C182 queue start")
    kill = lambda rows: Q168.own_kill(rows, trainer_line=15)
    ts = [threading.Thread(target=QC.arm, args=(screens[n], kill), daemon=True) for n, _, _ in ARMS]
    for t in ts:                                         # Screen.launch retries while the slots are full
        t.start()
        time.sleep(90)
    QC.supervise(screens)
    for t in ts:
        t.join(timeout=120)
    Q.log("C182 queue end")


if __name__ == "__main__":
    main()
