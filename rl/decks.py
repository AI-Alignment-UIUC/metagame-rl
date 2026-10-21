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


def pokemon_overlap(pool: Pool, a: np.ndarray, b: np.ndarray) -> float:
    """Overlap of two decks' Pokémon: shared copies / the larger Pokémon count. Whole-list overlap does not tell the
    human archetypes apart (their shared staples put Haymaker against Wigglytuff at a median 0.54, Wigglytuff against
    itself at 0.57); on the Pokémon alone it is 0.35 against 0.56 (log #120)."""
    m = np.zeros(len(a), dtype=bool)
    m[[c["id"] for c in pool.cards if c["superType"] == 1]] = True
    return float(np.minimum(a[m], b[m]).sum()) / max(a[m].sum(), b[m].sum(), 1)


def changed(a: np.ndarray, b: np.ndarray) -> int:
    """Cards of a that are not in b (copies count), so 0 for the same list and 60 for disjoint ones."""
    return DECK_SIZE - int(np.minimum(a, b).sum())


def deck_shape(pool: Pool, v: np.ndarray) -> dict:
    return {"pokemon": int(v[[c["id"] for c in pool.cards if c["superType"] == 1]].sum()),
            "trainer": int(v[[c["id"] for c in pool.cards if c["superType"] == 2]].sum()),
            "basic_energy": int(v[pool.basic_energy].sum()),
            "special_energy": int(v[[c["id"] for c in pool.cards if c["superType"] == 3 and c["energyType"] != 0]].sum())}


def wide_deck(pool: Pool, rng) -> np.ndarray:
    """A random deck with a playable structure and no strategy, for the pilot's practice (log #127; log #42's generator,
    on which pilot-v2 learned, over the whole pool): 1-4 Pokémon lines (a Basic, 1-4 copies; a Stage 1 of it 60% of
    the time, 1-3 copies, and then a Stage 2 of that half the time, 1-2 copies), an Energy count drawn uniformly from
    8-34, each basic Energy of one of the lines' types 75% of the time and any basic type otherwise, and the rest
    Trainers and special Energy drawn uniformly. It reads only what the rules give (stages, what evolves from what, a
    Pokémon's type, the Energy a card provides); no human list or deck shape enters it."""
    ok = [c for c in pool.cards if pool.allowed[c["id"]]]
    basics = [c for c in ok if c["superType"] == 1 and c["stage"] == 2]
    evolves = {}
    for c in ok:
        if c["superType"] == 1 and c.get("evolvesFrom"):
            evolves.setdefault(c["evolvesFrom"], []).append(c)
    limited = [c["id"] for c in ok if c["superType"] == 2 or (c["superType"] == 3 and c["energyType"] != 0)]
    energy = [c for c in ok if c["superType"] == 3 and c["energyType"] == 0]

    def room(v, cid):
        return MAX_COPIES - int(pool.name_counts(np.where(pool.basic_energy, 0, v))[pool.name_of[cid]])

    def add(v, c, k):
        v[c["id"]] += max(0, min(k, room(v, c["id"])))

    while True:
        v = np.zeros(pool.n, dtype=np.int32)
        types = set()
        for i in rng.choice(len(basics), size=int(rng.integers(1, 5)), replace=False):
            b = basics[i]
            add(v, b, int(rng.integers(1, 5)))
            types |= {t for t, x in enumerate(b["types"]) if x}
            s1 = evolves.get(b["name"], [])
            if s1 and rng.random() < 0.6:
                e1 = s1[rng.integers(len(s1))]
                add(v, e1, int(rng.integers(1, 4)))
                s2 = evolves.get(e1["name"], [])
                if s2 and rng.random() < 0.5:
                    add(v, s2[rng.integers(len(s2))], int(rng.integers(1, 3)))
        typed = [e for e in energy if any(e["provides"][t] for t in types)] or energy
        for _ in range(int(rng.integers(8, 35))):
            pick = typed if rng.random() < 0.75 else energy
            v[pick[rng.integers(len(pick))]["id"]] += 1
        for _ in range(2000):
            if v.sum() >= DECK_SIZE:
                break
            cid = limited[rng.integers(len(limited))]
            if room(v, cid) > 0:
                v[cid] += 1
        if pool.legal(v):
            return v


def random_deck(pool: Pool, rng) -> np.ndarray:
    """A random legal deck from the format's rules alone (the 'flat' decks of log #52): a Dirichlet split
    of 60 into Pokémon / limited cards (Trainers, Special Energy) / basic Energy, one Basic Pokémon, the
    rest drawn uniformly from the allowed cards, so an evolution may come without its Basic. Nothing
    coherent is built in."""
    ok = [c for c in pool.cards if pool.allowed[c["id"]]]
    basics = [c["id"] for c in ok if c["superType"] == 1 and c["stage"] == 2]
    pokemon = [c["id"] for c in ok if c["superType"] == 1]
    limited = [c["id"] for c in ok if c["superType"] == 2 or (c["superType"] == 3 and c["energyType"] != 0)]
    energy = [c["id"] for c in ok if c["superType"] == 3 and c["energyType"] == 0]

    def room(v, cid):
        if pool.basic_energy[cid]:
            return DECK_SIZE
        return MAX_COPIES - int(pool.name_counts(np.where(pool.basic_energy, 0, v))[pool.name_of[cid]])

    def fill(v, ids, n):
        for _ in range(2000):
            if n <= 0:
                break
            cid = ids[rng.integers(len(ids))]
            k = min(int(rng.integers(1, 5)), room(v, cid), n)
            v[cid] += k
            n -= k

    while True:
        v = np.zeros(pool.n, dtype=np.int32)
        share = rng.dirichlet([1.0, 1.0, 1.0])
        v[basics[rng.integers(len(basics))]] += 1
        fill(v, pokemon, max(1, int(round(share[0] * DECK_SIZE))) - 1)
        fill(v, limited, min(int(round(share[1] * DECK_SIZE)), DECK_SIZE - int(v.sum())))
        kinds = rng.choice(energy, size=int(rng.integers(1, 4)), replace=False)
        for _ in range(DECK_SIZE - int(v.sum())):
            v[kinds[rng.integers(len(kinds))]] += 1
        if pool.legal(v):
            return v
