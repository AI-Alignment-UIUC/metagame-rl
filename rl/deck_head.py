"""Deck building from the pilot's own representations (2026-10-07; notes/analysis-2026-10-06.md step 4).

The pilot's start-of-game state holds the whole deck (MY_UNSEEN, with counts) next to the
opponent's list (OPP_DECKLIST), and its encoder attends over both. Two uses of that encoding:

  deck embedding  z(deck) = the encoder's token 0 at the start of the game, averaged over the deals
                  and weighted over the support decks it faces (the same states the value is read at,
                  so it costs no extra forward pass). Novelty = mean distance to the k nearest
                  population decks, divided by the population's own median, so 1 is typical.
  edit head       a pointer head on the frozen encoder: every card of the pool is a candidate, twice
                  (add a copy, remove a copy), and cross-attends to the state tokens, starting from
                  the pilot's own candidate cross-attention. A swap (in, out) is predicted to change
                  the score by add[in] + remove[out]. Trained by regression on the swaps the search
                  scored (expert iteration: the search improves decks, the head learns which edits
                  it found good), then used to propose some of the search's swaps.

Nothing here names a card or uses a human list: the inputs are the pilot's states and the scores
the search computed.
"""
import copy

import numpy as np
import torch
import torch.nn as nn

TOKENS = ("tok_card", "tok_kind", "tok_aux", "glob", "slots")


def deck_embeddings(st: dict, n_decks: int, n_opp: int, openings: int, w: np.ndarray) -> np.ndarray:
    """z [n_decks, d] from values(states=True) over pairs ordered (deck, opponent): the pooled state
    averaged over the live deals of each pair, then weighted by w over the opponents."""
    P = st["pooled"].reshape(n_decks, n_opp, openings, -1)
    L = st["live"].reshape(n_decks, n_opp, openings, 1).astype(np.float32)
    per = (P * L).sum(2) / np.maximum(L.sum(2), 1)
    return (per * w[None, :, None]).sum(1)


def knn_distance(z: np.ndarray, ref: np.ndarray, k: int = 5, exclude_self: bool = False) -> np.ndarray:
    d = np.sqrt(((z[:, None, :] - ref[None, :, :]) ** 2).sum(-1))
    if exclude_self:
        d = np.sort(d, 1)[:, 1:]
    else:
        d = np.sort(d, 1)
    return d[:, :k].mean(1)


class Novelty:
    """Novelty against a reference set of embeddings, in units of the set's own median k-NN distance."""

    def __init__(self, ref: np.ndarray, k: int = 5):
        self.ref, self.k = ref, min(k, len(ref) - 1) if len(ref) > 1 else 1
        own = knn_distance(ref, ref, self.k, exclude_self=True) if len(ref) > 1 else np.ones(1)
        self.scale = float(np.median(own)) or 1.0

    def __call__(self, z: np.ndarray) -> np.ndarray:
        return knn_distance(z, self.ref, self.k) / self.scale


class EditHead(nn.Module):
    """add[c], remove[c] for every card c of the pool, from one start-of-game state."""

    def __init__(self, pilot, n_cards: int):
        super().__init__()
        d = pilot.ln_out.normalized_shape[0]
        self.n = n_cards
        self.cand_in = nn.Linear(d, d)
        self.op = nn.Embedding(2, d)                        # 0 add, 1 remove
        self.cross = copy.deepcopy(pilot.cross)             # starts from the pilot's action cross-attention
        self.score = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))
        nn.init.zeros_(self.score[-1].weight)
        nn.init.zeros_(self.score[-1].bias)
        self.register_buffer("ids", torch.arange(n_cards))

    def forward(self, cards, x, mask):
        """cards: the pilot's card embeddings [n, d] (frozen); x, mask: the encoded state [B, T, d], [B, T]
        -> add [B, n], remove [B, n]."""
        B = x.shape[0]
        c = self.cand_in(cards)[None, None] + self.op.weight[None, :, None, :]          # [1, 2, n, d]
        c = c.expand(B, 2, self.n, -1).reshape(B, 2 * self.n, -1) + x[:, :1]
        c = self.cross(c, x, mask)
        s = self.score(c).squeeze(-1).view(B, 2, self.n)
        return s[:, 0], s[:, 1]


