"""The G1 watch for drafting-lever screens (research, C120 Amendment 1; from C121 on): a lever's screen stops if its last-5 G1
(the mean of aa_window.dist over the last 5 logged iterations) stays above --above (17.77, C93's ungated mean) for --run-of
(5) consecutive iterations at or after --after (15). Prints FIRE or OK with the trail; with --stop, a FIRE writes "g1watch" to
the run's STOP file (rl.metagame's --stop-file ends it after the current iteration). Base measurements don't use it.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/g1_watch.py runs/screens/<run> [--stop]
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aa_window as aw   # noqa: E402


def check(run: Path, above: float = 17.77, after: int = 15, run_of: int = 5):
    rs = aw.rows(run)
    its = sorted(rs)
    d = {i: aw.dist(rs[i]) for i in its}
    last5 = {i: float(np.mean([d[j] for j in range(i - 4, i + 1)])) for i in its if all(j in d for j in range(i - 4, i + 1))}
    streak, fire = 0, None
    for i in sorted(last5):
        if i < after:
            continue
        streak = streak + 1 if last5[i] > above else 0
        if streak >= run_of and fire is None:
            fire = i
    return fire, {i: round(v, 2) for i, v in last5.items() if i >= after}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--above", type=float, default=17.77)
    ap.add_argument("--after", type=int, default=15)
    ap.add_argument("--run-of", type=int, default=5)
    ap.add_argument("--stop", action="store_true")
    a = ap.parse_args()
    run = Path(a.run)
    fire, trail = check(run, a.above, a.after, a.run_of)
    if fire is not None and a.stop:
        (run / "STOP").write_text("g1watch\n")
    print(("FIRE at iteration %d" % fire) if fire is not None else "OK", trail)
