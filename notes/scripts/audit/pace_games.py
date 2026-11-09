"""C114 (pace probe): P-list mirrors, untimed with a safety cap of 200 game turns (a draw), the same pilot on both seats, through
notes/scripts/audit/pace_worker.js (env/remote_worker.js plus a log-only per-turn hook). Output: runs/probe/C114-pace/<pilot>_P<list>_s<seed>.jsonl
Run: PYTHONPATH=. .venv/Scripts/python.exe notes/scripts/audit/pace_games.py --pilot start|arm0|simplebot --seed 91 --n 256 [--lists 3 1 21 2] [--off]
--off: hook off (no PACE_TRACE_OUT); writes the per-game results to <...>.results.json, for the bit-identity check."""
import argparse, json, os, sys, time
from pathlib import Path
import torch

ROOT = Path.cwd()
import rl.remote as R
from rl.gpu_matrix import load_policy, history_of, chain_of, canon_of

ap = argparse.ArgumentParser()
ap.add_argument("--pilot", required=True)
ap.add_argument("--seed", type=int, default=91)
ap.add_argument("--n", type=int, default=256)
ap.add_argument("--lists", type=int, nargs="*", default=[0, 1, 2, 3])
ap.add_argument("--workers", type=int, default=12)
ap.add_argument("--concurrency", type=int, default=16)
ap.add_argument("--off", action="store_true")
ap.add_argument("--tag", default="")
ap.add_argument("--ckpt", help="the pilot checkpoint, in place of --pilot's (--pilot is then the file label; BENCH-P9)")
ap.add_argument("--out-dir", help="the output folder, in place of the default one (BENCH-P9)")
args = ap.parse_args()
torch.set_num_threads(4)

OUT = ROOT / "runs/probe/C114-pace"
if args.out_dir:
    OUT = ROOT / args.out_dir
OUT.mkdir(parents=True, exist_ok=True)
worker = str(ROOT / "notes/scripts/audit/pace_worker.js")
_popen = R.subprocess.Popen
R.subprocess.Popen = lambda a, **kw: _popen(["node", worker], **kw)

decks = json.loads((ROOT / "runs/probe/BENCH/decks_P.json").read_text(encoding="utf-8"))
ckpt = args.ckpt or {"start": "ar/data/start.pt"}.get(args.pilot, "runs/probe/BENCH/arm-arm0-s1/pilot.pt")   # simplebot: the model is loaded but never asked
device = "cuda" if torch.cuda.is_available() and args.pilot != "simplebot" else "cpu"
model, _ = load_policy(ckpt, device)
models = {0: model.eval()}

for di in args.lists:
    name = f"{args.pilot}_P{di}_s{args.seed}{args.tag}"
    path = OUT / f"{name}.jsonl"
    path.unlink(missing_ok=True)
    if args.off:
        os.environ.pop("PACE_TRACE_OUT", None)
    else:
        os.environ["PACE_TRACE_OUT"] = str(path)
    pool = R.RemotePool(args.workers)
    t0 = time.time()
    try:
        jobs = [{"i": di, "j": di, "iSeat": 1, "seed": args.seed * 1000000 + di * 10000 + k, **({"bot": "simplebot"} if args.pilot == "simplebot" else {})}
                for k in range(args.n)]
        shards = [jobs[w::args.workers] for w in range(args.workers)]
        msgs = [{"cmd": "games", "encoding": "tokens", "decks": decks, "jobs": s, "greedy": True, "concurrency": args.concurrency,
                 "history": history_of(models), "chain": chain_of(models), "canon": canon_of(models), "slots": [0] * len(decks),
                 "maxTurns": 200} for s in shards]
        reps = pool.collect(msgs, models, device)
    finally:
        pool.close()
    res = sorted(({"seed": x.get("seed"), "winner": x.get("winner"), "ending": x.get("ending"), "steps": x.get("steps"), "error": x.get("error")}
                  for r in reps for x in r["results"]), key=lambda x: json.dumps(x))
    if args.tag.startswith("_id"):
        (OUT / f"{name}.results.json").write_text(json.dumps(res), encoding="utf-8")
    print(name, "games", len(res), "errors", sum(1 for x in res if x.get("error")), "seconds", round(time.time() - t0), flush=True)
