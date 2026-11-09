"""C190 (runs/probe/C190-edit-channel-split/record.md): where a deck's shape at iteration N came from, split exactly per deck
alive at N into its entry (S) and its kept edits: single in-picks (K_in), single out-picks (K_out), group moves in (G_in) and
out (G_out), for Energy (basic + special), Trainers and Pokemon. CPU only; reads a run's edit_slots.jsonl, log.jsonl and
population_it*.pt; writes only into the record's folder.

Kept = rl.metagame.paired_move with --candidates 1: mean of (candidate - deck) over the row's complete slots above its SE
(ddof 1), n >= 2. A pick [out, copies, n, in] moves 1 + n copies of out to in; n > 0 is a group move, all 1 + n counted as G.
Entry = the deck in the first snapshot holding it, minus its kept edits up to that snapshot (snapshots are saved after
selection and turnover). Integrity gate: entry + kept edits must rebuild every deck in every snapshot up to N, and each
iteration's kept edits must match log.jsonl's select.moved, select.acc x moved and select.card.acc_net; otherwise VOID.

    py notes/scripts/c190_split.py --run C188-W0S-s48 --at 44
    py notes/scripts/c190_split.py --control C171-W-s48 --at 44      # W: no edit_slots, population-level S and net K only
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.decks import Pool                    # noqa: E402
from rl.metagame import recent_score         # noqa: E402

OUT = ROOT / "runs/probe/C190-edit-channel-split"
POOL = Pool()
ST = {c["fullName"]: c["superType"] for c in POOL.cards}           # 1 Pokemon, 2 Trainer, 3 Energy
CLS = {"P": 1, "T": 2, "E": 3}
REF = {"P": 13.5, "T": 28, "E": 18}                                 # the lists' medians: the reading's reference only


def shape(v):
    st = np.zeros(POOL.n, dtype=np.int64)
    for c in POOL.cards:
        st[c["id"]] = c["superType"]
    return {k: int(v[st == s].sum()) for k, s in CLS.items()}


def snaps(run, at):
    out = {}
    for f in sorted(run.glob("population_it*.pt")):
        it = int(f.stem[-4:])
        if it <= at:
            p = torch.load(f, map_location="cpu", weights_only=False)["population"]
            out[it] = {a["id"]: (POOL.vector(a["deck"]), a) for a in p}
    return out


def log_rows(run):
    rows = {}
    for l in open(run / "log.jsonl", encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            rows[r["iter"]] = r                                   # a resumed run's later row wins
    return rows


def kept_rule(slots):
    """edit_slots rounds results to 4 places; they are thirds (0, 1/3, 2/3, 1 on these runs), restored exactly so a borderline
    m against se reads as rl.metagame read it (W0S s48's (15, 12): 8e-6 above se rounded, below it exact)."""
    d = np.array([round(c * 3) / 3 - round(a * 3) / 3 for _, a, c in slots], dtype=np.float64)
    assert all(abs(x * 3 - round(x * 3)) < 1e-3 for _, a, c in slots for x in (a, c)), "a slot result that isn't a third"
    if len(d) < 2:
        return False, None
    m, se = d.mean(), d.std(ddof=1) / np.sqrt(len(d))
    return bool(m > se), float(m - se)


def edits(run, at):
    """(iter, deck) -> the row, kept or not; the last row wins on a repeat."""
    rows = {}
    for l in open(run / "edit_slots.jsonl", encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            if r["iter"] <= at and r["entry"] == 1:
                rows[(r["iter"], r["deck"])] = r
    for r in rows.values():
        r["kept"], r["margin"] = kept_rule(r["slots"])
        dv = np.zeros(POOL.n, dtype=np.int64)
        for out, _, n, inn in r["picks"]:
            dv[POOL.id[out]] -= 1 + n
            dv[POOL.id[inn]] += 1 + n
        r["dv"] = dv
    return rows


def channels(r):
    """Per class: K_in, K_out, G_in, G_out of one kept row."""
    c = {k: [0, 0, 0, 0] for k in CLS}
    for out, _, n, inn in r["picks"]:
        g = 2 if n > 0 else 0
        for k, s in CLS.items():
            if ST[inn] == s:
                c[k][g] += 1 + n
            if ST[out] == s:
                c[k][g + 1] -= 1 + n
    return c


def split(name, at):
    run = ROOT / "runs/screens" / name
    S, L, E = snaps(run, at), log_rows(run), edits(run, at)
    assert at in S, f"no population_it{at:04d}.pt in {run}"
    kept = defaultdict(dict)                                      # deck -> iter -> row
    for (it, d), r in E.items():
        if r["kept"]:
            kept[d][it] = r
    gate = {"iters": 0, "moved_mismatch": [], "acc_mismatch": [], "card_mismatch": [], "snap_decks": 0, "snap_mismatch": []}
    # each iteration's kept edits against the log
    for it in range(0, at + 1):
        sel = (L.get(it) or {}).get("select") or {}
        ks = [r for (i, _), r in E.items() if i == it and r["kept"]]
        gate["iters"] += 1
        if sel.get("moved") != len(ks):
            gate["moved_mismatch"].append([it, sel.get("moved"), len(ks)])
        if ks:
            tot = np.sum([[shape(r["dv"])[k] for k in CLS] for r in ks], 0)
            acc = np.array(sel.get("acc") or [0, 0, 0]) * len(ks)
            if np.abs(tot - acc).max() > 0.0005 * len(ks) + 1e-9:
                gate["acc_mismatch"].append([it, tot.tolist(), np.round(acc, 3).tolist()])
            net = np.sum([r["dv"] for r in ks], 0)
            logged = np.zeros(POOL.n, dtype=np.int64)
            for i, v in ((sel.get("card") or {}).get("acc_net") or {}).items():
                logged[int(i)] = v
            if not np.array_equal(net, logged):
                gate["card_mismatch"].append([it, int(np.abs(net - logged).sum())])
    # entry of every deck that ever appears, and the rebuild of every snapshot
    first = {}
    for it in sorted(S):
        for d in S[it]:
            first.setdefault(d, it)
    entry, born = {}, {}
    for d, it0 in first.items():
        v, a = S[it0][d]
        dv = sum((r["dv"] for i, r in kept[d].items() if i <= it0), np.zeros(POOL.n, dtype=np.int64))
        entry[d], born[d] = v - dv, a.get("born", 0)
    for it in sorted(S):
        for d, (v, _) in S[it].items():
            gate["snap_decks"] += 1
            dv = sum((r["dv"] for i, r in kept[d].items() if i <= it), np.zeros(POOL.n, dtype=np.int64))
            if not np.array_equal(entry[d] + dv, v):
                gate["snap_mismatch"].append([it, d])
    ties = sum(1 for r in E.values() if r["margin"] is not None and abs(r["margin"]) < 1e-12)    # m = se exactly (often all-zero differences): not kept
    ok = not any(gate[k] for k in ("moved_mismatch", "acc_mismatch", "card_mismatch", "snap_mismatch"))
    gate["tie_rows"] = ties

    def decomp(ids):
        out = {}
        for k in CLS:
            per = []
            for d in ids:
                ch = np.sum([channels(r)[k] for i, r in kept[d].items() if i <= at] or [[0, 0, 0, 0]], 0)
                s = shape(entry[d])[k] - REF[k]
                x = shape(S[at][d][0])[k] - REF[k]
                assert abs(s + ch.sum() - x) < 1e-9, (d, k)
                per.append([x, s, *ch])
            a = np.array(per, dtype=np.float64)
            m = a.mean(0)
            se = a.std(0, ddof=1) / np.sqrt(len(a)) if len(a) > 1 else np.zeros(6)
            out[k] = {"X": round(m[0], 3), "S": round(m[1], 3), "K_in": round(m[2], 3), "K_out": round(m[3], 3), "G_in": round(m[4], 3),
                      "G_out": round(m[5], 3), "K": round(m[2:].sum(), 3), "se": {"X": round(se[0], 3), "S": round(se[1], 3), "K": round(float(a[:, 2:].sum(1).std(ddof=1) / np.sqrt(len(a))), 3) if len(a) > 1 else 0.0}}
        return out

    alive = list(S[at])
    top = [a["id"] for a in sorted((a for _, a in S[at].values()), key=lambda a: -recent_score(a, 0.0))[:12]]
    res = {"run": name, "at": at, "gate": "PASS" if ok else "VOID", "gate_detail": gate,
           "kept_rows": sum(1 for r in E.values() if r["kept"]), "rows": len(E),
           "moved_logged": sum(((L.get(i) or {}).get("select") or {}).get("moved", 0) for i in range(at + 1)),
           "alive": decomp(alive), "top12": decomp(top)}
    # S's split: the generator's mean entry (all decks that ever entered) and survivors' selection
    for k in CLS:
        gen = np.mean([shape(entry[d])[k] for d in entry]) - REF[k]
        res["alive"][k]["S_generator"] = round(float(gen), 3)
        res["alive"][k]["S_selection"] = round(res["alive"][k]["S"] - float(gen), 3)
        res["alive"][k]["entered"] = len(entry)
    # groups' share of Energy brought in, and gross Trainer removals
    ae = res["alive"]["E"]
    res["E_in_group_share"] = round(ae["G_in"] / (ae["K_in"] + ae["G_in"]), 3) if ae["K_in"] + ae["G_in"] else None
    res["T_gross_removed"] = round(res["alive"]["T"]["K_out"] + res["alive"]["T"]["G_out"], 3)
    allk = [r for r in E.values() if r["kept"]]
    res["T_gross_removed_all_kept"] = int(sum(channels(r)["T"][1] + channels(r)["T"][3] for r in allk))
    # proposed and kept Energy shares of the copies moved in and out, by stage
    stages = {}
    for lo, hi in ((0, 14), (15, 29), (30, 44)):
        if lo > at:
            continue
        rs = [r for (i, _), r in E.items() if lo <= i <= min(hi, at)]
        row = {}
        for lab, sub in (("proposed", rs), ("kept", [r for r in rs if r["kept"]])):
            ins = outs = ein = eout = 0
            for r in sub:
                for out, _, n, inn in r["picks"]:
                    ins += 1 + n
                    outs += 1 + n
                    ein += (1 + n) * (ST[inn] == 3)
                    eout += (1 + n) * (ST[out] == 3)
            row[lab] = {"E_share_in": round(ein / ins, 3) if ins else None, "E_share_out": round(eout / outs, 3) if outs else None, "rows": len(sub)}
        stages[f"{lo}-{min(hi, at)}"] = row
    res["stages"] = stages
    return res


def control(name, at):
    """W has no edit_slots: population-level S and net K from select.acc x moved, summed over iterations, per deck slot."""
    run = ROOT / "runs/screens" / name
    L = log_rows(run)
    p = torch.load(run / f"population_it{at:04d}.pt", map_location="cpu", weights_only=False)["population"]
    D = len(p)
    x = np.mean([[shape(POOL.vector(a["deck"]))[k] for k in CLS] for a in p], 0) - np.array([REF[k] for k in CLS])
    netk = np.sum([np.array(L[i]["select"]["acc"]) * L[i]["select"]["moved"] for i in range(at + 1) if (L.get(i) or {}).get("select", {}).get("acc")], 0) / D
    return {"run": name, "at": at, "note": "population level, not lineage-exact: net K includes edits to decks that later died", **{k: {"X": round(float(x[j]), 3), "netK": round(float(netk[j]), 3), "S_approx": round(float(x[j] - netk[j]), 3)} for j, k in enumerate(CLS)}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--control")
    ap.add_argument("--at", type=int, default=44)
    a = ap.parse_args()
    res = split(a.run, a.at) if a.run else control(a.control, a.at)
    OUT.mkdir(exist_ok=True)
    f = OUT / f"split_{a.run or a.control}_at{a.at}.json"
    f.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in res if k not in ("gate_detail",)} | ({"gate_detail": {k: (v if not isinstance(v, list) else v[:5]) for k, v in res["gate_detail"].items()}} if "gate_detail" in res else {}), indent=1))


if __name__ == "__main__":
    main()
