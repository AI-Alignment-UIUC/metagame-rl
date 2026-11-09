"""C118 (runs/probe/C118-conversion/record.md): is converting drawn cards into tempo the bottleneck? Evaluation only, CPU.
C116's states (arm 0 s1's held Professor Oak at main-phase decisions in the P-list mirrors, greedy live games under the round
rule, seed 91), re-collected on CPU (the pairing with C116 is approximate). At each state, play Oak against the greedy hold on
K CRN re-deals, under two continuations on the same re-deals (env/tools/probe_conversion_worker.js):
  C-pilot: the pilot sampled at temperature 1 on both seats to game end (as C116);
  C-search: for the rest of this turn and the seat's next turn, the deciding seat's main-phase decisions by the pilot's own
            turn-end comparator (PolicySearchAgent: the top --search-k options by policy, --search-dets CRN copies to the
            turn's end, scored by the pilot's value); then sampled as C-pilot.
Scored by the training reward at game end: Δ = play − hold under each, and their paired difference, pooled and with 25 or more
cards left (game-clustered CIs, as C116); Prizes taken; how many of Oak's 7 drawn cards left the hand / reached the board in
the window; how often the search's choice differs from the pilot's greedy one. Bands as the record.
  CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=. .venv/Scripts/python notes/scripts/c118_probe.py [--n 100] [--m 8] [--out ...]
"""
import argparse
import collections
import gzip
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rl import limits                       # noqa: E402
from rl.gpu_matrix import GpuMatrix, load_policy   # noqa: E402
from rl.train import round_turns            # noqa: E402
import probe_target_signal as pts           # noqa: E402
from probe_draw_hold import ci              # noqa: E402

ROOT = pts.ROOT


def play(model, args, device):
    pts.WORKER = ROOT / "env" / "tools" / "probe_conversion_worker.js"
    mus = json.loads((ROOT / args.matchups).read_text())
    seen, mir = set(), []
    for a, b in mus:
        if a["name"] == b["name"] and a["name"] not in seen:
            seen.add(a["name"]); mir.append((a, b))
    rng = np.random.default_rng(args.seed)
    rp = pts.ProbePool(args.workers); rp.pace = 0.25
    gm = GpuMatrix.attach(model, rp, args.workers, device=device, greedy=True)
    probes, stats, errors, games, batch, key, log = [], [], 0, 0, 0, 0, []
    t0 = time.time()
    try:
        while games < args.max_games and time.time() - t0 < args.budget_s:
            need = {"Oak": max(0, args.n - sum(p["stratum"] == "Oak" for p in probes)), "Bill": 0}
            if not need["Oak"]:
                break
            n = args.workers * args.batch_games
            decks, pairs, keys = [], [], []
            for _ in range(n):
                a, b = mir[int(rng.integers(len(mir)))]
                pairs.append((len(decks), len(decks) + 1)); decks += [a, b]; keys.append(key); key += 1
            rp.cfg = {"m": args.m, "cap": 2, "maxLine": 600, "mainP": args.main_p, "maxPerGame": args.max_per_game,
                      "minValid": args.min_valid, "need": need, "rot": batch,
                      "search": {"k": args.search_k, "dets": args.search_dets, "maxSteps": 40, "seed": args.seed}}
            rp.probes, rp.stats = [], []
            tb = time.time()
            gm.play(decks, 1, args.seed, pairs=pairs, pair_keys=keys, round_turns=round_turns(args.round_turns))
            games += n; batch += 1
            probes += rp.probes; stats += rp.stats
            errors += sum(bool(r.get("error")) for r in gm.results)
            st = pts.sum_stats(stats)
            print(f"batch {batch}: {n} games {time.time() - tb:.0f}s total {time.time() - t0:.0f}s Oak states {sum(p['stratum'] == 'Oak' for p in probes)} "
                  f"lines {st.get('lines', 0)} lineErrors {st.get('lineErrors', 0)} searched {st.get('searched', 0)} "
                  f"search {st.get('search', {})} game errors {errors}", flush=True)
            if st.get("lines", 0) >= 200 and st.get("lineErrors", 0) > 0.01 * st["lines"]:
                log.append("KILL: engine errors over 1%"); print(log[-1]); break
        if time.time() - t0 >= args.budget_s:
            log.append(f"budget {args.budget_s:.0f}s reached at {sum(p['stratum'] == 'Oak' for p in probes)} states")
    finally:
        rp.close()
    return {"probes": [p for p in probes if p["stratum"] == "Oak"], "stats": pts.sum_stats(stats), "games": games,
            "game_errors": errors, "log": log, "seconds": round(time.time() - t0, 1)}


