"""Checks of the learner-side components (run: .venv/Scripts/python -m rl.tests).

- matchup model: P(a, b) = 1 - P(b, a) and P(a, a) = 0.5 for random weights
- edit masks (rl/builder.py) agree with the construction rules (rl/decks.py): every removal the
  mask allows, followed by any addition it allows, leaves a legal deck, and every single-card
  swap that leaves a legal deck is allowed by the masks
- random legal decks (rl/psro.py) are legal
"""
import json
import sys

import numpy as np
import torch

from rl.builder import EditMasks
from rl.decks import Pool, archived_decks
from rl.matchup import MatchupModel
from rl.psro import random_deck


def main():
    failures = []
    table = json.load(open("notes/data/cards/pool.json", encoding="utf-8"))["cards"]
    text = np.load("notes/data/cards/text_emb.npy")
    archived = archived_decks(Pool())
    field = sorted({c for _, v in archived for c in Pool().names(v)})
    rng = np.random.default_rng(0)

    m = MatchupModel(table, text).eval()
    D = torch.from_numpy(np.stack([v for _, v in archived]).astype(np.float32))
    with torch.no_grad():
        p = m(D[:-1], D[1:])
        q = m(D[1:], D[:-1])
        s = m(D, D)
    if not torch.allclose(p + q, torch.ones_like(p), atol=1e-6):
        failures.append("matchup model is not antisymmetric")
    if not torch.allclose(s, torch.full_like(s, 0.5), atol=1e-6):
        failures.append("matchup model: a deck against itself is not 0.5")

    for name, pool in (("field", Pool(restrict=field)), ("full", Pool())):
        masks = EditMasks(pool, "cpu")
        decks = [v for _, v in archived] + [random_deck(pool, rng) for _ in range(40)]
        bad = sum(not pool.legal(v) for v in decks[len(archived):])
        if bad:
            failures.append(f"{name}: {bad} random decks not legal")
        checked = 0
        for v in decks[:30]:
            V = torch.from_numpy(v[None, :].astype(np.float32))
            rem = masks.removable(V)[0].numpy()
            for r in np.nonzero(v)[0]:
                w = v.copy()
                w[r] -= 1
                add = masks.addable(torch.from_numpy(w[None, :].astype(np.float32)))[0].numpy()
                for a in range(1, pool.n):
                    x = w.copy()
                    x[a] += 1
                    legal = pool.legal(x) and pool.allowed[a]
                    allowed = bool(rem[r] and add[a])
                    if allowed and not legal:
                        failures.append(f"{name}: masks allow removing {pool.full_name[r]} and adding {pool.full_name[a]}, which is illegal")
                    if legal and not allowed and x[r] != v[r]:
                        failures.append(f"{name}: masks forbid a legal swap {pool.full_name[r]} -> {pool.full_name[a]}")
                    checked += 1
        print(f"{name} pool: {checked} single-card swaps checked")
    for f in failures[:20]:
        print("FAIL", f)
    print("FAIL" if failures else "PASS")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
