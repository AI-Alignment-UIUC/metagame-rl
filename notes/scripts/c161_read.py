"""C161 (runs/probe/C161-search-disagreement/record.md): per Trainer c, over the searched decisions where a play of c is legal (n_c),
d_c = the share where C135's SV search plays c and greedy doesn't, a_c = the reverse share, and d_c - a_c with a 95% bootstrap CI
clustered by game (2,000 resamples of the games); also each side's play rate of c. Trainers with n_c >= 30 are ranked by d_c - a_c,
and the record's bands read on the top 5 (the human-list cards judge the signal only, row 86). Writes summary<tag>.json.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c161_read.py [--tag ""]
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C161-search-disagreement"
LACK = ("Professor Oak", "Bill", "Computer Search", "PlusPower", "Gust of Wind", "Item Finder", "Scoop Up")
bare = lambda k: re.sub(r" [A-Z0-9]+$", "", k.split("|")[1]) if k.startswith("trainer|") else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="")
    ap.add_argument("--min-n", type=int, default=30)
    a = ap.parse_args()
    rows = [json.loads(x) for x in (OUT / f"decisions{a.tag}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    res = json.loads((OUT / f"results{a.tag}.json").read_text(encoding="utf-8"))
    games = sorted({r["seed"] for r in rows})
    gi = {s: k for k, s in enumerate(games)}
    names = sorted({c for r in rows for c in r["legal"]})
    # per game and Trainer: [n, search plays and greedy doesn't, greedy plays and search doesn't, search plays, greedy plays]
    T = np.zeros((len(games), len(names), 5))
    ni = {c: k for k, c in enumerate(names)}
    for r in rows:
        s, g = bare(r["search"]), bare(r["greedy"])
        for c in r["legal"]:
            T[gi[r["seed"]], ni[c]] += [1, s == c and g != c, g == c and s != c, s == c, g == c]
    rng = np.random.default_rng(161)
    boot = T[rng.integers(len(games), size=(2000, len(games)))].sum(1)          # resampled games, summed
    tot = T.sum(0)
    out = []
    for c, k in ni.items():
        n = tot[k, 0]
        if n < a.min_n:
            continue
        bn = np.maximum(boot[:, k, 0], 1)
        bd = (boot[:, k, 1] - boot[:, k, 2]) / bn
        out.append({"trainer": c, "n": int(n), "d": round(tot[k, 1] / n, 4), "a": round(tot[k, 2] / n, 4),
                    "d_minus_a": round((tot[k, 1] - tot[k, 2]) / n, 4), "ci95": [round(float(np.percentile(bd, 2.5)), 4),
                    round(float(np.percentile(bd, 97.5)), 4)], "search_plays": round(tot[k, 3] / n, 4), "greedy_plays": round(tot[k, 4] / n, 4),
                    "games": int((T[:, k, 0] > 0).sum())})
    out.sort(key=lambda x: -x["d_minus_a"])
    top = [x["trainer"] for x in out[:5]]
    hits = sum(c in LACK for c in top)
    summary = {"games": len(res), "errors": sum(1 for x in res if x.get("error")), "games_with_searches": len(games),
               "decisions": len(rows), "search_differs": round(sum(r["search"] != r["greedy"] for r in rows) / max(len(rows), 1), 4),
               "greedy_is_argmax": round(sum(r["greedy"] == r["argmax"] for r in rows) / max(len(rows), 1), 4),
               "top5": top, "top5_hits": hits, "band": "R-signal" if hits >= 2 else "R-signal-off" if hits == 0 else "between",
               "trainers": out}
    (OUT / f"summary{a.tag}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "trainers"}))
    for x in out:
        print(f"  {x['trainer']:24s} n {x['n']:5d}  d {x['d']:.3f}  a {x['a']:.3f}  d-a {x['d_minus_a']:+.3f} "
              f"[{x['ci95'][0]:+.3f}, {x['ci95'][1]:+.3f}]  search {x['search_plays']:.3f}  greedy {x['greedy_plays']:.3f}")


if __name__ == "__main__":
    main()
