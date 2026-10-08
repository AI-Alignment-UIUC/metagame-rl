"""Best-of-K ceiling per deck against SimpleBot (log #47): the same deals (evaluate.js --seed) played once
greedily and K times sampling the pilot's moves (--agent-seed). A deal counts as winnable if any of
the K + 1 plays won it. Later shuffles and coin flips follow the actions taken, so a sampled play can
also be luckier: this estimates the ceiling, it does not bound it.

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/ceiling_by_deck.py runs/ceiling [--top 6] [--out decks.json]
"""
import argparse
import collections
import glob
import json
import os

ap = argparse.ArgumentParser()
ap.add_argument("dir")
ap.add_argument("--top", type=int, default=6, help="how many decks with the largest gap to write out")
ap.add_argument("--out")
args = ap.parse_args()

greedy = json.load(open(os.path.join(args.dir, "greedy.json")))["rows"]
samples = [json.load(open(f))["rows"] for f in sorted(glob.glob(os.path.join(args.dir, "sample*.json")))]
won = {r["seed"]: r["xWins"] for r in greedy}
best = dict(won)
for rows in samples:
    for r in rows:
        best[r["seed"]] = max(best.get(r["seed"], 0), r["xWins"])
deck = {r["seed"]: r["xDeck"] for r in greedy}

by = collections.defaultdict(lambda: [0, 0.0, 0.0])
for s, d in deck.items():
    by[d][0] += 1
    by[d][1] += won[s]
    by[d][2] += best[s]
rows = sorted(((d, n, g / n, b / n) for d, (n, g, b) in by.items()), key=lambda x: -(x[3] - x[2]))
n = len(won)
print(f"{n} deals, K = {len(samples)} sampled plays each: greedy {sum(won.values()) / n:.3f}, "
      f"best-of-{len(samples) + 1} {sum(best.values()) / n:.3f}, never won {sum(1 for v in best.values() if v == 0)} deals")
print(f"{'deck':58s} {'n':>3s} {'greedy':>7s} {'ceiling':>8s} {'gap':>6s}")
for d, k, g, b in rows:
    print(f"{d[:58]:58s} {k:3d} {g:7.3f} {b:8.3f} {b - g:6.3f}")
if args.out:
    json.dump([d for d, *_ in rows[:args.top]], open(args.out, "w"), indent=1)
