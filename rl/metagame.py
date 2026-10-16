"""The metagame (logs #65-67): a population of decks, one pilot, one draft head.

Every iteration:
  1. the draft head reads every deck of the population through the pilot, against --field-sample other
     decks of the population (rl/draft.py)
  2. --games games between decks drawn at random from the population, seats at random; for every game
     each side draws a fresh deck from its population deck (--swaps cards replaced, chosen by the head)
  3. the pilot learns by PPO from --record of those games (both seats), with potential-based prize shaping
     that fades from --shaping to 0 over --shaping-iters (rl/train.py shape_rewards)
  4. the draft head takes one REINFORCE step on every draw's result (win 1, draw 0.5, loss 0) plus
     --draft-margin times the prize margin at the end ((opponent's prizes left - own) / 6), with a
     leave-one-out baseline over each deck's games; the margin tells draws apart in a matchup that is
     always lost (log #66)
  5. every population deck moves to one more draw
  6. every --turnover-every iterations the --turnover share of decks with the worst results over that
     period is replaced: by a fresh random deck (the format's rules only), or 1 in 4 by a deck of the
     best quarter with 10 cards replaced at random (log #67)
Nothing human enters training: the archived lists and SimpleBot are for evaluation only
(rl/evaluate_agents.py).

Run: .venv/Scripts/python -m rl.metagame --run runs/meta-99 --decks 99 --init-from runs/pilot-v2/model_it00349.pt
"""
import argparse
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from rl import limits
from rl.decks import Pool, deck_shape, random_deck
from rl.draft import Drafter, random_changes, rloo
from rl.remote import RemotePool
from rl.rollouts import concat, read_rollout, subset
from rl.train import advantages, build_model, model_inputs, ppo_update, shape_rewards

ROOT = Path(__file__).resolve().parent.parent
PILOT = {"d": 256, "layers": 4, "heads": 8, "count_features": True, "cross_layers": 1, "cand_self": 0}   # pilot-v2's shape
PPO = {"model": "tokens", "amp": True, "epochs": 3, "minibatch": 4096, "micro_batch": 1024, "clip": 0.2, "vf": 0.5,
       "ent": 0.01, "max_grad_norm": 0.5, "gpu_load": 0.7}                                            # tourn-3's settings
