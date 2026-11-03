"""PPO self-play training (plan items A1.5, A3, A4).

Rollouts are played by Node workers (env/remote_worker.js) that send their decisions here: the policy, a
TokenPointerNet over env/tokens.js, runs on the GPU in large batches across workers (rl/remote.py). One iteration:
collect N transitions per worker -> PPO epochs -> log. The learner plays itself, and both seats are recorded.

Example (C49, runs/pilot/C49/chain.sh):
  .venv/Scripts/python -m rl.train --run runs/pilot/C49-sd --matchups-file runs/pilot/C30/matchups.json \
      --inference gpu --model tokens --d 256 --tok-layers 4 --heads 8 --deck-mode cross --round-turns 20-45
"""
import argparse
import collections
import json
import os
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from rl import limits
from rl.rollouts import read_rollout, concat

ROOT = Path(__file__).resolve().parent.parent
TOKEN_FIELDS = ("obs.tokCard", "obs.tokKind", "obs.tokAux", "obs.glob", "obs.slots", "obs.cand", "obs.nCand")


def advantages(r: dict, gamma: float, lam: float, lam_turn: float = None, gamma_turn: float = None):
    """GAE per trajectory (one player's decisions in one game, in order); reward only at the end. lam_turn (log #96):
    the lambda between two decisions of the same game turn (glob byte 0, env/tokens.js), lam across turns, so a turn's
    outcome credits every decision of that turn in full with lam_turn = 1. gamma_turn (C121): the discount between two
    decisions is gamma * gamma_turn ** (game turns between them), so 1 within a turn; None leaves gamma alone."""
    T = len(r["action"])
    adv = np.zeros(T, dtype=np.float32)
    nxt_v, nxt_a, nxt_turn = {}, {}, {}
    value, reward, done, traj = r["value"], r["reward"], r["done"], r["traj"]
    turn = r["obs.glob"].reshape(T, -1)[:, 0] if lam_turn is not None or gamma_turn is not None else None
    for t in range(T - 1, -1, -1):
        k = traj[t]
        if done[t]:
            v1, a1 = 0.0, 0.0
        else:
            v1, a1 = nxt_v.get(k, 0.0), nxt_a.get(k, 0.0)
        g = gamma if gamma_turn is None else gamma * gamma_turn ** max(int(nxt_turn.get(k, turn[t])) - int(turn[t]), 0)
        delta = reward[t] + g * v1 - value[t]
        l = lam_turn if lam_turn is not None and nxt_turn.get(k) == turn[t] else lam
        adv[t] = delta + g * l * a1
        nxt_v[k], nxt_a[k] = value[t], adv[t]
        if turn is not None:
            nxt_turn[k] = turn[t]
    return adv, adv + value


def explained_variance(batch: dict):
    """1 - var(G - value) / var(G), G the Monte Carlo return (gamma 1), over all decisions (ev_mc) and over
    those at game turn <= 4 (ev_open; the turn is glob byte 0, env/tokens.js). None where undefined (no such
    decisions, no glob, var(G) = 0 up to float32 noise)."""
    T = len(batch["action"])
    if T == 0:
        return None, None
    _, G = advantages(batch, 1.0, 1.0)
    G, v = G.astype(np.float64), batch["value"].astype(np.float64)

    def ev(sel):
        g = G[sel]
        if len(g) == 0 or g.var() < 1e-8:
            return None
        return float(1 - (g - v[sel]).var() / g.var())
    early = batch["obs.glob"].reshape(T, -1)[:, 0] <= 4 if "obs.glob" in batch else np.zeros(T, bool)
    return ev(np.ones(T, bool)), ev(early)


def probe_targets(replies: list, rolls: list, K: int):
    """Soft search targets (--search-distill, C49, log #169): from the workers' probes, per transition of the
    concatenated rollouts the searched moves (-1 none) and their mean copy scores, plus a log row."""
    T = sum(len(ro["action"]) for ro in rolls)
    pc = np.full((T, K), -1, dtype=np.int64)
    pq = np.zeros((T, K), dtype=np.float32)
    base, spread, n_pr = 0, [], 0
    for rep, ro in zip(replies, rolls):
        for p in rep.get("probes") or []:
            if "cands" not in p:
                continue
            qs = [[x for x in sc if x is not None] for sc in p["scores"]]
            cands = [(c, float(np.mean(q))) for c, q in zip(p["cands"], qs) if q]
            if len(cands) < 2:
                continue
            row = base + int(p["k"])
            for i, (c, q) in enumerate(cands[:K]):
                pc[row, i], pq[row, i] = c, q
            spread.append(max(q for _, q in cands) - min(q for _, q in cands))
            n_pr += 1
        base += len(ro["action"])
    return pc, pq, {"probes": n_pr, "q_spread_median": round(float(np.median(spread)), 4) if spread else None}


