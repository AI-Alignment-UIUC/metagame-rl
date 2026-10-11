"""Cross-play of the final agents of several tournament runs (rl/tournament.py, log #59-63): an absolute
yardstick across runs, which within-run standings (always 0.5 on average) cannot give.

Two round-robins over every run's final (deck, network) strategies:
  own     each deck piloted by its own agent's network (deck and pilot together)
  common  every deck piloted by one common network (--common, e.g. the shared starting checkpoint): the
          decks alone, without the pilots' differences
Per run: mean win rate of its agents against the other runs' agents in each matrix, its share of the
equilibrium over all strategies, and its best agent. Greedy play, as the tournaments measure.

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/tournament_crossplay.py --runs runs/tourn-3 runs/tourn-6 \
        runs/tourn-9 runs/tourn-3-s2 --common runs/pilot-v2/model_it00349.pt --out notes/data/eval/tournament_crossplay.json
"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from rl import limits
from rl.decks import Pool
from rl.gpu_matrix import GpuMatrix
from rl.nash import solve
from rl.remote import RemotePool
from rl.train import build_model

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--common", required=True, help="checkpoint that pilots every deck in the 'common' matrix")
    ap.add_argument("--games", type=int, default=32)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    limits.apply(device, args.workers)
    rp = RemotePool(args.workers)
    rp.pace = 0.25
    info = rp.ask_all([{"cmd": "info"}] * args.workers)[0]
    pool = Pool()

    def load(state, cfg):
        net = build_model(SimpleNamespace(model="tokens", d=cfg["d"], tok_layers=cfg["layers"], heads=cfg["heads"],
                                          count_features=cfg.get("count_features", False),
                                          cross_layers=cfg.get("cross_layers", 1), cand_self=cfg.get("cand_self", 0),
                                          n_agents=0), info).to(device)
        net.load_state_dict(state)
        return net.eval()

    strategies, models = [], {}
    for r in args.runs:
        st = torch.load(ROOT / r / "checkpoint.pt", map_location=device, weights_only=False)
        for a, sd in zip(st["agents"], st["nets"]):
            k = len(strategies)
            models[k] = load(sd, st["config"])
            strategies.append({"run": Path(r).name, "agent": a["id"], "round": st["round"], "cards": a["deck"],
                               "name": f"{Path(r).name}/a{a['id']}"})
    c = torch.load(ROOT / args.common, map_location=device, weights_only=False)
    common_slot = len(strategies)
    models[common_slot] = load(c["model"], c["config"])
    decks = [{"name": s["name"], "cards": s["cards"]} for s in strategies]
    n = len(decks)
    gm = GpuMatrix.attach(models[0], rp, args.workers, device=device)
    out = {"strategies": [{k: v for k, v in s.items() if k != "cards"} for s in strategies], "games_per_pair": args.games}
    runs = sorted({s["run"] for s in strategies}, key=[Path(r).name for r in args.runs].index)
    for label, slots in (("own", list(range(n))), ("common", [common_slot] * n)):
        W, G, _ = gm.play(decks, args.games, args.seed, slots=slots, models=models)
        P = W / np.maximum(G, 1)
        sigma, _ = solve(P)
        per_run = {}
        for run in runs:
            mine = [i for i, s in enumerate(strategies) if s["run"] == run]
            other = [j for j, s in enumerate(strategies) if s["run"] != run]
            rates = [float(P[i, other].mean()) for i in mine]
            per_run[run] = {"mean_vs_other_runs": round(float(np.mean(rates)), 4),
                            "best_vs_other_runs": round(max(rates), 4), "worst_vs_other_runs": round(min(rates), 4),
                            "equilibrium_share": round(float(sigma[mine].sum()), 4),
                            "best_agent": strategies[mine[int(np.argmax(rates))]]["name"]}
        out[label] = {"P": np.round(P, 3).tolist(), "sigma": np.round(sigma, 4).tolist(), "per_run": per_run,
                      "games": gm.last}
        print(f"{label}: " + "; ".join(f"{run} mean {v['mean_vs_other_runs']:.3f} (best {v['best_vs_other_runs']:.3f}), "
                                         f"equilibrium {v['equilibrium_share']:.2f}" for run, v in per_run.items()), flush=True)
    rp.close()
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        json.dump(out, open(args.out, "w"), indent=1)


if __name__ == "__main__":
    main()
