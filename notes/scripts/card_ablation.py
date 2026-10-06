"""Does the pilot get value from a card? (A5 diagnosis, log #32.)

For every archived deck that plays the card, a copy with all of them replaced by the deck's most
common basic Energy plays the original deck, seat-swapped, under the same pilot (greedy, GPU).
The original's win rate above 50% is what the card is worth to that pilot in that deck.

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/card_ablation.py --policy runs/a4-tok/model_it00249.pt \
        --games 200 --cards "Computer Search,Item Finder,Double Colorless Energy,Professor Oak" \
        --json notes/data/eval/card_ablation.json
"""
import argparse
import collections
import json

import numpy as np

from rl.decks import Pool, archived_decks
from rl.gpu_matrix import GpuMatrix


def cpu_play(args, decks, pairs):
    import os, subprocess, tempfile, time
    with tempfile.TemporaryDirectory() as d:
        df, of = os.path.join(d, "decks.json"), os.path.join(d, "out.json")
        json.dump(decks, open(df, "w"))
        t0 = time.time()
        subprocess.run(["node", "env/tools/matrix.js", "--agent", args.agent, "--decks-file", df, "--games", str(args.games),
                        "--workers", str(args.workers), "--seed", str(args.seed), "--pairs", ",".join(f"{i}-{j}" for i, j in pairs),
                        "--out", of], check=True, stdout=subprocess.DEVNULL)
        m = json.load(open(of))
        return np.array(m["wins"]), np.array(m["games"]), round(len(pairs) * args.games / (time.time() - t0), 1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", help="checkpoint (.pt) piloting both sides, on the GPU")
    ap.add_argument("--cards", required=True, help="comma-separated card names (all printings)")
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--seed", type=int, default=41)
    ap.add_argument("--agent", help="a matrix.js agent spec (e.g. simplebot) on CPU workers instead of --policy on the GPU")
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    pool = Pool()
    field = [(n, pool.names(v)) for n, v in archived_decks(pool)]
    gm = GpuMatrix(args.policy, args.workers) if not args.agent else None
    out = {}
    try:
        for card in [c.strip() for c in args.cards.split(",")]:
            decks, pairs, rows = [], [], []
            for name, cards in field:
                hit = [c for c in cards if pool.name[pool.id[c]] == card]
                if not hit:
                    continue
                energy = collections.Counter(c for c in cards if pool.basic_energy[pool.id[c]]).most_common(1)[0][0]
                cut = [energy if pool.name[pool.id[c]] == card else c for c in cards]
                pairs.append((len(decks), len(decks) + 1))
                decks += [{"name": name, "cards": cards}, {"name": name + " -" + card, "cards": cut}]
                rows.append({"deck": name, "copies": len(hit), "filler": energy})
            if not pairs:
                print(f"{card}: in no archived deck")
                continue
            if gm:
                W, G, _ = gm.play(decks, args.games, args.seed, pairs=pairs)
                speed = gm.last["games_per_s"]
            else:
                W, G, speed = cpu_play(args, decks, pairs)
            for r, (i, j) in zip(rows, pairs):
                r["original_win"] = float(W[i, j] / G[i, j])
            w = np.array([r["original_win"] for r in rows])
            se = np.sqrt(w.mean() * (1 - w.mean()) / (len(w) * args.games))
            out[card] = {"decks": len(rows), "mean_original_win": float(w.mean()), "se": float(se), "rows": rows}
            print(f"{card:26s} in {len(rows):2d} decks: original beats the cut deck {100 * w.mean():.1f}% ± {100 * 1.96 * se:.1f} "
                  f"(per deck {100 * w.min():.0f}-{100 * w.max():.0f}%), {speed} games/s", flush=True)
    finally:
        if gm:
            gm.close()
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