def round_turns(text: str):
    """--round-turns: "T" (every game cut at T) or "A-B" (T drawn per deal from A..B), for the 2000 round rule (env/game.js,
    log #160); "0" or "" for none."""
    if not text or text == "0":
        return 0
    a, _, b = str(text).partition("-")
    return [int(a), int(b)] if b else int(a)


def round_score(r: dict, seat: int, rule) -> float:
    """A seat's score for one game result: 1 a win, 0 a loss, 0.5 a draw; under the round rule (rule set) the event's
    points over 3: a win 1, a win on Prizes at time 2/3, a draw 1/3 to each seat, a loss 0 (env/game.js reward)."""
    w = r["winner"]
    if not rule:
        return 1.0 if w == seat else 0.0 if w in (1, 2) else 0.5
    return (2 / 3 if r.get("ending") == "time" else 1.0) if w == seat else 0.0 if w in (1, 2) else 1 / 3


def ending_kinds(games: list) -> dict:
    """Game results by deck pair kind: RR if both decks are rules-only random ones (names "rnd..."), PR if one
    is, else PP. cut = games with no ending and no error (cut off)."""
    by = {}
    for g in games:
        r = sum(str(n).startswith("rnd") for n in (g.get("decks") or [])[:2])
        by.setdefault(("PP", "PR", "RR")[r], []).append(g)
    return {k: {"games": len(v), "endings": dict(collections.Counter(g.get("ending") or "none" for g in v)),
                "steps": round(float(np.mean([g["steps"] for g in v])), 1),
                "errors": sum(1 for g in v if g.get("error")),
                "cut": sum(1 for g in v if not g.get("ending") and not g.get("error"))} for k, v in sorted(by.items())}


def save_atomic(obj, path: Path):
    """torch.save to a temp file in the same directory, synced, then moved over path: a kill or power loss
    mid-write leaves the previous file intact."""
    tmp = path.with_suffix(".tmp")
    torch.save(obj, tmp)
    with open(tmp, "rb+") as f:
        os.fsync(f.fileno())
    for k in range(5):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:           # Windows: a reader or a virus scan holding either file for a moment
            if k == 4:
                raise
            time.sleep(0.5 * (k + 1))


def shape_rewards(r: dict, lam: float, prize_glob) -> np.ndarray:
    """The rewards plus potential-based prize shaping (log #65). Phi = lam * (opponent's prizes left -
    own) / 6, read from each recorded decision's observation; prize_glob = the glob bytes holding own and
    opponent's prizes left, 8 per prize (env/tokens.js PRIZE_GLOB). Each decision gets Phi at the
    player's next decision minus Phi now, the last one -Phi, so with gamma = 1 a trajectory's rewards
    still sum to the game's result: only when the credit arrives changes. lam = 0 changes nothing."""
    reward = r["reward"].astype(np.float32).copy()
    T = len(reward)
    if lam == 0 or T == 0:
        return reward
    g = r["obs.glob"].reshape(T, -1).astype(np.float32)
    phi = lam * (g[:, prize_glob[1]] - g[:, prize_glob[0]]) / (8 * 6)
    order = np.lexsort((np.arange(T), r["traj"]))      # each trajectory's decisions, in order
    same = r["traj"][order][1:] == r["traj"][order][:-1]
    nxt = np.zeros(T, dtype=np.float32)
    nxt[:-1][same] = phi[order][1:][same]
    reward[order] += nxt - phi[order]
    return reward


def legal_mask(idx: torch.Tensor, offsets: torch.Tensor, ids: torch.Tensor, action_size: int) -> torch.Tensor:
    starts, ends = offsets[idx], offsets[idx + 1]
    counts = ends - starts
    rows = torch.repeat_interleave(torch.arange(len(idx), device=idx.device), counts)
    first = torch.repeat_interleave(torch.cumsum(counts, 0) - counts, counts)
    pos = torch.arange(int(counts.sum()), device=idx.device) - first
    cols = ids[starts[rows] + pos]
    mask = torch.zeros(len(idx), action_size, dtype=torch.bool, device=idx.device)
    mask[rows, cols] = True
    return mask


def model_inputs(batch: dict, kind: str = "tokens") -> list:
    """The token network's inputs for every transition, as arrays with the batch dimension first (kind: 'tokens',
    the only encoding left)."""
    assert kind == "tokens", f"model_inputs: only the token encoding is left, not {kind}"
    T = len(batch["action"])
    return [batch[k].reshape(T, -1) if k != "obs.nCand" else batch[k] for k in TOKEN_FIELDS]


