"""C116 (runs/probe/C116-draw-hold/record.md): is the pilot's hold on Professor Oak and Bill a value bias? Evaluation only.
Reuses probe_target_signal's ProbePool with env/tools/probe_draw_worker.js. Greedy live games (pilot both seats) on the P-list
mirrors under the round rule; at held Oak/Bill decisions: play vs greedy, K CRN re-deals to the game's end (dB, training
reward), to the end of the turn (dT, the pilot's value), and dV (the value right after the action). --from-raw reanalyses."""
import argparse
import collections
import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rl import limits
from rl.gpu_matrix import GpuMatrix, load_policy
from rl.train import round_turns
import probe_target_signal as pts

ROOT = pts.ROOT
CARDS = ["Oak", "Bill"]


def play(model, args, device):
    pts.WORKER = ROOT / "env" / "tools" / "probe_draw_worker.js"
    mus = json.loads((ROOT / args.matchups).read_text())
    seen, mir = set(), []
    for a, b in mus:
        if a["name"] == b["name"] and a["name"] not in seen:
            seen.add(a["name"]); mir.append((a, b))
    rng = np.random.default_rng(args.seed)
    rounds = round_turns(args.round_turns)
    rp = pts.ProbePool(args.workers); rp.pace = 0.25
    gm = GpuMatrix.attach(model, rp, args.workers, device=device, greedy=True)
    probes, stats, errors, games, batch, key = [], [], 0, 0, 0, 0
    t0 = time.time(); log = []
    try:
        while games < args.max_games and time.time() - t0 < args.budget_s:
            c = collections.Counter(p["stratum"] for p in probes)
            need = {k: max(0, args.n - c.get(k, 0)) for k in CARDS}
            if not any(need.values()):
                break
            n = args.workers * args.batch_games
            decks, pairs, keys = [], [], []
            for g in range(n):
                a, b = mir[int(rng.integers(len(mir)))]
                pairs.append((len(decks), len(decks) + 1)); decks += [a, b]; keys.append(key); key += 1
            rp.cfg = {"m": args.m, "cap": 2, "maxLine": 600, "mainP": args.main_p, "maxPerGame": args.max_per_game,
                      "minValid": args.min_valid, "need": need, "rot": batch}
            rp.probes, rp.stats = [], []
            tb = time.time()
            gm.play(decks, 1, args.seed, pairs=pairs, pair_keys=keys, round_turns=rounds)
            games += n; batch += 1
            probes += rp.probes; stats += rp.stats
            errors += sum(bool(r.get("error")) for r in gm.results)
            st = pts.sum_stats(stats)
            print(f"batch {batch}: {n} games {time.time() - tb:.0f}s total {time.time() - t0:.0f}s probes {len(probes)} "
                  f"{dict(collections.Counter(p['stratum'] for p in probes))} lines {st.get('lines', 0)} lineErrors {st.get('lineErrors', 0)} "
                  f"unsearchable {st.get('unsearchable', 0)} game errors {errors}", flush=True)
            if st.get("lines", 0) >= 200 and st.get("lineErrors", 0) > 0.01 * st["lines"]:
                log.append("KILL: engine errors over 1%"); print(log[-1]); break
    finally:
        rp.close()
    return {"probes": probes, "stats": pts.sum_stats(stats), "games": games, "game_errors": errors, "log": log,
            "seconds": round(time.time() - t0, 1)}


def ci(x, g):
    """Mean with a game-clustered 95% CI (cluster-robust SE of the state mean), normal."""
    x, g = np.asarray(x, float), np.asarray(g)
    if len(x) == 0:
        return {"n": 0}
    m = x.mean(); ug = np.unique(g)
    if len(ug) < 2:
        return {"n": len(x), "games": len(ug), "mean": round(float(m), 4)}
    se = np.sqrt(sum(((x[g == u] - m).sum()) ** 2 for u in ug) * len(ug) / (len(ug) - 1)) / len(x)
    return {"n": len(x), "games": len(ug), "mean": round(float(m), 4), "lo": round(float(m - 1.96 * se), 4), "hi": round(float(m + 1.96 * se), 4)}


