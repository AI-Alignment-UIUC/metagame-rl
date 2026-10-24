"""Checks of the learner-side components (run: .venv/Scripts/python -m rl.tests).

- decks: random decks (rl/decks.py random_deck) are legal, and Pool.removable / Pool.addable agree with
  the construction rules on the field and full pools: every removal they allow, followed by any
  addition they allow, leaves a legal deck, and every legal single-card swap is allowed, except that
  the deck's last Basic Pokémon is never removed (even for another Basic: add one first)
- subset() keeps every kept row's own legal ids and fields (per-agent PPO batches)
- the ONNX export of a TokenPointerNet matches PyTorch, and cutting a batch to its longest state and option
  list (as the GPU server does) changes no output
- prize shaping (rl/train.py shape_rewards): lam = 0 changes nothing; each trajectory's rewards still
  sum to its result; each step gets lam times the change in the prize potential; the same telescoping
  on real rollouts (runs/pilot-v2/rollout_w*.bin, when present)
- the leave-one-out baseline (rl/draft.py rloo)
- the draft head (rl/draft.py): the pre-game state's layout (deck, a free token, opponent's list); every
  draw is legal and makes exactly --swaps replacements; the batched log-probability equals the one
  accumulated while drawing; random_changes (turnover mutants) stays legal; and on a bandit (a draw's
  reward is the share of its incoming cards among 8 targets) REINFORCE moves the incoming mass on the
  targets from ~3% to over 30%
- rl/train.py logging and lr schedule: lr_at's endpoints and clipping, and without --lr-final the optimizer's
  lr is left alone; explained_variance equals the closed form on two trajectories; ending_kinds' PP / PR / RR;
  save_atomic keeps the old file when a save fails; ppo_update's stats equal their closed forms on one step
  (grad_norm the pre-clip norm, kl_last the last epoch's kl), and two seeded calls give identical parameters;
  out of GPU memory mid-minibatch, it redoes the minibatch in micro-batches half the size, with the same step
- search-strength judging (log #148): rl/metagame.py judged_mean, its noise baseline and recent_score (check_judged),
  and rl/remote.py's top-k reply on a fake pool: plain replies unchanged, each row's top K legal options best first,
  chunked forwards alike (check_topk)
"""
import argparse
import contextlib
import copy
import glob
import io
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from rl.decks import Pool, archived_decks, changed, pokemon_overlap, random_deck
from rl.draft import LEAD, MY_UNSEEN, OPPONENT_LIST, SLOT, Drafter, deck_tokens, floor_temperature, random_changes, rloo
from rl.model import IdentityMLP
from rl.rollouts import concat, read_rollout, subset
from rl.token_model import TokenPointerNet, export_token_onnx
from rl.train import (ZERO_AT_GROWTH, advantages, aux_targets, ending_kinds, explained_variance, legal_mask, load_grown, lr_at, ppo_update,
                      remap_adam, save_atomic, schedule_lr, shape_rewards)

PRIZE_GLOB = (6, 22)


def tiny_pilot(table, text, seed=0, n_names=8, layers=2, **kw):
    torch.manual_seed(seed)
    return TokenPointerNet(table, text, n_names=n_names, glob_f=82, slot_f=20, max_tok=128, max_cand=48, d=64, layers=layers,
                           heads=4, count_features=True, **kw).eval()


def check_decks(failures, archived, rng):
    field = sorted({c for _, v in archived for c in Pool().names(v)})
    for name, pool in (("field", Pool(restrict=field)), ("full", Pool())):
        decks = [random_deck(pool, rng) for _ in range(40)]
        bad = sum(not pool.legal(v) for v in decks)
        if bad:
            failures.append(f"{name}: {bad} random decks not legal")
        checked = 0
        for v in [v for _, v in archived[:5]] + decks[:5]:
            rem = pool.removable(v)
            last_basic = v[pool.basic_pokemon].sum() <= 1
            for r in np.nonzero(v)[0]:
                w = v.copy()
                w[r] -= 1
                add = pool.addable(w)
                for a in range(1, pool.n):
                    x = w.copy()
                    x[a] += 1
                    legal = pool.legal(x) and pool.allowed[a]
                    allowed = bool(rem[r] and add[a])
                    if allowed and not legal:
                        failures.append(f"{name}: removing {pool.full_name[r]} and adding {pool.full_name[a]} is allowed but illegal")
                    if legal and not allowed and x[r] != v[r] and not (last_basic and pool.basic_pokemon[r]):
                        failures.append(f"{name}: the legal swap {pool.full_name[r]} -> {pool.full_name[a]} is not allowed")
                    checked += 1
        print(f"{name} pool: 40 random decks, {checked} single-card swaps checked")


def check_subset(failures, rng):
    T = 300
    counts = rng.integers(1, 9, size=T)
    off = np.concatenate([[0], np.cumsum(counts)]).astype(np.int64)
    batch = {"action": rng.integers(0, 8, size=T).astype(np.int32), "adv": rng.normal(size=T).astype(np.float32),
             "slot": rng.integers(0, 4, size=T).astype(np.int32), "legal_offsets": off,
             "legal_ids": rng.integers(0, 48, size=int(off[-1])).astype(np.int32),
             "obs.tokCard": rng.integers(0, 300, size=T * 5).astype(np.int16), "obs.nCand": counts.astype(np.int32),
             "obs": np.zeros((T, 0), np.uint8)}
    idx = np.nonzero(batch["slot"] == 2)[0]
    sub = subset(batch, idx)
    ok = len(sub["action"]) == len(idx) and sub["obs"].shape == (len(idx), 0)
    for r, i in enumerate(idx):
        ok &= np.array_equal(sub["legal_ids"][sub["legal_offsets"][r]:sub["legal_offsets"][r + 1]],
                             batch["legal_ids"][off[i]:off[i + 1]])
        ok &= np.array_equal(sub["obs.tokCard"].reshape(len(idx), 5)[r], batch["obs.tokCard"].reshape(T, 5)[i])
        ok &= sub["adv"][r] == batch["adv"][i] and sub["obs.nCand"][r] == batch["obs.nCand"][i]
    if not ok:
        failures.append("subset() does not keep the rows' own legal ids / fields")
    print(f"subset: {len(idx)} of {T} rows checked")


def check_onnx(failures, m, rng):
    import onnxruntime as ort
    B, T, M = 16, m.max_tok, m.max_cand
    n_cards = m.card_feats.shape[0]
    L = rng.integers(20, T, size=B)
    kind = np.zeros((B, T), np.uint8)
    for b in range(B):
        kind[b, :L[b]] = rng.integers(1, 16 if getattr(m, "history", 0) else 14, size=L[b])
    card = (rng.integers(0, n_cards, size=(B, T)) * (kind > 0)).astype(np.int16)
    aux = (rng.integers(0, 30, size=(B, T)) * (kind > 0)).astype(np.uint8)
    aux = np.where(kind >= 14, rng.integers(0, 184, size=(B, T)), aux).astype(np.uint8)     # history: verb * 8 + age
    glob_ = rng.integers(0, 49, size=(B, m.glob_f)).astype(np.uint8)
    slots = rng.integers(0, 49, size=(B, 12 * m.slot_f)).astype(np.uint8)
    cand = np.stack([rng.integers(0, 32, size=(B, M)), rng.integers(0, n_cards, size=(B, M)),
                     rng.integers(0, 16, size=(B, M)), rng.integers(0, 16, size=(B, M)),
                     rng.integers(0, 9, size=(B, M)), rng.integers(0, 64, size=(B, M))], -1).reshape(B, M * 6).astype(np.int16)
    n_cand = rng.integers(2, M + 1, size=B).astype(np.int32)
    x = [torch.from_numpy(a) for a in (card, kind, aux, glob_, slots, cand, n_cand)]
    with torch.no_grad():
        lt, vt = m(*x)
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "m.onnx")
        export_token_onnx(m, path)
        sess = ort.InferenceSession(path)
        lo, vo = sess.run(None, {i.name: t.numpy() for i, t in zip(sess.get_inputs(), x)})
    if not (np.allclose(lo, lt.numpy(), atol=2e-4) and np.allclose(vo, vt.numpy(), atol=2e-5)):
        failures.append(f"ONNX export differs from PyTorch: logits {np.abs(lo - lt.numpy()).max():.2e}")
    print("onnx: export matches PyTorch")
    L, M = int(L.max()), int(n_cand.max())                  # the GPU server's trim (rl/remote.py)
    with torch.no_grad():
        lc, vc = m(x[0][:, :L], x[1][:, :L], x[2][:, :L], x[3], x[4], x[5][:, :M * 6], x[6])
    valid = np.arange(M)[None, :] < n_cand[:, None]
    if not (np.allclose(lc.numpy()[valid], lt.numpy()[:, :M][valid], atol=1e-4) and np.allclose(vc.numpy(), vt.numpy(), atol=1e-5)):
        failures.append("trimming a batch to its longest state and option list changes the outputs")
    print("trim: outputs unchanged when a batch is cut to its longest state and option list")


