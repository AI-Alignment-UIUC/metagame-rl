"""Deck search for PSRO (plan item A5.2), with the three ways of scoring a candidate from log #27,
compared in log #34:

  games  real games against the Nash support decks, weighted by the mixture: the ground truth,
         and the most expensive, so it sees the fewest candidates
  model  an ensemble of matchup models (rl/matchup.py), each refit on resampled results; ranked
         by mean + beta x spread against the mixture, so decks the models disagree on get tried
  value  the pilot's start-of-game value against the support decks (forward passes, no games)

Every scorer runs the same search under the same wall-clock budget: restarts from a random deck
or a support deck (kicked MIN_CHANGED random swaps away, so it can become a new deck), each with an
edit budget drawn from 12-60 (how many cards it may change from its start), then
hill climbing by single-card swaps; all candidates of a step, and the current deck, are scored
together (for games, on the same deals). Proposals are the best final decks at least
MIN_CHANGED cards from each other and from the population. Whatever the scorer, only real games
enter the matrix.
"""
import time

import numpy as np
import torch

from rl.decks import DECK_SIZE, Pool, overlap
from rl.matchup import MatchupModel, fit

MIN_CHANGED = 10          # cards a new deck must differ by from every other deck


def changed(a: np.ndarray, b: np.ndarray) -> int:
    return DECK_SIZE - int(np.minimum(a, b).sum())


def random_swap(pool: Pool, v: np.ndarray, rng) -> np.ndarray:
    """One copy out, one in, legal: half the time the card added is one the deck already plays."""
    rem = np.nonzero(pool.removable(v))[0]
    w = v.copy()
    w[rng.choice(rem)] -= 1
    add = pool.addable(w)
    own = np.nonzero(add & (v > 0))[0]
    choices = own if len(own) and rng.random() < 0.5 else np.nonzero(add)[0]
    w[rng.choice(choices)] += 1
    return w


class GamesScorer:
    """Win rate against the support decks over `games` real games each, weighted by sigma."""
    name, candidates = "games", 6

    def __init__(self, gm, games: int = 24, max_support: int = 6):
        self.gm, self.games, self.max_support = gm, games, max_support
        self.calls = 0

    def prepare(self, pop, sigma, seed):
        top = np.argsort(-sigma)[:self.max_support]
        self.opp = [i for i in top if sigma[i] > 1e-3]
        w = sigma[self.opp]
        self.w = w / w.sum()
        self.opp_decks = [{"name": f"s{i}", "cards": pop.pool.names(pop.decks[i])} for i in self.opp]
        self.seed = seed % 100003          # game seeds stay below 2^53 (exact in JavaScript)

    def __call__(self, cands):
        n = len(self.opp_decks)
        decks = self.opp_decks + [{"name": f"c{k}", "cards": self.pool.names(c)} for k, c in enumerate(cands)]
        pairs = [(n + k, j) for k in range(len(cands)) for j in range(n)]
        self.calls += 1
        W, G, _ = self.gm.play(decks, self.games, self.seed * 1000 + self.calls, pairs=pairs)   # same deals for every candidate
        return np.array([sum(self.w[j] * W[n + k, j] / G[n + k, j] for j in range(n)) for k in range(len(cands))])


class ModelScorer:
    """Ensemble of matchup models refit each iteration on bootstrap-resampled results."""
    name, candidates = "model", 64

    def __init__(self, table, text, device, members: int = 5, beta: float = 1.0):
        self.table, self.text, self.device, self.members, self.beta = table, text, device, members, beta

    def prepare(self, pop, sigma, seed):
        rng = np.random.default_rng(seed)
        D = np.stack(pop.decks).astype(np.float32)
        P = pop.wins / np.maximum(pop.games, 1)
        self.models, self.fits = [], []
        for k in range(self.members):
            W = rng.binomial(pop.games.astype(np.int64), P).astype(np.float64)   # resampled games, same counts
            W = np.triu(W, 1) + np.tril(pop.games - np.triu(W, 1).T, -1)       # keep W[j, i] = G - W[i, j]
            m = MatchupModel(self.table, self.text)
            self.fits.append(fit(m, D, W, pop.games, self.device, seed=seed * 31 + k))
            self.models.append(m)
        self.opp = torch.from_numpy(D).to(self.device)
        self.sigma = torch.from_numpy(sigma.astype(np.float32)).to(self.device)

    @torch.no_grad()
    def __call__(self, cands):
        C = torch.from_numpy(np.stack(cands).astype(np.float32)).to(self.device)
        n, D = len(C), len(self.opp)
        a = C.repeat_interleave(D, 0)
        b = self.opp.repeat(n, 1)
        per = torch.stack([(m(a, b).view(n, D) * self.sigma).sum(1) for m in self.models])
        return (per.mean(0) + self.beta * per.std(0)).cpu().numpy()

    @torch.no_grad()
    def mean(self, cands):
        """The ensemble's mean prediction, without the optimism bonus (for calibration)."""
        beta, self.beta = self.beta, 0.0
        try:
            return self(cands)
        finally:
            self.beta = beta


