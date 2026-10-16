"""Memory diagnostic (log #76; evaluation only): does the gradient reach back through a pilot's memory, and does
the pilot use what it remembers?

On a memory pilot's own last training batch (its run's rollout_w*.bin):
  reach   for sampled decisions t of sampled trajectories, the gradient of log pi(a_t) + v_t with respect to the
          memory input at decision t - k (the pooled state fed to the recurrent core, held fixed as a leaf), as a
          share of its norm at t itself: the median and mean by lag k. A GRU's share typically decays with k
          (vanishing gradients); the attention memory reaches every earlier decision in one step.
  usage   the same decisions with the memory cut to the current decision only (each trajectory split into
          trajectories of length 1): mean KL(full || amnesic) of the policy, mean |value difference|, and the
          value's explained variance against the result with and without memory.

Run: PYTHONPATH=. .venv/Scripts/python.exe notes/scripts/memory_reach.py --run runs/abl/mem-gru [--snapshot model_it00079.pt]
"""
import argparse
import glob
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from rl import limits
from rl.gpu_matrix import load_policy
from rl.rollouts import concat, read_rollout
from rl.train import TOKEN_FIELDS, advantages

ROOT = Path(__file__).resolve().parents[2]
LAGS = (1, 2, 4, 8, 16, 32, 64)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--snapshot", default="checkpoint.pt")
    ap.add_argument("--trajectories", type=int, default=120)
    ap.add_argument("--targets", type=int, default=8, help="decisions per trajectory whose gradient is traced")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    limits.apply(device, 0)
    run = ROOT / args.run
    model, _ = load_policy(str((run / args.snapshot).relative_to(ROOT)), device)
    assert model.memory != "none", "not a pilot with memory"
    if model.memory == "gru":
        model.mem_gru.train()                          # cuDNN's RNN backward needs it; no dropout, so the same outputs
    b = concat([read_rollout(f) for f in sorted(glob.glob(str(run / "rollout_w*.bin")))])
    T = len(b["action"])
    _, G = advantages(b, 1.0, 1.0)                     # the result from each decision (gamma 1, lambda 1)
    traj = np.asarray(b["traj"])
    order = np.lexsort((np.arange(T), traj))
    tj = traj[order]
    starts = np.flatnonzero(np.r_[True, tj[1:] != tj[:-1]])
    lens = np.diff(np.r_[starts, T])
    rng = np.random.default_rng(args.seed)
    pick = rng.choice(len(starts), min(args.trajectories, len(starts)), replace=False)
    lag_share = {k: [] for k in LAGS}
    kl, dv, vf, va, gs = [], [], [], [], []
    for p in pick:
        rows = order[starts[p]:starts[p] + lens[p]]
        n = len(rows)
        xs = [torch.from_numpy(np.ascontiguousarray(b[k].reshape(T, -1)[rows] if k != "obs.nCand" else b[k][rows])).to(device)
              for k in TOKEN_FIELDS]
        with torch.no_grad():
            x, msk = model.encode(*xs[:5])
            m0 = model.memory_inputs(x[:, 0], xs[3]).float()
            full = model(*xs, mem_lens=[n])
            amn = model(*xs, mem_lens=[1] * n)
        nc = xs[6].long()
        valid = torch.arange(full[0].shape[1], device=device)[None, :] < nc[:, None]
        lf = F.log_softmax(full[0].float().masked_fill(~valid, -1e9), -1)
        la = F.log_softmax(amn[0].float().masked_fill(~valid, -1e9), -1)
        kl.append((lf.exp() * (lf - la)).masked_fill(~valid, 0).sum(-1).cpu().numpy())
        dv.append((full[1] - amn[1]).abs().float().cpu().numpy())
        vf.append(full[1].float().cpu().numpy()); va.append(amn[1].float().cpu().numpy()); gs.append(G[rows])
        # Gradient reach: memory inputs as a leaf, heads on top (the encoder's output held fixed).
        act = torch.from_numpy(b["action"][rows].astype(np.int64)).to(device)
        for t in rng.choice(n, min(args.targets, n), replace=False):
            if t < 1:
                continue
            e = m0.detach().clone().requires_grad_()
            with torch.autocast(device_type=device, enabled=False):
                h = model.memory_seq(e, [n])
            pooled = x[:, 0].float() + model.mem_out(h)
            xx = torch.cat([pooled[:, None], x[:, 1:].float()], 1)
            logits, v = model.heads(xx[t:t + 1], msk[t:t + 1], xs[5][t:t + 1], xs[6][t:t + 1])
            lp = F.log_softmax(logits.masked_fill(~valid[t:t + 1], -1e9), -1)[0, act[t]]
            (lp + v[0]).backward()
            g = e.grad.norm(dim=-1).cpu().numpy()
            if g[t] <= 0:
                continue
            for k in LAGS:
                if t - k >= 0:
                    lag_share[k].append(g[t - k] / g[t])
    vf, va, gs = np.concatenate(vf), np.concatenate(va), np.concatenate(gs)
    ev = lambda v: float(1 - np.var(gs - v) / np.var(gs))
    out = {"run": args.run, "snapshot": args.snapshot, "memory": model.memory, "trajectories": len(pick),
           "decisions": int(len(gs)),
           "reach": {k: {"n": len(v), "median": round(float(np.median(v)), 4), "mean": round(float(np.mean(v)), 4)}
                     for k, v in lag_share.items() if v},
           "usage": {"kl_full_vs_amnesic": round(float(np.concatenate(kl).mean()), 4),
                     "value_abs_diff": round(float(np.concatenate(dv).mean()), 4),
                     "value_ev_full": round(ev(vf), 4), "value_ev_amnesic": round(ev(va), 4)}}
    print(json.dumps(out, indent=1))
    (run / f"memory_reach_{Path(args.snapshot).stem}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
