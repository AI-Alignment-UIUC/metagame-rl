"""C205's read (runs/probe/C205-overdraw-branch/record.md, with Amendment 1), from probe_draw_hold.py's raw files (TAG.probes.json.gz).
Per pilot (w48, w49), both game seeds pooled: Δ = the game-end result of playing the draw card now minus the other answer (played
states: the policy's most likely other option; skipped: the greedy hold), mean over each state's valid CRN branches, by deck left
(≤10, 11-20, 21-30, >30; and ≤15), with game-clustered SE; the live play rate of the cards by bin; deck-out share by the deck's
draw-card copies. Bands on the primary bin (≤10 if it holds ≥100 played states over both seeds, else ≤15): R-misplay Δ_play ≤ −0.03
at 2 SE with a play rate in the bin ≥ 0.3; R-shared |Δ_play| < 0.015 with SE ≤ 0.0075; between otherwise.
    PYTHONPATH=. .venv/Scripts/python notes/scripts/c205_read.py
"""
import gzip
import json
from pathlib import Path

import numpy as np

D = Path(__file__).resolve().parents[2] / "runs/probe/C205-overdraw-branch"
BINS = {"le10": lambda l: l <= 10, "11-20": lambda l: 11 <= l <= 20, "21-30": lambda l: 21 <= l <= 30, "gt30": lambda l: l > 30,
        "le15": lambda l: l <= 15}
PR_BINS = ("le10", "11-20", "21-30", "gt30")


def cse(x, g):
    x, g = np.asarray(x, float), np.asarray(g)
    if len(x) < 2:
        return {"n": len(x), "mean": round(float(x.mean()), 4) if len(x) else None, "se": None}
    m, ug = x.mean(), np.unique(g)
    se = np.sqrt(sum(((x[g == u] - m).sum()) ** 2 for u in ug) * len(ug) / max(len(ug) - 1, 1)) / len(x)
    return {"n": len(x), "games": len(ug), "mean": round(float(m), 4), "se": round(float(se), 4)}


def main():
    out = {}
    for pilot in ("w48", "w49"):
        rows, pr, do, meta = [], {}, {}, []
        for sd in (1, 2):
            f = D / f"{pilot}s{sd}.probes.json.gz"
            if not f.exists():
                continue
            raw = json.loads(gzip.open(f, "rt").read())
            meta.append({"seed": sd, "games": raw["games"], "game_errors": raw["game_errors"], "seconds": raw["seconds"], "probes": len(raw["probes"]),
                         "lines": raw["stats"].get("lines"), "lineErrors": raw["stats"].get("lineErrors")})
            for p in raw["probes"]:
                ok = [j for j in p["valid"] if p["rew"][0][j] is not None and p["rew"][1][j] is not None]
                if ok:
                    rows.append({"kind": "played" if p["stratum"].endswith("+played") else "skip", "left": p["deckLeft"],
                                 "card": p["stratum"].replace("+played", ""), "game": f"{sd}:{p['game']}",
                                 "d": float(np.mean([p["rew"][0][j] - p["rew"][1][j] for j in ok]))})
            for k, v in (raw["stats"].get("playRate") or {}).items():
                pr[k] = pr.get(k, 0) + v
            for k, v in (raw.get("deckouts") or {}).items():
                e = do.setdefault(int(k), [0, 0]); e[0] += v[0]; e[1] += v[1]
        if not rows:
            continue
        o = {"runs": meta, "by_bin": {}, "play_rate": {}, "deckout_by_copies": {}}
        for b, f in BINS.items():
            o["by_bin"][b] = {kd: cse([r["d"] for r in rows if r["kind"] == kd and f(r["left"])],
                                      [r["game"] for r in rows if r["kind"] == kd and f(r["left"])]) for kd in ("played", "skip")}
        for b in PR_BINS:
            e, p_ = pr.get(b + "|elig", 0), pr.get(b + "|play", 0)
            o["play_rate"][b] = {"eligible": e, "played": p_, "rate": round(p_ / e, 4) if e else None}
        e15 = sum(pr.get(b + "|elig", 0) for b in ("le10",)), 0
        for k in sorted(do):
            o["deckout_by_copies"][k] = {"seat_games": do[k][0], "deckout_losses": do[k][1], "share": round(do[k][1] / do[k][0], 4) if do[k][0] else None}
        prim = "le10" if o["by_bin"]["le10"]["played"]["n"] >= 100 else "le15"
        dp = o["by_bin"][prim]["played"]
        rate = o["play_rate"]["le10"]["rate"] if prim == "le10" else None
        if prim == "le15":                               # the live rate's bins are fixed; ≤15 uses ≤10 and 11-20 weighted by eligibility
            e = pr.get("le10|elig", 0) + pr.get("11-20|elig", 0)
            rate = round((pr.get("le10|play", 0) + pr.get("11-20|play", 0)) / e, 4) if e else None
        m, se = dp.get("mean"), dp.get("se")
        band = ("R-misplay" if m is not None and se and m <= -0.03 and m <= -2 * se and rate is not None and rate >= 0.3 else
                "R-shared" if m is not None and se is not None and abs(m) < 0.015 and se <= 0.0075 else "between")
        o.update({"primary_bin": prim, "primary_played": dp, "primary_play_rate": rate, "band": band})
        out[pilot] = o
    (D / "read.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
