"""C179 with its Amendment 1 (runs/probe/C179-shape-dose/record.md): copy minus list, event points/3, on the same deals, averaged by list, bootstrap over the 24 lists. Bands at both pilots: R-additive, a dose-14 arm at +0.10 or more and 2 SE, the same arm at both, and it says which. R-nonlinear, both dose-14 arms at +0.03 or less at both. Between otherwise. Beside it: win share, full wins and full losses; per-list prices; which Trainers leave most; for each arm what was added, the realised P/T/E and the colourless share, against W s49's top 12.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c179_read.py [--glob "G_*.json"] [--summary summary.json]
"""
import argparse
import collections
import json
from pathlib import Path

import numpy as np
import torch

from c139_read import pts, r3
from probe_meta_premise import best_decks
from rl.decks import Pool

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "runs/probe/C179-shape-dose"
ARMS = ("d6", "d14", "d14n")
pool = Pool()
card = {c["fullName"]: c for c in pool.cards}


def shape(cards):
    return [sum(card[c]["superType"] == s for c in cards) for s in (1, 2, 3)]


def colourless(cards):
    p = [x for x in cards if card[x]["superType"] == 1]
    return sum(not any(v for t, v in enumerate(card[x]["types"]) if t != 0) for x in p) / max(1, len(p))


def boot(x, reps=4000):
    rng = np.random.default_rng(179)
    x = np.array(x)
    return float(np.std([x[rng.integers(len(x), size=len(x))].mean() for _ in range(reps)]))


def read(f, copies):
    r = json.loads(f.read_text(encoding="utf-8"))
    n0 = r["n_lists"]
    ok = [x for x in r["results"] if not x.get("error")]
    deals = collections.defaultdict(dict)
    for x in ok:
        deals[x["seed"]][x["i"]] = x
    per = {a: collections.defaultdict(list) for a in ARMS}
    side = {a: collections.Counter() for a in ARMS + ("list",)}
    n = collections.Counter()
    for seed, g in deals.items():
        base = next((v for i, v in g.items() if i < n0), None)
        if base is None:
            continue
        p0 = pts(base)[0]
        for t in ("list",):
            n[t] += 1
            side[t]["win"] += base["winner"] == base["iSeat"]
            side[t]["full_win"] += base["winner"] == base["iSeat"] and base.get("ending") != "time"
            side[t]["full_loss"] += base["winner"] in (1, 2) and base["winner"] != base["iSeat"] and base.get("ending") != "time"
            side[t]["pts"] += p0
        for i, v in g.items():
            if i < n0:
                continue
            c = copies[i - n0]
            a = c["arm"]
            per[a][c["list"]].append(pts(v)[0] - p0)
            n[a] += 1
            side[a]["win"] += v["winner"] == v["iSeat"]
            side[a]["full_win"] += v["winner"] == v["iSeat"] and v.get("ending") != "time"
            side[a]["full_loss"] += v["winner"] in (1, 2) and v["winner"] != v["iSeat"] and v.get("ending") != "time"
            side[a]["pts"] += pts(v)[0]
    out = {"pilot": r["pilot"], "games": r["last"]["games"], "errors": r["last"]["errors"], "games_per_s": r["last"]["games_per_s"], "endings": r["last"]["endings"], "search": bool(r.get("search")), "arms": {}}
    out["list_side"] = {k: r3(side["list"][k] / max(1, n["list"])) for k in ("win", "full_win", "full_loss", "pts")}
    for a in ARMS:
        if not per[a]:
            continue
        by = {k: float(np.mean(v)) for k, v in per[a].items()}
        vals = list(by.values())
        out["arms"][a] = {"change": r3(float(np.mean(vals))), "se_lists": r3(boot(vals)), "lists": len(vals), "games": n[a], **{k: r3(side[a][k] / max(1, n[a])) for k in ("win", "full_win", "full_loss", "pts")}, "by_list": {str(k): r3(v) for k, v in sorted(by.items())}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="G_*.json")
    ap.add_argument("--summary", default="summary.json")
    a = ap.parse_args()
    copies = json.loads((D / "decks.json").read_text(encoding="utf-8"))
    res = {}
    for f in sorted(D.glob(a.glob)):
        res[f.stem] = read(f, copies)
    info = {}
    for arm in ARMS:
        cs = [c for c in copies if c["arm"] == arm]
        info[arm] = {"P_T_E": [r3(float(x)) for x in np.mean([shape(c["cards"]) for c in cs], 0)], "pokemon_added_own": r3(float(np.mean([len(c["added_pokemon"]) for c in cs]))), "pokemon_added_new": r3(float(np.mean([len(c["added_new"]) for c in cs]))), "energy_added": r3(float(np.mean([len(c["added_energy"]) for c in cs]))), "stopped_to_energy": r3(float(np.mean([c["stopped_to_energy"] for c in cs]))), "colourless_share": r3(float(np.mean([colourless(c["cards"]) for c in cs])))}
        info[arm]["trainers_out_top"] = collections.Counter(card[x]["name"] for c in cs for x in c["trainers_out"]).most_common(8)
        info[arm]["new_names_top"] = collections.Counter(card[x]["name"] for c in cs for x in c["added_new"]).most_common(8)
    lists = json.loads((ROOT / "runs/probe/C163-draw-deck-field/L.json").read_text(encoding="utf-8"))
    info["lists"] = {"P_T_E": [r3(float(x)) for x in np.mean([shape(d["cards"]) for d in lists], 0)], "colourless_share": r3(float(np.mean([colourless(d["cards"]) for d in lists])))}
    for tag, path in (("W_s49_at_74", "runs/screens/C171-W-s49/population_it0074.pt"), ("W_s49_at_79", "runs/screens/C171-W-s49/population_it0079.pt")):
        ds = [x["cards"] for x in best_decks(path, 12)]
        info[tag] = {"P_T_E": [r3(float(x)) for x in np.mean([shape(d) for d in ds], 0)], "colourless_share": r3(float(np.mean([colourless(d) for d in ds])))}
    out = {"cells": res, "decks": info}
    if len(res) >= 2:
        passes = lambda v, arm: v["arms"].get(arm) and v["arms"][arm]["change"] >= 0.10 and v["arms"][arm]["change"] >= 2 * v["arms"][arm]["se_lists"]
        low = lambda v, arm: v["arms"].get(arm) and v["arms"][arm]["change"] <= 0.03
        cells = list(res.values())
        add = [arm for arm in ("d14", "d14n") if all(passes(v, arm) for v in cells)]
        non = all(low(v, arm) for v in cells for arm in ("d14", "d14n"))
        out["band"] = f"R-additive on {'+'.join(add)}" if add else "R-nonlinear" if non else "between"
    (D / a.summary).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("band", out.get("band"))
    for k, v in res.items():
        print(k, {q: v[q] for q in ("pilot", "games", "errors", "games_per_s", "endings", "list_side")})
        for arm, x in v["arms"].items():
            print("  ", arm, {q: x[q] for q in x if q != "by_list"})
    print(json.dumps(info))


if __name__ == "__main__":
    main()
