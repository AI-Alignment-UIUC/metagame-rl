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
learned). With group_p > 0 (log #127) a change is, with that probability, a group change: after the same two choices
every remaining original copy of card j goes out for copies of c, as many as the copy limit lets in (4 Snorlax for 4
Hitmonchan, 9 Psychic Energy for 9 Fighting), so one draw can make the coordinated moves a deck type needs; the extra
copies follow from the two choices, so the draw's log-probability is still exact. Only copies of the original deck can go out, and the masks are updated after each change, so every
draw is legal and its log-probability exact. REINFORCE on the games' results trains the head.

With base="features" (H110's Nf, log #193) the incoming draw starts from a base measure q0 instead of the uniform: q0(c | j)
∝ exp(cos(E_c, E_j) / tau), the pilot's own reading of each candidate against the card going out, with tau set per view
so q0's mean entropy is base_ent nats. Its log is a fixed offset on the head's incoming logits, so log-probs stay exact;
the floor tempers the head's part toward q0 (KL(q || q0) at most log(legal) - floor, which is the entropy floor when
q0 is uniform), and the head's entropy bonus becomes -KL(q || q0). No card kinds or names are used.
"""
import math

import numpy as np
import torch
import torch.nn as nn

from rl.decks import MAX_COPIES, Pool
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
        self.b0 = self.b0np = None                               # base measure offsets [J, n] (base="features")


def floor_temperature(x: np.ndarray, floor: float, b: np.ndarray = None) -> float:
    """The smallest temperature >= 1 at which softmax(x / T) over x's finite entries has entropy >= floor (nats, capped
    just below the uniform's); 1 if it already has. With a base measure's offsets b, softmax(b + x / T) instead, with
    KL from softmax(b) at most log(n) - floor (the same condition when b is constant)."""
    f = np.isfinite(x)
    if floor <= 0 or f.sum() <= 1:
        return 1.0
    y0 = x[f] - x[f].max()
    floor = min(floor, math.log(f.sum()) - 1e-3)
    if b is not None:
        lq0 = b[f] - b[f].max()
        lq0 -= np.log(np.exp(lq0).sum())
        budget = math.log(f.sum()) - floor

        def H(T):                                                # -KL, so the search below is the same
            y = lq0 + y0 / T
            p = np.exp(y - y.max())
            p /= p.sum()
            return float(-(p * (np.log(np.maximum(p, 1e-300)) - lq0)).sum())
        floor = -budget
    else:
        def H(T):
            p = np.exp(y0 / T)
            p /= p.sum()
            return float(-(p * np.log(np.maximum(p, 1e-300))).sum())
    if H(1.0) >= floor:
        return 1.0
    lo, hi = 1.0, 2.0
    while H(hi) < floor and hi < 1e6:
        lo, hi = hi, hi * 2
    for _ in range(30):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if H(mid) < floor else (lo, mid)
    return hi


def base_tau(cos: torch.Tensor, mask: torch.Tensor, target: float) -> float:
    """The temperature at which softmax(cos / tau) over each row's legal entries has mean entropy `target` nats
    (inf, a uniform base, if the target is at or above the uniform's)."""
    n = mask.sum(1).clamp(min=1).float()
    if target >= float(torch.log(n).mean()) - 1e-6:
        return math.inf

    def H(tau):
        lq = torch.log_softmax((cos / tau).masked_fill(~mask, -1e9), 1)
        return float((-(lq.exp() * lq).masked_fill(~mask, 0).sum(1)).mean())
    lo, hi = math.log(1e-4), math.log(1e4)                      # entropy rises with tau; bisect on log tau
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if H(math.exp(mid)) < target else (lo, mid)
    return math.exp(hi)


class Drafter:
    """The draft head and its optimizer."""

    def __init__(self, pool: Pool, d: int, heads: int, swaps: int, lr: float, device: str, h_in_floor: float = 0.0,
                 group_p: float = 0.0, base: str = "uniform", base_ent: float = 3.0):
        assert base in ("uniform", "features"), base
        self.pool, self.device, self.swaps, self.group_p = pool, device, swaps, group_p
        self.head = DraftHead(pool.n, d, heads).to(device)
        self.opt = torch.optim.Adam(self.head.parameters(), lr=lr)
        self.h_in_floor = h_in_floor          # nats; an incoming choice below it is sampled warmer (log #109)
        self.base, self.base_ent = base, base_ent       # the incoming draw's base measure (log #193)

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
        self.set_base(vw)
        self.refresh(vw)
        return vw

    @torch.no_grad()
    def set_base(self, vw: DeckView):
        """base="features": q0(c | j) ∝ exp(cos(E_c, E_j) / tau) on the view, tau giving mean entropy base_ent."""
        if self.base != "features":
            return
        F = torch.nn.functional.normalize(vw.E, dim=1)
        cos = F[torch.from_numpy(vw.ids).to(F.device)] @ F.T           # [J, n]
        tau = base_tau(cos, vw.base, self.base_ent)
        vw.b0 = cos / tau if math.isfinite(tau) else torch.zeros_like(cos)
        vw.b0np = vw.b0.cpu().numpy().astype(np.float64)
        vw.tau = tau

    @torch.no_grad()
    def refresh(self, vw: DeckView):
        out, logits = self.head(vw.H, vw.h0, vw.E)
        vw.s = out.cpu().numpy().astype(np.float64)
        vw.logits = logits.cpu().numpy().astype(np.float64)

    def sample(self, vw: DeckView, rng) -> dict:
        """One draw: `swaps` copies of the deck replaced one after another, legal throughout."""
        pool, v = self.pool, vw.deck.copy()
        left = vw.counts.astype(np.int64).copy()                 # copies of the original deck not yet replaced
        ev_j, ev_c, ev_mask, ev_left, ev_T = [], [], [], [], []
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
            b = None if vw.b0np is None else vw.b0np[j]
            T = floor_temperature(x, self.h_in_floor, b)
            y = (x - x.max()) / T if b is None else b + x / T
            q = np.exp(y - y.max())
            new = int(rng.choice(pool.n, p=q / q.sum()))
            lp += math.log(q[new] / q.sum())
            v[new] += 1
            if self.group_p > 0 and rng.random() < self.group_p:     # a group change: the rest of j's copies too
                n = int(left[j])
                if not pool.basic_energy[new]:
                    nb = v.copy()
                    nb[pool.basic_energy] = 0
                    n = min(n, MAX_COPIES - int(pool.name_counts(nb)[pool.name_of[new]]))
                if pool.basic_pokemon[c] and not pool.basic_pokemon[new]:
                    n = min(n, int(v[pool.basic_pokemon].sum()) - 1)    # the last Basic stays
                n = max(n, 0)
                v[c] -= n
                left[j] -= n
                v[new] += n
            ev_j.append(j)
            ev_c.append(new)
            ev_mask.append(m)
            ev_T.append(T)
        assert pool.legal(v), "drawn deck is not legal"
        return {"deck": v, "ev_j": ev_j, "ev_c": ev_c, "ev_mask": ev_mask, "ev_left": ev_left, "ev_T": ev_T, "logp": lp}

    def log_prob(self, vw: DeckView, samples: list):
        """log pi of each draw of this deck under the current head, the head's entropies on the deck, and the incoming
        choice's bonus (its entropy, or -KL from the base measure)."""
        dev = self.device
        s, logits = self.head(vw.H, vw.h0, vw.E)
        b0 = vw.b0
        lp = torch.zeros(len(samples), device=dev)
        ev_s = [i for i, x in enumerate(samples) for _ in x["ev_j"]]
        if ev_s:
            j = torch.tensor([y for x in samples for y in x["ev_j"]], device=dev)
            c = torch.tensor([y for x in samples for y in x["ev_c"]], device=dev)
            m = torch.from_numpy(np.stack([y for x in samples for y in x["ev_mask"]])).to(dev)
            left = torch.from_numpy(np.stack([y for x in samples for y in x["ev_left"]])).to(dev).float()
            lw = torch.where(left > 0, torch.log(left.clamp(min=1)) + s[None], torch.full_like(left, -1e9))
            out_lp = lw.gather(1, j[:, None]).squeeze(1) - torch.logsumexp(lw, 1)
            T = torch.tensor([y for x in samples for y in x.get("ev_T", [1.0] * len(x["ev_j"]))], device=dev)
            row = logits[j] / T[:, None] if b0 is None else b0[j] + logits[j] / T[:, None]
            row = row.masked_fill(~m, -1e9)
            in_lp = row.gather(1, c[:, None]).squeeze(1) - torch.logsumexp(row, 1)
            lp = lp.index_add(0, torch.tensor(ev_s, device=dev), out_lp + in_lp)
        po = torch.log_softmax(s + torch.log(torch.tensor(vw.counts, dtype=torch.float32, device=dev)), 0)
        h_out = -(po.exp() * po).sum()
        q = torch.log_softmax((logits if b0 is None else b0 + logits).masked_fill(~vw.base, -1e9), 1)
        h_in = (po.exp().detach() * -(q.exp() * q).masked_fill(~vw.base, 0).sum(1)).sum()
        if b0 is None:
            return lp, h_out, h_in, h_in
        q0 = torch.log_softmax(b0.masked_fill(~vw.base, -1e9), 1)
        kl = (po.exp().detach() * (q.exp() * (q - q0)).masked_fill(~vw.base, 0).sum(1)).sum()
        return lp, h_out, h_in, -kl

    def update(self, batch: list, beta: float) -> dict:
        """One REINFORCE step over [(view, draws, advantages)]; advantages are scaled to unit standard
        deviation over the whole batch."""
        a_all = np.concatenate([np.asarray(a, dtype=np.float64) for _, _, a in batch]) if batch else np.zeros(0)
        sd = a_all.std() if len(a_all) and a_all.std() > 0 else 1.0
        n = max(len(a_all), 1)
        self.opt.zero_grad()
        h_out = h_in = kl_in = 0.0
        for vw, samples, a in batch:
            lp, ho, hi, bonus = self.log_prob(vw, samples)
            at = torch.tensor(np.asarray(a) / sd, dtype=torch.float32, device=self.device)
            loss = -(at * lp).sum() / n - beta * (ho + bonus) / len(batch)
            loss.backward()
            h_out += float(ho.detach()) / len(batch)
            h_in += float(hi.detach()) / len(batch)
            kl_in -= float(bonus.detach()) / len(batch)
        grad = float(torch.nn.utils.clip_grad_norm_(self.head.parameters(), 1.0))
        self.opt.step()
        for vw, _, _ in batch:
            self.refresh(vw)
        out = {"h_out": round(h_out, 4), "h_in": round(h_in, 4), "grad_norm": round(grad, 4)}
        if self.base != "uniform":
            out["kl_in"] = round(kl_in, 4)
        return out

    def summary(self, vw: DeckView, top: int = 3) -> dict:
        """The head's favourite moves on a deck: cards out and cards in."""
        pool = self.pool
        po = np.log(vw.counts) + vw.s
        po = np.exp(po - po.max())
        po /= po.sum()
        base = vw.base.cpu().numpy()
        x = np.where(base, vw.logits if vw.b0np is None else vw.b0np + vw.logits, -np.inf)
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
