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
--season K > 1 (log #93): a deck's draws are practised before they count. At the start of a season every deck draws
--candidates draws, and every game of the season plays one of them, chosen at random; the pilot trains on all of them
by PPO, but only the season's last iteration feeds the draft head (step 4), whose leave-one-out baseline then compares
a deck's candidates after the same practice; at its end every deck moves to one of its candidates, chosen at random
(step 5). A deck that turnover brings in mid-season draws its candidates at once. --season 1 is the loop above.
--select (log #127): the deck itself is one of its candidates, played unchanged beside its --candidates draws (every
iteration with --season 1, else through the season), and at the move (step 5) the deck moves to whichever of them scored
best in its games, itself on a tie, instead of to a random draw. Without it a deck moves every iteration to a draw of
--swaps forced changes whatever their results, and once the head's incoming choice collapses onto one card every draw
adds that card until the copy limit stops it, so basic Energy, which has none, piles up (#127).
--draft-heads K > 1 (log #120): a league of K draft heads sharing the one pilot. Every deck belongs to one head, which
reads it, draws for it and learns from its games (steps 1, 2, 4, 5); all decks still play one another at random, and
turnover replaces each head's worst decks within its own share, with mutants from its own best quarter (step 6). A
source with fewer heads keeps its own as the first ones; the others start uniform (--draft-heads-init fresh) or as
copies of its first head (copy), and the decks are dealt to the heads round-robin. With --draft-exploit (log #123) the
heads after the first are exploiters, as in AlphaStar's league: still paired at random, but their REINFORCE step and their
decks' results (turnover, best decks) count only their games against the first head's decks.
Nothing human enters training: the archived lists and SimpleBot are for evaluation only
(rl/evaluate_agents.py). The one exception is a diagnosis, never a lab card or the main line: --fixed-decks (log #127)
puts fixed lists, such as the archived ones, on one side of a --fixed-share of the games, never drafted or turned over,
so a fork's pilot practises them and one can ask whether they would win once played well.
--practice-games N (log #127): N more games an iteration between two fresh random decks of a playable structure and no
strategy (rl/decks.py wide_deck, the kind pilot-v2 learned on), all recorded for PPO and outside the population and the
draft head, so the pilot keeps playing every kind of deck: a pilot trained only on its population's one deck type
played other types so badly that no other type could win a place (#127).

Run: .venv/Scripts/python -m rl.metagame --run runs/meta-99 --decks 99 --init-from runs/pilot-v2/model_it00349.pt

The lab (rl/lab.py, notes/plan-lab.md) runs this loop as its main line and its branches: --fork-from continues another
run's whole state (pilot, optimizer, draft head, population, random state) in a new run, --pilot-opts grows the pilot
by new modules that start as the identity or at zero (rl/train.py load_grown), --reseed draws the fork's pairings and
deals afresh (the A/A test), --freeze-pilot skips PPO (meta-only screens), --stop-file ends the run cleanly after
an iteration.
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
from rl.decks import Pool, deck_shape, random_deck, wide_deck
from rl.draft import Drafter, random_changes, rloo
from rl.remote import RemotePool
from rl.rollouts import concat, read_rollout, subset
from rl.train import advantages, aux_targets, load_grown, model_inputs, ppo_update, remap_adam, shape_rewards, token_net

ROOT = Path(__file__).resolve().parent.parent
PILOT = {"d": 256, "layers": 4, "heads": 8, "count_features": True, "cross_layers": 1, "cand_self": 0}   # pilot-v2's shape
PPO = {"model": "tokens", "amp": True, "epochs": 3, "minibatch": 4096, "micro_batch": 1024, "clip": 0.2, "vf": 0.5,
       "ent": 0.01, "max_grad_norm": 0.5, "gpu_load": 0.7}                                            # tourn-3's settings
MUTANT_SHARE, MUTANT_CHANGES = 0.25, 10


def assign_heads(pop: list, K: int, keep: bool):
    """Each deck's draft head: kept when the source had K heads (keep), else dealt round-robin by position."""
    if not keep or any(a.get("head", K) >= K for a in pop):
        for d, a in enumerate(pop):
            a["head"] = d % K


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
    ap.add_argument("--draft-h-in-floor", type=float, default=0.0,
                    help="a floor in nats on the entropy the incoming card is drawn with: a choice below it is drawn at "
                         "the temperature that reaches it (log #109)")
    ap.add_argument("--draft-group-p", type=float, default=0.0,
                    help="chance that a change of a draw is a group change: all of the card's remaining copies (log #127)")
    ap.add_argument("--draft-heads", type=int, default=1,
                    help="draft heads, each drafting its share of the population with the one pilot (a league, log #120)")
    ap.add_argument("--draft-heads-init", choices=["fresh", "copy"], default="fresh",
                    help="heads a source does not have: uniform at the start (fresh) or copies of its first head (copy)")
    ap.add_argument("--draft-exploit", action="store_true",
                    help="heads after the first are exploiters: their draws and decks count only the games against the "
                         "first head's decks (log #123)")
    ap.add_argument("--draft-margin", type=float, default=0.5,
                    help="weight of the end-of-game prize margin in the draft head's reward (0 = result only)")
    ap.add_argument("--shaping", type=float, default=0.0, help="prize-shaping weight at iteration 0")
    ap.add_argument("--shaping-iters", type=int, default=100, help="iterations over which the shaping fades to 0")
    ap.add_argument("--season", type=int, default=1,
                    help="iterations a deck's draws are played before their results count (1 = a fresh draw every game)")
    ap.add_argument("--candidates", type=int, default=4, help="--season > 1 or --select: draws per deck per season")
    ap.add_argument("--select", action="store_true",
                    help="a deck moves to the best-scoring of itself and its candidates, not to a random draw (log #127)")
    ap.add_argument("--turnover-every", type=int, default=10)
    ap.add_argument("--turnover", type=float, default=0.15, help="share of the population replaced at a turnover")
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--save-every", type=int, default=25)
    ap.add_argument("--fork-from", default="", help="a metagame checkpoint whose whole state this run continues")
    ap.add_argument("--pilot-opts", default="", help='JSON architecture options added to the pilot, e.g. {"value_query": 4}')
    ap.add_argument("--reseed", type=int, default=None, help="at a fork: pairings and deals from this seed")
    ap.add_argument("--freeze-pilot", action="store_true", help="no PPO: the pilot plays and reads decks, unchanged")
    ap.add_argument("--ent", type=float, default=PPO["ent"])
    ap.add_argument("--epochs", type=int, default=PPO["epochs"])
    ap.add_argument("--micro-batch", type=int, default=PPO["micro_batch"])
    ap.add_argument("--lam", type=float, default=0.95, help="GAE lambda")
    ap.add_argument("--lam-turn", type=float, default=None,
                    help="GAE lambda between decisions of the same game turn (log #96; default: --lam everywhere)")
    ap.add_argument("--aux", type=float, default=0.0, help="weight of the auxiliary heads' loss (pilot aux_heads)")
    ap.add_argument("--distill", type=float, default=0.0,
                    help="expert iteration (log #96): weight of the cross-entropy toward a turn-level search's best option")
    ap.add_argument("--search-p", type=float, default=0.1, help="--distill: share of recorded main-phase decisions searched")
    ap.add_argument("--search-max", type=int, default=2, help="--distill: searched decisions a game at most")
    ap.add_argument("--search-options", type=int, default=6, help="--distill: options a search plays at most")
    ap.add_argument("--search-lines", type=int, default=2, help="--distill: lines an option (copies, hidden cards re-dealt)")
    ap.add_argument("--search-prize", type=float, default=0.0, help="--distill: a line's score per prize taken in the turn")
    ap.add_argument("--search-horizon", type=int, default=1,
                    help="--distill: turns a line is played before it is scored (1: the end of the turn; 2: after the reply)")
    ap.add_argument("--search-margin", type=float, default=0.02,
                    help="--distill: a search sets a target only if its best and worst options differ by more than this")
    ap.add_argument("--search-lethal", action="store_true",
                    help="--distill: targets only where an option won the game in every line (no value in the target; "
                         "the played option if it is one of them), log #106")
    ap.add_argument("--practice-games", type=int, default=0,
                    help="games an iteration between fresh wide random decks, for PPO only (log #127)")
    ap.add_argument("--fixed-decks", default="", help="diagnosis only (log #127): a JSON [{name, cards}] of fixed decks")
    ap.add_argument("--fixed-share", type=float, default=0.3, help="--fixed-decks: share of games with one on one side")
    ap.add_argument("--stop-file", default="", help="end cleanly after the iteration in which this file appears")
    args = ap.parse_args(argv)
    D, K = args.decks, args.draft_heads
    assert D >= 2 and K >= 1

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
    ckpt = run / "checkpoint.pt"
    st = torch.load(ckpt, map_location=device, weights_only=False) if args.resume and ckpt.exists() else None
    fork = torch.load(ROOT / args.fork_from, map_location=device, weights_only=False) if args.fork_from and not st else None
    init = (torch.load(ROOT / args.init_from, map_location=device, weights_only=False)
            if args.init_from and not (st or fork) else None)
    opts = json.loads(args.pilot_opts) if args.pilot_opts else {}
    # The architecture: a resumed run's own (any --pilot-opts are already in it), else the source's plus --pilot-opts.
    c0 = st["config"] if st else {**(fork or init or {"config": PILOT})["config"], **opts}
    net = token_net(c0, info).to(device)
    if init:
        load_grown(net, init["model"])
    net.eval()
    opt = torch.optim.Adam(net.parameters(), lr=args.lr, eps=1e-5)
    drafters = [Drafter(pool, c0["d"], c0["heads"], args.swaps, args.draft_lr, device, h_in_floor=args.draft_h_in_floor,
                        group_p=args.draft_group_p)
                for _ in range(K)]
    targs = SimpleNamespace(**{**PPO, "ent": args.ent, "epochs": args.epochs, "micro_batch": args.micro_batch,
                               "aux": args.aux, "distill": args.distill})

    start, deal_seed, cands = 0, args.seed, {}          # cands (--season > 1): deck id -> its draws this season
    if st or fork:
        src = st or fork
        if st:
            net.load_state_dict(st["net"])
            opt.load_state_dict(st["opt"])
        elif load_grown(net, fork["net"]):              # new modules: Adam's moments carried over by name
            old = [n for n, _ in token_net(fork["config"], info).named_parameters()]
            opt.load_state_dict(remap_adam(fork["opt"], old, net))
        else:
            opt.load_state_dict(fork["opt"])
        for g in opt.param_groups:                       # --lr wins over the saved one (a lab card may change it)
            g["lr"] = args.lr
        src_heads = src.get("drafters") or [src["drafter"]]
        assert len(src_heads) <= K, f"the source has {len(src_heads)} draft heads, more than --draft-heads {K}"
        for h, dr in enumerate(drafters):
            if h < len(src_heads):
                dr.load(src_heads[h])
            elif args.draft_heads_init == "copy":
                dr.load(src_heads[0])
        pop = [{**a, "deck": pool.vector(a["deck"])} for a in src["population"]]
        assign_heads(pop, K, keep=len(src_heads) == K)
        next_id, start = src["next_id"], src["iter"] + 1
        rng.bit_generator.state = src["rng"]
        deal_seed = src.get("deal_seed", args.seed)
        cands = (src.get("season") or {}).get("cands", {}) if args.season > 1 or args.select else {}
        if fork and args.reseed is not None:
            rng, deal_seed = np.random.default_rng(args.reseed), args.reseed
            torch.manual_seed(args.reseed)
    if not st:
        (run / "config.json").write_text(json.dumps({**vars(args), "pilot": net.config(), "ppo": vars(targs),
                                                    "device": device}, indent=1))
    if not (st or fork):
        pop = [{"id": i, "deck": random_deck(pool, rng), "born": 0, "parent": None, "kind": "initial", "sum": 0.0, "n": 0}
               for i in range(D)]
        assign_heads(pop, K, keep=False)
        next_id = D
    D = len(pop)                                         # a fork or resume keeps its own population size
    fixed = [pool.vector(x["cards"]) for x in json.load(open(ROOT / args.fixed_decks, encoding="utf-8"))] if args.fixed_decks else []
    assert D >= K, f"{D} decks for {K} draft heads"
    log = open(run / "log.jsonl", "a")

    try:
        for it in range(start, args.iters):
            t0 = time.time()
            lam = args.shaping * max(0.0, 1.0 - it / max(args.shaping_iters, 1))
            season = args.season > 1 or args.select
            counted = it % args.season == args.season - 1                # the draft head learns from this iteration
            if season and it % args.season == 0:
                cands = {}
            # 1. read every deck against a sample of the field
            views = []
            for d in range(D):
                others = [e for e in range(D) if e != d]
                field = [pop[e]["deck"] for e in rng.choice(others, min(args.field_sample, len(others)), replace=False)]
                views.append(drafters[pop[d]["head"]].view(net, pop[d]["deck"], field))
            t1 = time.time()
            # 2. games: random pairs, a fresh draw for each side (in a season: one of the side's candidates)
            if season:
                for d in range(D):
                    if pop[d]["id"] not in cands:
                        held = ([{"deck": pop[d]["deck"].copy(), "ev_j": [], "ev_c": [], "ev_mask": [], "ev_left": [],
                                  "ev_T": [], "logp": 0.0}] if args.select else [])     # the deck itself, unchanged
                        held += [drafters[pop[d]["head"]].sample(views[d], rng) for _ in range(args.candidates)]
                        for x in held:
                            x["sum"], x["n"] = 0.0, 0
                        cands[pop[d]["id"]] = held
            shards = [{"decks": [], "jobs": []} for _ in range(args.workers)]
            games_meta, draws = {}, {}
            rec_share = 0.0 if args.freeze_pilot else min(1.0, args.record / max(args.games, 1))
            for g in range(args.games):
                k, l = (int(x) for x in rng.choice(D, 2, replace=False))
                if fixed and rng.random() < args.fixed_share:   # a fixed deck f on l's side, as l = -1 - f
                    l = -1 - int(rng.integers(len(fixed)))
                k_seat, seed = 1 + int(rng.integers(2)), (deal_seed * 100_000 + it) * 1_000_003 + g
                sh = shards[g % args.workers]
                for a in (k, l):
                    if a < 0:
                        draws[g, a] = {"deck": fixed[-1 - a]}
                    elif season:
                        held = cands[pop[a]["id"]]
                        draws[g, a] = held[int(rng.integers(len(held)))]
                    else:
                        draws[g, a] = drafters[pop[a]["head"]].sample(views[a], rng)
                    sh["decks"].append({"name": f"g{g}d{a}", "cards": pool.names(draws[g, a]["deck"])})
                i = len(sh["decks"]) - 2
                sh["jobs"].append({"i": i, "j": i + 1, "iSeat": k_seat, "seed": seed, "rec": bool(rng.random() < rec_share)})
                games_meta[seed] = (g, k, l, k_seat)
            for g in range(args.games, args.games + (0 if args.freeze_pilot else args.practice_games)):
                seed = (deal_seed * 100_000 + it) * 1_000_003 + g    # practice: two wide decks, recorded, nobody's draw
                sh = shards[g % args.workers]
                sh["decks"] += [{"name": f"p{g}a", "cards": pool.names(wide_deck(pool, rng))},
                                {"name": f"p{g}b", "cards": pool.names(wide_deck(pool, rng))}]
                i = len(sh["decks"]) - 2
                sh["jobs"].append({"i": i, "j": i + 1, "iSeat": 1 + int(rng.integers(2)), "seed": seed, "rec": True})
                games_meta[seed] = None
            t2 = time.time()
            search = args.distill > 0 and not args.freeze_pilot
            extra = ({"cmd": "tsearch", "probeP": args.search_p, "maxProbes": args.search_max, "maxOptions": args.search_options,
                      "lines": args.search_lines, "prizeWeight": args.search_prize, "horizon": args.search_horizon} if search else {})
            msgs = [{"cmd": "games", "encoding": "tokens", "greedy": False, "deckoutWin": 1,
                     "concurrency": max(8, min(48, len(sh["jobs"]))), "out": str(run / f"rollout_w{w}.bin"),
                     "decks": sh["decks"], "jobs": sh["jobs"],
                     "history": int(net.config().get("history", 0) or 0),      # a pilot's action-history tokens (#76)
                     **extra, **({"seed": (deal_seed * 100_000 + it) * 31 + w} if search else {})}
                    for w, sh in enumerate(shards) if sh["jobs"]]
            replies = rp.collect(msgs, {0: net}, device)
            t3 = time.time()

            # 3. PPO on the recorded games
            recorded, ppo = 0, {}
            if not args.freeze_pilot:
                rolls = [read_rollout(r["out"]) for r in replies]
                batch = concat(rolls)
                recorded = len(batch["action"])
                if search:                                   # each searched decision's target: its best-scoring option
                    batch["search_target"] = np.full(recorded, -1, dtype=np.int32)
                    off, n_t, n_moved = 0, 0, 0
                    verbs = {"target": {}, "played": {}}         # where the two differ: the kind of move each is
                    for r, ro in zip(replies, rolls):
                        for pr in r.get("probes", []):
                            sc = [x for x in pr["score"] if x is not None]
                            won = [i for i, (w, n) in enumerate(zip(pr.get("won", []), pr["n"])) if n and w == n]
                            if args.search_lethal:
                                bi = next((i for i in won if pr["probed"][i] == pr["chosen"]), won[0] if won else None)
                            elif len(sc) >= 2 and max(sc) - min(sc) > args.search_margin:
                                bi = max((x, i) for i, x in enumerate(pr["score"]) if x is not None)[1]
                            else:
                                bi = None
                            if bi is not None:
                                best = pr["probed"][bi]
                                batch["search_target"][off + pr["k"]] = best
                                n_t += 1
                                if best != pr["chosen"]:
                                    n_moved += 1
                                    if "keys" in pr:
                                        for side, key in (("target", pr["keys"][bi]), ("played", pr["chosenKey"])):
                                            v = key.split("|")[0]
                                            verbs[side][v] = verbs[side].get(v, 0) + 1
                        off += len(ro["action"])
                    search_stats = {"probes": sum(len(r.get("probes", [])) for r in replies), "targets": n_t,
                                    "differs": n_moved, "lines": sum(r.get("lines", 0) for r in replies),
                                    "line_errors": sum(r.get("lineErrors", 0) for r in replies),
                                    "seconds": round(max((r.get("searchSeconds", 0) for r in replies), default=0), 1),
                                    "verbs": verbs}
                if net.config().get("aux_heads"):
                    batch["aux_target"] = aux_targets(batch)        # before the shaping: the unshaped result
                batch["reward"] = shape_rewards(batch, lam, prize_glob)
                batch["adv"], batch["ret"] = advantages(batch, 1.0, args.lam, args.lam_turn)
                if args.ppo_transitions and recorded > args.ppo_transitions:
                    batch = subset(batch, np.sort(rng.choice(recorded, args.ppo_transitions, replace=False)))
                batch["inputs"] = model_inputs(batch, "tokens")
                net.train()
                ppo = {q: round(v, 5) for q, v in ppo_update(net, opt, batch, targs, device).items()}
                net.eval()
            t4 = time.time()

            # 4. REINFORCE for the draft head on every draw
            practice = [r for rep in replies for r in rep["results"] if games_meta[r["seed"]] is None]
            games = [r for rep in replies for r in rep["results"] if games_meta[r["seed"]] is not None]
            per = {d: {"samples": [], "z": [], "margin": []} for d in range(D)}
            vs0 = [[] for _ in range(K)]                     # each head's results against head 0's decks
            fixed_z = [[] for _ in fixed]                    # --fixed-decks: each fixed deck's results
            for r in games:
                g, k, l, k_seat = games_meta[r["seed"]]
                zk = 1.0 if r["winner"] == k_seat else 0.0 if r["winner"] in (1, 2) else 0.5
                left = r.get("prizesLeft") or {}
                mk = (left.get(str(3 - k_seat), 0) - left.get(str(k_seat), 0)) / 6.0
                for a, b, z, m in ((k, l, zk, mk), (l, k, 1.0 - zk, -mk)):
                    if a < 0:
                        fixed_z[-1 - a].append(z)
                        continue
                    if b >= 0 and pop[b]["head"] == 0:
                        vs0[pop[a]["head"]].append(z)
                    elif args.draft_exploit and pop[a]["head"] > 0:   # an exploiter counts only games against head 0
                        continue
                    per[a]["samples"].append(draws[g, a])
                    per[a]["z"].append(z)
                    per[a]["margin"].append(m)
                    if season:                               # each candidate's results this season (--select)
                        draws[g, a]["sum"] += z
                        draws[g, a]["n"] += 1
            batch_d, z_iter = [[] for _ in range(K)], np.full(D, np.nan)      # each head learns from its own decks
            for d in range(D):
                if not per[d]["z"]:
                    continue
                z, m = np.array(per[d]["z"]), np.array(per[d]["margin"])
                if counted:
                    batch_d[pop[d]["head"]].append((views[d], per[d]["samples"], rloo(z + args.draft_margin * m, np.zeros(len(z)))))
                z_iter[d] = z.mean()
                pop[d]["sum"] += float(z.sum())
                pop[d]["n"] += len(z)
            parts = [dr.update(b, args.draft_ent) for dr, b in zip(drafters, batch_d)] if counted else []
            draft = (parts[0] if K == 1 else {**{q: round(float(np.mean([p[q] for p in parts])), 4) for q in parts[0]},
                                              "heads": parts}) if parts else {}
            t5 = time.time()

            # 5. every population deck moves to one more draw (in a season, at its end: to one of its practised candidates;
            #    with --select to the best-scoring of them, the deck itself first among equals)
            select = {}
            if not season:
                for d in range(D):
                    pop[d]["deck"] = drafters[pop[d]["head"]].sample(views[d], rng)["deck"]
            elif counted:
                moved, gain = 0, []
                for d in range(D):
                    held = cands[pop[d]["id"]]
                    if args.select:
                        mean = [x["sum"] / x["n"] if x["n"] else -1.0 for x in held]
                        k = max(range(len(held)), key=lambda q: (mean[q], -q))
                        moved += k > 0
                        if k > 0 and held[0]["n"]:
                            gain.append(mean[k] - mean[0])
                    else:
                        k = int(rng.integers(len(held)))
                    pop[d]["deck"] = held[k]["deck"].copy()
                if args.select:
                    select = {"moved": moved, "gain": round(float(np.mean(gain)), 4) if gain else None,
                              "games_per_candidate": round(float(np.mean([x["n"] for h in cands.values() for x in h])), 2)}
                cands = {}

            # 6. turnover
            turnover = []
            if args.turnover_every and (it + 1) % args.turnover_every == 0:
                score = np.array([a["sum"] / a["n"] if a["n"] else 0.5 for a in pop])
                for h in range(K):                               # each head's share, so a head is never crowded out
                    mine = np.array([d for d in range(D) if pop[d]["head"] == h])
                    order = mine[np.argsort(score[mine])]
                    top = order[-max(1, len(mine) // 4):]
                    for d in order[:int(round(args.turnover * len(mine)))]:
                        if rng.random() < MUTANT_SHARE:
                            p = int(rng.choice(top))
                            new = {"deck": random_changes(pool, pop[p]["deck"], MUTANT_CHANGES, rng), "parent": pop[p]["id"],
                                   "kind": "mutant"}
                        else:
                            new = {"deck": random_deck(pool, rng), "parent": None, "kind": "random"}
                        turnover.append({"out": pop[d]["id"], "score": round(float(score[d]), 4), "in": next_id,
                                         "kind": new["kind"], **({"head": h} if K > 1 else {})})
                        pop[d] = {"id": next_id, "born": it + 1, "sum": 0.0, "n": 0, "head": h, **new}
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
                   "recorded": recorded, "ppo": ppo, "draft": draft, "counted": counted,
                   **({"select": select} if select else {}),
                   **({"practice": {"games": len(practice), "errors": sum(1 for r in practice if r.get("error")),
                                    "steps_per_game": round(float(np.mean([r["steps"] for r in practice])), 1)}}
                      if practice else {}),
                   **({"search": search_stats} if search and not args.freeze_pilot and recorded else {}),
                   "margin_abs": round(float(np.mean([abs(m) for d in range(D) for m in per[d]["margin"]])), 4),
                   "shape_quartiles": {k: np.percentile(shapes[:, i], [25, 50, 75]).tolist()
                                       for i, k in enumerate(("pokemon", "trainer", "energy"))},
                   "z": [None if np.isnan(x) else round(float(x), 3) for x in z_iter],
                   "ids": [a["id"] for a in pop], "shapes": shapes.tolist(),
                   "best": [{"id": pop[d]["id"], "z": round(float(z_iter[d]), 3), "kind": pop[d]["kind"], "born": pop[d]["born"],
                             **({"head": pop[d]["head"]} if K > 1 else {}),
                             **deck_shape(pool, pop[d]["deck"]), **drafters[pop[d]["head"]].summary(views[d])} for d in best],
                   **({"heads": [{"decks": len(mine), "z": round(float(np.nanmean(z_iter[mine])), 3) if mine else None,
                                  "median": np.median(shapes[mine], 0).tolist() if mine else None,
                                  "vs0": round(float(np.mean(vs0[h])), 3) if vs0[h] else None}
                                 for h, mine in enumerate([d for d in range(D) if pop[d]["head"] == h] for h in range(K))]}
                      if K > 1 else {}),
                   "turnover": turnover,
                   **({"fixed": {"games": sum(map(len, fixed_z)), "z": round(float(np.mean([x for f in fixed_z for x in f])), 4)
                                 if any(fixed_z) else None,
                                 "by_deck": [round(float(np.mean(f)), 3) if f else None for f in fixed_z]}} if fixed else {}),
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

            state = {"net": net.state_dict(), "opt": opt.state_dict(), "drafter": drafters[0].state(),
                     **({"drafters": [dr.state() for dr in drafters]} if K > 1 else {}), "config": net.config(),
                     "population": [{**a, "deck": pool.names(a["deck"])} for a in pop], "next_id": next_id,
                     "iter": it, "round": it, "rng": rng.bit_generator.state, "deal_seed": deal_seed,
                     "season": {"cands": cands} if season else None,
                     "agents": [{"id": a["id"], "deck": pool.names(a["deck"])} for a in pop]}
            tmp = ckpt.with_suffix(".tmp")
            torch.save(state, tmp)
            os.replace(tmp, ckpt)
            if args.save_every and (it + 1) % args.save_every == 0:
                torch.save({k: state[k] for k in ("net", "drafter", "drafters", "config", "population", "agents", "iter", "round")
                            if k in state},
                           run / f"population_it{it:04d}.pt")
            for f in run.glob("rollout_w*.bin"):
                f.unlink(missing_ok=True)
            if args.stop_file and Path(args.stop_file).exists():
                print(f"stop file {args.stop_file}: ending after iteration {it}", flush=True)
                break
    finally:
        rp.close()
        log.close()


if __name__ == "__main__":
    main()
