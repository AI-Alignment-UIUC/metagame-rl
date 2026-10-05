"""PPO self-play training (plan items A1.5 and A3).

Rollouts are played by Node workers (env/rollout_worker.js) running the current policy as ONNX;
this process trains on them with PyTorch (GPU if available) and exports the next policy. One
iteration: export -> every worker collects N transitions -> PPO epochs -> log.

Opponents: the learner plays itself ("self") and, with --league, past snapshots of itself,
added every --snapshot-every iterations. Both seats are recorded when it plays itself.

Example (A3, one matchup, both directions):
  .venv/Scripts/python -m rl.train --run runs/a3-wiggly-haymaker \
      --matchup "15+ #2 William Lieu|15+ #1 Andrew Marshall" --both-directions --iterations 200
"""
import argparse
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from rl.model import IdentityMLP, export_onnx, build
from rl.rollouts import read_rollout, concat

ROOT = Path(__file__).resolve().parent.parent


class Workers:
    """Node rollout workers, one JSON command per line each way."""

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


def advantages(r: dict, gamma: float, lam: float):
    """GAE per trajectory (one player's decisions in one game, in order); reward only at the end."""
    T = len(r["action"])
    adv = np.zeros(T, dtype=np.float32)
    nxt_v, nxt_a = {}, {}
    value, reward, done, traj = r["value"], r["reward"], r["done"], r["traj"]
    for t in range(T - 1, -1, -1):
        k = traj[t]
        if done[t]:
            v1, a1 = 0.0, 0.0
        else:
            v1, a1 = nxt_v.get(k, 0.0), nxt_a.get(k, 0.0)
        delta = reward[t] + gamma * v1 - value[t]
        adv[t] = delta + gamma * lam * a1
        nxt_v[k], nxt_a[k] = value[t], adv[t]
    return adv, adv + value


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


def ppo_update(model, opt, batch, args, device):
    T = len(batch["action"])
    obs = torch.from_numpy(batch["obs"]).to(device)
    act = torch.from_numpy(batch["action"].astype(np.int64)).to(device)
    old_logp = torch.from_numpy(batch["logp"]).to(device)
    adv = torch.from_numpy(batch["adv"]).to(device)
    ret = torch.from_numpy(batch["ret"]).to(device)
    old_v = torch.from_numpy(batch["value"]).to(device)
    offsets = torch.from_numpy(batch["legal_offsets"]).to(device)
    ids = torch.from_numpy(batch["legal_ids"].astype(np.int64)).to(device)
    adv = (adv - adv.mean()) / (adv.std() + 1e-8)
    stats = {"pi_loss": 0.0, "v_loss": 0.0, "entropy": 0.0, "kl": 0.0, "clipfrac": 0.0}
    n = 0
    for _ in range(args.epochs):
        perm = torch.randperm(T, device=device)
        for s in range(0, T, args.minibatch):
            idx = perm[s:s + args.minibatch]
            logits, v = model(obs[idx])
            mask = legal_mask(idx, offsets, ids, model.action_size)
            logits = logits.masked_fill(~mask, -1e9)
            logp_all = F.log_softmax(logits, dim=-1)
            logp = logp_all.gather(1, act[idx, None]).squeeze(1)
            p_all = logp_all.exp()
            entropy = -(p_all * logp_all).masked_fill(~mask, 0.0).sum(-1).mean()
            ratio = (logp - old_logp[idx]).exp()
            a = adv[idx]
            pi_loss = -torch.min(ratio * a, ratio.clamp(1 - args.clip, 1 + args.clip) * a).mean()
            v_clipped = old_v[idx] + (v - old_v[idx]).clamp(-args.clip, args.clip)
            v_loss = torch.max((v - ret[idx]) ** 2, (v_clipped - ret[idx]) ** 2).mean()
            loss = pi_loss + args.vf * v_loss - args.ent * entropy
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
            opt.step()
            with torch.no_grad():
                stats["pi_loss"] += pi_loss.item()
                stats["v_loss"] += v_loss.item()
                stats["entropy"] += entropy.item()
                stats["kl"] += (old_logp[idx] - logp).mean().item()
                stats["clipfrac"] += ((ratio - 1).abs() > args.clip).float().mean().item()
                n += 1
    return {k: v / max(n, 1) for k, v in stats.items()}


