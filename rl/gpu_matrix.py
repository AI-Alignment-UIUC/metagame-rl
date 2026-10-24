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


def load_policy(path: str, device: str, overrides: dict = None):
    """A checkpoint (.pt) as a model on `device`, and the encoding its workers must use. overrides: config keys to
    change (e.g. a new value readout, log #77); weights the checkpoint lacks then keep their initialisation."""
    state = torch.load(ROOT / path, map_location="cpu", weights_only=False)
    cfg = {**state["config"], **(overrides or {})}
    if cfg.get("kind") == "TokenPointerNet":
        from rl.token_model import build_token_model
        m = build_token_model(str(ROOT / "notes/data/cards/pool.json"), str(ROOT / "notes/data/cards/text_emb.npy"),
                              cfg["n_names"], cfg["glob_f"], cfg["slot_f"], cfg["max_tok"], cfg["max_cand"],
                              d=cfg["d"], layers=cfg["layers"], heads=cfg["heads"],
                              count_features=cfg.get("count_features", False),
                              cross_layers=cfg.get("cross_layers", 1), cand_self=cfg.get("cand_self", 0),
                              n_agents=cfg.get("n_agents", 0), card_inputs=cfg.get("card_inputs", "all"),
                              deck_tokens=cfg.get("deck_tokens", True), slot_bind=cfg.get("slot_bind", False),
                              ability_text=cfg.get("ability_text", False), deck_mode=cfg.get("deck_mode", "joint"),
                              deck_layers=cfg.get("deck_layers", 1), history=cfg.get("history", 0),
                              memory=cfg.get("memory", "none"), value_tower=cfg.get("value_tower", 0),
                              value_query=cfg.get("value_query", 0), aux_heads=cfg.get("aux_heads", 0))
        enc = "tokens"
    else:
        from rl.model import build
        m = build(cfg)
        enc = "identity"
    missing, unexpected = m.load_state_dict(state["model"] if "model" in state else state["net"],   # rl.train or rl.metagame
                                            strict=not overrides)
    assert not unexpected and all(k.startswith(("vquery", "vcross.", "vblocks.", "ln_v.", "aux_head.")) for k in missing), (missing, unexpected)
    return m.to(device).eval(), enc


def history_of(models: dict) -> int:
    """The action-history window the workers must encode (env/tokens.js): the longest any of the models reads."""
    return max([int(getattr(m, "cfg", {}).get("history", 0) or 0) for m in models.values()] + [0])


def jobs_for(n: int, games: int, seed: int, new: int = 0, pairs: list = None, pair_keys: list = None) -> list:
    """Game g of pair p gets seed SEED * 1000003 + p * games + g, or pair_keys[p] in place of p: pairs with
    equal keys (the same deck pair under other pilots) then get the same deals."""
    if pairs is None:
        pairs = [(i, j) for i in range(n) for j in range(i + 1, n) if not new or j >= n - new]
    keys = list(range(len(pairs))) if pair_keys is None else [int(k) for k in pair_keys]
    assert len(keys) == len(pairs) and min(keys, default=0) >= 0
    assert 0 <= seed * 1000003 + (max(keys, default=-1) + 1) * games < 2 ** 53, "job seeds must stay exact in JavaScript"
    jobs = []
    for (i, j), key in zip(pairs, keys):
        for g in range(games):
            jobs.append({"i": i, "j": j, "iSeat": 1 if g % 2 == 0 else 2, "seed": seed * 1000003 + key * games + g})
    return jobs


def shards_for(jobs: list, workers: int, keyed: bool = False) -> list:
    """Rounds of one job list per worker, interleaved so every worker gets every pair. env/remote_worker.js
    matches results to jobs by seed, so with keyed (repeated) seeds no worker may hold a seed twice: the jobs
    go sorted by seed (ties shuffled) and dealt round robin, each seed at most `workers` times a round."""
    if not keyed:
        return [[jobs[w::workers] for w in range(workers)]]
    seen, rounds = {}, {}
    for k in np.random.default_rng(0).permutation(len(jobs)):
        s = jobs[k]["seed"]
        rounds.setdefault(seen.get(s, 0) // workers, []).append(jobs[k])
        seen[s] = seen.get(s, 0) + 1
    out = []
    for r in sorted(rounds):
        js = sorted(rounds[r], key=lambda j: j["seed"])
        out.append([js[w::workers] for w in range(workers)])
    return out


class GpuMatrix:
    """Keeps the workers and the model loaded across PSRO iterations."""

    def __init__(self, policy: str, workers: int = 14, concurrency: int = 64, greedy: bool = True, device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        workers = limits.cap_workers(workers)
        limits.apply(self.device, workers)
        self.model, self.encoding = load_policy(policy, self.device)
        self.pool = RemotePool(workers)
        self.workers, self.concurrency, self.greedy = workers, concurrency, greedy

    @classmethod
    def attach(cls, model, pool: RemotePool, workers: int, encoding: str = "tokens", concurrency: int = 64,
               greedy: bool = True, device: str = None):
        """A matrix over a model and workers someone else owns (rl/coevolve.py: the learner itself,
        and the trainer's workers). Don't close() it; the owner closes the pool."""
        self = cls.__new__(cls)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model, self.encoding, self.pool = model, encoding, pool
        self.workers, self.concurrency, self.greedy = workers, concurrency, greedy
        return self

    def play(self, decks: list, games: int, seed: int, new: int = 0, pairs: list = None, value_at_turn: int = 0,
             slots: list = None, models: dict = None, pair_keys: list = None, round_turns=0, search: dict = None):
        """decks: [{name, cards}] -> (wins, games, steps) as [n, n] arrays; mirrors filled with 0.5.
        `pairs` [(i, j)] plays only those pairs instead of all (or all involving the last `new`).
        slots / models (rl/league.py): deck i is piloted by model slot slots[i] of `models` instead of
        slot 0 = self.model in both seats. pair_keys (one int per pair): deal seeds by key (jobs_for). round_turns: every
        game under the 2000 round rule (T or [a, b]; env/game.js, log #160), a win on Prizes at time counted as a win.
        search ({k, dets, maxSteps, concurrency, crn}; C03, log #162): every game with both seats played by
        env/agents.js PolicySearchAgent over its deck's model slot on the GPU (env/remote_worker.js judgeSearch), the
        summed searchStats in self.last."""
        n = len(decks)
        jobs = jobs_for(n, games, seed, new, pairs, pair_keys)
        if search:
            for j in jobs:
                j["search"] = True
        t0 = time.time()
        replies = []
        for shards in shards_for(jobs, self.workers, pair_keys is not None):
            msgs = [{"cmd": "games", "encoding": self.encoding, "decks": decks, "jobs": s, "greedy": self.greedy,
                     **({"judgeSearch": {**search, "seed": (seed * 7919 + len(replies)) * 64 + w}} if search else {}),
                     "concurrency": self.concurrency, "valueAtTurn": value_at_turn, "history": history_of(models or {0: self.model}),
                     **({"slots": [int(x) for x in slots]} if slots is not None else {}),
                     **({"roundTurns": round_turns} if round_turns else {})} for w, s in enumerate(shards)]
            replies += self.pool.collect(msgs, models or {0: self.model}, self.device)   # fp32, as the ONNX pilot
        self.results = [x for rep in replies for x in rep["results"]]   # per game (with its job's seed), for analyses
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
        if search:
            st = [rep["searchStats"] for rep in replies if rep.get("searchStats")]
            self.last["search"] = {q: round(sum(x[q] for x in st), 1) for q in (st[0] if st else {})}
        return W, G, S

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
