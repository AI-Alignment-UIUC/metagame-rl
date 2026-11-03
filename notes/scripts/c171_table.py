"""C171's table (runs/probe/C171-table-drafting/record.md): C165's fit on a run's own factorial games, under the run's start pilot. Writes table.json ({Pokemon name: coefficient}) and fit.json: lambda, residual SD, r_sh over Pokemon names and Trainers, the Spearman
with C165's s16 table (under 0.6 means hold and report), and the top names.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c171_table.py --dir runs/probe/C171-table-drafting/table-s48
"""
import argparse
import json

import numpy as np

import c165_read as R
from c139_read import r3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    out = R.ROOT / a.dir
    R.OUT = out
    ds = R.load_design()
    _, x, z, y, _, err = R.games(out / "games.json")
    f = R.Fit(ds, x, z, y)
    lam, _ = f.choose_lambda()
    w = f.solve(f.pods, lam)
    k = len(ds["tn"])
    theta = w[1 + k + 4:]
    table = {n: float(v) for n, v in zip(ds["pn"], theta)}
    odd, even = [p for p in f.pods if p % 2], [p for p in f.pods if p % 2 == 0]
    wo, we = f.solve(odd, lam), f.solve(even, lam)
    ref = json.loads((R.ROOT / "runs/probe/C165-trainer-factorial/summary.json").read_text(encoding="utf-8"))["pilots"]["s16"]["pokemon"]["all"]
    both = sorted(set(ref) & set(table))
    fit = {"games": len(y), "errors": err, "lambda": lam, "residual_sd": r3(f.residual_sd(w)), "names": len(table), "names_shared_with_s16_table": len(both),
           "r_sh_pokemon": r3(R.spearman(wo[1 + k + 4:], we[1 + k + 4:])), "r_sh_trainers": r3(R.spearman(wo[1:1 + k], we[1:1 + k])),
           "spearman_with_s16_table": r3(R.spearman([table[n] for n in both], [ref[n] for n in both])),
           "top": [[n, r3(v)] for n, v in sorted(table.items(), key=lambda t: -t[1])[:12]], "sd": r3(float(np.std(theta)))}
    fit["hold"] = fit["spearman_with_s16_table"] < 0.6
    (out / "table.json").write_text(json.dumps(table), encoding="utf-8")
    (out / "fit.json").write_text(json.dumps(fit, indent=1), encoding="utf-8")
    print(json.dumps(fit))


if __name__ == "__main__":
    main()
