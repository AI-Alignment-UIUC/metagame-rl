"""C133 (runs/probe/C133-scripted-rank/record.md; copy of wiggly_games.py): C115b's games with the pilot arm 0 s1 in slot 0 as a shadow
(--mode shadow: the scripted move is played, the pilot's rank of it logged) or as the attacker itself (--mode pilot: arm 0 greedy on the
same deals, its V logged), through notes/scripts/audit/c133_worker.js. Output: runs/probe/C133-scripted-rank/<mode>_s<seed><tag>.jsonl
(one line a logged decision) and <mode>_s<seed><tag>.trace.jsonl (C114's per-turn trace). C115b's notes follow.
C115b: scripted Wigglytuff (list 1) against the passive Goldfish (list 3, decks_P index 0), 256 games, seed 91, untimed (maxTurns 200).
Attacker seat by seed parity (even: seat 1, odd: seat 2). Output: runs/probe/C115-goldfish/c115b/wiggly_s<seed>.jsonl
Run: PYTHONPATH=. .venv/Scripts/python.exe notes/scripts/audit/wiggly_games.py [--seed 91] [--n 256]"""
import argparse, json, os, time
from pathlib import Path
import torch

ROOT = Path.cwd()
import rl.remote as R
from rl.gpu_matrix import load_policy, history_of, chain_of, canon_of

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=91)
ap.add_argument("--n", type=int, default=256)
ap.add_argument("--workers", type=int, default=12)
ap.add_argument("--concurrency", type=int, default=16)
ap.add_argument("--mode", choices=["shadow", "pilot"], default="shadow")
ap.add_argument("--tag", default="")
ap.add_argument("--pilot", default="runs/probe/BENCH/arm-arm0-s1/pilot.pt")
args = ap.parse_args()
torch.set_num_threads(4)

OUT = ROOT / "runs/probe/C133-scripted-rank"
OUT.mkdir(parents=True, exist_ok=True)
worker = str(ROOT / "notes/scripts/audit/c133_worker.js")
_popen = R.subprocess.Popen
R.subprocess.Popen = lambda a, **kw: _popen(["node", worker], **kw)

decks = json.loads((ROOT / "runs/probe/BENCH/decks_P.json").read_text(encoding="utf-8"))
device = "cuda" if torch.cuda.is_available() else "cpu"
model, _ = load_policy(args.pilot, device)          # the shadow (or, with --mode pilot, the attacker)
models = {0: model.eval()}
path = OUT / f"{args.mode}_s{args.seed}{args.tag}.jsonl"
trace = OUT / f"{args.mode}_s{args.seed}{args.tag}.trace.jsonl"
path.unlink(missing_ok=True); trace.unlink(missing_ok=True)
os.environ["PACE_TRACE_OUT"] = str(trace)
os.environ["C133_OUT"] = str(path)
os.environ["C133_MODE"] = args.mode
pool = R.RemotePool(args.workers)
t0 = time.time()
try:
    # deck i = 1 (Wigglytuff), deck j = 0 (Haymaker); iSeat 1 puts i in seat 1, which the worker gives to the Wigglytuff agent on even seeds
    jobs = [{"i": 1, "j": 0, "iSeat": 1 if (args.seed * 1000000 + k) % 2 == 0 else 2, "seed": args.seed * 1000000 + k} for k in range(args.n)]
    shards = [jobs[w::args.workers] for w in range(args.workers)]
    msgs = [{"cmd": "games", "encoding": "tokens", "decks": decks, "jobs": s, "greedy": True, "concurrency": args.concurrency,
             "history": history_of(models), "chain": chain_of(models), "canon": canon_of(models), "slots": [0] * len(decks),
             "maxTurns": 200} for s in shards]
    reps = pool.collect(msgs, models, device)
finally:
    pool.close()
res = [x for r in reps for x in r["results"]]
print("games", len(res), "errors", sum(1 for x in res if x.get("error")), "seconds", round(time.time() - t0), flush=True)
