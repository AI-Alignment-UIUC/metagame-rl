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
  (grad_norm the pre-clip norm, kl_last the last epoch's kl), and two seeded calls give identical parameters
"""
import argparse
import copy
import glob
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from rl.decks import Pool, archived_decks, changed, random_deck
from rl.draft import LEAD, MY_UNSEEN, OPPONENT_LIST, SLOT, Drafter, deck_tokens, random_changes, rloo
from rl.model import IdentityMLP
from rl.rollouts import concat, read_rollout, subset
from rl.token_model import TokenPointerNet, export_token_onnx
from rl.train import (ending_kinds, explained_variance, legal_mask, lr_at, ppo_update, save_atomic, schedule_lr,
                      shape_rewards)

PRIZE_GLOB = (6, 22)


def tiny_pilot(table, text, seed=0, n_names=8, **kw):
    torch.manual_seed(seed)
    return TokenPointerNet(table, text, n_names=n_names, glob_f=82, slot_f=20, max_tok=128, max_cand=48, d=64, layers=2,
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
        lp, _, _ = dr.log_prob(vw, samples)
        gaps.append(np.abs(lp.detach().numpy() - np.array([s["logp"] for s in samples])).max())
        wrong += sum(len(s["ev_c"]) != 3 or changed(s["deck"], v) > 3 for s in samples)
    if max(gaps) > 1e-3:
        failures.append(f"draft: batched log-prob differs from the drawn one by {max(gaps):.2e}")
    if wrong:
        failures.append(f"draft: {wrong} draws do not make exactly 3 replacements")
    print(f"draft: {n} draws legal, 3 replacements each, log-prob gap {max(gaps):.1e}")

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
        dr.update([(vw, samples, rloo(z, np.zeros(len(z))))], beta=0.0)
    m1 = mass()
    if not (m0 < 0.06 and m1 > 0.30):
        failures.append(f"draft bandit: target mass {m0:.3f} -> {m1:.3f}, not ~0.03 -> over 0.30")
    print(f"draft bandit: incoming mass on 8 target cards {m0:.3f} -> {m1:.3f} in 200 steps")


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
    print(f"train: lr_at, explained_variance ({ev[0]:.4f}, {ev[1]:.4f}), ending_kinds, save_atomic ok; ppo_update "
          f"stats match the closed form, grad_norm {s1['grad_norm']:.4f} = step {step(m1):.4f}, kl_last {s3['kl_last']:.5f}")


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
    for f in failures[:20]:
        print("FAIL", f)
    print("FAIL" if failures else "PASS")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
