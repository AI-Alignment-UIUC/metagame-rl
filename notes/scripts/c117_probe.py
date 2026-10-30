"""C117 (runs/probe/C117-fast-opponent/record.md): C116's Oak and Bill branch test against a fast scripted opponent. Evaluation only.
The pilot (arm 0 s1, greedy live games) plays lists 3, 1, 21 and 2 (decks_P) against list 1 piloted by C115b's scripted
Wigglytuff line (env/tools/probe_fastopp_worker.js: the 'OPP ' deck's seat is the script's, in the live games and in every branch
line). At the pilot's main-phase decisions where Oak or Bill is playable and greedy holds it: play vs hold, K CRN re-deals to the
game's end with the pilot sampled on its side and the script on the other, scored by the training reward (dB), with dV and dT
as C116, and the Prizes each side has taken at the line's end (dPz). Also the pilot's base win rate and Prizes taken against the
script, by list. The pilot's seat alternates by pair key. The record's band is on Oak with 25 or more cards left.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c117_probe.py [--n 150] [--budget-s 1800]
"""
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
from rl import limits                       # noqa: E402
from rl.gpu_matrix import GpuMatrix, load_policy   # noqa: E402
from rl.train import round_turns            # noqa: E402
import probe_target_signal as pts           # noqa: E402
from probe_draw_hold import CARDS, ci, group   # noqa: E402

ROOT = pts.ROOT
OUT = ROOT / "runs/probe/C117-fast-opponent"
LEFT = (("ge25", lambda r: r["left"] >= 25), ("15to24", lambda r: 15 <= r["left"] < 25), ("lt15", lambda r: r["left"] < 15))


def play(model, args, device, plist, opp):
    pts.WORKER = ROOT / "env" / "tools" / "probe_fastopp_worker.js"
    rng = np.random.default_rng(args.seed)
    rp = pts.ProbePool(args.workers); rp.pace = 0.25
    gm = GpuMatrix.attach(model, rp, args.workers, device=device, greedy=True)
    probes, stats, base, errors, games, batch, key, log = [], [], [], 0, 0, 0, 0, []
    t0 = time.time()
    try:
        while games < args.max_games and time.time() - t0 < args.budget_s:
            c = collections.Counter(p["stratum"] for p in probes)
            need = {k: max(0, args.n - c.get(k, 0)) for k in CARDS}
            if not any(need.values()):
                break
            n = args.workers * args.batch_games
            decks, pairs, keys = [], [], []
            for _ in range(n):
                a = len(decks)
                decks += [plist[int(rng.integers(len(plist)))], opp]          # the pilot's deck at even indices
                pairs.append((a, a + 1) if key % 2 == 0 else (a + 1, a)); keys.append(key); key += 1
            rp.cfg = {"m": args.m, "cap": 2, "maxLine": 600, "mainP": args.main_p, "maxPerGame": args.max_per_game,
                      "minValid": args.min_valid, "need": need, "rot": batch}
            rp.probes, rp.stats = [], []
            tb = time.time()
            gm.play(decks, 1, args.seed, pairs=pairs, pair_keys=keys, round_turns=round_turns(args.round_turns))
            for r in gm.results:
                pi = r["i"] if r["i"] % 2 == 0 else r["j"]
                ps = r["iSeat"] if r["i"] % 2 == 0 else 3 - r["iSeat"]
                pl = r.get("prizesLeft") or {}
                base.append({"list": decks[pi]["name"], "seat": ps, "winner": r["winner"], "ending": r.get("ending"), "turns": r.get("turns"),
                             "pz": 6 - pl[str(ps)] if str(ps) in pl else None, "pzOpp": 6 - pl[str(3 - ps)] if str(3 - ps) in pl else None,
                             "error": r.get("error")})
            games += n; batch += 1
            probes += rp.probes; stats += rp.stats
            errors += sum(bool(r.get("error")) for r in gm.results)
            st = pts.sum_stats(stats)
            print(f"batch {batch}: {n} games {time.time() - tb:.0f}s total {time.time() - t0:.0f}s probes {len(probes)} "
                  f"{dict(collections.Counter(p['stratum'] for p in probes))} lines {st.get('lines', 0)} lineErrors {st.get('lineErrors', 0)} "
                  f"scriptMoves {st.get('scriptMoves', 0)} game errors {errors}", flush=True)
            if st.get("lines", 0) >= 200 and st.get("lineErrors", 0) > 0.01 * st["lines"]:
                log.append("KILL: engine errors over 1%"); print(log[-1]); break
        if time.time() - t0 >= args.budget_s:
            log.append(f"budget {args.budget_s:.0f}s reached: {dict(collections.Counter(p['stratum'] for p in probes))} states")
    finally:
        rp.close()
    return {"probes": probes, "stats": pts.sum_stats(stats), "base": base, "games": games, "game_errors": errors, "log": log,
            "seconds": round(time.time() - t0, 1)}


def base_summary(base):
    out = {}
    for name in sorted({b["list"] for b in base}) + ["pooled"]:
        B = [b for b in base if (name == "pooled" or b["list"] == name) and not b["error"]]
        if not B:
            continue
        out[name] = {"games": len(B), "win_share": round(float(np.mean([1.0 if b["winner"] == b["seat"] else 0.5 if b["winner"] not in (1, 2) else 0.0
                                                                        for b in B])), 4),
                     "prizes_taken": round(float(np.mean([b["pz"] for b in B if b["pz"] is not None])), 3),
                     "prizes_taken_opp": round(float(np.mean([b["pzOpp"] for b in B if b["pzOpp"] is not None])), 3),
                     "turns_mean": round(float(np.mean([b["turns"] for b in B if b["turns"] is not None])), 1),
                     "endings": dict(collections.Counter(b["ending"] or "none" for b in B))}
    return out