def evaluate(policy: Path, opponent: str, d1: str, d2: str, games: int, workers: int, seed: int) -> dict:
    """Seat- and deck-swapped match of the policy (greedy) against a fixed opponent (env/tools/evaluate.js)."""
    out = policy.with_suffix(f".eval-{opponent}.json")
    cmd = ["node", str(ROOT / "env" / "tools" / "evaluate.js"), "--x", f"onnx:{policy}:greedy", "--y", opponent,
           "--d1", d1, "--d2", d2, "--games", str(games), "--workers", str(workers), "--concurrency", "8",
           "--seed", str(seed), "--json", str(out)]
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    r = json.load(open(out))
    out.unlink(missing_ok=True)
    return {"all": round(r["all"]["xWinRate"], 4), "ci95": round(r["all"]["ci95"], 4),
            "dir1": round(r["dir1"]["xWinRate"], 4), "dir2": round(r["dir2"]["xWinRate"], 4)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--matchup", action="append", required=True,
                    help='"learner deck|opponent deck" (substring of an archived deck name); repeatable')
    ap.add_argument("--both-directions", action="store_true", help="also train each matchup with the decks swapped")
    ap.add_argument("--iterations", type=int, default=100)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--transitions", type=int, default=4096, help="per worker per iteration")
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--hidden", type=int, default=512)
    ap.add_argument("--layers", type=int, default=2)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--minibatch", type=int, default=4096)
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--clip", type=float, default=0.2)
    ap.add_argument("--vf", type=float, default=0.5)
    ap.add_argument("--ent", type=float, default=0.01)
    ap.add_argument("--max-grad-norm", type=float, default=0.5)
    ap.add_argument("--league", action="store_true", help="also play past snapshots")
    ap.add_argument("--snapshot-every", type=int, default=10)
    ap.add_argument("--self-weight", type=float, default=0.5, help="share of games against itself with --league")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--eval-every", type=int, default=0, help="evaluate against --eval-opponents every N iterations")
    ap.add_argument("--eval-opponents", default="simplebot,heuristic")
    ap.add_argument("--eval-games", type=int, default=200)
    ap.add_argument("--eval-workers", type=int, default=8)
    args = ap.parse_args(argv)

    run = ROOT / args.run
    (run / "policies").mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(args.seed)
    random.seed(args.seed)

    matchups = []
    for m in args.matchup:
        a, b = m.split("|")
        matchups.append([a.strip(), b.strip()])
        if args.both_directions:
            matchups.append([b.strip(), a.strip()])

    workers = Workers(args.workers)
    info = workers.ask_all([{"cmd": "info"}] * args.workers)[0]
    model = IdentityMLP(info["obsSize"], info["actionSize"], args.hidden, args.layers).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, eps=1e-5)
    start = 0
    snapshots = []
    ckpt = run / "checkpoint.pt"
    if args.resume and ckpt.exists():
        state = torch.load(ckpt, map_location=device)
        model.load_state_dict(state["model"])
        opt.load_state_dict(state["opt"])
        start = state["iteration"] + 1
        snapshots = state.get("snapshots", [])
    (run / "config.json").write_text(json.dumps({**vars(args), "matchups": matchups, "model": model.config(),
                                                 "device": device}, indent=1))
    log = open(run / "log.jsonl", "a")
    print(f"device {device}, obs {info['obsSize']}, actions {info['actionSize']}, "
          f"params {sum(p.numel() for p in model.parameters())}, matchups {matchups}", flush=True)

    try:
        for it in range(start, args.iterations):
            t0 = time.time()
            policy = run / "policies" / f"it{it:05d}.onnx"
            export_onnx(model, str(policy))
            model.to(device).train()
            opponents = [{"spec": "self", "weight": 1.0}]
            if args.league and snapshots:
                opponents = [{"spec": "self", "weight": args.self_weight}] + [
                    {"spec": "onnx:" + s, "weight": (1 - args.self_weight) / len(snapshots)} for s in snapshots]
            msgs = [{"cmd": "collect", "model": str(policy), "transitions": args.transitions, "concurrency": args.concurrency,
                     "seed": args.seed * 1_000_003 + it * 1009 + w, "matchups": matchups, "opponents": opponents,
                     "out": str(run / f"rollout_w{w}.bin")} for w in range(args.workers)]
            replies = workers.ask_all(msgs)
            t1 = time.time()
            batch = concat([read_rollout(r["out"]) for r in replies])
            adv, ret = advantages(batch, args.gamma, args.lam)
            batch["adv"], batch["ret"] = adv, ret
            stats = ppo_update(model, opt, batch, args, device)
            t2 = time.time()

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
                   "win_vs": {k: float(np.mean(v)) for k, v in vs.items()},
                   "collect_s": round(t1 - t0, 1), "train_s": round(t2 - t1, 1), **{k: round(v, 5) for k, v in stats.items()}}
            log.write(json.dumps(row) + "\n")
            log.flush()
            print(f"it {it:4d}  T={row['transitions']:6d} games={row['games']:4d} len={row['steps_per_game']:.0f} "
                  f"ent={stats['entropy']:.3f} kl={stats['kl']:.4f} clip={stats['clipfrac']:.3f} v={stats['v_loss']:.3f} "
                  f"win={row['win_vs']} collect {row['collect_s']}s train {row['train_s']}s", flush=True)

            if args.eval_every and (it + 1) % args.eval_every == 0:
                d1, d2 = args.matchup[0].split("|")
                ev = {"iteration": it, "eval": {}}
                for opp in args.eval_opponents.split(","):
                    ev["eval"][opp] = evaluate(policy, opp, d1.strip(), d2.strip(), args.eval_games, args.eval_workers,
                                               args.seed * 7 + it)
                log.write(json.dumps(ev) + "\n")
                log.flush()
                print(f"  eval it {it}: " + "  ".join(f"vs {k} {v['all']:.3f} ± {v['ci95']:.3f} "
                                                      f"(dirs {v['dir1']:.3f} / {v['dir2']:.3f})" for k, v in ev["eval"].items()),
                      flush=True)

            if args.league and (it + 1) % args.snapshot_every == 0:
                snapshots.append(str(policy))
            torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "iteration": it, "snapshots": snapshots,
                        "config": model.config()}, ckpt)
            if (it + 1) % args.snapshot_every == 0:
                torch.save({"model": model.state_dict(), "config": model.config()}, run / f"model_it{it:05d}.pt")
            # keep the policy files snapshots point to; drop the rest
            for old in (run / "policies").glob("it*.onnx"):
                if str(old) not in snapshots and old != policy and int(old.stem[2:]) < it - 2:
                    old.unlink(missing_ok=True)
    finally:
        workers.close()
        log.close()


if __name__ == "__main__":
    main()
