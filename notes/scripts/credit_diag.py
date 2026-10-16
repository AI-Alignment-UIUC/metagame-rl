"""Credit diagnostic (log #75; evaluation only): how far back in a game the training signal reaches.

The pilot has no memory (each decision sees only the current state), so nothing is backpropagated through time:
the only route by which a result reaches an earlier decision is the advantage PPO is trained on, GAE(lambda) over
one player's decisions with gamma 1, bridged by the value head. This measures that route against ground truth.

collect  self-play games with a pilot, sampled as in training, on random pairs of a deck panel; every decision of
         both seats is recorded. At sampled main-phase decisions env/remote_worker.js qprobe plays each option (up to
         --max-options, always the one played) to the end of the game --rollouts times from copies of the game,
         the pilot sampling in both seats: Q^pi(s, a) by Monte Carlo.
analyse  per probe: the true advantage of the action played, A* = Q(s, a_t) - V^pi(s), V^pi = sum_a pi(a|s) Q(s, a)
         (pi from the pilot, renormalised over the probed options); the policy improvement gap max_a Q - V^pi
         (split-half: the best option picked on one half of the lines, valued on the other, so it is not inflated
         by noise); the advantages training would assign from the recorded game: GAE for several lambdas (lambda 0
         is the one-step TD error, lambda 1 the Monte Carlo z - V). By game turn and by the player's decisions to
         the end of the game: the correlation of each with A*, corrected for A*'s own noise by its split-half
         reliability, and the value head's explained variance against the result over every decision.

Run: PYTHONPATH=. .venv/Scripts/python.exe notes/scripts/credit_diag.py --pilot runs/abl/base/model_it00079.pt
       --games 280 --tag base79 [--panel train|heldout] [--rollouts 8] [--max-options 8] [--probe-p 0.12]
     PYTHONPATH=. .venv/Scripts/python.exe notes/scripts/credit_diag.py --analyse-only --tag base79
Writes runs/credit/<tag>/ (worker files, probes.json) and runs/credit/<tag>.json (the summary).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

from rl import limits
from rl.gpu_matrix import load_policy
from rl.remote import RemotePool
from rl.rollouts import read_rollout
from rl.train import TOKEN_FIELDS, advantages

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/credit"
LAMBDAS = (0.0, 0.5, 0.8, 0.9, 0.95, 0.98, 0.99, 1.0)
TURN_BINS = ((1, 2), (3, 4), (5, 6), (7, 9), (10, 14), (15, 999))
END_BINS = ((0, 4), (5, 9), (10, 19), (20, 39), (40, 79), (80, 10 ** 6))


class PolicyValue(torch.nn.Module):
    """One pilot's policy with another network's value (notes/scripts/value_refit.py): the probe's rollouts then
    play exactly as the pilot, and only the values, the signals training would compute, change."""

    def __init__(self, policy, value):
        super().__init__()
        self.p, self.v = policy, value
        self.memory, self.cfg = "none", policy.cfg

    def forward(self, *x, **kw):
        return self.p(*x)[0], self.v(*x)[1]


def collect(args):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    workers = limits.cap_workers(args.workers)
    limits.apply(device, workers)
    model, enc = load_policy(args.pilot, device)
    assert enc == "tokens"
    assert model.memory == "none", "copies of a game do not carry a memory pilot's state (log #76)"
    if args.value_pilot:
        model = PolicyValue(model, load_policy(args.value_pilot, device)[0])
    decks = json.load(open(ROOT / "runs/abl/decks.json"))[args.panel]
    rng = np.random.default_rng(args.seed)
    jobs = []
    for g in range(args.games):
        i, j = (int(x) for x in rng.choice(len(decks), 2, replace=False))
        jobs.append({"i": i, "j": j, "iSeat": 1 + g % 2, "seed": args.seed * 1000003 + g})
    d = OUT / args.tag
    d.mkdir(parents=True, exist_ok=True)
    pool = RemotePool(workers)
    pool.pace = args.pace
    t0 = time.time()
    try:
        msgs = [{"cmd": "qprobe", "decks": decks, "jobs": jobs[w::workers], "out": str(d / f"w{w}.bin"),
                 "probeP": args.probe_p, "maxProbes": args.max_probes, "maxOptions": args.max_options,
                 "rollouts": args.rollouts, "seed": args.seed * 100 + w, "concurrency": args.concurrency,
                 "deckoutWin": args.deckout_win, "redeal": args.redeal,
                 "history": int(model.cfg.get("history", 0) or 0)} for w in range(workers)]
        replies = pool.collect(msgs, {0: model}, device)
    finally:
        pool.close()
    meta = {"pilot": args.pilot, "panel": args.panel, "games": args.games, "rollouts": args.rollouts,
            "max_options": args.max_options, "probe_p": args.probe_p, "max_probes": args.max_probes, "seed": args.seed,
            "redeal": args.redeal, "value_pilot": args.value_pilot,
            "seconds": round(time.time() - t0, 1), "lines": sum(r["lines"] for r in replies),
            "line_errors": sum(r["lineErrors"] for r in replies),
            "game_errors": sum(1 for r in replies for g in r["results"] if g.get("error"))}
    probes = [dict(p, worker=w) for w, r in enumerate(replies) for p in r["probes"]]
    json.dump({"meta": meta, "probes": probes, "results": [r["results"] for r in replies]}, open(d / "probes.json", "w"))
    print(json.dumps(meta), flush=True)


def corr(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or x.std() < 1e-12 or y.std() < 1e-12:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def boot_corr(x, y, n=400, seed=0):
    """Correlation and a bootstrap 95% interval over probes."""
    c = corr(x, y)
    if c is None:
        return None, None
    rng = np.random.default_rng(seed)
    x, y = np.asarray(x, float), np.asarray(y, float)
    bs = [corr(x[i], y[i]) for i in (rng.integers(0, len(x), len(x)) for _ in range(n))]
    bs = [b for b in bs if b is not None]
    return c, (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))


def analyse(args):
    d = OUT / args.tag
    blob = json.load(open(d / "probes.json"))
    meta, probes = blob["meta"], blob["probes"]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _ = load_policy(meta["pilot"], device)
    workers = sorted({p["worker"] for p in probes} | set(range(len(blob["results"]))))
    every = {"ev": [], "end": [], "turn": [], "z": [], "v": []}
    rows = []
    for w in workers:
        f = d / f"w{w}.bin"
        if not f.exists():
            continue
        r = read_rollout(str(f))
        T = len(r["action"])
        if T == 0:
            continue
        traj, value = r["traj"], r["value"].astype(np.float64)
        # Position in the player's own decision sequence, decisions to its end, and the result z (its last reward).
        end = np.zeros(T, np.int64)
        z = np.zeros(T)
        last = {}
        for t in range(T - 1, -1, -1):
            k = int(traj[t])
            if k not in last:
                last[k] = (t, float(r["reward"][t]), 0)
            else:
                last[k] = (last[k][0], last[k][1], last[k][2] + 1)
            end[t], z[t] = last[k][2], last[k][1]
        turn = r["obs.glob"].reshape(T, -1)[:, 0].astype(np.int64)
        every["end"].append(end); every["turn"].append(turn); every["z"].append(z); every["v"].append(value)
        gae = {lam: advantages(r, 1.0, lam)[0].astype(np.float64) for lam in LAMBDAS}
        mine = [p for p in probes if p["worker"] == w]
        if not mine:
            continue
        idx = np.array([p["k"] for p in mine], np.int64)
        with torch.no_grad():
            xs = [torch.from_numpy(np.ascontiguousarray(r[k].reshape(T, -1)[idx] if k != "obs.nCand" else r[k][idx])).to(device)
                  for k in TOKEN_FIELDS]
            logits, v = model(*xs)
            logits = logits.float().cpu().numpy()
        for n, p in enumerate(mine):
            k = p["k"]
            nopt = p["nOptions"]
            lg = logits[n, :nopt]
            pi = np.exp(lg - lg.max()); pi /= pi.sum()
            probed = np.array(p["probed"])
            q = [np.array(x, float) for x in p["q"]]
            if any(len(x) < 2 for x in q):
                continue
            pp = pi[probed]
            mass = float(pp.sum())
            pp = pp / pp.sum()
            Q = np.array([x.mean() for x in q])
            Qa = np.array([x[0::2].mean() for x in q])
            Qb = np.array([x[1::2].mean() for x in q])
            ci = int(np.where(probed == p["chosen"])[0][0])
            vpi, vpa, vpb = float(pp @ Q), float(pp @ Qa), float(pp @ Qb)
            gap = 0.5 * ((Qb[np.argmax(Qa)] - vpb) + (Qa[np.argmax(Qb)] - vpa))
            mode = int(np.argmax(pp))
            credit = None
            # --options: the credit terms over the options the pilot plays (pi >= 0.1), or the ones it rarely plays,
            # whose successor states the value has seen little of in training
            keep = {"all": np.ones(len(probed), bool), "likely": pi[probed] >= 0.1, "unlikely": pi[probed] < 0.1}[args.options]
            if "sig" in p and keep.sum() >= 2:   # expected training signal per option (qprobe, GAE along each line)
                S = np.array(p["sig"], float)[keep]                    # [options, lambdas, lines]
                Sa, Sb = S[:, :, 0::2].mean(-1), S[:, :, 1::2].mean(-1)  # [options, lambdas]
                ca, cb = Qa[keep] - Qa[keep].mean(), Qb[keep] - Qb[keep].mean()
                credit = {"qq": float(ca @ cb), "dof": int(keep.sum()) - 1,
                          "sq": (0.5 * ((Sb - Sb.mean(0)).T @ ca + (Sa - Sa.mean(0)).T @ cb)).tolist(),
                          "ss": ((Sa - Sa.mean(0)) * (Sb - Sb.mean(0))).sum(0).tolist(),
                          "noise": S.var(-1, ddof=1).mean(0).tolist()}
            rows.append({"turn": p["turn"], "end": int(end[k]), "n_options": nopt, "mass": mass, "credit": credit,
                         "a_star": float(Q[ci] - vpi), "a_star_a": float(Qa[ci] - vpa), "a_star_b": float(Qb[ci] - vpb),
                         "gap": float(gap), "mode_regret": 0.5 * float((Qb[np.argmax(Qa)] - Qb[mode]) + (Qa[np.argmax(Qb)] - Qa[mode])),
                         "q_spread": float(Q.max() - Q.min()), "v_net": float(value[k]), "v_pi": vpi, "z": float(z[k]),
                         "after": float(np.mean([np.mean(a) for a in p["after"]])),
                         **{f"gae{lam}": float(gae[lam][k]) for lam in LAMBDAS}})
    ev_all = {key: np.concatenate(v) for key, v in every.items() if key != "ev"}

    def ev(sel):
        zz, vv = ev_all["z"][sel], ev_all["v"][sel]
        if sel.sum() < 30 or zz.var() < 1e-9:
            return None
        return round(float(1 - (zz - vv).var() / zz.var()), 3)

    def table(key, bins, src):
        out = []
        for lo, hi in bins:
            sel = [x for x in src if lo <= x[key] <= hi]
            row = {"bin": f"{lo}-{hi if hi < 999 else '+'}", "probes": len(sel)}
            allsel = (ev_all[key] >= lo) & (ev_all[key] <= hi)
            row["decisions"] = int(allsel.sum())
            row["value_ev"] = ev(allsel)
            row["reach_0.95"] = round(float(np.mean(0.95 ** ev_all["end"][allsel])), 3) if allsel.any() else None
            if len(sel) >= 20:
                a = np.array([x["a_star"] for x in sel])
                rel = corr([x["a_star_a"] for x in sel], [x["a_star_b"] for x in sel])
                rel_full = 2 * rel / (1 + rel) if rel is not None and rel > 0 else None
                row.update({"abs_a_star": round(float(np.abs(a).mean()), 4), "gap": round(float(np.mean([x["gap"] for x in sel])), 4),
                            "mode_regret": round(float(np.mean([x["mode_regret"] for x in sel])), 4),
                            "q_spread": round(float(np.mean([x["q_spread"] for x in sel])), 3),
                            "a_star_reliability": None if rel_full is None else round(rel_full, 3),
                            "v_err": round(float(np.mean([abs(x["v_net"] - x["v_pi"]) for x in sel])), 3),
                            "decisions_after": round(float(np.mean([x["after"] for x in sel])), 1)})
                for lam in LAMBDAS:
                    c, ci = boot_corr([x[f"gae{lam}"] for x in sel], a)
                    row[f"corr{lam}"] = None if c is None else round(c, 3)
                    row[f"ci{lam}"] = None if ci is None else [round(ci[0], 3), round(ci[1], 3)]
                    if c is not None and rel_full:
                        row[f"true_corr{lam}"] = round(c / np.sqrt(rel_full), 3)
            out.append(row)
        return out

    def credit_table(key, bins, src):
        """Share of the true credit that reaches a decision: for options of the same decision, the covariance of the
        expected training signal GAE(lambda) (one half of the lines) with the option's true value Q (the other half),
        over the same for the Monte Carlo signal (lambda 1, which is Q - V: share 1). Below 1, part of an option's
        true effect never reaches its decision's gradient; noise_sd is the signal's spread over single games."""
        lams = next((p["lams"] for p in probes if "lams" in p), None)
        out = []
        for lo, hi in bins:
            sel = [x for x in src if lo <= x[key] <= hi and x["credit"] is not None]
            row = {"bin": f"{lo}-{hi if hi < 999 else '+'}", "probes": len(sel)}
            if len(sel) >= 20 and lams:
                qq = np.array([x["credit"]["qq"] for x in sel])
                sq = np.array([x["credit"]["sq"] for x in sel])            # [probes, lambdas]
                dof = np.array([x["credit"]["dof"] for x in sel])
                noise = np.array([x["credit"]["noise"] for x in sel]).mean(0)
                ss = np.array([x["credit"]["ss"] for x in sel]).sum(0)        # variance of the expected signal (halves)
                share = sq.sum(0) / qq.sum()
                # alignment: the correlation, across a decision's options, of the expected training signal with the
                # true value (1 = the signal ranks the options as Q does, only scaled; below 1 = biased direction)
                align = sq.sum(0) / np.sqrt(np.maximum(ss, 1e-12) * qq.sum())
                rng = np.random.default_rng(1)
                bs = []
                for _ in range(400):
                    i = rng.integers(0, len(sel), len(sel))
                    if qq[i].sum() > 0:
                        bs.append(sq[i].sum(0) / qq[i].sum())
                bs = np.array(bs)
                var_true = qq.sum() / dof.sum()
                row.update({"true_sd": round(float(np.sqrt(max(var_true, 0))), 4)})
                for li, lam in enumerate(lams):
                    row[f"share{lam}"] = round(float(share[li]), 3)
                    row[f"ci{lam}"] = [round(float(np.percentile(bs[:, li], 2.5)), 3), round(float(np.percentile(bs[:, li], 97.5)), 3)]
                    row[f"noise{lam}"] = round(float(np.sqrt(noise[li])), 3)
                    row[f"align{lam}"] = round(float(align[li]), 3) if ss[li] > 0 else None
                    # the signal-to-noise ratio of one game's signal for telling this decision's options apart
                    row[f"snr{lam}"] = round(float(share[li] ** 2 * max(var_true, 0) / max(noise[li], 1e-9)), 4)
            out.append(row)
        return out

    summary = {"meta": meta, "probes": len(rows),
               "credit_by_turn": credit_table("turn", TURN_BINS, rows), "credit_by_end": credit_table("end", END_BINS, rows),
               "credit_all": credit_table("turn", ((0, 10 ** 6),), rows)[0],
               "value_ev_all": ev(np.ones(len(ev_all["z"]), bool)),
               "by_turn": table("turn", TURN_BINS, rows), "by_end": table("end", END_BINS, rows),
               "all": table("turn", ((0, 10 ** 6),), rows)[0]}
    summary["options"] = args.options
    (OUT / f"{args.tag}{'' if args.options == 'all' else '_' + args.options}.json").write_text(json.dumps(summary, indent=1))
    show(summary)


def show(s):
    print(f"{s['meta']['pilot']}: {s['probes']} probes, value EV over all decisions {s['value_ev_all']}")
    for name in ("credit_by_turn", "credit_by_end"):
        rows = [r for r in s.get(name, []) if "true_sd" in r]
        if not rows:
            continue
        lams = [k[5:] for k in rows[0] if k.startswith("share")]
        print(f"\n{name}: share of the true credit reaching the decision (lambda 1 = 1), [snr of one game's signal]")
        print("bin      probes  sd(dQ)  " + "  ".join(f"l={l:<11}" for l in lams))
        for r in rows:
            print(f"{r['bin']:<8} {r['probes']:6d}  {r['true_sd']:.3f}   " +
                  "  ".join(f"{r['share' + l]:5.2f} [{r['snr' + l]:.3f}]" for l in lams))
        print("alignment of the expected signal with Q across a decision's options (1 = right direction):")
        for r in rows:
            print(f"{r['bin']:<8} {r['probes']:6d}           " +
                  "  ".join(f"{r['align' + l] if r['align' + l] is not None else float('nan'):5.2f}         " for l in lams))
    for name in ("by_turn", "by_end"):
        print(f"\n{name}  (corr = corr(training advantage, true advantage A*), corrected for A*'s noise)")
        print("bin      probes  EV(V)  reach.95  |A*|    gap     q_spread  rel   " + "  ".join(f"l={l:<4}" for l in LAMBDAS))
        for r in s[name]:
            tc = "  ".join(f"{r.get(f'true_corr{l}', float('nan')) if r.get(f'true_corr{l}') is not None else float('nan'):6.3f}" for l in LAMBDAS)
            print(f"{r['bin']:<8} {r['probes']:6d}  {r['value_ev'] if r['value_ev'] is not None else float('nan'):5.2f}  "
                  f"{r['reach_0.95'] if r['reach_0.95'] is not None else float('nan'):7.3f}  "
                  f"{r.get('abs_a_star', float('nan')):6.3f}  {r.get('gap', float('nan')):6.3f}  {r.get('q_spread', float('nan')):7.3f}  "
                  f"{r.get('a_star_reliability') if r.get('a_star_reliability') is not None else float('nan'):5.2f}  {tc}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pilot", help="an rl.train snapshot")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--panel", choices=["train", "heldout"], default="train")
    ap.add_argument("--games", type=int, default=280)
    ap.add_argument("--rollouts", type=int, default=8)
    ap.add_argument("--max-options", type=int, default=8)
    ap.add_argument("--max-probes", type=int, default=4)
    ap.add_argument("--probe-p", type=float, default=0.12)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--concurrency", type=int, default=64)
    ap.add_argument("--pace", type=float, default=0.25)
    ap.add_argument("--deckout-win", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=75)
    ap.add_argument("--redeal", action="store_true",
                    help="re-deal what the deciding player can't see in each line (Q over its information set)")
    ap.add_argument("--value-pilot", help="play --pilot's policy with this checkpoint's value (value_refit.py)")
    ap.add_argument("--options", choices=["all", "likely", "unlikely"], default="all",
                    help="analyse: credit over all probed options, those the pilot plays (pi >= 0.1), or the others")
    ap.add_argument("--analyse-only", action="store_true")
    args = ap.parse_args(argv)
    if not args.analyse_only:
        if not args.pilot:
            sys.exit("--pilot is needed to collect")
        collect(args)
    analyse(args)


if __name__ == "__main__":
    main()
