"""A repeating tournament of deck-owning agents (log #59): back to basics after the league (#54-58).

N agents, each with a network and an optimizer of its own (rl/league.py SeparatePilots: copies of the
--init-from checkpoint, nothing shared after that) and a deck of its own, all starting from different
random decks (rl/deckgen.py). Every round:
  1. tournament: every pair of agents plays --games games, each agent piloting its own deck; win-rate
     matrix, standings (mean win rate against the field), the meta game's equilibrium, cycles
  2. draft: every agent redrafts its own deck against the field (the other agents' decks of this round,
     equally weighted, each piloted by its agent), all at once. Climbs by the agent's own start-of-game
     value, with exploration: a swap adds a card the deck already plays or, half the time, any card weighted
     toward the cards played least (max((1 + training games it was in) ^ -0.5, --coverage-floor), so a card
     the others play is still proposed, at most 1/floor times less often); half the climbs start from a
     random kick of the current deck; each step is drawn from softmax(value / --draft-temp) instead of
     the best; one finalist is drawn at random. Search effort is --draft-calls value calls an agent, in
     climbs of at most --climb-steps calls (so several climbs, kicks and finalists fit in a round), each
     candidate read on --draft-deals deals spread over the opponents, the same at any N. A round may change
     up to --draft-budget cards (default 45,
     75% of the deck). Real games decide in two stages (as rl/league.py): the best finalist on
     --confirm-min games, re-tested against the current deck on fresh games, replaces it if it wins the
     re-test by --adopt-margin, or, with probability --explore-adopt, if it is within --explore-tol of it
     (exploration: a slightly worse deck is sometimes kept, to move between basins)
  3. train: --ppo-iters PPO iterations; each agent plays its own deck against the others (opponent drawn
     uniformly), and learns from its own side only; --agent-transitions per agent per iteration, so the
     budget per agent is the same at any N (collection aims at --collect-margin times the total, then each
     agent's transitions are subsampled to exactly the budget; an agent that still falls short is logged). Each agent's entropy coefficient rises (never below
     --ent) when its policy's entropy falls below --ent-target: play keeps exploring, slightly
     suboptimally, instead of collapsing
Nothing human enters training; archived lists and SimpleBot are labels and evaluation only (each
agent piloting its own deck against SimpleBot on the same deck, --eval-every rounds).

Run: .venv/Scripts/python -m rl.tournament --run runs/tourn-3 --agents 3 --init-from runs/pilot-v2/model_it00349.pt
"""
import argparse
import json
import math
import os
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from rl import limits
from rl.deckgen import Coverage, DeckGen
from rl.decks import Pool, archived_decks, overlap
from rl.gpu_matrix import GpuMatrix
from rl.league import SeparatePilots, deck_shape, deck_types, subset
from rl.nash import solve
from rl.psro import label_of
from rl.remote import RemotePool
from rl.rollouts import concat, read_rollout
from rl.search import changed, softmax_order
from rl.train import advantages, build_model, export_policy

ROOT = Path(__file__).resolve().parent.parent
# Cards in most archived lists (log #24 and the A5 ablations): evaluation only, never an input.
STAPLES = ("Professor Oak", "Double Colorless Energy", "Gust of Wind", "Computer Search", "Scyther", "Bill",
           "Item Finder", "PlusPower", "Energy Removal", "Super Energy Removal")


