"""C176 with its Amendment 1 (runs/probe/C176-sampled-price/record.md): the Trainers' price under sampled play, as the loop's population games, against greedy on the same decks, pairs and deals, paired by pod. C49-sd on both tables, s48 and s49, 20 pods each. W s48's last net on the rival fit's 6 pods is a beside read. Mean beta over the 42 Trainers, sampled - greedy, jackknife. R-regime-differs: |change| at 0.004 or more and 2 SE, the same sign at both seeds. R-same: under 0.002 at both, with an SE that excludes 0.004. Between otherwise. With no band: the Spearman of per-card prices across regimes, the lists' top 12, T4, draw, rho_L, the shape optimum, endings, the capped share.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c176_read.py
"""
import collections
import json

import numpy as np

import c165_read as R
import c173_b1 as B
from c139_read import r3

D = B.ROOT / "runs/probe/C176-sampled-price"
TABLES = B.ROOT / "runs/probe/C171-table-drafting"
CELLS = {"s48": ("c49s48_p*.json", TABLES / "table-s48", TABLES / "table-s48/games.json"),
         "s49": ("c49s49_p*.json", TABLES / "table-s49", TABLES / "table-s49/games.json"),
         "W54": ("w_p*.json", TABLES / "table-s48", B.ROOT / "runs/probe/C173-search-table/B1/rival_54.json")}


def load(pattern):
    res, endings = [], collections.Counter()
    for f in sorted(D.glob(pattern)):
        r = json.loads(f.read_text(encoding="utf-8"))
        res += r["results"]
        endings.update(r["last"]["endings"])
    return res, dict(endings)


def caps(pattern):
    games, turns = set(), set()
    for f in sorted(D.glob(pattern + ".caps")):
        for line in open(f, encoding="utf-8"):
            if line.strip():
                s, t = json.loads(line)[:2]
                games.add(s)
                turns.add((s, t))
    return len(games), len(turns)


def main():
    out, m = {"cells": {}}, {}
    for name, (pattern, table, greedy_file) in CELLS.items():
        res, endings = load(pattern)
        if not res:
            continue
        R.OUT = table
        ds = R.load_design()
        tn = ds["tn"]
        target = R.lists_mean_copies(tn)
        groups = {"all_42": list(tn), "lists_top_12": [tn[i] for i in np.argsort(-target)[:12]], "T4": list(R.T4), "draw": list(R.DRAW), "PlusPower": ["PlusPower"]}
        groups["other_30"] = [n for n in tn if n not in groups["lists_top_12"]]
        greedy = json.loads(greedy_file.read_text(encoding="utf-8"))["results"]
        v = B.arm_read(ds, tn, target, groups, res, greedy, name)
        t = v["table"]
        pods = set(v["pods"])
        g_end = collections.Counter(x.get("ending") for x in greedy if x["i"] // R.POD in pods)
        n_cap, t_cap = caps(pattern)
        a = v["groups"]["all_42"]
        m[name] = (a["search_minus_greedy"], a["se_paired"])
        out["cells"][name] = {"pods": v["pods"], "df": v["df"], "games": v["games"], "errors": v["errors"], "same_deals": v["same_deals"], "lambda": v["lambda"], "residual_sd": v["residual_sd"], "mean_points": v["mean_points"], "rho_L": v["rho_L"],
                              "groups": {g: {"greedy": x["greedy"], "sampled": x["search"], "change": x["search_minus_greedy"], "se": x["se_paired"]} for g, x in v["groups"].items()},
                              "spearman_across_regimes": r3(R.spearman(np.array([x["greedy"] for x in t]), np.array([x["search"] for x in t]))), "shape": {k: v["beside"][k]["shape_optimum"] for k in ("greedy", "search")},
                              "endings": {"sampled": endings, "greedy": dict(g_end)}, "capped_sampled": {"games": n_cap, "turns": t_cap, "of": v["games"]["search"]},
                              "table": sorted(({"trainer": x["trainer"], "greedy": x["greedy"], "sampled": x["search"], "change": r3(x["search"] - x["greedy"])} for x in t), key=lambda x: -x["change"])}
    if "s48" in m and "s49" in m:
        vals = [m["s48"], m["s49"]]
        diff = all(abs(d) >= 0.004 and abs(d) >= 2 * s for d, s in vals) and vals[0][0] * vals[1][0] > 0
        same = all(abs(d) < 0.002 and abs(d) + 2 * s < 0.004 for d, s in vals)
        out["band"] = "R-regime-differs" if diff else "R-same" if same else "between"
    (D / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("band", out.get("band"))
    for name, v in out["cells"].items():
        print(name, {k: v[k] for k in ("pods", "games", "errors", "same_deals", "lambda", "residual_sd", "mean_points", "rho_L", "spearman_across_regimes", "endings", "capped_sampled")})
        for g, x in v["groups"].items():
            print("  ", g, x)
        print("   shape", v["shape"])
        print("   rises", [(x["trainer"], x["change"]) for x in v["table"][:6]], "falls", [(x["trainer"], x["change"]) for x in v["table"][-4:]])


if __name__ == "__main__":
    main()
