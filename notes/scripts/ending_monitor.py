"""C30's stop rule for a pilot trained from scratch (log #154, H99), applied to an rl.train run's log.jsonl by writing its
--stop-file. Evaluation and control only; training never reads the endings.

  criterion: at least --decisive of the games end by Prizes or no Pokemon, and at most --deckout by deck-out, for
             --run-of iterations running; the run then trains --extra more iterations and stops.
  at --check (default iteration 59, the 60th): if the criterion has not been met, deck-outs (mean of the last 3
             iterations) at or above --fail stop the run (the bootstrap failed); below it the run goes on to its
             --iterations cap (90, chosen in advance).

  .venv/Scripts/python notes/scripts/ending_monitor.py runs/pilot/C30-h99-scratch-s1 --stop-file .../STOP
"""
import argparse
import json
import time
from pathlib import Path


def shares(r: dict):
    e = r["endings"]
    n = max(1, sum(e.values()))
    return (e.get("prizes", 0) + e.get("no-pokemon", 0)) / n, e.get("deck-out", 0) / n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--stop-file", required=True)
    ap.add_argument("--decisive", type=float, default=0.70)
    ap.add_argument("--deckout", type=float, default=0.25)
    ap.add_argument("--run-of", type=int, default=3)
    ap.add_argument("--extra", type=int, default=10)
    ap.add_argument("--check", type=int, default=59)
    ap.add_argument("--fail", type=float, default=0.50)
    ap.add_argument("--poll", type=float, default=30.0)
    a = ap.parse_args(argv)
    log, stop = Path(a.run) / "log.jsonl", Path(a.stop_file)
    met, checked = None, False
    while not stop.exists():
        rows = [json.loads(x) for x in log.read_text().splitlines() if x.strip()] if log.exists() else []
        rows = [r for r in rows if "endings" in r]
        streak = 0
        for r in rows:
            d, o = shares(r)
            streak = streak + 1 if d >= a.decisive and o <= a.deckout else 0
            if streak >= a.run_of and met is None:
                met = r["iteration"]
                print(f"criterion met at iteration {met}; stopping after {met + a.extra}", flush=True)
        last = rows[-1]["iteration"] if rows else -1
        if met is not None and last >= met + a.extra - 1:
            stop.write_text(f"C30 criterion met at {met}; {a.extra} more iterations done (log #154)\n")
            print(f"STOP written after iteration {last}", flush=True)
            break
        if met is None and not checked and last >= a.check:
            checked = True
            o = sum(shares(r)[1] for r in rows[-3:]) / len(rows[-3:])
            if o >= a.fail:
                stop.write_text(f"C30 bootstrap failed: deck-outs {o:.2f} at iteration {last} (log #154)\n")
                print(f"STOP written: deck-outs {o:.2f} at {last}", flush=True)
                break
            print(f"iteration {last}: deck-outs {o:.2f} < {a.fail}, criterion not met; on to the cap", flush=True)
        time.sleep(a.poll)


if __name__ == "__main__":
    main()
