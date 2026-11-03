"""C187's queue (runs/probe/C187-head-off/record.md): H0, W's recipe with the draft head frozen at its fresh start (--draft-lr 0), seeds 48 and 49, to iteration 44, one seed first, seed 49 once C184's first round is up. queue_c171's supervisor; stops as the record's: errors, Pokemon slide, wall kill, median Trainers at or under 15 at 3 reads, G1 watch off. Holds on GPU-PAUSE and row 73 in Screen.launch.
  .venv/Scripts/python notes/scripts/queue_c187.py [--chains-only]
"""
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

D = ROOT / "runs" / "probe" / "C187-head-off"
Q.D = D
QC.D = D
RECORD = "runs/probe/C187-head-off/record.md"
ARMS = [("C187-H0-s48", "H0", 48), ("C187-H0-s49", "H0", 49)]
QC.ARMS = ARMS
ITERS = 45


def make_screens():
    out = {}
    for name, _, seed in ARMS:
        run = ROOT / "runs" / "screens" / name
        run.mkdir(parents=True, exist_ok=True)
        (run / "NO_G1_WATCH").write_text("C187's record: the G1 watch prints and doesn't stop this run\n", encoding="utf-8")
        chain = Q168.CHAIN.format(name=name, seed=seed, iters=ITERS, flag=" --save-first", note=", W's recipe with the draft head frozen").replace("runs/probe/C168-long-fresh-turnover/record.md", RECORD)
        assert chain.count("--draft-lr 0.0003") == 1
        (run / "chain.sh").write_text(chain.replace("--draft-lr 0.0003", "--draft-lr 0"), encoding="utf-8", newline="\n")
        out[name] = Q.Screen(name, "C187", RECORD, run, "prevention", "fresh", ["--components", "head-off"] + (["--replicate-of", "C187-H0-s48"] if seed == 49 else []))
    return out


def in_order(screens, kill):
    """Seed 48 now; seed 49 only once C184's first round is up (WR s50 alive, or finished), so it doesn't take DN s50's or ND s48's slot."""
    first = ROOT / "runs/screens/C184-WR-s50/population_it0044.pt"
    for n, _, seed in ARMS:
        while seed != 48 and not (Q.alive("C184-WR-s50") or first.exists()):
            time.sleep(60)
        s = screens[n]
        if not Q.alive(n):
            s.launch(resume=n in Q.reg())
        threading.Thread(target=s.watch, args=(kill,), daemon=True).start()


def main():
    screens = make_screens()
    if "--chains-only" in sys.argv:
        print("chains written:", list(screens))
        return
    Q.log("C187 queue start")
    kill = lambda rows: Q168.own_kill(rows, trainer_line=15)
    threading.Thread(target=in_order, args=(screens, kill), daemon=True).start()
    QC.supervise(screens)
    Q.log("C187 queue end")


if __name__ == "__main__":
    main()