class ValueScorer:
    """The pilot's start-of-game value v(c, j) in [-1, 1] against the support decks, weighted by
    sigma, mapped to [0, 1] so it reads like a win rate."""
    name, candidates = "value", 12

    def __init__(self, gm, openings: int = 8, max_support: int = 6, novelty: float = 0.0, edit=None,
                 head_share: float = 0.5, head_tau: float = 0.5, train_every: int = 20, common_deals: bool = False):
        """novelty > 0 adds novelty x the deck's novelty in the pilot's own embedding (rl/deck_head.py:
        mean distance to the 5 nearest population decks, 1 = the population's typical spacing).
        edit: an rl.deck_head.EditLearner, trained on every climb step's scored swaps and proposing
        head_share of the swaps from the second step of a climb on."""
        self.gm, self.openings, self.max_support = gm, openings, max_support
        self.novelty, self.edit = novelty, edit
        self.head_share, self.head_tau, self.train_every = head_share, head_tau, train_every
        self.cache, self.observed, self.head_loss = {}, 0, []
        self.common_deals = common_deals       # the same deals for every candidate (GpuMatrix.values)

    def prepare(self, pop, sigma, seed):
        GamesScorer.prepare(self, pop, sigma, seed)
        self.cache = {}
        self.nov = None
        if self.novelty > 0:
            from rl.deck_head import Novelty, deck_embeddings
            n = len(self.opp_decks)
            decks = self.opp_decks + [{"name": f"p{k}", "cards": pop.pool.names(v)} for k, v in enumerate(pop.decks)]
            pairs = [(n + k, j) for k in range(len(pop.decks)) for j in range(n)]
            _, st = self.gm.values(decks, pairs, self.openings, self.seed if self.common_deals else self.seed + 1,
                                   states=True, common_deals=self.common_deals)
            self.nov = Novelty(deck_embeddings(st, len(pop.decks), n, self.openings, self.w))
        if self.edit is not None:
            self.edit.pilot = self.gm.model           # the pilot may have been fine-tuned since
            if self.edit.buf:
                self.head_loss.append(self.edit.train(60))

    def _deck_states(self, st, k, n):
        """Deck k's live states of the last call and their weights (w over opponents, even over deals)."""
        o = self.openings
        rows = np.arange(k * n * o, (k + 1) * n * o)
        live = st["live"][rows].astype(bool)
        per_opp = st["live"][rows].reshape(n, o).sum(1)
        w = np.repeat(self.w / np.maximum(per_opp, 1), o)[live]
        return {key: st[key][rows[live]] for key in ("tok_card", "tok_kind", "tok_aux", "glob", "slots")}, w / w.sum()

    def __call__(self, cands):
        n = len(self.opp_decks)
        decks = self.opp_decks + [{"name": f"c{k}", "cards": self.pool.names(c)} for k, c in enumerate(cands)]
        pairs = [(n + k, j) for k in range(len(cands)) for j in range(n)]
        if self.nov is None and self.edit is None:
            v = self.gm.values(decks, pairs, self.openings, self.seed,
                               common_deals=self.common_deals).reshape(len(cands), n)
            return 0.5 + 0.5 * (v * self.w[None, :]).sum(1)
        v, st = self.gm.values(decks, pairs, self.openings, self.seed, states=True, common_deals=self.common_deals)
        self.base = 0.5 + 0.5 * (v.reshape(len(cands), n) * self.w[None, :]).sum(1)
        if self.edit is not None:
            self.cache = {c.tobytes(): self._deck_states(st, k, n) for k, c in enumerate(cands)}
        if self.nov is None:
            return self.base
        from rl.deck_head import deck_embeddings
        self.last_novelty = self.nov(deck_embeddings(st, len(cands), n, self.openings, self.w))
        return self.base + self.novelty * self.last_novelty

    def head_swaps(self, cur, m, rng):
        """m swaps proposed by the edit head for the current deck, or None before the head has
        data or when the deck's states are not in the last call."""
        if self.edit is None or not self.edit.buf or cur.tobytes() not in self.cache:
            return None
        states, w = self.cache[cur.tobytes()]
        a, r = self.edit.scores(states, w)
        a, r = a.cpu().numpy(), r.cpu().numpy()
        return [self.edit.propose(self.pool, cur, a, r, rng, self.head_tau) for _ in range(m)]

    def observe(self, cur, cands):
        """After a climb step: the current deck's states and the base score change of each swap."""
        if self.edit is None or cur.tobytes() not in self.cache:
            return
        states, w = self.cache[cur.tobytes()]
        real = [q for q, c in enumerate(cands) if not (c == cur).all()]    # a swap can put back what it took out
        if len(real) < 2:
            return
        swaps = np.array([[int(np.argmax(cands[q] - cur)), int(np.argmax(cur - cands[q]))] for q in real])
        self.edit.add(states, w, swaps, self.base[1:][real] - self.base[0])
        self.observed += 1
        if self.observed % self.train_every == 0:
            self.head_loss.append(self.edit.train(5))


