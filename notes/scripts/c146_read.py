"""C146 (runs/probe/C146-draw-provenance/record.md): the draw group's price (list - its draw -> Energy copy, c145_read.per_deal) on C144's
California pairs, greedy, under the start pilot (S0, seed 91), arm 0 (A: C144's G) and the loop's pilot (B: C145's B), with S0 - B and
S0 - A paired on the seed-91 deals, and C145's B - A replicated at seed 92 (A92, B92). The record's bands and replication rule; checks
from c142_read. Writes summary.json.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c146_read.py
"""
import json
from pathlib import Path

import c142_read as C142
from c139_read import boot, r3
from c145_read import per_deal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C146-draw-provenance"
CELLS = {"S0": OUT / "S0_s91.json", "A": ROOT / "runs/probe/C144-trainer-groups/G_draw_s91.json",
         "B": ROOT / "runs/probe/C145-draw-context/B_s91.json", "A92": OUT / "A92_s92.json", "B92": OUT / "B92_s92.json"}


def main():
    d, out = {}, {"cells": {}}
    for k, p in CELLS.items():
        r, d[k] = per_deal(p, "draw", 1)
        xs, s = list(d[k].values()), C142.read([p])
        out["cells"][k] = {"pilot": r["pilot"], "seed": r["seed"], "deals": len(xs), "errors": s["errors"], "price": r3(sum(xs) / len(xs)),
                           "se": r3(boot(xs)), "checks": s["checks"]}
    for a, b in (("B", "S0"), ("A", "S0"), ("A92", "B92")):
        keys = sorted(set(d[a]) & set(d[b]))
        xs = [d[b][x] - d[a][x] for x in keys]
        out[f"{b}-{a}"] = {"deals": len(keys), "mean": r3(sum(xs) / len(xs)), "se": r3(boot(xs))}
    sb, sa, rep = out["S0-B"], out["S0-A"], out["B92-A92"]
    out["band"] = ("R-co-adapt" if sb["mean"] >= 0.04 and sb["mean"] >= 2 * sb["se"] and abs(sa["mean"]) < 0.04 else
                   "R-provenance" if abs(sb["mean"]) < 0.04 and -sa["mean"] >= 0.04 and -sa["mean"] >= 2 * sa["se"] else "between")
    out["replicated"] = rep["mean"] <= -0.03 and rep["mean"] <= -2 * rep["se"]
    (OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
