"""Learned deck drafting (logs #65, #67): a draw replaces k cards of a deck, chosen through the pilot.

One draft head serves every deck of the population (rl/metagame.py); it conditions on the deck it edits.
The pilot (rl/token_model.py, frozen here; it learns only by PPO) reads a deck as it does at the start of a
game: GLOBAL, the 12 empty board slots, one MY_UNSEEN token per distinct card with its copy count, and an
opponent's list (OPPONENT_LIST tokens). The deck is read against a sample of the field (other decks of the
population) and the readings averaged, so the pick answers the field, not one opponent. Without an
opponent's list the pilot reads a deck off its training distribution (log #65: same-card cosine with real
openings 0.36 without one, 0.64 with one, 0.72 between two real openings). That gives H_j, card j as the
pilot reads it in this deck, and h0, the pooled state. Each candidate card c is read the same way inside the
deck it would join (D plus one copy of c), giving E_c, so what the pilot has learned from play about how
cards go together is what the head reads. A draw makes k changes, one after another:

  out  a copy of the deck, card j with probability proportional to copies_j x exp(out(H_j)) (uniform over
       copies at the start)
  in   q_j = CrossBlock(H_j -> [h0, H]) (identity at the start); logits over the pool
       (E_c . W q_j) / sqrt(d) + b_in[c], over the cards that keep the deck legal (never j itself)

The number of changes is fixed (log #66: a learned change rate collapsed to 0, after which nothing more was
learned). Only copies of the original deck can go out, and the masks are updated after each change, so every
draw is legal and its log-probability exact. REINFORCE on the games' results trains the head.
"""
import math

import numpy as np
import torch
import torch.nn as nn

from rl.decks import Pool
from rl.token_model import CrossBlock

GLOBAL, SLOT, MY_UNSEEN, OPPONENT_LIST = 1, 2, 9, 10      # token kinds (env/tokens.js KIND)
LEAD = 13                                                  # GLOBAL + 12 board slots come first, as in every real state


def deck_tokens(ids: np.ndarray, counts: np.ndarray, width: int, opp_ids=(), opp_counts=()):
    """The pre-game state of a deck (distinct card ids and their copies) against an opponent's list, as
    encoder inputs of `width` tokens: card, kind and aux, each [width]. One free token follows the deck."""
    card = np.zeros(width, dtype=np.int64)
    kind = np.zeros(width, dtype=np.int64)
    aux = np.zeros(width, dtype=np.int64)
    kind[0] = GLOBAL
    kind[1:LEAD] = SLOT
    aux[1:LEAD] = np.arange(12)
    J, K = len(ids), len(opp_ids)
    card[LEAD:LEAD + J], kind[LEAD:LEAD + J], aux[LEAD:LEAD + J] = ids, MY_UNSEEN, np.minimum(counts, 255)
    o = LEAD + J + 1
    card[o:o + K], kind[o:o + K], aux[o:o + K] = opp_ids, OPPONENT_LIST, np.minimum(opp_counts, 255)
    return card, kind, aux


def rloo(z: np.ndarray, groups: np.ndarray) -> np.ndarray:
    """z minus the mean of the other samples in its group (0 for a sample alone in its group)."""
    z = np.asarray(z, dtype=np.float64)
    adv = np.zeros_like(z)
    for g in np.unique(groups):
        i = np.nonzero(groups == g)[0]
        if len(i) > 1:
            adv[i] = z[i] - (z[i].sum() - z[i]) / (len(i) - 1)
    return adv


def random_changes(pool: Pool, v: np.ndarray, n: int, rng) -> np.ndarray:
    """v with n random legal one-copy replacements (uniform over copies out and over legal cards in)."""
    v = v.copy()
    for _ in range(n):
        rem = np.nonzero(pool.removable(v))[0]
        out = rng.choice(np.repeat(rem, v[rem]))
        v[out] -= 1
        add = pool.addable(v)
        add[[0, out]] = False
        v[rng.choice(np.nonzero(add)[0])] += 1
    assert pool.legal(v)
    return v


class DraftHead(nn.Module):
    def __init__(self, n_cards: int, d: int, heads: int):
        super().__init__()
        self.out = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))
        nn.init.zeros_(self.out[-1].weight)                      # uniform over copies at the start
        nn.init.zeros_(self.out[-1].bias)
        self.cross = CrossBlock(d, heads, 2 * d)
        for m in (self.cross.proj, self.cross.ff[-1]):          # identity at the start: q_j = H_j
            nn.init.zeros_(m.weight)
            nn.init.zeros_(m.bias)
        self.W = nn.Linear(d, d, bias=False)
        nn.init.zeros_(self.W.weight)                            # uniform over the legal cards at the start
        self.b_in = nn.Parameter(torch.zeros(n_cards))
        self.d = d

    def forward(self, H, h0, E):
        """H [J, d] deck cards, h0 [d], E [n, d] candidates in context -> out scores [J], in logits [J, n]."""
        keys = torch.cat([h0[None], H], 0)[None]
        q = self.cross(H[None], keys, torch.ones(1, keys.shape[1], dtype=torch.bool, device=H.device))[0]
        return self.out(H).squeeze(-1), (self.W(q) @ E.T) / math.sqrt(self.d) + self.b_in


