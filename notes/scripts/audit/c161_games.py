"""C161 (runs/probe/C161-search-disagreement/record.md): the loop's pilot (C127 s16, iteration 29) on its own population
(population_it0029.pt, 99 decks, uniformly random ordered pairs as the loop draws them, seeds alternating), greedy on both seats, round
rule [20, 45], through notes/scripts/audit/c161_worker.js: at a seeded share --p of the Trainer-playable main-phase decisions (at most
--max a worker) C135's SV search is asked on the side and both choices are logged. Evaluation only. Output:
runs/probe/C161-search-disagreement/decisions<tag>.jsonl (one line a searched decision; .accept with --keep) and results<tag>.json.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/audit/c161_games.py --n 24 --p 0.2 --max 20 --keep 20 --workers 1 --tag _accept
"""
import argparse
import json
import os
import random
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[3]
import rl.remote as R                                                   # noqa: E402
from rl.gpu_matrix import load_policy, history_of, chain_of, canon_of  # noqa: E402

LOOP = "runs/screens/C127-R1-K-paired-ledger-s16/population_it0029.pt"

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=400)
ap.add_argument("--p", type=float, default=1.0)
ap.add_argument("--max", type=int, default=500, help="searched decisions a worker at most")
ap.add_argument("--keep", type=int, default=0, help="acceptance: re-search a worker's first N searched states with a fresh agent")
ap.add_argument("--seed", type=int, default=161)
ap.add_argument("--workers", type=int, default=6)
ap.add_argument("--concurrency", type=int, default=16)
ap.add_argument("--tag", default="")
a = ap.parse_args()
torch.set_num_threads(4)

OUT = ROOT / "runs/probe/C161-search-disagreement"
pop = torch.load(ROOT / LOOP, map_location="cpu", weights_only=False)["population"]
decks = [{"name": f"pop{x['id']}", "cards": x["deck"]} for x in pop]
rng = random.Random(a.seed)
pick = [tuple(rng.sample(range(len(decks)), 2)) for _ in range(a.n)]
worker = str(ROOT / "notes/scripts/audit/c161_worker.js")       # after the decks: R.subprocess is the subprocess module itself
_popen = R.subprocess.Popen
R.subprocess.Popen = lambda cmd, **kw: _popen(["node", worker], **kw)
device = "cuda" if torch.cuda.is_available() else "cpu"
model, _ = load_policy(LOOP, device)
models = {0: model.eval()}
path = OUT / f"decisions{a.tag}.jsonl"
for f in (path, Path(str(path) + ".accept")):
    f.unlink(missing_ok=True)
os.environ.update({"C161_OUT": str(path), "C161_P": str(a.p), "C161_MAX": str(a.max), "C161_KEEP": str(a.keep)})
jobs = [{"i": i, "j": j, "iSeat": 1 + (k % 2), "seed": a.seed * 1000000 + k} for k, (i, j) in enumerate(pick)]
shards = [jobs[w::a.workers] for w in range(a.workers)]
msgs = [{"cmd": "games", "encoding": "tokens", "decks": decks, "jobs": s, "greedy": True, "concurrency": a.concurrency,
         "history": history_of(models), "chain": chain_of(models), "canon": canon_of(models), "slots": [0] * len(decks),
         "roundTurns": [20, 45]} for s in shards]
pool = R.RemotePool(a.workers)
t0 = time.time()
try:
    reps = pool.collect(msgs, models, device)
finally:
    pool.close()
res = [x for r in reps for x in r["results"]]
(OUT / f"results{a.tag}.json").write_text(json.dumps(res), encoding="utf-8")
n_dec = sum(1 for _ in open(path, encoding="utf-8")) if path.exists() else 0
print("C161 games", len(res), "errors", sum(1 for x in res if x.get("error")), "seconds", round(time.time() - t0),
      "searched decisions", n_dec, flush=True)
