"""C192 (runs/probe/C192-turnover-energy-split/record.md): at each turnover (iterations 4, 9, ..., 44), the population mean's
change split into the kill term, sum over removed decks of (X_pop - X_out) / D, and dilution, sum over entrants of
(X_in - X_pop) / D (wide and mutant apart), X_pop the mean just before the turnover, for E (basic + special), T and P.
Snapshots are saved at an iteration's end, after its selection and then its turnover, so population_it0004 already holds
iteration 4's entrants; the population just before turnover t is snapshot t-5 plus kept edits t-4..t.
--run (edit_slots arms): exact, through c190_split's rebuild. --approx (W, no edit_slots): X_pop from snapshot t-5 plus
log.jsonl's drift (select.moved x select.acc / D, acc rounded to 3 places), kill as the remainder; each removed deck's own
composition taken at snapshot t-5, so the score correlation only is approximate.
Gate: drift + kill + dilution reproduces each window's change in population mean within 0.05; VOID otherwise.
    py notes/scripts/c192_split.py --run C188-W0S-s48 --at 44
    py notes/scripts/c192_split.py --approx C171-W-s48 --at 44
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c190_split as C                                   # noqa: E402

OUT = C.ROOT / "runs/probe/C192-turnover-energy-split"
K = ("E", "T", "P")
J = {"P": 0, "T": 1, "E": 2}                             # log.jsonl's acc order


def vec(v):
    s = C.shape(v)
    return {k: s[k] for k in K}


def split(name, at, exact):
    run = C.ROOT / "runs/screens" / name
    S, L = C.snaps(run, at), C.log_rows(run)
    D = len(S[0])
    kept = defaultdict(dict)
    if exact:
        for (it, d), r in C.edits(run, at).items():
            if r["kept"]:
                kept[d][it] = r

    def drift_log(lo, hi):                               # summed drift over iterations lo..hi, from the log
        out = {k: 0.0 for k in K}
        for i in range(lo, hi + 1):
            s = (L.get(i) or {}).get("select") or {}
            if s.get("acc"):
                for k in K:
                    out[k] += s["moved"] * s["acc"][J[k]] / D
        return out

    def comp(d, it_from, it):                            # exact: the deck at the end of `it`'s selection, from snapshot it_from
        v = S[it_from][d][0].copy()
        for i, r in kept[d].items():
            if it_from < i <= it:
                v = v + r["dv"]
        return v

    mean = lambda it: {k: float(np.mean([vec(v)[k] for v, _ in S[it].values()])) for k in K}
    events, gate, removed = [], [], []
    tot = {k: {"drift": 0.0, "kill": 0.0, "dil_wide": 0.0, "dil_mutant": 0.0} for k in K}
    for t in range(4, at + 1, 5):
        prev = t - 5 if t >= 9 else 0
        tov = (L.get(t) or {}).get("turnover") or []
        outs, ins = {x["out"] for x in tov}, {x["in"]: x["kind"] for x in tov}
        if exact:
            pre = {d: vec(comp(d, prev, t)) for d in S[prev]}
            dr = {k: (np.mean([pre[d][k] for d in pre]) - mean(prev)[k]) for k in K}
            xpop = {k: float(np.mean([pre[d][k] for d in pre])) for k in K}
            xout = {d: pre[d] for d in outs}
        else:
            dr = drift_log(prev + 1, t)
            xpop = {k: mean(prev)[k] + dr[k] for k in K}
            xout = {d: vec(S[prev][d][0]) for d in outs if d in S[prev]}   # approximate: before t-4..t's edits
        xin = {d: (vec(S[t][d][0]), ins[d]) for d in ins}
        assert set(S[t]) == (set(S[prev]) - outs) | set(ins), f"turnover {t}: snapshot ids don't follow the log"
        ev = {"iter": t, "removed": len(outs), "wide": sum(1 for _, k in xin.values() if k == "wide"), "mutant": sum(1 for _, k in xin.values() if k == "mutant")}
        for k in K:
            dil = {kind: sum(x[k] - xpop[k] for x, kk in xin.values() if kk == kind) / D for kind in ("wide", "mutant")}
            step = mean(t)[k] - xpop[k]                          # turnover's change in the mean
            kill = step - dil["wide"] - dil["mutant"] if not exact else sum(xpop[k] - xout[d][k] for d in outs) / D
            if exact:
                gate.append([t, k, round(step - kill - dil["wide"] - dil["mutant"], 6)])
            win = mean(t)[k] - mean(prev)[k]                     # the log's drift, an independent source in exact mode
            gate.append([t, k, "window", round(win - (drift_log(prev + 1, t)[k] + kill + dil["wide"] + dil["mutant"]), 6)])
            ev[k] = {"pop_before": round(xpop[k], 3), "drift": round(dr[k], 4), "kill": round(kill, 4), "dil_wide": round(dil["wide"], 4),
                     "dil_mutant": round(dil["mutant"], 4), "in_mean": {kind: (round(float(np.mean([x[k] for x, kk in xin.values() if kk == kind])), 2)
                                                                         if any(kk == kind for _, kk in xin.values()) else None) for kind in ("wide", "mutant")},
                     "out_mean": round(float(np.mean([xout[d][k] for d in xout])), 2) if xout else None}
            tot[k]["drift"] += dr[k]
            tot[k]["kill"] += kill
            tot[k]["dil_wide"] += dil["wide"]
            tot[k]["dil_mutant"] += dil["mutant"]
        for x in tov:
            if x["out"] in xout:
                removed.append((x["score"], xout[x["out"]]["E"], xout[x["out"]]["T"]))
        events.append(ev)
    worst = max(abs(g[-1]) for g in gate)
    res = {"run": name, "at": at, "exact": exact, "snapshot_timing": "after the iteration's selection and turnover (population_it0004 holds iteration 4's entrants)",
           "gate": "PASS" if worst <= 0.05 else "VOID", "gate_worst": worst, "D": D}
    for k in K:
        t_ = tot[k]
        term = t_["kill"] + t_["dil_wide"] + t_["dil_mutant"]
        dil = t_["dil_wide"] + t_["dil_mutant"]
        res[k] = {"pop_0": round(mean(0)[k], 3), "pop_at": round(mean(at)[k], 3), "drift": round(t_["drift"], 3), "turnover_term": round(term, 3),
                  "kill": round(t_["kill"], 3), "dilution": round(dil, 3), "dil_wide": round(t_["dil_wide"], 3), "dil_mutant": round(t_["dil_mutant"], 3),
                  "kill_share": round(t_["kill"] / term, 3) if term else None, "dilution_share": round(dil / term, 3) if term else None}
    if removed:
        r = np.array(removed, dtype=float)
        res["removed_corr_score_E"] = round(float(np.corrcoef(r[:, 0], r[:, 1])[0, 1]), 3)
        res["removed_corr_score_T"] = round(float(np.corrcoef(r[:, 0], r[:, 2])[0, 1]), 3)
        res["removed_n"] = len(r)
    e = res["E"]
    if e["turnover_term"] > 0:
        res["band_E"] = ("R-kill" if e["kill"] >= 0.5 * e["turnover_term"] else
                         "R-generator" if e["dilution"] >= 0.5 * e["turnover_term"] and e["kill"] < 0.25 * e["turnover_term"] else "between")
    else:
        res["band_E"] = "turnover term not positive: bands don't apply"
    res["events"] = events
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--approx")
    ap.add_argument("--at", type=int, default=44)
    a = ap.parse_args()
    name = a.run or a.approx
    res = split(name, a.at, exact=bool(a.run))
    OUT.mkdir(exist_ok=True)
    (OUT / f"split_{name}_at{a.at}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "events"}, indent=1))


if __name__ == "__main__":
    main()
