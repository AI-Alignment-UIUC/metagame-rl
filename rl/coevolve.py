"""Co-evolution of the decks and the pilot (log #52): the pilot trains only on decks the system
itself drafts, and the drafting explores the whole deck space.

One process holds the learner, its optimizer, its league of past snapshots and one set of rollout
workers, which serve both training and the matchup matrix. Each round:
  1. measure every pair of the population under the current pilot (greedy, real games), solve the
     meta game -> mixture sigma; drop decks out of the support when the population is over its cap
  2. draft: the value search (rl/search.py, with novelty) proposes --new decks against sigma, with
     restarts from coverage-weighted random decks (rl/deckgen.py); a fresh exploration set of
     --explore decks is drawn the same way, and the --explore-admit of them the pilot rates best
     join the population too
  3. pilot: --ppo-iters PPO iterations; every iteration's matchups are drawn anew from
       sigma vs sigma                 --p-nash
       this round's new decks vs sigma --p-new
       any population deck vs sigma   --p-pop
       exploration decks vs sigma or each other (the rest)
     the learner plays itself and its league on them, both seats. Each card's exposure (training
     games it was in) is counted and steers the next draws toward the least seen.
Nothing human enters training: decks start random over the pool and are built by the search; the
archived lists and SimpleBot appear only in evaluation (--eval-every) and in the log's "nearest
archived list" labels.

Run (from pilot-v2):
  .venv/Scripts/python -m rl.coevolve --run runs/coevo-1 --init-from runs/pilot-v2/model_it00349.pt \
      --rounds 30 --pool full
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
from rl.psro import Population, label_of
from rl.remote import RemotePool
from rl.rollouts import concat, read_rollout
from rl.search import MIN_CHANGED, GamesScorer, ValueScorer, changed, search
from rl.train import advantages, build_model, evaluate, export_policy, model_inputs, ppo_update

ROOT = Path(__file__).resolve().parent.parent


def drop(pop: Population, keep: list):
    """Keeps only the decks at indices `keep` (in that order)."""
    pop.decks = [pop.decks[i] for i in keep]
    pop.names = [pop.names[i] for i in keep]
    pop.origin = [pop.origin[i] for i in keep]
    ix = np.ix_(keep, keep)
    pop.wins, pop.games = pop.wins[ix], pop.games[ix]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--init-from", help="pilot checkpoint to start from (its architecture is used)")
    ap.add_argument("--pool", choices=["field", "full"], default="full")
    ap.add_argument("--rounds", type=int, default=30)
    ap.add_argument("--init-decks", type=int, default=16, help="random decks in the first population")
    ap.add_argument("--max-pop", type=int, default=48, help="population cap; decks out of the support leave, oldest first")
    ap.add_argument("--games", type=int, default=24, help="games per pair when measuring the population")
    ap.add_argument("--new", type=int, default=4, help="decks the search proposes per round")
    ap.add_argument("--search-seconds", type=float, default=120)
    ap.add_argument("--search-temperature", type=float, default=0.0)
    ap.add_argument("--novelty", type=float, default=0.03)
    ap.add_argument("--explore", type=int, default=64, help="exploration decks drawn per round (training only)")
    ap.add_argument("--explore-admit", type=int, default=2, help="of them, how many the pilot rates best join the population")
    ap.add_argument("--p-flat", type=float, default=0.5, help="share of random decks with the game-agnostic flat shape")
    ap.add_argument("--coverage-power", type=float, default=0.5, help="card weight (1 + exposure) ^ -power; 0 = uniform")
    ap.add_argument("--ppo-iters", type=int, default=10, help="PPO iterations per round")
    ap.add_argument("--matchups", type=int, default=256, help="matchups drawn per PPO iteration")
    ap.add_argument("--p-nash", type=float, default=0.4)
    ap.add_argument("--p-new", type=float, default=0.2)
    ap.add_argument("--p-pop", type=float, default=0.15)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--gpu-pace", type=float, default=0.25,
                    help="inference rests this x its GPU time after each batch (0.25: ~80%% busy at most; CLAUDE.md load cap)")
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
    ap.add_argument("--deckout-win", type=float, default=1.0,
                    help="reward for a deck-out win; 1 = the plain game result (no game-specific shaping)")
    ap.add_argument("--snapshot-every", type=int, default=25, help="PPO iterations between league snapshots")
    ap.add_argument("--max-snapshots", type=int, default=8)
    ap.add_argument("--self-weight", type=float, default=0.5)
    ap.add_argument("--eval-every", type=int, default=5, help="rounds between SimpleBot evaluations (0: never)")
    ap.add_argument("--eval-games", type=int, default=400)
    ap.add_argument("--eval-workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args(argv)

    run = ROOT / args.run
    run.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    args.eval_workers = limits.cap_workers(args.eval_workers)
    limits.apply(device, args.workers)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    srng = np.random.default_rng(args.seed + 7)

    archived = archived_decks(Pool())                  # labels and evaluation only
    field = sorted({c for _, v in archived for c in Pool().names(v)})
    pool = Pool(restrict=field if args.pool == "field" else None)
    gen = DeckGen(pool)
    cov = Coverage(pool)

    rp = RemotePool(args.workers)
    rp.pace = args.gpu_pace
    info = rp.ask_all([{"cmd": "info"}] * args.workers)[0]
    cfg = {"d": 192, "layers": 3, "heads": 4, "count_features": False, "cross_layers": 1, "cand_self": 0}
    init = torch.load(ROOT / args.init_from, map_location=device) if args.init_from else None
    if init is not None:
        cfg.update({k: init["config"][k] for k in cfg if k in init["config"]})
    margs = SimpleNamespace(model="tokens", d=cfg["d"], tok_layers=cfg["layers"], heads=cfg["heads"],
                            count_features=cfg["count_features"], cross_layers=cfg["cross_layers"], cand_self=cfg["cand_self"])
    model = build_model(margs, info).to(device)
    if init is not None:
        model.load_state_dict(init["model"])
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, eps=1e-5)
    targs = SimpleNamespace(**vars(args), model="tokens", amp=True)
    gm = GpuMatrix.attach(model, rp, args.workers, device=device)

    pop = Population(pool)
    start, it_total, snapshots, pending = 0, 0, [], []
    ckpt = run / "checkpoint.pt"
    if args.resume and ckpt.exists():
        st = torch.load(ckpt, map_location=device, weights_only=False)
        model.load_state_dict(st["model"])
        opt.load_state_dict(st["opt"])
        start, it_total, snapshots = st["round"] + 1, st["ppo_iter"], st["snapshots"]
        for d in st["population"]:
            pop.add(pool.vector(d["cards"]), d["name"], d["origin"])
        pop.wins, pop.games = st["wins"], st["games"]
        cov.exposure = st["exposure"]
        rng = np.random.default_rng(args.seed * 7919 + start)
        srng = np.random.default_rng(args.seed * 104729 + start)
    else:
        for k in range(args.init_decks):
            pop.add(gen(rng, cov.weights(args.coverage_power), args.p_flat), f"random-{k}", "random")
    (run / "config.json").write_text(json.dumps({**vars(args), "model_config": cfg, "device": device}, indent=1))
    log = open(run / "log.jsonl", "a")
    snapshot_models = {}

    def nearest(v):
        o = [overlap(v, a) for _, a in archived]
        k = int(np.argmax(o))
        return label_of(archived[k][0]), round(o[k], 3)

    def deck_json(i):
        return {"name": pop.names[i], "cards": pool.names(pop.decks[i])}

    def draw(sig, n):
        return list(rng.choice(len(sig), size=n, p=sig))

    try:
        for rnd in range(start, args.rounds + 1):
            t0 = time.time()
            # 1. measure every pair under the current pilot, solve, trim
            model.eval()
            pop.measure(run, None, args.games, args.workers, 0, args.seed * 1000 + rnd, gm)
            P = pop.wins / np.maximum(pop.games, 1)
            sigma, _ = solve(P)
            row = {"round": rnd, "ppo_iter": it_total, "population": len(pop.decks), "matrix": gm.last}
            if pending:
                by_name = {n: i for i, n in enumerate(pop.names)}
                row["realized"] = [{"deck": n, "predicted": round(p, 4),
                                    "real_vs_sigma": round(float(P[by_name[n]] @ sigma), 4)}
                                   for n, p in pending if n in by_name]
                pending = []
            if len(pop.decks) > args.max_pop:
                out = [i for i in range(len(pop.decks)) if sigma[i] <= 1e-4][:len(pop.decks) - args.max_pop]
                keep = [i for i in range(len(pop.decks)) if i not in out]
                with open(run / "retired.jsonl", "a") as f:
                    for i in out:
                        f.write(json.dumps({"round": rnd, **deck_json(i), "origin": pop.origin[i]}) + "\n")
                drop(pop, keep)
                sigma = sigma[keep] / sigma[keep].sum()
                row["retired"] = len(out)
            support = [(i, float(sigma[i])) for i in np.argsort(-sigma) if sigma[i] > 1e-4]
            row["support"] = [{"deck": pop.names[i], "weight": round(w, 4), "origin": pop.origin[i],
                               "energy": int(pop.decks[i][pool.basic_energy].sum()), "nearest": nearest(pop.decks[i])}
                              for i, w in support]
            row["coverage"] = cov.summary(pop.decks, [pop.decks[i] for i, _ in support])
            row["seconds"] = {"measure": round(time.time() - t0, 1)}
            print(f"round {rnd}: population {len(pop.decks)}, support " + ", ".join(
                f"{pop.names[i][:24]} {w:.2f}" for i, w in support[:6]) + f"; coverage {row['coverage']}", flush=True)
            if rnd == args.rounds:
                log.write(json.dumps(row) + "\n")
                break

            # 2. draft: proposals from the value search, plus exploration decks
            t1 = time.time()
            w_cov = cov.weights(args.coverage_power)
            scorer = ValueScorer(gm, novelty=args.novelty)
            props, sinfo = search(scorer, pop, sigma, args.new, args.search_seconds, srng,
                                  lambda pl, r: gen(r, w_cov, args.p_flat), confirm=GamesScorer(gm),
                                  temperature=args.search_temperature)
            row["search"] = {k: v for k, v in sinfo.items() if k != "runs"}
            new_idx = []
            for k, (v, score, _) in enumerate(props):
                name = f"r{rnd}-s{k} ({nearest(v)[0]}-like)"
                pop.add(v, name, f"search r{rnd}")
                pending.append((name, score))
                new_idx.append(len(pop.decks) - 1)
            explore = [gen(rng, w_cov, args.p_flat) for _ in range(args.explore)]
            if args.explore_admit:
                s = scorer(explore)                        # value vs sigma (+ novelty), as the search scored
                admitted = 0
                for k in np.argsort(-s):
                    if admitted == args.explore_admit:
                        break
                    if all(changed(explore[k], u) >= MIN_CHANGED for u in pop.decks):
                        name = f"r{rnd}-x{admitted} ({nearest(explore[k])[0]}-like)"
                        pop.add(explore[k], name, f"explore r{rnd}")
                        pending.append((name, float(s[k])))
                        new_idx.append(len(pop.decks) - 1)
                        admitted += 1
            row["proposals"] = [{"deck": pop.names[i], "energy": int(pop.decks[i][pool.basic_energy].sum()),
                                 "nearest": nearest(pop.decks[i])} for i in new_idx]
            row["seconds"]["draft"] = round(time.time() - t1, 1)

            # 3. pilot: PPO on drafted decks, matchups redrawn every iteration
            t2 = time.time()
            sig = np.zeros(len(pop.decks))
            sig[:len(sigma)] = sigma
            sig /= sig.sum()
            ex_json = [{"name": f"x{k}", "cards": pool.names(v)} for k, v in enumerate(explore)]
            train_rows = []
            for _ in range(args.ppo_iters):
                ms = []
                for _ in range(args.matchups):
                    u = rng.random()
                    if u < args.p_nash:
                        a, b = (deck_json(i) for i in draw(sig, 2))
                    elif u < args.p_nash + args.p_new and new_idx:
                        a, b = deck_json(new_idx[rng.integers(len(new_idx))]), deck_json(draw(sig, 1)[0])
                    elif u < args.p_nash + args.p_new + args.p_pop:
                        a, b = deck_json(int(rng.integers(len(pop.decks)))), deck_json(draw(sig, 1)[0])
                    else:
                        a = ex_json[rng.integers(len(ex_json))]
                        b = deck_json(draw(sig, 1)[0]) if rng.random() < 0.5 else ex_json[rng.integers(len(ex_json))]
                    ms.append([a, b] if rng.random() < 0.5 else [b, a])
                league = snapshots[-args.max_snapshots:]
                opponents = [{"spec": "self", "weight": 1.0}]
                if league:
                    opponents = [{"spec": "self", "weight": args.self_weight}] + [
                        {"spec": f"slot:{k + 1}", "weight": (1 - args.self_weight) / len(league)} for k in range(len(league))]
                for f in league:
                    if f not in snapshot_models:
                        m = build_model(margs, info).to(device)
                        m.load_state_dict(torch.load(f, map_location=device)["model"])
                        snapshot_models[f] = m.eval()
                for f in list(snapshot_models):
                    if f not in league:
                        del snapshot_models[f]
                models = {0: model.eval(), **{k + 1: snapshot_models[f] for k, f in enumerate(league)}}
                ti = time.time()
                msgs = [{"cmd": "collect", "encoding": "tokens", "transitions": args.transitions,
                         "concurrency": args.concurrency, "deckoutWin": args.deckout_win,
                         "seed": (args.seed * 1_000_003 + it_total * 1009 + w) % 2_000_000_000,
                         "matchups": ms, "opponents": opponents, "out": str(run / f"rollout_w{w}.bin")} for w in range(args.workers)]
                replies = rp.collect(msgs, models, device)
                tc = time.time() - ti
                model.train()
                batch = concat([read_rollout(r["out"]) for r in replies])
                adv, ret = advantages(batch, args.gamma, args.lam)
                batch["adv"], batch["ret"] = adv, ret
                batch["inputs"] = model_inputs(batch, "tokens")
                stats = ppo_update(model, opt, batch, targs, device)
                games = [g for r in replies for g in r["results"]]
                cards_of = {d["name"]: d["cards"] for m in ms for d in m}
                cov.add_games([cards_of[n] for g in games for n in (g.get("decks") or []) if n in cards_of])
                vs = {}
                for g in games:
                    for seat in ("1", "2"):
                        if g["seats"][seat] != "learner":
                            continue
                        other = g["seats"]["2" if seat == "1" else "1"]
                        vs.setdefault(other, []).append(1.0 if g["winner"] == int(seat) else 0.5 if g["winner"] not in (1, 2) else 0.0)
                tr = {"ppo_iter": it_total, "transitions": int(len(batch["action"])), "games": len(games),
                      "steps_per_game": round(float(np.mean([g["steps"] for g in games])), 1) if games else 0,
                      "errors": sum(1 for g in games if g.get("error")),
                      "endings": {e: sum(1 for g in games if (g.get("ending") or "none") == e)
                                  for e in {g.get("ending") or "none" for g in games}},
                      "win_vs": {k: round(float(np.mean(v)), 4) for k, v in vs.items()},
                      "collect_s": round(tc, 1), **{k: round(v, 5) for k, v in stats.items()}}
                train_rows.append(tr)
                print(f"  ppo {it_total}: games {tr['games']} len {tr['steps_per_game']} ent {stats['entropy']:.3f} "
                      f"kl {stats['kl']:.4f} clip {stats['clipfrac']:.3f} v {stats['v_loss']:.3f} endings {tr['endings']}", flush=True)
                it_total += 1
                if it_total % args.snapshot_every == 0:
                    snap = run / f"model_it{it_total - 1:05d}.pt"
                    torch.save({"model": model.state_dict(), "config": model.config()}, snap)
                    snapshots.append(str(snap))
            model.eval()
            row["train"] = train_rows
            row["seconds"]["pilot"] = round(time.time() - t2, 1)

            if args.eval_every and (rnd + 1) % args.eval_every == 0:     # evaluation only: archived decks, SimpleBot
                path = run / f"eval_r{rnd:03d}.onnx"
                spec = export_policy(model, path, "tokens")
                model.to(device)
                row["eval_simplebot"] = evaluate(spec, "simplebot", "all", "all", args.eval_games, args.eval_workers,
                                                 args.seed * 7 + rnd, run.name)
                path.unlink(missing_ok=True)
                print(f"  eval vs SimpleBot (archived decks): {row['eval_simplebot']}", flush=True)

            log.write(json.dumps(row) + "\n")
            log.flush()
            (run / "population.json").write_text(json.dumps(
                [{"name": n, "cards": pool.names(v), "origin": o} for n, v, o in zip(pop.names, pop.decks, pop.origin)]))
            torch.save({"model": model.state_dict(), "config": model.config()}, run / f"model_r{rnd:03d}.pt")
            torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "round": rnd, "ppo_iter": it_total,
                        "snapshots": snapshots, "population": [{"name": n, "cards": pool.names(v), "origin": o}
                                                               for n, v, o in zip(pop.names, pop.decks, pop.origin)],
                        "wins": pop.wins, "games": pop.games, "exposure": cov.exposure, "config": model.config()}, ckpt)
            for f in run.glob("rollout_w*.bin"):
                f.unlink(missing_ok=True)
    finally:
        rp.close()
        log.close()


if __name__ == "__main__":
    main()
