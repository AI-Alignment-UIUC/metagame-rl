"""C78 (log #243): how far below the human lists are a population's best decks under the frozen pilot? The premise of the
metagame autoresearch loop (arm/): it can only close a gap its judge can see. Evaluation only.

Each population's 12 best decks (by their judged score, sum / n, as trainer_value.py --decks reads them) play the 24 human
lists, the same pilot on both seats, greedy, the 2000 round rule 20-45, 8 games a pair with seats alternating, fixed
deals. The readout is the mean over the 288 pairs of the deck's share of decisive games (arm/'s metric M).

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/probe_meta_premise.py --pilot runs/pilot/C49-sd/model_it00199.pt \
        --pops runs/screens/C52-h110.nf-c49sd199-s3/population_it0029.pt ... --out runs/probe/C78-premise/premise.json
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from rl import limits
from rl.decks import Pool, archived_decks
from rl.gpu_matrix import GpuMatrix, load_policy
from rl.remote import RemotePool

ROOT = Path(__file__).resolve().parents[2]


def best_decks(path: str, top: int) -> list:
    st = torch.load(ROOT / path, map_location="cpu", weights_only=False)
    score = lambda a: a["sum"] / a["n"] if a.get("n") else 0.0
    return [{"name": f"a{a['id']}", "cards": a["deck"]} for a in sorted(st["population"], key=lambda a: -score(a))[:top]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--pops", nargs="+", required=True)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--games", type=int, default=8)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=93)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    workers = limits.cap_workers(a.workers)
    limits.apply(device, workers)
    pool = Pool()
    lists = [{"name": n, "cards": pool.names(v)} for n, v in archived_decks(pool)]
    model, _ = load_policy(a.pilot, device)
    rp = RemotePool(workers)
    rp.pace = 0.25
    out = {"pilot": a.pilot, "games": a.games, "round_turns": [20, 45], "pops": {}}
    try:
        gm = GpuMatrix.attach(model, rp, workers, device=device)
        for path in a.pops:
            mine = best_decks(path, a.top)
            decks = mine + lists
            pairs = [(i, len(mine) + j) for i in range(len(mine)) for j in range(len(lists))]
            gm.play(decks, a.games, a.seed, pairs=pairs, pair_keys=[j for _, j in pairs], round_turns=[20, 45])
            wins, dec = {}, {}
            for r in gm.results:
                k = (r["i"], r["j"])
                if r["winner"] in (1, 2):
                    dec[k] = dec.get(k, 0) + 1
                    wins[k] = wins.get(k, 0) + (r["winner"] == r["iSeat"])
            share = np.array([wins.get(k, 0) / dec[k] for k in pairs if dec.get(k)])
            by_deck = [float(np.mean([wins.get((i, len(mine) + j), 0) / dec[(i, len(mine) + j)]
                                      for j in range(len(lists)) if dec.get((i, len(mine) + j))])) for i in range(len(mine))]
            shapes = [[sum(1 for c in d["cards"] if pool.cards[pool.id[c] - 1]["superType"] == s) for s in (1, 2, 3)]
                      for d in mine]
            out["pops"][path] = {"M": round(float(share.mean()), 4), "se_pairs": round(float(share.std(ddof=1) / np.sqrt(len(share))), 4),
                                 "by_deck": [round(x, 4) for x in by_deck], "shapes": shapes, "last": gm.last}
            print(path, json.dumps(out["pops"][path]), flush=True)
    finally:
        rp.close()
    (ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / a.out).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