def ppo_update(model, opt, batch, args, device):
    T = len(batch["action"])
    inputs = [torch.from_numpy(np.ascontiguousarray(x)).to(device) for x in batch["inputs"]]
    act = torch.from_numpy(batch["action"].astype(np.int64)).to(device)
    old_logp = torch.from_numpy(batch["logp"]).to(device)
    adv = torch.from_numpy(batch["adv"]).to(device)
    ret = torch.from_numpy(batch["ret"]).to(device)
    old_v = torch.from_numpy(batch["value"]).to(device)
    offsets = torch.from_numpy(batch["legal_offsets"].astype(np.int64)).to(device)
    ids = torch.from_numpy(batch["legal_ids"].astype(np.int64)).to(device)
    # Decisions recorded as not sampled (batch["sampled"] 0, mostly greedy collection, log #81) don't train the policy,
    # since their recorded log-probability is not what the move was chosen with; the value and the entropy use every one.
    pol = torch.from_numpy(batch["sampled"].astype(np.float32)).to(device) if "sampled" in batch \
        else torch.ones(T, device=device)
    sel = pol > 0 if int((pol > 0).sum()) >= 2 else torch.ones(T, dtype=torch.bool, device=device)
    adv = (adv - adv[sel].mean()) / (adv[sel].std() + 1e-8)
    stats = {"pi_loss": 0.0, "v_loss": 0.0, "entropy": 0.0, "kl": 0.0, "clipfrac": 0.0}
    # Soft search targets (C49, log #169; --search-distill): at a probed decision, over the moves the search scored,
    # target = pi * exp(clip((q - mean q) / tau)) renormalised (pi detached, restricted to those moves), and the loss
    # KL(target || pi restricted) at weight args.search_distill, averaged over all the minibatch's rows.
    sd_w = getattr(args, "search_distill", 0.0) if "probe_c" in batch else 0.0
    # --distill-margin D (C137): a hard target in place of the soft one, the searched move with the best mean score, kept only
    # where it beats the move searched first (the pilot's own top-1 when probed) by D or more; the loss is search_distill x
    # cross-entropy toward it, summed over kept rows and divided by the minibatch's rows (as the soft KL). None: the soft target.
    sd_m = getattr(args, "distill_margin", None) if sd_w else None
    if sd_w:
        p_c = torch.from_numpy(batch["probe_c"]).to(device)
        p_q = torch.from_numpy(batch["probe_q"]).to(device)
        stats["sd_kl"] = 0.0
        stats["sd_agree"] = 0.0
        if sd_m is not None:
            stats.update({"sd_ce": 0.0, "sd_kept": 0.0, "sd_probed": 0.0, "sd_entropy": 0.0})   # raw sums; ratios at the end
    n = 0
    grad_norm, kl_last, n_last = 0.0, 0.0, 0      # pre-clip norm per step; kl over the last epoch only
    tok_len = None
    pace = limits.Pace(device, getattr(args, "gpu_load", limits.LOAD))
    if args.model == "tokens":                # tokens fill from the front; kind 0 is padding
        kind = inputs[1]
        tok_len = ((kind > 0).long() * torch.arange(1, kind.shape[1] + 1, device=device)).amax(1)
    # A pilot with memory (log #76) trains on whole trajectories: a minibatch and each micro-batch hold complete
    # trajectories (one player's decisions in one game, in order), so the backward pass runs through the game.
    memory = getattr(model, "memory", "none") != "none"
    if memory:
        traj_np = np.asarray(batch["traj"])
        order = np.lexsort((np.arange(T), traj_np))
        tj = traj_np[order]
        starts = np.flatnonzero(np.r_[True, tj[1:] != tj[:-1]])
        lens = np.diff(np.r_[starts, T])
        trajs = [torch.from_numpy(order[a:a + n]).to(device) for a, n in zip(starts, lens)]

    def chunks(ids, size):
        """Trajectory ids in groups of about `size` rows (whole trajectories)."""
        out, cur, n = [], [], 0
        for t in ids:
            cur.append(int(t))
            n += int(lens[t])
            if n >= size:
                out.append(cur)
                cur, n = [], 0
        return out + ([cur] if cur else [])

    def cut(src, rows):
        """A minibatch's micro-batches: chunks of its sorted rows, or groups of whole trajectories (memory)."""
        size = args.micro_batch or rows
        if memory:
            return [(torch.cat([trajs[t] for t in mc]), [int(lens[t]) for t in mc]) for mc in chunks(src, size)]
        return [(src[m:m + size], None) for m in range(0, len(src), size)]

    def accumulate(rows, micros):
        """The minibatch's loss accumulated over its micro-batches (same gradient, less memory) into .grad; its stats."""
        mb_stats = {k: 0.0 for k in stats}
        M = float(sum(pol[j].sum() for j, _ in micros))      # the minibatch's decisions that train the policy
        P = float(sum((p_c[j][:, 0] >= 0).sum() for j, _ in micros)) if sd_w else 0.0   # ... that were probed
        for j, mem_lens in micros:
            w = len(j) / rows
            pm = pol[j]
            wp = float(pm.sum()) / M if M > 0 else 0.0
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=args.amp and device == "cuda"):
                xs = [x[j] for x in inputs]
                if tok_len is not None:
                    L = int(tok_len[j].max())
                    xs[:3] = [x[:, :L] for x in xs[:3]]
                kw = {"mem_lens": mem_lens} if memory else {}
                logits, v = model(*xs, **kw)
            logits, v = logits.float(), v.float()
            mask = legal_mask(j, offsets, ids, model.action_size)
            logits = logits.masked_fill(~mask, -1e9)
            logp_all = F.log_softmax(logits, dim=-1)
            logp = logp_all.gather(1, act[j, None]).squeeze(1)
            p_all = logp_all.exp()
            entropy = -(p_all * logp_all).masked_fill(~mask, 0.0).sum(-1).mean()
            ratio = (logp - old_logp[j]).exp()
            a = adv[j]
            pi_rows = -torch.min(ratio * a, ratio.clamp(1 - args.clip, 1 + args.clip) * a) * pm
            pi_loss = pi_rows.sum() / pm.sum().clamp(min=1)
            v_clipped = old_v[j] + (v - old_v[j]).clamp(-args.clip, args.clip)     # PPO's value clip, at --clip
            v_loss = torch.max((v - ret[j]) ** 2, (v_clipped - ret[j]) ** 2).mean()
            # the policy term is the mean over the minibatch's policy decisions (all of them unless some are unsampled)
            loss = (pi_rows.sum() / M if M > 0 else 0.0 * pi_rows.sum()) + w * (args.vf * v_loss - args.ent * entropy)
            if sd_w and P > 0 and sd_m is not None:   # C137's hard target
                prow = p_c[j][:, 0] >= 0
                if prow.any():
                    c, q = p_c[j][prow], p_q[j][prow]
                    ok = c >= 0
                    qx = q.masked_fill(~ok, -1e9)
                    best = qx.argmax(1)
                    keep = (qx.gather(1, best[:, None]).squeeze(1) - q[:, 0]) >= sd_m
                    # a target must be legal at its own transition (#621: one C137 s28 row at iteration 0 wasn't; its masked
                    # log-probability, -1e9, made a CE of about 1e9 whose gradient flattens the policy)
                    keep = keep & mask[prow].gather(1, c.gather(1, best[:, None]).clamp(min=0)).squeeze(1)
                    mb_stats["sd_probed"] += float(prow.sum())
                    if keep.any():
                        tgt = c.gather(1, best[:, None]).squeeze(1)[keep]
                        lpk = logp_all[prow][keep]
                        ce = -lpk.gather(1, tgt[:, None]).squeeze(1)
                        loss = loss + sd_w * ce.sum() / rows
                        with torch.no_grad():
                            mb_stats["sd_ce"] += ce.sum().item()
                            mb_stats["sd_kept"] += float(keep.sum())
                            mb_stats["sd_agree"] += (lpk.argmax(1) == tgt).float().sum().item()
                            mb_stats["sd_entropy"] += -(lpk.exp() * lpk).masked_fill(lpk < -1e8, 0.0).sum(1).sum().item()
            elif sd_w and P > 0:
                prow = p_c[j][:, 0] >= 0
                if prow.any():
                    c, q = p_c[j][prow], p_q[j][prow]
                    ok = c >= 0
                    lp = logp_all[prow].gather(1, c.clamp(min=0)).masked_fill(~ok, -1e9)
                    lpc = lp - torch.logsumexp(lp, 1, keepdim=True)          # pi restricted to the searched moves
                    qm = q.masked_fill(~ok, 0.0).sum(1, keepdim=True) / ok.sum(1, keepdim=True).clamp(min=1)
                    a_hat = ((q - qm) / args.distill_tau).clamp(-args.distill_clip, args.distill_clip).masked_fill(~ok, 0.0)
                    with torch.no_grad():
                        lt = (lpc + a_hat).masked_fill(~ok, -1e9)
                        lt = lt - torch.logsumexp(lt, 1, keepdim=True)
                    kl = (lt.exp() * (lt - lpc)).masked_fill(~ok, 0.0).sum(1)
                    loss = loss + sd_w * kl.sum() / rows
                    with torch.no_grad():
                        mb_stats["sd_kl"] += kl.sum().item() / P
                        best_q = q.masked_fill(~ok, -1e9).argmax(1)
                        mb_stats["sd_agree"] += (lpc.argmax(1) == best_q).float().sum().item() / P
            loss.backward()
            pace.tick()                   # per micro-batch: the same share of rest, in finer slices
            with torch.no_grad():
                n_pm = pm.sum().clamp(min=1)
                mb_stats["pi_loss"] += wp * pi_loss.item()
                mb_stats["v_loss"] += w * v_loss.item()
                mb_stats["entropy"] += w * entropy.item()
                mb_stats["kl"] += wp * ((old_logp[j] - logp) * pm).sum().item() / n_pm.item()
                mb_stats["clipfrac"] += wp * (((ratio - 1).abs() > args.clip).float() * pm).sum().item() / n_pm.item()
        return mb_stats

    for e in range(args.epochs):
        if memory:
            plan = []
            for mb in chunks(torch.randperm(len(trajs)).tolist(), args.minibatch):
                plan.append((int(sum(lens[t] for t in mb)), mb))
        else:
            perm = torch.randperm(T, device=device)
            plan = []
            for s in range(0, T, args.minibatch):
                idx = perm[s:s + args.minibatch]
                if tok_len is not None:           # similar lengths share a micro-batch, cut to its longest
                    idx = idx[torch.argsort(tok_len[idx])]
                plan.append((len(idx), idx))
        for rows, src in plan:
            # Out of GPU memory, the minibatch starts again in micro-batches half the size, kept for the rest of the run:
            # the same gradient (log #121). A part of it may already be in .grad, so the whole minibatch is redone.
            while True:
                opt.zero_grad(set_to_none=True)
                try:
                    mb_stats = accumulate(rows, cut(src, rows))
                    break
                except torch.cuda.OutOfMemoryError:
                    if (args.micro_batch or rows) < 2:
                        raise
                opt.zero_grad(set_to_none=True)
                torch.cuda.empty_cache()
                args.micro_batch = (args.micro_batch or rows) // 2
                print(f"ppo_update: out of GPU memory; micro-batch now {args.micro_batch}", flush=True)
            grad_norm += float(torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm))
            opt.step()
            for k in stats:
                stats[k] += mb_stats[k]
            n += 1
            if e == args.epochs - 1:
                kl_last += mb_stats["kl"]
                n_last += 1
    out = {k: v / max(n, 1) for k, v in stats.items()}
    if sd_m is not None:                              # C137: per kept row (CE, agreement, entropy), kept per probed row; sd_kept
        kept = stats["sd_kept"]                       # and sd_probed stay as means a minibatch (the dose)
        out.update({"sd_ce": stats["sd_ce"] / max(kept, 1), "sd_agree": stats["sd_agree"] / max(kept, 1),
                    "sd_entropy": stats["sd_entropy"] / max(kept, 1), "sd_kept_share": kept / max(stats["sd_probed"], 1)})
        return {**out, "grad_norm": grad_norm / max(n, 1), "kl_last": kl_last / max(n_last, 1)}
    return {**{k: v / max(n, 1) for k, v in stats.items()}, "grad_norm": grad_norm / max(n, 1),
            "kl_last": kl_last / max(n_last, 1)}


