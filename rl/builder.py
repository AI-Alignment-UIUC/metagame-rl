"""Deck-edit builder (plan item A5.2): a policy that improves a deck by K remove-and-add edits.

An episode starts from a legal deck. Each edit is two pointer choices: a card to remove (one
copy, from the deck) and a card to add (from the pool), both masked by the construction rules
(rl/decks.py), so every intermediate deck is legal. The reward after each edit is the change in
predicted win rate against the meta mixture,
    M(deck) = sum_j sigma_j P(deck beats population_j)       (rl/matchup.py)
which telescopes to the final deck's improvement. Episodes run batched on the GPU; trained with
PPO. Proposals are the final decks of sampled episodes, the best few kept that are distinct from
each other and from the population.
"""
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from rl.decks import Pool, overlap
from rl.token_model import card_feature_matrix


class EditMasks:
    """Construction-rule masks for batches of count vectors (torch)."""

    def __init__(self, pool: Pool, device):
        names = len(pool.name_index)
        self.n = pool.n
        N = np.zeros((pool.n, names), dtype=np.float32)
        for i in range(1, pool.n):
            N[i, pool.name_of[i]] = 1
        self.N = torch.from_numpy(N).to(device)
        self.basic_energy = torch.from_numpy(pool.basic_energy).to(device)
        self.basic_pokemon = torch.from_numpy(pool.basic_pokemon).to(device)
        self.allowed = torch.from_numpy(pool.allowed).to(device)
        self.allowed[0] = False

    def removable(self, V):
        m = V > 0
        last_basic = (V * self.basic_pokemon).sum(-1, keepdim=True) <= 1
        return m & ~(last_basic & self.basic_pokemon[None, :])

    def addable(self, V):
        nonbasic = V * (~self.basic_energy).float()[None, :]
        counts = nonbasic @ self.N                                  # copies per card name
        per_card = counts @ self.N.T                                # each card's name count
        return self.allowed[None, :] & (self.basic_energy[None, :] | (per_card < 4))


class EditPolicy(nn.Module):
    def __init__(self, table: list, text_emb: np.ndarray, d: int = 128, steps: int = 16):
        super().__init__()
        self.register_buffer("feats", torch.from_numpy(card_feature_matrix(table)))
        self.register_buffer("text", torch.from_numpy(text_emb.astype(np.float32)))
        n = self.feats.shape[0]
        self.card_struct = nn.Linear(self.feats.shape[1], d)
        self.card_text = nn.Linear(self.text.shape[1], d)
        self.card_resid = nn.Embedding(n, d)
        nn.init.zeros_(self.card_resid.weight)
        self.deck = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Linear(d, d))
        self.meta = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Linear(d, d))
        self.step = nn.Embedding(steps + 1, d)
        self.query = nn.Sequential(nn.Linear(3 * d, d), nn.GELU(), nn.Linear(d, d))
        self.rm_key = nn.Linear(d, d)
        self.add_key = nn.Linear(d, d)
        self.add_q = nn.Linear(2 * d, d)
        self.value = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))

    def cards(self):
        return self.card_struct(self.feats) + self.card_text(self.text) + self.card_resid.weight

    def forward(self, V, meta_counts, sigma, step):
        """V [B, n] counts; meta_counts [P, n] population decks; sigma [P] mixture; step [B]."""
        E = self.cards()
        deck = self.deck(V.float() @ E / 60.0)
        meta = self.meta((sigma[:, None] * (meta_counts.float() @ E / 60.0)).sum(0))[None, :].expand_as(deck)
        q = self.query(torch.cat([deck, meta, self.step(step)], -1))
        rm_logits = (self.rm_key(E) @ q.T).T                       # [B, n]
        return q, rm_logits, E

    def add_logits(self, q, E, removed):
        qa = self.add_q(torch.cat([q, E[removed]], -1))
        return (self.add_key(E) @ qa.T).T


