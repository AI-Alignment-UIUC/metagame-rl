"""C117's validity check (runs/probe/C117-fast-opponent/record.md): the scripted opponent's pace in games like C117's base games.
arm 0 s1 (greedy) on each P list against list 1 piloted by C115b's scripted Wigglytuff (notes/scripts/audit/c117_pace_worker.js),
the cap [20, 45] as C117, the pilot's seat 1 on even seeds and 2 on odd ones. Writes runs/probe/C117-fast-opponent/pace/P<list>_s<seed>.jsonl
(C114's per-turn trace) and prints, for the script and the pilot: knockouts per own turn, own turns to the first knockout, the
cap-reached share, win share. Evaluation only.
Run: PYTHONPATH=. .venv/Scripts/python.exe notes/scripts/audit/c117_pace.py [--seed 91] [--n 64] [--device cuda|cpu]"""
import argparse, collections, json, os, statistics, time
from pathlib import Path
import torch

ROOT = Path.cwd()
import rl.remote as R
from rl.gpu_matrix import load_policy, history_of, chain_of, canon_of

ap = argparse.ArgumentParser()
ap.add_argument("--pilot", default="runs/probe/BENCH/arm-arm0-s1/pilot.pt")
ap.add_argument("--seed", type=int, default=91)
ap.add_argument("--n", type=int, default=64, help="games a list")
ap.add_argument("--workers", type=int, default=8)
ap.add_argument("--concurrency", type=int, default=16)
ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
args = ap.parse_args()
torch.set_num_threads(4)
OUT = ROOT / "runs/probe/C117-fast-opponent/pace"
OUT.mkdir(parents=True, exist_ok=True)
worker = str(ROOT / "notes/scripts/audit/c117_pace_worker.js")
_popen = R.subprocess.Popen
R.subprocess.Popen = lambda a, **kw: _popen(["node", worker], **kw)
P = json.loads((ROOT / "runs/probe/BENCH/decks_P.json").read_text(encoding="utf-8"))
decks = P + [{**P[1], "name": "OPP " + P[1]["name"]}]
model, _ = load_policy(args.pilot, args.device)
models = {0: model.eval()}
games = []
for di in range(4):
    path = OUT / f"P{di}_s{args.seed}.jsonl"
    path.unlink(missing_ok=True)
    os.environ["PACE_TRACE_OUT"] = str(path)
    jobs = []
    for k in range(args.n):
        s = args.seed * 1000000 + di * 10000 + k
        jobs.append({"i": di, "j": 4, "iSeat": 1 if s % 2 == 0 else 2, "seed": s})
    pool = R.RemotePool(args.workers)
    t0 = time.time()
    try:
        msgs = [{"cmd": "games", "encoding": "tokens", "decks": decks, "jobs": jobs[w::args.workers], "greedy": True, "concurrency": args.concurrency,
                 "history": history_of(models), "chain": chain_of(models), "canon": canon_of(models), "slots": [0] * len(decks),
                 "roundTurns": [20, 45]} for w in range(args.workers)]
        reps = pool.collect(msgs, models, args.device)
    finally:
        pool.close()
    res = [x for r in reps for x in r["results"]]
    print(f"P{di} {P[di]['name']}: games {len(res)} errors {sum(1 for x in res if x.get('error'))} seconds {time.time() - t0:.0f}", flush=True)
    games += [dict(json.loads(l), list=P[di]["name"]) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def side(gs, script):
    """Per seat (the script's, or the pilot's): knockouts per own turn, median own turns to the first knockout, win share."""
    kos, turns, first, wins = 0, 0, [], 0.0
    for g in gs:
        opp = 2 if g["seed"] % 2 == 0 else 1                  # the pilot sits in seat 1 on even seeds
        me = opp if script else 3 - opp
        mine = [t for t in g["turns"] if t["p"] == me]
        kos += sum(t["kos"] for t in mine); turns += len(mine)
        i = next((i for i, t in enumerate(mine, 1) if t["kos"]), None)
        if i: first.append(i)
        wins += 1.0 if g["winner"] == me else 0.5 if g["winner"] not in (1, 2) else 0.0
    return {"kos_per_own_turn": round(kos / max(turns, 1), 4), "median_own_turns_to_first_ko": statistics.median(first) if first else None,
            "share_with_a_ko": round(len(first) / max(len(gs), 1), 3), "win_share": round(wins / max(len(gs), 1), 4)}


out = {}
for name in sorted({g["list"] for g in games}) + ["pooled"]:
    gs = [g for g in games if name == "pooled" or g["list"] == name]
    out[name] = {"games": len(gs), "cap_reached_share": round(sum(1 for g in gs if g["ending"] == "time") / max(len(gs), 1), 3),
                 "endings": dict(collections.Counter(g["ending"] or "none" for g in gs)), "script": side(gs, True), "pilot": side(gs, False)}
v = out["pooled"]
out["validity"] = {"script_kos_per_own_turn": v["script"]["kos_per_own_turn"], "arm0_mirror_rate": 0.098, "ratio": round(v["script"]["kos_per_own_turn"] / 0.098, 3),
                   "cap_reached_share": v["cap_reached_share"],
                   "valid": v["script"]["kos_per_own_turn"] >= 1.2 * 0.098 and v["cap_reached_share"] < 0.75}
(OUT / f"summary_s{args.seed}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for k, x in out.items():
    print(k, json.dumps(x))