def build_model(args, info):
    """A TokenPointerNet sized to the workers' token bounds (info); architecture options args lacks take the defaults."""
    from rl.token_model import build_token_model
    t = info["tokens"]
    return build_token_model(str(ROOT / "notes/data/cards/pool.json"), str(ROOT / "notes/data/cards/text_emb.npy"),
                             t["names"], t["globF"], t["slotF"], t["maxTok"], t["maxCand"],
                             d=args.d, layers=args.tok_layers, heads=args.heads,
                             count_features=getattr(args, "count_features", False),
                             cross_layers=getattr(args, "cross_layers", 1), cand_self=getattr(args, "cand_self", 0),
                             n_agents=getattr(args, "n_agents", 0),
                             card_inputs=getattr(args, "card_inputs", "all"), deck_tokens=getattr(args, "deck_tokens", True),
                             slot_bind=getattr(args, "slot_bind", False), ability_text=getattr(args, "ability_text", False),
                             deck_mode=getattr(args, "deck_mode", "joint"), deck_layers=getattr(args, "deck_layers", 1),
                             history=getattr(args, "history", 0), memory=getattr(args, "memory", "none"),
                             value_tower=getattr(args, "value_tower", 0), value_query=getattr(args, "value_query", 0),
                             chain=getattr(args, "chain", 0), cand_latent=getattr(args, "cand_latent", 0),
                             cand_latent_zone=getattr(args, "cand_latent_zone", 0),
                             cand_latent_gate=getattr(args, "cand_latent_gate", 0),
                             cand_latent_pick=getattr(args, "cand_latent_pick", 0),
                             cand_latent_center=getattr(args, "cand_latent_center", 0),
                             state_canon=getattr(args, "state_canon", 0), state_key=getattr(args, "state_key", 0),
                             card_content=getattr(args, "card_content", 0), emb_scale=getattr(args, "emb_scale", 0.0),
                             cand_origin=getattr(args, "cand_origin", 0))


