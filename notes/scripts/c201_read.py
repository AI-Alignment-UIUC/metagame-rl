"""C201's read (runs/probe/C201-dce-density/record.md). CPU, seconds. Per set and judge (greedy; h2 if run): S_e (dce1) and S_f
(dce2), the variant's decisive share against its original, the mean over decks of each deck's share, SE with the decks fixed
(C193 Amendment 3: within-deck variance over variants); sets A and B pooled (mean of the two, SE hypot / 2), each set's side
of 0.50 reported. S_e apart for decks whose 2 basics came from off-type copies and from the commonest basic ("main"). From the
greedy games (--trainer-play): attacks a turn and no-Energy turns, variant seat (3 - iSeat) against the original.
Bands on pooled greedy S_e: R-density >= 0.52; R-C169-stands 0.48-0.52 with SE <= 0.010; R-worse <= 0.48; between otherwise.
    py notes/scripts/c201_read.py
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

D = Path(__file__).resolve().parents[2] / "runs/probe/C201-dce-density"
SETS = ("setA", "setB")


def share(rows, dr, keep=None):
    c = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["dir"] == dr and r["winner"] in (1, 2) and (keep is None or keep(r)):
            a = c[(r["list"], r["v"])]; a[0] += r["winner"] == 3 - r["iSeat"]; a[1] += 1
    by = defaultdict(list)
    for (l, _), (w, n) in c.items():
        by[l].append(w / n)
    if len(by) < 2:
        return None
    m = np.array([np.mean(v) for v in by.values()])
    var_w = sum(np.var(v, ddof=1) / len(v) for v in by.values() if len(v) > 1)
    return {"S": round(float(m.mean()), 4), "se_lists_fixed": round(float(np.sqrt(var_w) / len(m)), 4),
            "se_over_lists": round(float(m.std(ddof=1) / np.sqrt(len(m))), 4), "decks": len(m), "decisive": int(sum(n for _, n in c.values()))}


def counters(rows, dr):
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["dir"] != dr or not r.get("turnSeat"):
            continue
        for lab, s in (("var", str(3 - r["iSeat"])), ("orig", str(r["iSeat"]))):
            t = r["turnSeat"].get(s)
            if t and t["turns"]:
                acc[f"{lab}_attacks_a_turn"][r["list"]].append(t["atk"] / t["turns"])
                acc[f"{lab}_noE_share"][r["list"]].append(t["noE"] / t["turns"])
    out = {k: round(float(np.mean([np.mean(x) for x in v.values()])), 4) for k, v in acc.items()}
    for k in ("attacks_a_turn", "noE_share"):
        if f"var_{k}" in out:
            out[f"diff_{k}"] = round(out[f"var_{k}"] - out[f"orig_{k}"], 4)
    return out


def main():
    out = {}
    for pl, fn in (("greedy", "cells_greedy_s1.json"), ("h2", "cells_search_s1.json")):
        per = {}
        for st in SETS:
            f = D / st / fn
            if not f.exists():
                continue
            d = json.loads(f.read_text(encoding="utf-8"))
            if not d.get("complete"):
                continue
            src = {(x["list"], x["dir"]): x["src"] for x in json.loads((D / st / "variants_s1.json").read_text(encoding="utf-8")) if x["dir"] in ("dce1", "dce2")}
            r = d["results"]
            per[st] = {"games": d["games"], "errors": d["errors"], "S_e": share(r, "dce1"), "S_f": share(r, "dce2"),
                       "S_e_off": share(r, "dce1", lambda x: src.get((x["list"], "dce1")) == "off"),
                       "S_e_main": share(r, "dce1", lambda x: src.get((x["list"], "dce1")) == "main"),
                       **({"counters_e": counters(r, "dce1"), "counters_f": counters(r, "dce2")} if pl == "greedy" else {})}
        if not per:
            continue
        o = {"sets": per}
        if len(per) == 2:
            for k in ("S_e", "S_f"):
                a, b = per["setA"][k], per["setB"][k]
                m, se = (a["S"] + b["S"]) / 2, float(np.hypot(a["se_lists_fixed"], b["se_lists_fixed"]) / 2)
                o[f"pooled_{k}"] = {"S": round(m, 4), "se": round(se, 4), "same_side_of_0.50": (a["S"] - 0.5) * (b["S"] - 0.5) > 0}
            p = o["pooled_S_e"]
            o["band"] = ("R-density" if p["S"] >= 0.52 else "R-worse" if p["S"] <= 0.48 else
                         "R-C169-stands" if p["se"] <= 0.010 else "between")
        out[pl] = o
    (D / "read.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
