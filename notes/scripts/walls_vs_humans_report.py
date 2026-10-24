"""Report for notes/scripts/walls_vs_humans.js runs (evaluation only): A's (the walls') score against the human lists,
with a 95% CI clustered by deck pair (bootstrap over pairs), by wall and by archetype, endings by winner, and, for two
runs on the same deals, the paired difference (game by game: same pair, same game index, same seed).

  .venv/Scripts/python notes/scripts/walls_vs_humans_report.py runs/probe/wvh_greedy.jsonl runs/probe/wvh_psearch_k4.jsonl

Runs with a prizeTrace (log #150) also get the 2000 STS round rule scored exactly at turn cuts of 30-80.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
B = [d["name"] for d in json.load(open(ROOT / "runs/probe/archived.json", encoding="utf-8"))]
A = [d["name"] for d in json.load(open(ROOT / "runs/probe/walls_resetcap499.json", encoding="utf-8"))]


def archetype(j):
    return re.search(r"\(([^)]*)\)$", B[j]).group(1)


def load(path):
    return [json.loads(x) for x in open(ROOT / path, encoding="utf-8") if x.strip()]


def boot_ci(rows, key=lambda r: r["aScore"], n=4000, seed=0):
    """Mean and 95% CI, resampling deck pairs (i, j) with their games."""
    by = defaultdict(list)
    for r in rows:
        by[(r["i"], r["j"])].append(key(r))
    groups = [np.array(v, float) for v in by.values()]
    rng = np.random.default_rng(seed)
    sums = np.array([g.sum() for g in groups]); cnts = np.array([len(g) for g in groups])
    idx = rng.integers(0, len(groups), (n, len(groups)))
    bs = sums[idx].sum(1) / cnts[idx].sum(1)
    m = sums.sum() / cnts.sum()
    return m, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def summary(name, rows):
    m, lo, hi = boot_ci(rows)
    p = m
    print(f"\n== {name}: {len(rows)} games, errors {sum(1 for r in rows if r.get('error'))}, cut/draw "
          f"{sum(1 for r in rows if r['aScore'] == 0.5)}")
    print(f"walls' score {m:.3f}  95% CI by pair [{lo:.3f}, {hi:.3f}]  (binomial +-{1.96 * np.sqrt(p * (1 - p) / len(rows)):.3f})")
    for i in sorted({r["i"] for r in rows}):
        rs = [r for r in rows if r["i"] == i]
        print(f"  {A[i]:8s} {np.mean([r['aScore'] for r in rs]):.3f}  n {len(rs)}")
    arch = defaultdict(list)
    for r in rows:
        arch[archetype(r["j"])].append(r["aScore"])
    print("  by human archetype:", ", ".join(f"{k} {np.mean(v):.2f} (n {len(v)})" for k, v in sorted(arch.items())))
    end = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        end[r.get("ending") or "none"][0 if r["aScore"] == 1 else 1 if r["aScore"] == 0 else 2] += 1
    print("  endings [walls' wins, human lists' wins, other]:", dict(end))
    print(f"  mean turns {np.mean([r['turns'] for r in rows]):.1f}; prizes left at the end, walls / human lists "
          f"{np.mean([r['prizesLeftA'] for r in rows]):.2f} / {np.mean([r['prizesLeftB'] for r in rows]):.2f}")
    # The walls' deck-out wins: who was ahead on prizes when the human list ran out of cards (a prize count is how a
    # timed round would be decided), and how long these games ran
    do = [r for r in rows if r.get("ending") == "deck-out" and r["aScore"] == 1]
    if do:
        lead = np.array([r["prizesLeftA"] - r["prizesLeftB"] for r in do])
        print(f"  walls' deck-out wins {len(do)}: human list ahead on prizes {int((lead > 0).sum())}, even {int((lead == 0).sum())}, "
              f"walls ahead {int((lead < 0).sum())}; prizes left walls / human {np.mean([r['prizesLeftA'] for r in do]):.2f} / "
              f"{np.mean([r['prizesLeftB'] for r in do]):.2f}; turns median {np.median([r['turns'] for r in do]):.0f}")
    t = np.array([r["turns"] for r in rows])
    print(f"  turns quartiles {np.percentile(t, 25):.0f} / {np.median(t):.0f} / {np.percentile(t, 75):.0f}; walls' score in games "
          f"over 40 turns {np.mean([r['aScore'] for r in rows if r['turns'] > 40] or [np.nan]):.3f} "
          f"(n {int((t > 40).sum())}), 40 or fewer {np.mean([r['aScore'] for r in rows if r['turns'] <= 40] or [np.nan]):.3f}")
    sts(rows)
    return m


def sts_points(r, cut):
    """The walls' and the human list's points for one game under the 2000 STS round rule at an engine-turn cut (log
    #150): a game over by turn `cut` keeps its result (3 / 0; a draw 1 / 1); an unfinished one goes to the side that took
    more Prizes by the time turn cut + 1 begins (2 / 0), a Prize tie 1 / 1. Exact with the run's prizeTrace."""
    if r["turns"] <= cut:
        return (3, 0) if r["aScore"] == 1 else (0, 3) if r["aScore"] == 0 else (1, 1)
    at = [e for e in r["prizeTrace"] if e[0] <= cut + 1][-1]
    a_left, b_left = at[1], at[2]
    return (2, 0) if a_left < b_left else (0, 2) if b_left < a_left else (1, 1)


def sts(rows, cuts=(30, 40, 50, 60, 70, 80)):
    if not rows or "prizeTrace" not in rows[0]:
        return
    print("  STS round rule, exact (cut in engine turns, both players' turns counted): walls' share of points "
          "[95% CI by pair], walls' points a game of 3, games unfinished at the cut")
    for c in cuts:
        pts = [sts_points(r, c) for r in rows]
        share = [{"i": r["i"], "j": r["j"], "aScore": a / (a + b)} for r, (a, b) in zip(rows, pts)]
        tot_a, tot = sum(a for a, _ in pts), sum(a + b for a, b in pts)
        _, lo, hi = boot_ci(share)
        print(f"    {c:3d}: share {tot_a / tot:.3f} [{lo:.3f}, {hi:.3f}], points {tot_a / len(rows):.2f}, unfinished "
              f"{sum(1 for r in rows if r['turns'] > c) / len(rows):.0%}")


def paired(ra, rb, na, nb):
    ka = {(r["i"], r["j"], r["g"]): r for r in ra}
    common = [(ka[(r["i"], r["j"], r["g"])], r) for r in rb if (r["i"], r["j"], r["g"]) in ka]
    if not common:
        return
    assert all(x["seed"] == y["seed"] for x, y in common)
    rows = [{"i": x["i"], "j": x["j"], "aScore": y["aScore"] - x["aScore"]} for x, y in common]
    m, lo, hi = boot_ci(rows)
    same = sum(1 for x, y in common if x["aScore"] == y["aScore"])
    print(f"\n== paired on {len(common)} identical deals: walls' score {nb} - {na} = {m:+.3f}  95% CI by pair "
          f"[{lo:+.3f}, {hi:+.3f}]; same result {same}, walls lost only under {nb} "
          f"{sum(1 for x, y in common if y['aScore'] < x['aScore'])}, won only under {nb} "
          f"{sum(1 for x, y in common if y['aScore'] > x['aScore'])}")
    a_m = np.mean([x["aScore"] for x, _ in common]); b_m = np.mean([y["aScore"] for _, y in common])
    print(f"   on these deals: {na} {a_m:.3f}, {nb} {b_m:.3f}")


def main():
    paths = sys.argv[1:]
    runs = [(Path(p).stem, load(p)) for p in paths]
    for n, r in runs:
        summary(n, r)
    if len(runs) >= 2:
        for k in range(1, len(runs)):
            paired(runs[0][1], runs[k][1], runs[0][0], runs[k][0])


if __name__ == "__main__":
    main()
