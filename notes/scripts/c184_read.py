"""C184 (runs/probe/C184-recovery-arm/record.md, Amendments 1 and 2). DN, the mass-neutral Trainer table from Trainers 13-17, against WR, seeds 50 and 51; ND, the same bonus from the normal start, against W (C171), seeds 48 and 49. Band at 44, on DN - WR's median Trainers, both seeds (taken by default, the record's numbers on the difference, row 115): R-recovers, +5 or more with survivors' high-table copies rising in DN; R-no, under +2; between otherwise. No band for ND: reads. Acceptance (--accept): Trainers proposed a candidate over iterations 0-4, DN against WR, within noise. Beside it: body facts, E, draw, T4, G1, deck-outs, the ledger and the head as C182's reader, by the plain mean table's top 12 against the other 30, and the head's own mass (head_mass in log.jsonl, C187's caps/ for W). Seeds are replicates. A cell says not_ready until it has the iteration.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c184_read.py --it 29
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c184_read.py --accept
"""
import argparse
import json
from pathlib import Path

import numpy as np

import c182_read as C
from c139_read import r3

ROOT = C.ROOT
D = ROOT / "runs/probe/C184-recovery-arm"
CAPS = ROOT / "runs/probe/C187-head-off/caps"


def rows(run):
    out = {}
    if not (run / "log.jsonl").exists():
        return out
    for line in open(run / "log.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if "iter" in d:
            out[d["iter"]] = d
    return out


def start_median(run):
    return rows(run)[4]["shape_quartiles"]["trainer"][1] if 4 in rows(run) else None


def window(run, lo, hi, key="prop"):
    """Mean P/T/E a candidate over these iterations, and the SE of Trainers over iterations."""
    r = rows(run)
    x = [r[i]["select"][key] for i in range(lo, hi + 1) if i in r and (r[i].get("select") or {}).get(key)]
    if not x:
        return None
    a = np.array(x, dtype=float)
    return {"iters": len(a), "pte": np.round(a.mean(0), 3).tolist(), "T_se": r3(float(a[:, 1].std(ddof=1) / len(a) ** 0.5)) if len(a) > 1 else None}


def head_mass(run, lo, hi):
    r = rows(run)
    x = [r[i]["head_mass"] for i in range(lo, hi + 1) if i in r and r[i].get("head_mass")]
    if not x:
        return None
    return {k: np.round(np.mean([v[k] for v in x], 0), 4).tolist() for k in x[0]}


def cell(name, it, hi, lo, top, stages=None):
    run = ROOT / "runs/screens" / name
    st = C.stage(stages or D / "stages.jsonl", name, it) if (stages or D / "stages.jsonl").exists() else None
    if not st:
        return {"not_ready": True}
    s0 = start_median(run)
    out = {"start_median_T": s0, "median": st["median_pte"], "T_over_start": st["median_pte"][1] - s0, "population": st["population"]["pte"], "G1_mean5": st["G1_mean5"], "T4": st["population"]["T4"], "draw": st["population"]["draw"], "E": st["population"]["E"], "A7": st["population"].get("A7"), "rho_L": st["population"].get("rho_L"), "wall": st.get("wall_share"), "survivors": st["survivors"], "errors": st["errors"], "games": st["games"]}
    out["discipline"] = C.discipline(run, it, st)
    out["slope"] = C.slope(run, it, hi, lo)
    out["ledger"] = C.ledger(run, it, top)
    out["cards"] = C.per_card(run, it, top)
    out["proposed_last_10"] = window(run, it - 9, it)
    out["accepted_last_10"] = window(run, it - 9, it, "acc")
    out["head_mass_last_5"] = head_mass(run, it - 4, it)
    if st.get("survivors"):
        out["high_low"] = C.survivors(run, it, hi, lo)
    return out


def accept():
    out = {}
    for s in (50, 51):
        dn, wr = ROOT / f"runs/screens/C184-DN-s{s}", ROOT / f"runs/screens/C184-WR-s{s}"
        if not ((dn / "log.jsonl").exists() and (wr / "log.jsonl").exists()):
            out[s] = {"not_ready": True}
            continue
        a, b = window(dn, 0, 4), window(wr, 0, 4)
        if not a or not b or a["iters"] < 5 or b["iters"] < 5:
            out[s] = {"not_ready": True, "DN": a, "WR": b}
            continue
        d, se = a["pte"][1] - b["pte"][1], (a["T_se"] ** 2 + b["T_se"] ** 2) ** 0.5
        out[s] = {"DN": a, "WR": b, "T_DN_minus_WR": r3(d), "se": r3(se), "within_2se": abs(d) <= 2 * se, "head_mass_DN": head_mass(dn, 0, 4)}
    (D / "accept.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, default=float))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--it", type=int, default=29)
    ap.add_argument("--accept", action="store_true")
    a = ap.parse_args()
    if a.accept:
        return accept()
    hi, lo, top = C.groups()
    out = {"iter": a.it, "cells": {f"{x}-s{s}": cell(f"C184-{x}-s{s}", a.it, hi, lo, top) for x, ss in (("DN", (50, 51)), ("WR", (50, 51)), ("ND", (48, 49))) for s in ss}}
    for s in (48, 49):
        out["cells"][f"W-s{s}"] = cell(f"C171-W-s{s}", a.it, hi, lo, top, C.W_STAGES)
    c = out["cells"]
    pairs = [(c[f"DN-s{s}"], c[f"WR-s{s}"]) for s in (50, 51)]
    ready = [(x, y) for x, y in pairs if "not_ready" not in x and "not_ready" not in y]
    out["DN_minus_WR_median_T"] = [x["median"][1] - y["median"][1] for x, y in ready]
    if a.it == 44 and len(ready) == 2:
        d = out["DN_minus_WR_median_T"]
        rising = all(x.get("high_low", {}).get("high", {}).get("change", -1) > 0 for x, _ in ready)
        out["band"] = "R-recovers" if all(v >= 5 for v in d) and rising else "R-no" if all(v < 2 for v in d) else "between"
    for s in (48, 49):
        x, y = c[f"ND-s{s}"], c[f"W-s{s}"]
        if "not_ready" not in x and "not_ready" not in y:
            out[f"ND_minus_W_s{s}"] = {"median_T": x["median"][1] - y["median"][1], "G1_mean5": r3(x["G1_mean5"] - y["G1_mean5"]), "survivors_T": r3(x["survivors"]["trainers"]["change"] - y["survivors"]["trainers"]["change"])}
    (D / f"read_{a.it}.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, default=float))


if __name__ == "__main__":
    main()