# Weights a pilot may lack when a checkpoint is read into a larger architecture: new modules that start as the
# identity or at zero, so the larger pilot plays as the checkpoint did (log #77; the lab's branches, rl/lab.py). The
# memory core (mem_*) starts at zero through mem_out; history tokens (hist_*) and a separate deck encoder (deck_*) do
# not start as the identity (new tokens to attend to; the board encoder stops seeing the deck), log #94. The chain head
# (chain_*) starts as the identity: chain_cross's outputs are zero from __init__.
NEW_WEIGHTS = ("cross_extra.", "cand_blocks.", "vquery", "vcross.", "vblocks.", "ln_v.", "owner.", "same_bias",
               "ability_proj.", "aux_head.", "mem_", "hist_", "deck_null", "deck_blocks.", "fuse.", "chain_",
               "g_lat", "g_ptr", "lat_", "ptr_", "flag_emb", "g_flag", "key_bias")
ZERO_AT_GROWTH = ("owner.weight", "ability_proj.weight", "ability_proj.bias",   # additive inputs: start at 0
                  "fuse.0.proj.weight", "fuse.0.proj.bias", "fuse.0.ff.2.weight", "fuse.0.ff.2.bias")   # deck fusion: a pass-through
DEEPER_ZERO = ("proj.weight", "proj.bias", "ff.2.weight", "ff.2.bias")    # a new encoder block: a pass-through