class StrengthScorer:
    """The deck-strength model of rl/strength.py (logs #38-39) on each candidate: `games` real games
    against the top support decks (game statistics and the value at turn 5), its start-of-game value
    against them, its decklist (shape, goldfish) and its distance to the population. No opponent
    context in the model: the support decks are only who the games are played against."""
    name, candidates = "strength", 6
    max_steps = 20          # ~2 s a step, so shorter climbs and more restarts in the budget

    def __init__(self, gm, model_path: str, games: int = 16, max_support: int = 4, openings: int = 4):
        from rl.strength import StrengthModel
        self.gm, self.games, self.max_support, self.openings = gm, games, max_support, openings
        self.model = StrengthModel.load(model_path)
        self.calls = 0

    def prepare(self, pop, sigma, seed):
        GamesScorer.prepare(self, pop, sigma, seed)
        self.known = list(pop.decks)
        self.rng = np.random.default_rng(seed)

    def __call__(self, cands):
        from rl.strength import deck_features, distance_to_nearest, game_features
        n = len(self.opp_decks)
        per = max(2, 2 * round(self.games / n / 2))           # even, so both seats
        decks = self.opp_decks + [{"name": f"c{k}", "cards": self.pool.names(c)} for k, c in enumerate(cands)]
        pairs = [(n + k, j) for k in range(len(cands)) for j in range(n)]
        self.calls += 1
        self.gm.play(decks, per, self.seed * 1000 + self.calls, pairs=pairs, value_at_turn=5)
        games = self.gm.results
        fw = self.gm.values(decks, pairs, self.openings, self.seed + self.calls)
        bw = self.gm.values(decks, [(b, a) for a, b in pairs], self.openings, self.seed + self.calls + 7)
        vstart = ((fw - bw) / 2).reshape(len(cands), n) @ self.w
        feats = [{**deck_features(self.pool, c, self.rng, sims=100), **game_features(games, n + k),
                  "value_start": float(vstart[k]), "distance_to_nearest": distance_to_nearest(c, self.known)}
                 for k, c in enumerate(cands)]
        return 1 / (1 + np.exp(-self.model.logit(feats)))


def softmax_order(scores, tau: float, rng) -> list:
    """Indices in the order they are drawn without replacement from softmax(scores / tau); with
    tau = 0, best first (deterministic)."""
    scores = np.asarray(scores, dtype=np.float64)
    if tau <= 0:
        return list(np.argsort(-scores, kind="stable"))
    left, out = list(range(len(scores))), []
    while left:
        z = scores[left] / tau
        p = np.exp(z - z.max())
        k = int(rng.choice(len(left), p=p / p.sum()))
        out.append(left.pop(k))
    return out


