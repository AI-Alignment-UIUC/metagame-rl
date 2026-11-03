"""C145 (runs/probe/C145-draw-context/record.md): the draw cards' price in four cells, signed so positive means the draw cards beat the
Energy. A (C144's G: arm 0, California, list - its draw -> Energy copy) and B (the loop's pilot on A's pairs and deals) are c142_run.py
files; C (arm 0) and D (the loop's pilot) are c145_run.py files on the loop's population (copy with 2 Oak + 2 Bill - deck). Prices and
bootstrap SEs come from c142_read.read; B - A and D - C are paired on the same deals. Checks: c142_read's, plus every C/D copy keeping
the copy limit (4 a name, basic Energy aside) and differing from its deck in exactly the recorded cards. Writes summary.json.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c145_read.py
"""
import json
from collections import Counter
from pathlib import Path

import c142_read as C142
from c139_read import boot, pts, r3

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C145-draw-context"
CELLS = {"A": (ROOT / "runs/probe/C144-trainer-groups/G_draw_s91.json", "draw", 1), "B": (OUT / "B_s91.json", "draw", 1),
         "C": (OUT / "C_s91.json", "oakbill", -1), "D": (OUT / "D_s91.json", "oakbill", -1)}


def per_deal(path, g, sign):
    r = json.loads(path.read_text(encoding="utf-8"))
    by = {(x["i"], x["j"], x["seed"]): x for x in r["results"] if not x.get("error")}
    out = {}
    for m in r["meta"]:
        c = m["copies"][g]
        for s in {s for (i, j, s) in by if i == m["list"] and j == m["opp"]}:
            if (c, m["opp"], s) in by:
                out[(m["key"], s)] = sign * (pts(by[(m["list"], m["opp"], s)])[0] - pts(by[(c, m["opp"], s)])[0])
    return r, out


def copy_checks(r):
    from rl.decks import Pool
    card = {c["fullName"]: c for c in Pool().cards}
    basic = lambda x: card[x]["superType"] == 3 and card[x]["energyType"] == 0
    cards = r["deck_cards"]
    lim = all(n <= 4 for v in r["variants"] for x, n in Counter(card[y]["name"] for y in cards[v["variant"]] if not basic(y)).items())
    diff = all(sum(a != b for a, b in zip(cards[v["base"]], cards[v["variant"]])) == v["replaced"] for v in r["variants"])
    return {"copy_limit": lim, "diff_equals_recorded": diff}


def main():
    out, d = {"cells": {}}, {}
    for k, (p, g, sign) in CELLS.items():
        if not p.exists():
            continue
        s = C142.read([p])
        r, d[k] = per_deal(p, g, sign)
        xs = list(d[k].values())
        out["cells"][k] = {"pilot": r["pilot"], "deals": len(xs), "errors": s["errors"], "price": r3(sum(xs) / len(xs)), "se": r3(boot(xs)),
                           "copies_mean": s["singles"][g]["copies_mean"], "checks": {**s["checks"], **(copy_checks(r) if g == "oakbill" else {})}}
        if g == "oakbill":
            out["cells"][k]["added"] = dict(Counter(f"{n} {c}" for v in r["variants"] for c, n in v["added"].items()))
            out["cells"][k]["decks"] = len(r["variants"])
    for a, b in (("A", "B"), ("C", "D")):
        if a in d and b in d:
            keys = sorted(set(d[a]) & set(d[b]))
            xs = [d[b][x] - d[a][x] for x in keys]
            out[f"{b}-{a}"] = {"deals": len(keys), "mean": r3(sum(xs) / len(xs)), "se": r3(boot(xs))}
    c = out["cells"]
    if all(k in c for k in "ABCD"):
        ba = out["B-A"]
        flags = {"loop_wants_draw": c["D"]["price"] >= 0.04 and c["D"]["price"] >= 2 * c["D"]["se"],
                 "pilot": -ba["mean"] >= 0.04 and -ba["mean"] >= 2 * ba["se"] and c["D"]["price"] < 0.04,
                 "context": c["C"]["price"] < 0.04 and c["A"]["price"] >= 0.06}
        out["flags"] = flags
        out["band"] = ("R-loop-wants-draw" if flags["loop_wants_draw"] else "R-both" if flags["pilot"] and flags["context"] else
                       "R-pilot" if flags["pilot"] else "R-context" if flags["context"] else "between")
    (OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
