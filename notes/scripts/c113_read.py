"""C113's readout: per run file (c113_run.py) and pair group, the list's share against its Energy copy, as win share with draws
half ("share", rules i, ii and iii-b) and as event points ("points": full win 3, win on time 2, draw 1 each, loss 0; rule iii-a
on rule i's games, and iii-b); M = the mean over energy+6#r of the list's share, F = the mean of the four focus cards' pooled
prices; per (card, list) prices; endings; the share of games reaching time; Prize ties at time; game length (turns) and its
80th percentile (rule iii-b's T, from the untimed run).
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c113_read.py <run.json> [<run.json> ...]
"""
import collections
import json
import sys

import numpy as np

FOCUS = ["PlusPower", "Gust of Wind", "Item Finder", "Scoop Up"]


def read(path):
    r = json.load(open(path, encoding="utf-8"))
    pairs = {(p["base"], p["variant"]): p for p in r["pairs"]}
    names = r["deck_names"]
    share, pts, tot, n = collections.defaultdict(float), collections.defaultdict(float), collections.defaultdict(float), collections.Counter()
    endings, turns, ties, timed = collections.Counter(), [], 0, 0
    for g in r["results"]:
        p = pairs.get((g["i"], g["j"]))
        if p is None or g.get("error"):
            continue
        key = (p["group"], names[p["base"]])
        win = g["winner"] == g["iSeat"]
        draw = g["winner"] not in (1, 2)
        timeout = g.get("ending") == "time"
        share[key] += 0.5 if draw else 1.0 if win else 0.0
        lp = 1 if draw else (2 if timeout else 3) if win else 0
        cp = 1 if draw else 0 if win else (2 if timeout else 3)
        pts[key] += lp
        tot[key] += lp + cp
        n[key] += 1
        endings[g.get("ending") or "draw/cut"] += 1
        timed += timeout
        ties += timeout and draw
        if g.get("turns") is not None:
            turns.append(g["turns"])
    by = {k: {"share": share[k] / n[k], "points": pts[k] / tot[k], "n": n[k]} for k in n}
    out = {"file": path, "rule": r["rule"], "seed": r["seed"], "pilot": r["pilot"], "games": sum(n.values()), "endings": dict(endings),
           "time_share": round(timed / max(sum(n.values()), 1), 4), "tie_share_at_time": round(ties / max(timed, 1), 4),
           "turns_mean": round(float(np.mean(turns)), 2) if turns else None,
           "turns_p80": float(np.percentile(turns, 80)) if turns else None}
    for metric in ("share", "points"):
        m = [v[metric] for (g, l), v in by.items() if g.startswith("energy+6")]
        out[f"M_{metric}"] = round(float(np.mean(m)), 4)
        cards = {}
        for c in FOCUS:
            per = {l: round(v[metric], 4) for (g, l), v in by.items() if g == c}
            cards[c] = {"pooled": round(float(np.mean(list(per.values()))), 4), "per_list": per}
        out[f"cards_{metric}"] = cards
        out[f"F_{metric}"] = round(float(np.mean([cards[c]["pooled"] for c in FOCUS])), 4)
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        o = read(p)
        json.dump(o, open(p.replace(".json", ".read.json"), "w"), indent=1)
        print(json.dumps({k: o[k] for k in ("rule", "seed", "games", "endings", "time_share", "tie_share_at_time", "turns_mean", "turns_p80",
                                            "M_share", "F_share", "M_points", "F_points")}))
