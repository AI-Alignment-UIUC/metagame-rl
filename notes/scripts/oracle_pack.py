"""C94 (runs/probe/C94-oracle/record.md): packs the oracle set for the value-head testbed. Evaluation targets only:
nothing may train on this file (row 60).

Loads probe_target_signal's raw probes (<out>.probes.json.gz), reruns the pilot offline on each stored prompt row
(probe_target_signal.offline: the probabilities, the input of model.score at every answer, V0), and saves one torch file
of per-probe records: the state (obs), legal ids, answers, Trainer, stratum, per-rollout returns R[a, j] (nan where a
rollout is not valid; the two halves are j's parity), Q and the half means Qh, the option embeddings, V0 and the pilot's
probabilities over the answers, and each rollout's later values of the seat (vals). Also prints the oracle's split-half R (Spearman-Brown) on the named five and on all.

  PYTHONPATH=. .venv/Scripts/python notes/scripts/oracle_pack.py --raw runs/probe/C94-oracle/oracle.json.probes.json.gz \
      --out runs/probe/C94-oracle/oracle.pt
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
from probe_target_signal import NAMED, offline, pearson, prepare, zpool  # noqa: E402
from rl.gpu_matrix import load_policy                    # noqa: E402


def split_half(recs) -> dict:
    """The tool's R (probe_target_signal's readout): Spearman-Brown split-half correlation of Q across answers, over probes
    with 3 or more answers and no missing Q, pooled by Fisher z."""
    rsb = []
    for r in recs:
        if len(r["answers"]) >= 3 and not np.isnan(r["Q"]).any():
            c = pearson(r["Qh"][0], r["Qh"][1])
            rsb.append(None if c is None else 2 * c / (1 + c) if c > -0.99 else -0.999)
    return zpool(rsb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--pilot", default="ar/data/start.pt")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _ = load_policy(a.pilot, device)
    probes = json.loads(gzip.open(a.raw, "rt").read())["probes"]
    offline(model, probes, device)
    recs = []
    for p in probes:
        q = prepare(p)
        R = np.array([[np.nan if x is None else x for x in row] for row in p["rew"]], float)
        recs.append({"game": p["game"], "turn": p["turn"], "seat": p["seat"], "trainer": p.get("trainer"),
                     "stratum": p.get("stratum"), "prompt": p.get("prompt"), "type": p.get("type"), "obs": p["obs"],
                     "legal": p["legal"], "keys": p.get("keys"), "answers": p["answers"], "taken": q["taken"], "greedy": q["greedy"],
                     "R": R, "Q": q["Q"], "Qh": q["Qh"], "emb": q["emb"], "V0": p.get("V0off", p["V0"]), "pi": q["pi"],
                     "vals": p["vals"]})                  # per answer and rollout: the seat's later values (C95's bootstrap targets)
    named = [r for r in recs if r["trainer"] and any(r["trainer"].startswith(n) for n in NAMED)]
    rel = {"named5": split_half(named), "all": split_half(recs), "probes": len(recs), "named5_probes": len(named),
           "m": int(probes[0]["m"]) if probes else None}
    torch.save({"records": recs, "reliability": rel, "pilot": a.pilot, "raw": a.raw,
                "note": "evaluation targets only; nothing trains on this file (row 60)"}, ROOT / a.out)
    print(json.dumps(rel))


if __name__ == "__main__":
    main()
