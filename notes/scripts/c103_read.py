"""C103's readout (runs/probe/C103-energy-curve/record.md): per pilot, the variant's share against its list (1 - the list's
per-pair score) at each Energy shift, pooled over the P lists and 4 replicates and per list, with a binomial SE per pair (64
games), seeds pooled where both ran; the oracle row (arm 0 s1, S against G at +-4); and the record's bands. Evaluation only.

  PYTHONPATH=. .venv/Scripts/python notes/scripts/c103_read.py
"""
import collections
import json
from pathlib import Path

import numpy as np

C = Path(__file__).resolve().parents[2] / "runs" / "probe" / "C103-energy-curve"


def curve(pairs, per_pair, names):
    """{shift: (pooled share, SE, {list: share})} with shift = +K / -K from the group name energy+K#r."""
    by = collections.defaultdict(list)
    for p, s in zip(pairs, per_pair):
        g = p["group"]
        by[int(g[6:].split("#")[0])].append((names[p["base"]], 1 - s))
    out = {}
    for k, xs in sorted(by.items()):
        v = np.array([x for _, x in xs])
        se = float(np.sqrt(sum(max(x * (1 - x), 1e-4) / 64 for x in v)) / len(v))
        per = collections.defaultdict(list)
        for n, x in xs:
            per[n].append(x)
        out[k] = (float(v.mean()), se, {n: round(float(np.mean(x)), 3) for n, x in per.items()})
    return out


def main():
    res = {}
    runs = sorted(C.glob("greedy_s*.json"))
    pooled = collections.defaultdict(lambda: collections.defaultdict(list))
    for f in runs:
        j = json.loads(f.read_text(encoding="utf-8"))
        names = [d["name"][:22] for d in json.loads(Path(j["decks"]).read_text(encoding="utf-8"))]
        for pl, v in j["players"].items():
            for k, x in curve(j["pairs"], v["per_pair"], names).items():
                pooled[pl][k].append(x)
    for pl, ks in pooled.items():
        row = {}
        for k, xs in ks.items():
            m = float(np.mean([x[0] for x in xs]))
            se = float(np.sqrt(sum(x[1] ** 2 for x in xs)) / len(xs))
            row[k] = {"share": round(m, 4), "se": round(se, 4), "ci": [round(m - 1.96 * se, 4), round(m + 1.96 * se, 4)],
                      "per_list": xs[0][2] if len(xs) == 1 else None, "seeds": len(xs)}
        s4, m4 = row.get(4), row.get(-4)
        row["bands"] = {"R-energy-hungry": bool(s4 and s4["share"] >= 0.53 and s4["ci"][0] > 0.5),
                        "R-flat": bool(s4 and m4 and abs(s4["share"] - 0.5) <= 0.03 and abs(m4["share"] - 0.5) <= 0.03),
                        "lists-optimal": bool(s4 and m4 and s4["share"] < 0.47 and m4["share"] < 0.47)}
        res[pl] = row
        print(pl)
        for k in sorted(k for k in row if isinstance(k, int)):
            x = row[k]
            print(f"  Energy {k:+d}: variant {x['share']:.3f} [{x['ci'][0]:.3f}, {x['ci'][1]:.3f}] ({x['seeds']} seed(s))  per list {x['per_list']}")
        print("  bands", row["bands"])
    o = C / "oracle_arm0s1_s91.json"
    j = json.loads(o.read_text(encoding="utf-8")) if o.exists() else {}
    if "S" in j.get("arms", {}):
        names = [d["name"][:22] for d in j["lists"]] if isinstance(j.get("lists"), list) and j["lists"] and isinstance(j["lists"][0], dict) \
            else [str(i) for i in range(64)]
        cg = curve(j["pairs"], j["arms"]["G"]["per_pair"], names)
        cs = curve(j["pairs"], j["arms"]["S"]["per_pair"], names)
        res["oracle_row"] = {k: {"G": round(cg[k][0], 4), "S": round(cs[k][0], 4), "S_minus_G": round(cs[k][0] - cg[k][0], 4),
                                 "se": round(float(np.hypot(cg[k][1], cs[k][1])), 4)} for k in cg}
        print("oracle row (arm 0 s1, s91):", res["oracle_row"])
    (C / "readout.json").write_text(json.dumps({str(k): v for k, v in res.items()}, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
