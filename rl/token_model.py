"""Token + pointer policy-value network (plan item A4.2).

Inputs come from env/tokens.js: card tokens (card id, kind, aux), global and slot features
(bytes, round(48 x)), and one candidate per legal option ([verb, card, slot1, slot2, name, extra]).

  card embedding  = Linear(structured card features) + Linear(rules-text embedding, frozen)
                    + a learned per-card residual (starts at zero), so an unseen card still has
                    a representation from its features and text
  token           = card embedding + kind + aux (+ global / slot features on tokens 0 and 1..12)
  encoder         = pre-LN transformer blocks over the tokens (padding masked)
  candidate       = verb + card embedding + the encoder output of the slot(s) it targets
                    + attack/Power name + extra, then cross-attention to the tokens
  policy          = one logit per candidate (a pointer over the options on offer)
  value           = from the global token

With n_agents > 0 the network is a population (rl/league.py, log #53; NeuPL-style): a learned agent
embedding is added to every token, and each agent has its own value head. Both start as the base
network's (embedding zero, heads copied by init_agents_from_base), so every agent first plays exactly
as the checkpoint it was loaded from; forward(agent=ids) picks the agent per row, and without ids the
network is agent `fixed_agent` (what an ONNX export bakes in).

Written with plain matmul attention so it exports to ONNX for the Node rollout workers.
"""
import json
import math

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

TYPES = 11
NUM_KINDS = 16
NUM_VERBS = 32


def card_feature_matrix(table: list) -> np.ndarray:
    """Structured features per card id (row 0 = no card)."""
    rows = [np.zeros(0)]
    for c in table:
        f = []
        f += [1.0 if c["superType"] == k else 0.0 for k in (1, 2, 3)]                 # Pokemon / Trainer / Energy
        f += [1.0 if c["stage"] == k else 0.0 for k in (1, 2, 3, 4)]                  # restored / basic / stage 1 / 2
        f += [c["hp"] / 100.0]
        f += [float(x) for x in c["types"]]
        f += [float(x) for x in c["weakness"]]
        f += [float(x) for x in c["resistance"]]
        f += [c["retreat"] / 4.0]
        f += [1.0 if c["trainerType"] == k else 0.0 for k in (0, 1, 2, 3)]
        f += [float(x) for x in c["provides"]] + [c["provideAmount"] / 2.0]
        f += [1.0 if c["energyType"] == k else 0.0 for k in (0, 1)]
        attacks = c["attacks"][:3]
        for i in range(3):
            if i < len(attacks):
                a = attacks[i]
                f += [1.0, sum(a["cost"]) / 4.0, a["damage"] / 100.0, 1.0 if a["text"] else 0.0]
                f += [x / 2.0 for x in a["cost"]]
            else:
                f += [0.0] * (4 + TYPES)
        f += [len(c["powers"]) / 2.0, 1.0 if c["evolvesFrom"] else 0.0]
        rows.append(np.array(f, dtype=np.float32))
    width = len(rows[1])
    rows[0] = np.zeros(width, dtype=np.float32)
    return np.stack(rows)


def attend(q, k, v, mask):
    """Attention over the unmasked keys. Plain matmuls when exporting to ONNX; PyTorch's fused
    kernel otherwise (same result, much less memory in training)."""
    if torch.onnx.is_in_onnx_export():
        att = (q @ k.transpose(-1, -2)) / math.sqrt(q.shape[-1])
        return att.masked_fill(~mask[:, None, None, :], -1e9).softmax(-1) @ v
    return F.scaled_dot_product_attention(q, k, v, attn_mask=mask[:, None, None, :])


