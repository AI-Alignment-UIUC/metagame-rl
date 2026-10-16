"""Is the pilot leaving value on the table by attacking before drawing? (log #69; evaluation only)

The population's pilot plays against itself on the population's best decks, one side with a hand-written
rule on top: whenever one of the listed draw Trainers can be played, play it (greedy otherwise). If the rule
side wins clearly, the pilot's turn order costs games, and something that sees the rest of the turn (search,
whole-turn choices, better credit) would gain it back; if not, drawing first is worth little in this field.
The rule is a diagnostic; it never enters training.

  bill  Bill only
  draw  Bill, Professor Oak, Computer Search

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/draw_first.py --checkpoint runs/meta-99/checkpoint.pt \
        --out notes/data/eval/draw_first_meta99.json
"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
import torch.nn as nn

from rl import limits
from rl.decks import Pool
from rl.gpu_matrix import GpuMatrix
from rl.remote import RemotePool
from rl.train import build_model

ROOT = Path(__file__).resolve().parents[2]
TRAINER = 5
RULES = {"bill": ("Bill BS",), "draw": ("Bill BS", "Professor Oak BS", "Computer Search BS")}


class DrawFirst(nn.Module):
    """The pilot, with any playable card of `ids` played first."""

    def __init__(self, net, ids):
        super().__init__()
        self.net = net
        self.register_buffer("ids", torch.tensor(sorted(ids)))

    def forward(self, tok_card, tok_kind, tok_aux, glob, slots, cand, n_cand):
        logits, value = self.net(tok_card, tok_kind, tok_aux, glob, slots, cand, n_cand)
        c = cand.long().view(cand.shape[0], -1, 6)
        hit = (c[..., 0] == TRAINER) & torch.isin(c[..., 1], self.ids.to(c.device))
        hit &= torch.arange(c.shape[1], device=c.device)[None] < n_cand.long()[:, None]
        return logits + 1e4 * hit.float(), value


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--games", type=int, default=16, help="games per (rule deck, plain deck) pair")
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--seed", type=int, default=9)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    limits.apply(device, args.workers)
    pool = Pool()
    st = torch.load(ROOT / args.checkpoint, map_location=device, weights_only=False)
    pop = st["population"]
    score = [a["sum"] / a["n"] if a.get("n") else a.get("last", 0.0) for a in pop]
    best = sorted(range(len(pop)), key=lambda i: -score[i])[:args.top]
    K = len(best)
    rp = RemotePool(args.workers)
    rp.pace = 0.25
    info = rp.ask_all([{"cmd": "info"}] * args.workers)[0]
    cfg = st["config"]
    net = build_model(SimpleNamespace(model="tokens", d=cfg["d"], tok_layers=cfg["layers"], heads=cfg["heads"],
                                      count_features=cfg.get("count_features", False), cross_layers=cfg.get("cross_layers", 1),
                                      cand_self=cfg.get("cand_self", 0)), info).to(device)
    net.load_state_dict(st["net"])
    net.eval()
    out = {"checkpoint": args.checkpoint, "iter": st.get("iter"), "decks": [pop[i]["id"] for i in best]}
    try:
        gm = GpuMatrix.attach(net, rp, args.workers, device=device)
        for r, names in RULES.items():
            models = {0: net, 1: DrawFirst(net, [pool.id[n] for n in names]).to(device).eval()}
            decks = [{"name": f"p{k}", "cards": pop[i]["deck"]} for k, i in enumerate(best)] + \
                    [{"name": f"r{k}", "cards": pop[i]["deck"]} for k, i in enumerate(best)]
            pairs = [(K + i, j) for i in range(K) for j in range(K)]          # rule side on deck i, plain on deck j
            W, G, _ = gm.play(decks, args.games, args.seed, pairs=pairs, slots=[0] * K + [1] * K, models=models)
            w = sum(W[K + i, j] for i in range(K) for j in range(K))
            g = sum(G[K + i, j] for i in range(K) for j in range(K))
            p = w / g
            mirror = sum(W[K + i, i] for i in range(K)) / sum(G[K + i, i] for i in range(K))
            out[r] = {"win_rate": round(p, 4), "ci95": round(1.96 * np.sqrt(p * (1 - p) / g), 4), "games": int(g),
                      "mirror_win_rate": round(float(mirror), 4), **gm.last}
            print(r, json.dumps(out[r]), flush=True)
    finally:
        rp.close()
    if args.out:
        Path(ROOT / args.out).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
