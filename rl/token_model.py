"""Token + pointer policy-value network (plan item A4.2).

Inputs come from env/tokens.js: card tokens (card id, kind, aux), global and slot features
(bytes, round(48 x)), and one candidate per legal option ([verb, card, slot1, slot2, name, extra]).

  card embedding  = Linear(structured card features) + Linear(rules-text embedding, frozen)
                    + a learned per-card residual (starts at zero), so an unseen card still has
                    a representation from its features and text
  token           = card embedding + kind + aux (+ global / slot features on tokens 0 and 1..12)
  encoder         = pre-LN transformer blocks over the tokens (padding masked); with deck_mode cross the
                    board encoder skips the decklist tokens, which a deck encoder reads, and the board
                    tokens then cross-attend to them
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
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

TYPES = 11
NUM_KINDS = 16
NUM_VERBS = 32
DECK_KINDS = (9, 10)       # env/tokens.js KIND.MY_UNSEEN, KIND.OPP_DECKLIST
HIST_KINDS = (14, 15)      # env/tokens.js KIND.HIST_ME, KIND.HIST_OPP (aux = verb * 8 + turns ago)
SLOT_KIND, UNDER_KIND, ENERGY_KIND, TOOL_KIND = 2, 3, 4, 5      # their aux is a slot (ENERGY: slot * 8 + copies)


def owner_and_count(kind, aux):
    """Per token, the board slot it belongs to (1..12; 0 = none) and its copy count. A SLOT token owns its
    slot; UNDER / ENERGY / TOOL cards are attached to the slot in their aux (ENERGY: aux = slot * 8 +
    copies, env/tokens.js); every other token's aux is its count."""
    attached = (kind == UNDER_KIND) | (kind == TOOL_KIND)
    energy = kind == ENERGY_KIND
    slot = torch.where(energy, torch.div(aux, 8, rounding_mode="floor"), aux)
    owner = torch.where((kind == SLOT_KIND) | attached | energy, (slot + 1).clamp(max=12), torch.zeros_like(aux))
    count = torch.where(energy, aux - 8 * slot, torch.where((kind == SLOT_KIND) | attached, torch.zeros_like(aux), aux))
    return owner, count


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


def attend(q, k, v, mask, bias=None):
    """Attention over the unmasked keys, plus an optional additive bias [B, heads, T, T]. Plain matmuls
    when exporting to ONNX; PyTorch's fused kernel otherwise (same result, much less memory in training)."""
    if torch.onnx.is_in_onnx_export():
        att = (q @ k.transpose(-1, -2)) / math.sqrt(q.shape[-1])
        if bias is not None:
            att = att + bias
        return att.masked_fill(~mask[:, None, None, :], -1e9).softmax(-1) @ v
    if bias is None:
        return F.scaled_dot_product_attention(q, k, v, attn_mask=mask[:, None, None, :])
    full = bias.to(q.dtype).masked_fill(~mask[:, None, None, :], float("-inf"))
    return F.scaled_dot_product_attention(q, k, v, attn_mask=full)


