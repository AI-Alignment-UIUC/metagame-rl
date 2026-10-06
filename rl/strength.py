"""Deck-strength features and model (logs #38-39): a deck's win rate against a field, with no
opponent context, from five input groups. Training (notes/scripts/deck_strength.py) and the
search's StrengthScorer (rl/search.py) compute features with these same functions.

  shape        counts of basic / special Energy, Pokémon, Basics, Trainers, draw cards; Energy fit
  goldfish     the chance a Basic can pay its cheapest attack by turn 2 / 3 (one matching Energy
               attached per turn, Trainers ignored); Energy in the first 10 cards
  game_stats   turns and decisions per game, share of games ending by deck-out / no Pokémon
  value        the pilot's start-of-game value; its value at game turn 5, in play
  uncertainty  cards changed from the nearest known deck
"""
import json

import numpy as np

from rl.decks import DECK_SIZE

DRAW = {"Bill", "Professor Oak", "Computer Search", "Item Finder", "Energy Search", "Pokémon Trader",
        "Energy Retrieval", "Pokémon Breeder", "Gambler", "Super Energy Retrieval"}
GROUPS = {
    "shape": ["basic_energy", "special_energy", "pokemon", "basic_pokemon", "trainers", "draw", "energy_fit"],
    "goldfish": ["attack_by_t2", "attack_by_t3", "energy_in_first_10"],
    "game_stats": ["turns", "decisions", "deck_out_share", "no_pokemon_share"],
    "value": ["value_start", "value_turn5"],
    "uncertainty": ["distance_to_nearest"],
}
NAMES = [f for g in GROUPS.values() for f in g]


def deck_features(pool, v, rng, sims: int = 200) -> dict:
    """The shape and goldfish groups, from the decklist alone."""
    cards = pool.cards
    c = lambda i: cards[i - 1]
    ids = [i for i in np.nonzero(v)[0] for _ in range(int(v[i]))]
    basic_e = [i for i in ids if pool.basic_energy[i]]
    special = [i for i in ids if c(i)["superType"] == 3 and not pool.basic_energy[i]]
    poke = [i for i in ids if c(i)["superType"] == 1]
    need = np.zeros(11)
    for i in poke:
        for a in c(i)["attacks"]:
            need += np.array(a["cost"]) > 0          # index 0 is Colorless, which any Energy pays
    fit = float(np.mean([need[np.argmax(c(i)["provides"])] > 0 for i in basic_e])) if basic_e else 0.0

    def cheapest(i):
        costs = [np.array(a["cost"]) for a in c(i)["attacks"]]
        return min(costs, key=lambda x: x.sum()) if costs else None

    def can_pay(cost, energy):
        return cost is not None and not (energy[1:] < cost[1:]).any() and energy.sum() >= cost.sum()

    hits, e10 = {2: 0, 3: 0}, 0
    for _ in range(sims):
        order = rng.permutation(ids)
        e10 += sum(c(i)["superType"] == 3 for i in order[:10])
        if not any(pool.basic_pokemon[i] for i in order[:7]):
            continue
        for t in (2, 3):
            seen = order[:7 + t]
            energy = np.zeros(11)
            for i in [i for i in seen if c(i)["superType"] == 3][:t]:
                energy += np.array(c(i)["provides"]) * max(1, c(i)["provideAmount"])
            hits[t] += any(can_pay(cheapest(i), energy) for i in seen if pool.basic_pokemon[i])
    return {"basic_energy": len(basic_e), "special_energy": len(special), "pokemon": len(poke),
            "basic_pokemon": sum(pool.basic_pokemon[i] for i in ids),
            "trainers": DECK_SIZE - len(poke) - len(basic_e) - len(special),
            "draw": sum(c(i)["name"] in DRAW for i in ids), "energy_fit": fit,
            "attack_by_t2": hits[2] / sims, "attack_by_t3": hits[3] / sims, "energy_in_first_10": e10 / sims}


def game_features(games: list, deck: int) -> dict:
    """The game_stats group and the in-play value, from GpuMatrix.results games deck `deck` played
    (games run with value_at_turn=5)."""
    mine = [g for g in games if g["i"] == deck or g["j"] == deck]
    n = max(len(mine), 1)
    seat = lambda g: g["iSeat"] if g["i"] == deck else 3 - g["iSeat"]
    v5 = [((g.get("valueAt") or {}).get(str(seat(g)))) for g in mine]
    v5 = [x for x in v5 if x is not None]
    return {"turns": sum(g.get("turns") or 0 for g in mine) / n, "decisions": sum(g["steps"] for g in mine) / n,
            "deck_out_share": sum(g.get("ending") == "deck-out" for g in mine) / n,
            "no_pokemon_share": sum(g.get("ending") == "no-pokemon" for g in mine) / n,
            "value_turn5": float(np.mean(v5)) if v5 else 0.0}


def distance_to_nearest(v, known) -> float:
    return float(min((DECK_SIZE - int(np.minimum(v, u).sum()) for u in known), default=DECK_SIZE))


class StrengthModel:
    """Logistic model over standardized features: P(win against the field)."""

    def __init__(self, names, mu, sd, beta):
        self.names, self.mu, self.sd, self.beta = list(names), np.asarray(mu), np.asarray(sd), np.asarray(beta)

    def logit(self, feats: list) -> np.ndarray:
        X = np.array([[f[k] for k in self.names] for f in feats], dtype=np.float64)
        return ((X - self.mu) / self.sd) @ self.beta[1:] + self.beta[0]

    def save(self, path):
        json.dump({"names": self.names, "mu": self.mu.tolist(), "sd": self.sd.tolist(), "beta": self.beta.tolist()},
                  open(path, "w"), indent=1)

    @staticmethod
    def load(path):
        d = json.load(open(path))
        return StrengthModel(d["names"], d["mu"], d["sd"], d["beta"])
