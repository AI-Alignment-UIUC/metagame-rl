"""Decks as card-count vectors over the card table (plan item A5), with the format's
construction rules — the same as the engine's DeckAnalyser: exactly 60 cards, at most 4 of any
card name across printings (basic Energy exempt), at least one Basic Pokémon card.

Card ids are the 1-based ids of notes/data/cards/pool.json; vectors have one entry per id plus
the unused 0. The archived decklists come from notes/data/2000-super-trainer-showdown-california.
"""
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DECK_SIZE, MAX_COPIES = 60, 4


class Pool:
    def __init__(self, table_file: str = str(ROOT / "notes/data/cards/pool.json"), restrict: list = None):
        cards = json.load(open(table_file, encoding="utf-8"))["cards"]
        self.cards = cards
        self.n = len(cards) + 1
        self.id = {c["fullName"]: c["id"] for c in cards}
        self.full_name = {c["id"]: c["fullName"] for c in cards}
        self.name = np.array([""] + [c["name"] for c in cards], dtype=object)
        self.basic_energy = np.zeros(self.n, dtype=bool)
        self.basic_pokemon = np.zeros(self.n, dtype=bool)
        for c in cards:
            self.basic_energy[c["id"]] = c["superType"] == 3 and c["energyType"] == 0
            self.basic_pokemon[c["id"]] = c["superType"] == 1 and c["stage"] == 2
        names = sorted(set(self.name[1:]))
        self.name_index = {n: i for i, n in enumerate(names)}
        self.name_of = np.array([-1] + [self.name_index[c["name"]] for c in cards])
        # Cards the builder may add (all of the pool, or a restricted list such as the 56 the field played).
        self.allowed = np.zeros(self.n, dtype=bool)
        if restrict is None:
            self.allowed[1:] = True
        else:
            for f in restrict:
                self.allowed[self.id[f]] = True

    def vector(self, full_names: list) -> np.ndarray:
        v = np.zeros(self.n, dtype=np.int32)
        for f in full_names:
            v[self.id[f]] += 1
        return v

    def names(self, v: np.ndarray) -> list:
        return [self.full_name[i] for i in np.nonzero(v)[0] for _ in range(int(v[i]))]

    def name_counts(self, v: np.ndarray) -> np.ndarray:
        out = np.zeros(len(self.name_index), dtype=np.int32)
        np.add.at(out, self.name_of[np.nonzero(v)[0]], v[np.nonzero(v)[0]])
        return out

    def legal(self, v: np.ndarray) -> bool:
        if v.sum() != DECK_SIZE or not (v[self.basic_pokemon] > 0).any():
            return False
        nb = v.copy()
        nb[self.basic_energy] = 0
        return bool((self.name_counts(nb) <= MAX_COPIES).all())

    def removable(self, v: np.ndarray) -> np.ndarray:
        """Cards whose removal keeps at least one Basic Pokémon."""
        m = v > 0
        basics = v[self.basic_pokemon].sum()
        if basics <= 1:
            m &= ~(self.basic_pokemon & (v > 0))
        return m

    def addable(self, v: np.ndarray) -> np.ndarray:
        """Cards that can be added to a 59-card deck without breaking the copy limit."""
        nb = v.copy()
        nb[self.basic_energy] = 0
        counts = self.name_counts(nb)
        ok = self.allowed.copy()
        ok[0] = False
        limited = ~self.basic_energy
        ok[limited] &= counts[self.name_of[limited].clip(0)] < MAX_COPIES
        return ok


def archived_decks(pool: Pool) -> list:
    """[(name, vector)] for the archived lists, resolved like env/decks.js does (via Node)."""
    import subprocess
    out = subprocess.run(["node", "-e", "const {archivedDecks}=require('./env/decks.js');"
                          "console.log(JSON.stringify(archivedDecks()))"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    return [(d["name"], pool.vector(d["cards"])) for d in json.loads(out.stdout)]


def overlap(a: np.ndarray, b: np.ndarray) -> float:
    """Card overlap of two decks: shared copies / 60 (1 = identical lists)."""
    return float(np.minimum(a, b).sum()) / DECK_SIZE
