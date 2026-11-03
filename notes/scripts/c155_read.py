"""C155 (runs/screens/C155-powered-selection/record.md): powered selection. Per seed, from select.budget's evaluated decks over 0-29: the kept
moves' held-out half-B differences (the share above 0 and their mean with an SE across kept moves), the same for the moves not kept, the kept
moves' net draw- and tempo-copy change a move (mean and SE), moves an iteration; the drafting outcomes as C151 reads them (c151_read.read);
and the record's bands (R-power on the kept moves pooled over both seeds with a Wilson 95% CI, Amendment 1;
R-direction, R-lever, Harm), with half A's acceptance rate against the null's about 2.3%. Writes runs/screens/C155-powered-selection/readout.json.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c155_read.py
"""
import json
from pathlib import Path

import numpy as np

import c151_read as R

ROOT = Path(__file__).resolve().parents[2]
SCREENS = ROOT / "runs/screens"
RUNS = ["C155-R1-K-paired-budget-s44", "C155-R1-K-paired-budget-s45"]


def stat(xs):
    xs = np.asarray(xs, dtype=np.float64)
    if len(xs) < 2:
        return {"n": len(xs), "mean": float(xs.mean()) if len(xs) else None, "se": None}
    return {"n": len(xs), "mean": round(float(xs.mean()), 4), "se": round(float(xs.std(ddof=1) / np.sqrt(len(xs))), 4)}


def read(name):
    rows = [json.loads(x) for x in (SCREENS / name / "log.jsonl").read_text().splitlines() if x.strip()]
    ev = [e for r in rows for e in r["select"].get("budget", {}).get("evaluated", []) if e.get("entry") is not None]
    kept, rest = [e for e in ev if e["kept"]], [e for e in ev if not e["kept"]]
    out = {"iterations": len(rows), "evaluated": len(ev), "kept": len(kept),
           "kept_B_positive_share": round(sum(e["mB"] > 0 for e in kept) / len(kept), 3) if kept else None,
           "kept_B": stat([e["mB"] for e in kept]), "kept_A": stat([e["mA"] for e in kept]), "not_kept_B": stat([e["mB"] for e in rest]),
           "kept_d_draw": stat([e["d_draw"] for e in kept]), "kept_d_T4": stat([e["d_T4"] for e in kept]),
           "slots_per_deck": round(float(np.mean([e["n"] for e in ev])), 1) if ev else None}
    out.update({k: v for k, v in R.read(name).items() if k in ("errors", "moves_per_iter", "lambda_T4", "lambda_draw", "T4", "draw", "G1", "g1_watch")})
    vs = SCREENS / name / "vs_lists.json"
    out["G3"] = list(json.loads(vs.read_text())["pops"].values())[0]["M"] if vs.exists() else None
    out["types_at_last"] = rows[-1].get("types")
    return out


def main():
    out = {"runs": {n: read(n) for n in RUNS if (SCREENS / n / "log.jsonl").exists()}}
    r = list(out["runs"].values())
    if len(r) == 2:                                  # Amendment 1: R-power on the kept moves pooled over both seeds
        kept, evaluated = [], 0
        for name in RUNS:
            rows = [json.loads(x) for x in (SCREENS / name / "log.jsonl").read_text().splitlines() if x.strip()]
            ev = [e for rr in rows for e in rr["select"].get("budget", {}).get("evaluated", []) if e.get("entry") is not None]
            evaluated += len(ev)
            kept += [e for e in ev if e["kept"]]
        k, pos = len(kept), sum(e["mB"] > 0 for e in kept)
        share = pos / k if k else None
        z = 1.96                                     # Wilson score interval for the share above 0
        lo = ((share + z * z / (2 * k) - z * np.sqrt(share * (1 - share) / k + z * z / (4 * k * k))) / (1 + z * z / k)) if k else None
        pb = stat([e["mB"] for e in kept])
        pd = stat([e["d_draw"] for e in kept])
        b = {"pooled_kept": k, "pooled_B_positive_share": round(share, 3) if share is not None else None,
             "pooled_B_share_ci_low": round(float(lo), 3) if lo is not None else None, "pooled_kept_B": pb,
             "acceptance_rate": round(k / evaluated, 4) if evaluated else None, "acceptance_rate_null": 0.023,
             "per_seed_share": {name: out["runs"][name]["kept_B_positive_share"] for name in RUNS}, "pooled_kept_d_draw": pd}
        b["R-power"] = bool(share is not None and share >= 0.70 and lo > 0.5 and pb["se"] and pb["mean"] >= 2 * pb["se"])
        b["R-direction"] = bool(pd["se"] and pd["mean"] >= 2 * pd["se"])
        b["R-lever"] = all(x["T4"] >= 2.57 or x["draw"] >= 2.13 + 1.0 for x in r) or any(x["G1"] <= 5.92 for x in r)
        b["Harm"] = any(x["g1_watch"] for x in r) or all(x["G3"] is not None and x["G3"] < 0.25 for x in r)
        out["bands"] = b
        out["band"] = "Harm" if b["Harm"] else ", ".join(q for q in ("R-power", "R-direction", "R-lever") if b[q]) or "R-null"
    (SCREENS / "C155-powered-selection/readout.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