def cell(rows):
    o = group(rows)
    g = [r["game"] for r in rows]
    o["dPz"] = ci([r["dPz"] for r in rows], g)
    o["dPzOpp"] = ci([r["dPzOpp"] for r in rows], g)
    o["pz_hold"] = round(float(np.mean([r["pz_hold"] for r in rows])), 3) if rows else None
    o["win_hold"] = round(float(np.mean([r["win_hold"] for r in rows])), 3) if rows else None
    return o


def band(o, base_win):
    """The record's sign rule on dB (or on dPz if the base win rate is under 10% or over 90%)."""
    k = "dPz" if base_win < 0.10 or base_win > 0.90 else "dB"
    b = o[k]
    if not b.get("n"):
        return {"on": k, "band": "no states"}
    if b["mean"] > 0 and b.get("lo", -9) > 0:
        return {"on": k, "band": "R-opponent-pace"}
    if b["mean"] <= 0:
        return {"on": k, "band": "R-pace-independent"}
    return {"on": k, "band": "between"}


def analyze(raw, plist):
    names = {",".join(sorted(d["cards"])): d["name"] for d in plist}
    rows = []
    for p in raw["probes"]:
        ok = [j for j in p["valid"] if all(p[k][a][j] is not None for k in ("rew", "v1", "vt", "pz", "pzOpp") for a in (0, 1))]
        if not ok:
            continue
        d = lambda k: float(np.mean([p[k][0][j] - p[k][1][j] for j in ok]))
        rows.append({"card": p["stratum"], "game": p["game"], "turn": p["turn"], "left": p["deckLeft"], "list": names.get(p["cards"], "?"),
                     "dV": d("v1"), "dB": d("rew"), "dT": d("vt"), "dPz": d("pz"), "dPzOpp": d("pzOpp"), "K": len(ok), "capped": p["capped"],
                     "pz_hold": float(np.mean([p["pz"][1][j] for j in ok])), "win_hold": float(np.mean([p["rew"][1][j] > 0 for j in ok]))})
    bs = base_summary(raw["base"])
    bw = bs["pooled"]["win_share"]
    out = {}
    for c in CARDS:
        R = [r for r in rows if r["card"] == c]
        o = {"pooled": cell(R), "by_left": {nm: cell([r for r in R if f(r)]) for nm, f in LEFT},
             "by_list": {l: cell([r for r in R if r["list"] == l]) for l in sorted({r["list"] for r in R})}}
        out[c] = o
    out["band"] = {"cell": "Oak, 25 or more cards left", "base_win_share": bw, **band(out["Oak"]["by_left"]["ge25"], bw)}
    return out, rows, bs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default="runs/probe/BENCH/arm-arm0-s1/pilot.pt")
    ap.add_argument("--out", default="runs/probe/C117-fast-opponent/C117")
    ap.add_argument("--n", type=int, default=150, help="states a card")
    ap.add_argument("--m", type=int, default=8)
    ap.add_argument("--min-valid", type=int, default=6)
    ap.add_argument("--main-p", type=float, default=0.15)
    ap.add_argument("--max-per-game", type=int, default=2, help="a card, a game")
    ap.add_argument("--batch-games", type=int, default=6)
    ap.add_argument("--max-games", type=int, default=3000)
    ap.add_argument("--budget-s", type=float, default=1800)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--round-turns", default="20-45")
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--from-raw", default=None)
    args = ap.parse_args()
    args.workers = limits.cap_workers(args.workers); limits.apply(args.device, args.workers)
    P = json.loads((ROOT / "runs/probe/BENCH/decks_P.json").read_text(encoding="utf-8"))
    opp = {**P[1], "name": "OPP " + P[1]["name"]}
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.from_raw:
        raw = json.loads(gzip.open(args.from_raw, "rt").read())
    else:
        model, _ = load_policy(args.pilot, args.device)
        raw = play(model, args, args.device, P, opp)
        with gzip.open(str(out) + ".probes.json.gz", "wt") as f:
            json.dump(raw, f)
    res, rows, bs = analyze(raw, P)
    summ = {"pilot": args.pilot, "args": vars(args), "games": raw["games"], "game_errors": raw["game_errors"], "log": raw["log"],
            "seconds": raw["seconds"], "stats": raw["stats"], "base": bs, "readouts": res, "rows": rows}
    (out.parent / (out.name + "-summary.json")).write_text(json.dumps(summ, indent=1))
    print("base", json.dumps(bs.get("pooled")))
    for l, v in bs.items():
        print("  base", l, v["games"], "win", v["win_share"], "prizes", v["prizes_taken"], "/", v["prizes_taken_opp"], v["endings"])
    for c in CARDS:
        o = res[c]
        for k, v in [("pooled", o["pooled"])] + list(o["by_left"].items()) + list(o["by_list"].items()):
            print(c, k, v["states"], "dB", v["dB"].get("mean"), v["dB"].get("lo"), v["dB"].get("hi"), "dPz", v["dPz"].get("mean"),
                  v["dPz"].get("lo"), v["dPz"].get("hi"), "dV", v["dV"].get("mean"), "dT", v["dT"].get("mean"))
    print("band", json.dumps(res["band"]))


if __name__ == "__main__":
    main()
