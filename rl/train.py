"""PPO self-play training (plan items A1.5, A3, A4).

Rollouts are played by Node workers. Two ways to run the policy for them:
  --inference onnx  each worker runs the current policy exported to ONNX (env/rollout_worker.js);
                    identity model only
  --inference gpu   workers send their decisions here and the policy runs on the GPU in large
                    batches across workers (env/remote_worker.js, rl/remote.py); needed for the
                    token model, and faster for big networks
Models: --model identity (IdentityMLP over env/encode.js) or tokens (TokenPointerNet over
env/tokens.js). One iteration: collect N transitions per worker -> PPO epochs -> log.

Opponents: the learner plays itself ("self") and, with --league, past snapshots of itself
(every --snapshot-every iterations), and optionally fixed bots (--bot-opponents heuristic=0.1).
Both seats are recorded when it plays itself.

Example (A3, one matchup, both directions):
  .venv/Scripts/python -m rl.train --run runs/a3 --matchup "15+ #2 William Lieu|15+ #1 Andrew Marshall" \
      --both-directions --iterations 200 --league --eval-every 20
"""
import argparse
import collections
import json
import os
import random
import subprocess
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from rl import limits
from rl.model import IdentityMLP, export_onnx
from rl.rollouts import read_rollout, concat

ROOT = Path(__file__).resolve().parent.parent
TOKEN_FIELDS = ("obs.tokCard", "obs.tokKind", "obs.tokAux", "obs.glob", "obs.slots", "obs.cand", "obs.nCand")


