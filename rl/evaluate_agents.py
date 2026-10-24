"""Evaluation of a population of (deck, pilot) agents (rl/metagame.py checkpoints, and rl/tournament.py's
from the `pre-simplify` tag). Training never imports this; the archived lists and SimpleBot enter here only.

  simplebot   each agent's pilot on its own deck against SimpleBot on the same deck (env/tools/evaluate.js
              --mirror), greedy
  meta        round-robin of the agents, each deck piloted by its own agent, greedy: win matrix, Nash
              equilibrium and its support, cyclic triads (intransitivity)
  archived    every agent's deck against each of the 24 archived lists, both piloted by one common pilot
              (--common), so the decks are compared without the pilots' differences
  sb_archived the same panel with SimpleBot on both sides (log #85): a pilot that shares no habits with the
              learned ones (#69: pilot-v2 also leaves draw Trainers unplayed, which favours Trainer-light decks)
  answer key  each deck's nearest archived archetype by card overlap, the field staples it plays, and its
              card classes

Run: .venv/Scripts/python -m rl.evaluate_agents --checkpoint runs/meta-dev/checkpoint.pt \
        --common runs/pilot-v2/model_it00349.pt --out runs/meta-dev/eval.json
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import torch

from rl import limits
from rl.answer_key import label_of
from rl.decks import Pool, archived_decks, deck_shape, overlap
from rl.gpu_matrix import GpuMatrix
from rl.metagame import recent_score
from rl.nash import solve
from rl.remote import RemotePool
from rl.train import export_policy, token_net

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
    ap.add_argument("--checkpoint", required=True,
                    help="a metagame checkpoint (population and one net) or a tournament one (agents and their nets)")
    ap.add_argument("--top", type=int, default=12, help="a population is evaluated on its best decks only")
    ap.add_argument("--common", default="runs/pilot-v2/model_it00349.pt", help="pilot for the archived-list panel")
    ap.add_argument("--games", type=int, default=32, help="games per pair, meta and archived panel")
    ap.add_argument("--simplebot-games", type=int, default=200)
    ap.add_argument("--skip", nargs="*", default=[], choices=["simplebot", "meta", "archived", "sb_archived"])
    ap.add_argument("--sb-archived-games", type=int, default=240, help="sb_archived: games per deck (both directions)")
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    limits.apply(device, args.workers)
    pool = Pool()
    archived = archived_decks(pool)
    st = torch.load(ROOT / args.checkpoint, map_location=device, weights_only=False)
    agents = st["agents"]
    if "population" in st:                             # one pilot for every deck: its best decks by recent results
        def score(a):                                  # the judged score with --judge-search (log #148)
            return recent_score(a, 0.0)
        best = sorted(range(len(agents)), key=lambda i: -score(st["population"][i]))[:args.top]
        agents = [{**agents[i], "score": round(score(st["population"][i]), 4)} for i in best]
    N = len(agents)
    decks = [{"name": f"a{a['id']}", "cards": a["deck"]} for a in agents]
    vecs = [pool.vector(a["deck"]) for a in agents]
    out = {"checkpoint": args.checkpoint, "iter": st.get("iter", st.get("round")), "agents": []}

    rp = RemotePool(args.workers)
    rp.pace = 0.25
    info = rp.ask_all([{"cmd": "info"}] * args.workers)[0]

    def load(state, cfg):
        net = token_net(cfg, info).to(device)          # any architecture options the checkpoint has (rl/lab.py)
        net.load_state_dict(state)
        return net.eval()
    if "net" in st:
        shared = load(st["net"], st["config"])
        models = {k: shared for k in range(N)}
    else:
        models = {k: load(sd, st["config"]) for k, sd in enumerate(st["nets"])}
    try:
        gm = GpuMatrix.attach(models[0], rp, args.workers, device=device)
        if "meta" not in args.skip:
            W, G, _ = gm.play(decks, args.games, args.seed, slots=list(range(N)), models=models)
            P = W / np.maximum(G, 1)
            sigma, _ = solve(P)
            out["meta"] = {"P": np.round(P, 4).tolist(), "nash": np.round(sigma, 4).tolist(),
                           "support": [int(i) for i in np.nonzero(sigma > 1e-4)[0]],
                           "standings": np.round((P.sum(1) - 0.5) / (N - 1), 4).tolist(),
                           "cyclic_triads": cyclic_triads(P, G), **gm.last}
        if "archived" not in args.skip:
            c = torch.load(ROOT / args.common, map_location=device, weights_only=False)
            models[N] = load(c["model"] if "model" in c else c["net"], c["config"])   # rl.train or rl.metagame
            panel = decks + [{"name": n, "cards": pool.names(v)} for n, v in archived]
            pairs = [(i, N + j) for i in range(N) for j in range(len(archived))]
            W, G, _ = gm.play(panel, args.games, args.seed + 1, pairs=pairs, slots=[N] * len(panel), models=models)
            vs = (W / np.maximum(G, 1))[:N, N:]
            out["archived"] = {"common": args.common, "vs_field": np.round(vs.mean(1), 4).tolist(),
                               "mean": round(float(vs.mean()), 4), **gm.last}
    finally:
        rp.close()

    if "simplebot" not in args.skip:
        with tempfile.TemporaryDirectory() as tmp:
            for k in range(N):
                spec = export_policy(models[k], Path(tmp) / f"a{k}.onnx", "tokens")
                dfile, res = Path(tmp) / f"d{k}.json", Path(tmp) / f"e{k}.json"
                dfile.write_text(json.dumps([decks[k]]))
                subprocess.run(["node", str(ROOT / "env/tools/evaluate.js"), "--x", spec, "--y", "simplebot",
                                "--decks-file", str(dfile), "--mirror", "--games", str(args.simplebot_games),
                                "--workers", str(min(6, args.workers)), "--concurrency", "8", "--seed", str(args.seed + k),
                                "--json", str(res)], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
                r = json.load(open(res))
                out.setdefault("simplebot", []).append({"win": round(r["all"]["xWinRate"], 4), "ci95": round(r["all"]["ci95"], 4)})

    if "sb_archived" not in args.skip:
        # Each deck as D1 against the 24 lists as D2 (evaluate.js cycles D2; even games SimpleBot X has D1, odd D2,
        # so D1's rate is dir1's for X and 1 - dir2's).
        arch = [{"name": n, "cards": pool.names(v)} for n, v in archived]
        with tempfile.TemporaryDirectory() as tmp:
            rates = []
            for k in range(N):
                dfile, res = Path(tmp) / f"sb{k}.json", Path(tmp) / f"sbr{k}.json"
                dfile.write_text(json.dumps([{"name": "agentdeck", "cards": decks[k]["cards"]}] + arch))
                subprocess.run(["node", str(ROOT / "env/tools/evaluate.js"), "--x", "simplebot", "--y", "simplebot",
                                "--decks-file", str(dfile), "--d1", "agentdeck", "--d2", "#", "--tokens",
                                "--games", str(args.sb_archived_games), "--workers", str(min(6, args.workers)),
                                "--concurrency", "8", "--seed", str(args.seed + 100 + k), "--json", str(res)],
                               cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
                r = json.load(open(res))
                d1, d2 = r["dir1"], r["dir2"]
                rates.append((d1["xWinRate"] * d1["n"] + (1 - d2["xWinRate"]) * d2["n"]) / max(d1["n"] + d2["n"], 1))
            out["sb_archived"] = {"vs_field": np.round(rates, 4).tolist(), "mean": round(float(np.mean(rates)), 4),
                                  "games_per_deck": args.sb_archived_games}

    for k, v in enumerate(vecs):
        o = [overlap(v, x) for _, x in archived]
        nearest = int(np.argmax(o))
        plays = [s for s in STAPLES if v[[c["id"] for c in pool.cards if c["name"] == s]].sum() > 0]
        out["agents"].append({"agent": agents[k]["id"], "score": agents[k].get("score"), **deck_shape(pool, v),
                              "nearest": label_of(archived[nearest][0]), "overlap": round(o[nearest], 3), "staples": plays})
    print(json.dumps({k: v for k, v in out.items() if k != "agents"}, indent=None)[:2000])
    for a in out["agents"]:
        print(a)
    if args.out:
        Path(ROOT / args.out).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
