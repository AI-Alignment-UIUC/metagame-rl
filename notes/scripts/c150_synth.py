"""C150's acceptance (runs/screens/C150-thompson-proposals/record.md): does rl/metagame.py's thompson_fit recover a card planted at +0.05?
Synthetic paired slots as the loop makes them: 99 wide decks (rl.decks.wide_deck), each slot a random deck against its random 6-copy
change (rl.draft.random_changes), --slots slots (C127: 1,000 an iteration over a 5-iteration window), y = 0.05 x the planted card's
count change + N(0, --noise). Planted, in turn: the most often changed card, the median-changed card among those changed at all, and
the median of the cards a deck holds. Reads each planted card's posterior mean and SD (prior SD 0.02) and whether 0.05 is within 2 SDs;
also the posterior's noise SD and its largest mean among the unplanted cards.
  .venv/Scripts/python notes/scripts/c150_synth.py
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.decks import Pool, wide_deck            # noqa: E402
from rl.draft import random_changes             # noqa: E402
from rl.metagame import thompson_fit            # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--slots", type=int, default=5000)
ap.add_argument("--noise", type=float, default=0.8)
ap.add_argument("--seed", type=int, default=150)
a = ap.parse_args()
pool = Pool()
rng = np.random.default_rng(a.seed)
decks = [wide_deck(pool, rng) for _ in range(99)]
dvs = []
for _ in range(a.slots):
    v = decks[int(rng.integers(len(decks)))]
    dvs.append(random_changes(pool, v, 6, rng) - v)
freq = np.array([sum(1 for dv in dvs if dv[c] != 0) for c in range(pool.n)])
held = np.array([sum(1 for v in decks if v[c] > 0) for c in range(pool.n)])
changed = np.nonzero(freq)[0]
picks = {"most_changed": int(np.argmax(freq)),
         "median_changed": int(changed[np.argsort(freq[changed])[len(changed) // 2]]),
         "median_held": int(np.nonzero(held)[0][np.argsort(held[np.nonzero(held)[0]])[len(np.nonzero(held)[0]) // 2]])}
out = {"slots": a.slots, "noise": a.noise, "results": {}}
for label, c in picks.items():
    noise = rng.normal(0, a.noise, a.slots)
    slots = []
    for dv, e in zip(dvs, noise):
        nz = np.nonzero(dv)[0]
        slots.append((nz.tolist(), dv[nz].tolist(), float(0.05 * dv[c] + e)))
    mu, P, sigma = thompson_fit(slots, pool.n, 0.02)
    sd = float(np.linalg.inv(P)[c, c]) ** 0.5
    others = np.delete(mu, [0, c])
    out["results"][label] = {"card": pool.full_name[c], "slots_changed": int(freq[c]), "mean": round(float(mu[c]), 4), "sd": round(sd, 4),
                             "within_2sd": abs(float(mu[c]) - 0.05) <= 2 * sd, "z_vs_0": round(float(mu[c]) / sd, 2),
                             "noise_sd_fit": round(sigma, 3), "max_other_mean": round(float(np.abs(others).max()), 4)}
print(json.dumps(out, indent=1))
