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
import json
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
    ids = torch.from_numpy(batch["legal_ids"].astype(np.int64)).to(device)
    adv = (adv - adv.mean()) / (adv.std() + 1e-8)
    stats = {"pi_loss": 0.0, "v_loss": 0.0, "entropy": 0.0, "kl": 0.0, "clipfrac": 0.0}
    n = 0
    tok_len = None
    if args.model == "tokens":                # tokens fill from the front; kind 0 is padding
        kind = inputs[1]
        tok_len = ((kind > 0).long() * torch.arange(1, kind.shape[1] + 1, device=device)).amax(1)
    for _ in range(args.epochs):
        perm = torch.randperm(T, device=device)
        for s in range(0, T, args.minibatch):
            idx = perm[s:s + args.minibatch]
            if tok_len is not None:           # similar lengths share a micro-batch, cut to its longest
                idx = idx[torch.argsort(tok_len[idx])]
            opt.zero_grad(set_to_none=True)
            # The minibatch's loss is accumulated over micro-batches (same gradient, less memory).
            micro = args.micro_batch or len(idx)
            mb_stats = {k: 0.0 for k in stats}
            for m in range(0, len(idx), micro):
                j = idx[m:m + micro]
                w = len(j) / len(idx)
                with torch.autocast("cuda", dtype=torch.bfloat16, enabled=args.amp and device == "cuda"):
                    xs = [x[j] for x in inputs]
                    if tok_len is not None:
                        L = int(tok_len[j].max())
                        xs[:3] = [x[:, :L] for x in xs[:3]]
                    logits, v = model(*xs)
                logits, v = logits.float(), v.float()
                mask = legal_mask(j, offsets, ids, model.action_size)
                logits = logits.masked_fill(~mask, -1e9)
                logp_all = F.log_softmax(logits, dim=-1)
                logp = logp_all.gather(1, act[j, None]).squeeze(1)
                p_all = logp_all.exp()
                entropy = -(p_all * logp_all).masked_fill(~mask, 0.0).sum(-1).mean()
                ratio = (logp - old_logp[j]).exp()
                a = adv[j]
                pi_loss = -torch.min(ratio * a, ratio.clamp(1 - args.clip, 1 + args.clip) * a).mean()
                v_clipped = old_v[j] + (v - old_v[j]).clamp(-args.clip, args.clip)
                v_loss = torch.max((v - ret[j]) ** 2, (v_clipped - ret[j]) ** 2).mean()
                loss = pi_loss + args.vf * v_loss - args.ent * entropy
                (loss * w).backward()
                with torch.no_grad():
                    mb_stats["pi_loss"] += w * pi_loss.item()
                    mb_stats["v_loss"] += w * v_loss.item()
                    mb_stats["entropy"] += w * entropy.item()
                    mb_stats["kl"] += w * (old_logp[j] - logp).mean().item()
                    mb_stats["clipfrac"] += w * ((ratio - 1).abs() > args.clip).float().mean().item()
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
            opt.step()
            for k in stats:
                stats[k] += mb_stats[k]
            n += 1
    return {k: v / max(n, 1) for k, v in stats.items()}


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
                                 d=args.d, layers=args.tok_layers, heads=args.heads)
    i = info["identity"] if "identity" in info else info
    return IdentityMLP(i["obsSize"], i["actionSize"], args.hidden, args.layers)


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
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--minibatch", type=int, default=4096)
    ap.add_argument("--micro-batch", type=int, default=0, help="split each minibatch into chunks of this size (0 = whole)")
    ap.add_argument("--gpu-mem-fraction", type=float, default=0.8,
                    help="cap this process's GPU memory (at most 0.8, rl/limits.py)")
    ap.add_argument("--amp", action="store_true", help="bfloat16 autocast for the forward pass on the GPU")
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--clip", type=float, default=0.2)
    ap.add_argument("--vf", type=float, default=0.5)
    ap.add_argument("--ent", type=float, default=0.01)
    ap.add_argument("--max-grad-norm", type=float, default=0.5)
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
        model.load_state_dict(torch.load(ROOT / args.init_from, map_location=device)["model"])
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
                     "concurrency": args.concurrency, "seed": args.seed * 1_000_003 + it * 1009 + w,
                     "matchups": matchups, "opponents": opponents, "out": str(run / f"rollout_w{w}.bin"),
                     **({"model": str(policy)} if args.inference == "onnx" else {})} for w in range(args.workers)]
            replies = pool.collect(msgs, models, device) if args.inference == "gpu" else pool.ask_all(msgs)
            model.train()
            t1 = time.time()
            batch = concat([read_rollout(r["out"]) for r in replies])
            adv, ret = advantages(batch, args.gamma, args.lam)
            batch["adv"], batch["ret"] = adv, ret
            batch["inputs"] = model_inputs(batch, args.model)
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
                   "win_vs": {k: round(float(np.mean(v)), 4) for k, v in vs.items()},
                   "collect_s": round(t1 - t0, 1), "train_s": round(t2 - t1, 1), **{k: round(v, 5) for k, v in stats.items()}}
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
                torch.save({"model": model.state_dict(), "config": model.config()}, snap)
                if args.league:
                    snapshots.append(str(snap) if args.inference == "gpu" else str(run / "policies" / f"it{it:05d}.onnx"))
                    if args.inference == "onnx":
                        export_onnx(model, snapshots[-1])
                        model.to(device)
            torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "iteration": it, "snapshots": snapshots,
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