def search(scorer, pop, sigma, k: int, seconds: float, rng, random_deck, restart_random: float = 0.5,
           patience: int = 2, max_steps: int = 60, confirm: GamesScorer = None, finalists: int = 8,
           confirm_share: float = 0.1, temperature: float = 0.0):
    """Restarts + hill climbing within `seconds`; returns up to k (deck, score, scorer's score)
    proposals and a log of the searches. With `confirm` (a GamesScorer), the search stops at
    (1 - confirm_share) of the budget, the `finalists` best distinct decks play real games against
    the support, and the k best by those games are proposed (A5.2 step 3).

    temperature > 0 samples instead of taking the best (log #40): each climb step moves to a deck
    drawn from softmax(score / T) over the current deck and its candidates (so it can step down; the
    climb returns the best deck it visited), and finalists and proposals are drawn the same way
    without replacement. 0 is the greedy search of result #1."""
    pool = pop.pool
    scorer.pool = pool
    max_steps = getattr(scorer, "max_steps", max_steps)
    t0 = time.time()
    t_search = seconds * (1 - confirm_share) if confirm is not None else seconds
    scorer.prepare(pop, sigma, int(rng.integers(1 << 30)))
    t_prep = time.time() - t0
    support = [i for i in np.argsort(-sigma) if sigma[i] > 1e-3]
    finals, runs = [], []
    by_src, best_src = ([], []), [0, 0]      # score changes of random (0) and head (1) swaps
    while time.time() - t0 < t_search:
        if rng.random() < restart_random or not support:
            start, origin = random_deck(pool, rng), "random"
        else:
            i = int(rng.choice(support, p=sigma[support] / sigma[support].sum()))
            start, origin = pop.decks[i].copy(), f"support {pop.names[i]}"
        budget = int(rng.integers(MIN_CHANGED + 2, 61))
        cur, cur_score, stall, steps, scored = start, None, 0, 0, 0
        best_deck, best_score = None, -np.inf
        if origin != "random":                 # kick a support deck MIN_CHANGED swaps away first
            while changed(cur, start) < MIN_CHANGED:
                cur = random_swap(pool, cur, rng)
        while steps < max_steps and stall < patience and time.time() - t0 < t_search:
            cands, src = [], []
            m_head = int(round(scorer.candidates * getattr(scorer, "head_share", 0.0)))
            head = scorer.head_swaps(cur, m_head * 4, rng) if m_head and hasattr(scorer, "head_swaps") else None
            for c in head or []:
                if changed(c, start) <= budget and pool.legal(c) and not (c == cur).all():
                    cands.append(c)
                    src.append(1)
                if len(cands) == m_head:
                    break
            for _ in range(scorer.candidates * 4):
                if len(cands) >= scorer.candidates:
                    break
                c = random_swap(pool, cur, rng)
                if changed(c, start) <= budget and pool.legal(c):
                    cands.append(c)
                    src.append(0)
            if not cands:
                break
            s = scorer([cur] + cands)          # the current deck rescored with the candidates
            scored += len(cands)
            if getattr(scorer, "edit", None) is not None:
                scorer.observe(cur, cands)
                base = scorer.base
                for q, sk in enumerate(src):
                    by_src[sk].append(float(base[1 + q] - base[0]))
                if head is not None:
                    best_src[src[int(np.argmax(base[1:]))]] += 1
            cur_score = float(s[0])
            if cur_score > best_score:
                best_deck, best_score = cur, cur_score
            if temperature > 0:
                pick = softmax_order(s, temperature, rng)[0]
                if pick == 0:
                    stall += 1
                else:
                    cur, cur_score, stall = cands[pick - 1], float(s[pick]), 0
            else:
                best = int(np.argmax(s[1:]))
                if s[1 + best] > s[0]:
                    cur, cur_score, stall = cands[best], float(s[1 + best]), 0
                else:
                    stall += 1
            if cur_score > best_score:
                best_deck, best_score = cur, cur_score
            steps += 1
        if cur_score is not None:
            cur, cur_score = best_deck, best_score
            finals.append((cur, cur_score))
            runs.append({"origin": origin, "budget": budget, "steps": steps, "scored": scored,
                         "changed": changed(cur, start), "score": round(cur_score, 4)})
    def distinct(items, n):
        out = []
        for i in softmax_order([sc for _, sc in items], temperature, rng):
            v, sc = items[i]
            if all(changed(v, u) >= MIN_CHANGED for u in list(pop.decks) + [c[0] for c in out]):
                out.append((v, sc))
            if len(out) == n:
                break
        return out

    t_confirm = 0.0
    if confirm is None:
        chosen = [(v, sc, sc) for v, sc in distinct(finals, k)]
    else:
        t1 = time.time()
        top = distinct(finals, finalists)
        chosen = []
        if top:
            confirm.pool = pool
            confirm.prepare(pop, sigma, int(rng.integers(1 << 30)))
            real = confirm([v for v, _ in top])
            order = softmax_order(real, temperature, rng)[:k]
            chosen = [(top[i][0], float(real[i]), top[i][1]) for i in order]
        t_confirm = time.time() - t1
    info = {"scorer": scorer.name, "seconds": round(time.time() - t0, 1), "prepare_s": round(t_prep, 1),
            "confirm_s": round(t_confirm, 1),
            "searches": len(runs), "candidates_scored": sum(r["scored"] for r in runs),
            "from_random": sum(r["origin"] == "random" for r in runs), "runs": runs}
    if getattr(scorer, "fits", None):
        info["model_fit"] = scorer.fits
    if any(by_src):
        info["swaps"] = {name: {"n": len(d), "mean_delta": round(float(np.mean(d)), 5) if d else None,
                                "improve": round(float(np.mean(np.array(d) > 0)), 4) if d else None}
                         for name, d in zip(("random", "head"), by_src)}
        info["best_from"] = {"random": best_src[0], "head": best_src[1]}
        info["head_loss"] = [round(x, 4) for x in getattr(scorer, "head_loss", []) if x is not None][-5:]
    if getattr(scorer, "nov", None) is not None:
        info["novelty_scale"] = round(scorer.nov.scale, 4)
    return chosen, info
