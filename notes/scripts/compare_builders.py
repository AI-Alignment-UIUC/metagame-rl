"""Compares the three builder designs of log #27 (log #34): PSRO runs that differ only in how the
search scores a candidate deck (rl/search.py: games, model, value).

Each run's final Nash mixture is taken from its own matrix. Then one shared panel, every run's
support decks plus the 24 archived lists, plays a fresh matrix under the same pilot, and from it:
  - head to head: each run's mixture against each other run's mixture
  - against the field: each mixture against the archived lists, uniformly weighted
  - exploitability in the panel: the best panel deck's win rate against the mixture
  - the panel's own Nash: how much weight each run's decks get
plus, from each run's log: staple counts, nearest archetypes, how well the score each proposal
was chosen on predicted its real result, and how many candidates the search scored.

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/compare_builders.py --runs runs/cmp-games,runs/cmp-model,runs/cmp-value \
        --policy runs/deckout-w0/model_it00014.pt --games 60 --json notes/data/eval/builders_compare.json
"""
import argparse
import collections
import json
import re

import numpy as np

from rl.decks import Pool, archived_decks, overlap
from rl.gpu_matrix import GpuMatrix
from rl.nash import solve

STAPLES = ["Computer Search", "Item Finder", "Double Colorless Energy", "Professor Oak", "Bill", "Gust of Wind",
           "PlusPower", "Energy Removal", "Super Energy Removal", "Scyther"]


def label(name):
    m = re.search(r"\(([^)]*)\)\s*$", name)
    return m.group(1) if m else name


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--games", type=int, default=60)
    ap.add_argument("--min-weight", type=float, default=0.01, help="support decks below this weight are left out")
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    pool = Pool()
    archived = archived_decks(pool)
    arch_counts = np.mean([[collections.Counter(pool.name[pool.id[c]] for c in pool.names(v)).get(s, 0) for s in STAPLES]
                           for _, v in archived], 0)

    runs, panel, owner = {}, [], []
    for path in args.runs.split(","):
        key = path.rstrip("/").split("/")[-1]
        pop = json.load(open(f"{path}/population.json", encoding="utf-8"))
        m = np.load(f"{path}/matrix.npz")
        sigma, _ = solve(m["wins"] / np.maximum(m["games"], 1))
        sup = [i for i in np.argsort(-sigma) if sigma[i] >= args.min_weight]
        w = sigma[sup] / sigma[sup].sum()
        log = [json.loads(l) for l in open(f"{path}/log.jsonl")]
        real = [r for row in log for r in row.get("realized", [])]
        searches = [row["search"] for row in log if "search" in row]
        vecs = [pool.vector(pop[i]["cards"]) for i in sup]
        counts = np.array([[collections.Counter(pool.name[pool.id[c]] for c in pop[i]["cards"]).get(s, 0) for s in STAPLES]
                           for i in sup])
        runs[key] = {
            "population": len(pop),
            "support": [{"deck": pop[i]["name"], "weight": round(float(x), 4),
                         "nearest": max(((label(n), round(overlap(v, a), 3)) for n, a in archived), key=lambda t: t[1])}
                        for i, x, v in zip(sup, w, vecs)],
            "staples_weighted": {s: round(float(c), 2) for s, c in zip(STAPLES, w @ counts)},
            "proposals": len(real),
            "chosen_score_vs_real_mae": round(float(np.mean([abs(r["predicted"] - r["real"]) for r in real])), 4) if real else None,
            "scorer_vs_real_mae": round(float(np.mean([abs(r["scorer"] - r["real"]) for r in real])), 4) if real and "scorer" in real[0] else None,
            "mean_real_vs_its_mixture": round(float(np.mean([r["real"] for r in real])), 4) if real else None,
            "real_by_iteration": [round(float(np.mean([r["real"] for r in row["realized"]])), 3) for row in log if row.get("realized")],
            "candidates_scored": sum(s["candidates_scored"] for s in searches),
            "search_seconds": round(sum(s["seconds"] for s in searches), 1),
        }
        for i, x in zip(sup, w):
            panel.append({"name": f"{key}: {pop[i]['name']}", "cards": pop[i]["cards"]})
            owner.append((key, float(x)))
    n_runs = len(panel)
    for name, v in archived:
        panel.append({"name": f"archived: {name}", "cards": pool.names(v)})
        owner.append(("archived", 1.0 / len(archived)))

    gm = GpuMatrix(args.policy, 14)
    try:
        W, G, _ = gm.play(panel, args.games, args.seed)
        speed = gm.last
    finally:
        gm.close()
    P = W / np.maximum(G, 1)
    keys = list(runs) + ["archived"]
    mix = {k: np.array([x if o == k else 0.0 for o, x in owner]) for k in keys}
    h2h = {a: {b: round(float(mix[a] @ P @ mix[b]), 4) for b in keys if b != a} for a in keys}
    for k in runs:
        br = P @ mix[k]                          # each panel deck's win rate against the mixture
        j = int(np.argmax(br))
        runs[k]["vs_archived_field"] = h2h[k]["archived"]
        runs[k]["exploitability"] = {"best_response": panel[j]["name"], "win": round(float(br[j]), 4)}
    sigma, _ = solve(P)
    share = {k: round(float(sum(s for s, (o, _) in zip(sigma, owner) if o == k)), 4) for k in keys}
    out = {"games_per_pair": args.games, "panel": len(panel), "from_runs": n_runs, "matrix": speed,
           "head_to_head": h2h, "panel_nash_share": share, "archived_staples_mean": dict(zip(STAPLES, np.round(arch_counts, 2).tolist())),
           "runs": runs}
    for k, r in runs.items():
        print(f"{k}: vs field {r['vs_archived_field']:.3f}, exploitability {r['exploitability']['win']:.3f}, "
              f"panel Nash share {share[k]:.2f}, proposals real {r['mean_real_vs_its_mixture']}, "
              f"score MAE {r['chosen_score_vs_real_mae']}, candidates {r['candidates_scored']}")
    print("head to head:", json.dumps(h2h))
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
