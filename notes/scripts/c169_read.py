"""C169 (runs/probe/C169-body-split/record.md, with Amendment 1): the body chain A -> E2 -> S -> G -> B, base scores. Special = A - E2, Identity = E2 - S, Structure = S - G, Fit = G - B, summing to A - B. Read at
four pilot-field pairs: C127 s16 and arm 0 s1 on C162's rules-only field (A and B are C167's and C163's games), C127 s16 on its own population at 29 (F), and arm 0 s1 on the 24 lists. SE is the larger of a deal bootstrap
and a bootstrap over source lists. A part carries at +0.07 and 2 SE, doesn't under +0.03; a cell under 0.25 or over 0.75 makes its effects provisional (logit +0.28 and +0.12), under 0.15 or over 0.85 unreadable. On the
list field the read is on logit (+0.28 and 2 SE carries, under +0.12 doesn't). R-<part> and R-mixed also need the part to carry on the list field where readable; R-weak-field is a part carrying on the rules-only field and not on
the lists. Reported beside them: win share in every cell, and each cell's score by opponent on the list field.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c169_read.py [--check FILE --cell E2]
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

import c167_read as C
from c139_read import r3

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C169-body-split"
CELLS = ("A", "E2", "S", "G", "B")
PARTS = {"Special": "AE", "Identity": "ES", "Structure": "SG", "Fit": "GB"}
KEY = {"A": "A", "E": "E2", "S": "S", "G": "G", "B": "B"}
PAIRS = {"s16_rules": ("s16", "rules"), "arm0_rules": ("arm0", "rules"), "s16_drafted": ("s16", "drafted"), "arm0_lists": ("arm0", "lists")}
REP_PAIRS = {"s17_rules": ("s17", "rules"), "s2_rules": ("s2", "rules"), "s17_drafted": ("s17", "drafted"), "s2_lists": ("s2", "lists")}
C.DECKS.update({"E2": OUT / "E2.json", "S": OUT / "S.json", "G": OUT / "G.json"})


def path_of(pilot, field, cell):
    if field == "drafted":
        return OUT / f"{cell}_F_{pilot}.json"
    if field == "lists":
        return OUT / f"{cell}_L_{pilot}.json"
    if cell in ("A", "B"):
        return C.path_of(pilot, cell)
    return OUT / f"{cell}_{pilot}.json"


def parts(m):
    return {"Special": m["A"] - m["E2"], "Identity": m["E2"] - m["S"], "Structure": m["S"] - m["G"], "Fit": m["G"] - m["B"]}


def analyse(cells, reps=2000):
    rng = np.random.default_rng(169)
    means = {k: float(c["score"].mean()) for k, c in cells.items()}
    pl = C.per_list(cells)
    lists = sorted(pl["A"])
    point, point_l = parts(means), parts({k: C.logit(v) for k, v in means.items()})
    runs = {s: defaultdict(list) for s in ("deal", "clus", "deal_l", "clus_l")}
    for _ in range(reps):
        d = {k: float(c["score"][rng.integers(len(c["score"]), size=len(c["score"]))].mean()) for k, c in cells.items()}
        draw = [lists[int(i)] for i in rng.integers(len(lists), size=len(lists))]
        cl = {k: float(np.mean([pl[k][s] for s in draw])) for k in CELLS}
        for k, v in parts(d).items():
            runs["deal"][k].append(v)
        for k, v in parts({x: C.logit(y) for x, y in d.items()}).items():
            runs["deal_l"][k].append(v)
        for k, v in parts(cl).items():
            runs["clus"][k].append(v)
        for k, v in parts({x: C.logit(y) for x, y in cl.items()}).items():
            runs["clus_l"][k].append(v)
    se = lambda a, b, k: max(float(np.std(runs[a][k], ddof=1)), float(np.std(runs[b][k], ddof=1)))
    return means, {k: {"est": point[k], "se": se("deal", "clus", k), "logit": float(point_l[k]), "logit_se": se("deal_l", "clus_l", k)} for k in point}


def statuses(means, eff, on_logit=False):
    soft = {k: not 0.25 <= v <= 0.75 for k, v in means.items()}
    hard = {k: not 0.15 <= v <= 0.85 for k, v in means.items()}
    out = {}
    for name, e in eff.items():
        used = [KEY[c] for c in PARTS[name]]
        if any(hard[c] for c in used):
            out[name] = {"unreadable": True, "provisional": True, "carries": False, "doesnt": False}
            continue
        prov = any(soft[c] for c in used)
        logit_carries = e["logit"] >= 0.28 and e["logit"] >= 2 * e["logit_se"]
        if on_logit:
            out[name] = {"unreadable": False, "provisional": prov, "carries": logit_carries, "doesnt": e["logit"] < 0.12}
            continue
        carries = e["est"] >= 0.07 and e["est"] >= 2 * e["se"] and (not prov or logit_carries)
        doesnt = e["est"] < 0.03 and (not prov or e["logit"] < 0.12)
        out[name] = {"unreadable": False, "provisional": prov, "carries": carries, "doesnt": doesnt}
    return out


def band(res):
    """res holds, in order, two rules-only pairs, a drafted pair and a list pair."""
    names = list(PARTS)
    rules, drafted, lists_key = list(res)[:2], list(res)[2], list(res)[3]
    base = rules + [drafted]
    lists = res[lists_key]["status"]
    list_ok = lambda n: lists[n]["unreadable"] or lists[n]["carries"]
    all3 = [n for n in names if all(res[p]["status"][n]["carries"] for p in base) and list_ok(n)]
    anyp = [n for n in names if any(res[p]["status"][n]["carries"] for p in base)]
    weak = [n for n in names if all(res[p]["status"][n]["carries"] for p in rules) and lists[n]["doesnt"]]
    unread = [n for n in names if lists[n]["unreadable"]]
    if len(all3) >= 2:
        b = "R-mixed"
    elif len(all3) == 1 and anyp == all3:
        b = f"R-{all3[0].lower()}"
    elif weak:
        b = "R-weak-field"
    elif any((all(res[p]["status"][n]["carries"] for p in rules) and res[drafted]["status"][n]["doesnt"])
             or (res[drafted]["status"][n]["carries"] and all(res[p]["status"][n]["doesnt"] for p in rules)) for n in names):
        b = "R-field-dependent"
    else:
        b = "between"
    return b, {"weak_field_parts": weak, "unreadable_on_lists": unread}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", default="")
    ap.add_argument("--cell", default="")
    ap.add_argument("--rep", action="store_true", help="the replication's pilots")
    a = ap.parse_args()
    if a.check:
        c = C.read_cell(a.check, a.cell)
        print(json.dumps({"cell": a.cell, "games": c["n"], "errors": c["errors"], "score": r3(float(c["score"].mean())), "win": r3(float(c["win"].mean())), "never_source": c["never_source"],
                          "last": {k: c["last"].get(k) for k in ("games", "seconds", "games_per_s")}}))
        sys.exit(0 if c["never_source"] and c["errors"] <= 0.02 * c["n"] else 3)
    res = {}
    for pair, (pilot, field) in (REP_PAIRS if a.rep else PAIRS).items():
        cells = {k: C.read_cell(path_of(pilot, field, k), k) for k in CELLS}
        means, eff = analyse(cells)
        pl = C.per_list(cells)
        res[pair] = {"means": {k: r3(v) for k, v in means.items()}, "win_share": {k: r3(float(c["win"].mean())) for k, c in cells.items()},
                     "effects": {k: {x: r3(y) for x, y in v.items()} for k, v in eff.items()}, "status": statuses(means, eff, on_logit=field == "lists"),
                     "A_minus_B": r3(means["A"] - means["B"]), "endings": {k: c["endings"] for k, c in cells.items()}, "errors": {k: c["errors"] for k, c in cells.items()},
                     "never_source": all(c["never_source"] for c in cells.values()), "per_list": {n: {k: r3(pl[k][n]) for k in CELLS} for n in pl["A"]}}
        if field == "lists":
            res[pair]["by_opponent"] = {k: {o: r3(float(c["score"][c["opp"] == o].mean())) for o in sorted(set(c["opp"].tolist()))} for k, c in cells.items()}
    b, notes = band(res)
    out = {"band": b, **notes, "pairs": res}
    (OUT / ("summary_rep.json" if a.rep else "summary.json")).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("band", b, notes)
    for p, v in res.items():
        print(p, "means", v["means"], "win", v["win_share"], "A-B", v["A_minus_B"], "errors", v["errors"], "never_source", v["never_source"])
        for k, e in v["effects"].items():
            print("  ", k, e, {x: y for x, y in v["status"][k].items() if y})
        print("   endings", v["endings"])


if __name__ == "__main__":
    main()