def check_ablations(failures, table, text, rng):
    """The pilot ablations of log #70: each variant exports to ONNX, reads cards only from what it is given,
    and with deck_tokens=False its outputs do not depend on the decklist tokens."""
    from rl.token_model import DECK_KINDS
    from rl.token_model import owner_and_count
    o, c = owner_and_count(torch.tensor([[1, 2, 3, 4, 5, 6, 9]]), torch.tensor([[0, 3, 3, 3 * 8 + 2, 7, 4, 2]]))
    if o.tolist() != [[0, 4, 4, 4, 8, 0, 0]] or c.tolist() != [[0, 0, 0, 2, 0, 4, 2]]:
        failures.append(f"owner_and_count: owners {o.tolist()}, counts {c.tolist()}")
    from rl.card_text import ability_texts
    ab = dict(np.load("notes/data/cards/ability_text.npz"))
    names, rows = ability_texts(table)
    for r, (cid, name, txt) in enumerate(rows):          # the lookup finds each card's own ability
        if ab["index"][cid, names.index(name) + 1] != r + 1 and rows[ab["index"][cid, names.index(name) + 1] - 1][2] != txt:
            failures.append(f"ability_text: card {cid} {name} looks up another text")
    for kw in ({"card_inputs": "feats"}, {"card_inputs": "ids"}, {"deck_tokens": False}, {"slot_bind": True},
               {"ability_text": ab, "n_names": len(names)}, {"deck_mode": "cross"}, {"deck_mode": "interleave"},
               {"deck_mode": "cross", "slot_bind": True, "deck_layers": 2}, {"history": 4},
               {"history": 4, "slot_bind": True, "deck_mode": "cross"}, {"value_tower": 2}, {"value_query": 4},
               {"value_query": 2, "value_tower": 1}):
        m = tiny_pilot(table, text, **kw)
        if m.slot_bind:                          # a bias that matters, so the export has to carry it
            with torch.no_grad():
                m.same_bias.normal_(0, 2)
        names = {n.split(".")[0] for n, _ in m.named_parameters()}
        want = {"all": {"card_struct", "card_text"}, "feats": {"card_struct"}, "ids": set()}[m.card_inputs]
        if names & {"card_struct", "card_text"} != want:
            failures.append(f"{kw}: card input layers {sorted(names & {'card_struct', 'card_text'})}")
        n = len(failures)
        check_onnx(failures, m, rng)
        if len(failures) > n:
            failures[-1] += f" ({sorted(kw)})"
    m = tiny_pilot(table, text, deck_tokens=False)
    B, T, M = 8, m.max_tok, m.max_cand
    kind = rng.integers(1, 14, size=(B, T)).astype(np.uint8)
    card = rng.integers(1, m.card_feats.shape[0], size=(B, T)).astype(np.int16)
    aux = rng.integers(0, 30, size=(B, T)).astype(np.uint8)
    rest = [torch.from_numpy(rng.integers(0, 49, size=(B, m.glob_f)).astype(np.uint8)),
            torch.from_numpy(rng.integers(0, 49, size=(B, 12 * m.slot_f)).astype(np.uint8)),
            torch.from_numpy(np.stack([rng.integers(0, 32, size=(B, M)), rng.integers(0, 200, size=(B, M))] +
                                      [rng.integers(0, 9, size=(B, M))] * 4, -1).reshape(B, -1).astype(np.int16)),
            torch.from_numpy(np.full(B, M, np.int32))]
    deck = np.isin(kind, DECK_KINDS)
    card2, aux2 = card.copy(), aux.copy()
    card2[deck] = rng.integers(1, 200, size=deck.sum())
    aux2[deck] = rng.integers(0, 30, size=deck.sum())
    with torch.no_grad():
        a = m(torch.from_numpy(card), torch.from_numpy(kind), torch.from_numpy(aux), *rest)
        b = m(torch.from_numpy(card2), torch.from_numpy(kind), torch.from_numpy(aux2), *rest)
    if not (torch.allclose(a[0], b[0], atol=1e-5) and torch.allclose(a[1], b[1], atol=1e-6)):
        failures.append("deck_tokens=False: outputs change with the decklist tokens")
    # history (log #76): a model without it ignores the history tokens (kinds 14 / 15), one with it reads them.
    hk = rng.integers(1, 16, size=(B, T)).astype(np.uint8)
    hist = hk >= 14
    ha = np.where(hist, rng.integers(0, 184, size=(B, T)), aux).astype(np.uint8)
    hc2, ha2 = card.copy(), ha.copy()
    hc2[hist] = rng.integers(1, 200, size=hist.sum())
    ha2[hist] = rng.integers(0, 184, size=hist.sum())
    for hw, should_change in ((0, False), (4, True)):
        mh = tiny_pilot(table, text, history=hw)
        with torch.no_grad():
            if hw:
                mh.score[-1].weight.normal_(0, 1)          # the heads start at zero: make the logits depend on the input
            a = mh(torch.from_numpy(card), torch.from_numpy(hk), torch.from_numpy(ha), *rest)
            b = mh(torch.from_numpy(hc2), torch.from_numpy(hk), torch.from_numpy(ha2), *rest)
        same = torch.allclose(a[0], b[0], atol=1e-5) and torch.allclose(a[1], b[1], atol=1e-6)
        if same == should_change:
            failures.append(f"history={hw}: outputs {'do not change' if should_change else 'change'} with the history tokens")
    # value_tower (log #77): the policy does not read the value tower, the value does.
    mv = tiny_pilot(table, text, value_tower=2)
    with torch.no_grad():
        mv.value[-1].weight.normal_(0, 1)
        mv.score[-1].weight.normal_(0, 1)
        args_v = (torch.from_numpy(card), torch.from_numpy(kind), torch.from_numpy(aux), *rest)
        a = mv(*args_v)
        for prm in mv.vblocks.parameters():
            prm.add_(torch.randn_like(prm))
        b = mv(*args_v)
    if not torch.allclose(a[0], b[0], atol=1e-5) or torch.allclose(a[1], b[1], atol=1e-4):
        failures.append("value_tower: the policy reads the value tower, or the value does not")
    mq = tiny_pilot(table, text, value_query=4)
    with torch.no_grad():
        mq.value[-1].weight.normal_(0, 1)
        mq.vcross.proj.weight.normal_(0, 0.5)                 # starts as the identity; make the attention count
        a = mq(*args_v)
        mq.vcross.kv.weight.add_(torch.randn_like(mq.vcross.kv.weight))
        b = mq(*args_v)
    if not torch.allclose(a[0], b[0], atol=1e-5) or torch.allclose(a[1], b[1], atol=1e-4):
        failures.append("value_query: the policy reads the value's cross-attention, or the value does not")
    print("value tower: the policy ignores it, the value reads it; value cross-attention likewise")
    # memory (log #76): a trajectory run whole in training (mem_lens) gives the outputs of the same decisions played
    # one at a time with the state carried (memory_step); the loss at a trajectory's last decision has a gradient
    # at its first decision's state.
    for kind_ in ("gru", "attn"):
        mm = tiny_pilot(table, text, memory=kind_)
        with torch.no_grad():
            mm.mem_out[-1].weight.normal_(0, 0.5)
            mm.score[-1].weight.normal_(0, 1)
            mm.value[-1].weight.normal_(0, 1)
        lens = [3, 1, 4]
        xs = [torch.from_numpy(a) for a in (card[:8], kind[:8], aux[:8])] + [r[:8] for r in rest]
        with torch.no_grad():
            ls, vs = mm(*xs, mem_lens=lens)
            states, ld, vd = [None] * 3, [], []
            for step in range(max(lens)):
                rr = [s0 + step for s0, n in zip(np.cumsum([0] + lens[:-1]), lens) if step < n]
                tr = [t for t, n in enumerate(lens) if step < n]
                out = mm(*[x[rr] for x in xs], mem_states=[states[t] for t in tr])
                for q, t in enumerate(tr):
                    states[t] = out[2][q]
                ld.append((rr, out[0])); vd.append((rr, out[1]))
        lstep, vstep = torch.zeros_like(ls), torch.zeros_like(vs)
        for (rr, l), (_, v) in zip(ld, vd):
            lstep[rr], vstep[rr] = l, v
        if not (torch.allclose(ls, lstep, atol=1e-4) and torch.allclose(vs, vstep, atol=1e-5)):
            failures.append(f"memory {kind_}: whole-trajectory outputs differ from step-by-step play "
                            f"({(ls - lstep).abs().max():.2e})")
        x0, msk = mm.encode(*xs[:5])
        e = mm.memory_inputs(x0[:, 0], xs[3]).detach().requires_grad_()
        h = mm.memory_seq(e, lens)
        h[2].sum().backward()                                # trajectory 0's last decision
        if not (e.grad[0].abs().sum() > 0 and e.grad[3:].abs().sum() == 0):
            failures.append(f"memory {kind_}: gradient does not reach the first decision, or leaks across trajectories")
    print("memory: gru and attn give the same outputs whole-trajectory and step by step; gradients reach back "
          "within a trajectory only")
    # deck_mode cross (log #72): the board encoder's output does not depend on the decklist tokens, the
    # fused output does, and a state with no decklist tokens at all still gives finite outputs (the null key).
    m = tiny_pilot(table, text, deck_mode="cross")
    with torch.no_grad():
        m.deck_null.normal_(0, 1)
        args = lambda c, a, k=kind: (torch.from_numpy(c), torch.from_numpy(k), torch.from_numpy(a), *rest[:2])
        (xa, bm), (xb, _) = m.encode(*args(card, aux), board_only=True), m.encode(*args(card2, aux2), board_only=True)
        fa, fb = m.encode(*args(card, aux))[0], m.encode(*args(card2, aux2))[0]     # the heads start at zero
        nodeck = m(*args(card, aux, np.where(deck, 6, kind).astype(np.uint8)), *rest[2:])
    if not torch.allclose(xa[bm], xb[bm], atol=1e-5):
        failures.append("deck_mode cross: the board encoder's output changes with the decklist tokens")
    if torch.allclose(fa[bm], fb[bm], atol=1e-4):
        failures.append("deck_mode cross: the fused board tokens ignore the decklist tokens")
    if not all(torch.isfinite(t).all() for t in nodeck):
        failures.append("deck_mode cross: a state without decklist tokens gives non-finite outputs")
    print(f"history: {int(hist.sum())} history tokens changed: ignored without the option, read with it")
    print(f"ablations: card inputs feats / ids, hidden decklists, slot binding, ability text, deck modes and history export; "
          f"{len(rows)} abilities look up their own text; {int(deck.sum())} decklist tokens changed: hidden-decklist "
          f"outputs and the cross board encoder unchanged, the fused board tokens changed")


