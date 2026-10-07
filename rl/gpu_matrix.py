"""Matchup matrix with central GPU inference (plan item A5): env/tools/matrix.js, but the policy runs
once on the GPU for all workers' decisions instead of as a CPU ONNX session in every worker.

Same games as matrix.js: every unordered pair (or only those involving the last `new` decks)
plays `games` games, alternating which deck sits in seat 1, with seed SEED * 1000003 + k.
Draws and cut-off games count half. Greedy by default, as matrix.js runs the policy.

Run: .venv/Scripts/python -m rl.gpu_matrix --policy runs/a4-tok/model_it00249.pt \
        --decks-file runs/a5/population.json --games 100 --workers 14 --out matrix.json
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

from rl import limits
from rl.remote import RemotePool

ROOT = Path(__file__).resolve().parent.parent


def load_policy(path: str, device: str):
    """A checkpoint (.pt) as a model on `device`, and the encoding its workers must use."""
    state = torch.load(ROOT / path, map_location="cpu")
    cfg = state["config"]
    if cfg.get("kind") == "TokenPointerNet":
        from rl.token_model import build_token_model
        m = build_token_model(str(ROOT / "notes/data/cards/pool.json"), str(ROOT / "notes/data/cards/text_emb.npy"),
                              cfg["n_names"], cfg["glob_f"], cfg["slot_f"], cfg["max_tok"], cfg["max_cand"],
                              d=cfg["d"], layers=cfg["layers"], heads=cfg["heads"])
        enc = "tokens"
    else:
        from rl.model import build
        m = build(cfg)
        enc = "identity"
    m.load_state_dict(state["model"])
    return m.to(device).eval(), enc


def jobs_for(n: int, games: int, seed: int, new: int = 0, pairs: list = None) -> list:
    if pairs is None:
        pairs = [(i, j) for i in range(n) for j in range(i + 1, n) if not new or j >= n - new]
    assert 0 <= seed * 1000003 + len(pairs) * games < 2 ** 53, "job seeds must stay exact in JavaScript"
    jobs, k = [], 0
    for i, j in pairs:
        for g in range(games):
            jobs.append({"i": i, "j": j, "iSeat": 1 if g % 2 == 0 else 2, "seed": seed * 1000003 + k})
            k += 1
    return jobs


class GpuMatrix:
    """Keeps the workers and the model loaded across PSRO iterations."""

    def __init__(self, policy: str, workers: int = 14, concurrency: int = 64, greedy: bool = True, device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        workers = limits.cap_workers(workers)
        limits.apply(self.device, workers)
        self.model, self.encoding = load_policy(policy, self.device)
        self.pool = RemotePool(workers)
        self.workers, self.concurrency, self.greedy = workers, concurrency, greedy

    def play(self, decks: list, games: int, seed: int, new: int = 0, pairs: list = None, value_at_turn: int = 0):
        """decks: [{name, cards}] -> (wins, games, steps) as [n, n] arrays; mirrors filled with 0.5.
        `pairs` [(i, j)] plays only those pairs instead of all (or all involving the last `new`)."""
        n = len(decks)
        jobs = jobs_for(n, games, seed, new, pairs)
        shards = [jobs[w::self.workers] for w in range(self.workers)]   # interleaved: every worker gets every pair
        msgs = [{"cmd": "games", "encoding": self.encoding, "decks": decks, "jobs": s, "greedy": self.greedy,
                 "concurrency": self.concurrency, "valueAtTurn": value_at_turn} for s in shards]
        t0 = time.time()
        replies = self.pool.collect(msgs, {0: self.model}, self.device)   # fp32, as the ONNX pilot
        self.results = [x for rep in replies for x in rep["results"]]   # per game, for analyses
        W, G, S = np.zeros((n, n)), np.zeros((n, n)), np.zeros((n, n))
        errors = cut = 0
        endings = {}
        for r in (x for rep in replies for x in rep["results"]):
            i, j = r["i"], r["j"]
            iw = 1.0 if r["winner"] == r["iSeat"] else 0.0 if r["winner"] in (1, 2) else 0.5
            cut += iw == 0.5
            errors += bool(r.get("error"))
            if r.get("ending"):
                endings[r["ending"]] = endings.get(r["ending"], 0) + 1
            W[i, j] += iw; W[j, i] += 1 - iw
            G[i, j] += 1; G[j, i] += 1
            S[i, j] += r["steps"]; S[j, i] += r["steps"]
        np.fill_diagonal(W, games / 2)
        np.fill_diagonal(G, games)
        secs = time.time() - t0
        total = len(jobs)
        self.last = {"games": total, "seconds": round(secs, 1), "games_per_s": round(total / max(secs, 1e-9), 1),
                     "errors": errors, "cut": int(cut), "endings": endings, "decisions_per_game": round(float(np.triu(S, 1).sum()) / max(total, 1), 1)}
        return W, G, S

    def values(self, decks: list, pairs: list, openings: int, seed: int, states: bool = False,
               common_deals: bool = False):
        """The pilot's start-of-game value v(a, b) for deck a against deck b, averaged over
        `openings` deals (forward passes only, no games). pairs: [(a, b)] -> array [len(pairs)].
        Sent in chunks of at most `chunk` deals: all of a chunk's states go through one forward pass.

        states=True also returns the states the values were read at, one per deal in the order
        (pair, opening): {"live": [J] (0 if the game ended in setup), "pooled": [J, d] (the encoder's
        token 0), and the five token inputs}, for deck embeddings and the edit head (rl/deck_head.py).

        common_deals=True seeds each deal by (opponent b, opening) instead of by the pair's position,
        so every deck facing b gets the same deals (common random numbers): the same deck always
        scores the same, and two decks' scores differ by the decks, not by the luck of the deal."""
        key = (lambda k, b: b) if common_deals else (lambda k, b: k)
        jobs = [{"a": a, "b": b, "seed": seed * 1000003 + key(k, b) * openings + o, "pair": k, "job": k * openings + o}
                for k, (a, b) in enumerate(pairs) for o in range(openings)]
        tot = np.zeros(len(pairs))
        out = None
        chunk = 4096
        for c in range(0, len(jobs), chunk):
            part = jobs[c:c + chunk]
            shards = [part[w::self.workers] for w in range(self.workers)]
            msgs = [{"cmd": "values", "decks": decks, "jobs": sh} for sh in shards]
            self.pool.capture = {} if states else None
            try:
                replies = self.pool.collect(msgs, {0: self.model}, self.device)
                cap, self.pool.capture = self.pool.capture, None
            finally:
                self.pool.capture = None
            for w, (sh, rep) in enumerate(zip(shards, replies)):
                for j, v in zip(sh, rep["values"]):
                    tot[j["pair"]] += v
                if not states or not sh:
                    continue
                got = cap.get(w, [])
                arrs = {k: np.concatenate([g[0][k] for g in got]) for k in got[0][0]} if got else {}
                pooled = np.concatenate([g[1] for g in got]) if got else None
                live = [j for j, l in zip(sh, rep["live"]) if l]
                assert len(live) == (len(pooled) if got else 0), "captured states do not match the live deals"
                if out is None and got:
                    out = {"live": np.zeros(len(jobs), np.uint8),
                           "pooled": np.zeros((len(jobs), pooled.shape[1]), np.float32),
                           **{k: np.zeros((len(jobs),) + a.shape[1:], a.dtype) for k, a in arrs.items()}}
                idx = np.array([j["job"] for j in live], dtype=np.int64)
                if len(idx):
                    out["live"][idx] = 1
                    out["pooled"][idx] = pooled
                    for k, a in arrs.items():
                        out[k][idx] = a
        return (tot / openings, out) if states else tot / openings

    def close(self):
        self.pool.close()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    ap.add_argument("--decks-file", required=True)
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--new", type=int, default=0)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--concurrency", type=int, default=64)
    ap.add_argument("--sample", action="store_true", help="sample actions instead of greedy")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    decks = json.load(open(args.decks_file, encoding="utf-8"))
    gm = GpuMatrix(args.policy, args.workers, args.concurrency, greedy=not args.sample)
    try:
        W, G, S = gm.play(decks, args.games, args.seed, args.new)
    finally:
        gm.close()
    print(json.dumps(gm.last))
    if args.out:
        json.dump({"agent": args.policy, "gamesPerPair": args.games, "seed": args.seed, "decks": [d["name"] for d in decks],
                   "wins": W.tolist(), "games": G.tolist(), "steps": S.tolist()}, open(args.out, "w"), indent=1)


if __name__ == "__main__":
    main()
