"""How much is each group of Trainers worth to a player? (log #91; evaluation only)

Each deck plays a copy of itself with one group of its Trainers replaced by its most common basic Energy, the same
player on both sides, both seats. A player that gets nothing from the group scores 0.5 against the copy without it;
one that plays the group well scores above, and one that is better off with the Energy (the drafted decks' choice)
scores below. Learned pilots get the same deals per deck (pair keys); SimpleBot, a hand-written heuristic that plays
Trainers by rule, is the yardstick of what the cards are worth to a simple, consistent player. The groups are by card
name, a diagnostic only: nothing here enters training.

  --decks archived            the 24 archived lists (26-34 Trainers each)
  --decks <metagame ckpt>     a population's best decks by recent results (--top)

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/trainer_value.py --decks archived \
        --players runs/lab/main/seg_0220.pt runs/pilot-v2/model_it00349.pt simplebot --out notes/data/eval/trainer_value.json
"""
import argparse
import collections
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import torch

from rl import limits
from rl.decks import Pool, archived_decks
from rl.gpu_matrix import GpuMatrix, load_policy
from rl.remote import RemotePool
from rl.train import round_turns

ROOT = Path(__file__).resolve().parents[2]
GROUPS = {
    "draw": ("Professor Oak", "Bill", "Gambler"),
    "search": ("Computer Search", "Item Finder", "Energy Retrieval", "Nightly Garbage Run", "Energy Search",
               "Pokémon Trader", "Pokémon Breeder"),
    "disrupt": ("Energy Removal", "Super Energy Removal", "Rocket's Sneak Attack", "Lass", "Goop Gas Attack",
                "Imposter Oak's Revenge"),
    "tempo": ("Gust of Wind", "PlusPower", "Scoop Up", "Switch", "Defender", "Potion", "Super Potion",
              "Pokémon Center"),
}


def variants(pool: Pool, decks: list, groups: list) -> tuple:
    """[base decks] + [each base with a group's Trainers replaced by its most common basic Energy], and the pairs
    (base, variant, group, base index); a group the deck does not play makes no pair."""
    card = {c["fullName"]: c for c in pool.cards}
    out, pairs = list(decks), []
    for k, d in enumerate(decks):
        basics = collections.Counter(x for x in d["cards"] if card[x]["superType"] == 3 and card[x]["energyType"] == 0)
        if not basics:
            continue
        fill = basics.most_common(1)[0][0]
        for g in groups:
            hit = (lambda c: c["superType"] == 2) if g == "all" else (lambda c, names=GROUPS[g]: c["name"] in names)
            cards = [fill if hit(card[x]) else x for x in d["cards"]]
            n = sum(a != b for a, b in zip(cards, d["cards"]))
            if n:
                pairs.append({"base": k, "variant": len(out), "group": g, "replaced": n})
                out.append({"name": f"{d['name']}-{g}", "cards": cards})
    return out, pairs


def play_pilot(path: str, decks: list, pairs: list, games: int, seed: int, workers: int, device: str,
               rounds=0, search: dict = None) -> list:
    model, enc = load_policy(path, device)
    rp = RemotePool(workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, workers, device=device)
        W, G, _ = gm.play(decks, games, seed, pairs=[(p["base"], p["variant"]) for p in pairs],
                          pair_keys=[p["base"] for p in pairs], round_turns=rounds, search=search)
        print(path, gm.last, flush=True)
    finally:
        rp.close()
    return [float(W[p["base"], p["variant"]] / max(G[p["base"], p["variant"]], 1)) for p in pairs]


def play_simplebot(decks: list, pairs: list, games: int, seed: int, workers: int) -> list:
    """evaluate.js plays D1 as X in even games and D2 in odd ones, so D1's rate is dir1's for X and 1 - dir2's."""
    rates = []
    with tempfile.TemporaryDirectory() as tmp:
        for n, p in enumerate(pairs):
            dfile, res = Path(tmp) / "d.json", Path(tmp) / "r.json"
            dfile.write_text(json.dumps([{**decks[p["base"]], "name": "base"}, {**decks[p["variant"]], "name": "variant"}]))
            subprocess.run(["node", str(ROOT / "env/tools/evaluate.js"), "--x", "simplebot", "--y", "simplebot",
                            "--decks-file", str(dfile), "--d1", "base", "--d2", "variant", "--tokens",
                            "--games", str(games), "--workers", str(workers), "--concurrency", "8",
                            "--seed", str(seed + n), "--json", str(res)], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
            r = json.load(open(res))
            d1, d2 = r["dir1"], r["dir2"]
            rates.append((d1["xWinRate"] * d1["n"] + (1 - d2["xWinRate"]) * d2["n"]) / max(d1["n"] + d2["n"], 1))
    return rates


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--decks", default="archived", help="archived, or a metagame checkpoint (its best --top decks)")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--players", nargs="+", required=True, help="checkpoints (.pt) and/or simplebot")
    ap.add_argument("--groups", nargs="+", default=["all", "draw", "search", "disrupt", "tempo"])
    ap.add_argument("--games", type=int, default=64, help="games per deck pair (both seats)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--round-turns", default="0", help='learned pilots only: the 2000 round rule in every game, "T" or '
                    '"A-B" (log #160; a win on Prizes at time counts as a win); default off')
    ap.add_argument("--search", default="", help='learned pilots only: both seats searched on the GPU (C03, log #162), '
                    '"K:DETS" or "K:DETS:crn"; default off')
    ap.add_argument("--search-conc", type=int, default=16, help="searched games at once per worker")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    rounds = round_turns(args.round_turns)
    sp = args.search.split(":") if args.search else None
    search = {"k": int(sp[0]), "dets": int(sp[1]), "maxSteps": 40, "concurrency": args.search_conc,
              "crn": len(sp) > 2 and sp[2] == "crn"} if sp else None
    device = "cuda" if torch.cuda.is_available() else "cpu"
    workers = limits.cap_workers(args.workers)
    limits.apply(device, workers)
    pool = Pool()
    if args.decks == "archived":
        decks = [{"name": n, "cards": pool.names(v)} for n, v in archived_decks(pool)]
    else:
        st = torch.load(ROOT / args.decks, map_location="cpu", weights_only=False)
        score = lambda a: a["sum"] / a["n"] if a.get("n") else 0.0
        best = sorted(st["population"], key=lambda a: -score(a))[:args.top]
        decks = [{"name": f"a{a['id']}", "cards": a["deck"]} for a in best]
    alld, pairs = variants(pool, decks, args.groups)
    out = {"decks": args.decks, "games": args.games, "round_turns": args.round_turns, "search": args.search,
           "pairs": pairs, "players": {}}
    for pl in args.players:
        s = (play_simplebot(alld, pairs, args.games, args.seed, min(6, workers)) if pl == "simplebot"
             else play_pilot(pl, alld, pairs, args.games, args.seed, workers, device, rounds, search))
        rows = {}
        for g in args.groups:
            x = np.array([v for v, p in zip(s, pairs) if p["group"] == g])
            if len(x):
                se = float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else 0.5
                rows[g] = {"decks": len(x), "score": round(float(x.mean()), 4), "ci": [round(float(x.mean() - 1.96 * se), 4),
                           round(float(x.mean() + 1.96 * se), 4)], "replaced": round(float(np.mean(
                           [p["replaced"] for p in pairs if p["group"] == g])), 1)}
        out["players"][pl] = {"by_group": rows, "per_pair": [round(v, 4) for v in s]}
        print(pl, json.dumps(rows), flush=True)
    if args.out:
        Path(ROOT / args.out).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