def check_shaping(failures, rng):
    # Three interleaved trajectories; prizes left are written into the glob bytes (8 per prize).
    trajs = {0: 9, 1: 7, 2: 5}
    order = rng.permutation(np.repeat(list(trajs), list(trajs.values())))
    T = len(order)
    g = np.zeros((T, 82), np.uint8)
    reward = np.zeros(T, np.float32)
    done = np.zeros(T, np.uint8)
    result = {0: 1.0, 1: -1.0, 2: 0.0}
    left = {k: [6, 6] for k in trajs}
    seen = {k: 0 for k in trajs}
    for t, k in enumerate(order):
        if seen[k] and rng.random() < 0.4:
            left[k][int(rng.integers(2))] -= 1
        g[t, PRIZE_GLOB[0]], g[t, PRIZE_GLOB[1]] = 8 * left[k][0], 8 * left[k][1]
        seen[k] += 1
        if seen[k] == trajs[k]:
            done[t], reward[t] = 1, result[k]
    r = {"reward": reward, "done": done, "traj": order.astype(np.int64), "obs.glob": g.reshape(-1)}
    if not np.array_equal(shape_rewards(r, 0.0, PRIZE_GLOB), reward):
        failures.append("shaping with lam = 0 changes the rewards")
    lam = 0.5
    s = shape_rewards(r, lam, PRIZE_GLOB)
    phi = lam * (g[:, PRIZE_GLOB[1]].astype(float) - g[:, PRIZE_GLOB[0]]) / 48
    for k in trajs:
        i = np.nonzero(order == k)[0]
        if not np.isclose(s[i].sum(), result[k] - phi[i[0]], atol=1e-6):
            failures.append(f"shaping: trajectory {k} sums to {s[i].sum():.4f}, not {result[k]}")
        want = np.append(phi[i[1:]] - phi[i[:-1]], result[k] - phi[i[-1]])
        if not np.allclose(s[i], want, atol=1e-6):
            failures.append(f"shaping: trajectory {k}'s steps are not lam x the potential's change")
    files = sorted(glob.glob("runs/pilot-v2/rollout_w*.bin"))
    if files:
        b = concat([read_rollout(f) for f in files])
        s = shape_rewards(b, 0.5, PRIZE_GLOB)
        gb = b["obs.glob"].reshape(len(s), -1).astype(float)
        phi = 0.5 * (gb[:, PRIZE_GLOB[1]] - gb[:, PRIZE_GLOB[0]]) / 48
        tr = b["traj"]
        first = np.unique(tr, return_index=True)[1]
        raw = np.bincount(np.unique(tr, return_inverse=True)[1], weights=b["reward"])
        new = np.bincount(np.unique(tr, return_inverse=True)[1], weights=s)
        if not np.allclose(new, raw - phi[first], atol=1e-5):
            failures.append("shaping: real trajectories do not telescope")
        print(f"shaping: synthetic ok; {len(first)} real trajectories telescope, "
              f"potential 0 at the first decision in {int((phi[first] == 0).sum())}")
    else:
        print("shaping: synthetic ok (no pilot-v2 rollouts here)")


def check_rloo(failures):
    a = rloo(np.array([1.0, 0.0, 1.0, 0.5, 0.0]), np.array([0, 0, 0, 1, 2]))
    want = np.array([1 - 0.5, 0 - 1.0, 1 - 0.5, 0.0, 0.0])
    if not np.allclose(a, want):
        failures.append(f"rloo gives {a}, not {want}")
    print("rloo: ok")


def check_draft(failures, table, text, archived, rng):
    pool = Pool()
    card, kind, aux = deck_tokens(np.array([5, 9]), np.array([3, 57]), LEAD + 5, np.array([7]), np.array([60]))
    if not (kind[0] == 1 and (kind[1:LEAD] == SLOT).all() and list(aux[1:LEAD]) == list(range(12))
            and list(card[LEAD:LEAD + 2]) == [5, 9] and list(aux[LEAD:LEAD + 2]) == [3, 57]
            and (kind[LEAD:LEAD + 2] == MY_UNSEEN).all() and kind[LEAD + 2] == 0
            and card[LEAD + 3] == 7 and kind[LEAD + 3] == OPPONENT_LIST and aux[LEAD + 3] == 60 and kind[-1] == 0):
        failures.append("deck_tokens: wrong layout")
    bad = sum(changed(random_changes(pool, v, 10, rng), v) > 10 for _, v in archived[:10])
    if bad:
        failures.append(f"random_changes: {bad} decks changed by more than 10 cards")
    pilot = tiny_pilot(table, text)
    dr = Drafter(pool, 64, 4, swaps=3, lr=1e-3, device="cpu")
    field = [archived[5][1], random_deck(pool, rng)]
    gaps, n, wrong = [], 0, 0
    for v in [v for _, v in archived[:2]] + [random_deck(pool, rng) for _ in range(2)]:
        vw = dr.view(pilot, v, field)
        samples = [dr.sample(vw, rng) for _ in range(125)]
        n += len(samples)
        lp = dr.log_prob(vw, samples)[0]
        gaps.append(np.abs(lp.detach().numpy() - np.array([s["logp"] for s in samples])).max())
        wrong += sum(len(s["ev_c"]) != 3 or changed(s["deck"], v) > 3 for s in samples)
    if max(gaps) > 1e-3:
        failures.append(f"draft: batched log-prob differs from the drawn one by {max(gaps):.2e}")
    if wrong:
        failures.append(f"draft: {wrong} draws do not make exactly 3 replacements")
    print(f"draft: {n} draws legal, 3 replacements each, log-prob gap {max(gaps):.1e}")
    # group changes (log #127): every change takes all of the card's remaining copies the copy limit lets in; the draws
    # stay legal (sample asserts it), the log-prob stays exact, and they change more than one card per change
    gr = Drafter(pool, 64, 4, swaps=3, lr=1e-3, device="cpu", group_p=1.0)
    gaps, sizes = [], []
    for v in [v for _, v in archived[:2]] + [random_deck(pool, rng) for _ in range(2)]:
        vw = gr.view(pilot, v, field)
        samples = [gr.sample(vw, rng) for _ in range(125)]
        with torch.no_grad():
            lp = gr.log_prob(vw, samples)[0]
        gaps.append(np.abs(lp.numpy() - np.array([s["logp"] for s in samples])).max())
        sizes += [changed(s["deck"], v) for s in samples]
    if max(gaps) > 1e-3 or np.mean(sizes) <= 3.5:
        failures.append(f"draft groups: log-prob gap {max(gaps):.1e}, {np.mean(sizes):.2f} cards changed a draw (want > 3.5)")
    print(f"draft groups: {len(sizes)} draws legal, {np.mean(sizes):.2f} cards changed a draw by 3 changes, "
          f"log-prob gap {max(gaps):.1e}")

    # Bandit: a draw pays the share of its incoming cards that are among 8 targets.
    v = archived[0][1]
    dr = Drafter(pool, 64, 4, swaps=3, lr=3e-3, device="cpu")
    vw = dr.view(pilot, v, field)
    cands = np.nonzero(pool.allowed & ~pool.basic_energy)[0]
    target = set(int(c) for c in rng.choice(cands[cands > 0], 8, replace=False))

    def mass():
        base = vw.base.numpy()
        x = np.where(base, vw.logits, -np.inf)
        q = np.exp(x - x.max(1, keepdims=True))
        q /= q.sum(1, keepdims=True)
        return float(q[:, sorted(target)].sum(1).mean())
    m0 = mass()
    for _ in range(200):
        samples = [dr.sample(vw, rng) for _ in range(64)]
        z = np.array([np.mean([c in target for c in s["ev_c"]]) for s in samples])
        st = dr.update([(vw, samples, rloo(z, np.zeros(len(z))))], beta=0.0)
    m1 = mass()
    if not (m0 < 0.06 and m1 > 0.30):
        failures.append(f"draft bandit: target mass {m0:.3f} -> {m1:.3f}, not ~0.03 -> over 0.30")
    # the same bandit with a floor of 2 nats on the incoming choice (log #109): every choice is drawn with entropy >= 2,
    # a draw's log-prob is the one the update uses, and the head still learns the targets
    fl = Drafter(pool, 64, 4, swaps=3, lr=3e-3, device="cpu", h_in_floor=2.0)
    vf = fl.view(pilot, v, field)
    zs, gap = [], 0.0
    for i in range(200):
        samples = [fl.sample(vf, rng) for _ in range(64)]
        if i in (0, 199):
            with torch.no_grad():
                gap = max(gap, float(np.abs(fl.log_prob(vf, samples)[0].numpy() - [s["logp"] for s in samples]).max()))
        z = np.array([np.mean([c in target for c in s["ev_c"]]) for s in samples])
        zs.append(z.mean())
        sf = fl.update([(vf, samples, rloo(z, np.zeros(len(z))))], beta=0.0)
    hs = []
    for j in range(len(vf.ids)):
        x = np.where(vf.base[j].numpy(), vf.logits[j], -np.inf)
        y = (x - x.max()) / floor_temperature(x, 2.0)
        q = np.exp(y[np.isfinite(y)])
        q /= q.sum()
        hs.append(float(-(q * np.log(np.maximum(q, 1e-300))).sum()))
    if not (min(hs) >= 2.0 - 1e-3 and gap < 1e-3 and np.mean(zs[-20:]) > 0.3):
        failures.append(f"draft floor: drawn entropy min {min(hs):.3f} (floor 2), log-prob gap {gap:.1e}, "
                        f"target share {np.mean(zs[-20:]):.2f} at the end")
    print(f"draft bandit: incoming mass on 8 target cards {m0:.3f} -> {m1:.3f} in 200 steps, incoming entropy "
          f"{st['h_in']:.2f}; with a 2-nat floor: drawn entropy >= {min(hs):.2f}, head's own {sf['h_in']:.2f}, "
          f"targets {np.mean(zs[-20:]):.2f} of the draws, log-prob gap {gap:.1e}")
    # the features base measure (H110's Nf, log #193): q0's mean entropy is the target, a draw's log-prob is still the
    # one the update uses, the floor holds as KL(q || q0) <= log(legal) - floor, and the head still learns the targets
    nf = Drafter(pool, 64, 4, swaps=3, lr=3e-3, device="cpu", h_in_floor=2.0, group_p=0.3, base="features", base_ent=2.5)
    vn = nf.view(pilot, v, field)
    lq0 = torch.log_softmax(vn.b0.masked_fill(~vn.base, -1e9), 1)
    hq0 = float((-(lq0.exp() * lq0).masked_fill(~vn.base, 0).sum(1)).mean())
    zs, gap = [], 0.0
    for i in range(200):
        samples = [nf.sample(vn, rng) for _ in range(64)]
        if i in (0, 199):
            with torch.no_grad():
                gap = max(gap, float(np.abs(nf.log_prob(vn, samples)[0].numpy() - [s["logp"] for s in samples]).max()))
        z = np.array([np.mean([c in target for c in s["ev_c"]]) for s in samples])
        zs.append(z.mean())
        sn = nf.update([(vn, samples, rloo(z, np.zeros(len(z))))], beta=0.0)
    kls = []
    for j in range(len(vn.ids)):
        x = np.where(vn.base[j].numpy(), vn.logits[j], -np.inf)
        b = vn.b0np[j]
        y = b + x / floor_temperature(x, 2.0, b)
        f = np.isfinite(y)
        q = np.exp(y[f] - y[f].max())
        q /= q.sum()
        p0 = np.exp(b[f] - b[f].max())
        p0 /= p0.sum()
        kls.append(float((q * np.log(np.maximum(q, 1e-300) / p0)).sum()) - (np.log(f.sum()) - 2.0))
    if not (abs(hq0 - 2.5) < 0.01 and gap < 1e-3 and max(kls) <= 1e-3 and np.mean(zs[-20:]) > np.mean(zs[:20]) + 0.1):
        failures.append(f"draft base: q0 entropy {hq0:.3f} (want 2.5), log-prob gap {gap:.1e}, KL over the floor's "
                        f"budget by {max(kls):.3f}, targets {np.mean(zs[:20]):.2f} -> {np.mean(zs[-20:]):.2f}")
    print(f"draft base (features): q0 mean entropy {hq0:.3f} (target 2.5), log-prob gap {gap:.1e}, KL within the floor's "
          f"budget ({max(kls):+.1e}), kl_in {sn['kl_in']:.2f}, targets {np.mean(zs[:20]):.2f} -> {np.mean(zs[-20:]):.2f}")


