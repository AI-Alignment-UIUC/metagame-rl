"""C173's stage A (runs/probe/C173-search-table/record.md, with Amendment 1): Y against the lists' own Pokemon under search. Cells G, Y plain s48, Y plain s49 and E2 on the lists, C139's search on both seats, 6 opponents at 2 deals, on C171's gate decks, under C49-sd, then E2 and both Y under arm 0, each with a greedy cell of the same design under arm 0 (C49-sd's greedy cells are the gate's,
12 opponents at 2 deals). The gate (#794): pooled over about 400 games each, search reaches 0.57 win share head to head under C49-sd and the mirror is within 2 SE of 0.5, or that pilot's read is void. Bands on decided-win logit, bootstrap over lists, at both Y seeds. R-converges: E2 - Y at +0.20 and 2 SE under both pilots; under arm 0 alone it reads familiarity, since arm 0 trained only on lists. R-holds: Y - E2 estimate - 2 SE at -0.20 or better; otherwise unresolved, with B held. Beside it: points, Y - G and E2 - G,
(Y - E2 under search) - (Y - E2 under greedy), paired by list, Switch under Paralysis, Rampage and Supersonic. Report only.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c173_read.py [--check FILE --cell KEY]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np

import c167_read as C
import c170_read as V
from c139_read import r3

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C173-search-table"
GATE = ROOT / "runs/probe/C171-table-drafting/gate"
C.DECKS.update({"G": V.C169 / "G.json", "E2": V.C169 / "E2.json", "Y_s48": GATE / "Y_s48.json", "Y_s49": GATE / "Y_s49.json"})
YS = ("Y_s48", "Y_s49")


def trace(path):
    f = Path(str(path) + ".trace.jsonl")
    if not f.exists():
        return {}
    rows = [json.loads(x) for x in open(f, encoding="utf-8")]
    turns = collections.defaultdict(list)
    for r in rows:
        if r["kind"] == "paralyzed":
            turns[(r["seed"], r["turn"])].append(r)
    held = [v for v in turns.values() if any(r["sw"] for r in v)]
    played = [v for v in held if any(r["card"] == "Switch" for r in v)]
    return {"turns_paralyzed": len(turns), "switch_held": len(held), "switch_played": len(played), "switch_rate": r3(len(played) / len(held)) if held else None,
            "attacks": dict(collections.Counter(f"{r['ac']}: {r['an']}" for r in rows if r["kind"] == "attack").most_common())}


def change(sy, se, gy, ge, key, rng, reps=2000):
    """(Y - E2 under search) - (Y - E2 under greedy) in logit, paired by list, a bootstrap over lists."""
    lists = sorted(set(sy[key]) & set(se[key]) & set(gy[key]) & set(ge[key]))
    arr = [np.array([d[key][x] for x in lists]) for d in (sy, se, gy, ge)]
    point = float(C.logit(sy[f"{key}_mean"]) - C.logit(se[f"{key}_mean"]) - C.logit(gy[f"{key}_mean"]) + C.logit(ge[f"{key}_mean"]))
    draws = rng.integers(len(lists), size=(reps, len(lists)))
    m = [C.logit(a[draws].mean(1)) for a in arr]
    return {"est": r3(point), "se": r3(float((m[0] - m[1] - m[2] + m[3]).std(ddof=1))), "lists": len(lists)}


def read_pair(search, greedy, rng):
    """One pilot's read: E2 - Y on decided-win logit at each Y seed, and the band."""
    s = {k: V.scales(c) for k, c in search.items()}
    g = {k: V.scales(c) for k, c in greedy.items()}
    eff = {}
    for y in YS:
        if y in s and "E2" in s:
            eff[f"E2-{y}"] = {"won_logit": V.effect(s["E2"], s[y], "won", rng), "points_logit": V.effect(s["E2"], s[y], "score", rng)}
            if y in g and "E2" in g:
                eff[f"E2-{y}"]["greedy_won_logit"] = V.effect(g["E2"], g[y], "won", rng)
                eff[f"E2-{y}"]["greedy_points_logit"] = V.effect(g["E2"], g[y], "score", rng)
                eff[f"E2-{y}"]["change_in_Y_minus_E2_won"] = change(s[y], s["E2"], g[y], g["E2"], "won", rng)
                eff[f"E2-{y}"]["change_in_Y_minus_E2_points"] = change(s[y], s["E2"], g[y], g["E2"], "score", rng)
    for k in YS + ("E2",):
        if k in s and "G" in s:
            eff[f"{k}-G"] = {"won_logit": V.effect(s[k], s["G"], "won", rng), "points_logit": V.effect(s[k], s["G"], "score", rng)}
            if k in g and "G" in g:
                eff[f"{k}-G"]["greedy_won_logit"] = V.effect(g[k], g["G"], "won", rng)
    keys = [f"E2-{y}" for y in YS]
    verdict = "not read yet"
    if all(k in eff for k in keys):
        d = [eff[k]["won_logit"] for k in keys]
        if all(x["est"] >= 0.20 and x["est"] >= 2 * x["se"] for x in d):
            verdict = "falls"
        elif all(-x["est"] - 2 * x["se"] >= -0.20 for x in d):
            verdict = "holds"
        else:
            verdict = "unresolved"
    return s, g, eff, verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", default="")
    ap.add_argument("--cell", default="")
    a = ap.parse_args()
    if a.check:
        c = C.read_cell(a.check, a.cell)
        print(json.dumps({"cell": a.cell, "games": c["n"], "errors": c["errors"], "score": r3(float(c["score"].mean())), "won": r3(float((c["win"] == 1.0).mean())), "never_source": c["never_source"], "last": {k: c["last"].get(k) for k in ("games", "seconds", "games_per_s")}}))
        sys.exit(0 if c["never_source"] and c["errors"] <= 0.02 * c["n"] else 3)
    rng = np.random.default_rng(173)
    files = {"C49": ({k: OUT / f"{k}_S.json" for k in ("E2", "Y_s48", "G", "Y_s49")}, {k: GATE / ("G_C49.json" if k == "G" else "E2_C49.json" if k == "E2" else f"{k}_C49.json") for k in ("E2", "Y_s48", "G", "Y_s49")}),
             "arm0": ({k: OUT / f"{k}_Sa.json" for k in ("E2", "Y_s48", "Y_s49")}, {k: OUT / f"{k}_Ga.json" for k in ("E2", "Y_s48", "Y_s49")})}
    out = {"pilots": {}}
    for tag, (fs, fg) in files.items():
        cs = {k: C.read_cell(f, k) for k, f in fs.items() if f.exists()}
        cg = {k: C.read_cell(f, k) for k, f in fg.items() if f.exists()}
        s, g, eff, verdict = read_pair(cs, cg, rng)
        out["pilots"][tag] = {"verdict": verdict, "effects": eff,
                              "cells": {k: {"games": cs[k]["n"], "errors": cs[k]["errors"], "score": r3(s[k]["score_mean"]), "won": r3(s[k]["won_mean"]), "lost": r3(s[k]["lost"]), "endings": cs[k]["endings"], "rate": cs[k]["last"].get("games_per_s"), "never_source": cs[k]["never_source"], "trace": trace(fs[k])} for k in s},
                              "greedy_cells": {k: {"score": r3(v["score_mean"]), "won": r3(v["won_mean"]), "lost": r3(v["lost"]), "trace": trace(fg[k])} for k, v in g.items()}}
    # the strength gate (#794): pooled over the first and enlarged runs, the mirror within 2 SE of 0.5 and search at 0.57 or more; a mirror off 0.5 voids C49-sd's read until explained
    from c139_read import boot, pts

    def pooled(tags):
        res = [r for t in tags if (OUT / f"h2h_{t}.json").exists() for r in json.loads((OUT / f"h2h_{t}.json").read_text(encoding="utf-8"))["results"] if not r.get("error")]
        if not res:
            return None
        ws = [pts({**r, "iSeat": 3 - r["iSeat"]})[1] for r in res]
        by = {sd: [pts({**r, "iSeat": 3 - r["iSeat"]})[1] for r in res if 3 - r["iSeat"] == sd] for sd in (1, 2)}
        return {"games": len(res), "win_share": r3(sum(ws) / len(ws)), "se": r3(boot(ws)), "by_seat": {sd: r3(sum(v) / len(v)) for sd, v in by.items() if v}}
    search_h, mirror_h = pooled(("C49", "C49_b")), pooled(("C49_aa", "C49_aa_b"))
    enlarged = (OUT / "h2h_C49_b.json").exists() and (OUT / "h2h_C49_aa_b.json").exists()
    mirror_ok = bool(mirror_h and abs(mirror_h["win_share"] - 0.5) <= 2 * mirror_h["se"])
    gate_ok = bool(search_h and search_h["win_share"] >= 0.57 and mirror_ok) if enlarged else None
    out["h2h"] = {"search": search_h, "mirror": mirror_h, "enlarged": enlarged, "mirror_within_2_se_of_0.5": mirror_ok, "gate_stands": gate_ok}
    v49, v0 = out["pilots"]["C49"]["verdict"], out["pilots"]["arm0"]["verdict"]
    out["C49_null_void"] = gate_ok is False
    if v0 == "not read yet" or v49 == "not read yet":
        band = f"stage A read only: C49-sd {v49}, arm 0 not read yet" + (" (C49-sd's null is void: its gate failed)" if gate_ok is False else "")
    elif v49 == "falls" and v0 == "falls":
        band = "R-converges"
    elif v0 == "falls" and v49 != "falls":
        band = "familiarity: a fall under arm 0 alone"
    elif v49 == "holds" and v0 == "holds" and gate_ok is not False:
        band = "R-holds"
    elif gate_ok is False and v0 == "holds":
        band = "R-holds rests on arm 0 alone: C49-sd's null is void"
    else:
        band = "unresolved, B held"
    out["band"] = band
    (OUT / "summary_A.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("band", band, "| h2h", out["h2h"])
    for t, p in out["pilots"].items():
        print(t, "verdict", p["verdict"])
        for k, v in p["cells"].items():
            print("  ", k, {x: v[x] for x in ("games", "errors", "score", "won", "lost", "rate", "never_source")}, "greedy", {x: y for x, y in p["greedy_cells"].get(k, {}).items() if x != "trace"}, "trace", v["trace"])
        for k, v in p["effects"].items():
            print("  ", k, v)


if __name__ == "__main__":
    main()
