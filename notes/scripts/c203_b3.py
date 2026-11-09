"""C203 (b3) read (runs/probe/C203-lists-in-selection/record.md, Amendments 1-2): the 24 lists under W s48's frozen nets, turnover on.
At --at IT (59 or 74; snapshots every iteration from 45; the lists are the population "at 44"):
- the nets' hashes against W s48's snapshot (a difference is a learner update: exit 9, the record's kill);
- the population mean E (basic + special) change from the lists, split exactly (C192's split, through edit_slots' kept edits,
  c190_split's kept rule): edits' drift at every iteration, and at each turnover (49, 54, ...) kill (removed decks) and dilution
  (wide and mutant entrants), with a rebuild gate (non-turnover iterations: previous snapshot + kept edits = this one, deck by deck)
  and the identity drift + turnover terms = total change;
- the same for T and P; by lineage (parents followed to a root): the share of the population descended from the lists, from wide
  entrants, the lists' descendants' own mean P/T/E and its change from the lists, and entrant survival past 20 iterations.
    PYTHONPATH=. .venv/Scripts/python notes/scripts/c203_b3.py --run runs/screens/C203-lists-b3-s48 --at 59
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
sys.path.insert(0, str(ROOT))
import c190_split as C                                   # noqa: E402
from c203_b import hashes, SRC                           # noqa: E402
from rl.decks import archived_decks                      # noqa: E402

P = C.POOL
KIND = np.zeros(P.n, dtype=np.int64)
for c in P.cards:
    KIND[c["id"]] = c["superType"]
K = {"P": 1, "T": 2, "E": 3}
START = 45


def shape(v):
    return {k: int(v[KIND == s].sum()) for k, s in K.items()}


def main():
    run = ROOT / sys.argv[sys.argv.index("--run") + 1]
    at = int(sys.argv[sys.argv.index("--at") + 1])
    h0, _ = hashes(SRC)
    h1, _ = hashes(run / f"population_it{at:04d}.pt")
    S, meta = {}, {}
    lists = [v for _, v in archived_decks(P)]
    S[START - 1] = {i: np.asarray(v) for i, v in enumerate(lists)}
    meta.update({i: {"kind": "list", "parent": None, "born": START - 20} for i in range(len(lists))})
    for it in range(START, at + 1):
        pop = torch.load(run / f"population_it{it:04d}.pt", map_location="cpu", weights_only=False)["population"]
        S[it] = {a["id"]: (P.vector(a["deck"]) if isinstance(a["deck"], list) else np.asarray(a["deck"])) for a in pop}
        for a in pop:
            meta.setdefault(a["id"], {"kind": a.get("kind"), "parent": a.get("parent"), "born": a.get("born")})
    L = C.log_rows(run)
    E = C.edits(run, at)
    kept = defaultdict(dict)
    for (it, d), r in E.items():
        if r["kept"]:
            kept[it][d] = r["dv"]
    D = len(lists)
    mean = lambda decks, k: float(np.mean([shape(v)[k] for v in decks.values()]))
    tot = {k: {"drift": 0.0, "kill": 0.0, "dil_wide": 0.0, "dil_mutant": 0.0} for k in K}
    gate = {"rebuild_mismatch": [], "identity_worst": 0.0}
    for it in range(START, at + 1):
        prev = S[it - 1]
        pre = {d: prev[d] + kept[it].get(d, 0) for d in prev}
        tov = (L.get(it) or {}).get("turnover") or []
        for k in K:
            tot[k]["drift"] += mean(pre, k) - mean(prev, k)
        if tov:
            outs, ins = {x["out"] for x in tov}, {x["in"]: x["kind"] for x in tov}
            for k in K:
                xpop = mean(pre, k)
                kill = sum(xpop - shape(pre[d])[k] for d in outs) / D
                dil = {kd: sum(shape(S[it][d])[k] - xpop for d, kk in ins.items() if kk == kd) / D for kd in ("wide", "mutant")}
                tot[k]["kill"] += kill
                tot[k]["dil_wide"] += dil["wide"]
                tot[k]["dil_mutant"] += dil["mutant"]
                gate["identity_worst"] = max(gate["identity_worst"], abs(mean(S[it], k) - xpop - kill - dil["wide"] - dil["mutant"]))
            kept_ids = set(prev) - outs
        else:
            kept_ids = set(prev)
        for d in kept_ids:
            if d in S[it] and not np.array_equal(pre[d], S[it][d]):
                gate["rebuild_mismatch"].append([it, d])

    def root(d):
        seen = 0
        while meta.get(d, {}).get("parent") is not None and seen < 999:
            d, seen = meta[d]["parent"], seen + 1
        return meta.get(d, {}).get("kind")
    end = S[at]
    by_root = defaultdict(list)
    for d, v in end.items():
        by_root[root(d)].append(v)
    lists_mean = {k: float(np.mean([shape(v)[k] for v in lists])) for k in K}
    entrants = [d for d, m in meta.items() if m["kind"] in ("wide", "mutant")]
    surv = {}
    for d in entrants:
        b = meta[d]["born"]
        if b is not None and b + 20 <= at:
            surv.setdefault(b, [0, 0])
            surv[b][1] += 1
            surv[b][0] += d in S[b + 20]
    out = {"run": run.relative_to(ROOT).as_posix(), "at": at, "hash_source": h0, "hash_at": h1, "learner_unchanged": h0 == h1,
           "gate": "PASS" if not gate["rebuild_mismatch"] and gate["identity_worst"] < 1e-9 else "VOID",
           "gate_detail": {"rebuild_mismatch": gate["rebuild_mismatch"][:10], "identity_worst": gate["identity_worst"]},
           "lists_mean_pte": [round(lists_mean[k], 3) for k in K], "pop_mean_pte": [round(mean(end, k), 3) for k in K],
           "split": {k: {**{q: round(v, 3) for q, v in tot[k].items()}, "total": round(mean(end, k) - lists_mean[k], 3),
                         "turnover": round(tot[k]["kill"] + tot[k]["dil_wide"] + tot[k]["dil_mutant"], 3)} for k in K},
           "share_by_root": {r: round(len(v) / len(end), 3) for r, v in by_root.items()},
           "list_descendants": {"n": len(by_root.get("list", [])),
                                "mean_pte": [round(float(np.mean([shape(v)[k] for v in by_root["list"]])), 3) for k in K] if by_root.get("list") else None},
           "entrants_total": len(entrants), "entrant_survival_past_20": {str(b): s for b, s in sorted(surv.items())},
           "kept_edits": sum(len(v) for v in kept.values()), "edit_rows": len(E)}
    if out["list_descendants"]["mean_pte"]:
        out["list_descendants"]["change"] = [round(out["list_descendants"]["mean_pte"][j] - lists_mean[k], 3) for j, k in enumerate(K)]
    f = ROOT / f"runs/probe/C203-lists-in-selection/b3_read_{at}.json"
    f.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    if not out["learner_unchanged"]:
        print("KILL: a learner changed")
        sys.exit(9)


if __name__ == "__main__":
    main()