class Block(nn.Module):
    """Pre-LN transformer block; keys masked by `mask` (True = real token)."""

    def __init__(self, d: int, heads: int, ff: int):
        super().__init__()
        self.h = heads
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv = nn.Linear(d, 3 * d)
        self.proj = nn.Linear(d, d)
        self.ff = nn.Sequential(nn.Linear(d, ff), nn.GELU(), nn.Linear(ff, d))

    def forward(self, x, mask):
        B, T, d = x.shape
        hd = d // self.h
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, hd).permute(2, 0, 3, 1, 4)
        y = attend(q, k, v, mask).transpose(1, 2).reshape(B, T, d)
        x = x + self.proj(y)
        return x + self.ff(self.ln2(x))


class CrossBlock(nn.Module):
    """Candidates attend to the state tokens."""

    def __init__(self, d: int, heads: int, ff: int):
        super().__init__()
        self.h = heads
        self.lnq, self.lnk, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d), nn.LayerNorm(d)
        self.q = nn.Linear(d, d)
        self.kv = nn.Linear(d, 2 * d)
        self.proj = nn.Linear(d, d)
        self.ff = nn.Sequential(nn.Linear(d, ff), nn.GELU(), nn.Linear(ff, d))

    def forward(self, c, x, mask):
        B, M, d = c.shape
        T = x.shape[1]
        hd = d // self.h
        q = self.q(self.lnq(c)).view(B, M, self.h, hd).transpose(1, 2)
        k, v = self.kv(self.lnk(x)).view(B, T, 2, self.h, hd).permute(2, 0, 3, 1, 4)
        y = attend(q, k, v, mask).transpose(1, 2).reshape(B, M, d)
        c = c + self.proj(y)
        return c + self.ff(self.ln2(c))


# Ordered features of a token's aux value (the copy count of a card token, or a slot index), added
# with count_features=True: the value itself on two scales and a thermometer code (aux >= k), so
# count n sits between n-1 and n+1 and a count never seen in training is read from the ones that
# were. The aux embedding alone gives every count an unrelated random vector that barely moves in
# training (2-6% of its norm, log #46), and a count never seen is pure initialization.
COUNT_THRESHOLDS = (1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 18, 21, 25, 30, 35, 40)
COUNT_F = 2 + len(COUNT_THRESHOLDS)


def count_features(aux: torch.Tensor) -> torch.Tensor:
    a = aux.float().unsqueeze(-1)
    k = torch.tensor(COUNT_THRESHOLDS, dtype=torch.float32, device=aux.device)
    return torch.cat([a / 8.0, a / 32.0, (a >= k).float()], dim=-1)


