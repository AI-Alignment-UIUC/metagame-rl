"""C135 (runs/probe/C135-fullwidth-pp/record.md; copy of bp_games.py, field H only): --arm G, SV or SP through
notes/scripts/audit/c135_worker.js (the designated seat greedy, or full-width search at Trainer-playable decisions scored by V or
Prizes), arm 0 s1 on both seats, the 276 California pairs in C134's seeded order, round rule [20, 45]. Output:
runs/probe/C135-fullwidth-pp/<arm>_s<seed><tag>.jsonl (the designated seat's attacks) and .results.json (each game's result).
C134's notes follow.
C134 (runs/probe/C134-breakpoints/record.md): games for the breakpoint readouts, both seats the same greedy pilot, under the round
rule [20, 45] (as the loop and C113 play it), through notes/scripts/audit/bp_worker.js (one JSON line an attack). Fields:
  H   the 24 California lists (env/decks.js archivedDecks, the ground truth), round-robin pairs, under arm 0 s1;
  L   C127 s16's population at iteration 29 (99 decks), uniformly random pairs as the loop draws them, under that run's pilot;
  LH  the loop's pilot (C127 s16's) on field H, to separate the field from the pilot.
--n games in all: H and LH cycle through the 276 pairs in a seeded order, seats by seed parity. Output:
runs/probe/C134-breakpoints/<field>_s<seed><tag>.jsonl.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/audit/bp_games.py --field H --n 32 --tag _pilot
"""
import argparse
import json
import os
import random
import subprocess
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[3]
import rl.remote as R                                                   # noqa: E402
from rl.gpu_matrix import load_policy, history_of, chain_of, canon_of  # noqa: E402

LOOP = "runs/screens/C127-R1-K-paired-ledger-s16/population_it0029.pt"
ARM0 = "runs/probe/BENCH/arm-arm0-s1/pilot.pt"

ap = argparse.ArgumentParser()
ap.add_argument("--field", choices=["H"], default="H")
ap.add_argument("--arm", choices=["G", "SV", "SP"], required=True)
ap.add_argument("--n", type=int, default=32)
ap.add_argument("--seed", type=int, default=91)
ap.add_argument("--workers", type=int, default=6)
ap.add_argument("--concurrency", type=int, default=16)
ap.add_argument("--tag", default="")
ap.add_argument("--pilot", default=None, help="C152: field H's pilot in place of arm 0 s1 (default arm 0 s1)")
a = ap.parse_args()
torch.set_num_threads(4)

OUT = ROOT / "runs/probe/C135-fullwidth-pp"
OUT.mkdir(parents=True, exist_ok=True)
if a.field in ("H", "LH"):
    out = subprocess.run(["node", "-e", "const {archivedDecks}=require('./env/decks.js');console.log(JSON.stringify(archivedDecks()))"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    decks = json.loads(out.stdout)
    pairs = [(i, j) for i in range(len(decks)) for j in range(i + 1, len(decks))]
    random.Random(a.seed).shuffle(pairs)
    pick = [pairs[k % len(pairs)] for k in range(a.n)]
else:
    pop = torch.load(ROOT / LOOP, map_location="cpu", weights_only=False)["population"]
    decks = [{"name": f"pop{x['id']}", "cards": x["deck"]} for x in pop]
    rng = random.Random(a.seed)
    pick = []
    for _ in range(a.n):
        i, j = rng.sample(range(len(decks)), 2)
        pick.append((i, j))
worker = str(ROOT / "notes/scripts/audit/c135_worker.js")       # after the decks: R.subprocess is the subprocess module itself
_popen = R.subprocess.Popen
R.subprocess.Popen = lambda cmd, **kw: _popen(["node", worker], **kw)
pilot = a.pilot or (ARM0 if a.field == "H" else LOOP)
device = "cuda" if torch.cuda.is_available() else "cpu"
model, _ = load_policy(pilot, device)
models = {0: model.eval()}
path = OUT / f"{a.arm}_s{a.seed}{a.tag}.jsonl"
path.unlink(missing_ok=True)
os.environ["C135_OUT"] = str(path)
os.environ["C135_ARM"] = a.arm
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
(OUT / f"{a.arm}_s{a.seed}{a.tag}.results.json").write_text(json.dumps(res), encoding="utf-8")
ends = {}
for x in res:
    ends[str(x.get("ending"))] = ends.get(str(x.get("ending")), 0) + 1
print(a.arm, "games", len(res), "errors", sum(1 for x in res if x.get("error")), "seconds", round(time.time() - t0), "ends", ends,
      "attacks", sum(1 for _ in open(path)) if path.exists() else 0, flush=True)
