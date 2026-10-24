"""Selection's lean (S37, log #204): accepted minus proposed Pokemon / Trainers / Energy a move, per window.

Reads the `select` records (`acc`, `prop`) of a metagame run's log.jsonl and prints, for each window of iterations
counted from the run's first logged iteration, the mean and the SE over iterations.

    .venv/Scripts/python notes/scripts/select_lean.py C53-h20.fju-c49sd199-s1 scr-ctl479 [--window 10]
"""
import argparse
import json
import math
import pathlib


def lean(path):
    rows = []
    for line in open(path / "log.jsonl"):
        d = json.loads(line)
        s = d.get("select") or {}
        if "acc" in s and "prop" in s:
            rows.append((d.get("iter"), [a - p for a, p in zip(s["acc"], s["prop"])]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="run folders, or names under runs/screens")
    ap.add_argument("--window", type=int, default=10)
    args = ap.parse_args()
    for r in args.runs:
        path = pathlib.Path(r)
        if not path.exists():
            path = pathlib.Path("runs/screens") / r
        rows = lean(path)
        print(f"== {path.name}: {len(rows)} iterations with select records")
        for w in range(0, len(rows), args.window):
            chunk = rows[w:w + args.window]
            n = len(chunk)
            cells = []
            for k in range(3):
                xs = [x[k] for _, x in chunk]
                m = sum(xs) / n
                se = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1) / n) if n > 1 else float("nan")
                cells.append(f"{m:+.2f} ({se:.2f})")
            print(f"  iters {chunk[0][0]}-{chunk[-1][0]} (n {n}): P / T / E  " + " / ".join(cells))


if __name__ == "__main__":
    main()