def analyze(raw):
    rows = []
    for p in raw["probes"]:
        ok = [j for j in p["valid"] if all(p[k][c][a][j] is not None for k in ("rewC", "pz") for c in (0, 1) for a in (0, 1))]
        if not ok:
            continue
        d = lambda k, c: float(np.mean([p[k][c][0][j] - p[k][c][1][j] for j in ok]))
        mean = lambda k, c: (lambda v: float(np.mean(v)) if v else None)([p[k][c][0][j] for j in ok if p[k][c][0][j] is not None])
        rows.append({"game": p["game"], "turn": p["turn"], "left": p["deckLeft"], "K": len(ok),
                     "dP": d("rewC", 0), "dS": d("rewC", 1), "dPzP": d("pz", 0), "dPzS": d("pz", 1),
                     "drawnLeftP": mean("drawnLeft", 0), "drawnLeftS": mean("drawnLeft", 1),
                     "drawnBoardP": mean("drawnBoard", 0), "drawnBoardS": mean("drawnBoard", 1)})
        rows[-1]["dSmP"] = rows[-1]["dS"] - rows[-1]["dP"]

    def cell(R):
        g = [r["game"] for r in R]
        out = {"states": len(R), "games": len(set(g))}
        for k in ("dP", "dS", "dSmP", "dPzP", "dPzS"):
            out[k] = ci([r[k] for r in R], g)
        for k in ("drawnLeftP", "drawnLeftS", "drawnBoardP", "drawnBoardS"):
            v = [r[k] for r in R if r[k] is not None]
            out[k] = round(float(np.mean(v)), 3) if v else None
        return out

    pooled, ge25 = cell(rows), cell([r for r in rows if r["left"] >= 25])
    s = raw["stats"].get("search", {})
    dS = pooled["dS"]
    band = ("R-conversion" if dS.get("n") and dS["mean"] > 0 and dS.get("lo", -9) > 0 and pooled["dSmP"].get("lo", -9) > 0
            else "R-not-conversion" if dS.get("n") and dS["mean"] <= 0 else "between")
    return {"pooled": pooled, "ge25": ge25, "search_changed_share": round(s["changed"] / s["searches"], 3) if s.get("searches") else None,
            "search": s, "band": band}, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default="runs/probe/BENCH/arm-arm0-s1/pilot.pt")
    ap.add_argument("--matchups", default="runs/probe/BENCH/bench_matchups.json")
    ap.add_argument("--out", default="runs/probe/C118-conversion/C118")
    ap.add_argument("--n", type=int, default=100, help="Oak states")
    ap.add_argument("--m", type=int, default=8, help="K, the CRN re-deals a state")
    ap.add_argument("--min-valid", type=int, default=6)
    ap.add_argument("--main-p", type=float, default=0.15)
    ap.add_argument("--max-per-game", type=int, default=2)
    ap.add_argument("--batch-games", type=int, default=6)
    ap.add_argument("--max-games", type=int, default=3000)
    ap.add_argument("--budget-s", type=float, default=1800)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--round-turns", default="20-45")
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--search-k", type=int, default=6)
    ap.add_argument("--search-dets", type=int, default=4)
    ap.add_argument("--from-raw", default=None)
    args = ap.parse_args()
    device = "cpu"
    args.workers = limits.cap_workers(args.workers); limits.apply(device, args.workers)
    model, _ = load_policy(args.pilot, device)
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.from_raw:
        raw = json.loads(gzip.open(args.from_raw, "rt").read())
    else:
        raw = play(model, args, device)
        with gzip.open(str(out) + ".probes.json.gz", "wt") as f:
            json.dump(raw, f)
    res, rows = analyze(raw)
    summ = {"pilot": args.pilot, "args": vars(args), "games": raw["games"], "game_errors": raw["game_errors"], "log": raw["log"],
            "seconds": raw["seconds"], "stats": raw["stats"], "readout": res, "rows": rows}
    (out.parent / (out.name + "-summary.json")).write_text(json.dumps(summ, indent=1))
    for k in ("pooled", "ge25"):
        v = res[k]
        print(k, v["states"], "dP", v["dP"].get("mean"), v["dP"].get("lo"), v["dP"].get("hi"), "| dS", v["dS"].get("mean"), v["dS"].get("lo"),
              v["dS"].get("hi"), "| dS-dP", v["dSmP"].get("mean"), v["dSmP"].get("lo"), v["dSmP"].get("hi"), "| drawn left/board P",
              v["drawnLeftP"], v["drawnBoardP"], "S", v["drawnLeftS"], v["drawnBoardS"])
    print("search changed share", res["search_changed_share"], "band", res["band"], "seconds", raw["seconds"])


if __name__ == "__main__":
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
    main()
