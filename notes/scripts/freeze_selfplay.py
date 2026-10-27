"""C94 (runs/probe/C94-oracle/record.md): one frozen self-play dataset for the value-head testbed's offline candidates
(row 83: the pilot's own play may train a value; the oracle set never does).

The start pilot (ar/data/start.pt, C49-sd 199) plays fixed.practice_matchups() against itself with ar/train.py's
collection settings (fixed.GAME, tokens, the self opponent, no search probes) for --iters batches at fixed seeds. Saves
the concatenated rollouts (every field read_rollout gives: the token inputs, legal ids, action, logp, the pilot's value,
reward, done, traj) plus the Monte Carlo return (gamma 1) and the GAE(0.95) target, with the pilot's path and sha256.
Human-free: practice matchups and self-play only.

  PYTHONPATH=. .venv/Scripts/python notes/scripts/freeze_selfplay.py --out runs/probe/C94-oracle/selfplay.pt
"""
import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ar"))
sys.path.insert(0, str(ROOT))
import fixed                                            # noqa: E402
from rl import limits                                   # noqa: E402
from rl.remote import RemotePool                        # noqa: E402
from rl.rollouts import concat, read_rollout            # noqa: E402

TRANSITIONS, CONCURRENCY, PACE = 4096, 108, 0.25        # ar/train.py's, per worker per batch


def advantages(batch: dict, gamma: float, lam: float):
    """ar/train.py's GAE per trajectory; (adv, adv + value)."""
    value, reward, done, traj = batch["value"], batch["reward"], batch["done"], batch["traj"]
    adv = np.zeros(len(value), dtype=np.float32)
    nxt_v, nxt_a = {}, {}
    for t in range(len(value) - 1, -1, -1):
        k = traj[t]
        v1, a1 = (0.0, 0.0) if done[t] else (nxt_v.get(k, 0.0), nxt_a.get(k, 0.0))
        adv[t] = reward[t] + gamma * v1 - value[t] + gamma * lam * a1
        nxt_v[k], nxt_a[k] = value[t], adv[t]
    return adv, adv + value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=4)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    device = "cuda"
    workers = limits.cap_workers(a.workers)
    limits.apply(device, workers)
    model, _ = fixed.start_model(device)
    matchups = fixed.practice_matchups()
    tmp = ROOT / a.out
    tmp = tmp.parent / (tmp.stem + "_rollouts")
    tmp.mkdir(parents=True, exist_ok=True)
    pool = RemotePool(workers)
    pool.pace = PACE
    parts, games, errors = [], 0, 0
    try:
        for it in range(a.iters):
            msgs = [{"cmd": "collect", "encoding": "tokens", "transitions": TRANSITIONS, "concurrency": CONCURRENCY,
                     "seed": a.seed * 1_000_003 + it * 1009 + w, **fixed.GAME, "matchups": matchups,
                     "opponents": [{"spec": "self", "weight": 1.0}], "out": str(tmp / f"rollout_i{it}_w{w}.bin"),
                     "history": model.config().get("history", 0), "chain": model.config().get("chain", 0), "canon": 0}
                    for w in range(workers)]
            replies = pool.collect(msgs, {0: model.eval()}, device)
            res = [g for r in replies for g in r["results"]]
            games += len(res)
            errors += sum(1 for g in res if g.get("error"))
            parts += [read_rollout(r["out"]) for r in replies]
            print(f"batch {it}: {sum(len(r['action']) for r in parts[-workers:])} rows, {len(res)} games", flush=True)
    finally:
        pool.close()
    data = concat(parts)                                 # trajectory ids made unique per file
    data["mc_ret"] = advantages(data, 1.0, 1.0)[1]
    data["gae_ret"] = advantages(data, 1.0, 0.95)[1]
    sha = hashlib.sha256(fixed.START.read_bytes()).hexdigest()
    torch.save({"batch": data, "pilot": str(fixed.START.relative_to(ROOT)), "pilot_sha256": sha, "games": games,
                "errors": errors, "seed": a.seed, "iters": a.iters, "workers": workers,
                "note": "the pilot's own self-play (row 83); the oracle set (oracle.pt) is evaluation only"}, ROOT / a.out)
    print(f"rows {len(data['action'])}, games {games}, errors {errors}, pilot sha256 {sha[:12]}")


if __name__ == "__main__":
    main()
