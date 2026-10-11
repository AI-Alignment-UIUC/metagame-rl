"""Which agents and decks of a league checkpoint play games that run to the step cap (log #58).

Rebuilds the league of a run's checkpoint (rl/league.py, separate networks), plays one batch of
training-style games (each live agent on its own deck against every strategy in turn, the generalist on
league decks), and counts the games cut off at env/game.js MAX_STEPS by focal agent and deck pair.
With --export DIR it also writes each live agent's network as ONNX and the strategies' decks, for
notes/scripts/trace_loop.js.

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/league_loops.py --run runs/league-3 --export <dir>
"""
import argparse
import collections
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from rl import limits
from rl.decks import Pool
from rl.league import FROZEN_SLOT, SeparatePilots
from rl.remote import RemotePool
from rl.train import build_model, export_policy

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--transitions", type=int, default=3000, help="per worker")
    ap.add_argument("--export")
    ap.add_argument("--seed", type=int, default=5)
    args = ap.parse_args(argv)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    limits.apply(device, args.workers)
    run = ROOT / args.run
    cfg = json.load(open(run / "config.json"))
    st = torch.load(run / "checkpoint.pt", map_location=device, weights_only=False)
    c0 = st["config"]
    pool = Pool()
    rp = RemotePool(args.workers)
    rp.pace = 0.25
    info = rp.ask_all([{"cmd": "info"}] * args.workers)[0]

    def build(k):
        return build_model(SimpleNamespace(model="tokens", d=c0["d"], tok_layers=c0["layers"], heads=c0["heads"],
                                           count_features=c0.get("count_features", False),
                                           cross_layers=c0.get("cross_layers", 1), cand_self=c0.get("cand_self", 0),
                                           n_agents=k), info)
    n_agents = cfg["n_agents"]
    pilots = SeparatePilots(build, n_agents, st["nets"][0], 1e-4, device)
    pilots.load(st)
    agents, history = st["agents"], st["history"]
    G = n_agents - 1
    strategies = [{"name": f"{a['lineage']}.v{a['version']}", "cards": a["deck"], "slot": a["id"]} for a in agents]
    models = {k: pilots.model(k) for k in range(n_agents)}
    for i, h in enumerate(history):
        net = build(0).to(device)
        net.load_state_dict(torch.load(run / "snapshots" / f"{h['net']}.pt", map_location=device, weights_only=False)["model"])
        models[FROZEN_SLOT + i] = net.eval()
        strategies.append({"name": h["name"], "cards": h["deck"], "slot": FROZEN_SLOT + i})
    print(f"round {st['round']}: {len(agents)} live specialists, {len(history)} frozen strategies", flush=True)

    rng = np.random.default_rng(args.seed)
    matches = []
    for a in agents:                                  # every specialist against every strategy
        mine = next(s for s in strategies if s["slot"] == a["id"])
        for s in strategies:
            matches.append({"a": {"deck": {"name": mine["name"], "cards": mine["cards"]}, "slot": a["id"], "record": True},
                            "b": {"deck": {"name": s["name"], "cards": s["cards"]}, "slot": s["slot"], "record": False}})
    for _ in range(len(strategies)):                  # the generalist on league decks
        x, y = rng.choice(len(strategies), 2)
        matches.append({"a": {"deck": {"name": strategies[x]["name"], "cards": strategies[x]["cards"]}, "slot": G, "record": True},
                        "b": {"deck": {"name": strategies[y]["name"], "cards": strategies[y]["cards"]}, "slot": G, "record": False}})
    out = ROOT / "runs" / "_loops"
    out.mkdir(exist_ok=True)
    msgs = [{"cmd": "league", "transitions": args.transitions, "concurrency": 32, "deckoutWin": 1,
             "seed": args.seed * 1009 + w, "matches": matches, "out": str(out / f"r{w}.bin")} for w in range(args.workers)]
    replies = rp.collect(msgs, models, device)
    rp.close()
    games = [g for r in replies for g in r["results"]]
    cut = [g for g in games if g.get("ending") is None and g["winner"] not in (1, 2)]
    print(f"{len(games)} games, {len(cut)} cut off ({100 * len(cut) / max(len(games), 1):.1f}%); "
          f"steps: median {int(np.median([g['steps'] for g in games]))}, max {max(g['steps'] for g in games)}")
    by_focal, by_pair, tot_focal = collections.Counter(), collections.Counter(), collections.Counter()
    for g in games:
        focal = next(v for v in g["seats"].values() if v.startswith("r"))
        tot_focal[focal] += 1
    for g in cut:
        focal = next(v for v in g["seats"].values() if v.startswith("r"))
        by_focal[focal] += 1
        by_pair[(g["seats"]["1"], g["decks"][0], g["seats"]["2"], g["decks"][1])] += 1
    print("cut-off games by focal agent (cut / played):",
          {k: f"{by_focal[k]}/{tot_focal[k]}" for k in sorted(tot_focal)})
    print("most frequent cut-off pairings (seat 1 agent, deck, seat 2 agent, deck):")
    for k, v in by_pair.most_common(12):
        print(f"  {v:3d}  {k}")
    for f in out.glob("r*.bin"):
        f.unlink()

    if args.export:
        d = Path(args.export)
        d.mkdir(parents=True, exist_ok=True)
        for k in range(n_agents):
            export_policy(pilots.nets[k], d / f"agent{k}.onnx", "tokens")
        json.dump(strategies, open(d / "strategies.json", "w"))
        print(f"exported {n_agents} agents and {len(strategies)} strategies to {d}")


if __name__ == "__main__":
    main()
