"""C184's queue (runs/probe/C184-recovery-arm/record.md, Amendments 1 and 2): DN, the plain mean Trainer table at kappa 1 with the mass-neutral bonus (--table-neutral), on wide decks rejection-sampled to Trainers 13-17 at init and turnover (--init-t-range 13-17), seeds 50 and 51, against WR, W's recipe from the same starts; and ND, the same neutral bonus from the normal start, seeds 48 and 49, against W (C171). To iteration 44. DR (the plain bonus) isn't resumed: its files stay as a read of the push. One of each first (DN s50, ND s48), then WR s50, then the seconds, one launch at a time. queue_c171's supervisor; stops as the record's: errors, Pokemon slide, wall kill; no Trainer floor for DN and WR, which start near 15; ND's line 15, as D's; G1 watch off. Holds on GPU-PAUSE and row 73 in Screen.launch. WR s50 resumes from its checkpoint at iteration 4, once its STOP is off.
  .venv/Scripts/python notes/scripts/queue_c184.py [--chains-only]
"""
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
sys.path.insert(0, str(ROOT))
import queue_c90 as Q                                    # noqa: E402
import queue_c168 as Q168                                # noqa: E402
import queue_c171 as QC                                  # noqa: E402

D = ROOT / "runs" / "probe" / "C184-recovery-arm"
Q.D = D
QC.D = D
RECORD = "runs/probe/C184-recovery-arm/record.md"
TABLE = "runs/probe/C182-trainer-table-drafting/table.json"
ARMS = [("C184-DN-s50", "DN", 50), ("C184-ND-s48", "ND", 48), ("C184-WR-s50", "WR", 50), ("C184-DN-s51", "DN", 51), ("C184-ND-s49", "ND", 49), ("C184-WR-s51", "WR", 51)]
QC.ARMS = ARMS
ITERS = 45
FIRST = {"DN": 50, "ND": 48, "WR": 50}


def make_screens():
    out = {}
    for name, arm, seed in ARMS:
        run = ROOT / "runs" / "screens" / name
        run.mkdir(parents=True, exist_ok=True)
        (run / "NO_G1_WATCH").write_text("C184's record: the G1 watch prints and doesn't stop this run\n", encoding="utf-8")
        flag = (" --init-t-range 13-17" if arm != "ND" else "") + (f" --table {TABLE} --table-kappa 1 --table-scope trainers --table-neutral" if arm != "WR" else "") + " --save-first"
        note = {"DN": " from Trainers 13-17 with the plain mean Trainer table at kappa 1, mass-neutral", "ND": " with the plain mean Trainer table at kappa 1, mass-neutral", "WR": " from Trainers 13-17, W's recipe"}[arm]
        (run / "chain.sh").write_text(Q168.CHAIN.format(name=name, seed=seed, iters=ITERS, flag=flag, note=note).replace("runs/probe/C168-long-fresh-turnover/record.md", RECORD), encoding="utf-8", newline="\n")
        parts = {"DN": "trainer-table,t-range", "ND": "trainer-table", "WR": "t-range"}[arm]
        extra = ["--components", parts] + (["--replicate-of", f"C184-{arm}-s{FIRST[arm]}"] if seed != FIRST[arm] else [])
        out[name] = Q.Screen(name, "C184", RECORD, run, "prevention", "fresh", extra)
    return out


def in_order(screens, kills):
    """One launch at a time, in ARMS's order: Screen.launch retries while the slots are full, so no later arm takes a slot first. A watch beside each."""
    for n, a, _ in ARMS:
        s = screens[n]
        if not Q.alive(n):
            s.launch(resume=n in Q.reg())
        threading.Thread(target=s.watch, args=(kills[a],), daemon=True).start()


def main():
    screens = make_screens()
    if "--chains-only" in sys.argv:
        print("chains written:", list(screens))
        return
    Q.log("C184 queue start")
    kills = {"DN": lambda rows: Q168.own_kill(rows, trainer_line=0), "WR": lambda rows: Q168.own_kill(rows, trainer_line=0), "ND": lambda rows: Q168.own_kill(rows, trainer_line=15)}
    threading.Thread(target=in_order, args=(screens, kills), daemon=True).start()
    QC.supervise(screens)
    Q.log("C184 queue end")


if __name__ == "__main__":
    main()
