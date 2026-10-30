"""A1 (runs/probe/A1-targetsignal/record.md): does the RL signal at a Trainer's prompt say which target is better?
Evaluation only: nothing here trains, and nothing it measures is ever trained on.

The pilot (sampled, both seats) plays the practice matchups; env/tools/probe_target_worker.js branches the decisions the
quotas still need (each Trainer prompt of the named five, prompts of any Trainer, main-phase control): every answer (all if
8 or fewer, else the pilot's greedy answer, the answer the live game took, and uniform draws) x m re-dealt copies (the same
seeds for every answer), played to the game's end with the pilot sampled at temperature 1 on both seats (the draws made in
JS from the pilot's probabilities, by an Rng seeded per rollout index: CRN). This driver runs batches of games until the
quotas fill (or --max-games), then reruns the pilot offline on each stored prompt row (probabilities, the input of
model.score for every answer, V0) and computes the record's readouts.

Run: see runs/probe/A1-targetsignal/chain.sh.
"""
import argparse
import collections
import gzip
import json
import math
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import torch
from scipy.stats import rankdata

from rl import limits
from rl.gpu_matrix import GpuMatrix, load_policy
from rl.remote import CHUNK, RESPONSE, TOKEN_INPUTS, RemotePool, pack_arrays, trim_inputs
from rl.train import round_turns

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "env" / "tools" / "probe_target_worker.js"
NAMED = ["Computer Search", "Super Energy Removal", "Energy Removal", "Energy Retrieval", "Gust of Wind"]
LAM = 0.95
ROWS_PER_S = 7000.0         # ASSUMED inference rows a second on the GPU (C76: 62-82 games/s x ~100 decisions); sizing only


