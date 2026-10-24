"""A learned practice distribution over decks for the pilot (C46, log #163): prioritized level replay (Jiang et al.,
"Prioritized Level Replay", ICML 2021, and "Replay-Guided Adversarial Environment Design", NeurIPS 2021) with ACCEL's
small edits (Parker-Holder et al., ICML 2022), the decks playing the part of the levels.

A buffer holds decks with a score each: the pilot's positive value loss on its own decisions with that deck the last
time it was played (the mean over those decisions of max(GAE advantage, 0)): how much better the game went than the
pilot expected, a proxy for what it can still learn there. Each deck of a practice matchup is, with probability rho, a
replay draw from the buffer's scored decks, P = (1 - staleness) * P_score + staleness * P_stale, with P_score
proportional to (1 / rank) ** (1 / beta) and P_stale to the iterations since the deck was last played; otherwise it is
a new deck: a start deck not played yet, and once every start deck has been, a replay draw with 1-`edits` random
one-copy replacements (rl.draft.random_changes). Played decks get their new score;
a new deck enters the buffer in place of the lowest-scoring one when it scores above it. It reads only the rules
(legality) and the pilot's own advantages: no human list, no deck shape and nothing specific to a game.
"""
import numpy as np

from rl.decks import Pool, deck_shape
from rl.draft import random_changes


class Curriculum:
    def __init__(self, decks: list, rho: float = 0.5, beta: float = 0.3, staleness: float = 0.3, edits: int = 4,
                 seed: int = 0):
        self.pool = Pool()
        self.rng = np.random.default_rng(seed)
        self.rho, self.beta, self.staleness, self.edits = rho, beta, staleness, edits
        self.buf = [{"name": d["name"], "cards": list(d["cards"]), "score": None, "seen": -1} for d in decks]
        self.new = {}                                  # name -> deck, this iteration's new decks
        self.count = 0
        self.clock = 0

    def _vec(self, cards):
        v = np.zeros(self.pool.n, dtype=np.int32)
        for c in cards:
            v[self.pool.id[c]] += 1
        return v

    def _probs(self):
        """Replay probabilities over the scored decks (0 for decks not yet played)."""
        n = len(self.buf)
        scored = np.array([d["score"] is not None for d in self.buf])
        if not scored.any():
            return None
        sc = np.array([d["score"] if d["score"] is not None else -np.inf for d in self.buf])
        order = np.argsort(-sc, kind="stable")
        rank = np.empty(n); rank[order] = np.arange(1, n + 1)
        ps = np.where(scored, (1.0 / rank) ** (1.0 / self.beta), 0.0)
        ps /= ps.sum()
        age = np.where(scored, np.array([self.clock - d["seen"] for d in self.buf], dtype=float), 0.0)
        pc = age / age.sum() if age.sum() > 0 else scored / scored.sum()
        return (1 - self.staleness) * ps + self.staleness * pc

    def _draw(self, p, unseen):
        """A replay draw with probability rho (once some deck is scored); otherwise a new deck: a start deck not yet
        played (its first visit), and once all have been, an edit of a replay draw."""
        if p is not None and self.rng.random() < self.rho:
            d = self.buf[self.rng.choice(len(self.buf), p=p)]
            return {"name": d["name"], "cards": d["cards"]}
        if unseen:
            d = self.buf[unseen.pop(int(self.rng.integers(len(unseen))))]
            return {"name": d["name"], "cards": d["cards"]}
        d = self.buf[self.rng.choice(len(self.buf), p=p)]
        v = random_changes(self.pool, self._vec(d["cards"]), int(self.rng.integers(1, self.edits + 1)), self.rng)
        self.count += 1
        nd = {"name": f"cur-{self.count}", "cards": self.pool.names(v)}
        self.new[nd["name"]] = nd
        return nd

    def matchups(self, n: int) -> list:
        """n practice matchups [deckA, deckB] for this iteration (each worker draws from them uniformly)."""
        self.new = {}
        p = self._probs()
        unseen = [i for i, d in enumerate(self.buf) if d["score"] is None]
        return [[self._draw(p, unseen), self._draw(p, unseen)] for _ in range(n)]

    def update(self, scores: dict) -> dict:
        """scores: deck name -> its positive value loss this iteration. Returns the iteration's curriculum log row."""
        by = {d["name"]: d for d in self.buf}
        replayed = admitted = 0
        for name, s in scores.items():
            if name in by:
                by[name]["score"], by[name]["seen"] = float(s), self.clock
                replayed += 1
        for name, s in sorted(((k, v) for k, v in scores.items() if k in self.new), key=lambda x: -x[1]):
            cand = [i for i, d in enumerate(self.buf) if d["score"] is not None]   # unplayed start decks stay
            if not cand:
                break
            worst = min(cand, key=lambda i: self.buf[i]["score"])
            if s > self.buf[worst]["score"]:
                self.buf[worst] = {**self.new[name], "score": float(s), "seen": self.clock}
                admitted += 1
        self.clock += 1
        sc = np.array([d["score"] for d in self.buf if d["score"] is not None])
        sh = [deck_shape(self.pool, self._vec(d["cards"])) for d in self.buf]
        ptype = np.array([[s["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"]] for s in sh])
        return {"replayed": replayed, "new": len(self.new), "admitted": admitted,
                "scored": int(len(sc)), "score_q": np.round(np.percentile(sc, [10, 50, 90]), 4).tolist() if len(sc) else None,
                "buffer_ptype_median": np.median(ptype, 0).tolist(),
                "from_start": sum(1 for d in self.buf if not d["name"].startswith("cur-"))}

    def state(self) -> dict:
        return {"buf": self.buf, "count": self.count, "clock": self.clock, "rng": self.rng.bit_generator.state}

    def load(self, st: dict):
        self.buf, self.count, self.clock = st["buf"], st["count"], st["clock"]
        self.rng.bit_generator.state = st["rng"]
