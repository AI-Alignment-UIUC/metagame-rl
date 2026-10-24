"""The screens' trajectories (log #128), from their log.jsonl rows: per iteration the population's median Pokémon /
Trainers / Energy, the 12 decks with the best results that iteration (their mean shape and its L1 distance from the
human lists' medians, rl/lab.py HUMAN_SHAPE), the draft head's incoming entropy, how many decks --select moved, and the
share of games ending by deck-out. Evaluation only.

  .venv/Scripts/python notes/scripts/screen_watch.py [names...] [--every 5] [--main]
"""
import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HUMAN = np.array([13.5, 28.0, 18.0])


def rows(path: Path) -> list:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


def line(r: dict) -> str:
    sh = np.array(r["shapes"], dtype=float)
    z = np.array([np.nan if x is None else x for x in r["z"]], dtype=float)
    top = np.argsort(-np.nan_to_num(z, nan=-1))[:12]
    t = sh[top].mean(0)
    med = np.median(sh, 0)
    n = max(1, sum(r["endings"].values()))
    sel = r.get("select", {}).get("moved")
    d = r.get("draft", {})
    return (f"{r['iter']:4d}  med {med[0]:4.1f}/{med[1]:4.1f}/{med[2]:4.1f}  top12 {t[0]:4.1f}/{t[1]:4.1f}/{t[2]:4.1f} "
            f"dist {np.abs(t - HUMAN).sum():5.1f}  h_in {d.get('h_in', float('nan')):5.2f}  moved {sel if sel is not None else '-':>3}"
            f"  deckout {r['endings'].get('deck-out', 0) / n:4.2f}  steps {r['steps_per_game']:5.1f}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--every", type=int, default=5)
    ap.add_argument("--main", action="store_true", help="also the lab's main line from 440")
    a = ap.parse_args(argv)
    runs = [ROOT / "runs" / "screens" / n for n in a.names] if a.names else sorted((ROOT / "runs" / "screens").glob("*"))
    if a.main:
        runs = [ROOT / "runs" / "lab" / "main"] + runs
    for run in runs:
        rs = [r for r in rows(run / "log.jsonl") if run.name != "main" or r["iter"] >= 440]
        if not rs:
            continue
        print(f"== {run.name}")
        for i, r in enumerate(rs):
            if i % a.every == 0 or i == len(rs) - 1:
                print("  " + line(r))


if __name__ == "__main__":
    main()
