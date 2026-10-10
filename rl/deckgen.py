"""Deck generators that cover the whole deck space, steered toward cards the system has seen least
(log #52, co-evolution).

Two shapes, drawn half and half by `explore_deck`:
  lines  Pokémon lines (a Basic and maybe what evolves from it, 1-4 lines), basic Energy of their
         types (8-34), limited cards (Trainers and Special Energy) for the rest. The shape of
         notes/scripts/pilot_decks.py, widened to the full pool and to Special Energy. Pokémon-specific:
         it knows what evolves from what and which Energy a Pokémon's type needs.
  flat   only the format's rules: a Dirichlet split of 60 into Pokémon / limited cards / basic Energy,
         at least one Basic, cards drawn independently (an evolution may come without its Basic). The
         game-agnostic shape: anything coherent has to be found by the search, not built in.

Every draw of a non-Energy card is weighted by `Coverage.weights()`, (1 + games the card has been in)
^ -power, so cards the pilot has rarely played with come up more often (count-based exploration over
cards; no card is treated specially).
"""
import numpy as np

from rl.decks import DECK_SIZE, MAX_COPIES, Pool


class Coverage:
    """How many training games each card has been in (any number of copies, either seat)."""

    def __init__(self, pool: Pool):
        self.pool = pool
        self.exposure = np.zeros(pool.n)

    def add_games(self, cards_per_game: list):
        """cards_per_game: one list of full card names per deck per game."""
        for names in cards_per_game:
            ids = {self.pool.id[f] for f in names if f in self.pool.id}
            self.exposure[list(ids)] += 1

    def weights(self, power: float = 0.5) -> np.ndarray:
        w = (1.0 + self.exposure) ** -power
        w[~self.pool.allowed] = 0.0
        w[0] = 0.0
        return w

    def summary(self, population: list, support: list, min_games: int = 200) -> dict:
        """Share of the allowed, non-basic-Energy cards in a population deck, in a support deck, and
        in at least `min_games` training games; normalized entropy of the exposure over them."""
        p = self.pool
        cards = p.allowed.copy()
        cards[0] = False
        cards &= ~p.basic_energy
        n = int(cards.sum())
        in_pop = (np.sum(population, 0) > 0) if population else np.zeros(p.n, bool)
        in_sup = (np.sum(support, 0) > 0) if support else np.zeros(p.n, bool)
        e = self.exposure[cards]
        q = e / e.sum() if e.sum() > 0 else np.full(n, 1 / n)
        ent = float(-(q[q > 0] * np.log(q[q > 0])).sum() / np.log(n))
        return {"cards": n, "in_population": round(float((in_pop & cards).sum()) / n, 4),
                "in_support": round(float((in_sup & cards).sum()) / n, 4),
                f"seen_{min_games}": round(float((self.exposure[cards] >= min_games).sum()) / n, 4),
                "exposure_entropy": round(ent, 4), "least_seen": int(e.min()), "median_seen": int(np.median(e))}


def _room(pool: Pool, v: np.ndarray, cid: int) -> int:
    """Copies of card cid that can still go in (basic Energy unlimited)."""
    if pool.basic_energy[cid]:
        return DECK_SIZE
    nb = np.where(pool.basic_energy, 0, v)
    return MAX_COPIES - int(pool.name_counts(nb)[pool.name_of[cid]])


def _pick(rng, ids: list, w: np.ndarray):
    p = w[ids]
    if p.sum() <= 0:
        return ids[rng.integers(len(ids))]
    return ids[rng.choice(len(ids), p=p / p.sum())]


class DeckGen:
    def __init__(self, pool: Pool):
        self.pool = pool
        allowed = [c for c in pool.cards if pool.allowed[c["id"]]]
        self.basics = [c["id"] for c in allowed if c["superType"] == 1 and c["stage"] == 2]
        self.pokemon = [c["id"] for c in allowed if c["superType"] == 1]
        self.limited = [c["id"] for c in allowed if c["superType"] == 2 or (c["superType"] == 3 and c["energyType"] != 0)]
        self.energy = [c["id"] for c in allowed if c["superType"] == 3 and c["energyType"] == 0]
        self.card = {c["id"]: c for c in pool.cards}
        self.evolves = {}
        for c in allowed:
            if c["superType"] == 1 and c.get("evolvesFrom"):
                self.evolves.setdefault(c["evolvesFrom"], []).append(c["id"])

    def _fill(self, v, ids, w, n, rng, copies=(1, 5)):
        """Adds up to n cards drawn from ids by weight, a random number of copies each."""
        tries = 0
        while n > 0 and tries < 2000:
            tries += 1
            cid = _pick(rng, ids, w)
            k = min(int(rng.integers(*copies)), _room(self.pool, v, cid), n)
            if k > 0:
                v[cid] += k
                n -= k
        return n

    def lines(self, rng, w) -> np.ndarray:
        p = self.pool
        v = np.zeros(p.n, dtype=np.int32)
        types = set()
        basics = list(self.basics)
        for _ in range(int(rng.integers(1, 5))):
            b = _pick(rng, basics, w)
            basics.remove(b)
            v[b] += int(rng.integers(1, 5))
            types |= {i for i, x in enumerate(self.card[b]["types"]) if x}
            name = self.card[b]["name"]
            while name in self.evolves and rng.random() < 0.6:
                e = _pick(rng, self.evolves[name], w)
                v[e] += min(int(rng.integers(1, 4)), _room(p, v, e))
                name = self.card[e]["name"]
        typed = [e for e in self.energy if any(self.card[e]["provides"][t] for t in types)] or self.energy
        for _ in range(int(rng.integers(8, 35))):
            pick = typed if rng.random() < 0.75 else self.energy
            v[pick[rng.integers(len(pick))]] += 1
        self._fill(v, self.limited, w, DECK_SIZE - int(v.sum()), rng)
        return v

    def flat(self, rng, w) -> np.ndarray:
        p = self.pool
        v = np.zeros(p.n, dtype=np.int32)
        share = rng.dirichlet([1.0, 1.0, 1.0])
        n_poke = max(1, int(round(share[0] * DECK_SIZE)))
        n_lim = int(round(share[1] * DECK_SIZE))
        v[_pick(rng, self.basics, w)] += 1                      # the format's one rule about Pokémon
        self._fill(v, self.pokemon, w, n_poke - 1, rng)
        self._fill(v, self.limited, w, min(n_lim, DECK_SIZE - int(v.sum())), rng)
        kinds = rng.choice(self.energy, size=int(rng.integers(1, 4)), replace=False)
        for _ in range(DECK_SIZE - int(v.sum())):
            v[kinds[rng.integers(len(kinds))]] += 1
        return v

    def __call__(self, rng, w=None, p_flat: float = 0.5) -> np.ndarray:
        w = np.ones(self.pool.n) if w is None else w
        while True:
            v = self.flat(rng, w) if rng.random() < p_flat else self.lines(rng, w)
            if v.sum() > DECK_SIZE:                                # an evolution overshot: trim at random
                while v.sum() > DECK_SIZE:
                    i = rng.choice(np.nonzero(self.pool.removable(v))[0])
                    v[i] -= 1
            if v.sum() < DECK_SIZE:
                v[self.energy[rng.integers(len(self.energy))]] += DECK_SIZE - int(v.sum())
            if self.pool.legal(v):
                return v