def token_net(cfg: dict, info: dict, **overrides):
    """A TokenPointerNet with a checkpoint's architecture (TokenPointerNet.config()) plus `overrides`, sized to the
    workers' current token bounds (info), as build_model does."""
    c = {"count_features": False, "cross_layers": 1, "cand_self": 0, **cfg, **overrides}   # older configs lack these
    return build_model(argparse.Namespace(model="tokens", d=c["d"], tok_layers=c["layers"], heads=c["heads"],
                                          **{k: c[k] for k in ("count_features", "cross_layers", "cand_self", "n_agents",
                                                               "card_inputs", "deck_tokens", "slot_bind", "ability_text",
                                                               "deck_mode", "deck_layers", "history", "memory",
                                                               "value_tower", "value_query", "chain", "cand_latent", "cand_latent_zone",
                                                               "cand_latent_gate", "cand_latent_pick", "cand_latent_center", "state_canon", "state_key",
                                                               "card_content", "emb_scale", "cand_origin")
                                                               if k in c}), info)


def load_grown(model, state: dict) -> list:
    """Loads `state` into `model`, which may have new modules (NEW_WEIGHTS) the state lacks; returns those. Encoder
    blocks beyond the state's (a deeper pilot, log #106) start as the identity: their attention and MLP outputs at 0."""
    missing, unexpected = model.load_state_dict(state, strict=False)
    assert not unexpected, f"checkpoint has weights this model lacks: {unexpected[:5]}"
    depth = len({k.split(".")[1] for k in state if k.startswith("blocks.")})
    deeper = lambda k: k.startswith("blocks.") and int(k.split(".")[1]) >= depth
    assert all(k.startswith(NEW_WEIGHTS) or deeper(k) for k in missing), f"missing weights: {missing[:5]}"
    with torch.no_grad():
        for n, p in model.named_parameters():
            if n in missing and (n in ZERO_AT_GROWTH or deeper(n) and n.split(".", 2)[2] in DEEPER_ZERO):
                p.zero_()
    return missing


def remap_adam(opt_state: dict, old_names: list, model) -> dict:
    """An Adam state_dict for `model`'s parameters, from one saved for parameters named `old_names` (in their
    order): each parameter the old model had keeps its moments, by name; a new one starts without."""
    by_name = {n: opt_state["state"][i] for i, n in enumerate(old_names) if i in opt_state["state"]}
    names = [n for n, _ in model.named_parameters()]
    group = {**opt_state["param_groups"][0], "params": list(range(len(names)))}
    return {"state": {i: by_name[n] for i, n in enumerate(names) if n in by_name}, "param_groups": [group]}