class Workers:
    """ONNX rollout workers, one JSON command per line each way."""

    def __init__(self, n: int):
        self.procs = [subprocess.Popen(["node", str(ROOT / "env" / "rollout_worker.js")], cwd=ROOT,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
                      for _ in range(n)]

    def ask_all(self, msgs: list) -> list:
        for p, m in zip(self.procs, msgs):
            p.stdin.write(json.dumps(m) + "\n")
            p.stdin.flush()
        out = []
        for p in self.procs:
            line = p.stdout.readline()
            if not line:
                raise RuntimeError("rollout worker exited")
            reply = json.loads(line)
            if not reply.get("ok"):
                raise RuntimeError("rollout worker failed: " + reply.get("error", "?"))
            out.append(reply)
        return out

    def close(self):
        for p in self.procs:
            try:
                p.stdin.write(json.dumps({"cmd": "quit"}) + "\n")
                p.stdin.flush()
            except OSError:
                pass


def advantages(r: dict, gamma: float, lam: float, lam_turn: float = None):
    """GAE per trajectory (one player's decisions in one game, in order); reward only at the end. lam_turn (log #96):
    the lambda between two decisions of the same game turn (glob byte 0, env/tokens.js), lam across turns, so a turn's
    outcome credits every decision of that turn in full with lam_turn = 1."""
    T = len(r["action"])
    adv = np.zeros(T, dtype=np.float32)
    nxt_v, nxt_a, nxt_turn = {}, {}, {}
    value, reward, done, traj = r["value"], r["reward"], r["done"], r["traj"]
    turn = r["obs.glob"].reshape(T, -1)[:, 0] if lam_turn is not None else None
    for t in range(T - 1, -1, -1):
        k = traj[t]
        if done[t]:
            v1, a1 = 0.0, 0.0
        else:
            v1, a1 = nxt_v.get(k, 0.0), nxt_a.get(k, 0.0)
        delta = reward[t] + gamma * v1 - value[t]
        l = lam_turn if turn is not None and nxt_turn.get(k) == turn[t] else lam
        adv[t] = delta + gamma * l * a1
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


def lr_at(it: int, args) -> float:
    """--lr until --lr-decay-start, then linear to --lr-final at --lr-decay-end (default the last iteration),
    held after; just --lr without --lr-final."""
    if args.lr_final is None:
        return args.lr
    end = args.iterations - 1 if args.lr_decay_end is None else args.lr_decay_end
    f = min(max((it - args.lr_decay_start) / max(end - args.lr_decay_start, 1), 0.0), 1.0)
    return (1 - f) * args.lr + f * args.lr_final


def schedule_lr(opt, it: int, args):
    """Sets every param group's lr to lr_at(it) with --lr-final; without it, leaves the optimizer alone."""
    if args.lr_final is not None:
        for group in opt.param_groups:
            group["lr"] = lr_at(it, args)


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


def aux_targets(r: dict) -> np.ndarray:
    """[T, 2] targets of the auxiliary heads (TokenPointerNet aux_heads), from a rollout batch alone, so any game has
    them: the deciding player's decisions left until its trajectory ends, as log(1 + k) / log(201), and the
    trajectory's result (the sum of its unshaped rewards; call before shape_rewards). A trajectory's rows may be
    interleaved with others' but are in decision order."""
    traj = np.asarray(r["traj"])
    T = len(traj)
    order = np.lexsort((np.arange(T), traj))
    tj = traj[order]
    starts = np.flatnonzero(np.r_[True, tj[1:] != tj[:-1]])
    lens = np.diff(np.r_[starts, T])
    rank = np.arange(T) - np.repeat(starts, lens)
    left = np.empty(T)
    left[order] = np.repeat(lens, lens) - 1 - rank
    result = np.empty(T)
    result[order] = np.repeat(np.add.reduceat(np.asarray(r["reward"], dtype=np.float64)[order], starts), lens)
    return np.stack([np.log1p(left) / np.log(201.0), result], 1).astype(np.float32)


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


def model_inputs(batch: dict, kind: str) -> list:
    """The network inputs for every transition, as arrays with the batch dimension first."""
    T = len(batch["action"])
    if kind == "tokens":
        return [batch[k].reshape(T, -1) if k != "obs.nCand" else batch[k] for k in TOKEN_FIELDS]
    return [batch["obs"]]


def ppo_update(model, opt, batch, args, device):
    T = len(batch["action"])
    inputs = [torch.from_numpy(np.ascontiguousarray(x)).to(device) for x in batch["inputs"]]
    act = torch.from_numpy(batch["action"].astype(np.int64)).to(device)
    old_logp = torch.from_numpy(batch["logp"]).to(device)
    adv = torch.from_numpy(batch["adv"]).to(device)
    ret = torch.from_numpy(batch["ret"]).to(device)
    old_v = torch.from_numpy(batch["value"]).to(device)
    offsets = torch.from_numpy(batch["legal_offsets"].astype(np.int64)).to(device)
    # agent-conditioned network (rl/league.py): each transition's agent id
    agents = torch.from_numpy(batch["agent"].astype(np.int64)).to(device) if "agent" in batch else None
    ids = torch.from_numpy(batch["legal_ids"].astype(np.int64)).to(device)
    # Mostly greedy collection (--explore, log #81): only the sampled decisions train the policy, since at the others
    # the recorded log-probability is not what the move was chosen with; the value and the entropy use every decision.
    pol = torch.from_numpy(batch["sampled"].astype(np.float32)).to(device) if "sampled" in batch \
        else torch.ones(T, device=device)
    sel = pol > 0 if int((pol > 0).sum()) >= 2 else torch.ones(T, dtype=torch.bool, device=device)
    adv = (adv - adv[sel].mean()) / (adv[sel].std() + 1e-8)
    stats = {"pi_loss": 0.0, "v_loss": 0.0, "entropy": 0.0, "kl": 0.0, "clipfrac": 0.0}
    aux_w = getattr(args, "aux", 0.0) if getattr(model, "aux_heads", 0) and "aux_target" in batch else 0.0
    if aux_w:
        aux_t = torch.from_numpy(batch["aux_target"]).to(device)
        stats["aux_loss"] = 0.0
    # Expert iteration (log #96): at decisions a turn-level search scored (rl/metagame.py --distill), the cross-entropy
    # toward the option it found best, at weight args.distill, averaged over the minibatch's searched decisions.
    dist_w = getattr(args, "distill", 0.0) if "search_target" in batch else 0.0
    if dist_w:
        s_t = torch.from_numpy(batch["search_target"].astype(np.int64)).to(device)
        stats["distill"] = 0.0
        stats["distill_agree"] = 0.0
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
        S = float(sum((s_t[j] >= 0).sum() for j, _ in micros)) if dist_w else 0.0   # ... that a search scored
        for j, mem_lens in micros:
            w = len(j) / rows
            pm = pol[j]
            wp = float(pm.sum()) / M if M > 0 else 0.0
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=args.amp and device == "cuda"):
                xs = [x[j] for x in inputs]
                if tok_len is not None:
                    L = int(tok_len[j].max())
                    xs[:3] = [x[:, :L] for x in xs[:3]]
                kw = {"agent": agents[j]} if agents is not None else {}
                if memory:
                    kw["mem_lens"] = mem_lens
                if aux_w:
                    logits, v, pooled = model(*xs, return_pooled=True, **kw)
                    aux_loss = ((model.aux_head(pooled).float() - aux_t[j]) ** 2).mean()
                else:
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
            vclip = getattr(args, "value_clip", None)
            vclip = args.clip if vclip is None else vclip
            if vclip > 0:
                v_clipped = old_v[j] + (v - old_v[j]).clamp(-vclip, vclip)
                v_loss = torch.max((v - ret[j]) ** 2, (v_clipped - ret[j]) ** 2).mean()
            else:
                v_loss = ((v - ret[j]) ** 2).mean()
            # the policy term is the mean over the minibatch's policy decisions (all of them without --explore)
            loss = (pi_rows.sum() / M if M > 0 else 0.0 * pi_rows.sum()) + w * (args.vf * v_loss - args.ent * entropy)
            if aux_w:
                loss = loss + w * aux_w * aux_loss
            if dist_w and S > 0:
                srow = s_t[j] >= 0
                if srow.any():
                    ce = -logp_all[srow].gather(1, s_t[j][srow, None]).squeeze(1)
                    loss = loss + dist_w * ce.sum() / S
                    with torch.no_grad():
                        mb_stats["distill"] += ce.sum().item() / S
                        mb_stats["distill_agree"] += (logp_all[srow].argmax(1) == s_t[j][srow]).float().sum().item() / S
            loss.backward()
            pace.tick()                   # per micro-batch: the same share of rest, in finer slices
            with torch.no_grad():
                n_pm = pm.sum().clamp(min=1)
                mb_stats["pi_loss"] += wp * pi_loss.item()
                mb_stats["v_loss"] += w * v_loss.item()
                mb_stats["entropy"] += w * entropy.item()
                if aux_w:
                    mb_stats["aux_loss"] += w * aux_loss.item()
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
    return {**{k: v / max(n, 1) for k, v in stats.items()}, "grad_norm": grad_norm / max(n, 1),
            "kl_last": kl_last / max(n_last, 1)}


