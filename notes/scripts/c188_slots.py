"""C188 Amendment 3: what real paired games pay for an edit, from thompson_slots.jsonl (C150, C153). CPU, no games.
  PYTHONPATH=<root>;<root>/notes/scripts .venv/Scripts/python notes/scripts/c188_slots.py"""
import json
import os
from collections import Counter
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
import numpy as np

from c184_neutral_test import ROOT, card_kinds
from rl.decks import Pool

RUNS = ("C150-R1-K-paired-thompson-s36", "C150-R1-K-paired-thompson-s37", "C153-R1-K-paired-tbonus-s40", "C153-R1-K-paired-tbonus-s41")
pool = Pool()
kinds = card_kinds(pool)
basic = np.asarray(pool.basic_energy)


def rows(run):
    out = []
    for line in open(ROOT / "runs/screens" / run / "thompson_slots.jsonl", encoding="utf-8"):
        d = json.loads(line)
        for ids, dv, diff in d["slots"]:
            ids, dv = np.array(ids), np.array(dv)
            o, i = -dv.clip(max=0), dv.clip(min=0)
            k = kinds[ids]
            eo, ei = o[basic[ids]].sum(), i[basic[ids]].sum()
            out.append(dict(key=(d["iter"], tuple(ids.tolist()), tuple(dv.tolist())), iter=d["iter"], diff=diff, moved=o.sum(), P_out=o[k == 1].sum(), T_out=o[k == 2].sum(), E_out=o[k == 3].sum(),
                            P_in=i[k == 1].sum(), T_in=i[k == 2].sum(), E_in=i[k == 3].sum(), E_swap=min(eo, ei), drop=o.max()))
    return out


def ols(R, names):
    X = np.array([[1.0] + [r[n] for n in names] for r in R])
    y = np.array([r["diff"] for r in R])
    XtXi = np.linalg.pinv(X.T @ X)
    b = XtXi @ X.T @ y
    e = y - X @ b
    groups = {}
    for n, r in enumerate(R):
        groups.setdefault(r["key"], []).append(n)
    M = np.zeros((X.shape[1], X.shape[1]))
    for g in groups.values():
        v = X[g].T @ e[g]
        M += np.outer(v, v)
    return b, XtXi @ M @ XtXi, len(groups)


res = {}
for run in RUNS:
    R = rows(run)
    names = ["P_out", "T_out", "E_out", "P_in", "T_in", "E_swap"]
    b, V, ng = ols(R, names)
    se = np.sqrt(np.diag(V))
    i_t, i_e = names.index("T_out") + 1, names.index("E_out") + 1
    d = np.zeros(len(b)); d[i_t], d[i_e] = 1.0, -1.0
    gap, gap_se = float(d @ b), float(np.sqrt(d @ V @ d))
    b2, V2, _ = ols(R, ["moved"])
    print(f"\n{run}: slots {len(R)} candidates {ng} iters {min(r['iter'] for r in R)}-{max(r['iter'] for r in R)} mean diff {np.mean([r['diff'] for r in R]):+.4f} SD {np.std([r['diff'] for r in R]):.3f}")
    print("  " + "  ".join(f"{n} {b[j+1]:+.4f} ({se[j+1]:.4f})" for j, n in enumerate(names)))
    print(f"  T out minus E out {gap:+.4f} ({gap_se:.4f})   total moved alone {b2[1]:+.4f} ({np.sqrt(V2[1,1]):.4f})")
    for lab, f in (("moved", "moved"), ("largest drop", "drop"), ("E_swap", "E_swap")):
        c = {}
        for r in R:
            c.setdefault(min(int(r[f]), 12 if f == "moved" else 6), []).append(r["diff"])
        print(f"  by {lab}: " + " ".join(f"{k}:{np.mean(v):+.3f}(n{len(v)})" for k, v in sorted(c.items())))
    res[run] = dict(slots=len(R), candidates=ng, coef={n: [float(b[j + 1]), float(se[j + 1])] for j, n in enumerate(names)}, T_minus_E_out=[gap, gap_se], moved_alone=[float(b2[1]), float(np.sqrt(V2[1, 1]))])
(ROOT / "runs/probe/C188-head-out-signal/slots.json").write_text(json.dumps(res, indent=1))
