"""Checks of the learner-side components (run: .venv/Scripts/python -m rl.tests).

- matchup model: P(a, b) = 1 - P(b, a) and P(a, a) = 0.5 for random weights
- edit masks (rl/builder.py) agree with the construction rules (rl/decks.py): every removal the
  mask allows, followed by any addition it allows, leaves a legal deck, and every single-card
  swap that leaves a legal deck is allowed by the masks
- random legal decks (rl/psro.py) are legal
- edit head (rl/deck_head.py): scores every card, its proposals are legal swaps, and a deck's
  novelty is about 1 for a member of the reference set (in units of its own spacing) and large far
  from it
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
    from rl.deck_head import EditHead, EditLearner, Novelty
    from rl.token_model import TokenPointerNet
    pilot = TokenPointerNet(table, text, n_names=8, glob_f=82, slot_f=20, max_tok=128, max_cand=48).eval()
    learner = EditLearner(pilot, Pool().n, "cpu")
    B, T = 3, 128
    states = {"tok_card": rng.integers(1, Pool().n, (B, T)).astype(np.int16),
              "tok_kind": np.ones((B, T), np.uint8), "tok_aux": np.ones((B, T), np.uint8),
              "glob": np.zeros((B, 82), np.uint8), "slots": np.zeros((B, 240), np.uint8)}
    a, r = learner.scores(states, np.full(B, 1 / B))
    if a.shape != (Pool().n,) or r.shape != (Pool().n,):
        failures.append(f"edit head: scores shaped {tuple(a.shape)}, {tuple(r.shape)}")
    learner.add(states, np.full(B, 1 / B), np.array([[1, 2], [3, 4], [5, 6]]), np.array([0.1, -0.1, 0.0]))
    if not np.isfinite(learner.train(2, batch=1)):
        failures.append("edit head: training loss not finite")
    a, r = learner.scores(states, np.full(B, 1 / B))
    for name, v in archived[:6]:
        for _ in range(20):
            w = learner.propose(Pool(), v, a.numpy() + rng.normal(size=a.shape), r.numpy(), rng, 0.5)
            if not Pool().legal(w) or np.abs(w - v).sum() != 2:
                failures.append(f"edit head: illegal proposal for {name}")
    Z = rng.normal(size=(10, 16))
    nov = Novelty(Z)
    near, far = float(nov(Z[:1])[0]), float(nov(Z[:1] + 100.0)[0])
    if not (near < 2.0 < 10.0 < far):
        failures.append(f"novelty: a member scores {near:.2f}, a far deck {far:.2f}")
    print(f"edit head: {Pool().n} cards scored, 120 proposals checked; novelty scale {nov.scale:.3f}")
    for f in failures[:20]:
        print("FAIL", f)
    print("FAIL" if failures else "PASS")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
