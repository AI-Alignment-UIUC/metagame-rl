"""League of deck-owning agents (log #53): the metagame from a population of agents that each draft
and pilot their own deck, instead of one pilot for every deck (rl/coevolve.py, log #52, collapsed to
one deck type: one pilot co-adapts to the leading deck, and new deck types are judged raw).

One agent-conditioned network (rl/token_model.py n_agents; each agent has an embedding and its own
value head, all starting as the --init-from checkpoint) holds every live agent:
  main agents       own a deck lineage each; improve it against the league's equilibrium mixture
  exploiters        own a lineage each; improve it against the main agents' strategies only. One that
                    beats them (>= --exploit-win) is frozen into the league and restarts from a fresh
                    random deck; one that stalls restarts without being frozen (AlphaStar's exploiters)
  generalist        owns no deck: plays any deck (league and exploration decks) in both seats, for the
                    "play any deck" goal and as a common pilot; it is what the SimpleBot check plays

A strategy of the meta game is a deck with its pilot: each live specialist's current deck under the
live network, and frozen strategies (a deck, an agent, a snapshot of the network). Each round:
  1. measure every pair that involves a live strategy (frozen pairs are cached), each side piloted by
     its own agent; solve the meta game -> sigma. Exploiters that beat the mains are frozen and reset;
     every --freeze-every rounds the mains' strategies are frozen too; the league keeps at most
     --max-history frozen strategies (out of the support, oldest first, leave)
  2. draft: each specialist hill-climbs its own deck by its own value against its opponents (at most
     --edit-budget cards a round, at least --niche cards from every other specialist's deck, so
     lineages stay distinct), then real games decide: the best finalist replaces the deck only if it
     beats the current deck against those opponents by --adopt-margin
  3. pilot: --ppo-iters PPO iterations; every iteration each live agent gets the same number of
     matches (mains vs sigma, exploiters vs the mains' part of sigma, the generalist on any decks), and
     only that agent's side of its own matches is recorded (with its agent id), so the leading deck's
     agent doesn't get extra practice from being everyone's opponent
Nothing human enters training; the archived lists and SimpleBot are only labels and evaluation.

Run: .venv/Scripts/python -m rl.league --run runs/league-1 --init-from runs/pilot-v2/model_it00349.pt
"""
import argparse
import json
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from rl import limits
from rl.deckgen import Coverage, DeckGen
from rl.decks import Pool, archived_decks, overlap
from rl.gpu_matrix import GpuMatrix
from rl.nash import solve
from rl.psro import label_of
from rl.remote import AgentView, RemotePool
from rl.rollouts import concat, read_rollout
from rl.search import changed, random_swap
from rl.train import advantages, build_model, evaluate, export_policy, model_inputs, ppo_update

ROOT = Path(__file__).resolve().parent.parent
FROZEN_SLOT = 1000            # frozen strategy i is model slot FROZEN_SLOT + i; live agent k is slot k


def deck_shape(pool, v):
    return {"pokemon": int(v[[c["id"] for c in pool.cards if c["superType"] == 1]].sum()),
            "trainer": int(v[[c["id"] for c in pool.cards if c["superType"] == 2]].sum()),
            "basic_energy": int(v[pool.basic_energy].sum()),
            "special_energy": int(v[[c["id"] for c in pool.cards if c["superType"] == 3 and c["energyType"] != 0]].sum())}


