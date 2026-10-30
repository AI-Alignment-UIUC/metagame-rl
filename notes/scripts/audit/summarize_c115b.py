"""C115b summary: runs/probe/C115-goldfish/c115b/wiggly_s<seed>.jsonl -> c115b/summary.json and a printout.
Attacker = the Wigglytuff agent: seat 1 on an even seed, seat 2 on an odd one. Run: .venv/Scripts/python.exe notes/scripts/audit/summarize_c115b.py [--seed 91]"""
import argparse, json
from collections import Counter
from pathlib import Path
import statistics as S

ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=91); args = ap.parse_args()
OUT = Path.cwd() / "runs/probe/C115-goldfish/c115b"
games = [json.loads(l) for l in (OUT / f"wiggly_s{args.seed}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
q = lambda x, p: None if not x else sorted(x)[min(len(x) - 1, int(p * len(x)))]
mean = lambda x: round(sum(x) / len(x), 3) if x else None
share = lambda n, d: round(n / d, 3) if d else None

rows, own_turns, endings, wave, atk_all = [], [], Counter(), [], []
for g in games:
    at = 1 if g["seed"] % 2 == 0 else 2
    ts = [t for t in g["turns"] if t["p"] == at]
    cum, six, ev, wig4 = 0, None, 0, False
    for n, t in enumerate(ts, 1):
        cum += t["prizes"]; ev += t["evolve"]
        if n == 4: wig4 = ev > 0
        if six is None and cum >= 6: six = n
    if len(ts) < 4: wig4 = ev > 0
    won = g["winner"] == at
    end = six if six else (len(ts) if won else None)
    endings[f'{"win" if won else "loss/draw"}:{g["ending"]}'] += 1
    rows.append({"seed": g["seed"], "own_turns": len(ts), "finish": end, "won": won, "ending": g["ending"], "wig_by_4": wig4})
    for t in ts:
        for a in t["A"]:
            atk_all.append((t, a))
            if a["ac"] == "Wigglytuff JU" and a["an"] == "Do the Wave": wave.append((t, a))
fin = [r["finish"] for r in rows if r["finish"]]
inf = [r["finish"] if r["finish"] else float("inf") for r in rows]
ok = [r["finish"] for r in rows if r["finish"] and r["wig_by_4"]]
def iqr(x): return [q(x, .25), q(x, .75)] if x else None
res = {"games": len(games), "errors": sum(1 for g in games if g["error"]), "endings": dict(endings),
  "finished_games": len(fin), "median_own_turns_finished_only": S.median(fin) if fin else None, "iqr_finished_only": iqr(fin),
  "median_own_turns_unfinished_as_inf": S.median(inf), "iqr_unfinished_as_inf": iqr(inf),
  "never_came_together_share": share(sum(1 for r in rows if not r["wig_by_4"]), len(rows)),
  "came_together_games": sum(1 for r in rows if r["wig_by_4"]), "median_came_together_finished": S.median(ok) if ok else None,
  "iqr_came_together_finished": iqr(ok), "came_together_unfinished": sum(1 for r in rows if r["wig_by_4"] and not r["finish"]),
  "do_the_wave_attacks": len(wave), "wave_bench_dist": {str(k): sum(1 for _, a in wave if a["bA"] == k) for k in range(6)},
  "wave_five_benched_share": share(sum(1 for _, a in wave if a["bA"] == 5), len(wave)), "wave_mean_bench": mean([a["bA"] for _, a in wave]),
  "wave_mean_dealt": mean([t["dmg"] for t, _ in wave]), "wave_mean_10_plus_10_bench": mean([10 + 10 * a["bA"] for _, a in wave]),
  "wave_dealt_equals_10_plus_10_bench_share": share(sum(1 for t, a in wave if t["dmg"] == 10 + 10 * a["bA"]), len(wave)),
  "wave_dealt_equals_with_PP_WR_share": share(sum(1 for t, a in wave if t["dmg"] == max(0, (10 + 10 * a["bA"] + 10 * a["pp"]) * a["mult"] + a["mod"] - 20 * a["df"])), len(wave)),
  "all_attacks": len(atk_all), "pluspower_played_per_wave_attack": share(sum(t["ppP"] for t, _ in wave), len(wave)),
  "wave_with_pluspower_attached_share": share(sum(1 for _, a in wave if a["pp"] > 0), len(wave)),
  "pluspower_played_per_any_attack": share(sum(t["ppP"] for t, _ in atk_all), len(atk_all)),
  "any_attack_with_pluspower_share": share(sum(1 for _, a in atk_all if a["pp"] > 0), len(atk_all)),
  "item_finder_returned_pluspower": sum(t["ifPP"] for g in games for t in g["turns"] if t["p"] == (1 if g["seed"] % 2 == 0 else 2)),
  "oak_bill_held_turns": 0, "oak_bill_held_unplayed_share": None}
own = [t for g in games for t in g["turns"] if t["p"] == (1 if g["seed"] % 2 == 0 else 2)]
held = [t for t in own if t["ob"] > 0]
res["oak_bill_held_turns"] = len(held); res["oak_bill_held_unplayed_share"] = share(sum(1 for t in held if t["obp"] == 0), len(held))
med = res["median_own_turns_unfinished_as_inf"]
res["band"] = "R-engine-ok" if med <= 10 else ("R-engine-slow (bench/PP conditions: check)" if med >= 16 else "between")
(OUT / "summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
