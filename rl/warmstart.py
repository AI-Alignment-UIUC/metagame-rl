"""Warm start for a changed pilot architecture (log #98). A change that cannot be grown as the identity (a deck-free
board encoder, which stops seeing the deck; history tokens, new tokens to attend to) starts behind the pilot it is
compared with, and the lab's early stop then closes it before it can catch up. Here a student with the new
architecture, grown from the teacher's weights (rl/train.py load_grown), is first trained to play as the teacher: the
KL divergence from the teacher's policy and the squared difference from its value, on states of the teacher's own
games on its population's decks, sampled as in training. Self-play states only; nothing human.

Writes a metagame checkpoint, the teacher's whole state with the student's net, config and optimizer, for
rl/metagame.py --fork-from (rl/lab.py does this for a card with "warm").

  python -m rl.warmstart --teacher runs/lab/main/seg_0250.pt --pilot-opts '{"deck_mode": "cross"}' --out runs/x/warm.pt
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from rl import limits
from rl.decks import Pool
from rl.remote import RemotePool
from rl.rollouts import concat, read_rollout
from rl.train import legal_mask, load_grown, model_inputs, token_net

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--teacher", required=True, help="a metagame checkpoint")
    ap.add_argument("--pilot-opts", default="{}", help="JSON architecture options of the student")
    ap.add_argument("--out", required=True)
    ap.add_argument("--games", type=int, default=2000)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--minibatch", type=int, default=1024)
    ap.add_argument("--micro-batch", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--vf", type=float, default=1.0)
    ap.add_argument("--holdout", type=float, default=0.1, help="share of games held out to measure the fit")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args(argv)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    workers = limits.cap_workers(args.workers)
    limits.apply(device, workers)
    rng = np.random.default_rng(args.seed)
    torch.manual_seed(args.seed)
    t0 = time.time()

    st = torch.load(ROOT / args.teacher, map_location="cpu", weights_only=False)
    opts = json.loads(args.pilot_opts)
    pool = Pool()
    rp = RemotePool(workers)
    rp.pace = 0.25
    out_dir = (ROOT / args.out).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        info = rp.ask_all([{"cmd": "info"}] * workers)[0]
        teacher = token_net(st["config"], info).to(device)
        teacher.load_state_dict(st["net"])
        teacher.eval()
        student = token_net({**st["config"], **opts}, info).to(device)
        grown = load_grown(student, st["net"])
        # the teacher's games, both seats recorded, with the student's history window if it reads one
        decks = [pool.names(pool.vector(a["deck"])) for a in st["population"]]
        shards = [{"decks": [], "jobs": []} for _ in range(workers)]
        for g in range(args.games):
            k, l = (int(x) for x in rng.choice(len(decks), 2, replace=False))
            sh = shards[g % workers]
            sh["decks"] += [{"name": f"g{g}a", "cards": decks[k]}, {"name": f"g{g}b", "cards": decks[l]}]
            i = len(sh["decks"]) - 2
            sh["jobs"].append({"i": i, "j": i + 1, "iSeat": 1 + int(rng.integers(2)), "seed": args.seed * 1_000_003 + g, "rec": True})
        msgs = [{"cmd": "games", "encoding": "tokens", "greedy": False, "deckoutWin": 1, "concurrency": 48,
                 "out": str(out_dir / f"warm_w{w}.bin"), "decks": sh["decks"], "jobs": sh["jobs"],
                 "history": int(student.config().get("history", 0) or 0)} for w, sh in enumerate(shards) if sh["jobs"]]
        replies = rp.collect(msgs, {0: teacher}, device)
    finally:
        rp.close()
    batch = concat([read_rollout(r["out"]) for r in replies])
    for r in replies:
        Path(r["out"]).unlink(missing_ok=True)
    T = len(batch["action"])
    inputs = [torch.from_numpy(np.ascontiguousarray(x)) for x in model_inputs(batch, "tokens")]
    offsets = torch.from_numpy(batch["legal_offsets"].astype(np.int64))
    ids = torch.from_numpy(batch["legal_ids"].astype(np.int64))
    traj = np.asarray(batch["traj"])
    held = np.isin(traj, rng.choice(np.unique(traj), max(1, int(args.holdout * len(np.unique(traj)))), replace=False))
    train_idx, test_idx = np.flatnonzero(~held), np.flatnonzero(held)

    def outputs(net, idx):
        xs = [x[idx].to(device) for x in inputs]
        L = int(((xs[1] > 0).long() * torch.arange(1, xs[1].shape[1] + 1, device=device)).amax())
        xs[:3] = [x[:, :L] for x in xs[:3]]
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
            logits, v = net(*xs)
        mask = legal_mask(torch.from_numpy(idx).to(device), offsets.to(device), ids.to(device), net.action_size)
        return F.log_softmax(logits.float().masked_fill(~mask, -1e9), -1), v.float(), mask

    @torch.no_grad()
    def fit(idx):
        """KL(teacher || student), top-1 agreement and value MSE over the rows idx."""
        student.eval()
        kl = agree = mse = 0.0
        for s in range(0, len(idx), args.micro_batch):
            j = idx[s:s + args.micro_batch]
            lt, vt, mask = outputs(teacher, j)
            ls, vs, _ = outputs(student, j)
            kl += float((lt.exp() * (lt - ls)).masked_fill(~mask, 0).sum())
            agree += float((lt.argmax(1) == ls.argmax(1)).sum())
            mse += float(((vs - vt) ** 2).sum())
        n = max(len(idx), 1)
        return {"kl": round(kl / n, 5), "agree": round(agree / n, 4), "v_mse": round(mse / n, 5)}

    before = fit(test_idx)
    opt = torch.optim.Adam(student.parameters(), lr=args.lr, eps=1e-5)
    pace = limits.Pace(device, limits.LOAD)
    for e in range(args.epochs):
        student.train()
        perm = rng.permutation(train_idx)
        for s in range(0, len(perm), args.minibatch):
            mb = perm[s:s + args.minibatch]
            opt.zero_grad(set_to_none=True)
            for m in range(0, len(mb), args.micro_batch):
                j = mb[m:m + args.micro_batch]
                with torch.no_grad():
                    lt, vt, mask = outputs(teacher, j)
                ls, vs, _ = outputs(student, j)
                kl = (lt.exp() * (lt - ls)).masked_fill(~mask, 0).sum(1).mean()
                loss = (kl + args.vf * ((vs - vt) ** 2).mean()) * len(j) / len(mb)
                loss.backward()
                pace.tick()
            torch.nn.utils.clip_grad_norm_(student.parameters(), 0.5)
            opt.step()
    after = fit(test_idx)

    state = {**st, "net": student.state_dict(), "config": student.config(), "opt": opt.state_dict(),
             "warm": {"teacher": args.teacher, "opts": opts, "grown": grown, "states": T, "before": before, "after": after,
                      "epochs": args.epochs, "seconds": round(time.time() - t0, 1)}}
    tmp = (ROOT / args.out).with_suffix(".tmp")
    torch.save(state, tmp)
    tmp.replace(ROOT / args.out)
    print(json.dumps(state["warm"]), flush=True)


if __name__ == "__main__":
    main()
