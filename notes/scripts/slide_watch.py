"""The Pokemon-slide harm stop (C150 Amendment 2, kept for C153): a screen's population median Pokemon count (log.jsonl's
shape_quartiles) rising by 4 or more within any 10 iterations. Prints the first such window; with --stop it also writes "slide ..." to
the run's STOP, so rl.metagame ends after its current iteration (the chain then ends that stage). Run beside training, as g1_watch.py.
  .venv/Scripts/python notes/scripts/slide_watch.py runs/screens/<run> [--stop]
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--rise", type=float, default=4.0)
    ap.add_argument("--window", type=int, default=10)
    ap.add_argument("--stop", action="store_true")
    a = ap.parse_args()
    run = Path(a.run)
    rows = [json.loads(x) for x in (run / "log.jsonl").read_text().splitlines() if x.strip()]
    m = [r["shape_quartiles"]["pokemon"][1] for r in rows]
    hit = next(((i, j) for j in range(len(m)) for i in range(max(0, j - a.window + 1), j) if m[j] - m[i] >= a.rise), None)
    if hit is None:
        return
    msg = f"slide: median Pokemon {m[hit[0]]} -> {m[hit[1]]} (iterations {rows[hit[0]]['iter']}-{rows[hit[1]]['iter']})"
    print(msg)
    stop = run / "STOP"
    if a.stop and "slide" not in (stop.read_text() if stop.exists() else ""):
        with open(stop, "a") as f:
            f.write(msg + "\n")


if __name__ == "__main__":
    main()