class Block(nn.Module):
    """Pre-LN transformer block; keys masked by `mask` (True = real token)."""

    def __init__(self, d: int, heads: int, ff: int):
        super().__init__()
        self.h = heads
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv = nn.Linear(d, 3 * d)
        self.proj = nn.Linear(d, d)
        self.ff = nn.Sequential(nn.Linear(d, ff), nn.GELU(), nn.Linear(ff, d))

    def forward(self, x, mask, bias=None):
        B, T, d = x.shape
        hd = d // self.h
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, hd).permute(2, 0, 3, 1, 4)
        y = attend(q, k, v, mask, bias).transpose(1, 2).reshape(B, T, d)
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
                 count_features: bool = False, cross_layers: int = 1, cand_self: int = 0, n_agents: int = 0,
                 card_inputs: str = "all", deck_tokens: bool = True, slot_bind: bool = False,
                 ability_text: dict = None, deck_mode: str = "joint", deck_layers: int = 1, history: int = 0,
                 memory: str = "none", value_tower: int = 0, value_query: int = 0, aux_heads: int = 0):
        super().__init__()
        feats = torch.from_numpy(card_feature_matrix(card_table))
        self.register_buffer("card_feats", feats)
        self.register_buffer("text_emb", torch.from_numpy(text_emb.astype(np.float32)))
        n_cards = feats.shape[0]
        self.cfg = dict(kind="TokenPointerNet", n_names=n_names, glob_f=glob_f, slot_f=slot_f, max_tok=max_tok,
                        max_cand=max_cand, d=d, layers=layers, heads=heads, count_features=count_features,
                        cross_layers=cross_layers, cand_self=cand_self, n_agents=n_agents, card_inputs=card_inputs,
                        deck_tokens=deck_tokens, slot_bind=slot_bind, ability_text=ability_text is not None,
                        deck_mode=deck_mode, deck_layers=deck_layers, history=history, memory=memory,
                        value_tower=value_tower, value_query=value_query, aux_heads=aux_heads)
        self.max_tok, self.max_cand, self.glob_f, self.slot_f = max_tok, max_cand, glob_f, slot_f
        self.action_size = max_cand
        # What a card id is read from (the ablations of log #70): "all" structured features + rules text +
        # residual, "feats" no text, "ids" the learned per-card embedding alone (then not zero at the start).
        # deck_tokens=False hides the decklist tokens (MY_UNSEEN, OPP_DECKLIST) from the encoder.
        assert card_inputs in ("all", "feats", "ids")
        self.card_inputs, self.deck_tokens = card_inputs, deck_tokens
        self.card_struct = nn.Linear(feats.shape[1], d) if card_inputs != "ids" else None
        self.card_text = nn.Linear(self.text_emb.shape[1], d) if card_inputs == "all" else None
        self.card_resid = nn.Embedding(n_cards, d)
        if card_inputs == "ids":
            nn.init.normal_(self.card_resid.weight, std=0.02)
        else:
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
        # slot_bind (log #71): a board card is tied to its Pokemon by more than its aux id. Every token gets
        # an embedding of the slot it belongs to, attached Energy its own copy count for the count features,
        # and each encoder layer a learned per-head attention bias between tokens of the same slot (the
        # Pokemon, its pre-evolutions, Energy and Tools), starting at 0.
        self.slot_bind = slot_bind
        if slot_bind:
            self.owner = nn.Embedding(13, d)
            nn.init.normal_(self.owner.weight, std=0.02)
            self.same_bias = nn.Parameter(torch.zeros(layers, heads))
        # deck_mode (log #72): how the decklist tokens (MY_UNSEEN, OPP_DECKLIST) meet the board.
        #   joint       one encoder over the board and deck tokens together (as before)
        #   cross       the board encoder never sees the deck, so its output is a deck-free state; a deck encoder
        #               (deck_layers blocks) reads the deck tokens alone, then one block lets the board tokens
        #               cross-attend to them: the deck-specific state
        #   interleave  as cross, but the board tokens cross-attend to the deck after every board layer
        # The deck stream's token 0 is a learned null key, so a state without deck tokens still has one.
        assert deck_mode in ("joint", "cross", "interleave")
        self.deck_mode = deck_mode
        if deck_mode != "joint":
            self.deck_null = nn.Parameter(torch.zeros(d))
            self.deck_blocks = nn.ModuleList([Block(d, heads, 2 * d) for _ in range(deck_layers)])
            self.fuse = nn.ModuleList([CrossBlock(d, heads, 2 * d) for _ in range(layers if deck_mode == "interleave" else 1)])
        # history (log #76): the action-history tokens (env/tokens.js, workers with history = W) are read, each as
        # its card + kind + an embedding of its verb and of how many turns ago it was; without it they are masked
        # out, so a model without the option ignores them and plays as before.
        self.history = history
        if history:
            self.hist_verb = nn.Embedding(NUM_VERBS, d)
            self.hist_age = nn.Embedding(8, d)
            nn.init.normal_(self.hist_verb.weight, std=0.02)
            nn.init.normal_(self.hist_age.weight, std=0.02)
        # memory (log #76): a recurrent core over the player's own decisions in the game, after the encoder. Its
        # input at each decision is the pooled state (token 0); its output is added to the pooled state that the
        # options and the value read (through mem_out, zero at the start, so it starts as the memoryless pilot).
        #   gru   a GRU; the state carried between decisions is its hidden vector
        #   attn  one causal attention block over the decision's and every earlier decision's pooled state (plus an
        #         embedding of the game turn), so a gradient reaches any earlier decision in one step
        # Training runs whole trajectories (mem_lens), play one decision at a time with the state carried by the
        # inference server (rl/remote.py); not exported to ONNX.
        assert memory in ("none", "gru", "attn")
        self.memory = memory
        if memory != "none":
            self.mem_in = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d))
            if memory == "gru":
                self.mem_gru = nn.GRU(d, d, batch_first=True)
            else:
                self.mem_turn = nn.Embedding(64, d)
                nn.init.normal_(self.mem_turn.weight, std=0.02)
                self.mem_block = Block(d, heads, 2 * d)
            self.mem_out = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d))
            nn.init.zeros_(self.mem_out[-1].weight)
            nn.init.zeros_(self.mem_out[-1].bias)
        # value_tower (log #77): the value reads its own stack of value_tower blocks over the same embedded tokens
        # (the input embeddings are shared, the attention is not), so the value's representation is no longer the
        # policy's; joint deck mode only.
        self.value_tower = value_tower
        if value_tower:
            assert deck_mode == "joint", "value_tower: joint deck mode only"
            self.vblocks = nn.ModuleList([Block(d, heads, 2 * d) for _ in range(value_tower)])
            self.ln_v = nn.LayerNorm(d)
        # value_query (log #77): the value reads the state by cross-attention, as each option does: value_query
        # learned queries, each plus the pooled state, attend to every encoder token (the value tower's, if any)
        # through their own block; the value MLP reads their mean. 0 = the MLP on the pooled token alone.
        self.value_query = value_query
        if value_query:
            self.vquery = nn.Parameter(torch.randn(value_query, d) * 0.02)
            self.vcross = CrossBlock(d, heads, 2 * d)
            for lin in (self.vcross.proj, self.vcross.ff[-1]):      # starts as the identity: the value first reads
                nn.init.zeros_(lin.weight)                          # the pooled token (plus the small queries), so a
                nn.init.zeros_(lin.bias)                            # checkpoint without it keeps its value
        # aux_heads (the lab, log #84; KataGo's auxiliary targets): a small head on the pooled state predicts
        # aux_heads game-general quantities (rl/train.py aux_targets: the decisions left until the game ends, the final
        # result). Not part of forward's outputs, so play, ONNX and inference are unchanged; trained through the shared
        # trunk by PPO's --aux loss, as a denser signal for the representation the value reads.
        self.aux_heads = aux_heads
        if aux_heads:
            self.aux_head = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d), nn.GELU(), nn.Linear(d, aux_heads))
        self.ln_out = nn.LayerNorm(d)
        self.verb = nn.Embedding(NUM_VERBS, d)
        self.name = nn.Embedding(n_names + 1, d)
        # ability_text (log #71): an attack or Power option also gets that ability's own rules text (frozen
        # sentence embedding, rl/card_text.py --abilities), looked up by the option's card and name; the
        # card's text embedding covers the whole card, and the learned name embedding knows nothing of an
        # ability it has not played.
        self.ability_text = ability_text is not None
        if self.ability_text:
            self.register_buffer("ability_emb", torch.from_numpy(ability_text["emb"].astype(np.float32)))
            self.register_buffer("ability_index", torch.from_numpy(ability_text["index"].astype(np.int64)).view(-1))
            self.ability_names = ability_text["index"].shape[1]
            assert self.ability_names == n_names + 1 and ability_text["index"].shape[0] == n_cards
            self.ability_proj = nn.Linear(self.ability_emb.shape[1], d)
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
        e = self.card_resid(ids)
        if self.card_struct is not None:
            e = e + self.card_struct(self.card_feats[ids])
        if self.card_text is not None:
            e = e + self.card_text(self.text_emb[ids])
        return e

    def encode(self, tok_card, tok_kind, tok_aux, glob, slots, agent=None, board_only: bool = False,
               with_value: bool = False):
        """The state's encoded tokens [B, T, d] and their mask [B, T]; token 0 is the pooled state. With
        board_only (deck_mode cross) the board encoder's own output, before any deck reaches it. With with_value
        and a value tower, also the value tower's encoded tokens [B, T, d]."""
        assert not board_only or self.deck_mode == "cross"
        tok_card, tok_kind, tok_aux = tok_card.long(), tok_kind.long(), tok_aux.long()
        B, T = tok_card.shape
        mask = tok_kind > 0
        is_deck = (tok_kind == DECK_KINDS[0]) | (tok_kind == DECK_KINDS[1])
        is_hist = (tok_kind == HIST_KINDS[0]) | (tok_kind == HIST_KINDS[1])
        if not self.deck_tokens:
            mask = mask & ~is_deck
        if not self.history:
            mask = mask & ~is_hist
        aux_in = torch.where(is_hist, torch.zeros_like(tok_aux), tok_aux)     # a history token's aux is not a count
        x = self.card_emb(tok_card) + self.kind(tok_kind) + self.aux(aux_in)
        if self.history:
            hv = torch.div(tok_aux, 8, rounding_mode="floor").clamp(max=NUM_VERBS - 1)
            hist = self.hist_verb(hv) + self.hist_age(tok_aux - 8 * torch.div(tok_aux, 8, rounding_mode="floor"))
            x = x + torch.where(is_hist[..., None], hist, torch.zeros_like(hist))
        same = None
        if self.slot_bind:
            owner, count = owner_and_count(tok_kind, aux_in)
            x = x + self.owner(owner)
            same = ((owner[:, :, None] == owner[:, None, :]) & (owner[:, :, None] > 0)).float()[:, None]   # [B, 1, T, T]
        if self.count_features:
            x = x + self.count_proj(count_features(count if self.slot_bind else aux_in))
        g = self.glob(glob.float() / 48.0)[:, None, :]
        s = self.slot_num(slots.float().view(B, 12, self.slot_f) / 48.0)
        pad = torch.zeros(B, T - 13, x.shape[-1], dtype=x.dtype, device=x.device)
        x = x + torch.cat([g, s, pad], dim=1)
        if self.n_agents:
            if agent is None:
                x = x + self.agent_emb.weight[self.fixed_agent][None, None, :]
            else:
                x = x + self.agent_emb(agent.long())[:, None, :]
        bias = lambda i: None if same is None else same * self.same_bias[i][None, :, None, None]
        if self.deck_mode == "joint":
            x0 = x
            for i, b in enumerate(self.blocks):
                x = b(x, mask, bias(i))
            if with_value and self.value_tower:
                xv = x0
                for b in self.vblocks:
                    xv = b(xv, mask)
                return self.ln_out(x), mask, self.ln_v(xv)
            return self.ln_out(x), mask
        first = (torch.arange(T, device=x.device) == 0)[None, :]
        board_mask, deck_mask = mask & ~is_deck, (mask & is_deck) | first
        dx = torch.where(first[..., None], self.deck_null.to(x.dtype), x)
        for b in self.deck_blocks:
            dx = b(dx, deck_mask)
        for i, b in enumerate(self.blocks):
            x = b(x, board_mask, bias(i))
            if self.deck_mode == "interleave":
                x = self.fuse[i](x, dx, deck_mask)
        if board_only:
            return self.ln_out(x), board_mask
        if self.deck_mode == "cross":
            x = self.fuse[0](x, dx, deck_mask)
        return self.ln_out(torch.where(is_deck[..., None], dx, x)), mask

    def memory_inputs(self, pooled, glob):
        m = self.mem_in(pooled)
        if self.memory == "attn":
            m = m + self.mem_turn(glob[:, 0].long().clamp(max=63))      # glob byte 0 is the game turn (env/tokens.js)
        return m

    def memory_seq(self, m, lens):
        """Memory outputs [B, d] for rows grouped by trajectory in decision order, lens = rows per trajectory."""
        parts = torch.split(m, [int(n) for n in lens])
        P = nn.utils.rnn.pad_sequence(parts, batch_first=True)                       # [n, L, d], padded at the end
        if self.memory == "gru":
            out, _ = self.mem_gru(P)
        else:
            out = self.mem_attend(P, None, causal=True)
        valid = torch.arange(P.shape[1], device=m.device)[None, :] < torch.as_tensor(lens, device=m.device)[:, None]
        return out[valid]

    def mem_attend(self, P, ctx_mask, causal=False):
        """The attention memory block: causal over P [n, L, d], or the last row of P over the rows ctx_mask allows."""
        blk = self.mem_block
        n, L, d = P.shape
        hd = d // blk.h
        q, k, v = blk.qkv(blk.ln1(P)).view(n, L, 3, blk.h, hd).permute(2, 0, 3, 1, 4)
        if causal:
            y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        else:
            y = F.scaled_dot_product_attention(q[:, :, -1:], k, v, attn_mask=ctx_mask[:, None, None, :])
            P = P[:, -1:]
        x = P + blk.proj(y.transpose(1, 2).reshape(n, -1, d))
        x = x + blk.ff(blk.ln2(x))
        return x if causal else x[:, 0]

    def memory_step(self, m, states):
        """One decision per row: states[i] is that row's memory so far (None at its first decision): the GRU's
        hidden vector, or the attention memory's earlier inputs [k, d]. -> (outputs [B, d], new states)."""
        B, d = m.shape
        if self.memory == "gru":
            h0 = torch.stack([torch.zeros(d, device=m.device, dtype=m.dtype) if s is None else s.to(m.dtype) for s in states])
            out, _ = self.mem_gru(m[:, None, :], h0[None])
            out = out[:, 0]
            return out, list(out.detach())
        prev = [torch.zeros(0, d, device=m.device, dtype=m.dtype) if s is None else s.to(m.dtype) for s in states]
        seqs = [torch.cat([p, m[i:i + 1]]) for i, p in enumerate(prev)]
        lens = torch.tensor([len(x) for x in seqs], device=m.device)
        L = int(lens.max())
        # right-aligned, so each row's own decision is last
        P = torch.zeros(B, L, d, device=m.device, dtype=m.dtype)
        for i, x in enumerate(seqs):
            P[i, L - len(x):] = x
        ctx = torch.arange(L, device=m.device)[None, :] >= (L - lens)[:, None]
        out = self.mem_attend(P, ctx)
        return out, [x.detach() for x in seqs]

    def forward(self, tok_card, tok_kind, tok_aux, glob, slots, cand, n_cand, return_pooled: bool = False,
                agent=None, mem_lens=None, mem_states=None):
        """With memory: mem_lens (training: rows grouped by trajectory in decision order, rows per trajectory) or
        mem_states (play: one per row, see memory_step; the new states are returned as a third output)."""
        B = tok_card.shape[0]
        enc = self.encode(tok_card, tok_kind, tok_aux, glob, slots, agent, with_value=True)
        x, mask = enc[0], enc[1]
        vx = enc[2] if len(enc) > 2 else None
        pooled = x[:, 0]
        new_states = None
        if self.memory != "none":
            m = self.memory_inputs(pooled, glob)
            with torch.autocast(device_type=m.device.type, enabled=False):      # the recurrence in float32
                m = m.float()
                if mem_lens is not None:
                    h = self.memory_seq(m, mem_lens)
                else:
                    h, new_states = self.memory_step(m, mem_states if mem_states is not None else [None] * B)
            pooled = pooled + self.mem_out(h)
            x = torch.cat([pooled[:, None].to(x.dtype), x[:, 1:]], 1)
        logits, value = self.heads(x, mask, cand, n_cand, agent, vx)
        if new_states is not None:
            return logits, value, new_states
        return (logits, value, x[:, 0]) if return_pooled else (logits, value)

    def heads(self, x, mask, cand, n_cand, agent=None, vx=None):
        """Policy logits and value from the encoded tokens x (token 0 = the pooled state, with memory if any); the
        value from vx instead when given (the value tower's tokens)."""
        B = x.shape[0]
        pooled = x[:, 0]
        src = x if vx is None else vx.to(x.dtype)
        if self.value_query:
            q = self.vquery[None].to(src.dtype) + src[:, :1]
            vin = self.vcross(q, src, mask).mean(1)
        else:
            vin = src[:, 0]
        cand = cand.long().view(B, -1, 6)               # up to max_cand; the GPU server trims to the batch's longest
        verb, card, s1, s2, name, extra = cand.unbind(-1)

        def slot_ref(sl):
            on_board = (sl >= 1) & (sl <= 12)
            idx = torch.where(on_board, sl, torch.zeros_like(sl))
            gathered = x.gather(1, idx[..., None].expand(-1, -1, x.shape[-1]))
            other = self.slot_other(torch.where(on_board, torch.zeros_like(sl), sl))
            return torch.where(on_board[..., None], gathered, other)

        c = (self.verb(verb) + self.card_emb(card) + slot_ref(s1) + slot_ref(s2) + self.name(name)
             + self.extra(extra.clamp(0, 63)))
        if self.ability_text:
            c = c + self.ability_proj(self.ability_emb[self.ability_index[card * self.ability_names + name]])
        c = self.cand_in(c) + pooled[:, None, :]
        c = self.cross(c, x, mask)
        valid = torch.arange(cand.shape[1], device=cand.device)[None, :] < n_cand.long().view(B, 1)
        for i, blk in enumerate(self.cand_blocks):
            if i < len(self.cross_extra):
                c = self.cross_extra[i](c, x, mask)
            c = blk(c, valid)
        for blk in self.cross_extra[len(self.cand_blocks):]:
            c = blk(c, x, mask)
        logits = self.score(c).squeeze(-1)
        logits = logits.masked_fill(~valid, -1e9)
        if not self.n_agents:
            value = torch.tanh(self.value(vin)).squeeze(-1)
        elif agent is None:
            value = torch.tanh(self.value_heads[self.fixed_agent](vin)).squeeze(-1)
        else:
            per = torch.cat([h(vin) for h in self.value_heads], dim=-1)          # [B, n_agents]
            value = torch.tanh(per.gather(1, agent.long().view(B, 1))).squeeze(-1)
        return logits, value

    def config(self) -> dict:
        return dict(self.cfg)