MUTANT_SHARE, MUTANT_CHANGES = 0.25, 10


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--decks", type=int, default=99, help="population size")
    ap.add_argument("--init-from", default="", help="pilot checkpoint to start from; empty = random init")
    ap.add_argument("--iters", type=int, default=150)
    ap.add_argument("--games", type=int, default=2000, help="games an iteration")
    ap.add_argument("--record", type=int, default=500, help="games an iteration recorded for PPO")
    ap.add_argument("--ppo-transitions", type=int, default=64000, help="PPO cap an iteration (0 = all recorded)")
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--swaps", type=int, default=3, help="cards a draw replaces")
    ap.add_argument("--field-sample", type=int, default=4, help="decks of the field each deck is read against")
    ap.add_argument("--draft-lr", type=float, default=1e-3)
    ap.add_argument("--draft-ent", type=float, default=0.01)
    ap.add_argument("--draft-margin", type=float, default=0.5,
                    help="weight of the end-of-game prize margin in the draft head's reward (0 = result only)")
    ap.add_argument("--shaping", type=float, default=0.0, help="prize-shaping weight at iteration 0")
    ap.add_argument("--shaping-iters", type=int, default=100, help="iterations over which the shaping fades to 0")
    ap.add_argument("--turnover-every", type=int, default=10)
    ap.add_argument("--turnover", type=float, default=0.15, help="share of the population replaced at a turnover")
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--save-every", type=int, default=25)
    args = ap.parse_args(argv)
    D = args.decks
    assert D >= 2

    run = ROOT / args.run
    run.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    limits.apply(device, args.workers)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    pool = Pool()

    rp = RemotePool(args.workers)
    rp.pace = 0.25
    info = rp.ask_all([{"cmd": "info"}] * args.workers)[0]
    prize_glob = info["tokens"]["prizeGlob"]
    init = torch.load(ROOT / args.init_from, map_location=device, weights_only=False) if args.init_from else None
    c0 = init["config"] if init else PILOT
    net = build_model(SimpleNamespace(model="tokens", d=c0["d"], tok_layers=c0["layers"], heads=c0["heads"],
                                      count_features=c0.get("count_features", False),
                                      cross_layers=c0.get("cross_layers", 1), cand_self=c0.get("cand_self", 0)), info).to(device)
    if init:
        net.load_state_dict(init["model"])
    net.eval()
    opt = torch.optim.Adam(net.parameters(), lr=args.lr, eps=1e-5)
    drafter = Drafter(pool, c0["d"], c0["heads"], args.swaps, args.draft_lr, device)
    targs = SimpleNamespace(**PPO)

    ckpt = run / "checkpoint.pt"
    start = 0
    if args.resume and ckpt.exists():
        st = torch.load(ckpt, map_location=device, weights_only=False)
        net.load_state_dict(st["net"])
        opt.load_state_dict(st["opt"])
        drafter.load(st["drafter"])
        pop = [{**a, "deck": pool.vector(a["deck"])} for a in st["population"]]
        next_id, start = st["next_id"], st["iter"] + 1
        rng.bit_generator.state = st["rng"]
    else:
        pop = [{"id": i, "deck": random_deck(pool, rng), "born": 0, "parent": None, "kind": "initial", "sum": 0.0, "n": 0}
               for i in range(D)]
        next_id = D
        (run / "config.json").write_text(json.dumps({**vars(args), "pilot": net.config(), "ppo": PPO, "device": device},
                                                    indent=1))
    log = open(run / "log.jsonl", "a")

    try:
        for it in range(start, args.iters):
            t0 = time.time()
            lam = args.shaping * max(0.0, 1.0 - it / max(args.shaping_iters, 1))
            # 1. read every deck against a sample of the field
            views = []
            for d in range(D):
                others = [e for e in range(D) if e != d]
                field = [pop[e]["deck"] for e in rng.choice(others, min(args.field_sample, len(others)), replace=False)]
                views.append(drafter.view(net, pop[d]["deck"], field))
            t1 = time.time()
            # 2. games: random pairs, a fresh draw for each side
            shards = [{"decks": [], "jobs": []} for _ in range(args.workers)]
            games_meta, draws = {}, {}
            rec_share = min(1.0, args.record / max(args.games, 1))
            for g in range(args.games):
                k, l = (int(x) for x in rng.choice(D, 2, replace=False))
                k_seat, seed = 1 + int(rng.integers(2)), (args.seed * 100_000 + it) * 1_000_003 + g
                sh = shards[g % args.workers]
                for a in (k, l):
                    draws[g, a] = drafter.sample(views[a], rng)
                    sh["decks"].append({"name": f"g{g}d{a}", "cards": pool.names(draws[g, a]["deck"])})
                i = len(sh["decks"]) - 2
                sh["jobs"].append({"i": i, "j": i + 1, "iSeat": k_seat, "seed": seed, "rec": bool(rng.random() < rec_share)})
                games_meta[seed] = (g, k, l, k_seat)
            t2 = time.time()
            msgs = [{"cmd": "games", "encoding": "tokens", "greedy": False, "deckoutWin": 1,
                     "concurrency": max(8, min(48, len(sh["jobs"]))), "out": str(run / f"rollout_w{w}.bin"),
                     "decks": sh["decks"], "jobs": sh["jobs"]} for w, sh in enumerate(shards) if sh["jobs"]]
            replies = rp.collect(msgs, {0: net}, device)
            t3 = time.time()

            # 3. PPO on the recorded games
            batch = concat([read_rollout(r["out"]) for r in replies])
            recorded = len(batch["action"])
            batch["reward"] = shape_rewards(batch, lam, prize_glob)
            batch["adv"], batch["ret"] = advantages(batch, 1.0, 0.95)
            if args.ppo_transitions and recorded > args.ppo_transitions:
                batch = subset(batch, np.sort(rng.choice(recorded, args.ppo_transitions, replace=False)))
            batch["inputs"] = model_inputs(batch, "tokens")
            net.train()
            ppo = {q: round(v, 5) for q, v in ppo_update(net, opt, batch, targs, device).items()}
            net.eval()
            t4 = time.time()

            # 4. REINFORCE for the draft head on every draw
            games = [r for rep in replies for r in rep["results"]]
            per = {d: {"samples": [], "z": [], "margin": []} for d in range(D)}
            for r in games:
                g, k, l, k_seat = games_meta[r["seed"]]
                zk = 1.0 if r["winner"] == k_seat else 0.0 if r["winner"] in (1, 2) else 0.5
                left = r.get("prizesLeft") or {}
                mk = (left.get(str(3 - k_seat), 0) - left.get(str(k_seat), 0)) / 6.0
                for a, z, m in ((k, zk, mk), (l, 1.0 - zk, -mk)):
                    per[a]["samples"].append(draws[g, a])
                    per[a]["z"].append(z)
                    per[a]["margin"].append(m)
            batch_d, z_iter = [], np.full(D, np.nan)
            for d in range(D):
                if not per[d]["z"]:
                    continue
                z, m = np.array(per[d]["z"]), np.array(per[d]["margin"])
                batch_d.append((views[d], per[d]["samples"], rloo(z + args.draft_margin * m, np.zeros(len(z)))))
                z_iter[d] = z.mean()
                pop[d]["sum"] += float(z.sum())
                pop[d]["n"] += len(z)
            draft = drafter.update(batch_d, args.draft_ent)
            t5 = time.time()

            # 5. every population deck moves to one more draw
            for d in range(D):
                pop[d]["deck"] = drafter.sample(views[d], rng)["deck"]

            # 6. turnover
            turnover = []
            if args.turnover_every and (it + 1) % args.turnover_every == 0:
                score = np.array([a["sum"] / a["n"] if a["n"] else 0.5 for a in pop])
                order = np.argsort(score)
                top = order[-max(1, D // 4):]
                for d in order[:int(round(args.turnover * D))]:
                    if rng.random() < MUTANT_SHARE:
                        p = int(rng.choice(top))
                        new = {"deck": random_changes(pool, pop[p]["deck"], MUTANT_CHANGES, rng), "parent": pop[p]["id"],
                               "kind": "mutant"}
                    else:
                        new = {"deck": random_deck(pool, rng), "parent": None, "kind": "random"}
                    turnover.append({"out": pop[d]["id"], "score": round(float(score[d]), 4), "in": next_id, "kind": new["kind"]})
                    pop[d] = {"id": next_id, "born": it + 1, "sum": 0.0, "n": 0, **new}
                    next_id += 1
                for a, sc in zip(pop, score):                    # a fresh window for everyone
                    if a["born"] <= it:
                        a["last"] = round(float(sc), 4)          # the window's result, for rl/evaluate_agents.py
                    a["sum"], a["n"] = 0.0, 0

            shapes = np.array([[s["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"]]
                               for s in (deck_shape(pool, a["deck"]) for a in pop)])
            best = [int(d) for d in np.argsort(-np.nan_to_num(z_iter, nan=-1))[:3]]
            cut = sum(1 for r in games if r["winner"] not in (1, 2))
            row = {"iter": it, "lam": round(lam, 5), "games": len(games), "errors": sum(1 for r in games if r.get("error")),
                   "cut_off": cut, "steps_per_game": round(float(np.mean([r["steps"] for r in games])), 1),
                   "endings": {e: sum(1 for r in games if (r.get("ending") or "none") == e) for e in {r.get("ending") or "none" for r in games}},
                   "recorded": recorded, "ppo": ppo, "draft": draft,
                   "margin_abs": round(float(np.mean([abs(m) for d in range(D) for m in per[d]["margin"]])), 4),
                   "shape_quartiles": {k: np.percentile(shapes[:, i], [25, 50, 75]).tolist()
                                       for i, k in enumerate(("pokemon", "trainer", "energy"))},
                   "z": [None if np.isnan(x) else round(float(x), 3) for x in z_iter],
                   "ids": [a["id"] for a in pop], "shapes": shapes.tolist(),
                   "best": [{"id": pop[d]["id"], "z": round(float(z_iter[d]), 3), "kind": pop[d]["kind"], "born": pop[d]["born"],
                             **deck_shape(pool, pop[d]["deck"]), **drafter.summary(views[d])} for d in best],
                   "turnover": turnover,
                   "seconds": {"read": round(t1 - t0, 1), "draw": round(t2 - t1, 1), "play": round(t3 - t2, 1),
                               "ppo": round(t4 - t3, 1), "draft": round(t5 - t4, 1), "total": round(time.time() - t0, 1)}}
            log.write(json.dumps(row) + "\n")
            log.flush()
            q = row["shape_quartiles"]
            print(f"it {it}: {len(games)} games in {row['seconds']['play']}s ({row['seconds']['total']}s), cut {cut}, "
                  f"recorded {recorded}, lam {lam:.3f}; median P/T/E {q['pokemon'][1]:.0f}/{q['trainer'][1]:.0f}/{q['energy'][1]:.0f}; "
                  "best " + ", ".join(f"#{b['id']} {b['z']:.2f} {b['pokemon']}/{b['trainer']}/{b['basic_energy'] + b['special_energy']}"
                                      for b in row["best"])
                  + (f"; turnover {len(turnover)}" if turnover else ""), flush=True)

            state = {"net": net.state_dict(), "opt": opt.state_dict(), "drafter": drafter.state(), "config": net.config(),
                     "population": [{**a, "deck": pool.names(a["deck"])} for a in pop], "next_id": next_id,
                     "iter": it, "round": it, "rng": rng.bit_generator.state,
                     "agents": [{"id": a["id"], "deck": pool.names(a["deck"])} for a in pop]}
            tmp = ckpt.with_suffix(".tmp")
            torch.save(state, tmp)
            os.replace(tmp, ckpt)
            if args.save_every and (it + 1) % args.save_every == 0:
                torch.save({k: state[k] for k in ("net", "drafter", "config", "population", "agents", "iter", "round")},
                           run / f"population_it{it:04d}.pt")
            for f in run.glob("rollout_w*.bin"):
                f.unlink(missing_ok=True)
    finally:
        rp.close()
        log.close()


if __name__ == "__main__":
    main()