def evaluate(policy_spec: str, opponent: str, d1: str, d2: str, games: int, workers: int, seed: int, tag: str) -> dict:
    """Seat- and deck-swapped match of the policy (greedy) against a fixed opponent (env/tools/evaluate.js)."""
    out = ROOT / "runs" / f".eval-{tag}-{opponent}.json"
    cmd = ["node", str(ROOT / "env" / "tools" / "evaluate.js"), "--x", policy_spec, "--y", opponent,
           "--d1", d1, "--d2", d2, "--games", str(games), "--workers", str(workers), "--concurrency", "8",
           "--seed", str(seed), "--json", str(out)]
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    r = json.load(open(out))
    out.unlink(missing_ok=True)
    return {"all": round(r["all"]["xWinRate"], 4), "ci95": round(r["all"]["ci95"], 4),
            "dir1": round(r["dir1"]["xWinRate"], 4), "dir2": round(r["dir2"]["xWinRate"], 4)}


def build_model(args, info):
    if args.model == "tokens":
        from rl.token_model import build_token_model
        t = info["tokens"]
        return build_token_model(str(ROOT / "notes/data/cards/pool.json"), str(ROOT / "notes/data/cards/text_emb.npy"),
                                 t["names"], t["globF"], t["slotF"], t["maxTok"], t["maxCand"],
                                 d=args.d, layers=args.tok_layers, heads=args.heads,
                                 count_features=args.count_features, cross_layers=args.cross_layers,
                                 cand_self=args.cand_self, n_agents=getattr(args, "n_agents", 0),
                                 card_inputs=getattr(args, "card_inputs", "all"), deck_tokens=getattr(args, "deck_tokens", True),
                                 slot_bind=getattr(args, "slot_bind", False), ability_text=getattr(args, "ability_text", False),
                                 deck_mode=getattr(args, "deck_mode", "joint"), deck_layers=getattr(args, "deck_layers", 1),
                                 history=getattr(args, "history", 0), memory=getattr(args, "memory", "none"),
                                 value_tower=getattr(args, "value_tower", 0), value_query=getattr(args, "value_query", 0),
                                 aux_heads=getattr(args, "aux_heads", 0))
    i = info["identity"] if "identity" in info else info
    return IdentityMLP(i["obsSize"], i["actionSize"], args.hidden, args.layers)