INPUTS = ["tok_card", "tok_kind", "tok_aux", "glob", "slots", "cand", "n_cand"]


def build_token_model(table_file: str, text_file: str, n_names: int, glob_f: int, slot_f: int, max_tok: int,
                      max_cand: int, **kw) -> TokenPointerNet:
    table = json.load(open(table_file, encoding="utf-8"))["cards"]
    if kw.pop("ability_text", False):
        kw["ability_text"] = dict(np.load(str(Path(text_file).parent / "ability_text.npz")))
    return TokenPointerNet(table, np.load(text_file), n_names, glob_f, slot_f, max_tok, max_cand, **kw)


def export_token_onnx(model: TokenPointerNet, path: str) -> None:
    assert model.memory == "none", "a pilot with memory plays through the inference server only (no ONNX export)"
    model = model.eval().to("cpu")
    B = 2
    dummy = (torch.zeros(B, model.max_tok, dtype=torch.int16), torch.ones(B, model.max_tok, dtype=torch.uint8),
             torch.zeros(B, model.max_tok, dtype=torch.uint8), torch.zeros(B, model.glob_f, dtype=torch.uint8),
             torch.zeros(B, 12 * model.slot_f, dtype=torch.uint8), torch.zeros(B, model.max_cand * 6, dtype=torch.int16),
             torch.ones(B, dtype=torch.int32))
    axes = {n: {0: "batch"} for n in INPUTS + ["logits", "value"]}
    torch.onnx.export(model, dummy, path, input_names=INPUTS, output_names=["logits", "value"], dynamic_axes=axes,
                      opset_version=17, dynamo=False)
