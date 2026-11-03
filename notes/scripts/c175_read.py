"""C175 (runs/probe/C175-trainers-strong-bodies/record.md): is the Trainers' low price a property of weak games? C165's fit in each class (Y, G, E2 bodies, each against itself; C49-sd, greedy), one lambda a class by leave-one-pod-out. Mean beta over the 42 Trainers, Y - G and E2 - G, with jackknife SEs over pods, added in quadrature since the classes' decks are independent. R-context: Y - G or E2 - G at +0.004 and 2 SE. R-not-context: both under +0.0015, each with an SE that excludes +0.004. Between otherwise. A claim needs a second seed.
Beside it, no band: the same contrasts for the lists' top 12 Trainers, T4 and draw; rho_L; endings; the shape optimum; Y by its bodies' top name. Amendment 1: the three classes against a common field, C162's decks, the same contrasts with no band.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c175_read.py [--synth] [--cell Y]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np

import c165_read as R
import c165_run as F
from c139_read import pts, r3

ROOT = R.ROOT
D = ROOT / "runs/probe/C175-trainers-strong-bodies"
CELLS = ("Y", "G", "E2")
F.SEED = 175
R.schedule = F.schedule


def design(cls):
    R.OUT = D / cls
    return R.load_design()


def arrays(res):
    ok = [x for x in res if not x.get("error")]
    a = np.array([x["i"] for x in ok])
    b = np.array([x["j"] for x in ok])
    assert (a // R.POD == b // R.POD).all(), "a game across pods"
    return a, b, np.array([pts(x)[0] - 0.5 for x in ok]), len(res) - len(ok)


def read_cell(cls, target_all):
    from rl.decks import Pool
    ds = design(cls)
    r = json.loads((D / cls / "games.json").read_text(encoding="utf-8"))
    a, b, y, err = arrays(r["results"])
    f = R.Fit(ds, a, b, y)
    lam, _ = f.choose_lambda()
    w = f.solve(f.pods, lam)
    tn = ds["tn"]
    if tuple(tn) != tuple(target_all["names"]):
        target = np.array([target_all["copies"][target_all["names"].index(n)] for n in tn])
    else:
        target = np.array(target_all["copies"])
    groups = {"all_42": list(tn), "lists_top_12": [tn[i] for i in np.argsort(-target)[:12]], "T4": [n for n in R.T4 if n in tn], "draw": [n for n in R.DRAW if n in tn]}
    out = {"games": len(y), "errors": err, "lambda": lam, "residual_sd": r3(f.residual_sd(w)), "mean_points": r3(float(y.mean() + 0.5)), "endings": r["last"]["endings"], "games_per_s": r["last"]["games_per_s"], "pods": len(f.pods), "rho_L": r3(R.spearman(f.beta(w), target)), "groups": {}}
    raw = {}
    for g, names in groups.items():
        ix = [tn.index(n) for n in names]
        fn = lambda v, ix=ix: float(np.mean(f.beta(v)[ix]))
        raw[g] = (fn(w), float(f.jackknife(lam, fn)))
        out["groups"][g] = {"mean": r3(raw[g][0]), "se": r3(raw[g][1])}
    keep = (ds["P"][a] >= 8) & (ds["P"][a] <= 24) & (ds["P"][b] >= 8) & (ds["P"][b] <= 24)
    if keep.sum() > 1000:
        fp = R.Fit(ds, a, b, y, keep)
        opt = R.optimum(fp.solve(fp.pods, lam), ds, fp.p0, fp.t0, len(tn))
        tlo, thi = np.percentile(ds["Tn"], [1, 99])
        plo, phi = np.percentile(ds["P"], [1, 99])
        out["shape_optimum"] = {"P": r3(float(opt[0])), "T": r3(float(opt[1])), "E": r3(float(opt[2])), "T_range": [r3(float(tlo)), r3(float(thi))], "P_range": [r3(float(plo)), r3(float(phi))]}
    out["table"] = sorted(({"trainer": tn[i], "beta": r3(float(f.beta(w)[i])), "lists_copies": r3(float(target[i]))} for i in range(len(tn))), key=lambda t: -t["beta"])
    if cls == "Y":
        card = {c["fullName"]: c for c in Pool().cards}
        decks = json.loads((D / cls / "decks.json").read_text(encoding="utf-8"))
        top = collections.Counter(n for d in decks for n in {card[x]["name"] for x in d["cards"] if card[x]["superType"] == 1})
        name = top.most_common(1)[0][0]
        holds = np.array([any(card[x]["name"] == name for x in d["cards"]) for d in decks])
        out["by_top_name"] = {"name": name, "decks_holding": int(holds.sum()), "of": len(decks)}
        keep_h = holds[a] & holds[b]
        if keep_h.sum() > 1000:
            fh = R.Fit(ds, a, b, y, keep_h)
            vh = fh.solve(fh.pods, lam)
            out["by_top_name"]["mean_beta_both_hold_it"] = r3(float(fh.beta(vh).mean()))
            out["by_top_name"]["games"] = int(keep_h.sum())
    return out, raw


def read_field(cls, target_all):
    """Amendment 1: the class's decks against C162's field. The design holds the class decks then the field, y is the class deck's points, the features are its values minus the field deck's. A row is always class deck minus field deck, whichever seat it took."""
    R.OUT = D / cls
    decks = json.loads((D / cls / "decks.json").read_text(encoding="utf-8"))
    field = json.loads((ROOT / "runs/probe/C163-draw-deck-field/R.json").read_text(encoding="utf-8"))
    R.OUT = D / cls / "with_field"
    R.OUT.mkdir(exist_ok=True)
    (R.OUT / "decks.json").write_text(json.dumps(decks + field), encoding="utf-8")
    ds = R.load_design()
    n = len(decks)
    r = json.loads((D / cls / "field_games.json").read_text(encoding="utf-8"))
    ok = [x for x in r["results"] if not x.get("error")]
    a, b, y = [], [], []
    for x in ok:
        if x["i"] < n:
            a.append(x["i"]), b.append(x["j"]), y.append(pts(x)[0] - 0.5)
        else:
            a.append(x["j"]), b.append(x["i"]), y.append(pts({**x, "iSeat": 3 - x["iSeat"]})[0] - 0.5)
    a, b, y = np.array(a), np.array(b), np.array(y)
    f = R.Fit(ds, a, b, y)
    lam, _ = f.choose_lambda()
    w = f.solve(f.pods, lam)
    tn = ds["tn"]
    target = np.array([target_all["copies"][target_all["names"].index(n_)] for n_ in tn])
    groups = {"all_42": list(tn), "lists_top_12": [tn[i] for i in np.argsort(-target)[:12]], "T4": [n_ for n_ in R.T4 if n_ in tn], "draw": [n_ for n_ in R.DRAW if n_ in tn]}
    raw, out = {}, {"games": len(y), "errors": len(r["results"]) - len(ok), "lambda": lam, "pods": len(f.pods), "mean_points": r3(float(y.mean() + 0.5)), "endings": r["last"]["endings"], "games_per_s": r["last"]["games_per_s"], "rho_L": r3(R.spearman(f.beta(w), target)), "groups": {}}
    for g, names in groups.items():
        ix = [tn.index(n_) for n_ in names]
        fn = lambda v, ix=ix: float(np.mean(f.beta(v)[ix]))
        raw[g] = (fn(w), float(f.jackknife(lam, fn)))
        out["groups"][g] = {"mean": r3(raw[g][0]), "se": r3(raw[g][1])}
    return out, raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth", action="store_true")
    ap.add_argument("--cell", default="Y")
    a = ap.parse_args()
    if a.synth:
        ds = design(a.cell)
        res = R.synth(ds, 0.32, 0.15, pods=12)
        print(json.dumps({"cell": a.cell, "reps": res}))
        ok = all(x["within_2se"] >= 37 for x in res)
        print("planted-value acceptance (at least 37 of 42 within 2 SE, each draw):", "PASS" if ok else "FAIL")
        sys.exit(0 if ok else 3)
    ds = design("G")
    target = {"names": list(ds["tn"]), "copies": R.lists_mean_copies(ds["tn"]).tolist()}
    cells, raw = {}, {}
    for c in CELLS:
        if (D / c / "games.json").exists():
            cells[c], raw[c] = read_cell(c, target)
    out = {"cells": cells, "contrasts": {}}
    for x in ("Y", "E2"):
        if x in raw and "G" in raw:
            out["contrasts"][f"{x}-G"] = {g: {"diff": r3(raw[x][g][0] - raw["G"][g][0]), "se": r3((raw[x][g][1] ** 2 + raw["G"][g][1] ** 2) ** 0.5)} for g in raw["G"]}
    fr = {}
    for c in CELLS:
        if (D / c / "field_games.json").exists():
            out.setdefault("common_field", {})[c], fr[c] = read_field(c, target)
    for x in ("Y", "E2"):
        if x in fr and "G" in fr:
            out.setdefault("common_field_contrasts", {})[f"{x}-G"] = {g: {"diff": r3(fr[x][g][0] - fr["G"][g][0]), "se": r3((fr[x][g][1] ** 2 + fr["G"][g][1] ** 2) ** 0.5)} for g in fr["G"]}
    con = out["contrasts"]
    if len(con) == 2:
        m = [con[k]["all_42"] for k in con]
        out["band"] = ("R-context" if any(x["diff"] >= 0.004 and x["diff"] >= 2 * x["se"] for x in m) else "R-not-context" if all(x["diff"] < 0.0015 and x["diff"] + 2 * x["se"] < 0.004 for x in m) else "between")
    (D / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("band", out.get("band"))
    print("contrasts", json.dumps(con))
    print("common field contrasts", json.dumps(out.get("common_field_contrasts")))
    for c, v in out.get("common_field", {}).items():
        print("field", c, {k: v[k] for k in v if k != "groups"}, v["groups"])
    for c, v in cells.items():
        print(c, {k: v[k] for k in v if k not in ("table", "groups")})
        print("   groups", v["groups"], "| top", [(t["trainer"], t["beta"]) for t in v["table"][:8]])


if __name__ == "__main__":
    main()