class TokenPointerNet(nn.Module):
    def __init__(self, card_table: list, text_emb: np.ndarray, n_names: int, glob_f: int, slot_f: int,
                 max_tok: int, max_cand: int, d: int = 192, layers: int = 3, heads: int = 4,
                 count_features: bool = False, cross_layers: int = 1, cand_self: int = 0, n_agents: int = 0):
        super().__init__()
        feats = torch.from_numpy(card_feature_matrix(card_table))
        self.register_buffer("card_feats", feats)
        self.register_buffer("text_emb", torch.from_numpy(text_emb.astype(np.float32)))
        n_cards = feats.shape[0]
        self.cfg = dict(kind="TokenPointerNet", n_names=n_names, glob_f=glob_f, slot_f=slot_f, max_tok=max_tok,
                        max_cand=max_cand, d=d, layers=layers, heads=heads, count_features=count_features,
                        cross_layers=cross_layers, cand_self=cand_self, n_agents=n_agents)
        self.max_tok, self.max_cand, self.glob_f, self.slot_f = max_tok, max_cand, glob_f, slot_f
        self.action_size = max_cand
        self.card_struct = nn.Linear(feats.shape[1], d)
        self.card_text = nn.Linear(self.text_emb.shape[1], d)
        self.card_resid = nn.Embedding(n_cards, d)
        nn.init.zeros_(self.card_resid.weight)
        self.kind = nn.Embedding(NUM_KINDS, d)
        self.aux = nn.Embedding(256, d)
        self.count_features = count_features
        if count_features:
            nn.init.normal_(self.aux.weight, std=0.02)   # small, so training can actually move it
            self.count_proj = nn.Linear(COUNT_F, d)
        self.glob = nn.Linear(glob_f, d)
        self.slot_num = nn.Linear(slot_f, d)
        self.blocks = nn.ModuleList([Block(d, heads, 2 * d) for _ in range(layers)])
        self.ln_out = nn.LayerNorm(d)
        self.verb = nn.Embedding(NUM_VERBS, d)
        self.name = nn.Embedding(n_names + 1, d)
        self.slot_other = nn.Embedding(16, d)   # 0 none, 13 empty bench, 14 hand, 15 discard
        self.extra = nn.Embedding(64, d)
        self.cand_in = nn.Linear(d, d)
        self.cross = CrossBlock(d, heads, 2 * d)
        # Optional extra candidate layers (log #47's architecture test). Each starts as the identity
        # (its residual outputs zeroed), so a model with them loads a checkpoint without them and
        # plays exactly as it did before fine-tuning:
        #   cross_layers - 1 more cross-attention blocks, candidates to the state tokens
        #   cand_self blocks in which the candidates attend to each other (options compared)
        self.cross_extra = nn.ModuleList([CrossBlock(d, heads, 2 * d) for _ in range(cross_layers - 1)])
        self.cand_blocks = nn.ModuleList([Block(d, heads, 2 * d) for _ in range(cand_self)])
        for blk in list(self.cross_extra) + list(self.cand_blocks):
            for lin in (blk.proj, blk.ff[-1]):
                nn.init.zeros_(lin.weight)
                nn.init.zeros_(lin.bias)
        self.score = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))
        self.value = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))
        nn.init.zeros_(self.score[-1].weight)
        nn.init.zeros_(self.score[-1].bias)
        nn.init.zeros_(self.value[-1].weight)
        nn.init.zeros_(self.value[-1].bias)
        self.n_agents, self.fixed_agent = n_agents, 0
        if n_agents:
            self.agent_emb = nn.Embedding(n_agents, d)
            nn.init.zeros_(self.agent_emb.weight)
            self.value_heads = nn.ModuleList([nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))
                                              for _ in range(n_agents)])
            self.init_agents_from_base()

    @torch.no_grad()
    def init_agents_from_base(self, agents=None):
        """Agents (all, or the listed ones) back to the base network: embedding zero, value head = the
        base value head."""
        for k in (range(self.n_agents) if agents is None else agents):
            self.agent_emb.weight[k].zero_()
            self.value_heads[k].load_state_dict(self.value.state_dict())

    @torch.no_grad()
    def copy_agent(self, src: int, dst: int):
        """Agent dst becomes a copy of agent src (embedding and value head)."""
        self.agent_emb.weight[dst].copy_(self.agent_emb.weight[src])
        self.value_heads[dst].load_state_dict(self.value_heads[src].state_dict())

    def card_emb(self, ids):
        return self.card_struct(self.card_feats[ids]) + self.card_text(self.text_emb[ids]) + self.card_resid(ids)

    def encode(self, tok_card, tok_kind, tok_aux, glob, slots, agent=None):
        """The state's encoded tokens [B, T, d] and their mask [B, T]; token 0 is the pooled state."""
        tok_card, tok_kind, tok_aux = tok_card.long(), tok_kind.long(), tok_aux.long()
        B, T = tok_card.shape
        mask = tok_kind > 0
        x = self.card_emb(tok_card) + self.kind(tok_kind) + self.aux(tok_aux)
        if self.count_features:
            x = x + self.count_proj(count_features(tok_aux))
        g = self.glob(glob.float() / 48.0)[:, None, :]
        s = self.slot_num(slots.float().view(B, 12, self.slot_f) / 48.0)
        pad = torch.zeros(B, T - 13, x.shape[-1], dtype=x.dtype, device=x.device)
        x = x + torch.cat([g, s, pad], dim=1)
        if self.n_agents:
            if agent is None:
                x = x + self.agent_emb.weight[self.fixed_agent][None, None, :]
            else:
                x = x + self.agent_emb(agent.long())[:, None, :]
        for b in self.blocks:
            x = b(x, mask)
        return self.ln_out(x), mask

    def forward(self, tok_card, tok_kind, tok_aux, glob, slots, cand, n_cand, return_pooled: bool = False,
                agent=None):
        cand = cand.long()
        B = tok_card.shape[0]
        x, mask = self.encode(tok_card, tok_kind, tok_aux, glob, slots, agent)
        pooled = x[:, 0]

        cand = cand.view(B, self.max_cand, 6)
        verb, card, s1, s2, name, extra = cand.unbind(-1)

        def slot_ref(sl):
            on_board = (sl >= 1) & (sl <= 12)
            idx = torch.where(on_board, sl, torch.zeros_like(sl))
            gathered = x.gather(1, idx[..., None].expand(-1, -1, x.shape[-1]))
            other = self.slot_other(torch.where(on_board, torch.zeros_like(sl), sl))
            return torch.where(on_board[..., None], gathered, other)

        c = (self.verb(verb) + self.card_emb(card) + slot_ref(s1) + slot_ref(s2) + self.name(name)
             + self.extra(extra.clamp(0, 63)))
        c = self.cand_in(c) + pooled[:, None, :]
        c = self.cross(c, x, mask)
        valid = torch.arange(self.max_cand, device=cand.device)[None, :] < n_cand.long().view(B, 1)
        for i, blk in enumerate(self.cand_blocks):
            if i < len(self.cross_extra):
                c = self.cross_extra[i](c, x, mask)
            c = blk(c, valid)
        for blk in self.cross_extra[len(self.cand_blocks):]:
            c = blk(c, x, mask)
        logits = self.score(c).squeeze(-1)
        logits = logits.masked_fill(~valid, -1e9)
        if not self.n_agents:
            value = torch.tanh(self.value(pooled)).squeeze(-1)
        elif agent is None:
            value = torch.tanh(self.value_heads[self.fixed_agent](pooled)).squeeze(-1)
        else:
            per = torch.cat([h(pooled) for h in self.value_heads], dim=-1)          # [B, n_agents]
            value = torch.tanh(per.gather(1, agent.long().view(B, 1))).squeeze(-1)
        return (logits, value, pooled) if return_pooled else (logits, value)

    def config(self) -> dict:
        return dict(self.cfg)