class EditLearner:
    """The edit head, its replay buffer of scored swaps and its training, around a frozen pilot."""

    def __init__(self, pilot, n_cards: int, device: str, buffer: int = 3000, lr: float = 3e-4, seed: int = 0):
        torch.manual_seed(seed)
        self.pilot, self.device, self.n = pilot, device, n_cards
        self.head = EditHead(pilot, n_cards).to(device)
        self.opt = torch.optim.AdamW(self.head.parameters(), lr=lr, weight_decay=1e-4)
        self.buf, self.cap = [], buffer
        self.rng = np.random.default_rng(seed)
        self.steps = 0
        self.stats = []

    @torch.no_grad()
    def _cards(self):
        return self.pilot.card_emb(self.head.ids)

    def _encode(self, states):
        t = [torch.from_numpy(states[k]).to(self.device) for k in TOKENS]
        with torch.no_grad():
            return self.pilot.encode(*t)

    def scores(self, states: dict, w: np.ndarray, grad: bool = False):
        """add, remove [n] for one deck from its states [n_opp * openings] (live deals only, weights w
        per state, summing to 1)."""
        x, mask = self._encode(states)
        ctx = torch.enable_grad() if grad else torch.no_grad()
        with ctx:
            a, r = self.head(self._cards(), x, mask)
            wt = torch.from_numpy(w.astype(np.float32)).to(self.device)[:, None]
            return (a * wt).sum(0), (r * wt).sum(0)

    def add(self, states: dict, w: np.ndarray, swaps: np.ndarray, delta: np.ndarray):
        """One climb step's data: the current deck's states and state weights, the swaps tried
        [m, 2] (card in, card out) and how each changed the score."""
        self.buf.append((states, w, swaps, delta.astype(np.float32)))
        if len(self.buf) > self.cap:
            self.buf.pop(int(self.rng.integers(len(self.buf))))

    def train(self, steps: int, batch: int = 8):
        """Regression of add[in] + remove[out] on the scored change, on steps x batch buffered climb
        steps. Targets are standardized per climb step: only the ranking within a step matters for
        proposing, and it removes the drift of the score's level across iterations."""
        if not self.buf:
            return None
        self.head.train()
        losses = []
        for _ in range(steps):
            loss = 0.0
            for i in self.rng.integers(len(self.buf), size=min(batch, len(self.buf))):
                states, w, swaps, delta = self.buf[i]
                a, r = self.scores(states, w, grad=True)
                sw = torch.from_numpy(swaps).to(self.device).long()
                pred = a[sw[:, 0]] + r[sw[:, 1]]
                t = torch.from_numpy((delta - delta.mean()) / (delta.std() + 1e-6)).to(self.device)
                loss = loss + ((pred - pred.mean() - t) ** 2).mean()
            loss = loss / min(batch, len(self.buf))
            self.opt.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(self.head.parameters(), 1.0)
            self.opt.step()
            losses.append(float(loss.detach()))
            self.steps += 1
        self.head.eval()
        return float(np.mean(losses))

    def propose(self, pool, v: np.ndarray, a: np.ndarray, r: np.ndarray, rng, tau: float) -> np.ndarray:
        """One legal swap drawn from the head: out ~ softmax(z(remove) / tau) over removable cards,
        then in ~ softmax(z(add) / tau) over cards addable after it (z: standardized over the legal
        choices, so tau means the same whatever the head's scale)."""
        def draw(s, ok):
            idx = np.nonzero(ok)[0]
            z = s[idx]
            z = (z - z.mean()) / (z.std() + 1e-6) / tau
            p = np.exp(z - z.max())
            return int(idx[rng.choice(len(idx), p=p / p.sum())])

        w = v.copy()
        w[draw(r, pool.removable(v))] -= 1
        w[draw(a, pool.addable(w))] += 1
        return w