class ProbePool(RemotePool):
    """RemotePool over the A1 worker. It adds each batch's probe parameters and a share of its quotas to every games command
    (collect), keeps the replies' probes and counts, and serves the lines' requests (header probs: 1) with the pilot's
    probabilities over the row's legal ids too (the server of rl/remote.py, with that one addition)."""

    def __init__(self, n: int):
        super().__init__(0)
        self.procs = [subprocess.Popen(["node", str(WORKER)], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)
                      for _ in range(n)]
        for i, p in enumerate(self.procs):
            threading.Thread(target=self._reader, args=(i, p), daemon=True).start()
        self.cfg = None         # {m, cap, ...probe parameters, need: {...}, rot} of the batch about to play
        self.probes, self.stats = [], []

    def collect(self, msgs, models, device):
        W = len(msgs)
        if self.cfg is not None:
            need = self.cfg["need"]
            for w, m in enumerate(msgs):
                share = {k: int(n) // W + (1 if (w - self.cfg["rot"]) % W < int(n) % W else 0) for k, n in need.items()}
                m["probe"] = {**{k: v for k, v in self.cfg.items() if k not in ("need", "rot")}, "need": share}
        replies = super().collect(msgs, models, device)
        for r in replies:
            if "targetProbes" in r:
                self.probes += r["targetProbes"]
                self.stats.append(r["targetStats"])
        return replies

    @torch.no_grad()
    def _serve_batches(self, requests, models, device):
        by_slot = {}
        for r in requests:
            by_slot.setdefault((r[1]["slot"], bool(r[1].get("greedy"))), []).append(r)
        for (slot, greedy), group in by_slot.items():
            model = models[slot]
            assert getattr(model, "memory", "none") == "none" and group[0][1]["encoding"] == "tokens"
            ns = [h["n"] for _, h, _ in group]
            B = sum(ns)

            def cat(k):
                return torch.from_numpy(np.concatenate([a[k] for _, _, a in group])).to(device)

            inputs = [cat(k) for k in TOKEN_INPUTS]
            inputs = [x.view(B, -1) if k != "n_cand" else x for k, x in zip(TOKEN_INPUTS, inputs)]
            self._chain_guard(model, inputs[5], B)
            inputs = trim_inputs(inputs, model)
            if B > CHUNK:
                parts = [model(*[x[c:c + CHUNK] for x in inputs]) for c in range(0, B, CHUNK)]
                logits, value = torch.cat([p[0] for p in parts]), torch.cat([p[1] for p in parts])
            else:
                logits, value = model(*inputs)
            rows, cols, row = [], [], 0
            for _, h, a in group:
                rows.append(np.repeat(np.arange(h["n"]) + row, np.diff(a["legal_offsets"])))
                cols.append(a["legal_ids"])
                row += h["n"]
            rows, cols = (torch.from_numpy(np.concatenate(x).astype(np.int64)).to(device) for x in (rows, cols))
            mask = torch.zeros(logits.shape, dtype=torch.bool, device=device)
            mask[rows, cols] = True
            logp_all = torch.log_softmax(logits.float().masked_fill(~mask, -1e9), -1)
            if greedy:
                action = logp_all.argmax(-1)
                sampled = torch.zeros(B, dtype=torch.bool, device=device)
            else:
                action = torch.multinomial(logp_all.exp(), 1).squeeze(1)
                sampled = torch.ones(B, dtype=torch.bool, device=device)
            logp = logp_all.gather(1, action[:, None]).squeeze(1)
            flat = logp_all[rows, cols].exp().cpu().numpy().astype(np.float32)     # each legal id's probability
            action, sampled = action.int().cpu().numpy(), sampled.cpu().numpy().astype(np.uint8)
            logp, value = logp.cpu().numpy(), value.float().cpu().numpy()
            start = lstart = 0
            for (i, h, a), n in zip(group, ns):
                sl = slice(start, start + n)
                L = len(a["legal_ids"])
                extra = [("probs", flat[lstart:lstart + L])] if h.get("probs") else []
                self._send(i, RESPONSE, pack_arrays({"id": h["id"], "n": n},
                                                    [("action", action[sl]), ("logp", logp[sl]), ("value", value[sl]),
                                                     ("sampled", sampled[sl])] + extra))
                start += n
                lstart += L


# ---------------------------------------------------------------------------------------------------------------- play
def sum_stats(stats: list) -> dict:
    out = {}
    for s in stats:
        for k, v in s.items():
            if isinstance(v, dict):
                d = out.setdefault(k, {})
                for q, n in v.items():
                    d[q] = d.get(q, 0) + n
            else:
                out[k] = out.get(k, 0) + v
    return out


def counts(probes: list) -> dict:
    c = collections.Counter(p["stratum"] for p in probes)
    return {"named": {s: c.get(s, 0) for s in NAMED}, "prompts": sum(v for k, v in c.items() if k != "main"), "main": c.get("main", 0)}


def needs(probes: list, args) -> dict:
    c = counts(probes)
    out = {s: max(0, args.per_trainer - c["named"][s]) for s in NAMED}
    out["any"] = max(0, args.prompts - c["prompts"])
    out["main"] = max(0, args.main - c["main"])
    return out


def play(model, args, device) -> dict:
    """Batches of games on the practice matchups until the quotas fill or --max-games."""
    matchups = json.loads((ROOT / args.matchups).read_text())
    rng = np.random.default_rng(args.seed)
    rounds = round_turns(args.round_turns)
    rp = ProbePool(args.workers)
    rp.pace = 0.25
    gm = GpuMatrix.attach(model, rp, args.workers, device=device, greedy=args.live_greedy)
    total_need = args.prompts + args.main
    m, key, batch, games, results, errors = args.m, 0, 0, 0, [], 0
    timed, t_start, log = False, time.time(), []
    probes, stats = [], []
    try:
        while games < args.max_games:
            need = needs(probes, args)
            if not any(need.values()):
                break
            if not timed:                                    # the first batches take only about 20 decisions (the timing)
                need = {k: min(v, 2 if k in NAMED else 6 if k == "any" else 4) for k, v in need.items()}
            n = min(args.workers * (4 if not timed else args.batch_games), args.max_games - games)
            decks, pairs, keys = [], [], []
            for g in range(n):
                a, b = matchups[int(rng.integers(len(matchups)))]
                if g % 2:
                    a, b = b, a
                pairs.append((len(decks), len(decks) + 1)); decks += [a, b]; keys.append(key); key += 1
            rp.cfg = {"m": m, "cap": args.cap, "maxLine": args.max_line, "p": args.probe_p, "mainP": args.main_p,
                      "maxPerGame": args.max_probes_per_game, "minValid": args.min_valid, "need": need, "rot": batch}
            rp.probes, rp.stats = [], []
            t0 = time.time()
            gm.play(decks, 1, args.seed, pairs=pairs, pair_keys=keys, round_turns=rounds)
            games += n; batch += 1
            probes += rp.probes
            stats += rp.stats
            results += [{k: r.get(k) for k in ("seed", "winner", "ending", "turns", "steps", "error")} for r in gm.results]
            errors += sum(bool(r.get("error")) for r in gm.results)
            st = sum_stats(stats)
            c = counts(probes)
            print(f"batch {batch}: {n} games {time.time() - t0:.0f}s, probes {len(probes)} {json.dumps(c)}, lines {st.get('lines', 0)}, "
                  f"lineErrors {st.get('lineErrors', 0)}, game errors {errors}", flush=True)
            if args.save_partial:                        # a crash keeps the batches so far (BENCH O_B, 12:22)
                with gzip.open(str(ROOT / args.out) + ".probes.partial.json.gz", "wt") as f:
                    json.dump({"probes": probes, "stats": st, "games": games, "results": results, "game_errors": errors,
                               "log": log, "seconds": round(time.time() - t_start, 1), "m_final": m}, f)
            if st.get("lines", 0) >= 200 and st.get("lineErrors", 0) > 0.01 * st["lines"]:
                log.append(f"KILL: engine errors {st['lineErrors']} of {st['lines']} rollouts (over 1%)")
                print(log[-1], flush=True)
                break
            if not timed and (len(probes) >= 20 or batch >= 3):
                timed = True
                el = time.time() - t_start
                proj = el / max(len(probes), 1) * total_need / 60
                log.append(f"timing: {len(probes)} decisions in {el:.0f}s -> projected {proj:.0f} min for {total_need} decisions at m={m}")
                if proj > args.time_limit_min:
                    log.append(f"WARNING: PROJECTED {proj:.0f} MIN IS PAST {args.time_limit_min:.0f} MIN; m stays {m} (Evan decides the share)")
                print(*log, sep=chr(10), flush=True)
    finally:
        rp.close()
    return {"probes": probes, "stats": sum_stats(stats), "games": games, "results": results, "game_errors": errors, "log": log,
            "seconds": round(time.time() - t_start, 1), "m_final": m}


# ---------------------------------------------------------------------------------------------------------- offline pass
def offline(model, probes: list, device: str) -> None:
    """Reruns the pilot on each probe's stored prompt row: adds p["pi"] (probabilities over the legal ids), p["logits"],
    p["emb"] (the INPUT of model.score at each answer, captured by a forward pre-hook) and p["V0off"]."""
    cap = []
    h = model.score.register_forward_pre_hook(lambda mod, inp: cap.append(inp[0].detach()))
    dt = {"tok_card": np.int16, "tok_kind": np.uint8, "tok_aux": np.uint8, "glob": np.uint8, "slots": np.uint8, "cand": np.int16}
    try:
        with torch.no_grad():
            for s in range(0, len(probes), 32):
                chunk = probes[s:s + 32]
                B = len(chunk)
                ins = [torch.from_numpy(np.stack([np.array(p["obs"][k], dtype=dt[k]) for p in chunk])).to(device) for k in dt]
                ins.append(torch.tensor([p["obs"]["n_cand"] for p in chunk], dtype=torch.int32, device=device))
                ins = trim_inputs(ins, model)
                cap.clear()
                logits, value = model(*ins)
                c = cap[0].float().cpu().numpy()
                logits, value = logits.float().cpu().numpy(), value.float().cpu().numpy()
                for i, p in enumerate(chunk):
                    legal = np.array(p["legal"])
                    lg = logits[i, legal].astype(np.float64)
                    pr = np.exp(lg - lg.max()); pr /= pr.sum()
                    p["pi"] = dict(zip(legal.tolist(), pr.tolist()))
                    p["logit"] = dict(zip(legal.tolist(), lg.tolist()))
                    p["emb"] = c[i, p["answers"]].tolist()
                    p["V0off"] = float(value[i])
    finally:
        h.remove()


# -------------------------------------------------------------------------------------------------------------- readouts
def gae(v0: float, vals: list, reward: float) -> float:
    """GAE advantage at the first row, gamma 1: deltas over V0, v1, ..., reward (no seat values: reward - V0)."""
    seq = [v0] + list(vals) + [reward]
    return float(sum(LAM ** k * (seq[k + 1] - seq[k]) for k in range(len(seq) - 1)))


def pearson(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or x.std() < 1e-12 or y.std() < 1e-12:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x, y):
    return pearson(rankdata(x), rankdata(y)) if len(x) >= 3 else None


def zpool(rs) -> dict:
    """Mean of Fisher z over decisions (None skipped), back-transformed."""
    rs = [r for r in rs if r is not None and not math.isnan(r)]
    if not rs:
        return {"r": None, "n": 0}
    z = np.arctanh(np.clip(rs, -0.999, 0.999))
    return {"r": round(float(np.tanh(z.mean())), 4), "n": len(rs)}


def prepare(p: dict) -> dict:
    """One probe's arrays: rewards R[a, j] (nan where a rollout is not valid), halves, Q, Vafter, pi, GAEs."""
    A, m = len(p["answers"]), p["m"]
    R = np.array([[np.nan if x is None else x for x in row] for row in p["rew"]], float)
    first = [[(v[0] if v else p["rew"][a][j]) if v is not None else np.nan for j, v in enumerate(row)] for a, row in enumerate(p["vals"])]
    Vf = np.array(first, float)
    half = np.arange(m) % 2
    pi = np.array([p["pi"][a] for a in p["answers"]]) if "pi" in p else None
    mass = float(pi.sum()) if pi is not None else None          # the pilot's probability the branched answers cover
    if pi is not None:
        pi = pi / pi.sum()
    greedy = p["answers"].index(p["greedy"]) if p["greedy"] in p["answers"] else (int(pi.argmax()) if pi is not None else 0)
    taken = p["answers"].index(p["taken"]) if p["taken"] in p["answers"] else None
    Q = np.nanmean(R, 1)
    Qh = [np.nanmean(R[:, half == h], 1) for h in (0, 1)]
    ok = ~np.isnan(R[0])
    d = R[:, ok] - np.nanmean(R[:, ok], 0, keepdims=True)          # CRN-paired: rollout effect common to the answers removed
    se2 = d.var(1, ddof=1) / ok.sum() if ok.sum() > 1 else np.full(A, np.nan)
    line_gae = None
    if taken is not None:
        line_gae = np.array([gae(p["V0"], p["vals"][taken][j], p["rew"][taken][j]) for j in range(m) if ok[j]])
    live = gae(p["V0"], p["liveVals"], p["liveReward"]) if p.get("liveReward") is not None else None
    return {"A": A, "Q": Q, "Qh": Qh, "Vf": np.nanmean(Vf, 1), "pi": pi, "greedy": greedy, "taken": taken, "se2": se2,
            "live": live, "line_gae": line_gae, "logit": np.array([p["logit"][a] for a in p["answers"]]) if "logit" in p else None,
            "emb": np.array(p["emb"]) if "emb" in p else None, "game": p["game"], "mass": mass}


def ridge_probe(D: list, lam: float, folds: int = 5) -> dict:
    """Ridge from the (within-decision centred) embeddings to Q centred within the decision, `folds` folds grouped by source game;
    the held-out within-decision Spearman, pooled by Fisher z, and top-1 accuracy against chance."""
    D = [d for d in D if d["emb"] is not None and not np.isnan(d["Q"]).any()]
    if len(D) < folds:
        return {"r": None, "n": 0}
    games = sorted({d["game"] for d in D})
    perm = np.random.default_rng(0).permutation(len(games))
    fold_of = {g: int(perm[k]) % folds for k, g in enumerate(games)}
    X = [d["emb"] - d["emb"].mean(0) for d in D]
    Y = [d["Q"] - d["Q"].mean() for d in D]
    rs, hit, chance = [], [], []
    for f in range(folds):
        tr = [i for i, d in enumerate(D) if fold_of[d["game"]] != f]
        te = [i for i, d in enumerate(D) if fold_of[d["game"]] == f]
        if not tr or not te:
            continue
        Xt, Yt = np.concatenate([X[i] for i in tr]), np.concatenate([Y[i] for i in tr])
        sd = Xt.std(0) + 1e-6
        Xs = Xt / sd
        w = np.linalg.solve(Xs.T @ Xs + lam * np.eye(Xs.shape[1]), Xs.T @ Yt)
        for i in te:
            pred = (X[i] / sd) @ w
            rs.append(spearman(pred, Y[i]) if D[i]["A"] >= 3 else None)
            hit.append(float(np.argmax(pred) == np.argmax(Y[i]))); chance.append(1.0 / D[i]["A"])
    out = zpool(rs)
    out.update({"top1": round(float(np.mean(hit)), 4), "chance": round(float(np.mean(chance)), 4), "n_decisions": len(hit)})
    return out


def readout(D: list, eligible_per_game: float) -> dict:
    """The record's readouts for one group of decisions."""
    if not D:
        return {"decisions": 0}
    D3 = [d for d in D if d["A"] >= 3 and not np.isnan(d["Q"]).any()]
    out = {"decisions": len(D), "decisions_A3": len(D3), "mean_answers": round(float(np.mean([d["A"] for d in D])), 2)}
    ms = [d["mass"] for d in D if d.get("mass") is not None]
    out["pi_mass_branched"] = {"mean": round(float(np.mean(ms)), 4), "min": round(float(np.min(ms)), 4)} if ms else None
    # R: Spearman-Brown split-half reliability of Q across answers, mean of Fisher z
    rsb = []
    for d in D3:
        r = pearson(d["Qh"][0], d["Qh"][1])
        rsb.append(None if r is None else 2 * r / (1 + r) if r > -0.99 else -0.999)
    out["R"] = zpool(rsb)
    # S: spread net of the paired SE
    sv = [max(0.0, float(np.var(d["Q"], ddof=1) - np.nanmean(d["se2"]))) for d in D if not np.isnan(d["Q"]).any() and not np.isnan(d["se2"]).any()]
    out["S"] = {"mean_sd": round(float(np.mean(np.sqrt(sv))), 4) if sv else None,
                "pooled": round(float(np.sqrt(np.mean(sv))), 4) if sv else None, "n": len(sv)}
    # G: best answer on one half, evaluated on the other, minus the pilot's greedy answer there; halves swapped
    g = []
    for d in D:
        if np.isnan(d["Qh"][0]).any() or np.isnan(d["Qh"][1]).any():
            continue
        g.append(np.mean([d["Qh"][1 - h][int(np.argmax(d["Qh"][h]))] - d["Qh"][1 - h][d["greedy"]] for h in (0, 1)]))
    if g:
        se = float(np.std(g, ddof=1) / np.sqrt(len(g))) if len(g) > 1 else float("nan")
        out["G"] = {"mean": round(float(np.mean(g)), 4), "se": round(se, 4), "upper90": round(float(np.mean(g)) + 1.28 * se, 4), "n": len(g)}
    out["rho_V"] = zpool([pearson(d["Vf"], d["Q"]) for d in D3])
    out["rho_pi"] = zpool([spearman(d["logit"], d["Q"]) if d["logit"] is not None else None for d in D3])
    # rho_A: the source game's GAE against A*(taken) = Q(taken) - sum pi Q
    T = [d for d in D if d["taken"] is not None and d["live"] is not None and d["pi"] is not None and not np.isnan(d["Q"]).any()]
    if T:
        live = np.array([d["live"] for d in T])
        Astar = np.array([d["Q"][d["taken"]] - float(d["pi"] @ d["Q"]) for d in T])
        out["rho_A"] = {"pearson": None if len(T) < 3 else round(pearson(live, Astar) or float("nan"), 4),
                        "spearman": None if len(T) < 3 else round(spearman(live, Astar) or float("nan"), 4), "n": len(T)}
        sd = float(np.std(live - Astar))
        nstar = (1.28 * sd / np.maximum(np.abs(Astar), 1e-9)) ** 2
        per = [(1.28 * float(d["line_gae"].std(ddof=1)) / max(abs(a), 1e-9)) ** 2 for d, a in zip(T, Astar)
               if d["line_gae"] is not None and len(d["line_gae"]) > 1]
        out["nstar"] = {"sd_gae_minus_Astar": round(sd, 4), "median_pooled_sd": round(float(np.median(nstar)), 1),
                        "median_per_decision_rollout_sd": round(float(np.median(per)), 1) if per else None,
                        "mean_abs_Astar": round(float(np.abs(Astar).mean()), 4), "n": len(T)}
        out["eligible_per_game"] = round(eligible_per_game, 3)
        if eligible_per_game > 0:
            out["nstar"]["games_for_median_pooled"] = round(float(np.median(nstar)) / eligible_per_game, 1)
    out["rho_probe"] = {str(lam): ridge_probe(D, lam) for lam in (10.0, 100.0, 1000.0)}
    out["rho_probe_primary"] = out["rho_probe"]["100.0"]
    return out


def verdict(r: dict) -> list:
    """Each band of the record, stated for one group's readout."""
    if r.get("decisions", 0) == 0 or "G" not in r:
        return ["no decisions"]
    out = []
    R = r["R"]["r"]
    sqR = math.sqrt(R) if R is not None and R > 0 else None
    out.append(f"R={R}: " + ("readable" if R is not None and R >= 0.3 else "unreadable (R < 0.3): rho_V, rho_A, rho_probe not readable; S and G stand"))
    G = r["G"]
    real = G["mean"] >= 0.01 and G["mean"] > 2 * G["se"]
    if G["upper90"] < 0.015:
        out.append(f"(c) small spread: G upper 90% bound {G['upper90']} < 0.015, the target is not the lever")
    elif real:
        out.append(f"real spread: G {G['mean']} >= 0.01 and > 2 SE ({G['se']})")
    else:
        out.append(f"between: G {G['mean']} (SE {G['se']}) is not real spread and not under 0.015: unreadable, more decisions next")
    if real and sqR is not None and R >= 0.3:
        rv, ra, rp = r["rho_V"]["r"], r.get("rho_A", {}).get("pearson"), r["rho_probe_primary"]["r"]
        if rv is not None and rv < 0.2 * sqR:
            out.append(f"(b) critic blind: rho_V {rv} < 0.2 sqrt(R) = {0.2 * sqR:.3f}")
        elif rv is not None and ra is not None and rv >= 0.5 * sqR and ra >= 0.2:
            out.append(f"(a) critic sees the target: rho_V {rv} >= {0.5 * sqR:.3f} and rho_A {ra} >= 0.2")
        else:
            out.append(f"partial: rho_V {rv}, rho_A {ra} (between the (a) and (b) bands): run (a) first, then (b)")
        if rp is not None:
            out.append(f"(d) representation fails: rho_probe {rp} < 0.2 sqrt(R) = {0.2 * sqR:.3f}" if rp < 0.2 * sqR
                       else f"information is in the embeddings: rho_probe {rp} >= 0.5 sqrt(R) = {0.5 * sqR:.3f}" if rp >= 0.5 * sqR
                       else f"rho_probe {rp} between 0.2 and 0.5 sqrt(R)")
    n = r.get("nstar", {}).get("median_pooled_sd")
    if n is not None:
        out.append(f"signal noise: median n* {n} " + ("> 1000: per-visit advantage too noisy for PPO to set the sign (favours (b)'s all-action gradient over (a))"
                                                      if n > 1000 else "< 100: PPO should have learned it, recheck (d)" if n < 100 else "(between 100 and 1000)"))
    rpi = r["rho_pi"]["r"]
    if rpi is not None and sqR is not None and rpi >= 0.3 * sqR:
        out.append(f"pipeline check: rho_pi {rpi} >= 0.3 sqrt(R) = {0.3 * sqR:.3f} contradicts X1: recheck X1 and this probe before any fix")
    return out


def analyze(probes: list, stats: dict, games: int) -> dict:
    D = [prepare(p) for p in probes]
    strata = [p["stratum"] for p in probes]
    el = stats.get("eligible", {})
    groups = {s: [d for d, k in zip(D, strata) if k == s] for s in NAMED + ["other", "main"]}
    groups["named5"] = [d for d, k in zip(D, strata) if k in NAMED]
    groups["prompts_all"] = [d for d, k in zip(D, strata) if k != "main"]
    rd = {}
    for name, ds in groups.items():
        epg = (sum(el.get(s, 0) for s in NAMED) if name == "named5" else sum(v for k, v in el.items() if k != "main") if name == "prompts_all"
               else el.get(name, 0)) / max(games, 1)
        rd[name] = readout(ds, epg)
        rd[name]["verdict"] = verdict(rd[name])
    main, pr = rd["main"], rd["named5"]
    if main.get("decisions") and pr.get("decisions"):
        mv, pv = main["rho_V"]["r"], pr["rho_V"]["r"]
        ma, pa = main.get("rho_A", {}).get("pearson"), pr.get("rho_A", {}).get("pearson")
        rd["control"] = (f"main rho_V {mv}, rho_A {ma}; named-5 rho_V {pv}, rho_A {pa}: " +
                         ("main-phase no higher than the prompts on both: prompts are not special, the fault is the critic in general"
                          if mv is not None and pv is not None and ma is not None and pa is not None and mv <= pv and ma <= pa
                          else "main-phase higher than the prompts on at least one: prompts are special (or one is unreadable)"))
    return rd


def clean(o):
    """JSON-safe: numpy scalars to Python, NaN to null."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if math.isnan(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    return o


# ------------------------------------------------------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default="ar/data/start.pt")
    ap.add_argument("--matchups", default="ar/data/practice.json", help="the practice matchups, [[deckA, deckB], ...]")
    ap.add_argument("--save-partial", action="store_true", help="rewrite <out>.probes.partial.json.gz after every batch")
    ap.add_argument("--max-games", type=int, default=3000, help="stop the batches here if the quotas are not full")
    ap.add_argument("--batch-games", type=int, default=6, help="games a worker a batch (after the timing batch)")
    ap.add_argument("--per-trainer", type=int, default=50, help="decisions each of the 5 named Trainers at least")
    ap.add_argument("--prompts", type=int, default=300, help="own-Trainer prompt decisions in all")
    ap.add_argument("--main", type=int, default=50, help="main-phase control decisions")
    ap.add_argument("--probe-p", type=float, default=0.3, help="chance a needed prompt decision is probed")
    ap.add_argument("--main-p", type=float, default=0.02, help="chance a needed main-phase decision is probed")
    ap.add_argument("--max-probes-per-game", type=int, default=3)
    ap.add_argument("--cap", type=int, default=8, help="answers a decision at most")
    ap.add_argument("--m", type=int, default=32, help="rollouts a answer (halves of m/2 by rollout index parity)")
    ap.add_argument("--min-valid", type=int, default=16, help="valid re-dealt copies a decision needs, else it is dropped")
    ap.add_argument("--max-line", type=int, default=600)
    ap.add_argument("--time-limit-min", type=float, default=60.0, help="projected minutes past which the timing warns (m is not changed)")
    ap.add_argument("--live-greedy", action="store_true", help="live games greedy (the determinism check: sampling is not reproducible)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--round-turns", default="20-45")
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default=None)
    ap.add_argument("--from-raw", default=None, help="skip the games: reanalyse a stored <out>.probes.json.gz")
    args = ap.parse_args(argv)
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    args.workers = limits.cap_workers(args.workers)
    limits.apply(device, args.workers)
    model, enc = load_policy(args.pilot, device)
    assert enc == "tokens"
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if args.from_raw:
        raw = json.loads(gzip.open(args.from_raw, "rt").read())
    else:
        raw = play(model, args, device)
        with gzip.open(str(out_path) + ".probes.json.gz", "wt") as f:
            json.dump(raw, f)
    probes, stats = raw["probes"], raw["stats"]
    offline(model, probes, device)
    diffs = [abs(p["V0off"] - p["V0"]) for p in probes]
    res = {"pilot": args.pilot, "args": vars(args), "games": raw["games"], "game_errors": raw["game_errors"], "log": raw["log"],
           "seconds": raw["seconds"], "m_final": raw["m_final"], "device": device, "results": raw["results"], "stats": stats,
           "counts": counts(probes), "probes": len(probes)}
    lines = stats.get("lines", 0)
    res["checks"] = {"v0_max_abs_diff": round(max(diffs), 6) if diffs else None, "v0_ok_1e-3": bool(diffs) and max(diffs) < 1e-3,
                     "probes_with_obs": sum(1 for p in probes if p.get("obs")), "lineErrors": stats.get("lineErrors", 0),
                     "lineErrors_share": round(stats.get("lineErrors", 0) / max(lines, 1), 5),
                     "capped_share": round(stats.get("capped", 0) / max(lines, 1), 5), "lines": lines,
                     "unsearchable": stats.get("unsearchable", 0), "dropped_copies": stats.get("droppedCopies", 0),
                     "tiers": {k[5:]: v for k, v in stats.items() if k.startswith("tier_")}}
    npro = max(len(probes), 1)
    rows_per_line = stats.get("lineAsked", 0) / max(lines, 1)
    lines_per_probe = lines / npro
    mean_answers = float(np.mean([len(p["answers"]) for p in probes])) if probes else 0.0
    full_rows = 350 * mean_answers * 32 * rows_per_line
    res["sizing"] = {"lines_per_probe": round(lines_per_probe, 1), "rows_per_line": round(rows_per_line, 1),
                     "rows_per_probe": round(stats.get("lineAsked", 0) / npro, 1),
                     "decisions_asked_per_game": round(stats.get("asked", 0) / max(raw["games"], 1), 1),
                     "probes_per_game": round(len(probes) / max(raw["games"], 1), 3),
                     "full_run_rows_m32_est": round(full_rows), "assumed_rows_per_s": ROWS_PER_S,
                     "full_run_gpu_minutes_est": round(full_rows / ROWS_PER_S / 60, 1),
                     "measured_here": {"seconds": raw["seconds"], "device": device}}
    res["readouts"] = analyze(probes, stats, raw["games"])
    res["decisions"] = [{"stratum": p["stratum"], "trainer": p["trainer"], "type": p["type"], "message": p["message"], "step": p["step"],
                         "game": p["game"], "answers": len(p["answers"]), "valid": len(p["valid"]), "tiers": p["tiers"],
                         "V0": round(p["V0"], 4), "V0off": round(p["V0off"], 4), "capped": p["capped"]} for p in probes]
    out_path.write_text(json.dumps(clean(res), indent=1))
    print(json.dumps({"counts": res["counts"], "checks": res["checks"], "sizing": res["sizing"]}, indent=1), flush=True)
    for name, r in res["readouts"].items():
        if isinstance(r, dict):
            print(name, {k: r.get(k) for k in ("decisions", "decisions_A3", "R", "S", "G", "rho_V", "rho_A", "rho_pi", "rho_probe_primary", "nstar")}, flush=True)
            for v in r.get("verdict", []):
                print("   ", v, flush=True)
    print("control:", res["readouts"].get("control"), flush=True)
    print("wrote", out_path, flush=True)


if __name__ == "__main__":
    main()
