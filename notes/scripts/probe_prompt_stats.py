"""C76: does the pilot get any learning signal at prompt answers? (runs/probe/C76-promptstats/record.md; evaluation only)

Self-play rollouts from a pilot exactly as ar/train.py collects them (the practice matchups, the 2000 round rule,
opponent self, no search probe), then one no-grad forward pass over every decision. Per decision: the number of legal
options, the policy's entropy (also over log n_legal) and top-1 minus top-2 margin, the value, the Monte Carlo return
(gamma 1, the reward at the end) and the GAE advantage (lambda 0.95, from the rollout's own values). Decisions are
grouped by the glob features of env/tokens.js: main phase (no prompt open, glob byte 48) against prompt answers, each
prompt type, and each (prompt type, message hash bin) with at least 200 rows. Forced rows (one legal option) are counted
but left out of the entropy and margin stats. Per group: rows, share, share forced, mean n_legal, mean normalised
entropy, median margin, mean / mean |.| / sd of the advantage, value MSE and explained variance against the return.
The call: "blind" if the prompt rows' mean |adv| is under half the main rows' and their explained variance is below
the main rows'; else "unexplored" if their mean normalised entropy is over 0.8; else "confident" if under 0.3; else
"mixed". Nothing trains and nothing is written to ar/.

Run (runs/probe/C76-promptstats/chain.sh): PYTHONPATH=. .venv/Scripts/python notes/scripts/probe_prompt_stats.py \
    --dir runs/probe/C76-promptstats --workers 6 --iterations 2 --seed 91
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ar"))
sys.path.insert(0, str(ROOT))
import fixed                                                # noqa: E402
from rl import limits                                       # noqa: E402
from rl.gpu_matrix import load_policy                       # noqa: E402
from rl.remote import RemotePool                            # noqa: E402
from rl.rollouts import read_rollout, concat                # noqa: E402
from rl.train import legal_mask, model_inputs               # noqa: E402

# env/tokens.js: the glob row is 3 + 2 * (8 + HASH 8) = 35 numbers, then one slot per prompt type and "no prompt open",
# then the 32-bin message hash.
PROMPT_TYPES = ['Choose cards', 'Choose pokemon', 'Choose energy', 'Attach energy', 'Move energy',
                'Move damage', 'Put damage', 'Order cards', 'Choose attack', 'Select', 'Confirm', 'Show cards', 'Alert']
NP, MSG_HASH = len(PROMPT_TYPES), 32
PO = 3 + 2 * (8 + 8)                                        # 35
NONE_SLOT = PO + NP                                         # 48, "no prompt open": 0 at a prompt answer
GAMMA, LAM, MICRO, MIN_ROWS = 1.0, 0.95, 512, 200


def advantages(batch: dict, gamma: float, lam: float):
    """GAE per trajectory (one player's decisions in one game, in order); the reward comes at the end."""
    value, reward, done, traj = batch["value"], batch["reward"], batch["done"], batch["traj"]
    adv = np.zeros(len(value), dtype=np.float32)
    nxt_v, nxt_a = {}, {}
    for t in range(len(value) - 1, -1, -1):
        k = traj[t]
        v1, a1 = (0.0, 0.0) if done[t] else (nxt_v.get(k, 0.0), nxt_a.get(k, 0.0))
        adv[t] = reward[t] + gamma * v1 - value[t] + gamma * lam * a1
        nxt_v[k], nxt_a[k] = value[t], adv[t]
    return adv, adv + value


def mc_returns(batch: dict, gamma: float) -> np.ndarray:
    """Discounted return per decision, the reward at the end of its trajectory."""
    reward, done, traj = batch["reward"], batch["done"], batch["traj"]
    ret = np.zeros(len(reward), dtype=np.float32)
    nxt = {}
    for t in range(len(reward) - 1, -1, -1):
        k = traj[t]
        ret[t] = reward[t] + gamma * (0.0 if done[t] else nxt.get(k, 0.0))
        nxt[k] = ret[t]
    return ret


@torch.no_grad()
def forward(model, batch: dict, device: str) -> dict:
    """Masked policy stats and the value for every row, in micro-batches of MICRO (tokens trimmed as in ppo_update)."""
    T = len(batch["action"])
    inputs = [torch.from_numpy(np.ascontiguousarray(x)).to(device) for x in batch["inputs"]]
    offsets = torch.from_numpy(batch["legal_offsets"].astype(np.int64)).to(device)
    ids = torch.from_numpy(batch["legal_ids"].astype(np.int64)).to(device)
    kind = inputs[1]
    tok_len = ((kind > 0).long() * torch.arange(1, kind.shape[1] + 1, device=device)).amax(1)
    order = torch.argsort(tok_len)
    out = {k: np.zeros(T, dtype=np.float32) for k in ("H", "margin", "v")}
    out["n_legal"] = np.zeros(T, dtype=np.int64)
    for m in range(0, T, MICRO):
        j = order[m:m + MICRO]
        xs = [x[j] for x in inputs]
        L = int(tok_len[j].max())
        xs[:3] = [x[:, :L] for x in xs[:3]]
        logits, v = model(*xs)
        mask = legal_mask(j, offsets, ids, model.action_size)
        logp = torch.log_softmax(logits.float().masked_fill(~mask, -1e9), dim=-1)
        p = logp.exp()
        top = p.topk(2, dim=-1).values
        H = -(p * logp).masked_fill(~mask, 0.0).sum(-1)
        jj = j.cpu().numpy()
        out["H"][jj] = H.cpu().numpy()
        out["margin"][jj] = (top[:, 0] - top[:, 1]).cpu().numpy()
        out["v"][jj] = v.float().reshape(-1).cpu().numpy()
        out["n_legal"][jj] = mask.sum(-1).cpu().numpy()
    return out


def group_stats(sel: np.ndarray, R: dict) -> dict:
    """The per-group numbers of the docstring over the rows in `sel`."""
    n = int(sel.sum())
    if n == 0:
        return {"rows": 0}
    nl = R["n_legal"][sel]
    free = nl >= 2
    hn = R["Hn"][sel][free]
    mg = R["margin"][sel][free]
    adv, ret, v = R["adv"][sel], R["ret"][sel], R["v"][sel]
    vr = float(np.var(ret))
    return {"rows": n, "share": n / len(sel), "forced_share": float((nl == 1).mean()), "mean_n_legal": float(nl.mean()),
            "free_rows": int(free.sum()),
            "mean_norm_entropy": float(hn.mean()) if len(hn) else None,
            "median_margin": float(np.median(mg)) if len(mg) else None,
            "mean_adv": float(adv.mean()), "mean_abs_adv": float(np.abs(adv).mean()), "sd_adv": float(adv.std()),
            "value_mse": float(((v - ret) ** 2).mean()),
            "explained_var": float(1 - np.var(ret - v) / vr) if vr > 0 else None}


def clean(x):
    """JSON-safe: numpy scalars to Python, nan to null."""
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return None if x != x else float(x)
    return x


def call(main: dict, prompt: dict) -> str:
    if not main.get("rows") or not prompt.get("rows"):
        return "undetermined"
    mev, pev = main["explained_var"], prompt["explained_var"]
    if prompt["mean_abs_adv"] < 0.5 * main["mean_abs_adv"] and pev is not None and mev is not None and pev < mev:
        return "blind"
    h = prompt["mean_norm_entropy"]
    if h is None:
        return "undetermined"
    return "unexplored" if h > 0.8 else "confident" if h < 0.3 else "mixed"


def fmt(x, d=3):
    return "-" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default=None, help="checkpoint (.pt); default the autoresearch start pilot")
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--iterations", type=int, default=1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dir", default="runs/probe/C76-promptstats")
    ap.add_argument("--out", default=None)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--transitions", type=int, default=4096)
    ap.add_argument("--concurrency", type=int, default=108)
    args = ap.parse_args()
    run = Path(args.dir)
    run.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else run / "promptstats.json"
    t0 = time.time()
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = args.device
    workers = limits.cap_workers(args.workers)
    limits.apply(device, workers)
    if args.pilot:
        model, _ = load_policy(args.pilot, device)
    else:
        model, _ = fixed.start_model(device, {})
    model.eval()
    matchups = fixed.practice_matchups()
    pool = RemotePool(workers)
    pool.pace = 0.25
    games, errors, parts = 0, 0, []
    try:
        for it in range(args.iterations):
            msgs = [{"cmd": "collect", "encoding": "tokens", "transitions": args.transitions,
                     "concurrency": args.concurrency, "seed": args.seed * 1_000_003 + it * 1009 + w, **fixed.GAME,
                     "matchups": matchups, "opponents": [{"spec": "self", "weight": 1.0}],
                     "out": str(run / f"rollout_it{it}_w{w}.bin"), "history": 0} for w in range(workers)]
            replies = pool.collect(msgs, {0: model}, device)
            batch = concat([read_rollout(r["out"]) for r in replies])
            results = [g for r in replies for g in r["results"]]
            games += len(results)
            errors += sum(1 for g in results if g.get("error"))
            batch["adv"], _ = advantages(batch, GAMMA, LAM)
            batch["ret"] = mc_returns(batch, GAMMA)
            batch["inputs"] = model_inputs(batch, "tokens")
            f = forward(model, batch, device)
            glob = batch["inputs"][3]
            f.update(adv=batch["adv"], ret=batch["ret"], ptype=glob[:, PO:PO + NP + 1].argmax(1),
                     msg=glob[:, PO + NP + 1:PO + NP + 1 + MSG_HASH].argmax(1), none_slot=glob[:, NONE_SLOT])
            parts.append(f)
            print(f"it {it} games {len(results)} rows {len(batch['action'])} {time.time() - t0:.0f}s", flush=True)
    finally:
        pool.close()
    R = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    R["Hn"] = R["H"] / np.log(np.maximum(R["n_legal"], 2))
    # prompt rows: "no prompt open" byte is 0 (as ar/train.py); cross-check against the one-hot's argmax
    is_prompt = R["none_slot"] == 0
    agree = float((is_prompt == (R["ptype"] != NP)).mean())
    N = len(is_prompt)
    everything = np.ones(N, dtype=bool)

    def add(name, sel, store):
        s = group_stats(sel, R)
        if s["rows"]:
            s["share"] = s["rows"] / N
        store[name] = s
        return s

    groups = {"a_main_vs_prompt": {}, "b_prompt_type": {}, "c_type_message": {}}
    add("all", everything, groups["a_main_vs_prompt"])
    main_s = add("main", ~is_prompt, groups["a_main_vs_prompt"])
    prompt_s = add("prompt", is_prompt, groups["a_main_vs_prompt"])
    for t in range(NP):
        add(PROMPT_TYPES[t], is_prompt & (R["ptype"] == t), groups["b_prompt_type"])
    for t in range(NP):
        for b in range(MSG_HASH):
            sel = is_prompt & (R["ptype"] == t) & (R["msg"] == b)
            if sel.sum() >= MIN_ROWS:
                add(f"{PROMPT_TYPES[t]}|bin{b}", sel, groups["c_type_message"])
    verdict = call(main_s, prompt_s)
    res = {"args": vars(args), "games": games, "errors": errors, "rows": N, "wall_s": round(time.time() - t0, 1),
           "prompt_flag_agrees_with_onehot": agree, "call": verdict,
           "bands": {"blind": "prompt mean|adv| < 0.5 x main's and prompt EV < main EV",
                     "unexplored": "prompt mean norm entropy > 0.8", "confident": "< 0.3", "mixed": "otherwise"},
           "groups": groups}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(clean(res), indent=1), encoding="utf-8")
    print(f"\ngames {games} errors {errors} rows {N} call {verdict} (byte 48 vs one-hot agree {agree:.4f})")
    print("| group | rows | share | forced | n_legal | H/log n | med margin | mean adv | mean abs adv | sd adv | v MSE | EV |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for part in groups.values():
        for name, s in part.items():
            if not s["rows"]:
                continue
            print(f"| {name} | {s['rows']} | {s['share']:.3f} | {s['forced_share']:.3f} | {s['mean_n_legal']:.2f} | "
                  f"{fmt(s['mean_norm_entropy'])} | {fmt(s['median_margin'])} | {s['mean_adv']:.3f} | "
                  f"{s['mean_abs_adv']:.3f} | {s['sd_adv']:.3f} | {s['value_mse']:.3f} | {fmt(s['explained_var'])} |")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
