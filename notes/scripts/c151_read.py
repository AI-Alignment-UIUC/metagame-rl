"""C151 (runs/screens/C151-retest-winners/record.md) and C150's screen readouts on the same pattern: per run, the re-tests' positive share
(select.retest, pooled over 0-29), moves an iteration, the ledger's lean for T4 and the draw group (select_lean.cards with the record's draw
group Oak / Bill / Gambler added), the G1 set's T4 and draw copies a deck at 29 (c119_counts.g1_set) and G1 there (aa_window.dist); the four
W 0 ledger controls (C127 s16, s17; C129 s20, s21) read the same way; and C151's bands. Writes runs/screens/C151-retest-winners/readout.json.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c151_read.py
"""
import argparse
import json
from pathlib import Path

import numpy as np

import aa_window as aw
import c119_counts as cc
import select_lean as sl

ROOT = Path(__file__).resolve().parents[2]
SCREENS = ROOT / "runs/screens"
CONTROLS = ["C127-R1-K-paired-ledger-s16", "C127-R1-K-paired-ledger-s17", "C129-R1-K-paired-ledger-s20", "C129-R1-K-paired-ledger-s21"]
DRAW = ["Professor Oak", "Bill", "Gambler"]
sl.GROUPS["draw"] = DRAW


def read(name: str, it: int = 29) -> dict:
    run = SCREENS / name
    rows = {r["iter"]: r for r in (json.loads(x) for x in (run / "log.jsonl").read_text().splitlines() if x.strip())}
    its = sorted(rows)
    rt = [rows[i]["select"].get("retest") for i in its if rows[i].get("select", {}).get("retest")]
    played, kept = sum(x["played"] for x in rt), sum(x["kept"] for x in rt)
    groups, bad, _ = sl.cards(run)
    decks, _, match = cc.g1_set(run, it)
    bare = lambda n: n.rsplit(" ", 1)[0]
    per = [sum(bare(x) in cc.T4 for x in d) for d in decks]
    drw = [sum(bare(x) in DRAW for x in d) for d in decks]
    stop = (run / "STOP").read_text() if (run / "STOP").exists() else ""
    return {"iterations": len(its), "last": its[-1], "errors": sum(rows[i]["errors"] for i in its),
            "moves_per_iter": round(float(np.mean([rows[i]["select"]["moved"] for i in its])), 2),
            "retest": {"played": played, "kept": kept, "positive_share": round(kept / played, 3) if played else None},
            "lambda_T4": groups["T4"]["lambda"], "lambda_T4_se": groups["T4"]["se"], "lambda_draw": groups["draw"]["lambda"],
            "lambda_draw_se": groups["draw"]["se"], "ledger_integrity_failures": len(bad),
            "T4": round(float(np.mean(per)), 3), "draw": round(float(np.mean(drw)), 3), "G1": round(aw.dist(rows[it]), 2),
            "g1_set_shapes_matched": match, "g1_watch": "g1watch" in stop}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", default=["C151-R1-K-paired-retest-s38", "C151-R1-K-paired-retest-s39"])
    ap.add_argument("--out", default=str(SCREENS / "C151-retest-winners/readout.json"))
    a = ap.parse_args()
    out = {"runs": {n: read(n) for n in a.runs}, "controls": {n: read(n) for n in CONTROLS}}
    c = out["controls"].values()
    out["controls_mean"] = {k: round(float(np.mean([x[k] for x in c])), 4) for k in ("lambda_T4", "lambda_draw", "T4", "draw", "G1",
                                                                                       "moves_per_iter")}
    out["controls_max_lambda_draw"] = max(x["lambda_draw"] for x in c)
    r = list(out["runs"].values())
    cm = out["controls_mean"]
    lt4, ldr = float(np.mean([x["lambda_T4"] for x in r])), float(np.mean([x["lambda_draw"] for x in r]))
    out["bands"] = {
        "R-noise": all(x["retest"]["positive_share"] is not None and x["retest"]["positive_share"] <= 0.60 for x in r),
        "R-lever": all(x["T4"] >= 2.57 or x["draw"] >= cm["draw"] + 1.0 for x in r) or any(x["G1"] <= 5.92 for x in r),
        "R-ledger": (lt4 >= 0.004 and all(x["lambda_T4"] > -0.066 for x in r))
                    or (ldr >= 0.13 and all(x["lambda_draw"] > 0.104 for x in r)),
        "Harm": any(x["g1_watch"] or x["moves_per_iter"] < 3 for x in r),
        "pooled_lambda_T4": round(lt4, 4), "pooled_lambda_draw": round(ldr, 4)}
    b = out["bands"]
    out["band"] = ("Harm" if b["Harm"] else "R-lever" if b["R-lever"] else "R-ledger" if b["R-ledger"] else
                   "R-null (R-noise)" if b["R-noise"] else "between")
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
