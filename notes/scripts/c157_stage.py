"""C157 (runs/screens/C157-powered-small-pop/record.md): a stage readout for both seeds at their last logged iteration, one JSON line each to
stdout: kept moves so far (select.budget) with their half-B-positive share and mean; the population's median P/T/E; the G1 set's mean
P/T/E and G1 (the top 12 of 24 by z, aa_window.dist); T4 and draw copies a deck in that set (c119_counts.g1_set, at a saved snapshot);
the largest type. With --power it also prints the pooled half-B-positive share over both seeds and exits 3 if it is under 0.6 (the
record's power check at stage 2's end).
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c157_stage.py [--power]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

import aa_window as aw
import c119_counts as cc

ROOT = Path(__file__).resolve().parents[2]
RUNS = ["C157-R1-K-paired-smallpop-s46", "C157-R1-K-paired-smallpop-s47"]
DRAW = ("Professor Oak", "Bill", "Gambler")


def stage(name):
    run = ROOT / "runs/screens" / name
    rows = [json.loads(x) for x in (run / "log.jsonl").read_text().splitlines() if x.strip()]
    r = rows[-1]
    ev = [e for x in rows for e in x["select"].get("budget", {}).get("evaluated", []) if e.get("entry") is not None]
    kept = [e for e in ev if e["kept"]]
    sh = np.array(r["shapes"], dtype=float)
    z = np.array([np.nan if v is None else v for v in r["z"]], dtype=float)
    top = np.argsort(-np.nan_to_num(z, nan=-1))[:12]
    out = {"run": name, "iter": r["iter"], "errors": sum(x["errors"] for x in rows), "kept": len(kept), "evaluated": len(ev),
           "kept_B_pos": sum(e["mB"] > 0 for e in kept), "kept_B_mean": round(float(np.mean([e["mB"] for e in kept])), 4) if kept else None,
           "median_pte": [r["shape_quartiles"][k][1] for k in ("pokemon", "trainer", "energy")],
           "median_pte_it0": [rows[0]["shape_quartiles"][k][1] for k in ("pokemon", "trainer", "energy")],
           "g1_set_pte": np.round(sh[top].mean(0), 2).tolist(), "G1": round(aw.dist(r), 2), "types": r.get("types")}
    snap = max((x["iter"] for x in rows if (run / f"population_it{x['iter']:04d}.pt").exists()), default=None)
    if snap is not None:
        decks, _, _ = cc.g1_set(run, snap)
        bare = lambda n: n.rsplit(" ", 1)[0]
        out.update({"snapshot": snap, "T4": round(float(np.mean([sum(bare(c) in cc.T4 for c in d) for d in decks])), 3),
                    "draw": round(float(np.mean([sum(bare(c) in DRAW for c in d) for d in decks])), 3)})
    return out, kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--power", action="store_true")
    a = ap.parse_args()
    pooled = []
    for name in RUNS:
        if not (ROOT / "runs/screens" / name / "log.jsonl").exists():
            continue
        out, kept = stage(name)
        pooled += kept
        print(json.dumps(out), flush=True)
    if a.power:
        share = sum(e["mB"] > 0 for e in pooled) / len(pooled) if pooled else None
        print(json.dumps({"power_check": {"pooled_kept": len(pooled), "share_B_positive": round(share, 3) if share is not None else None,
                                          "pass": share is not None and share >= 0.6}}), flush=True)
        if share is None or share < 0.6:
            sys.exit(3)


if __name__ == "__main__":
    main()
