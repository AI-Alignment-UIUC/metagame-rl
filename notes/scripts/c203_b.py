"""C203 (b) (runs/probe/C203-lists-in-selection/record.md): the 24 lists as a population under W s48's frozen nets at 44.
--hash FILE: sha256 of the pilot net and of the draft head in a snapshot (keys sorted, each tensor's bytes).
--read RUN: the run's last snapshot against the fork source: the nets' hashes (a difference is a learner update, the record's
    kill), the population's mean P/T/E against the 24 lists' (13.88/27.5/18.62 from archived_decks), its mean change, and the
    top 12 by recent_score (P/T/E, names), for G3 against the original 24 (probe_meta_premise.py on the same snapshot).
    PYTHONPATH=. .venv/Scripts/python notes/scripts/c203_b.py --read runs/screens/C203-lists-b-s48
    ... --read runs/screens/C203-lists-b-s49 --source runs/screens/C171-W-s49/population_it0044.pt --name b_read_s49 (the replication)
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.decks import Pool, archived_decks              # noqa: E402
from rl.metagame import recent_score                    # noqa: E402

SRC = ROOT / "runs/screens/C171-W-s48/population_it0044.pt"
P = Pool()
ST = np.array([0] + [0] * P.n)


def sha(sd):
    h = hashlib.sha256()
    for k in sorted(sd):
        v = sd[k]
        h.update(k.encode())
        if torch.is_tensor(v):
            h.update(v.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()[:16]


def hashes(f):
    st = torch.load(f, map_location="cpu", weights_only=False)
    return {"net": sha(st["net"]), "head": sha(st["drafter"]["head"])}, st


def pte(vecs):
    kind = np.zeros(P.n, dtype=np.int64)
    for c in P.cards:
        kind[c["id"]] = c["superType"]
    return np.array([[int(v[kind == k].sum()) for k in (1, 2, 3)] for v in vecs])


if __name__ == "__main__":
    if "--hash" in sys.argv:
        print(json.dumps(hashes(ROOT / sys.argv[sys.argv.index("--hash") + 1])[0]))
        sys.exit(0)
    run = ROOT / sys.argv[sys.argv.index("--read") + 1]
    src = ROOT / sys.argv[sys.argv.index("--source") + 1] if "--source" in sys.argv else SRC     # the replication: W s49's snapshot
    name = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else "b_read"
    last = sorted(run.glob("population_it*.pt"))[-1]
    h0, _ = hashes(src)
    h1, st = hashes(last)
    lists = pte([v for _, v in archived_decks(P)])
    pop = st["population"]
    now = pte([P.vector(a["deck"]) if isinstance(a["deck"], list) else a["deck"] for a in pop])
    top = sorted(pop, key=lambda a: -recent_score(a, 0.0))[:12]
    tp = pte([P.vector(a["deck"]) if isinstance(a["deck"], list) else a["deck"] for a in top])
    out = {"snapshot": last.relative_to(ROOT).as_posix(), "iter": st["iter"], "hash_source": h0, "hash_last": h1,
           "learner_unchanged": h0 == h1, "lists_mean_pte": np.round(lists.mean(0), 2).tolist(),
           "pop_mean_pte": np.round(now.mean(0), 2).tolist(), "mean_change": np.round(now.mean(0) - lists.mean(0), 2).tolist(),
           "top12_mean_pte": np.round(tp.mean(0), 2).tolist(), "top12_median_pte": np.median(tp, 0).tolist(),
           "top12_z": [round(recent_score(a, 0.0), 3) for a in top], "decks": len(pop)}
    out["source"] = src.relative_to(ROOT).as_posix()
    (ROOT / f"runs/probe/C203-lists-in-selection/{name}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    if not out["learner_unchanged"]:
        print("KILL: a learner changed (the nets' hashes differ from the fork source)")
        sys.exit(9)