class DeckView:
    """One deck as the pilot reads it, and the head's current choice scores for it (s, logits)."""

    def __init__(self, deck, ids, counts, H, h0, E, base):
        self.deck, self.ids, self.counts, self.H, self.h0, self.E, self.base = deck, ids, counts, H, h0, E, base
        self.s = self.logits = None


class Drafter:
    """The draft head and its optimizer."""

    def __init__(self, pool: Pool, d: int, heads: int, swaps: int, lr: float, device: str):
        self.pool, self.device, self.swaps = pool, device, swaps
        self.head = DraftHead(pool.n, d, heads).to(device)
        self.opt = torch.optim.Adam(self.head.parameters(), lr=lr)

    @torch.no_grad()
    def view(self, pilot, deck: np.ndarray, field: list) -> DeckView:
        """Reads the deck and every candidate with the pilot against each deck of `field`, averaged."""
        pool, dev = self.pool, self.device
        ids = np.nonzero(deck)[0]
        counts = deck[ids]
        J = len(ids)
        cands = np.nonzero(pool.allowed)[0]
        cands = cands[cands > 0]
        width = LEAD + J + 1 + max(int((opp > 0).sum()) for opp in field)
        rows, pos = [], []
        for opp in field:                                        # the deck, then D plus one copy of each c
            oi = np.nonzero(opp)[0]
            rows.append(deck_tokens(ids, counts, width, oi, opp[oi]))
            for c in cands:
                k = np.nonzero(ids == c)[0]
                row = deck_tokens(ids, counts, width, oi, opp[oi])
                if len(k):
                    row[2][LEAD + k[0]] = min(counts[k[0]] + 1, 255)
                    pos.append(LEAD + k[0])
                else:
                    row[0][LEAD + J], row[1][LEAD + J], row[2][LEAD + J] = c, MY_UNSEEN, 1
                    pos.append(LEAD + J)
                rows.append(row)
        card, kind, aux = (torch.from_numpy(np.stack(x)).to(dev) for x in zip(*rows))
        B = card.shape[0]
        glob = torch.zeros(B, pilot.glob_f, dtype=torch.uint8, device=dev)
        slots = torch.zeros(B, 12 * pilot.slot_f, dtype=torch.uint8, device=dev)
        x = pilot.encode(card, kind, aux, glob, slots)[0].float()
        F_, C = len(field), len(cands)
        first = torch.arange(F_, device=dev) * (C + 1)           # each opponent's plain deck row
        H, h0 = x[first, LEAD:LEAD + J].mean(0), x[first, 0].mean(0)
        crow = (first[:, None] + 1 + torch.arange(C, device=dev)[None]).reshape(-1)
        cpos = torch.tensor(pos, device=dev)
        E = torch.zeros(pool.n, x.shape[-1], device=dev)
        E[torch.from_numpy(cands).to(dev)] = x[crow, cpos].view(F_, C, -1).mean(0)
        base = np.zeros((J, pool.n), dtype=bool)                 # legal incoming cards for one copy out of D
        for j, c in enumerate(ids):
            w = deck.copy()
            w[c] -= 1
            base[j] = pool.addable(w)
            base[j, [0, c]] = False
        vw = DeckView(deck.copy(), ids, counts, H, h0, E, torch.from_numpy(base).to(dev))
        self.refresh(vw)
        return vw

    @torch.no_grad()
    def refresh(self, vw: DeckView):
        out, logits = self.head(vw.H, vw.h0, vw.E)
        vw.s = out.cpu().numpy().astype(np.float64)
        vw.logits = logits.cpu().numpy().astype(np.float64)

    def sample(self, vw: DeckView, rng) -> dict:
        """One draw: `swaps` copies of the deck replaced one after another, legal throughout."""
        pool, v = self.pool, vw.deck.copy()
        left = vw.counts.astype(np.int64).copy()                 # copies of the original deck not yet replaced
        ev_j, ev_c, ev_mask, ev_left = [], [], [], []
        lp = 0.0                                                 # log pi of the draw, for the tests
        for _ in range(self.swaps):
            ok = left > 0
            if v[pool.basic_pokemon].sum() <= 1:                 # the last Basic stays
                ok &= ~pool.basic_pokemon[vw.ids]
            if not ok.any():
                break
            lw = np.where(ok, np.log(np.maximum(left, 1)) + vw.s, -np.inf)
            p = np.exp(lw - lw.max())
            j = int(rng.choice(len(p), p=p / p.sum()))
            c = int(vw.ids[j])
            lp += math.log(p[j] / p.sum())
            ev_left.append(np.where(ok, left, 0))
            v[c] -= 1
            left[j] -= 1
            m = pool.addable(v)
            m[[0, c]] = False
            x = np.where(m, vw.logits[j], -np.inf)
            q = np.exp(x - x.max())
            new = int(rng.choice(pool.n, p=q / q.sum()))
            lp += math.log(q[new] / q.sum())
            v[new] += 1
            ev_j.append(j)
            ev_c.append(new)
            ev_mask.append(m)
        assert pool.legal(v), "drawn deck is not legal"
        return {"deck": v, "ev_j": ev_j, "ev_c": ev_c, "ev_mask": ev_mask, "ev_left": ev_left, "logp": lp}

    def log_prob(self, vw: DeckView, samples: list):
        """log pi of each draw of this deck under the current head, and the head's entropies on the deck."""
        dev = self.device
        s, logits = self.head(vw.H, vw.h0, vw.E)
        lp = torch.zeros(len(samples), device=dev)
        ev_s = [i for i, x in enumerate(samples) for _ in x["ev_j"]]
        if ev_s:
            j = torch.tensor([y for x in samples for y in x["ev_j"]], device=dev)
            c = torch.tensor([y for x in samples for y in x["ev_c"]], device=dev)
            m = torch.from_numpy(np.stack([y for x in samples for y in x["ev_mask"]])).to(dev)
            left = torch.from_numpy(np.stack([y for x in samples for y in x["ev_left"]])).to(dev).float()
            lw = torch.where(left > 0, torch.log(left.clamp(min=1)) + s[None], torch.full_like(left, -1e9))
            out_lp = lw.gather(1, j[:, None]).squeeze(1) - torch.logsumexp(lw, 1)
            row = logits[j].masked_fill(~m, -1e9)
            in_lp = row.gather(1, c[:, None]).squeeze(1) - torch.logsumexp(row, 1)
            lp = lp.index_add(0, torch.tensor(ev_s, device=dev), out_lp + in_lp)
        po = torch.log_softmax(s + torch.log(torch.tensor(vw.counts, dtype=torch.float32, device=dev)), 0)
        h_out = -(po.exp() * po).sum()
        q = torch.log_softmax(logits.masked_fill(~vw.base, -1e9), 1)
        h_in = (po.exp().detach() * -(q.exp() * q).masked_fill(~vw.base, 0).sum(1)).sum()
        return lp, h_out, h_in

    def update(self, batch: list, beta: float) -> dict:
        """One REINFORCE step over [(view, draws, advantages)]; advantages are scaled to unit standard
        deviation over the whole batch."""
        a_all = np.concatenate([np.asarray(a, dtype=np.float64) for _, _, a in batch]) if batch else np.zeros(0)
        sd = a_all.std() if len(a_all) and a_all.std() > 0 else 1.0
        n = max(len(a_all), 1)
        self.opt.zero_grad()
        h_out = h_in = 0.0
        for vw, samples, a in batch:
            lp, ho, hi = self.log_prob(vw, samples)
            at = torch.tensor(np.asarray(a) / sd, dtype=torch.float32, device=self.device)
            loss = -(at * lp).sum() / n - beta * (ho + hi) / len(batch)
            loss.backward()
            h_out += float(ho.detach()) / len(batch)
            h_in += float(hi.detach()) / len(batch)
        grad = float(torch.nn.utils.clip_grad_norm_(self.head.parameters(), 1.0))
        self.opt.step()
        for vw, _, _ in batch:
            self.refresh(vw)
        return {"h_out": round(h_out, 4), "h_in": round(h_in, 4), "grad_norm": round(grad, 4)}

    def summary(self, vw: DeckView, top: int = 3) -> dict:
        """The head's favourite moves on a deck: cards out and cards in."""
        pool = self.pool
        po = np.log(vw.counts) + vw.s
        po = np.exp(po - po.max())
        po /= po.sum()
        base = vw.base.cpu().numpy()
        x = np.where(base, vw.logits, -np.inf)
        q = np.exp(x - x.max(1, keepdims=True))
        q /= q.sum(1, keepdims=True)
        incoming = (po[:, None] * q).sum(0)
        return {"top_out": [[pool.full_name[int(vw.ids[j])], round(float(po[j]), 4)] for j in np.argsort(-po)[:top]],
                "top_in": [[pool.full_name[int(c)], round(float(incoming[c]), 4)] for c in np.argsort(-incoming)[:top]]}

    def state(self) -> dict:
        return {"head": self.head.state_dict(), "opt": self.opt.state_dict()}

    def load(self, st: dict):
        self.head.load_state_dict(st["head"])
        self.opt.load_state_dict(st["opt"])