INPUTS = ["tok_card", "tok_kind", "tok_aux", "glob", "slots", "cand", "n_cand"]


def build_token_model(table_file: str, text_file: str, n_names: int, glob_f: int, slot_f: int, max_tok: int,
                      max_cand: int, **kw) -> TokenPointerNet:
    table = json.load(open(table_file, encoding="utf-8"))["cards"]
    return TokenPointerNet(table, np.load(text_file), n_names, glob_f, slot_f, max_tok, max_cand, **kw)


def export_token_onnx(model: TokenPointerNet, path: str) -> None:
    model = model.eval().to("cpu")
    B = 2
    dummy = (torch.zeros(B, model.max_tok, dtype=torch.int16), torch.ones(B, model.max_tok, dtype=torch.uint8),
             torch.zeros(B, model.max_tok, dtype=torch.uint8), torch.zeros(B, model.glob_f, dtype=torch.uint8),
             torch.zeros(B, 12 * model.slot_f, dtype=torch.uint8), torch.zeros(B, model.max_cand * 6, dtype=torch.int16),
             torch.ones(B, dtype=torch.int32))
    axes = {n: {0: "batch"} for n in INPUTS + ["logits", "value"]}
    torch.onnx.export(model, dummy, path, input_names=INPUTS, output_names=["logits", "value"], dynamic_axes=axes,
                      opset_version=17, dynamo=False)