def cyclic_triads(P: np.ndarray, G: np.ndarray) -> tuple:
    """(cyclic, significant cyclic, total) triads of the 'beats' relation, a measure of intransitivity.
    A tie (P = 0.5) is no edge; a significant cycle has every edge more than 2 standard errors from 0.5."""
    n = len(P)
    s = np.sign(P - 0.5)
    se = np.sqrt(np.clip(P * (1 - P), 0.0625 / np.maximum(G, 1), None) / np.maximum(G, 1))
    sig = np.abs(P - 0.5) > 2 * se
    cyc = cyc_sig = tot = 0
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                tot += 1
                e = (s[i, j], s[j, k], s[k, i])
                if e[0] != 0 and e[0] == e[1] == e[2]:
                    cyc += 1
                    cyc_sig += bool(sig[i, j] and sig[j, k] and sig[k, i])
    return int(cyc), int(cyc_sig), int(tot)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--init-from", required=True, help="checkpoint every agent's network starts as")
    ap.add_argument("--agents", type=int, default=3)
    ap.add_argument("--pool", choices=["field", "full"], default="full")
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--games", type=int, default=32, help="tournament games per pair of agents")
    ap.add_argument("--init-dist", type=int, default=30, help="cards every starting deck differs from the others'")
    ap.add_argument("--niche", type=int, default=0, help="if > 0, cards a drafted deck must differ from the others'")
    ap.add_argument("--type-dist", type=int, default=20, help="decks closer than this count as one deck type (logs)")
    ap.add_argument("--draft-budget", type=int, default=45, help="cards a deck may change in one round (45 = 75%%)")
    ap.add_argument("--draft-calls", type=int, default=90, help="value calls per agent per round (search effort)")
    ap.add_argument("--climb-steps", type=int, default=15, help="value calls (steps) one climb may take")
    ap.add_argument("--draft-deals", type=int, default=16, help="deals per candidate, spread over the opponents")
    ap.add_argument("--draft-seconds", type=float, default=180, help="safety cap on one agent's drafting")
    ap.add_argument("--draft-candidates", type=int, default=12)
    ap.add_argument("--draft-temp", type=float, default=0.03, help="noise: climb steps drawn from softmax(value / T)")
    ap.add_argument("--explore-adopt", type=float, default=0.25,
                    help="probability of adopting a finalist that is not better but within --explore-tol on the re-test")
    ap.add_argument("--explore-tol", type=float, default=0.03)
    ap.add_argument("--p-kick", type=float, default=0.5, help="share of climbs that start from a random kick of the deck")
    ap.add_argument("--kick-min", type=int, default=8)
    ap.add_argument("--patience", type=int, default=3)
    ap.add_argument("--finalists", type=int, default=4, help="the best by value, plus one drawn at random")
    ap.add_argument("--confirm-games", type=int, default=16, help="games per opponent per finalist (at least)")
    ap.add_argument("--confirm-min", type=int, default=96, help="games per finalist in all, spread over the opponents")
    ap.add_argument("--adopt-margin", type=float, default=0.02)
    ap.add_argument("--p-flat", type=float, default=1.0, help="share of starting decks with the rules-only shape")
    ap.add_argument("--coverage-power", type=float, default=0.5)
    ap.add_argument("--coverage-floor", type=float, default=0.25, help="lowest card weight in exploratory swaps")
    ap.add_argument("--ppo-iters", type=int, default=8)
    ap.add_argument("--agent-transitions", type=int, default=8000, help="per agent per PPO iteration")
    ap.add_argument("--collect-margin", type=float, default=1.4,
                    help="collect this times the total budget, so agents with short games still reach theirs")
    ap.add_argument("--matches-per-agent", type=int, default=64)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--minibatch", type=int, default=4096)
    ap.add_argument("--micro-batch", type=int, default=1024)
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--clip", type=float, default=0.2)
    ap.add_argument("--vf", type=float, default=0.5)
    ap.add_argument("--ent", type=float, default=0.01, help="each agent's starting entropy coefficient")
    ap.add_argument("--ent-target", type=float, default=0.75, help="entropy each agent's policy is held near (0: fixed --ent)")
    ap.add_argument("--ent-rate", type=float, default=1.0, help="coefficient *= exp(rate x (target - entropy)) per iteration")
    ap.add_argument("--ent-min", type=float, default=0.01, help="never below the old fixed coefficient")
    ap.add_argument("--ent-max", type=float, default=0.05)
    ap.add_argument("--max-grad-norm", type=float, default=0.5)
    ap.add_argument("--deckout-win", type=float, default=1.0, help="1 = the plain game result (no shaping)")
    ap.add_argument("--gpu-pace", type=float, default=0.25)
    ap.add_argument("--gpu-load", type=float, default=0.7)
    ap.add_argument("--eval-every", type=int, default=5)
    ap.add_argument("--eval-games", type=int, default=200)
    ap.add_argument("--eval-workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args(argv)
    assert args.agents >= 2

    run = ROOT / args.run
    (run / "eval").mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    args.eval_workers = limits.cap_workers(args.eval_workers)
    limits.apply(device, args.workers)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    N = args.agents

    archived = archived_decks(Pool())                  # labels and evaluation only
    field = sorted({c for _, v in archived for c in Pool().names(v)})
    pool = Pool(restrict=field if args.pool == "field" else None)
    gen = DeckGen(pool)
    cov = Coverage(pool)
    staple_ids = {s: [c["id"] for c in pool.cards if c["name"] == s] for s in STAPLES}
    field_ids = np.zeros(pool.n, dtype=bool)          # the archived field's cards (labels only)
    for f in field:
        field_ids[pool.id[f]] = True

    rp = RemotePool(args.workers)
    rp.pace = args.gpu_pace
    info = rp.ask_all([{"cmd": "info"}] * args.workers)[0]
    init = torch.load(ROOT / args.init_from, map_location=device, weights_only=False)
    c0 = init["config"]

    def build(k):
        return build_model(SimpleNamespace(model="tokens", d=c0["d"], tok_layers=c0["layers"], heads=c0["heads"],
                                           count_features=c0.get("count_features", False),
                                           cross_layers=c0.get("cross_layers", 1), cand_self=c0.get("cand_self", 0),
                                           n_agents=k), info)
    pilots = SeparatePilots(build, N, init["model"], args.lr, device)
    models = {k: pilots.nets[k] for k in range(N)}
    targs = SimpleNamespace(**vars(args), model="tokens", amp=True)
    gm = GpuMatrix.attach(pilots.nets[0], rp, args.workers, device=device)

    start, it_total = 0, 0
    ckpt = run / "checkpoint.pt"
    if args.resume and ckpt.exists():
        st = torch.load(ckpt, map_location=device, weights_only=False)
        pilots.load(st)
        start, it_total = st["round"] + 1, st["ppo_iter"]
        agents = [{**a, "deck": pool.vector(a["deck"]), "initial": pool.vector(a["initial"])} for a in st["agents"]]
        cov.exposure = st["exposure"]
        rng.bit_generator.state = st["rng"]
    else:
        agents = []
        for k in range(N):                             # different random starting decks
            w = cov.weights(args.coverage_power)
            v = gen(rng, w, args.p_flat)
            for _ in range(200):
                if all(changed(v, a["deck"]) >= args.init_dist for a in agents):
                    break
                v = gen(rng, w, args.p_flat)
            agents.append({"id": k, "deck": v, "initial": v.copy(), "version": 0, "adoptions": 0, "explored": 0,
                           "ent": args.ent})
    (run / "config.json").write_text(json.dumps({**vars(args), "model_config": pilots.config(), "device": device},
                                                indent=1))
    log = open(run / "log.jsonl", "a")

    def explore_swap(v, w):
        """One copy out, one in, legal: half the time a card the deck already plays, else any card drawn
        with weight w (toward the cards played least)."""
        rem = np.nonzero(pool.removable(v))[0]
        x = v.copy()
        x[rng.choice(rem)] -= 1
        add = pool.addable(x)
        own = np.nonzero(add & (v > 0))[0]
        if len(own) and rng.random() < 0.5:
            x[rng.choice(own)] += 1
            return x
        ids = np.nonzero(add)[0]
        p = w[ids]
        x[ids[rng.choice(len(ids), p=p / p.sum())] if p.sum() > 0 else rng.choice(ids)] += 1
        return x

    def name(a):
        return f"a{a['id']}.v{a['version']}"

    def as_json(a, deck=None):
        return {"name": name(a), "cards": pool.names(a["deck"] if deck is None else deck)}

    def nearest(v):
        o = [overlap(v, x) for _, x in archived]
        k = int(np.argmax(o))
        return label_of(archived[k][0]), round(o[k], 3)

    def describe(a):
        v = a["deck"]
        return {"agent": a["id"], "version": a["version"], "adoptions": a["adoptions"], "explored": a["explored"],
                "ent_coef": round(a["ent"], 5), **deck_shape(pool, v),
                "drafted_share": round(changed(v, a["initial"]) / 60, 3), "nearest": nearest(v),
                "staples": [s for s, ids in staple_ids.items() if v[ids].sum() > 0],
                "field_share": round(float(v[field_ids & ~pool.basic_energy].sum()) / max(int(v[~pool.basic_energy].sum()), 1), 3),
                "cards": pool.names(v)}

    def improve(a, decks0, seed):
        """One round of drafting for agent a against the field `decks0` (every other agent's deck at the
        start of the round, piloted by its agent). Returns (log entry, the deck to adopt or None)."""
        t0 = time.time()
        cur = decks0[a["id"]]
        opp = [b["id"] for b in agents if b["id"] != a["id"]]
        n = len(opp)
        opp_json = [{"name": f"o{j}", "cards": pool.names(decks0[j])} for j in opp]
        budget = args.draft_budget

        def ok(c):
            return (pool.legal(c) and changed(c, cur) <= budget
                    and (args.niche <= 0 or all(changed(c, decks0[j]) >= args.niche for j in opp)))

        calls = [0]
        w_cov = np.maximum(cov.weights(args.coverage_power), args.coverage_floor)
        openings = max(2, round(args.draft_deals / n))

        def more():
            return calls[0] < args.draft_calls and time.time() - t0 < args.draft_seconds

        def value(cands):
            decks = opp_json + [{"name": f"c{k}", "cards": pool.names(c)} for k, c in enumerate(cands)]
            pairs = [(n + k, j) for k in range(len(cands)) for j in range(n)]
            calls[0] += 1
            v = gm.values(decks, pairs, openings, (seed * 7919 + calls[0]) % 1_000_003,
                          slots=[a["id"]] * len(pairs), models=models).reshape(len(cands), n)
            return 0.5 + 0.5 * v.mean(1)

        def mutate(x):
            k = 1 if rng.random() < 0.5 else int(rng.integers(2, 7))
            for _ in range(k):
                x = explore_swap(x, w_cov)
            return x

        finals, scored, climbs = [], 0, 0
        while more():
            climbs += 1
            x = cur.copy()
            if rng.random() < args.p_kick:             # noise: start somewhere else in the budget
                target = int(rng.integers(args.kick_min, max(args.kick_min + 1, budget - 4)))
                for _ in range(400):
                    if changed(x, cur) >= target:
                        break
                    y = explore_swap(x, w_cov)
                    if ok(y):
                        x = y
            best, stall, steps = None, 0, 0
            while stall < args.patience and steps < args.climb_steps and more():
                cands = []
                for _ in range(args.draft_candidates * 8):
                    c = mutate(x)
                    if ok(c):
                        cands.append(c)
                    if len(cands) == args.draft_candidates:
                        break
                if not cands:
                    break
                s = value([x] + cands)
                scored += len(cands)
                for q, d in enumerate([x] + cands):
                    if best is None or s[q] > best[1]:
                        best = (d, float(s[q]))
                pick = softmax_order(s, args.draft_temp, rng)[0]     # noise: a draw, not the best
                if pick == 0:
                    stall += 1
                else:
                    x, stall = cands[pick - 1], 0
                steps += 1
            if best is not None and changed(best[0], cur) > 0:
                finals.append(best)
        finals.sort(key=lambda t: -t[1])
        chosen = []
        for x, sx in finals:
            if all(changed(x, y) >= 2 for y, _ in chosen):
                chosen.append((x, sx))
            if len(chosen) == args.finalists - 1:
                break
        rest = [f for f in finals if all(changed(f[0], y) >= 2 for y, _ in chosen)]
        if rest:                                        # noise: one finalist drawn at random
            chosen.append(rest[int(rng.integers(len(rest)))])
        out = {"agent": a["id"], "climbs": climbs, "scored": scored, "value_calls": calls[0],
               "openings_per_opponent": openings, "finalists": len(chosen), "adopted": False}
        new = None
        if chosen:
            per_opp = max(args.confirm_games, -(-args.confirm_min // n))
            per_opp += per_opp % 2

            def real_games(decks_list, m, seed_):
                decks = opp_json + [{"name": f"d{k}", "cards": pool.names(d)} for k, d in enumerate(decks_list)]
                pairs = [(n + k, j) for k in range(m) for j in range(n)]
                slots = opp + [a["id"]] * m
                W, G, _ = gm.play(decks, per_opp, seed_ % 1_000_003, pairs=pairs, slots=slots, models=models)
                return np.array([np.mean([W[n + k, j] / max(G[n + k, j], 1) for j in range(n)]) for k in range(m)])

            real = real_games([cur] + [x for x, _ in chosen], 1 + len(chosen), seed * 104729 + 17)
            best = 1 + int(np.argmax(real[1:]))
            out.update({"games_per_opponent": per_opp, "current_real": round(float(real[0]), 4),
                        "best_real": round(float(real[best]), 4), "best_value": round(chosen[best - 1][1], 4),
                        "changed": int(changed(chosen[best - 1][0], cur)),
                        "best_was_random_pick": bool(best == len(chosen) and rest)})
            if real[best] >= real[0] - args.explore_tol:
                recheck = real_games([cur, chosen[best - 1][0]], 2, seed * 104729 + 7919)
                out.update({"recheck_current": round(float(recheck[0]), 4), "recheck_best": round(float(recheck[1]), 4)})
                if recheck[1] > recheck[0] + args.adopt_margin:
                    new = chosen[best - 1][0]
                    out["adopted"] = True
                elif recheck[1] >= recheck[0] - args.explore_tol and rng.random() < args.explore_adopt:
                    new = chosen[best - 1][0]                 # exploration: a near-equal deck, kept anyway
                    out["adopted"], out["exploratory"] = True, True
        out["seconds"] = round(time.time() - t0, 1)
        return out, new

    try:
        for rnd in range(start, args.rounds + 1):
            t0 = time.time()
            pilots.eval()
            row = {"round": rnd, "ppo_iter": it_total, "agents_n": N}
            # 1. tournament
            decks = [as_json(a) for a in agents]
            pairs = [(i, j) for j in range(N) for i in range(j)]   # pairs shared across N get the same deals
            W, G, S = gm.play(decks, args.games, args.seed * 1000 + rnd, pairs=pairs, slots=list(range(N)),
                              models=models)
            P = W / np.maximum(G, 1)
            sigma, _ = solve(P)
            standings = (P.sum(1) - 0.5) / (N - 1)
            support = [int(i) for i in np.argsort(-sigma) if sigma[i] > 1e-4]
            cyc, cyc_sig, tri = cyclic_triads(P, G)
            dist = [changed(agents[i]["deck"], agents[j]["deck"]) for i in range(N) for j in range(i + 1, N)]
            ent = float(-(sigma[sigma > 0] * np.log(sigma[sigma > 0])).sum())
            row["tournament"] = {"P": np.round(P, 3).tolist(), "sigma": np.round(sigma, 4).tolist(),
                                 "standings": np.round(standings, 4).tolist(), "support": support,
                                 "support_frac": round(len(support) / N, 4), "nash_entropy": round(ent, 4),
                                 "effective_support_frac": round(math.exp(ent) / N, 4),
                                 "cyclic_triads": [cyc, cyc_sig, tri],
                                 "cyclic_frac": round(cyc / tri, 4) if tri else None, "games": gm.last}
            row["deck_types"] = deck_types([a["deck"] for a in agents], args.type_dist)
            row["deck_types_frac"] = round(row["deck_types"] / N, 4)
            row["deck_types_in_support"] = deck_types([agents[i]["deck"] for i in support], args.type_dist)
            row["deck_distance"] = {"min": int(min(dist)), "mean": round(float(np.mean(dist)), 1)}
            row["decks"] = [describe(a) for a in agents]
            row["coverage"] = cov.summary([a["deck"] for a in agents], [agents[i]["deck"] for i in support])
            row["seconds"] = {"tournament": round(time.time() - t0, 1)}
            print(f"round {rnd}: {N} agents, {row['deck_types']} deck types ({row['deck_types_in_support']} in support), "
                  f"distance min {row['deck_distance']['min']} mean {row['deck_distance']['mean']}, cycles {cyc}/{tri} ({cyc_sig} clear); "
                  "standings " + " ".join(f"a{k} {standings[k]:.2f}" for k in range(N)) + "; support " +
                  " ".join(f"a{i} {sigma[i]:.2f}" for i in support), flush=True)
            if rnd == args.rounds:
                log.write(json.dumps(row) + "\n")
                break

            # 2. draft: everyone at once against this round's decks
            t1 = time.time()
            decks0 = {a["id"]: a["deck"].copy() for a in agents}
            row["draft"], adopt = [], {}
            for a in agents:
                d, new = improve(a, decks0, args.seed * 100 + rnd * 10 + a["id"])
                row["draft"].append(d)
                if new is not None:
                    adopt[a["id"]] = (new, bool(d.get("exploratory")))
            for a in agents:
                if a["id"] in adopt:
                    new, explored = adopt[a["id"]]
                    a["deck"], a["version"], a["adoptions"] = new, a["version"] + 1, a["adoptions"] + 1
                    a["explored"] += explored
            row["seconds"]["draft"] = round(time.time() - t1, 1)
            print("  draft: " + "; ".join(
                f"a{d['agent']} {('EXPLORED' if d.get('exploratory') else 'ADOPTED') if d['adopted'] else 'kept'} "
                f"{d.get('current_real', '-')} -> {d.get('best_real', '-')}"
                + (f" (re-test {d['recheck_current']} -> {d['recheck_best']}, {d['changed']} cards)" if "recheck_best" in d else "")
                for d in row["draft"]), flush=True)

            # 3. train: each agent on its own deck against the others
            t2 = time.time()
            ajson = {a["id"]: as_json(a) for a in agents}
            per_worker = math.ceil(args.collect_margin * N * args.agent_transitions / args.workers)
            conc = max(8, min(args.concurrency, per_worker // 140))   # games in flight overshoot the quota
            train_rows = []
            for _ in range(args.ppo_iters):
                ms = []
                for a in agents:
                    for _ in range(args.matches_per_agent):
                        j = int(rng.choice([b["id"] for b in agents if b["id"] != a["id"]]))
                        ms.append({"a": {"deck": ajson[a["id"]], "slot": a["id"], "record": True},
                                   "b": {"deck": ajson[j], "slot": j, "record": False}})
                ti = time.time()
                msgs = [{"cmd": "league", "transitions": per_worker, "concurrency": conc,
                         "deckoutWin": args.deckout_win, "seed": (args.seed * 1_000_003 + it_total * 1009 + w) % 2_000_000_000,
                         "matches": ms, "out": str(run / f"rollout_w{w}.bin")} for w in range(args.workers)]
                replies = rp.collect(msgs, models, device)
                tc = time.time() - ti
                batch = concat([read_rollout(r["out"]) for r in replies])
                assert "slot" in batch and int(batch["slot"].min()) >= 0 and int(batch["slot"].max()) < N
                adv, ret = advantages(batch, args.gamma, args.lam)
                batch["adv"], batch["ret"] = adv, ret
                collected = {k: int((batch["slot"] == k).sum()) for k in range(N)}
                keep = []                                # the same budget for every agent, at any N
                for k in range(N):
                    ix = np.nonzero(batch["slot"] == k)[0]
                    if len(ix) > args.agent_transitions:
                        ix = rng.choice(ix, args.agent_transitions, replace=False)
                    keep.append(ix)
                batch = subset(batch, np.sort(np.concatenate(keep)))
                stats, per_agent = pilots.update(batch, targs, ent={a["id"]: a["ent"] for a in agents})
                if args.ent_target > 0:                  # hold each agent's play near the entropy target
                    for a in agents:
                        if a["id"] in per_agent:
                            h = per_agent[a["id"]]["entropy"]
                            step = float(np.clip(math.exp(args.ent_rate * (args.ent_target - h)), 0.8, 1.25))
                            a["ent"] = float(np.clip(a["ent"] * step, args.ent_min, args.ent_max))
                games = [g for r in replies for g in r["results"]]
                cards_of = {d["name"]: d["cards"] for d in ajson.values()}
                cov.add_games([cards_of[x] for g in games for x in (g.get("decks") or []) if x in cards_of])
                cut = sum(1 for g in games if g.get("ending") is None and g["winner"] not in (1, 2))
                tr = {"ppo_iter": it_total, "transitions": int(len(batch["action"])), "games": len(games), "cut_off": cut,
                      "steps_per_game": round(float(np.mean([g["steps"] for g in games])), 1) if games else 0,
                      "errors": sum(1 for g in games if g.get("error")),
                      "endings": {e: sum(1 for g in games if (g.get("ending") or "none") == e)
                                  for e in {g.get("ending") or "none" for g in games}},
                      "agent_transitions": {int(k): int((batch["slot"] == k).sum()) for k in range(N)},
                      "agent_collected": collected, "concurrency": conc,
                      "agent_stats": {str(k): {q: round(v, 5) for q, v in s_.items()} for k, s_ in per_agent.items()},
                      "ent_coef": {str(a["id"]): round(a["ent"], 5) for a in agents},
                      "collect_s": round(tc, 1), **{k: round(v, 5) for k, v in stats.items()}}
                short = {k: v for k, v in collected.items() if v < args.agent_transitions}
                if short:
                    tr["short_of_budget"] = short
                    print(f"  WARNING: agents short of the {args.agent_transitions}-transition budget: {short}", flush=True)
                train_rows.append(tr)
                print(f"  ppo {it_total}: games {tr['games']} len {tr['steps_per_game']} cut {cut} ent {stats['entropy']:.3f} "
                      f"kl {stats['kl']:.4f} endings {tr['endings']}", flush=True)
                if games and cut > 0.02 * len(games):
                    print(f"  WARNING: {cut} of {len(games)} games cut off at the step cap (a free cycle?)", flush=True)
                it_total += 1
            row["train"] = train_rows
            row["seconds"]["train"] = round(time.time() - t2, 1)

            if args.eval_every and (rnd + 1) % args.eval_every == 0:     # evaluation only
                row["eval_simplebot_own_deck"] = {}
                for a in agents:
                    path = run / "eval" / f"agent{a['id']}.onnx"
                    spec = export_policy(pilots.nets[a["id"]], path, "tokens")
                    pilots.nets[a["id"]].to(device)
                    dfile = run / "eval" / f"deck{a['id']}.json"
                    dfile.write_text(json.dumps([as_json(a)]))
                    out = run / "eval" / f"eval{a['id']}.json"
                    subprocess.run(["node", str(ROOT / "env/tools/evaluate.js"), "--x", spec, "--y", "simplebot",
                                    "--decks-file", str(dfile), "--mirror", "--games", str(args.eval_games),
                                    "--workers", str(args.eval_workers), "--concurrency", "8",
                                    "--seed", str(args.seed * 7 + rnd), "--json", str(out)],
                                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
                    r = json.load(open(out))
                    row["eval_simplebot_own_deck"][str(a["id"])] = {"all": round(r["all"]["xWinRate"], 4),
                                                                    "ci95": round(r["all"]["ci95"], 4)}
                print("  eval, each agent and SimpleBot on the agent's deck: " + " ".join(
                    f"a{k} {v['all']:.3f}" for k, v in row["eval_simplebot_own_deck"].items()), flush=True)

            log.write(json.dumps(row) + "\n")
            log.flush()
            if args.eval_every and (rnd + 1) % args.eval_every == 0:     # every agent's network, now and then
                torch.save({"nets": pilots.state()["nets"], "config": pilots.config(),
                            "decks": [pool.names(a["deck"]) for a in agents]}, run / f"pilots_r{rnd:03d}.pt")
            tmp = ckpt.with_suffix(".tmp")
            torch.save({**pilots.state(), "round": rnd, "ppo_iter": it_total,
                        "agents": [{**a, "deck": pool.names(a["deck"]), "initial": pool.names(a["initial"])} for a in agents],
                        "exposure": cov.exposure, "rng": rng.bit_generator.state, "config": pilots.config()}, tmp)
            os.replace(tmp, ckpt)
            for f in run.glob("rollout_w*.bin"):
                f.unlink(missing_ok=True)
    finally:
        rp.close()
        log.close()


if __name__ == "__main__":
    main()