# Weights a pilot may lack when a checkpoint is read into a larger architecture: new modules that start as the
# identity or at zero, so the larger pilot plays as the checkpoint did (log #77; the lab's branches, rl/lab.py). The
# memory core (mem_*) starts at zero through mem_out; history tokens (hist_*) and a separate deck encoder (deck_*) do
# not start as the identity (new tokens to attend to; the board encoder stops seeing the deck), log #94.
NEW_WEIGHTS = ("cross_extra.", "cand_blocks.", "vquery", "vcross.", "vblocks.", "ln_v.", "owner.", "same_bias",
               "ability_proj.", "aux_head.", "mem_", "hist_", "deck_null", "deck_blocks.", "fuse.")
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
                                                               "value_tower", "value_query", "aux_heads") if k in c}), info)


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


def export_policy(model, path: Path, kind: str) -> str:
    """Exports for evaluate.js; returns its agent spec."""
    if kind == "tokens":
        from rl.token_model import export_token_onnx
        export_token_onnx(model, str(path))
        return f"onnxtok:{path}:greedy"
    export_onnx(model, str(path))
    return f"onnx:{path}:greedy"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--matchups-file", help="JSON [[deckA, deckB], ...]: names or {name, cards} decklists")
    ap.add_argument("--matchup", action="append", default=[],
                    help='"learner deck|opponent deck" (substring of an archived deck name); repeatable; "all" = every pair')
    ap.add_argument("--both-directions", action="store_true", help="also train each matchup with the decks swapped")
    ap.add_argument("--iterations", type=int, default=100)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--transitions", type=int, default=4096, help="per worker per iteration")
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--inference", choices=["onnx", "gpu"], default="onnx")
    ap.add_argument("--model", choices=["identity", "tokens"], default="identity")
    ap.add_argument("--hidden", type=int, default=512)
    ap.add_argument("--layers", type=int, default=2)
    ap.add_argument("--d", type=int, default=192, help="token model width")
    ap.add_argument("--tok-layers", type=int, default=3)
    ap.add_argument("--heads", type=int, default=4)
    ap.add_argument("--cross-layers", type=int, default=1, help="token model: candidate cross-attention blocks")
    ap.add_argument("--cand-self", type=int, default=0, help="token model: blocks where candidates attend to each other")
    ap.add_argument("--count-features", action="store_true",
                    help="token model: ordered count features (rl/token_model.py count_features)")
    ap.add_argument("--card-inputs", choices=["all", "feats", "ids"], default="all",
                    help="token model: card features + text + residual, no text, or the learned embedding only")
    ap.add_argument("--ability-text", action="store_true",
                    help="token model: attack / Power options also read that ability's own rules text")
    ap.add_argument("--slot-bind", action="store_true",
                    help="token model: slot embedding, attached-Energy counts and a same-slot attention bias")
    ap.add_argument("--deck-mode", choices=["joint", "cross", "interleave"], default="joint",
                    help="token model: deck tokens in the board encoder, or a deck-free board encoder that then "
                         "cross-attends to a separate deck encoder (once, or after every layer)")
    ap.add_argument("--deck-layers", type=int, default=1, help="token model: deck encoder blocks (deck-mode cross / interleave)")
    ap.add_argument("--no-deck-tokens", dest="deck_tokens", action="store_false",
                    help="token model: hide the decklist tokens (own unseen cards, opponent's list)")
    ap.add_argument("--history", type=int, default=0,
                    help="token model: read the action history of the last N turns (env/tokens.js history tokens; 0 = none)")
    ap.add_argument("--memory", choices=["none", "gru", "attn"], default="none",
                    help="token model: a recurrent core over the player's own decisions (rl/token_model.py, log #76)")
    ap.add_argument("--value-tower", type=int, default=0,
                    help="token model: the value reads its own N transformer blocks over the embedded tokens (log #77)")
    ap.add_argument("--value-query", type=int, default=0,
                    help="token model: the value reads the state by cross-attention with N learned queries (log #77)")
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--lr-final", type=float, default=None,
                    help="decay the lr linearly to this (lr_at; overrides a resumed optimizer's lr); default constant")
    ap.add_argument("--lr-decay-start", type=int, default=0, help="iteration where the lr decay starts")
    ap.add_argument("--lr-decay-end", type=int, default=None, help="iteration where it reaches --lr-final (default the last)")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--minibatch", type=int, default=4096)
    ap.add_argument("--micro-batch", type=int, default=0, help="split each minibatch into chunks of this size (0 = whole)")
    ap.add_argument("--gpu-mem-fraction", type=float, default=0.8,
                    help="cap this process's GPU memory (at most 0.8, rl/limits.py)")
    ap.add_argument("--amp", action="store_true", help="bfloat16 autocast for the forward pass on the GPU")
    ap.add_argument("--deckout-win", type=float, default=1.0,
                    help="reward for a win by deck-out (prizes or knockout: 1), to pay less for stalling")
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--clip", type=float, default=0.2)
    ap.add_argument("--value-clip", type=float, default=None,
                    help="PPO's clip of the value's change per update (default --clip; 0 = none; log #77)")
    ap.add_argument("--lam-value", type=float, default=None,
                    help="GAE lambda of the value targets (default --lam; 1 = Monte Carlo returns; log #77)")
    ap.add_argument("--vf", type=float, default=0.5)
    ap.add_argument("--ent", type=float, default=0.01)
    ap.add_argument("--explore", type=float, default=None,
                    help="mostly greedy collection (gpu inference; log #81): each decision samples with this probability "
                         "and otherwise plays the top option; only the sampled ones train the policy. Default: sample all")
    ap.add_argument("--policy-share", type=float, default=None,
                    help="train the policy on only this random share of the (sampled) decisions; the value on all "
                         "(the control for --explore's thinner policy data, log #82)")
    ap.add_argument("--max-grad-norm", type=float, default=0.5)
    ap.add_argument("--shaping", type=float, default=0.0, help="prize-shaping weight at iteration 0 (shape_rewards)")
    ap.add_argument("--shaping-iters", type=int, default=100, help="iterations over which the shaping fades to 0")
    ap.add_argument("--pace", type=float, default=0.25, help="gpu inference: rest this x each served batch's GPU time")
    ap.add_argument("--league", action="store_true", help="also play past snapshots")
    ap.add_argument("--snapshot-every", type=int, default=10)
    ap.add_argument("--max-snapshots", type=int, default=8, help="league size kept in play (gpu inference)")
    ap.add_argument("--self-weight", type=float, default=0.5, help="share of games against itself with --league")
    ap.add_argument("--bot-opponents", default="", help='fixed bots to play too, e.g. "heuristic=0.1"')
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--init-from", help="start from this checkpoint's weights (e.g. to pilot new decks)")
    ap.add_argument("--eval-every", type=int, default=0, help="evaluate against --eval-opponents every N iterations")
    ap.add_argument("--eval-opponents", default="simplebot,heuristic")
    ap.add_argument("--eval-games", type=int, default=200)
    ap.add_argument("--eval-workers", type=int, default=8)
    args = ap.parse_args(argv)
    if args.model == "tokens" and args.inference != "gpu":
        raise SystemExit("the token model needs --inference gpu")
    if args.explore is not None and (args.inference != "gpu" or not 0 < args.explore <= 1):
        raise SystemExit("--explore needs --inference gpu and a probability in (0, 1]")

    run = ROOT / args.run
    (run / "policies").mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    args.eval_workers = limits.cap_workers(args.eval_workers)
    limits.apply(device, args.workers, args.gpu_mem_fraction)
    torch.manual_seed(args.seed)
    random.seed(args.seed)


    if args.inference == "gpu":
        from rl.remote import RemotePool
        pool = RemotePool(args.workers)
        pool.pace = args.pace
    else:
        pool = Workers(args.workers)
    info = pool.ask_all([{"cmd": "info"}] * args.workers)[0]
    matchups = json.load(open(args.matchups_file)) if args.matchups_file else []
    for m in args.matchup:
        if m == "all":                     # every ordered pair of archived decks, mirrors included
            names = info["decks"]
            matchups += [[a, b] for a in names for b in names]
            continue
        a, b = m.split("|")
        matchups.append([a.strip(), b.strip()])
        if args.both_directions and a.strip() != b.strip():
            matchups.append([b.strip(), a.strip()])
    model = build_model(args, info).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, eps=1e-5)
    start = 0
    snapshots = []            # onnx: policy files; gpu: state-dict files
    ckpt = run / "checkpoint.pt"
    if args.init_from:
        # Layers the checkpoint lacks (extra candidate blocks) keep their identity initialization.
        missing, unexpected = model.load_state_dict(torch.load(ROOT / args.init_from, map_location=device)["model"],
                                                    strict=False)
        assert not unexpected, f"checkpoint has weights this model lacks: {unexpected[:5]}"
        assert all(k.startswith(("cross_extra.", "cand_blocks.", "vquery", "vcross.", "vblocks.", "ln_v."))
                   for k in missing), f"missing weights: {missing[:5]}"
        if missing:
            print(f"init-from: {len(missing)} new weights left at identity ({sorted({k.split('.')[0] for k in missing})})")
    if args.resume and ckpt.exists():
        state = torch.load(ckpt, map_location=device)
        model.load_state_dict(state["model"])
        opt.load_state_dict(state["opt"])
        start = state["iteration"] + 1
        snapshots = state.get("snapshots", [])
    (run / "config.json").write_text(json.dumps({**vars(args), "matchups": matchups, "model_config": model.config(),
                                                 "device": device}, indent=1))
    log = open(run / "log.jsonl", "a")
    print(f"device {device}, model {args.model}, inference {args.inference}, "
          f"params {sum(p.numel() for p in model.parameters() if p.requires_grad)}, matchups {len(matchups)}", flush=True)
    bots = []
    for b in filter(None, args.bot_opponents.split(",")):
        name, w = b.split("=")
        bots.append({"spec": name, "weight": float(w)})
    snapshot_models = {}

    try:
        for it in range(start, args.iterations):
            schedule_lr(opt, it, args)
            t0 = time.time()
            league = snapshots[-args.max_snapshots:]
            if args.inference == "gpu":
                opponents = [{"spec": "self", "weight": 1.0}]
                if args.league and league:
                    opponents = [{"spec": "self", "weight": args.self_weight}] + [
                        {"spec": f"slot:{k + 1}", "weight": (1 - args.self_weight) / len(league)} for k in range(len(league))]
                for k, f in enumerate(league):
                    if f not in snapshot_models:
                        m = build_model(args, info).to(device)
                        m.load_state_dict(torch.load(f, map_location=device)["model"])
                        snapshot_models[f] = m.eval()
                for f in list(snapshot_models):
                    if f not in league:
                        del snapshot_models[f]
                models = {0: model.eval(), **{k + 1: snapshot_models[f] for k, f in enumerate(league)}}
            else:
                policy = run / "policies" / f"it{it:05d}.onnx"
                export_onnx(model, str(policy))
                opponents = [{"spec": "self", "weight": 1.0}]
                if args.league and league:
                    opponents = [{"spec": "self", "weight": args.self_weight}] + [
                        {"spec": "onnx:" + s, "weight": (1 - args.self_weight) / len(league)} for s in league]
            opponents += bots
            msgs = [{"cmd": "collect", "encoding": args.model, "transitions": args.transitions,
                     "concurrency": args.concurrency, "deckoutWin": args.deckout_win, "seed": args.seed * 1_000_003 + it * 1009 + w,
                     "matchups": matchups, "opponents": opponents, "out": str(run / f"rollout_w{w}.bin"),
                     "history": getattr(args, "history", 0),
                     **({"explore": args.explore} if args.explore is not None else {}),
                     **({"model": str(policy)} if args.inference == "onnx" else {})} for w in range(args.workers)]
            replies = pool.collect(msgs, models, device) if args.inference == "gpu" else pool.ask_all(msgs)
            model.train()
            t1 = time.time()
            batch = concat([read_rollout(r["out"]) for r in replies])
            if args.policy_share is not None:      # the control for --explore (log #82): only a random share trains the policy
                keep = np.random.default_rng(args.seed * 7919 + it).random(len(batch["action"])) < args.policy_share
                batch["sampled"] = (batch.get("sampled", np.ones(len(keep), np.uint8)) * keep).astype(np.uint8)
            lam_shape = args.shaping * max(0.0, 1.0 - it / max(args.shaping_iters, 1))
            if lam_shape:
                batch["reward"] = shape_rewards(batch, lam_shape, info["tokens"]["prizeGlob"])
            adv, ret = advantages(batch, args.gamma, args.lam)
            if getattr(args, "lam_value", None) is not None and args.lam_value != args.lam:
                ret = advantages(batch, args.gamma, args.lam_value)[1]
            batch["adv"], batch["ret"] = adv, ret
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
                   **({"sampled": round(float(batch["sampled"].mean()), 4)} if "sampled" in batch else {})}
            log.write(json.dumps(row) + "\n")
            log.flush()
            print(f"it {it:4d}  T={row['transitions']:6d} games={row['games']:4d} len={row['steps_per_game']:.0f} "
                  f"ent={stats['entropy']:.3f} kl={stats['kl']:.4f} clip={stats['clipfrac']:.3f} v={stats['v_loss']:.3f} "
                  f"win={row['win_vs']} collect {row['collect_s']}s train {row['train_s']}s", flush=True)

            if args.eval_every and (it + 1) % args.eval_every == 0:
                d1, d2 = ("all", "all") if not args.matchup or args.matchup[0] == "all" else args.matchup[0].split("|")
                path = run / "policies" / f"it{it:05d}.onnx"
                spec = export_policy(model, path, args.model)
                model.to(device)
                ev = {"iteration": it, "eval": {}}
                for opp in args.eval_opponents.split(","):
                    ev["eval"][opp] = evaluate(spec, opp, d1.strip(), d2.strip(), args.eval_games, args.eval_workers,
                                               args.seed * 7 + it, run.name)
                log.write(json.dumps(ev) + "\n")
                log.flush()
                print(f"  eval it {it}: " + "  ".join(f"vs {k} {v['all']:.3f} ± {v['ci95']:.3f} "
                                                      f"(dirs {v['dir1']:.3f} / {v['dir2']:.3f})" for k, v in ev["eval"].items()),
                      flush=True)

            if (it + 1) % args.snapshot_every == 0:
                snap = run / f"model_it{it:05d}.pt"
                save_atomic({"model": model.state_dict(), "config": model.config()}, snap)
                if args.league:
                    snapshots.append(str(snap) if args.inference == "gpu" else str(run / "policies" / f"it{it:05d}.onnx"))
                    if args.inference == "onnx":
                        export_onnx(model, snapshots[-1])
                        model.to(device)
            save_atomic({"model": model.state_dict(), "opt": opt.state_dict(), "iteration": it, "snapshots": snapshots,
                         "config": model.config()}, ckpt)
            if args.inference == "onnx":
                for old in (run / "policies").glob("it*.onnx"):
                    if str(old) not in snapshots and int(old.stem[2:]) < it - 2:
                        old.unlink(missing_ok=True)
    finally:
        pool.close()
        log.close()


if __name__ == "__main__":
    main()