class Builder:
    def __init__(self, pool: Pool, table, text_emb, device, steps: int = 16, d: int = 128, lr: float = 3e-4):
        self.pool, self.device, self.steps = pool, device, steps
        self.masks = EditMasks(pool, device)
        self.policy = EditPolicy(table, text_emb, d, steps).to(device)
        self.opt = torch.optim.Adam(self.policy.parameters(), lr=lr)

    def score(self, model, V, pop, sigma):
        """M(deck) for decks V [B, n] against population pop [P, n] with mixture sigma [P]."""
        with torch.no_grad():
            za, zp = model.embed(V), model.embed(pop)
            B, P = za.shape[0], zp.shape[0]
            p = torch.sigmoid(model.logit(za[:, None, :].expand(B, P, -1).reshape(B * P, -1),
                                          zp[None, :, :].expand(B, P, -1).reshape(B * P, -1))).view(B, P)
            return p @ sigma

    def rollout(self, model, starts, pop, sigma, greedy=False):
        """Runs K edits from each start deck. Returns the trajectory and the final decks."""
        V = starts.clone()
        traj = {k: [] for k in ("V", "step", "rm", "add", "logp_rm", "logp_add", "value", "reward")}
        before = self.score(model, V, pop, sigma)
        for t in range(self.steps):
            stp = torch.full((V.shape[0],), t, device=self.device, dtype=torch.long)
            with torch.no_grad():
                q, rm_logits, E = self.policy(V, pop, sigma, stp)
                rm_logits = rm_logits.masked_fill(~self.masks.removable(V), -1e9)
                rm = rm_logits.argmax(-1) if greedy else torch.distributions.Categorical(logits=rm_logits).sample()
                V1 = V.clone()
                V1[torch.arange(V.shape[0]), rm] -= 1
                add_logits = self.policy.add_logits(q, E, rm).masked_fill(~self.masks.addable(V1), -1e9)
                add = add_logits.argmax(-1) if greedy else torch.distributions.Categorical(logits=add_logits).sample()
                V2 = V1.clone()
                V2[torch.arange(V.shape[0]), add] += 1
                after = self.score(model, V2, pop, sigma)
                traj["V"].append(V); traj["step"].append(stp); traj["rm"].append(rm); traj["add"].append(add)
                traj["logp_rm"].append(F.log_softmax(rm_logits, -1).gather(1, rm[:, None]).squeeze(1))
                traj["logp_add"].append(F.log_softmax(add_logits, -1).gather(1, add[:, None]).squeeze(1))
                traj["value"].append(self.policy.value(q).squeeze(-1))
                traj["reward"].append(after - before)
            V, before = V2, after
        return traj, V

    def train(self, model, starts_fn, pop, sigma, iterations=200, batch=256, epochs=4, clip=0.2, ent=0.01, gamma=1.0, lam=0.95):
        pop = pop.to(self.device)
        sigma = sigma.to(self.device)
        log = []
        for it in range(iterations):
            starts = starts_fn(batch).to(self.device)
            traj, final = self.rollout(model, starts, pop, sigma)
            T = self.steps
            R = torch.stack(traj["reward"])                         # [T, B]
            Vv = torch.stack(traj["value"])
            adv = torch.zeros_like(R)
            last = torch.zeros_like(R[0])
            for t in reversed(range(T)):
                nxt = Vv[t + 1] if t + 1 < T else torch.zeros_like(R[0])
                delta = R[t] + gamma * nxt - Vv[t]
                last = delta + gamma * lam * last
                adv[t] = last
            ret = adv + Vv
            flat = lambda k: torch.cat(traj[k])
            Vs, steps, rms, adds = flat("V"), flat("step"), flat("rm"), flat("add")
            old = flat("logp_rm") + flat("logp_add")
            A = adv.reshape(-1)
            A = (A - A.mean()) / (A.std() + 1e-8)
            Rt = ret.reshape(-1)
            for _ in range(epochs):
                q, rm_logits, E = self.policy(Vs, pop, sigma, steps)
                rm_logits = rm_logits.masked_fill(~self.masks.removable(Vs), -1e9)
                V1 = Vs.clone()
                V1[torch.arange(Vs.shape[0]), rms] -= 1
                add_logits = self.policy.add_logits(q, E, rms).masked_fill(~self.masks.addable(V1), -1e9)
                lp_rm, lp_add = F.log_softmax(rm_logits, -1), F.log_softmax(add_logits, -1)
                logp = lp_rm.gather(1, rms[:, None]).squeeze(1) + lp_add.gather(1, adds[:, None]).squeeze(1)
                entropy = -(lp_rm.exp() * lp_rm).sum(-1).mean() - (lp_add.exp() * lp_add).sum(-1).mean()
                ratio = (logp - old).exp()
                pi = -torch.min(ratio * A, ratio.clamp(1 - clip, 1 + clip) * A).mean()
                v = self.policy.value(q).squeeze(-1)
                loss = pi + 0.5 * ((v - Rt) ** 2).mean() - ent * entropy
                self.opt.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.policy.parameters(), 0.5)
                self.opt.step()
            gain = R.sum(0)
            log.append({"iteration": it, "gain": float(gain.mean()), "final_score": float(self.score(model, final, pop, sigma).mean())})
        return log

    def propose(self, model, starts, pop, sigma, k=4, samples=8, min_distance=0.1, existing=()):
        """The k best final decks of sampled episodes from `starts`, at least `min_distance`
        (1 - overlap) apart from each other and from `existing` (K edits change at most K/60)."""
        pop, sigma = pop.to(self.device), sigma.to(self.device)
        S = starts.repeat(samples, 1).to(self.device)
        _, final = self.rollout(model, S, pop, sigma)
        scores = self.score(model, final, pop, sigma).cpu().numpy()
        final = final.cpu().numpy()
        chosen = []
        for i in np.argsort(-scores):
            v = final[i]
            if not self.pool.legal(v):
                continue
            if any(1 - overlap(v, u) < min_distance for u in list(existing) + [c[0] for c in chosen]):
                continue
            chosen.append((v, float(scores[i])))
            if len(chosen) == k:
                break
        return chosen
