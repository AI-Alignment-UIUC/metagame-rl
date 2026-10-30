"""Engine audit part 1 (log #484, Evan's row 102): the per-turn tracer's games. Each human list of runs/probe/BENCH/decks_P.json plays
itself with the BENCH arm 0 seed 1 pilot (CPU, greedy, both seats), under the round rule [20, 45] and without a rule, through
notes/scripts/audit/trace_worker.js (env/remote_worker.js plus read-only tracing). Traces go to runs/probe/AUDIT-engine/trace_*.jsonl.
Run: CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=. .venv/Scripts/python.exe notes/scripts/audit/trace_games.py [--capped 100] [--untimed 30]"""
import argparse, json, os, sys, time
from pathlib import Path
import torch

ROOT = Path.cwd()
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
import rl.remote as R
from rl.gpu_matrix import load_policy, history_of, chain_of, canon_of

ap = argparse.ArgumentParser()
ap.add_argument("--capped", type=int, default=100)
ap.add_argument("--untimed", type=int, default=30)
ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--concurrency", type=int, default=16)
args = ap.parse_args()
torch.set_num_threads(4)

OUT = ROOT / "runs/probe/AUDIT-engine"
OUT.mkdir(parents=True, exist_ok=True)
worker = str(ROOT / "notes/scripts/audit/trace_worker.js")
_popen = R.subprocess.Popen
R.subprocess.Popen = lambda a, **kw: _popen(["node", worker], **kw)       # the pool starts the tracing worker

decks = json.loads((ROOT / "runs/probe/BENCH/decks_P.json").read_text(encoding="utf-8"))
model, _ = load_policy("runs/probe/BENCH/arm-arm0-s1/pilot.pt", "cpu")
model = model.eval()
models = {0: model}

for label, n, rt in (("capped", args.capped, [20, 45]), ("untimed", args.untimed, 0)):
    path = OUT / f"trace_{label}.jsonl"
    path.unlink(missing_ok=True)
    os.environ["AUDIT_TRACE_OUT"] = str(path)
    pool = R.RemotePool(args.workers)
    t0 = time.time()
    try:
        jobs = [{"i": di, "j": di, "iSeat": 1, "seed": 1000 + di * 100000 + k} for di in range(len(decks)) for k in range(n)]
        shards = [jobs[w::args.workers] for w in range(args.workers)]
        msgs = [{"cmd": "games", "encoding": "tokens", "decks": decks, "jobs": s, "greedy": True, "concurrency": args.concurrency,
                 "history": history_of(models), "chain": chain_of(models), "canon": canon_of(models), "slots": [0] * len(decks),
                 **({"roundTurns": rt} if rt else {})} for s in shards]
        reps = pool.collect(msgs, models, "cpu")
    finally:
        pool.close()
    print(label, "games", sum(r["games"] for r in reps), "seconds", round(time.time() - t0), flush=True)
