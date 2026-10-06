"""Training decks for a pilot that never sees a human list (log #42).

Random legal decks with no human deck shape: 1-4 Pokémon lines (Basics 1-4 copies, an evolution
60% of the time, 1-3 copies), an Energy count drawn uniformly from 8-34 (each Energy of one of the
deck's Pokémon types 75% of the time, any basic type otherwise), and Trainers uniformly at random
for the rest. Matchups are random pairs of these decks (mirrors included) for rl/train.py
--matchups-file. The card pool is still the field's 56 cards (--pool field), a prior removed later.

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/pilot_decks.py --out runs/pilot-scratch/matchups.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

from rl.decks import MAX_COPIES, Pool, archived_decks


def wide_random_deck(pool: Pool, rng) -> np.ndarray:
    cards = [c for c in pool.cards if pool.allowed[c["id"]]]
    by_name = {}
    for c in cards:
        by_name.setdefault(c["name"], c)
    basics = [c for c in by_name.values() if c["superType"] == 1 and c["stage"] == 2]
    evolutions = [c for c in by_name.values() if c["superType"] == 1 and c["stage"] in (3, 4)]
    trainers = [c for c in by_name.values() if c["superType"] == 2]
    energies = [c for c in cards if c["superType"] == 3 and c["energyType"] == 0]
    while True:
        v = np.zeros(pool.n, dtype=np.int32)
        types = set()
        for b in rng.choice(basics, size=rng.integers(1, 5), replace=False):
            v[b["id"]] += rng.integers(1, 5)
            types |= {i for i, x in enumerate(b["types"]) if x}
            evo = [e for e in evolutions if e["evolvesFrom"] == b["name"]]
            if evo and rng.random() < 0.6:
                v[evo[rng.integers(len(evo))]["id"]] += rng.integers(1, 4)
        typed = [e for e in energies if any(e["provides"][t] for t in types)] or energies
        for _ in range(int(rng.integers(8, 35))):
            pick = typed if rng.random() < 0.75 else energies
            v[pick[rng.integers(len(pick))]["id"]] += 1
        tries = 0
        while v.sum() < 60 and tries < 1000:
            tries += 1
            t = trainers[rng.integers(len(trainers))]
            if pool.name_counts(np.where(pool.basic_energy, 0, v))[pool.name_of[t["id"]]] < MAX_COPIES:
                v[t["id"]] += 1
        if v.sum() == 60 and pool.legal(v):
            return v


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--decks", type=int, default=512)
    ap.add_argument("--matchups", type=int, default=2048)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    rng = np.random.default_rng(args.seed)
    full = Pool()
    field = sorted({c for _, v in archived_decks(full) for c in full.names(v)})
    pool = Pool(restrict=field)
    decks = [{"name": f"rand-{k}", "cards": pool.names(wide_random_deck(pool, rng))} for k in range(args.decks)]
    matchups = [[decks[a], decks[b]] for a, b in rng.integers(len(decks), size=(args.matchups, 2)).tolist()]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(matchups, open(args.out, "w"))
    e = [sum(pool.cards[pool.id[c] - 1]["superType"] == 3 for c in d["cards"]) for d in decks]
    print(f"{len(decks)} decks, {len(matchups)} matchups; Energy per deck min {min(e)} median {int(np.median(e))} max {max(e)}")


if __name__ == "__main__":
    main()
