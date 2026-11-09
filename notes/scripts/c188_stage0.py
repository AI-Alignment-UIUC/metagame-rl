"""C188 stage 0 (runs/probe/C188-head-out-signal/record.md): is W's Trainer cut a cut of low-count names, or of the class?
Within-deck fit of the head's out score on log(copies) and class. CPU, no games.
  CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c188_stage0.py
--at 29 --runs a,b,c: the same fit at one iteration per run (the record's natural experiment on beta).
"""
import argparse
import json
import os
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
import numpy as np
import torch

from c184_neutral_test import ROOT, card_kinds
from c187_caps import load_weights, out_scores
from rl.decks import Pool
from rl.remote import RemotePool

OUT = ROOT / "runs/probe/C188-head-out-signal"


def collect(run_name, its, pool, info, kinds):
    run = ROOT / "runs/screens" / run_name
    cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
    rows = []
    for it in its:
        st, net, head = load_weights(run, it, pool, info, cfg)
        rng = np.random.default_rng(1873 + it)                   # #912's fields
        decks = [np.array(pool.vector(x["deck"])) for x in st["population"]]
        for d, a in enumerate(st["population"]):
            others = [e for e in range(len(decks)) if e != d]
            field = [decks[e] for e in rng.choice(others, cfg["field_sample"], replace=False)]
            ids, s = out_scores(head, net, decks[d], field)
            rows.append((a["id"], ids, decks[d][ids].astype(float), kinds[ids], s))
    return rows


def fit(rows, klass=None):
    """OLS with deck fixed effects: s on log(count) and T, E dummies, or on log(count) alone inside one class."""
    X, Y = [], []
    for _, ids, c, k, s in rows:
        m = np.ones(len(ids), bool) if klass is None else k == klass
        if m.sum() < 2:
            continue
        x = np.log(c[m])[:, None] if klass is not None else np.c_[np.log(c), k == 2, k == 3].astype(float)
        X.append(x - x.mean(0))
        Y.append(s[m] - s[m].mean())
    return np.linalg.lstsq(np.concatenate(X), np.concatenate(Y), rcond=None)[0]


def ratios(rows, sfun):
    """Mean out share over mean copy share, by P, T, E, under the scores sfun gives."""
    out, cop = np.zeros(3), np.zeros(3)
    for _, ids, c, k, s in rows:
        po = np.log(c) + sfun(c, k, s)
        po = np.exp(po - po.max())
        po /= po.sum()
        for i, x in enumerate((1, 2, 3)):
            out[i] += po[k == x].sum()
            cop[i] += c[k == x].sum() / c.sum()
    return out / cop


def summarize(rows):
    g, ot, oe = fit(rows)
    obs = ratios(rows, lambda c, k, s: s)
    conly = ratios(rows, lambda c, k, s: g * np.log(c))
    konly = ratios(rows, lambda c, k, s: ot * (k == 2) + oe * (k == 3))
    return dict(g=g, ot=ot, oe=oe, obs=obs, conly=conly, konly=konly,
                share=(conly[1] - 1) / (obs[1] - 1) if abs(obs[1] - 1) > 1e-6 else float("nan"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", type=int)
    ap.add_argument("--runs", default="C171-W-s48,C171-W-s49")
    ap.add_argument("--jsonl", help="with --at: append the fit as a row here and leave beta_at{N}.json alone (queue_c188's reads)")
    a = ap.parse_args()
    torch.set_num_threads(4)
    pool = Pool()
    kinds = card_kinds(pool)
    rp = RemotePool(1)
    info = rp.ask_all([{"cmd": "info"}])[0]
    rp.close()
    res = {}
    if a.at is not None:
        for r in a.runs.split(","):
            s = summarize(collect(r, (a.at,), pool, info, kinds))
            res[r] = {k: float(s[k]) for k in ("g", "ot", "oe", "share")} | {"T_ratio": float(s["obs"][1]), "E_ratio": float(s["obs"][2])}
            print(r, a.at, {k: round(v, 3) for k, v in res[r].items()}, flush=True)
            if a.jsonl:
                with open(a.jsonl, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"run": r, "iter": a.at, **res[r]}) + "\n")
        if not a.jsonl:
            (OUT / f"beta_at{a.at}.json").write_text(json.dumps(res, indent=1))
        return
    for r in a.runs.split(","):
        late = collect(r, (34, 39, 44), pool, info, kinds)
        S = summarize(late)
        uid = sorted({x[0] for x in late})
        by = {u: [x for x in late if x[0] == u] for u in uid}
        rng = np.random.default_rng(188)
        B = []
        for _ in range(400):
            b = summarize([x for u in rng.choice(uid, len(uid)) for x in by[u]])
            B.append((b["g"], b["ot"] - b["oe"], b["share"]))
        se = np.array(B).std(0)
        inside = {n: float(fit(late, x)[0]) for n, x in (("P", 1), ("T", 2), ("E", 3))}
        res[r] = dict(gamma=S["g"], gamma_se=se[0], offset_T=S["ot"], offset_E=S["oe"], T_minus_E_se=se[1], count_share=S["share"], count_share_se=se[2],
                      obs=S["obs"].tolist(), conly=S["conly"].tolist(), konly=S["konly"].tolist(), inside=inside)
        print(r, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in res[r].items()}, flush=True)
    (OUT / "stage0.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
