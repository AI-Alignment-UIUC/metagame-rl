"""C132 (runs/probe/C132-goldfish-search/record.md; copy of goldfish_games2.py): --arm G (greedy, as C115), SV (env/agents.js
PolicySearchAgent at every main-phase decision: C122's SEARCH with trainerOnly false, scored by the pilot's value) or SP (the
same search scored by Prizes taken by the line's end, ties by V; evaluation only, row 86). Every job of an S arm is a search
job (rl.gpu_matrix's judgeSearch path in env/remote_worker.js), its Goldfish seat set by goldfish_worker3.js, which also keeps
search copies out of the trace. Output: <out-dir>/<arm>_P<list>_s<seed>.jsonl, and the summed searchStats per list on stdout.
C115's notes follow.
C115 (goldfish probe): P-list mirrors, attacker (SimpleBot, arm0 or start) against a passive Goldfish on the other seat (seat by seed parity),
through notes/scripts/audit/goldfish_worker2.js. Untimed, safety cap 200 game turns. Output: runs/probe/C115-goldfish/<pilot>_P<list>_s<seed>.jsonl
Run: PYTHONPATH=. .venv/Scripts/python.exe notes/scripts/audit/goldfish_games.py --pilot start|arm0|simplebot --seed 91 --n 256 [--lists 3 1 21 2] [--off]
--off: hook off (no PACE_TRACE_OUT); writes the per-game results to <...>.results.json, for the bit-identity check."""
import argparse, json, os, sys, time
from pathlib import Path
import torch

ROOT = Path.cwd()
import rl.remote as R
from rl.gpu_matrix import load_policy, history_of, chain_of, canon_of

ap = argparse.ArgumentParser()
ap.add_argument("--pilot", default="arm0")
ap.add_argument("--arm", choices=["G", "SV", "SP"], required=True)
ap.add_argument("--horizon", type=int, default=1, help="C132b: the search horizon in game turns (3: the end of the next own turn)")
ap.add_argument("--max-steps", type=int, default=40, help="C132b: steps a line may take (120 at horizon 3, 200 at 5)")
ap.add_argument("--line-goldfish", action="store_true", help="C132b: the goldfish plays the other seat inside search lines")
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

OUT = ROOT / "runs/probe/C132-goldfish-search"
if args.out_dir:
    OUT = ROOT / args.out_dir
OUT.mkdir(parents=True, exist_ok=True)
worker = str(ROOT / "notes/scripts/audit/goldfish_worker3.js")
SEARCH = {"k": 3, "dets": 2, "maxSteps": 40, "crn": True, "trainerOnly": False, "includeTrainer": True}   # C122's, trainerOnly off
_popen = R.subprocess.Popen
R.subprocess.Popen = lambda a, **kw: _popen(["node", worker], **kw)

decks = json.loads((ROOT / "runs/probe/BENCH/decks_P.json").read_text(encoding="utf-8"))
ckpt = args.ckpt or {"start": "ar/data/start.pt"}.get(args.pilot, "runs/probe/BENCH/arm-arm0-s1/pilot.pt")   # simplebot: the model is loaded but never asked
device = "cuda" if torch.cuda.is_available() and args.pilot != "simplebot" else "cpu"
model, _ = load_policy(ckpt, device)
models = {0: model.eval()}

for di in args.lists:
    name = f"{args.arm}{f'h{args.horizon}' if args.horizon > 1 else ''}_P{di}_s{args.seed}{args.tag}"
    path = OUT / f"{name}.jsonl"
    path.unlink(missing_ok=True)
    if args.off:
        os.environ.pop("PACE_TRACE_OUT", None)
    else:
        os.environ["PACE_TRACE_OUT"] = str(path)
    pool = R.RemotePool(args.workers)
    t0 = time.time()
    try:
        jobs = [{"i": di, "j": di, "iSeat": 1, "seed": args.seed * 1000000 + di * 10000 + k, **({"bot": "simplebot"} if args.pilot == "simplebot" else {}),
                 **({"search": True} if args.arm != "G" else {})} for k in range(args.n)]
        shards = [jobs[w::args.workers] for w in range(args.workers)]
        msgs = [{"cmd": "games", "encoding": "tokens", "decks": decks, "jobs": s, "greedy": True, "concurrency": args.concurrency,
                 "history": history_of(models), "chain": chain_of(models), "canon": canon_of(models), "slots": [0] * len(decks),
                 "maxTurns": 200, **({"judgeSearch": {**SEARCH, "score": "prizes" if args.arm == "SP" else "value", "horizon": args.horizon,
                                                       "maxSteps": args.max_steps, **({"lineOpponent": "goldfish"} if args.line_goldfish else {}),
                                                       "seed": args.seed * 64 + w}} if args.arm != "G" else {})}
                for w, s in enumerate(shards)]
        reps = pool.collect(msgs, models, device)
    finally:
        pool.close()
    res = sorted(({"seed": x.get("seed"), "winner": x.get("winner"), "ending": x.get("ending"), "steps": x.get("steps"), "error": x.get("error")}
                  for r in reps for x in r["results"]), key=lambda x: json.dumps(x))
    if args.tag.startswith("_id"):
        (OUT / f"{name}.results.json").write_text(json.dumps(res), encoding="utf-8")
    st = [r["searchStats"] for r in reps if r.get("searchStats")]
    stats = {q: round(sum(x.get(q, 0) for x in st), 2) for q in (st[0] if st else {})}
    print(name, "games", len(res), "errors", sum(1 for x in res if x.get("error")), "seconds", round(time.time() - t0),
          "ends", {e: sum(1 for x in res if x.get("ending") == e) for e in sorted({str(x.get("ending")) for x in res})}, "search", stats, flush=True)
