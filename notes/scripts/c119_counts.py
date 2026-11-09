"""C119 (runs/screens/C119-gate-base/record.md): the tempo-card counts of a screen's G1 set, A99's per-card copies a deck (#412)
on C90 Amendment 3's set. Evaluation only, CPU, no games.
The set at an iteration with a population snapshot: the top 12 decks by z on that iteration's log row (aa_window.dist's set),
mapped by id to the snapshot's decks, their P / T / E checked against the row's shapes. Per run: mean copies a deck of
PlusPower, Gust of Wind, Item Finder and Scoop Up (T4, their sum), Computer Search, Professor Oak, Bill and Energy Removal; the
median P / T / E of the set and of the population; then the runs' mean and sd, and the 24 archived lists' means beside them.
Amendment 1 (#538): each run's T4 SE over its 12 decks, and its T4 range 2.292 ± 2 × sqrt(0.144² + SE²) (C90 s1-s4's mean and sd).
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c119_counts.py --runs C90-R1-K-base-paired C90-R1-K-base-paired-s2 ... --iter 29
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.decks import Pool, archived_decks   # noqa: E402

T4 = ["PlusPower", "Gust of Wind", "Item Finder", "Scoop Up"]
CARDS = T4 + ["Computer Search", "Professor Oak", "Bill", "Energy Removal"]
SUPER = {c["fullName"]: c["superType"] for c in json.loads((ROOT / "notes/data/cards/pool.json").read_text(encoding="utf-8"))["cards"]}
bare = lambda n: n.rsplit(" ", 1)[0]


def shape(deck):
    return [sum(SUPER[c] == k for c in deck) for k in (1, 2, 3)]


def counts(decks):
    per = {c: float(np.mean([sum(bare(x) == c for x in d) for d in decks])) for c in CARDS}
    per["T4"] = sum(per[c] for c in T4)
    return per


def g1_set(run: Path, it: int):
    rows = {}
    for x in (run / "log.jsonl").read_text().splitlines():
        if x.strip():
            r = json.loads(x)
            rows[r["iter"]] = r
    r = rows[it]
    z = np.array([np.nan if v is None else v for v in r["z"]], dtype=float)
    top = np.argsort(-np.nan_to_num(z, nan=-1))[:12]
    pop = torch.load(run / f"population_it{it:04d}.pt", map_location="cpu", weights_only=False)["population"]
    by_id = {a["id"]: a["deck"] for a in pop}
    decks = [by_id[r["ids"][k]] for k in top]
    match = sum(shape(d) == list(r["shapes"][k]) for d, k in zip(decks, top))
    return decks, [a["deck"] for a in pop], match


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True, help="screen names under runs/screens")
    ap.add_argument("--iter", type=int, default=29)
    ap.add_argument("--out")
    a = ap.parse_args()
    pool = Pool()
    lists = [pool.names(v) for _, v in archived_decks(pool)]
    res = {"iter": a.iter, "lists": {**counts(lists), "median_PTE": np.median([shape(d) for d in lists], 0).tolist()}, "runs": {}}
    for name in a.runs:
        g1, pop, match = g1_set(ROOT / "runs" / "screens" / name, a.iter)
        t4 = [sum(sum(bare(x) == c for x in d) for c in T4) for d in g1]   # Amendment 1 (#538): the seed's own SE of T4
        res["runs"][name] = {**counts(g1), "T4_se": round(float(np.std(t4, ddof=1) / np.sqrt(len(t4))), 3),
                             "T4_range_amendment1": [round(2.292 - 2 * float(np.hypot(0.144, np.std(t4, ddof=1) / np.sqrt(len(t4)))), 3),
                                                     round(2.292 + 2 * float(np.hypot(0.144, np.std(t4, ddof=1) / np.sqrt(len(t4)))), 3)],
                             "g1_median_PTE": np.median([shape(d) for d in g1], 0).tolist(),
                             "pop_median_PTE": np.median([shape(d) for d in pop], 0).tolist(), "shapes_matching_log_row": f"{match}/12"}
    keys = CARDS + ["T4"]
    v = {k: [res["runs"][n][k] for n in a.runs] for k in keys}
    res["mean_sd"] = {k: [round(float(np.mean(v[k])), 3), round(float(np.std(v[k], ddof=1)), 3) if len(a.runs) > 1 else None] for k in keys}
    if len(a.runs) > 1:
        m, s = res["mean_sd"]["T4"]
        res["T4_band_mean_pm_2sd"] = [round(m - 2 * s, 3), round(m + 2 * s, 3)]
    if a.out:
        Path(ROOT / a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
