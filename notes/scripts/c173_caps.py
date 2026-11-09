"""C173, research's ask after #827: how many games hit MAX_TURN_STEPS (env/game.js, 250 steps in a turn), by arm? Search arm: from the dose logs, a run of consecutive searched decisions by one player in one game; a run at --run or over is flagged. Where a pod has a .caps log (notes/scripts/audit/c173_dose_worker.js, log only, from seed 49's pod 4), the direct count is read beside it, so the proxy is checked. Greedy arm: the .caps log of a greedy replay (c165_run.py --caps), if there. Writes the flagged deal seeds of both arms, for c173_b1.py --drop. Evaluation only; no games here.
  .venv/Scripts/python notes/scripts/c173_caps.py [--seed 48] [--run 200]
"""
import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def caps_of(f):
    """A .caps log: [seed, turn, steps, turnCapped, recent keys]. Deal seed -> capped turns, and the recent keys seen."""
    turns, keys = collections.defaultdict(set), collections.Counter()
    if f.exists():
        for line in open(f, encoding="utf-8"):
            if line.strip():
                s, t, _, _, recent = json.loads(line)
                turns[s].add(t)
                keys.update(recent)
    return turns, keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=48)
    ap.add_argument("--run", type=int, default=200)
    a = ap.parse_args()
    D = ROOT / ("runs/probe/C173-search-table/B1" if a.seed == 48 else f"runs/probe/C173-search-table/B1-s{a.seed}")
    flagged, games, direct, proxy_on_caps, keys = {}, 0, {}, set(), collections.Counter()
    runs_hist = collections.Counter()
    for f in sorted(D.glob("full_p*.json.dose.jsonl")):
        seq = collections.defaultdict(list)
        for line in open(f, encoding="utf-8"):
            if line.strip():
                s, p = json.loads(line)
                seq[s].append(p)
        games += len(seq)
        file_flags = {}
        for s, ps in seq.items():
            cur, n, mx = None, 0, 0
            for p in ps:
                n = n + 1 if p == cur else 1
                cur = p
                mx = max(mx, n)
            runs_hist[min(mx // 50 * 50, 300)] += 1
            if mx >= a.run:
                file_flags[s] = mx
        flagged.update(file_flags)
        caps = Path(str(f) + ".caps")
        if caps.exists():
            turns, k = caps_of(caps)
            direct.update({s: len(v) for s, v in turns.items()})
            keys.update(k)
            proxy_on_caps |= set(seq)
    greedy, gkeys = caps_of(D / "greedy_replay.json.caps")
    out = {"seed": a.seed, "search_games": games, "search_flagged_by_run": len(flagged), "run_at_least": a.run, "max_run_histogram": {str(k): v for k, v in sorted(runs_hist.items())},
           "search_direct": {"games_logged": len(proxy_on_caps), "capped_games": len(direct), "capped_turns": sum(direct.values()), "flagged_and_capped": sum(s in direct for s in flagged if s in proxy_on_caps), "flagged_in_logged": sum(s in proxy_on_caps for s in flagged), "top_recent_keys": keys.most_common(8)},
           "greedy_direct": {"replayed": (D / "greedy_replay.json").exists(), "capped_games": len(greedy), "capped_turns": sum(len(v) for v in greedy.values()), "top_recent_keys": gkeys.most_common(8)},
           "drop": sorted(set(flagged) | set(direct) | set(greedy))}
    (D / "capped.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    (D / "capped_seeds.json").write_text(json.dumps(out["drop"]), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "drop"}), "dropping", len(out["drop"]))


if __name__ == "__main__":
    main()
