"""C183 (runs/probe/C183-draw-interaction/record.md), CPU, existing games: do draw cards make the other Trainers worth holding? C165's fit with one more free term, (draw copies) x (other Trainers' copies), centred over the design's decks, the coefficient being the value per extra other-Trainer copy per extra draw copy; jackknife over pods. The draw copies are the three named draw cards, for evaluation only, and, name-free, the plain mean table's top 3. On C165's four pilots, C171's concentrated and plain tables and C175's E2 under C49-sd and arm 0. R-draw-carries: positive and 2 SE on at least two independent tables (different decks), and at least +0.0009, the size that lifts the others by half of the -0.0075 gap at +4 draw copies. R-not: under half that, or negative, on all. Between otherwise. Post hoc in origin.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c183_read.py
"""
import json
from pathlib import Path

import numpy as np

import c165_read as R
from c139_read import pts, r3

ROOT = R.ROOT
D = ROOT / "runs/probe/C183-draw-interaction"
TAB = ROOT / "runs/probe/C171-table-drafting"
C165 = ROOT / "runs/probe/C165-trainer-factorial"
C175 = ROOT / "runs/probe/C175-trainers-strong-bodies/E2"
NAMED = ("Professor Oak", "Bill", "Gambler")
LINE = 0.0009
# name, deck folder, games file, deck set (independent when different), a band table
CELLS = [("C165 s16", C165, C165 / "games_s16.json", "C165", True), ("C165 s17", C165, C165 / "games_s17.json", "C165", True), ("C165 K1m", C165, C165 / "games_K1m.json", "C165", False), ("C165 arm 0", C165, C165 / "games_arm0.json", "C165", False),
         ("table-s48 C49", TAB / "table-s48", TAB / "table-s48/games.json", "s48", True), ("table-s49 C49", TAB / "table-s49", TAB / "table-s49/games.json", "s49", True), ("plain-s48 C49", TAB / "table-plain-s48", TAB / "table-plain-s48/games.json", "p48", True), ("plain-s49 C49", TAB / "table-plain-s49", TAB / "table-plain-s49/games.json", "p49", True),
         ("E2 C49", C175, C175 / "games.json", "E2", True), ("E2 arm 0", C175, ROOT / "runs/probe/C180-dose-by-practice/E2_arm0.json", "E2", True)]


class FitI(R.Fit):
    """R.Fit with one more free column after the shape terms: the interaction's difference."""

    def __init__(self, ds, a, b, y, inter):
        self.ds = ds
        self.p0, self.t0 = float(ds["P"].mean()), float(ds["Tn"].mean())
        pod = a // R.POD
        self.pods = sorted(set(pod.tolist()))
        k = len(ds["tn"])
        self.ix = 1 + k + 4
        self.n_free = self.ix + 1
        self.A, self.b, self.yy, self.n = {}, {}, {}, {}
        for p in self.pods:
            m = pod == p
            X0 = R.features(ds, a[m], b[m], self.p0, self.t0)
            X = np.hstack([X0[:, :self.ix], (inter[a[m]] - inter[b[m]])[:, None], X0[:, self.ix:]])
            self.A[p], self.b[p] = X.T @ X, X.T @ y[m]
            self.yy[p], self.n[p] = float(y[m] @ y[m]), int(m.sum())
        self.dim = X.shape[1]


def term(ds, names):
    idx = [ds["tn"].index(n) for n in names if n in ds["tn"]]
    d = ds["T"][:, idx].sum(1)
    o = ds["Tn"] - d
    return (d - d.mean()) * (o - o.mean()), d, o


def read(folder, games, top3):
    R.OUT = folder
    ds = R.load_design()
    res = [x for x in json.loads(Path(games).read_text(encoding="utf-8"))["results"] if not x.get("error")]
    a, b = np.array([x["i"] for x in res]), np.array([x["j"] for x in res])
    y = np.array([pts(x)[0] - 0.5 for x in res])
    out = {"games": len(y)}
    lam = None
    for tag, names in (("named", NAMED), ("table_top_3", top3)):
        inter, d, o = term(ds, names)
        f = FitI(ds, a, b, y, inter)
        if lam is None:
            lam, _ = f.choose_lambda()
        w = f.solve(f.pods, lam)
        fn = lambda v, ix=f.ix: float(v[ix])
        out[tag] = {"coef": r3(fn(w)), "se": r3(float(f.jackknife(lam, fn))), "draw_mean": r3(float(d.mean())), "draw_sd": r3(float(d.std())), "others_mean": r3(float(o.mean())), "corr_draw_others": r3(float(np.corrcoef(d, o)[0, 1])), "mean_beta": r3(float(f.beta(w).mean()))}
    out["lambda"] = lam
    out["pods"] = len(f.pods)
    return out


def main():
    table = json.loads((ROOT / "runs/probe/C182-trainer-table-drafting/table.json").read_text(encoding="utf-8"))
    top3 = sorted(table, key=lambda n: -table[n])[:3]
    out = {"table_top_3": top3, "line": LINE, "cells": {}}
    for name, folder, games, _, _ in CELLS:
        if Path(games).exists():
            out["cells"][name] = read(folder, games, top3)
    for tag in ("named", "table_top_3"):
        ok = {s for n, _, _, s, band in CELLS if band and n in out["cells"] and out["cells"][n][tag]["coef"] >= LINE and out["cells"][n][tag]["coef"] >= 2 * out["cells"][n][tag]["se"]}
        low = all(out["cells"][n][tag]["coef"] < LINE / 2 for n, _, _, _, band in CELLS if band and n in out["cells"])
        out[f"band_{tag}"] = "R-draw-carries" if len(ok) >= 2 else "R-not" if low else "between"
        out[f"tables_passing_{tag}"] = sorted(ok)
    D.mkdir(exist_ok=True)
    (D / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(top3, {k: out[k] for k in out if k.startswith("band") or k.startswith("tables")})
    for k, v in out["cells"].items():
        print(k, "games", v["games"], "pods", v["pods"], "lam", v["lambda"], "| named", {q: v["named"][q] for q in ("coef", "se", "draw_mean", "draw_sd", "corr_draw_others", "mean_beta")}, "| top3", {q: v["table_top_3"][q] for q in ("coef", "se", "draw_mean", "draw_sd")})


if __name__ == "__main__":
    main()