def group(rows):
    g = [r["game"] for r in rows]
    out = {"states": len(rows), "games": len(set(g))}
    for k in ("dV", "dB", "dT"):
        out[k] = ci([r[k] for r in rows], g)
        out["play_share_" + k] = round(float(np.mean([r[k] > 0 for r in rows])), 3) if rows else None
    out["sign_agree_dV_dB"] = round(float(np.mean([(r["dV"] > 0) == (r["dB"] > 0) for r in rows])), 3) if rows else None
    out["sign_agree_dV_dT"] = round(float(np.mean([(r["dV"] > 0) == (r["dT"] > 0) for r in rows])), 3) if rows else None
    return out


def band(r):
    b, v = r["dB"], r["dV"]
    if not b.get("n"):
        return "no states"
    bpos = b.get("lo", -9) > 0
    if bpos and v["mean"] <= 0:
        return "R-value-bias"
    if b["mean"] <= 0 and v["mean"] <= 0:
        return "R-hold-right"
    if bpos and v["mean"] > 0:
        return "R-both-play"
    return "between"


def analyze(probes, decks):
    names = {",".join(sorted(d["cards"])): d["name"] for d in decks}
    rows = []
    for p in probes:
        ok = [j for j in p["valid"] if all(p[k][a][j] is not None for k in ("rew", "v1", "vt") for a in (0, 1))]
        if not ok:
            continue
        d = lambda k: float(np.mean([p[k][0][j] - p[k][1][j] for j in ok]))
        rows.append({"card": p["stratum"], "game": p["game"], "turn": p["turn"], "left": p["deckLeft"], "list": names.get(p["cards"], "?"),
                     "dV": d("v1"), "dB": d("rew"), "dT": d("vt"), "K": len(ok), "capped": p["capped"]})
    out = {}
    for c in CARDS:
        R = [r for r in rows if r["card"] == c]
        o = {"pooled": group(R), "by_left": {}, "by_list": {}}
        o["pooled"]["band"] = band(o["pooled"])
        for nm, f in (("ge25", lambda r: r["left"] >= 25), ("15to24", lambda r: 15 <= r["left"] < 25), ("lt15", lambda r: r["left"] < 15)):
            o["by_left"][nm] = group([r for r in R if f(r)]); o["by_left"][nm]["band"] = band(o["by_left"][nm])
        for l in sorted({r["list"] for r in R}):
            o["by_list"][l] = group([r for r in R if r["list"] == l]); o["by_list"][l]["band"] = band(o["by_list"][l])
        out[c] = o
    return out, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default="runs/probe/BENCH/arm-arm0-s1/pilot.pt")
    ap.add_argument("--matchups", default="runs/probe/BENCH/bench_matchups.json")
    ap.add_argument("--out", default="runs/probe/C116-draw-hold/C116")
    ap.add_argument("--n", type=int, default=300, help="states a card")
    ap.add_argument("--m", type=int, default=8)
    ap.add_argument("--min-valid", type=int, default=6)
    ap.add_argument("--main-p", type=float, default=0.15)
    ap.add_argument("--max-per-game", type=int, default=2, help="a card, a game")
    ap.add_argument("--batch-games", type=int, default=6)
    ap.add_argument("--max-games", type=int, default=3000)
    ap.add_argument("--budget-s", type=float, default=1200)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--round-turns", default="20-45")
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--from-raw", default=None)
    args = ap.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers); limits.apply(device, args.workers)
    model, enc = load_policy(args.pilot, device)
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.from_raw:
        raw = json.loads(gzip.open(args.from_raw, "rt").read())
    else:
        raw = play(model, args, device)
        with gzip.open(str(out) + ".probes.json.gz", "wt") as f:
            json.dump(raw, f)
    decks = [d for m in json.loads((ROOT / args.matchups).read_text()) for d in m]
    res, rows = analyze(raw["probes"], decks)
    summ = {"pilot": args.pilot, "args": vars(args), "games": raw["games"], "game_errors": raw["game_errors"], "log": raw["log"],
            "seconds": raw["seconds"], "stats": raw["stats"], "readouts": res, "rows": rows}
    (out.parent / ("summary.json" if args.out.endswith("C116") else Path(args.out).name + "-summary.json")).write_text(json.dumps(summ, indent=1))
    for c, o in res.items():
        print(c, json.dumps(o["pooled"]))
        for k, v in list(o["by_left"].items()) + list(o["by_list"].items()):
            print("  ", k, v["states"], v["band"], "dV", v["dV"].get("mean"), "dB", v["dB"].get("mean"), v["dB"].get("lo"), v["dB"].get("hi"), "dT", v["dT"].get("mean"))


if __name__ == "__main__":
    main()
