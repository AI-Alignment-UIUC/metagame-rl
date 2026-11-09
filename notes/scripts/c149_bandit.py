"""C149 stage 0 (runs/probe/C149-mirror-update/record.md): a single-state bandit, 20 actions, one rare (initial probability 0.004) and
worth +0.3 over the others (all 0). Two update rules for a softmax policy over raw logits, the same number of updates (200):
- PPO: one sampled action an update, reward with noise sd 0.2, advantage against a running-mean baseline, the clipped surrogate (clip 0.2,
  4 epochs of plain gradient ascent on the logits) plus entropy 0.01. Its strongest version is read: the best of a learning-rate grid.
- mirror: pi_new proportional to pi_old * exp(eta * A), with every action's advantage A_i = R_i - sum_j pi_j R_j plus noise sd 0.2.
Reads the rare action's probability after 200 updates, the mean over --seeds seeds (and the min / max), and the band: R-mechanism if the
mirror arm (eta 1.0, stage 1's) reaches 0.5 or more while PPO at its best rate stays under 0.05. Deterministic by seed (numpy only).
  .venv/Scripts/python notes/scripts/c149_bandit.py --out runs/probe/C149-mirror-update/stage0.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

N, RARE, P0, GAIN, NOISE, UPDATES = 20, 0, 0.004, 0.3, 0.2, 200


def start_logits():
    """Logits with the rare action at P0 and the others equal."""
    x = np.zeros(N)
    x[RARE] = np.log(P0 * (N - 1) / (1 - P0))
    return x


def softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()


def ppo(seed, lr, ent=0.01, clip=0.2, epochs=4):
    rng = np.random.default_rng(seed)
    R = np.zeros(N); R[RARE] = GAIN
    th, base = start_logits(), 0.0
    for _ in range(UPDATES):
        pold = softmax(th)
        a = int(rng.choice(N, p=pold))
        r = R[a] + rng.normal(0, NOISE)
        A = r - base
        base += 0.1 * (r - base)                      # running-mean baseline
        for _ in range(epochs):
            p = softmax(th)
            rho = p[a] / pold[a]
            g = np.zeros(N)
            if (A > 0 and rho < 1 + clip) or (A < 0 and rho > 1 - clip):   # unclipped: d(rho A)/d theta
                e = np.zeros(N); e[a] = 1.0
                g += A * rho * (e - p)
            H = -(p * np.log(p)).sum()
            g += ent * (-p * (np.log(p) + H))             # d H / d theta
            th = th + lr * g
    return float(softmax(th)[RARE])


def mirror(seed, eta):
    rng = np.random.default_rng(seed)
    R = np.zeros(N); R[RARE] = GAIN
    p = softmax(start_logits())
    for _ in range(UPDATES):
        A = R - (p * R).sum() + rng.normal(0, NOISE, N)
        p = p * np.exp(eta * A)
        p /= p.sum()
    return float(p[RARE])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    summ = lambda xs: {"mean": round(float(np.mean(xs)), 4), "min": round(float(np.min(xs)), 4), "max": round(float(np.max(xs)), 4)}
    out = {"setup": {"actions": N, "p0": P0, "gain": GAIN, "noise_sd": NOISE, "updates": UPDATES, "seeds": a.seeds},
           "ppo": {str(lr): summ([ppo(s, lr) for s in range(a.seeds)]) for lr in (0.1, 0.3, 1.0, 3.0)},
           "mirror": {str(eta): summ([mirror(s, eta) for s in range(a.seeds)]) for eta in (0.3, 1.0)}}
    best_ppo = max(v["mean"] for v in out["ppo"].values())
    out["ppo_best_mean"] = best_ppo
    out["band"] = "R-mechanism" if out["mirror"]["1.0"]["mean"] >= 0.5 and best_ppo < 0.05 else "R-not"
    out["deterministic"] = ppo(7, 1.0) == ppo(7, 1.0) and mirror(7, 1.0) == mirror(7, 1.0)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
