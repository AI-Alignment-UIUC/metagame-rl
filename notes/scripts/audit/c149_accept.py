"""C149 stage 1's acceptance (runs/probe/C149-mirror-update/record.md): do afterstate values rank PlusPower above the greedy option at
b10 states? Arm 0 s1 on both seats of field H (the 24 California lists, C134's seeded round-robin pairs, round rule [20, 45]) through
notes/scripts/audit/c149_accept_worker.js, which scores every legal option at the designated seat's b10 states (PlusPower and an attack
legal, an attack leaving the opposing Active at exactly 10 HP) by the pilot's value at the afterstate (dets 1, log only). Reads up to
--states states: the share where PlusPower's afterstate value is above the greedy option's (the record: most of them; C135's
end-of-turn search 83%). Output: runs/probe/C149-mirror-update/accept_s<seed>.jsonl and accept_s<seed>.json.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/audit/c149_accept.py --n 600 --states 20
"""
import argparse
import json
import math
import os
import random
import subprocess
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import rl.remote as R                                                  # noqa: E402
from rl.gpu_matrix import canon_of, chain_of, history_of, load_policy  # noqa: E402

ARM0 = "runs/probe/BENCH/arm-arm0-s1/pilot.pt"
ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=600, help="games (C135 found about 1 b10 state with PlusPower in hand per 30 games)")
ap.add_argument("--states", type=int, default=20)
ap.add_argument("--seed", type=int, default=149)
ap.add_argument("--workers", type=int, default=6)
ap.add_argument("--concurrency", type=int, default=32)
a = ap.parse_args()
torch.set_num_threads(4)

OUT = ROOT / "runs/probe/C149-mirror-update"
OUT.mkdir(parents=True, exist_ok=True)
out = subprocess.run(["node", "-e", "const {archivedDecks}=require('./env/decks.js');console.log(JSON.stringify(archivedDecks()))"],
                     cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
decks = json.loads(out.stdout)
pairs = [(i, j) for i in range(len(decks)) for j in range(i + 1, len(decks))]
random.Random(a.seed).shuffle(pairs)
pick = [pairs[k % len(pairs)] for k in range(a.n)]
worker = str(ROOT / "notes/scripts/audit/c149_accept_worker.js")
_popen = R.subprocess.Popen
R.subprocess.Popen = lambda cmd, **kw: _popen(["node", worker], **kw)
device = "cuda" if torch.cuda.is_available() else "cpu"
model, _ = load_policy(ARM0, device)
models = {0: model.eval()}
path = OUT / f"accept_s{a.seed}.jsonl"
path.unlink(missing_ok=True)
os.environ["C149_OUT"] = str(path)
os.environ["C149_MAX"] = str(math.ceil(a.states / a.workers) + 1)
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
rows = [json.loads(l) for l in open(path, encoding="utf-8")] if path.exists() else []
rows = [r for r in rows if not r["greedyIsPP"] and r["ppScore"] is not None and r["greedyScore"] is not None][:a.states]
above = sum(r["ppScore"] > r["greedyScore"] for r in rows)
summ = {"games": len(res), "errors": sum(1 for x in res if x.get("error")), "seconds": round(time.time() - t0),
        "states": len(rows), "pp_above_greedy": above, "share": round(above / len(rows), 3) if rows else None,
        "mean_margin": round(sum(r["ppScore"] - r["greedyScore"] for r in rows) / len(rows), 4) if rows else None,
        "all_options_searched": all(r["searched"] == r["options"] for r in rows),
        "greedy_keys": sorted({r["greedy"].split("|")[0] for r in rows}),
        "line_errors": max((r["stats"]["lineErrors"] for r in rows), default=0)}
(OUT / f"accept_s{a.seed}.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
print(json.dumps(summ), flush=True)