def check_train(failures, rng):
    # lr schedule: held before the start and after the end, linear between; end defaults to the last iteration
    a = argparse.Namespace(lr=3e-4, lr_final=3e-5, lr_decay_start=80, lr_decay_end=219, iterations=220)
    b = argparse.Namespace(lr=1e-3, lr_final=0.0, lr_decay_start=0, lr_decay_end=None, iterations=101)
    for ar, want in ((a, {0: 3e-4, 80: 3e-4, 150: 3e-4 + (3e-5 - 3e-4) * 70 / 139, 219: 3e-5, 400: 3e-5}),
                     (b, {0: 1e-3, 50: 5e-4, 100: 0.0, 200: 0.0})):
        got = {i: lr_at(i, ar) for i in want}
        if not all(np.isclose(got[i], w, rtol=1e-12, atol=0) for i, w in want.items()):
            failures.append(f"lr_at: {got}, not {want}")
    opt = torch.optim.Adam([torch.nn.Parameter(torch.zeros(2))], lr=1.234e-4)     # e.g. a resumed optimizer
    schedule_lr(opt, 150, argparse.Namespace(**{**vars(a), "lr_final": None}))
    if opt.param_groups[0]["lr"] != 1.234e-4:
        failures.append("schedule_lr: without --lr-final it changes the optimizer's lr")
    schedule_lr(opt, 150, a)
    if opt.param_groups[0]["lr"] != lr_at(150, a):
        failures.append("schedule_lr: with --lr-final the lr is not lr_at")

    # Explained variance: trajectory 0 at t = 0, 2, 3 (rewards 0.25, 0, 1), trajectory 1 at t = 1, 4 (0, -1).
    g = np.zeros((5, 82), np.uint8)
    g[:, 0] = [1, 2, 5, 7, 3]                       # game turn
    r = {"action": np.zeros(5, np.int32), "traj": np.array([0, 1, 0, 0, 1]), "done": np.array([0, 0, 0, 1, 1], np.uint8),
         "reward": np.array([0.25, 0, 0, 1, -1], np.float32), "value": np.array([0.5, -0.2, 0.9, 0.7, -0.6], np.float32),
         "obs.glob": g.reshape(-1)}
    G, v = np.array([1.25, -1, 1, 1, -1]), r["value"].astype(float)
    early = np.array([0, 1, 4])
    ev = (1 - np.var(G - v) / np.var(G), 1 - np.var(G[early] - v[early]) / np.var(G[early]))
    got = explained_variance(r)
    if not (None not in got and np.allclose(got, ev, atol=1e-6)):
        failures.append(f"explained_variance: {got}, not {ev}")
    late = {**r, "obs.glob": np.where(np.arange(82) == 0, 9, g).astype(np.uint8).reshape(-1)}
    none = [explained_variance({**r, "reward": np.zeros(5, np.float32)}), explained_variance(late)[1:],
            explained_variance({k: x for k, x in r.items() if k != "obs.glob"})[1:],
            explained_variance({k: x[:0] for k, x in r.items()})]
    if any(x is not None for t in none for x in t):
        failures.append(f"explained_variance: {none}, not None where undefined")

    games = [{"decks": ["rnd3", "rnd7"], "ending": "deck-out", "steps": 100},
             {"decks": ["rnd1", "Haymaker"], "ending": "prizes", "steps": 200},
             {"decks": ["Haymaker", "rnd2"], "ending": None, "steps": 5000},
             {"decks": ["Haymaker", "Rain Dance"], "ending": None, "steps": 10, "error": "boom"},
             {"decks": ["15+ #2 William Lieu", "brnd"], "ending": "no-pokemon", "steps": 50},
             {"ending": "deck-out", "steps": 30}]
    want = {"PP": {"games": 3, "endings": {"none": 1, "no-pokemon": 1, "deck-out": 1}, "steps": 30.0, "errors": 1, "cut": 0},
            "PR": {"games": 2, "endings": {"prizes": 1, "none": 1}, "steps": 2600.0, "errors": 0, "cut": 1},
            "RR": {"games": 1, "endings": {"deck-out": 1}, "steps": 100.0, "errors": 0, "cut": 0}}
    if ending_kinds(games) != want:
        failures.append(f"ending_kinds: {ending_kinds(games)}")

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "checkpoint.pt"
        save_atomic({"it": 1}, p)
        save_atomic({"it": 2}, p)
        try:
            save_atomic({"it": 3, "f": lambda: 0}, p)          # fails while writing
        except Exception:
            pass
        if torch.load(p)["it"] != 2 or sorted(f.name for f in Path(tmp).glob("*.pt")) != ["checkpoint.pt"]:
            failures.append("save_atomic: a failed save does not leave the previous file intact")

    # PPO on a tiny batch whose old log-probs and values are the net's own, shifted.
    T, O, A = 256, 24, 12
    counts = rng.integers(1, A + 1, size=T)
    off = np.concatenate([[0], np.cumsum(counts)]).astype(np.int64)
    ids = np.concatenate([rng.choice(A, c, replace=False) for c in counts]).astype(np.int32)
    act = np.array([ids[off[t] + rng.integers(counts[t])] for t in range(T)], np.int32)
    obs = rng.integers(0, 49, size=(T, O)).astype(np.uint8)
    torch.manual_seed(3)
    net = IdentityMLP(O, A, 32, 2)
    with torch.no_grad():
        net.policy.weight.normal_(0, 0.3)
        net.value.weight.normal_(0, 0.3)
    mask = legal_mask(torch.arange(T), torch.from_numpy(off), torch.from_numpy(ids.astype(np.int64)), A)

    def policy(m):
        with torch.no_grad():
            logits, val = m(torch.from_numpy(obs))
            lp_all = F.log_softmax(logits.masked_fill(~mask, -1e9), -1)
        return lp_all, lp_all.gather(1, torch.from_numpy(act.astype(np.int64))[:, None]).squeeze(1), val
    lp_all, lp, val = policy(net)
    delta = torch.from_numpy(rng.normal(0, 0.15, size=T).astype(np.float32))
    old_v = val + torch.from_numpy(rng.normal(0, 0.3, size=T).astype(np.float32))
    adv = torch.from_numpy(rng.normal(size=T).astype(np.float32))
    ret = torch.from_numpy(rng.uniform(-1, 1, size=T).astype(np.float32))
    batch = {"action": act, "logp": (lp + delta).numpy(), "value": old_v.numpy(), "adv": adv.numpy(), "ret": ret.numpy(),
             "legal_offsets": off, "legal_ids": ids, "inputs": [obs]}

    def run(lr=0.05, adam=False, seed=11, **kw):
        m = copy.deepcopy(net)
        o = torch.optim.Adam(m.parameters(), lr=lr, eps=1e-5) if adam else torch.optim.SGD(m.parameters(), lr=lr)
        ar = argparse.Namespace(**{"model": "identity", "epochs": 1, "minibatch": T, "micro_batch": 0, "amp": False,
                                   "clip": 0.2, "vf": 0.5, "ent": 0.01, "max_grad_norm": 1e9, **kw})
        torch.manual_seed(seed)
        return m, ppo_update(m, o, batch, ar, "cpu")

    def step(m, lr=0.05):
        return float(sum(((p - q) ** 2).sum() for p, q in zip(m.state_dict().values(), net.state_dict().values()))) ** 0.5 / lr
    ratio, an = (-delta).exp(), (adv - adv.mean()) / (adv.std() + 1e-8)
    want = {"pi_loss": -torch.min(ratio * an, ratio.clamp(0.8, 1.2) * an).mean(),
            "v_loss": torch.max((val - ret) ** 2, (old_v + (val - old_v).clamp(-0.2, 0.2) - ret) ** 2).mean(),
            "entropy": -(lp_all.exp() * lp_all).masked_fill(~mask, 0.0).sum(-1).mean(),
            "kl": delta.mean(), "clipfrac": ((ratio - 1).abs() > 0.2).float().mean()}
    m1, s1 = run()                                  # one SGD step: the step is lr x the gradient
    m2, s2 = run(max_grad_norm=0.1 * s1["grad_norm"])
    m3, s3 = run(epochs=2)
    kl2 = float((torch.from_numpy(batch["logp"]) - policy(m1)[1]).mean())
    bad = [k for k, w in want.items() if not np.isclose(s1[k], float(w), atol=1e-4)]
    if bad:
        failures.append(f"ppo_update: {bad} differ from the closed form: {s1} vs {want}")
    if not (np.isclose(s1["grad_norm"], step(m1), rtol=1e-3) and s1["kl_last"] == s1["kl"]):
        failures.append(f"ppo_update: grad_norm {s1['grad_norm']} vs step {step(m1)}, kl_last {s1['kl_last']} vs kl {s1['kl']}")
    if not (np.isclose(s2["grad_norm"], s1["grad_norm"], rtol=1e-6) and np.isclose(step(m2), 0.1 * s1["grad_norm"], rtol=1e-3)):
        failures.append(f"ppo_update: clipped grad_norm {s2['grad_norm']} (step {step(m2)}), not the pre-clip {s1['grad_norm']}")
    if not (np.isclose(s3["kl_last"], kl2, atol=1e-5) and np.isclose(s3["kl"], (s1["kl"] + kl2) / 2, atol=1e-5)):
        failures.append(f"ppo_update: two epochs give kl_last {s3['kl_last']}, kl {s3['kl']}; want {kl2}, {(s1['kl'] + kl2) / 2}")
    (ma, sa), (mb, sb) = [run(lr=3e-3, adam=True, epochs=3, minibatch=64, micro_batch=16) for _ in range(2)]
    if set(sa) != set(want) | {"grad_norm", "kl_last"} or not (np.isfinite(sa["grad_norm"]) and sa["grad_norm"] > 0
                                                               and np.isfinite(sa["kl_last"])):
        failures.append(f"ppo_update: stats {sa}")
    if sa != sb or not all(torch.equal(p, q) for p, q in zip(ma.parameters(), mb.parameters())):
        failures.append("ppo_update: two seeded calls differ")
    # Expert iteration (--distill, log #96): with search targets on a quarter of the rows the stats give the cross-entropy
    # before the step, the step lowers it, and at weight 0 the targets change nothing.
    st = np.full(T, -1, np.int32)
    rows = np.arange(0, T, 4)
    st[rows] = [ids[off[t] + (t % counts[t])] for t in rows]
    pick = (torch.from_numpy(rows), torch.from_numpy(st[rows].astype(np.int64)))
    ce0 = float(-lp_all[pick].mean())
    batch["search_target"] = st
    md, sd = run(distill=5.0)
    m0, s0 = run(distill=0.0)
    del batch["search_target"]
    ce1 = float(-policy(md)[0][pick].mean())
    if not (np.isclose(sd["distill"], ce0, atol=1e-4) and ce1 < ce0 and "distill" not in s0
            and all(torch.equal(p, q) for p, q in zip(m0.parameters(), m1.parameters()))):
        failures.append(f"ppo_update distill: stats {sd.get('distill')} vs {ce0}, after the step {ce1}; weight 0 {s0}")
    # Mostly greedy collection (--explore, log #81): only the sampled decisions enter the policy terms, with the
    # advantage normalized over them; all ones changes nothing; micro-batches give the same step.
    smp = (np.arange(T) % 3 == 0).astype(np.uint8)
    k = torch.from_numpy(smp.astype(bool))
    an4 = (adv - adv[k].mean()) / (adv[k].std() + 1e-8)
    want4 = {**want, "pi_loss": -torch.min(ratio * an4, ratio.clamp(0.8, 1.2) * an4)[k].mean(), "kl": delta[k].mean(),
             "clipfrac": ((ratio - 1).abs() > 0.2)[k].float().mean()}
    batch["sampled"] = smp
    m4, s4 = run()
    m4b, _ = run(micro_batch=T // 4)
    batch["sampled"] = np.ones(T, np.uint8)
    _, s5 = run()
    del batch["sampled"]
    bad = [q for q, w in want4.items() if not np.isclose(s4[q], float(w), atol=1e-4)]
    if bad:
        failures.append(f"ppo_update with sampled: {bad} differ from the closed form: {s4} vs {want4}")
    if not all(np.isclose(s5[q], s1[q], atol=1e-6) for q in want):
        failures.append(f"ppo_update: sampled all ones gives {s5}, without it {s1}")
    if not all(torch.allclose(p, q, atol=1e-6) for p, q in zip(m4.parameters(), m4b.parameters())):
        failures.append("ppo_update with sampled: micro-batches change the step")
    # Out of GPU memory (log #121) in a minibatch's second micro-batch, after the first one's gradient is in .grad: the
    # minibatch is redone from zero in micro-batches half the size, kept for the next epoch, the step of that size.
    calls = []

    def tight(mod, inp):
        calls.append(len(inp[0]))
        if calls == [T // 2, T // 2]:
            raise torch.cuda.OutOfMemoryError("test")
    hook = net.register_forward_pre_hook(tight)
    try:
        m6, s6 = run(epochs=2, micro_batch=T // 2)
    finally:
        hook.remove()
    m6b, s6b = run(epochs=2, micro_batch=T // 4)
    if calls != [T // 2, T // 2] + [T // 4] * 8 or not all(np.isclose(s6[q], s6b[q], atol=1e-6) for q in s6b) \
            or not all(torch.allclose(p, q, atol=1e-6) for p, q in zip(m6.parameters(), m6b.parameters())):
        failures.append(f"ppo_update out of memory: calls {calls}, stats {s6} vs {s6b}")
    print(f"train: lr_at, explained_variance ({ev[0]:.4f}, {ev[1]:.4f}), ending_kinds, save_atomic ok; ppo_update "
          f"stats match the closed form, grad_norm {s1['grad_norm']:.4f} = step {step(m1):.4f}, kl_last {s3['kl_last']:.5f}")


def check_lab(failures, table, text, rng):
    """rl/lab.py: the sequential test's statistic, the pair scores, growing a pilot, Adam's state by name, the shares."""
    import subprocess
    from rl import lab
    # llr against the normal log-likelihood ratio computed directly; its sign and growth under each hypothesis
    x = np.clip(rng.normal(0.55, 0.2, 400), 0, 1)
    s0, s1, var = lab.expected_score(0.0), lab.expected_score(15.0), x.var(ddof=1)
    direct = float((((x - s0) ** 2 - (x - s1) ** 2) / (2 * var)).sum())
    if not np.isclose(lab.llr(x, 0.0, 15.0), direct, rtol=1e-9):
        failures.append(f"lab.llr {lab.llr(x, 0.0, 15.0)} vs direct {direct}")
    up = [lab.llr(np.clip(rng.normal(s1, 0.2, n), 0, 1), 0.0, 15.0) for n in (5000, 50000)]
    down = [lab.llr(np.clip(rng.normal(s0, 0.2, n), 0, 1), 0.0, 15.0) for n in (5000, 50000)]
    if not (0 < up[0] < up[1] and down[1] < down[0] < 0):
        failures.append(f"lab.llr under H1 {up}, under H0 {down}")
    if not all(abs(lab.elo_of(lab.expected_score(e)) - e) < 1e-6 for e in (-200.0, -15.0, 0.0, 30.0)):
        failures.append("lab.elo_of is not the inverse of expected_score")
    lo, hi = lab.bounds(0.05, 0.05)
    if not (np.isclose(lo, -2.944, atol=1e-3) and np.isclose(hi, 2.944, atol=1e-3)):
        failures.append(f"lab.bounds {lo}, {hi}")
    # pair scores: n = 3 decks; A wins both games on 0 against B on 1, B on 0 wins one of two against A on 1
    n, W, G = 3, np.zeros((6, 6)), np.full((6, 6), 2.0)
    W[0, 4], W[3, 1] = 2.0, 1.0
    if lab.pair_scores(W, G, [(0, 1)], n) != [0.75]:
        failures.append(f"lab.pair_scores {lab.pair_scores(W, G, [(0, 1)], n)}, want [0.75]")
    with tempfile.TemporaryDirectory() as tmp:                     # the swing of the median Trainers over a range
        Path(tmp, "log.jsonl").write_text("".join(json.dumps({"iter": i, "shape_quartiles": {"trainer": [0, x, 0]}}) + "\n"
                                                  for i, x in ((9, 30), (10, 12), (11, 20), (12, 15), (13, 2))))
        if lab.trainer_swing(Path(tmp), 10, 13) != 8.0:
            failures.append(f"lab.trainer_swing {lab.trainer_swing(Path(tmp), 10, 13)}, want 8")
        # deck types among the 12 best (log #120): 6 near a Haymaker list, 4 near a Wigglytuff list, 2 random singletons;
        # 3 more near Rain Dance rank below the 12 and do not count. The 24 human lists in placing order make 3 types.
        pool = Pool()
        arch = archived_decks(pool)
        near = lambda v, n: [random_changes(pool, v, 5, rng) for _ in range(n)]
        decks = near(arch[0][1], 6) + near(arch[1][1], 4) + [random_deck(pool, rng) for _ in range(2)] + near(arch[16][1], 3)
        pop = [{"deck": pool.names(v), "sum": 0.0, "n": 0, "last": 1.0 - i / 100} for i, v in enumerate(decks)]
        torch.save({"population": pop}, Path(tmp, "pop.pt"))
        ty = lab.deck_types(Path(tmp, "pop.pt"))
        torch.save({"population": [{"deck": pool.names(v), "n": 0, "last": 1.0 - i / 100} for i, (_, v) in enumerate(arch)]},
                   Path(tmp, "human.pt"))
        ty_h = lab.deck_types(Path(tmp, "human.pt"), top=24)
        po = [pokemon_overlap(pool, arch[a][1], arch[b][1]) for a, b in ((0, 1), (0, 16), (1, 16))]
        if ty != 2 or ty_h != 3 or max(po) >= 0.5:
            failures.append(f"lab.deck_types {ty} (want 2), human lists {ty_h} (want 3); Pokémon overlaps {po}")
    # draft heads (log #120): dealt round-robin unless the source had as many; a head out of range or missing is redealt
    from rl.metagame import assign_heads
    p1 = [{} for _ in range(7)]
    assign_heads(p1, 3, keep=False)
    p2 = [{"head": h} for h in (2, 2, 0, 1)]
    assign_heads(p2, 3, keep=True)
    p3 = [{"head": 0}, {"head": 3}, {}]
    assign_heads(p3, 3, keep=True)
    p4 = [{"head": 0} for _ in range(4)]
    assign_heads(p4, 2, keep=False)
    if ([a["head"] for a in p1] != [0, 1, 2, 0, 1, 2, 0] or [a["head"] for a in p2] != [2, 2, 0, 1]
            or [a["head"] for a in p3] != [0, 1, 2] or [a["head"] for a in p4] != [0, 1, 0, 1]):
        failures.append(f"assign_heads {p1} {p2} {p3} {p4}")
    if lab.cli({"--a": 1, "--b": True, "--c": False, "--d": {"k": 2}}) != ["--a", "1", "--b", "--d", '{"k": 2}']:
        failures.append(f"lab.cli {lab.cli({'--a': 1, '--b': True, '--c': False, '--d': {'k': 2}})}")
    # growing a pilot: the policy is unchanged, additive new inputs start at 0, Adam's moments follow the names
    base, grown = tiny_pilot(table, text, seed=3), tiny_pilot(table, text, seed=4, value_query=2, slot_bind=True)
    missing = load_grown(grown, base.state_dict())
    if not missing or not all(k.startswith(("vquery", "vcross.", "owner.", "same_bias")) for k in missing):
        failures.append(f"load_grown: missing {missing}")
    zeroed = [n for n, q in grown.named_parameters() if n in ZERO_AT_GROWTH]
    if not zeroed or any(q.abs().sum() > 0 for n, q in grown.named_parameters() if n in ZERO_AT_GROWTH):
        failures.append(f"load_grown: {zeroed} not at zero")
    vq = tiny_pilot(table, text, seed=4, value_query=2)
    load_grown(vq, base.state_dict())
    B = 4
    inp = (torch.randint(1, 50, (B, 128), dtype=torch.int16), torch.randint(1, 4, (B, 128), dtype=torch.uint8),
           torch.zeros(B, 128, dtype=torch.uint8), torch.zeros(B, 82, dtype=torch.uint8),
           torch.zeros(B, 240, dtype=torch.uint8), torch.randint(0, 9, (B, 48 * 6), dtype=torch.int16),
           torch.full((B,), 5, dtype=torch.int32))
    with torch.no_grad():
        (l0, v0), (l1, v1) = base(*inp), vq(*inp)
    if not torch.allclose(l0, l1, atol=1e-5):
        failures.append(f"grown pilot (value_query): policy changed by {(l0 - l1).abs().max():.2e}")
    for mode in ("joint", "cross"):                                   # a deeper pilot: two more encoder blocks
        b2, deep = tiny_pilot(table, text, seed=3, deck_mode=mode), tiny_pilot(table, text, seed=5, layers=4, deck_mode=mode)
        miss = load_grown(deep, b2.state_dict())
        if sorted({k.split(".")[1] for k in miss}) != ["2", "3"] or not all(k.startswith("blocks.") for k in miss):
            failures.append(f"load_grown (deeper, {mode}): missing {miss[:4]}")
        with torch.no_grad():
            (dl0, dv0), (dl1, dv1) = b2(*inp), deep(*inp)
        if not (torch.allclose(dl0, dl1, atol=1e-5) and torch.allclose(dv0, dv1, atol=1e-5)):
            failures.append(f"grown pilot (deeper, {mode}): changed by {(dl0 - dl1).abs().max():.2e}")
    opt = torch.optim.Adam(base.parameters(), lr=1e-3)
    base.train()
    base(*inp)[1].sum().backward()
    opt.step()
    sd = remap_adam(opt.state_dict(), [n for n, _ in base.named_parameters()], vq)
    opt2 = torch.optim.Adam(vq.parameters(), lr=1e-3)
    opt2.load_state_dict(sd)
    names_b = dict(base.named_parameters())
    same = [n for n, q in vq.named_parameters() if n in names_b and names_b[n] in opt.state]   # had a gradient
    bad = [n for n in same if not torch.equal(opt2.state[dict(vq.named_parameters())[n]]["exp_avg"],
                                              opt.state[names_b[n]]["exp_avg"])]
    new = [n for n, q in vq.named_parameters() if n not in names_b and q in opt2.state]
    if bad or new:
        failures.append(f"remap_adam: {len(bad)} moments differ, {len(new)} new parameters with a state")
    vq.train()
    vq(*inp)[1].sum().backward()
    opt2.step()
    # the shares: RL_GPU_SHARE and RL_CPU_THREADS in a fresh interpreter
    env = {**__import__("os").environ, "RL_GPU_SHARE": "0.333", "RL_CPU_THREADS": "10"}
    out = subprocess.run([sys.executable, "-c", "from rl import limits as L; p = L.Pace('cuda', 0.8); "
                          "print(L.GPU_SHARE, round(L.SERVER_PACE, 3), round(p.rest, 3), L.MAX_WORKERS, L.GPU_MEM_FRACTION)"],
                         capture_output=True, text=True, env=env).stdout.split()
    if out != ["0.333", "2.003", "2.003", "8", "0.333"]:
        failures.append(f"limits shares: {out}")
    out = subprocess.run([sys.executable, "-c", "from rl import limits as L; print(L.GPU_SHARE, L.SERVER_PACE, L.MAX_WORKERS)"],
                         capture_output=True, text=True,
                         env={k: v for k, v in env.items() if k not in ("RL_GPU_SHARE", "RL_CPU_THREADS")}).stdout.split()
    if out != ["0.8", "0.0", "14"]:
        failures.append(f"limits without shares: {out}")
    # auxiliary heads (log #84): targets from interleaved trajectories; a grown pilot plays as its source; the loss
    # reaches the trunk
    r = {"traj": np.array([0, 1, 0, 1, 0, 2]), "reward": np.array([0, 0, 0, -1, 1, 0], dtype=np.float32)}
    t = aux_targets(r)
    want_left = np.log1p([2, 1, 1, 0, 0, 0]) / np.log(201.0)
    if not (np.allclose(t[:, 0], want_left) and np.allclose(t[:, 1], [1, -1, 1, -1, 1, 0])):
        failures.append(f"aux_targets {t.tolist()}")
    ax = tiny_pilot(table, text, seed=5, aux_heads=2)
    grown_aux = load_grown(ax, base.state_dict())
    with torch.no_grad():                                        # base has taken a step above: its outputs now
        (l0, v0), (l2, v2) = base.eval()(*inp), ax(*inp)
    if not (grown_aux and all(k.startswith("aux_head.") for k in grown_aux) and torch.equal(l0, l2) and torch.equal(v0, v2)):
        failures.append(f"aux_heads: grown {grown_aux}, policy or value changed")
    ax.train()
    _, _, pooled = ax(*inp, return_pooled=True)
    ax.aux_head(pooled).pow(2).mean().backward()
    if not (ax.blocks[0].qkv.weight.grad is not None and ax.blocks[0].qkv.weight.grad.abs().sum() > 0):
        failures.append("aux_heads: the auxiliary loss does not reach the trunk")
    with tempfile.TemporaryDirectory() as tmp:
        export_token_onnx(ax, str(Path(tmp) / "ax.onnx"))
    print(f"lab: llr = direct ({direct:.3f}), grows under H1 {up[0]:.1f} -> {up[1]:.1f}, H0 {down[0]:.1f} -> {down[1]:.1f}; "
          f"pair scores, cli, deck types, draft heads dealt; grown pilot ({len(missing)} new weights, policy unchanged; 2 more blocks, joint and cross: unchanged), remap_adam, shares ok")


def check_lam_turn(failures):
    """rl/train.py advantages with lam_turn (log #96): lambda 1 inside a turn, lam across turns, on a hand-made
    trajectory interleaved with another; with lam_turn None it is the ordinary GAE."""
    v = np.array([0.1, 0.5, 0.2, 0.3, -0.4, 0.6], dtype=np.float32)
    r = {"action": np.zeros(6), "value": v, "reward": np.array([0, 0, 0, 0, 1, -1], dtype=np.float32),
         "done": np.array([0, 0, 0, 0, 1, 1]), "traj": np.array([0, 1, 0, 0, 0, 1]),
         "obs.glob": np.array([[1], [2], [1], [3], [3], [4]], dtype=np.uint8)}
    a, _ = advantages(r, 1.0, 0.0, 1.0)
    # trajectory 0 at rows 0, 2, 3, 4 with turns 1, 1, 3, 3: the deltas, then lambda 1 within turn 3 and within turn 1
    d4 = 1 - v[4]
    d3 = v[4] - v[3]
    d2 = v[3] - v[2]
    d0 = v[2] - v[0]
    want0 = {4: d4, 3: d3 + d4, 2: d2, 0: d0 + d2}
    plain, _ = advantages(r, 1.0, 0.5)
    same, _ = advantages(r, 1.0, 0.5, None)
    if not (all(np.isclose(a[i], w) for i, w in want0.items()) and np.isclose(a[5], -1 - v[5]) and np.isclose(a[1], v[5] - v[1])
            and np.allclose(plain, same)):
        failures.append(f"lam_turn advantages {a.tolist()}, want {want0}")
    print("lam_turn: lambda 1 inside a turn, lam across turns, interleaved trajectories; None = ordinary GAE")


def check_judged(failures):
    """rl/metagame.py judged / judged_mean (--judge-search, log #148): without searched games it is exactly (sum / n, n)
    (the score without --judge-search) in both modes, with none at all the default, with searched games only their
    mean and count; the searched mean is shrunk toward the greedy one by `prior` games (prior 0: unshrunk) and
    approaches its own mean as its games grow; 'min' at z 0 is the plain min of the two, and at z > 0 the greedy mean
    lowered only to the shrunk mean plus z of its errors (never above the greedy mean, never below the plain min, the
    greedy mean when search agrees), monotone in searched wins, with the shrunk mean's games behind a lowered score; on
    noise alone (search as strong as greedy) z 1.5 lowers scores by under 0.01 where the plain min lowers them ~0.05
    (the #148 review); null_searched redraws only scores with both kinds of game; recent_score prefers 'judged'."""
    from rl.metagame import judged, judged_mean, null_searched, recent_score
    rng = np.random.default_rng(5)
    bad = []
    for _ in range(200):
        n, sn = int(rng.integers(1, 30)), int(rng.integers(1, 30))
        x = {"sum": float(rng.integers(0, 2 * n + 1)) / 2, "n": n, "ssum": float(rng.integers(0, 2 * sn + 1)) / 2, "sn": sn}
        g, s = x["sum"] / n, x["ssum"] / sn
        prior = float(rng.choice([0.0, 1.0, 4.0, 16.0]))
        z = float(rng.choice([1.0, 1.5, 2.0]))
        m0, m, q = judged_mean(x, "min", prior, z=0.0), judged_mean(x, "min", prior, z=z), judged_mean(x, "search", prior)
        shrunk = (x["ssum"] + prior * g) / (sn + prior)
        if not (np.isclose(q, shrunk) and np.isclose(m0, min(g, shrunk)) and min(g, s) - 1e-12 <= q <= max(g, s) + 1e-12):
            bad.append(("bounds", x, prior, m0, q))
        p = min(0.85, max(0.15, (x["sum"] + x["ssum"]) / (n + sn)))
        u = shrunk + z * sn / (sn + prior) * (p * (1 - p) * (1 / sn + 1 / n)) ** 0.5
        if not (np.isclose(m, min(g, u)) and m0 - 1e-12 <= m <= g + 1e-12):
            bad.append(("z: min(greedy, shrunk + z errors)", x, prior, z, m))
        ns = (sn + prior) ** 2 / (sn + prior ** 2 / n)
        if not np.isclose(judged(x, "min", prior, z)[1], n if g <= u else ns) or not np.isclose(judged(x, "search", prior)[1], ns):
            bad.append(("games behind the score", x, prior, z))
        if s >= g and not (m == g and m0 == g):
            bad.append(("min = greedy when the searched mean is as high", x, m))
        if prior == 0 and not (np.isclose(q, s) and np.isclose(ns, sn)):
            bad.append(("prior 0", x, q))
        more = {**x, "ssum": x["ssum"] + 1, "sn": sn + 1}
        if (judged_mean(more, "search", prior) < q - 1e-12 or judged_mean(more, "min", prior, z=0.0) < m0 - 1e-12
                or judged_mean(more, "min", prior, z=z) < m - 1e-12):
            bad.append(("a searched win lowers the score", x, prior, z))
        plain = {"sum": x["sum"], "n": n}
        if not (judged_mean(plain, "min", prior) == x["sum"] / n == judged_mean({**plain, "ssum": 0.0, "sn": 0}, "search", prior)
                and judged(plain, "min", prior)[1] == n):
            bad.append(("no searched games", x))
        y = null_searched(x, rng)
        if not (y["sn"] == sn and y["n"] == n and y["sum"] == x["sum"] and 0 <= y["ssum"] <= sn and y["ssum"] == int(y["ssum"])):
            bad.append(("null_searched", x, y))
    if null_searched(plain, rng) is not plain or null_searched({"sum": 0.0, "n": 0, "ssum": 2.0, "sn": 3}, rng)["ssum"] != 2.0:
        bad.append(("null_searched: no redraw without both kinds of game",))
    if judged_mean({"sum": 0.0, "n": 0}, "min", 4.0, -1.0) != -1.0 or judged_mean({"sum": 0.0, "n": 0, "ssum": 0.0, "sn": 0}, "search", 4.0, 0.5) != 0.5:
        bad.append(("no games: the default",))
    if judged({"sum": 0.0, "n": 0, "ssum": 3.0, "sn": 4}, "min", 4.0) != (0.75, 4):
        bad.append(("searched only: their mean",))
    if judged_mean({"sum": 10.0, "n": 10, "ssum": 0.0, "sn": 4}, "min", 4.0, z=0.0) != 0.5:      # (0 + 4 x 1) / (4 + 4)
        bad.append(("shrinkage by the prior's games",))
    big = judged_mean({"sum": 6.0, "n": 10, "ssum": 2000.0, "sn": 10000}, "search", 4.0)
    if abs(big - 0.2) > 1e-3:
        bad.append(("many searched games: their own mean", big))
    bias = {}                                            # search exactly as strong as greedy: what noise alone costs
    for z in (0.0, 1.5):
        d = []
        for _ in range(4000):
            x = {"sum": float(rng.binomial(24, 0.5)), "n": 24, "ssum": float(rng.binomial(8, 0.5)), "sn": 8}
            d.append(judged_mean(x, "min", 4.0, z=z) - x["sum"] / 24)
        bias[z] = float(np.mean(d))
    if not (bias[0.0] < -0.03 and bias[1.5] > -0.01):
        bad.append(("noise alone", bias))
    a = {"sum": 3.0, "n": 4, "last": 0.2}
    if not (recent_score(a) == 0.75 and recent_score({**a, "judged": 0.6}) == 0.6 and recent_score({**a, "judged": None}) == 0.75
            and recent_score({"sum": 0.0, "n": 0, "last": 0.2, "judged": None}) == 0.2 and recent_score({"sum": 0.0, "n": 0}, 0.5) == 0.5):
        bad.append(("recent_score",))
    if bad:
        failures.append(f"judged_mean: {len(bad)} failures, first {bad[0]}")
    print(f"judged_mean: sum / n without searched games; shrinkage by the prior; min lowered only past z errors, "
          f"monotone in searched wins; noise alone {bias[0.0]:+.3f} at z 0, {bias[1.5]:+.3f} at z 1.5; recent_score")


def check_topk(failures, m, rng):
    """rl/remote.py's top-k reply (log #148), on a fake pool (no workers): a plain request gets exactly the reply it got
    before (no k, no top) and the same actions whoever shares its batch; a request with topk K gets each row's K most
    likely legal options, best first (the first its action), -1 past its legal ones; topk 0 marks a search's request
    without a top; and a search's batch forwarded in chunks answers as in one pass."""
    from rl import remote
    m = copy.deepcopy(m)                                 # its score head starts at zero (every logit tied): perturb it
    gen = torch.Generator().manual_seed(7)
    with torch.no_grad():
        for p in m.parameters():
            p.add_(0.05 * torch.randn(p.shape, generator=gen))
    B_M = m.max_cand
    n_cards = m.card_feats.shape[0]

    def req(rid, n, topk=None):
        T = m.max_tok
        L = rng.integers(20, T, size=n)
        kind = np.zeros((n, T), np.uint8)
        for b in range(n):
            kind[b, :L[b]] = rng.integers(1, 14, size=L[b])
        card = (rng.integers(0, n_cards, size=(n, T)) * (kind > 0)).astype(np.int16)
        aux = (rng.integers(0, 30, size=(n, T)) * (kind > 0)).astype(np.uint8)
        cand = np.stack([rng.integers(0, 32, size=(n, B_M)), rng.integers(0, n_cards, size=(n, B_M)),
                         rng.integers(0, 16, size=(n, B_M)), rng.integers(0, 16, size=(n, B_M)),
                         rng.integers(0, 9, size=(n, B_M)), rng.integers(0, 64, size=(n, B_M))], -1).reshape(n, B_M * 6).astype(np.int16)
        n_cand = rng.integers(1, B_M + 1, size=n).astype(np.int32)
        legal = [np.sort(rng.choice(int(c), int(rng.integers(1, min(int(c), 6) + 1)), replace=False)).astype(np.int32) for c in n_cand]
        offsets = np.concatenate([[0], np.cumsum([len(x) for x in legal])]).astype(np.int32)
        a = {"tok_card": card.ravel(), "tok_kind": kind.ravel(), "tok_aux": aux.ravel(),
             "glob": rng.integers(0, 49, size=n * m.glob_f).astype(np.uint8),
             "slots": rng.integers(0, 49, size=n * 12 * m.slot_f).astype(np.uint8), "cand": cand.ravel(), "n_cand": n_cand,
             "legal_offsets": offsets, "legal_ids": np.concatenate(legal), "keys": np.zeros(n, np.int32), "drop": np.zeros(0, np.int32)}
        h = {"id": rid, "slot": 0, "n": n, "encoding": "tokens", "greedy": True, **({"topk": topk} if topk is not None else {})}
        return (0, h, a), legal

    def serve(requests):
        pool = remote.RemotePool.__new__(remote.RemotePool)
        pool.mem, pool.pace, sent = {}, 0.0, {}
        pool._send = lambda i, kind, payload: sent.__setitem__(remote.unpack_arrays(payload)[0]["id"], remote.unpack_arrays(payload))
        pool._serve_batches([r for r, _ in requests], {0: m}, "cpu")
        return sent

    plain, top3, line = req(1, 7), req(2, 9, 3), req(3, 5, 0)
    alone = serve([plain])[1]
    mixed = serve([plain, top3, line])
    bad = []
    hp, ap = mixed[1]
    if set(hp) != {"id", "n", "arrays"} or [x["name"] for x in hp["arrays"]] != ["action", "logp", "value", "sampled"]:
        bad.append(("plain reply's fields", hp))
    if not (np.array_equal(ap["action"], alone[1]["action"]) and np.allclose(ap["value"], alone[1]["value"], atol=1e-5)):
        bad.append(("plain answers change with a top-k request in the batch",))
    hl, al = mixed[3]
    if "k" in hl or "top" in al:
        bad.append(("topk 0 got a top", hl))
    ht, at = mixed[2]
    (_, _, a2), legal2 = top3
    with torch.no_grad():
        x = [torch.from_numpy(a2[k].copy()).view(9, -1) if k != "n_cand" else torch.from_numpy(a2[k].copy()) for k in remote.TOKEN_INPUTS]
        logits = m(*x)[0].float().numpy()
    top = at.get("top")
    if ht.get("k") != 3 or top is None or len(top) != 27:
        bad.append(("top-k reply's shape", ht))
    else:
        top = top.reshape(9, 3)
        for r, lg in enumerate(legal2):
            want = sorted(lg.tolist(), key=lambda c: -logits[r, c])[:3]
            got = [int(c) for c in top[r] if c >= 0]
            if got != want or int(top[r][0]) != int(at["action"][r]) or list(top[r][len(want):]) != [-1] * (3 - len(want)):
                bad.append(("top row", r, got, want, int(at["action"][r])))
    old, remote.CHUNK = remote.CHUNK, 4                 # a search's batch of 21 rows in chunks of 4
    try:
        chunked = serve([plain, top3, line])
    finally:
        remote.CHUNK = old
    for rid in (1, 2, 3):
        if not (np.array_equal(chunked[rid][1]["action"], mixed[rid][1]["action"])
                and np.allclose(chunked[rid][1]["value"], mixed[rid][1]["value"], atol=1e-5)
                and np.array_equal(chunked[rid][1].get("top", np.zeros(0)), mixed[rid][1].get("top", np.zeros(0)))):
            bad.append(("chunked forward differs", rid))
    if bad:
        failures.append(f"top-k reply: {len(bad)} failures, first {bad[0]}")
    print("top-k reply: plain replies unchanged (fields and answers); each row's top K legal options best first, -1 past "
          "the legal ones; topk 0 gets none; chunked forward answers alike")


def check_lab_loop(failures):
    """rl/lab.py's loop with fake runs (an iteration count per run). (1) A STOP in the middle of a branch's segment, then
    a restart: every card is decided once, at the right iteration, including one that finished before the stop. (2) A
    card adopted while a two-segment card runs: that card is rebased and decided again from the new main line. (3) A held
    card that passes is not adopted, and the card beside it is not rebased."""
    from rl import lab
    names = ("ROOT", "LAB", "MAIN", "CARDS", "BRANCHES", "STOP", "EVENTS", "SETTINGS", "done", "run_metagame", "decide",
             "milestone", "wait_resources", "keep_awake", "run_warm")
    forks = {}                                       # a branch's --fork-from at its first segment
    untils = []                                      # (run, the iteration it was run to)
    saved = {k: getattr(lab, k) for k in names}

    def scenario(specs, stop_branch, stops):
        decided, stop_at = [], {"branch": stop_branch, "main": 10 ** 9}
        with tempfile.TemporaryDirectory() as tmp:
            lab.ROOT = Path(tmp)
            L = lab.ROOT / "lab"
            lab.LAB, lab.MAIN, lab.CARDS, lab.BRANCHES = L, L / "main", L / "cards", L / "branches"
            lab.STOP, lab.EVENTS, lab.SETTINGS = L / "STOP", L / "events.jsonl", L / "lab.json"
            lab.done = lambda run: int((run / "checkpoint.pt").read_text()) if (run / "checkpoint.pt").exists() else 0

            def run_metagame(run, args, until, s):
                run.mkdir(parents=True, exist_ok=True)
                untils.append((run.name, until))
                if "--fork-from" in args:
                    forks[run.name] = args[args.index("--fork-from") + 1]
                if stop_at["branch"] and run.name.startswith(stop_at["branch"]):  # stopped after 2 of its iterations
                    (run / "checkpoint.pt").write_text("152")
                    stop_at["branch"] = None
                    lab.STOP.touch()
                    return True
                (run / "checkpoint.pt").write_text(str(until))
                if run.name == "main" and until >= stop_at["main"]:
                    lab.STOP.touch()
                return True

            def decide(c, m, s):
                decided.append((c["id"], m))
                final = m >= c["base"] + s["seg"] * c.get("segments", 1)
                end = "measured" if c["kind"] == "aa" else "passed" if "pass" in c["id"] else "inconclusive"
                return {"at": m, **({"status": end} if final else {})}

            lab.run_metagame, lab.decide = run_metagame, decide
            lab.run_warm = lambda c, base, s: lab.BRANCHES / c["id"] / "warm.pt"
            lab.milestone, lab.keep_awake = (lambda k, s: None), (lambda: None)
            lab.wait_resources = lambda s: not lab.STOP.exists()
            for d in (lab.MAIN, lab.CARDS):
                d.mkdir(parents=True)
            (lab.MAIN / "checkpoint.pt").write_text("150")
            for cid, kind, segs in specs:
                lab.save_card({"id": cid, "kind": kind, "segments": segs, "args": {}, **({"hold": True} if "hold" in cid else {}),
                               **({"warm": {"pilot-opts": {}}} if "warm" in cid else {}),
                               **({"decide": "s1", "test": "noninferior"} if "long" in cid else {})})
            runs = []
            with contextlib.redirect_stdout(io.StringIO()):
                for stop in stops:
                    if lab.STOP.exists():
                        lab.STOP.unlink()
                    stop_at["main"] = stop
                    lab.lab_main()
                    runs.append(list(decided))
            status = {c["id"]: (c.get("status"), c.get("base")) for c in lab.cards()}
            return (runs, status, [a["card"] for a in lab.settings()["adopted"]],
                    {c["id"]: (c.get("decide"), c.get("test")) for c in lab.cards()})

    try:
        runs, status, _, _ = scenario((("001-aa", "aa", 1), ("002-aa", "aa", 1), ("003-pilot", "pilot", 2)), "002", (10 ** 9, 190))
        want = [("001-aa", 160), ("002-aa", 160), ("003-pilot", 170), ("003-pilot", 180)]
        if runs != [[], want] or status != {"001-aa": ("measured", 150), "002-aa": ("measured", 150),
                                            "003-pilot": ("inconclusive", 160)}:
            failures.append(f"lab loop, restart: decided {runs}, want [[], {want}]; status {status}")
        runs2, status2, adopted, rules2 = scenario((("001-long", "pilot", 2), ("002-pass", "pilot", 1)), None, (190,))
        want2 = [("001-long", 160), ("002-pass", 160), ("001-long-b", 170), ("001-long-b", 180)]
        if runs2 != [want2] or adopted != ["002-pass"] or status2 != {
                "001-long": ("rebased", 150), "001-long-b": ("inconclusive", 160), "002-pass": ("adopted", 150)}:
            failures.append(f"lab loop, adoption: decided {runs2}, want [{want2}]; status {status2}, adopted {adopted}")
        if rules2.get("001-long-b") != ("s1", "noninferior"):
            failures.append(f"lab loop, rebase: the requeued card is decided by {rules2.get('001-long-b')}, want its own rule")
        runs3, status3, adopted3, _ = scenario((("001-long", "pilot", 2), ("002-pass-hold", "pilot", 1)), None, (190,))
        if adopted3 or status3 != {"001-long": ("inconclusive", 150), "002-pass-hold": ("passed-held", 150)}:
            failures.append(f"lab loop, held card: status {status3}, adopted {adopted3}")
        forks.clear()
        untils.clear()
        _, status4, adopted4, _ = scenario((("001-scratch", "scratch", 2), ("002-pass", "pilot", 1)), None, (190,))
        if not ([u for r, u in untils if r == "001-scratch"] == [10, 20] and "001-scratch" not in forks
                and adopted4 == ["002-pass"] and status4.get("001-scratch") == ("inconclusive", 150)):
            failures.append(f"lab loop, scratch card: runs {untils}, forks {forks}, status {status4}, adopted {adopted4}")
        forks.clear()
        scenario((("001-warm", "pilot", 1), ("002-plain", "pilot", 1)), None, (170,))
        if not (forks.get("001-warm", "").endswith("001-warm/warm.pt") and forks.get("002-plain", "").endswith("seg_0150.pt")):
            failures.append(f"lab loop, warm card: forks {forks}")
    finally:
        for k, v in saved.items():
            setattr(lab, k, v)
    print(f"lab loop: a STOP mid-branch and a restart decide each card once ({runs[-1]}); a card running at an adoption "
          f"is rebased with its decision rule ({runs2[-1]}); a scratch card counts its own iterations, unforked and not rebased; a held pass is not adopted; a warm card forks from its warm start")


def main():
    failures = []
    table = json.load(open("notes/data/cards/pool.json", encoding="utf-8"))["cards"]
    text = np.load("notes/data/cards/text_emb.npy")
    archived = archived_decks(Pool())
    rng = np.random.default_rng(0)
    check_decks(failures, archived, rng)
    check_subset(failures, rng)
    check_onnx(failures, tiny_pilot(table, text), rng)
    check_ablations(failures, table, text, rng)
    check_shaping(failures, rng)
    check_rloo(failures)
    check_draft(failures, table, text, archived, rng)
    check_train(failures, np.random.default_rng(1))
    check_lab(failures, table, text, np.random.default_rng(2))
    check_lab_loop(failures)
    check_lam_turn(failures)
    check_judged(failures)
    check_topk(failures, tiny_pilot(table, text), np.random.default_rng(3))
    for f in failures[:20]:
        print("FAIL", f)
    print("FAIL" if failures else "PASS")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