def export_policy(model, path: Path, kind: str = "tokens") -> str:
    """Exports a token pilot for evaluate.js; returns its agent spec (kind: 'tokens', the only encoding left; an
    identity model exports with rl/model.py export_onnx)."""
    assert kind == "tokens", f"export_policy: only a token pilot exports here, not {kind}"
    from rl.token_model import export_token_onnx
    export_token_onnx(model, str(path))
    return f"onnxtok:{path}:greedy"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--matchups-file", required=True, help="JSON [[deckA, deckB], ...]: names or {name, cards} decklists")
    ap.add_argument("--iterations", type=int, default=100)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--transitions", type=int, default=4096, help="per worker per iteration")
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--inference", choices=["gpu"], default="gpu",
                    help="the policy runs here for the workers (rl/remote.py); the only choice left")
    ap.add_argument("--model", choices=["tokens"], default="tokens", help="TokenPointerNet; the only choice left")
    ap.add_argument("--d", type=int, default=192, help="token model width")
    ap.add_argument("--tok-layers", type=int, default=3)
    ap.add_argument("--heads", type=int, default=4)
    ap.add_argument("--slot-bind", action="store_true",
                    help="token model: slot embedding, attached-Energy counts and a same-slot attention bias")
    ap.add_argument("--deck-mode", choices=["joint", "cross"], default="joint",
                    help="token model: deck tokens in the board encoder, or a deck-free board encoder that then "
                         "cross-attends to a separate deck encoder")
    ap.add_argument("--no-deck-tokens", dest="deck_tokens", action="store_false",
                    help="token model: hide the decklist tokens (own unseen cards, opponent's list)")
    ap.add_argument("--history", type=int, default=0,
                    help="token model: read the action history of the last N turns (env/tokens.js history tokens; 0 = none)")
    ap.add_argument("--memory", choices=["none", "gru", "attn"], default="none",
                    help="token model: a recurrent core over the player's own decisions (rl/token_model.py, log #76)")
    ap.add_argument("--chain", type=int, default=0,
                    help="token model: the chain head, the player's own decisions this turn as the last K candidate rows "
                         "(rl/token_model.py chain; 0 = none)")
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--minibatch", type=int, default=4096)
    ap.add_argument("--micro-batch", type=int, default=0, help="split each minibatch into chunks of this size (0 = whole)")
    ap.add_argument("--gpu-mem-fraction", type=float, default=0.8,
                    help="cap this process's GPU memory (at most 0.8, rl/limits.py)")
    ap.add_argument("--amp", action="store_true", help="bfloat16 autocast for the forward pass on the GPU")
    ap.add_argument("--search-distill", type=float, default=0.0,
                    help="soft search targets (C49, log #169): weight of KL(target || policy) over the searched moves, "
                         "averaged over all rows (0 off)")
    ap.add_argument("--probe-p", type=float, default=0.05, help="--search-distill: share of main-phase decisions searched")
    ap.add_argument("--probe-k", type=int, default=4, help="--search-distill: the pilot's most likely moves searched")
    ap.add_argument("--probe-dets", type=int, default=4, help="--search-distill: re-dealt copies shared by the moves (CRN)")
    ap.add_argument("--distill-tau", type=float, default=0.1, help="--search-distill: target pi * exp(clip((q - mean q) / tau))")
    ap.add_argument("--distill-clip", type=float, default=1.0, help="--search-distill: the clip of (q - mean q) / tau")
    ap.add_argument("--round-turns", type=round_turns, default=0,
                    help='the 2000 round rule (log #160): "T" cuts every game at turn T, "A-B" draws T per deal from A..B; '
                         'an unfinished game goes to the player with more Prizes taken, rewards are the event points')
    ap.add_argument("--deckout-win", type=float, default=1.0,
                    help="reward for a win by deck-out (prizes or knockout: 1), to pay less for stalling")
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--clip", type=float, default=0.2)
    ap.add_argument("--vf", type=float, default=0.5)
    ap.add_argument("--ent", type=float, default=0.01)
    ap.add_argument("--max-grad-norm", type=float, default=0.5)
    ap.add_argument("--shaping", type=float, default=0.0, help="prize-shaping weight at iteration 0 (shape_rewards)")
    ap.add_argument("--shaping-iters", type=int, default=100, help="iterations over which the shaping fades to 0")
    ap.add_argument("--pace", type=float, default=0.25, help="rest this x each served batch's GPU time")
    ap.add_argument("--snapshot-every", type=int, default=10, help="save model_it*.pt every N iterations")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--stop-file", default="", help="stop after the iteration in which this file exists (log #154)")
    ap.add_argument("--init-from", help="start from this checkpoint's weights (e.g. to pilot new decks)")
    args = ap.parse_args(argv)

    run = ROOT / args.run
    run.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    limits.apply(device, args.workers, args.gpu_mem_fraction)
    torch.manual_seed(args.seed)
    random.seed(args.seed)

    from rl.remote import RemotePool
    pool = RemotePool(args.workers)
    pool.pace = args.pace
    info = pool.ask_all([{"cmd": "info"}] * args.workers)[0]
    matchups = json.load(open(args.matchups_file))
    model = build_model(args, info).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, eps=1e-5)
    start = 0
    ckpt = run / "checkpoint.pt"
    if args.init_from:
        # Layers the checkpoint lacks (extra candidate blocks) keep their identity initialization.
        missing, unexpected = model.load_state_dict(torch.load(ROOT / args.init_from, map_location=device)["model"],
                                                    strict=False)
        assert not unexpected, f"checkpoint has weights this model lacks: {unexpected[:5]}"
        assert all(k.startswith(("cross_extra.", "cand_blocks.", "vquery", "vcross.", "vblocks.", "ln_v.", "chain_", "flag_emb", "g_flag", "key_bias"))
                   for k in missing), f"missing weights: {missing[:5]}"
        if missing:
            print(f"init-from: {len(missing)} new weights left at identity ({sorted({k.split('.')[0] for k in missing})})")
    if args.resume and ckpt.exists():
        state = torch.load(ckpt, map_location=device)
        model.load_state_dict(state["model"])
        opt.load_state_dict(state["opt"])
        start = state["iteration"] + 1
    (run / "config.json").write_text(json.dumps({**vars(args), "matchups": matchups, "model_config": model.config(),
                                                 "device": device}, indent=1))
    log = open(run / "log.jsonl", "a")
    print(f"device {device}, model {args.model}, inference {args.inference}, "
          f"params {sum(p.numel() for p in model.parameters() if p.requires_grad)}, matchups {len(matchups)}", flush=True)

    try:
        for it in range(start, args.iterations):
            t0 = time.time()
            msgs = [{"cmd": "collect", "encoding": args.model, "transitions": args.transitions,
                     "concurrency": args.concurrency, "deckoutWin": args.deckout_win, "seed": args.seed * 1_000_003 + it * 1009 + w,
                     **({"roundTurns": args.round_turns} if getattr(args, "round_turns", 0) else {}),
                     **({"probe": {"p": args.probe_p, "k": args.probe_k, "dets": args.probe_dets, "maxSteps": 40,
                                   "seed": args.seed * 7919 + it}} if getattr(args, "search_distill", 0) else {}),
                     "matchups": matchups, "opponents": [{"spec": "self", "weight": 1.0}],
                     "out": str(run / f"rollout_w{w}.bin"), "history": getattr(args, "history", 0),
                     "chain": getattr(args, "chain", 0),
                     "canon": int(getattr(model, "cfg", {}).get("state_canon", 0) or 0)} for w in range(args.workers)]
            replies = pool.collect(msgs, {0: model.eval()}, device)
            model.train()
            t1 = time.time()
            rolls = [read_rollout(r["out"]) for r in replies]
            batch = concat(rolls)
            probe_row = None
            if getattr(args, "search_distill", 0):          # soft search targets: each probe's moves and mean scores
                batch["probe_c"], batch["probe_q"], probe_row = probe_targets(replies, rolls, args.probe_k)
            lam_shape = args.shaping * max(0.0, 1.0 - it / max(args.shaping_iters, 1))
            if lam_shape:
                batch["reward"] = shape_rewards(batch, lam_shape, info["tokens"]["prizeGlob"])
            batch["adv"], batch["ret"] = advantages(batch, args.gamma, args.lam)
            batch["inputs"] = model_inputs(batch, args.model)
            stats = ppo_update(model, opt, batch, args, device)
            t2 = time.time()
            ev_mc, ev_open = (None if x is None else round(x, 4) for x in explained_variance(batch))

            games = [g for r in replies for g in r["results"]]
            vs = {}
            for g in games:
                for seat in ("1", "2"):
                    if g["seats"][seat] != "learner":
                        continue
                    other = g["seats"]["2" if seat == "1" else "1"]
                    w = 1.0 if g["winner"] == int(seat) else 0.5 if g["winner"] not in (1, 2) else 0.0
                    vs.setdefault(other, []).append(w)
            row = {"iteration": it, "transitions": int(len(batch["action"])), "games": len(games),
                   "steps_per_game": float(np.mean([g["steps"] for g in games])) if games else 0,
                   "errors": sum(1 for g in games if g.get("error")),
                   "cut": sum(1 for g in games if not g.get("ending") and not g.get("error")),
                   "endings": dict(collections.Counter(g.get("ending") or "none" for g in games)),
                   "endings_by_kind": ending_kinds(games),
                   "win_vs": {k: round(float(np.mean(v)), 4) for k, v in vs.items()},
                   "shaping": round(lam_shape, 5), "collect_s": round(t1 - t0, 1), "train_s": round(t2 - t1, 1), **{k: round(v, 5) for k, v in stats.items()},
                   "ev_mc": ev_mc, "ev_open": ev_open, "lr": opt.param_groups[0]["lr"],
                   **({"sampled": round(float(batch["sampled"].mean()), 4)} if "sampled" in batch else {}),
                   **({"search_distill": probe_row} if probe_row is not None else {})}
            log.write(json.dumps(row) + "\n")
            log.flush()
            print(f"it {it:4d}  T={row['transitions']:6d} games={row['games']:4d} len={row['steps_per_game']:.0f} "
                  f"ent={stats['entropy']:.3f} kl={stats['kl']:.4f} clip={stats['clipfrac']:.3f} v={stats['v_loss']:.3f} "
                  f"win={row['win_vs']} collect {row['collect_s']}s train {row['train_s']}s", flush=True)

            if (it + 1) % args.snapshot_every == 0:
                save_atomic({"model": model.state_dict(), "config": model.config()}, run / f"model_it{it:05d}.pt")
            save_atomic({"model": model.state_dict(), "opt": opt.state_dict(), "iteration": it,
                         "config": model.config()}, ckpt)
            if args.stop_file and Path(args.stop_file).exists():
                print(f"stop file {args.stop_file} after iteration {it}", flush=True)
                break
    finally:
        pool.close()
        log.close()


if __name__ == "__main__":
    main()