def deck_types(decks, dist):
    """How many decks remain after merging any two within `dist` cards (greedy, in the given order)."""
    reps = []
    for v in decks:
        if all(changed(v, r) >= dist for r in reps):
            reps.append(v)
    return len(reps)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--init-from", required=True, help="checkpoint every agent starts from (plain or league)")
    ap.add_argument("--pool", choices=["field", "full"], default="full")
    ap.add_argument("--rounds", type=int, default=30)
    ap.add_argument("--mains", type=int, default=3)
    ap.add_argument("--exploiters", type=int, default=2)
    ap.add_argument("--games", type=int, default=24, help="games per pair when measuring the league")
    ap.add_argument("--niche", type=int, default=20, help="cards every specialist's deck differs from every other's")
    ap.add_argument("--type-dist", type=int, default=20, help="decks closer than this count as one deck type (logs)")
    ap.add_argument("--edit-budget", type=int, default=12, help="cards a main agent's deck may change per round")
    ap.add_argument("--exploit-budget", type=int, default=24, help="the same for an exploiter")
    ap.add_argument("--draft-seconds", type=float, default=30, help="value climbing per specialist per round")
    ap.add_argument("--draft-candidates", type=int, default=12)
    ap.add_argument("--openings", type=int, default=8)
    ap.add_argument("--max-opponents", type=int, default=6)
    ap.add_argument("--finalists", type=int, default=4)
    ap.add_argument("--confirm-games", type=int, default=16, help="games per opponent per finalist")
    ap.add_argument("--adopt-margin", type=float, default=0.02)
    ap.add_argument("--exploit-win", type=float, default=0.6)
    ap.add_argument("--exploit-patience", type=int, default=4, help="rounds without a better deck before a reset")
    ap.add_argument("--exploit-max-rounds", type=int, default=8)
    ap.add_argument("--freeze-every", type=int, default=3)
    ap.add_argument("--max-history", type=int, default=12)
    ap.add_argument("--explore", type=int, default=64, help="fresh exploration decks per round (generalist games)")
    ap.add_argument("--p-flat", type=float, default=0.5)
    ap.add_argument("--coverage-power", type=float, default=0.5)
    ap.add_argument("--ppo-iters", type=int, default=10)
    ap.add_argument("--matches", type=int, default=384, help="matches drawn per PPO iteration")
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--transitions", type=int, default=4096)
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--minibatch", type=int, default=4096)
    ap.add_argument("--micro-batch", type=int, default=1024)
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--clip", type=float, default=0.2)
    ap.add_argument("--vf", type=float, default=0.5)
    ap.add_argument("--ent", type=float, default=0.01)
    ap.add_argument("--max-grad-norm", type=float, default=0.5)
    ap.add_argument("--deckout-win", type=float, default=1.0, help="1 = the plain game result (no shaping)")
    ap.add_argument("--gpu-pace", type=float, default=0.25, help="inference rests this x its GPU time per batch")
    ap.add_argument("--gpu-load", type=float, default=0.7, help="PPO update: share of time the GPU may be busy")
    ap.add_argument("--eval-every", type=int, default=5)
    ap.add_argument("--eval-games", type=int, default=400)
    ap.add_argument("--eval-workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args(argv)

    run = ROOT / args.run
    (run / "snapshots").mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    args.eval_workers = limits.cap_workers(args.eval_workers)
    limits.apply(device, args.workers)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)

    archived = archived_decks(Pool())                  # labels and evaluation only
    field = sorted({c for _, v in archived for c in Pool().names(v)})
    pool = Pool(restrict=field if args.pool == "field" else None)
    gen = DeckGen(pool)
    cov = Coverage(pool)

    rp = RemotePool(args.workers)
    rp.pace = args.gpu_pace
    info = rp.ask_all([{"cmd": "info"}] * args.workers)[0]
    init = torch.load(ROOT / args.init_from, map_location=device, weights_only=False)
    c0 = init["config"]
    n_agents = args.mains + args.exploiters + 1
    G = n_agents - 1                                    # the generalist's agent id
    margs = SimpleNamespace(model="tokens", d=c0["d"], tok_layers=c0["layers"], heads=c0["heads"],
                            count_features=c0.get("count_features", False), cross_layers=c0.get("cross_layers", 1),
                            cand_self=c0.get("cand_self", 0), n_agents=n_agents)
    live = build_model(margs, info).to(device)
    missing, unexpected = live.load_state_dict(init["model"], strict=False)
    assert not unexpected, f"checkpoint has weights this network lacks: {unexpected[:4]}"
    assert all(k.startswith(("agent_emb.", "value_heads.")) for k in missing), f"missing weights: {missing[:4]}"
    if missing:
        live.init_agents_from_base()                   # a plain checkpoint: every agent starts as it
    opt = torch.optim.Adam(live.parameters(), lr=args.lr, eps=1e-5)
    targs = SimpleNamespace(**vars(args), model="tokens", amp=True)
    gm = GpuMatrix.attach(live, rp, args.workers, device=device)

    agents = [{"id": k, "role": "main", "lineage": f"m{k}", "version": 0, "born": 0, "stall": 0, "resets": 0}
              for k in range(args.mains)]
    agents += [{"id": args.mains + k, "role": "exploiter", "lineage": f"e{k}.0", "version": 0, "born": 0, "stall": 0,
                "resets": 0} for k in range(args.exploiters)]
    history, cache, snap_nets = [], {}, {}
    start, it_total = 0, 0
    ckpt = run / "checkpoint.pt"

    def snapshot_net(key):
        if key not in snap_nets:
            path = run / "snapshots" / f"{key}.pt"
            net = build_model(margs, info).to(device)
            if path.exists():
                net.load_state_dict(torch.load(path, map_location=device, weights_only=False)["model"])
            else:
                net.load_state_dict(live.state_dict())
                torch.save({"model": net.state_dict(), "config": net.config()}, path)
            snap_nets[key] = net.eval()
        return snap_nets[key]

    def fresh_deck(avoid):
        w = cov.weights(args.coverage_power)
        v = gen(rng, w, args.p_flat)
        for _ in range(200):
            if all(changed(v, o) >= args.niche for o in avoid):
                break
            v = gen(rng, w, args.p_flat)
        return v

    if args.resume and ckpt.exists():
        st = torch.load(ckpt, map_location=device, weights_only=False)
        live.load_state_dict(st["model"])
        opt.load_state_dict(st["opt"])
        start, it_total = st["round"] + 1, st["ppo_iter"]
        agents = st["agents"]
        for a in agents:
            a["deck"] = pool.vector(a["deck"])
        history = [{**h, "deck": pool.vector(h["deck"])} for h in st["history"]]
        cache = {tuple(k): tuple(v) for k, v in st["cache"]}
        cov.exposure = st["exposure"]
        rng.bit_generator.state = st["rng"]
        for h in history:
            snapshot_net(h["net"])
    else:
        for a in agents:
            a["deck"] = fresh_deck([b["deck"] for b in agents if "deck" in b])
    (run / "config.json").write_text(json.dumps({**vars(args), "n_agents": n_agents, "model_config": live.config(),
                                                 "device": device}, indent=1))
    log = open(run / "log.jsonl", "a")

    def nearest(v):
        o = [overlap(v, a) for _, a in archived]
        k = int(np.argmax(o))
        return label_of(archived[k][0]), round(o[k], 3)

    def live_name(a, rnd):
        return f"{a['lineage']}.v{a['version']}@r{rnd}"

    def strategies(rnd):
        """The meta game's strategies: live specialists (current deck, live network) then frozen ones."""
        out = [{"name": live_name(a, rnd), "deck": a["deck"], "agent": a["id"], "role": a["role"], "live": True,
                "slot": a["id"]} for a in agents]
        out += [{**h, "live": False, "slot": FROZEN_SLOT + i} for i, h in enumerate(history)]
        return out

    def model_table():
        models = {k: AgentView(live, k) for k in range(n_agents)}
        for i, h in enumerate(history):
            models[FROZEN_SLOT + i] = AgentView(snapshot_net(h["net"]), h["agent"])
        return models

    def as_json(s):
        return {"name": s["name"], "cards": pool.names(s["deck"])}

    def freeze(s, rnd, why):
        key = f"r{rnd:03d}"
        snapshot_net(key)
        history.append({"name": s["name"], "deck": s["deck"].copy(), "agent": s["agent"], "role": s["role"],
                        "net": key, "origin": why, "born": rnd})

    def reset(a, rnd):
        a["resets"] += 1
        a["lineage"] = f"e{a['id'] - args.mains}.{a['resets']}"
        a["version"], a["born"], a["stall"] = 0, rnd, 0
        a["deck"] = fresh_deck([b["deck"] for b in agents if b is not a])
        live.copy_agent(G, a["id"])                    # a fresh pilot: the generalist's

    def improve(a, opps, w, models, seed):
        """One round of drafting for specialist a: climb its deck by its own value against opponents
        `opps` (strategies, weighted w), then real games decide whether the deck changes."""
        t0 = time.time()
        cur = a["deck"]
        budget = args.edit_budget if a["role"] == "main" else args.exploit_budget
        others = [b["deck"] for b in agents if b is not a]
        n = len(opps)
        opp_json = [as_json(s) for s in opps]

        def ok(c):
            return (pool.legal(c) and changed(c, cur) <= budget
                    and all(changed(c, o) >= args.niche for o in others))

        calls = [0]

        def value(cands):
            decks = opp_json + [{"name": f"c{k}", "cards": pool.names(c)} for k, c in enumerate(cands)]
            pairs = [(n + k, j) for k in range(len(cands)) for j in range(n)]
            calls[0] += 1
            v = gm.values(decks, pairs, args.openings, (seed * 7919 + calls[0]) % 1_000_003,
                          slots=[a["id"]] * len(pairs), models=models).reshape(len(cands), n)
            return 0.5 + 0.5 * (v * w[None, :]).sum(1)

        def mutate(x):
            k = 1 if rng.random() < 0.6 else int(rng.integers(2, 5))
            for _ in range(k):
                x = random_swap(pool, x, rng)
            return x

        finals, scored, climbs = [], 0, 0
        while time.time() - t0 < args.draft_seconds:
            x, sx, stall, steps = cur.copy(), None, 0, 0
            climbs += 1
            while stall < 2 and steps < 40 and time.time() - t0 < args.draft_seconds:
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
                sx = float(s[0])
                b = int(np.argmax(s[1:]))
                if s[1 + b] > s[0]:
                    x, sx, stall = cands[b], float(s[1 + b]), 0
                else:
                    stall += 1
                steps += 1
            if sx is not None and changed(x, cur) > 0:
                finals.append((x, sx))
        finals.sort(key=lambda t: -t[1])
        chosen = []
        for x, sx in finals:
            if all(changed(x, y) >= 2 for y, _ in chosen):
                chosen.append((x, sx))
            if len(chosen) == args.finalists:
                break
        out = {"agent": a["id"], "role": a["role"], "lineage": a["lineage"], "climbs": climbs, "scored": scored,
               "finalists": len(chosen), "adopted": False}
        if chosen:
            decks = opp_json + [{"name": "cur", "cards": pool.names(cur)}] + \
                [{"name": f"f{k}", "cards": pool.names(x)} for k, (x, _) in enumerate(chosen)]
            m = 1 + len(chosen)
            pairs = [(n + k, j) for k in range(m) for j in range(n)]
            slots = [s["slot"] for s in opps] + [a["id"]] * m
            W, Gm, _ = gm.play(decks, args.confirm_games, (seed * 104729 + 17) % 1_000_003, pairs=pairs,
                               slots=slots, models=models)
            real = np.array([sum(w[j] * W[n + k, j] / max(Gm[n + k, j], 1) for j in range(n)) for k in range(m)])
            best = 1 + int(np.argmax(real[1:]))
            out.update({"current_real": round(float(real[0]), 4), "best_real": round(float(real[best]), 4),
                        "best_value": round(chosen[best - 1][1], 4), "changed": int(changed(chosen[best - 1][0], cur))})
            if real[best] > real[0] + args.adopt_margin:
                a["deck"] = chosen[best - 1][0]
                a["version"] += 1
                a["stall"] = 0
                out["adopted"] = True
        if not out["adopted"]:
            a["stall"] += 1
        out["seconds"] = round(time.time() - t0, 1)
        return out

    try:
        for rnd in range(start, args.rounds + 1):
            t0 = time.time()
            live.eval()
            row = {"round": rnd, "ppo_iter": it_total}
            # 1. measure, solve, freeze, reset, trim
            S = strategies(rnd)
            models = model_table()
            n = len(S)
            names = [s["name"] for s in S]
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)
                     if S[i]["live"] or S[j]["live"] or (names[i], names[j]) not in cache]
            W, Gm, _ = gm.play([as_json(s) for s in S], args.games, args.seed * 1000 + rnd, pairs=pairs,
                               slots=[s["slot"] for s in S], models=models)
            played = set(pairs)
            for i in range(n):
                for j in range(i + 1, n):
                    if (i, j) not in played:
                        wi, g = cache[(names[i], names[j])]
                        W[i, j], W[j, i], Gm[i, j], Gm[j, i] = wi, g - wi, g, g
            P = W / np.maximum(Gm, 1)
            sigma, _ = solve(P)
            row["matrix"] = {**gm.last, "pairs_played": len(pairs), "strategies": n}
            events = []
            mains_mask = np.array([s["role"] == "main" for s in S])
            for a in agents:
                if a["role"] != "exploiter":
                    continue
                i = next(k for k, s in enumerate(S) if s["live"] and s["agent"] == a["id"])
                wt = sigma * mains_mask
                if wt.sum() <= 1e-9:
                    wt = (mains_mask & np.array([s["live"] for s in S])).astype(float)
                wr = float(P[i] @ (wt / wt.sum()))
                ev = {"agent": a["id"], "lineage": a["lineage"], "vs_mains": round(wr, 4)}
                if wr >= args.exploit_win:
                    freeze(S[i], rnd, f"exploiter {a['lineage']} beat the mains {wr:.3f}")
                    reset(a, rnd)
                    events.append({**ev, "event": "success: frozen and reset"})
                elif a["stall"] >= args.exploit_patience or rnd - a["born"] >= args.exploit_max_rounds:
                    reset(a, rnd)
                    events.append({**ev, "event": "stalled: reset"})
            if rnd > 0 and rnd % args.freeze_every == 0:
                for k, s in enumerate(S):
                    if s["live"] and s["role"] == "main":
                        freeze(s, rnd, "main snapshot")
                        events.append({"agent": s["agent"], "event": f"frozen {s['name']}"})
            frozen = {h["name"] for h in history}
            for i in range(n):
                for j in range(i + 1, n):
                    if names[i] in frozen and names[j] in frozen:
                        cache[(names[i], names[j])] = (float(W[i, j]), float(Gm[i, j]))
                        cache[(names[j], names[i])] = (float(W[j, i]), float(Gm[i, j]))
            weight = dict(zip(names, sigma))
            while len(history) > args.max_history:
                old = [k for k, h in enumerate(history) if h["born"] < rnd]
                zero = [k for k in old if weight.get(history[k]["name"], 0.0) <= 1e-4]
                k = zero[0] if zero else min(old or range(len(history)), key=lambda q: weight.get(history[q]["name"], 0.0))
                events.append({"event": f"retired {history[k]['name']}"})
                history.pop(k)
            for key in [k for k in snap_nets if k not in {h["net"] for h in history}]:
                del snap_nets[key]
            support = [(i, float(sigma[i])) for i in np.argsort(-sigma) if sigma[i] > 1e-4]
            row["support"] = [{"name": names[i], "weight": round(wt, 4), "agent": S[i]["agent"], "role": S[i]["role"],
                               "live": S[i]["live"], **deck_shape(pool, S[i]["deck"]), "nearest": nearest(S[i]["deck"])}
                              for i, wt in support]
            row["deck_types_in_support"] = deck_types([S[i]["deck"] for i, _ in support], args.type_dist)
            row["live"] = [{"name": names[i], "agent": S[i]["agent"], "role": S[i]["role"], "weight": round(float(sigma[i]), 4),
                            **deck_shape(pool, S[i]["deck"])} for i in range(n) if S[i]["live"]]
            row["events"] = events
            row["coverage"] = cov.summary([a["deck"] for a in agents] + [h["deck"] for h in history],
                                          [S[i]["deck"] for i, _ in support])
            row["seconds"] = {"measure": round(time.time() - t0, 1)}
            print(f"round {rnd}: {n} strategies, {row['deck_types_in_support']} deck types in support: " + ", ".join(
                f"{names[i]} {wt:.2f}" for i, wt in support[:6]) + (f"; events {events}" if events else ""), flush=True)
            if rnd == args.rounds:
                log.write(json.dumps(row) + "\n")
                break

            # 2. draft: each specialist improves its own lineage
            t1 = time.time()
            row["draft"] = []
            for a in agents:
                if a["role"] == "main":
                    mask = np.ones(n, bool)
                else:
                    mask = mains_mask.copy()
                wt = sigma * mask
                if wt.sum() <= 1e-9:
                    wt = mask.astype(float)
                top = [i for i in np.argsort(-wt) if wt[i] > 1e-6][:args.max_opponents]
                ww = wt[top] / wt[top].sum()
                row["draft"].append(improve(a, [S[i] for i in top], ww, models, args.seed * 100 + rnd * 10 + a["id"]))
            row["seconds"]["draft"] = round(time.time() - t1, 1)
            print("  draft: " + "; ".join(f"{d['lineage']} {'ADOPTED' if d['adopted'] else 'kept'} "
                                          f"{d.get('current_real', '-')} -> {d.get('best_real', '-')}" for d in row["draft"]),
                  flush=True)

            # 3. pilot: PPO on league matches
            t2 = time.time()
            S2 = strategies(rnd)                         # current decks; frozen ones as they are now
            models = model_table()
            w_of = {s["name"]: weight.get(s["name"], 0.0) for s in S2}
            for s in S2:                                  # live entries keep their agent's weight
                if s["live"]:
                    w_of[s["name"]] = float(sum(sigma[i] for i in range(n) if S[i]["live"] and S[i]["agent"] == s["agent"]))
            wall = np.array([w_of[s["name"]] for s in S2]) + 1e-9
            wmain = wall * np.array([s["role"] == "main" for s in S2])
            if wmain.sum() <= 1e-6:
                wmain = np.array([1.0 if (s["role"] == "main" and s["live"]) else 0.0 for s in S2])
            explore = [{"name": f"x{rnd}-{k}", "cards": pool.names(fresh_deck([]))} for k in range(args.explore)]
            s_json = [as_json(s) for s in S2]
            general_pick = lambda: (s_json[int(rng.choice(len(S2), p=wall / wall.sum()))] if rng.random() < 0.5 else
                                    s_json[int(rng.integers(len(S2)))] if rng.random() < 0.5 else
                                    explore[int(rng.integers(len(explore)))])
            train_rows = []
            focal = [a["id"] for a in agents] + [G]
            for _ in range(args.ppo_iters):
                ms = []
                for m in range(args.matches):
                    k = focal[m % len(focal)]
                    if k == G:                          # one side recorded: the same budget as a specialist
                        ms.append({"a": {"deck": general_pick(), "slot": G, "record": True},
                                   "b": {"deck": general_pick(), "slot": G, "record": False}})
                        continue
                    a = next(x for x in agents if x["id"] == k)
                    p = wall if a["role"] == "main" else wmain
                    j = int(rng.choice(len(S2), p=p / p.sum()))
                    mine = next(q for q, s in enumerate(S2) if s["live"] and s["agent"] == k)
                    ms.append({"a": {"deck": s_json[mine], "slot": k, "record": True},
                               "b": {"deck": s_json[j], "slot": S2[j]["slot"], "record": False}})
                ti = time.time()
                msgs = [{"cmd": "league", "transitions": args.transitions, "concurrency": args.concurrency,
                         "deckoutWin": args.deckout_win, "seed": (args.seed * 1_000_003 + it_total * 1009 + w) % 2_000_000_000,
                         "matches": ms, "out": str(run / f"rollout_w{w}.bin")}
                        for w in range(args.workers)]
                replies = rp.collect(msgs, models, device)
                tc = time.time() - ti
                live.train()
                batch = concat([read_rollout(r["out"]) for r in replies])
                assert "slot" in batch and int(batch["slot"].max()) < n_agents and int(batch["slot"].min()) >= 0
                batch["agent"] = batch["slot"]
                adv, ret = advantages(batch, args.gamma, args.lam)
                batch["adv"], batch["ret"] = adv, ret
                batch["inputs"] = model_inputs(batch, "tokens")
                stats = ppo_update(live, opt, batch, targs, device)
                live.eval()
                games = [g for r in replies for g in r["results"]]
                cards_of = {d["name"]: d["cards"] for mt in ms for d in (mt["a"]["deck"], mt["b"]["deck"])}
                cov.add_games([cards_of[x] for g in games for x in (g.get("decks") or []) if x in cards_of])
                per = {}
                for g in games:
                    for seat in ("1", "2"):
                        name = g["seats"][seat][1:]            # model slot ('r' / 'o' prefix: recorded or not)
                        r_ = 1.0 if g["winner"] == int(seat) else 0.5 if g["winner"] not in (1, 2) else 0.0
                        per.setdefault(name, []).append(r_)
                tr = {"ppo_iter": it_total, "transitions": int(len(batch["action"])), "games": len(games),
                      "steps_per_game": round(float(np.mean([g["steps"] for g in games])), 1) if games else 0,
                      "errors": sum(1 for g in games if g.get("error")),
                      "endings": {e: sum(1 for g in games if (g.get("ending") or "none") == e)
                                  for e in {g.get("ending") or "none" for g in games}},
                      "agent_transitions": {int(k): int((batch["agent"] == k).sum()) for k in range(n_agents)},
                      "win_by_slot": {k: [len(v), round(float(np.mean(v)), 3)] for k, v in sorted(per.items())},
                      "collect_s": round(tc, 1), **{k: round(v, 5) for k, v in stats.items()}}
                train_rows.append(tr)
                print(f"  ppo {it_total}: games {tr['games']} len {tr['steps_per_game']} ent {stats['entropy']:.3f} "
                      f"kl {stats['kl']:.4f} clip {stats['clipfrac']:.3f} v {stats['v_loss']:.3f} endings {tr['endings']}",
                      flush=True)
                it_total += 1
            row["train"] = train_rows
            row["seconds"]["pilot"] = round(time.time() - t2, 1)

            if args.eval_every and (rnd + 1) % args.eval_every == 0:     # evaluation only: archived decks, SimpleBot
                path = run / f"eval_r{rnd:03d}.onnx"
                live.fixed_agent = G
                spec = export_policy(live, path, "tokens")
                live.fixed_agent = 0
                live.to(device)
                row["eval_simplebot_generalist"] = evaluate(spec, "simplebot", "all", "all", args.eval_games,
                                                            args.eval_workers, args.seed * 7 + rnd, run.name)
                path.unlink(missing_ok=True)
                print(f"  eval generalist vs SimpleBot (archived decks): {row['eval_simplebot_generalist']}", flush=True)

            log.write(json.dumps(row) + "\n")
            log.flush()
            torch.save({"model": live.state_dict(), "config": live.config()}, run / f"model_r{rnd:03d}.pt")
            torch.save({"model": live.state_dict(), "opt": opt.state_dict(), "round": rnd, "ppo_iter": it_total,
                        "agents": [{**a, "deck": pool.names(a["deck"])} for a in agents],
                        "history": [{**h, "deck": pool.names(h["deck"])} for h in history],
                        "cache": [[list(k), list(v)] for k, v in cache.items()], "exposure": cov.exposure,
                        "rng": rng.bit_generator.state, "config": live.config()}, ckpt)
            for f in run.glob("rollout_w*.bin"):
                f.unlink(missing_ok=True)
    finally:
        rp.close()
        log.close()


if __name__ == "__main__":
    main()
