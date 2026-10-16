"""Value refit (log #75; evaluation only): is the pilot's value head weak because of the network, or because of how
PPO trains it?

collect  self-play with a fixed pilot (sampled, as in training) on the training matchups, --collections rounds of
         rl.train's collection (about 110k decisions each), kept in memory with each decision's result z (gamma 1)
fit      (--value-query N: the copy gets a fresh cross-attention value readout, log #77)
         a copy of the pilot trained on the value alone, z as the target (Monte Carlo, unbiased), Adam, --epochs over
         the data, games split 90 / 10 for a held-out explained variance; --head-only retrains only the value MLP on
         the frozen trunk instead (do the trunk's features already hold what the value needs?)
Writes runs/vrefit/<tag>.pt (a checkpoint of the copy) and <tag>.json. notes/scripts/credit_diag.py --value-pilot
then plays the original pilot with this copy's value, so the credit share and alignment of TD signals can be
compared with the original value head under the same policy.

Run: PYTHONPATH=. .venv/Scripts/python.exe notes/scripts/value_refit.py --pilot runs/abl/base/model_it00079.pt --tag base79-full
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

from rl import limits
from rl.gpu_matrix import load_policy
from rl.remote import RemotePool
from rl.rollouts import concat, read_rollout
from rl.train import TOKEN_FIELDS, advantages, save_atomic

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/vrefit"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--collections", type=int, default=6)
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--head-only", action="store_true")
    ap.add_argument("--value-query", type=int, default=0,
                    help="replace the value's read of the pooled token by a fresh cross-attention readout with N queries")
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--seed", type=int, default=91)
    args = ap.parse_args(argv)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    workers = limits.cap_workers(args.workers)
    limits.apply(device, workers)
    torch.manual_seed(args.seed)
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / f"_{args.tag}"
    tmp.mkdir(exist_ok=True)
    model, _ = load_policy(args.pilot, device, {"value_query": args.value_query} if args.value_query else None)
    cfg = json.load(open(ROOT / "runs/abl/base/config.json"))
    matchups = cfg["matchups"]

    # Collect, keeping only what the value needs (tokens trimmed to the longest state).
    t0 = time.time()
    pool = RemotePool(workers)
    pool.pace = 0.25
    parts = []
    try:
        for c in range(args.collections):
            msgs = [{"cmd": "collect", "encoding": "tokens", "transitions": 4096, "concurrency": 48, "deckoutWin": 1.0,
                     "seed": args.seed * 1_000_003 + c * 1009 + w, "matchups": matchups, "opponents": [{"spec": "self", "weight": 1.0}],
                     "out": str(tmp / f"w{w}.bin"), "history": int(model.cfg.get("history", 0) or 0)} for w in range(workers)]
            replies = pool.collect(msgs, {0: model}, device)
            b = concat([read_rollout(r["out"]) for r in replies])
            T = len(b["action"])
            _, z = advantages(b, 1.0, 1.0)
            kinds = b["obs.tokKind"].reshape(T, -1)
            L = int(((kinds > 0) * np.arange(1, kinds.shape[1] + 1)).max())
            game = np.asarray(b["traj"]) // 2 + c * 10 ** 7          # both seats of a game stay on one side of the split
            parts.append({"tok": [b[k].reshape(T, -1)[:, :L] for k in TOKEN_FIELDS[:3]],
                          "glob": b["obs.glob"].reshape(T, -1), "slots": b["obs.slots"].reshape(T, -1),
                          "cand": b["obs.cand"].reshape(T, -1), "ncand": b["obs.nCand"], "z": z.astype(np.float32),
                          "v_old": b["value"].astype(np.float32), "game": game})
            print(f"collection {c}: {T} decisions, {len(replies[0]['results'])}+ games, tokens {L}", flush=True)
    finally:
        pool.close()
    Lmax = max(p["tok"][0].shape[1] for p in parts)
    pad = lambda a: np.pad(a, ((0, 0), (0, Lmax - a.shape[1])))
    data = {"tok": [np.concatenate([pad(p["tok"][i]) for p in parts]) for i in range(3)],
            **{k: np.concatenate([p[k] for p in parts]) for k in ("glob", "slots", "cand", "ncand", "z", "v_old", "game")}}
    N = len(data["z"])
    games = np.unique(data["game"])
    rng = np.random.default_rng(args.seed)
    held = set(rng.choice(games, len(games) // 10, replace=False).tolist())
    is_held = np.array([g in held for g in data["game"]])
    tr, va = np.flatnonzero(~is_held), np.flatnonzero(is_held)
    t_collect = time.time() - t0

    def batch(idx):
        x = [torch.from_numpy(a[idx]).to(device) for a in data["tok"]]
        x += [torch.from_numpy(data[k][idx]).to(device) for k in ("glob", "slots", "cand", "ncand")]
        return x, torch.from_numpy(data["z"][idx]).to(device)

    @torch.no_grad()
    def ev(net, idx):
        net.eval()
        vs = []
        for s in range(0, len(idx), 2048):
            x, _ = batch(idx[s:s + 2048])
            vs.append(net(*x)[1].float().cpu().numpy())
        v, z = np.concatenate(vs), data["z"][idx]
        return float(1 - np.var(z - v) / np.var(z)), float(np.mean((z - v) ** 2))

    ev0 = ev(model, va)
    old = float(1 - np.var(data["z"][va] - data["v_old"][va]) / np.var(data["z"][va]))
    if args.head_only:
        for p in model.parameters():
            p.requires_grad_(False)
        for mod in [model.value] + ([model.vcross] if args.value_query else []):
            for p in mod.parameters():
                p.requires_grad_(True)
        if args.value_query:
            model.vquery.requires_grad_(True)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.Adam(params, lr=args.lr, eps=1e-5)
    hist = []
    best = (ev0[0], {k: v.detach().clone() for k, v in model.state_dict().items()}, -1)   # kept: the best held-out EV
    t1 = time.time()
    pace = limits.Pace(device)                       # rests between steps, as rl.train, to hold the GPU near 80%
    for e in range(args.epochs):
        model.train()
        perm = rng.permutation(tr)
        tot = 0.0
        for s in range(0, len(perm), args.batch):
            x, z = batch(perm[s:s + args.batch])
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
                _, v = model(*x)
            loss = ((v.float() - z) ** 2).mean()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 0.5)
            opt.step()
            pace.tick()
            tot += loss.item() * len(z)
        hev = ev(model, va)
        hist.append({"epoch": e, "train_mse": round(tot / len(perm), 4), "held_ev_mse": [round(x, 4) for x in hev]})
        print(json.dumps(hist[-1]), flush=True)
        if hev[0] > best[0]:
            best = (hev[0], {k: v.detach().clone() for k, v in model.state_dict().items()}, e)
    model.load_state_dict(best[1])
    model.eval()
    save_atomic({"model": model.state_dict(), "config": model.config()}, OUT / f"{args.tag}.pt")
    out = {"pilot": args.pilot, "tag": args.tag, "head_only": args.head_only, "decisions": int(N), "train": int(len(tr)),
           "held": int(len(va)), "held_ev_recorded": round(old, 4), "held_ev_before": [round(x, 4) for x in ev0], "epochs": hist,
           "kept_epoch": best[2], "kept_held_ev": round(best[0], 4),
           "collect_s": round(t_collect, 1), "fit_s": round(time.time() - t1, 1)}
    (OUT / f"{args.tag}.json").write_text(json.dumps(out, indent=1))
    for f in tmp.glob("*.bin"):
        f.unlink()
    print(json.dumps(out))


if __name__ == "__main__":
    main()
