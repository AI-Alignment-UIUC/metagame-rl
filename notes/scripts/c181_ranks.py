"""C181's step 2, the check before any training (runs/probe/C181-table-practice/record.md): the plain fits' Trainer coefficients at seeds 48 and 49, from C171's plain table games (rules-only, human-free, read through play), by C165's fit. Ranks, SEs by jackknife over pods, and whether Oak, Energy Removal and Bill are in the top 8 on both seeds. Writes each seed's coefficients for the arm's Trainer weights. Lists are read only here, for the ranks' correlation.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c181_ranks.py
"""
import json

import numpy as np

import c165_read as R
from c139_read import pts, r3

ROOT = R.ROOT
D = ROOT / "runs/probe/C181-table-practice"
TARGET = ("Professor Oak", "Energy Removal", "Bill")


def fit(seed):
    R.OUT = ROOT / f"runs/probe/C171-table-drafting/table-plain-s{seed}"
    ds = R.load_design()
    res = json.loads((R.OUT / "games.json").read_text(encoding="utf-8"))["results"]
    ok = [x for x in res if not x.get("error")]
    a, b = np.array([x["i"] for x in ok]), np.array([x["j"] for x in ok])
    y = np.array([pts(x)[0] - 0.5 for x in ok])
    f = R.Fit(ds, a, b, y)
    lam, _ = f.choose_lambda()
    w = f.solve(f.pods, lam)
    beta = f.beta(w)
    se = f.jackknife(lam, f.beta)
    tn = list(ds["tn"])
    order = np.argsort(-beta)
    rank = {tn[i]: int(r) + 1 for r, i in enumerate(order)}
    target = R.lists_mean_copies(tn)
    return {"seed": seed, "games": len(y), "pods": len(f.pods), "lambda": lam, "sd": r3(float(beta.std())), "mean": r3(float(beta.mean())), "rho_L": r3(R.spearman(beta, target)), "top_12": [(tn[i], r3(float(beta[i])), r3(float(se[i]))) for i in order[:12]], "ranks_of_target": {n: rank.get(n) for n in TARGET}, "coefficients": {n: float(v) for n, v in zip(tn, beta)}}


def main():
    D.mkdir(exist_ok=True)
    out = {str(s): fit(s) for s in (48, 49)}
    a, b = out["48"]["coefficients"], out["49"]["coefficients"]
    k = sorted(set(a) & set(b))
    out["spearman_across_seeds"] = r3(R.spearman(np.array([a[q] for q in k]), np.array([b[q] for q in k])))
    out["all_in_top_8_on_both"] = all((out[s]["ranks_of_target"][n] or 99) <= 8 for s in ("48", "49") for n in TARGET)
    (D / "ranks.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for s in ("48", "49"):
        print(s, {q: out[s][q] for q in ("games", "pods", "lambda", "sd", "mean", "rho_L", "ranks_of_target")})
        print("   top 12", out[s]["top_12"])
    print("spearman across seeds", out["spearman_across_seeds"], "| Oak, ER, Bill in the top 8 on both:", out["all_in_top_8_on_both"])


if __name__ == "__main__":
    main()
