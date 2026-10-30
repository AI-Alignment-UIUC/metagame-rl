"""C115 (goldfish probe): summary of runs/probe/C115-goldfish/<pilot>_P<list>_s<seed>.jsonl per attacker and list, the record's band on SimpleBot, and
the Goldfish check. The attacker is seat 1 on an odd seed, seat 2 on an even one (goldfish_worker.js). Writes summary.json.
Run: .venv/Scripts/python.exe notes/scripts/audit/summarize_goldfish.py [--seed 91]"""
import argparse, collections, json, statistics
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=91)
args = ap.parse_args()
OUT = Path.cwd() / "runs/probe/C115-goldfish"
LISTS = {0: "list 3", 1: "list 1", 2: "list 21", 3: "list 2"}
PILOTS = ["simplebot", "arm0", "start"]
r = lambda x, k=2: None if x is None else round(x, k)


def q(x):
    if len(x) < 2: return [x[0]] * 3 if x else [None] * 3
    return [r(v, 1) for v in statistics.quantiles(x, n=4, method="inclusive")]


def summarize(games):
    six, first, rows, gf = [], [], [], collections.Counter()
    for g in games:
        gs = 2 if g["seed"] % 2 == 0 else 1
        at = 3 - gs
        mine = [t for t in g["turns"] if t["p"] == at]
        for t in g["turns"]:
            if t["p"] == gs:
                gf["turns"] += 1
                for k in ("att", "atk", "trainers", "retreat", "evolve", "sw"): gf[k] += t[k]
        rows += mine
        if g["ending"] == "prizes" and g["winner"] == at: six.append(len(mine))
        i = next((i for i, t in enumerate(mine, 1) if t["kos"]), None)
        if i: first.append(i)
    n, nt = len(games), len(rows)
    pay = [t for t in rows if t["payE"] is not None]
    return {"games": n, "errors": sum(1 for g in games if g["error"]), "attacker_own_turns": nt,
            "six_prizes_share": r(len(six) / n, 3), "six_prizes_games": len(six), "median_own_turns_to_six": statistics.median(six) if six else None,
            "iqr_own_turns_to_six_q1_med_q3": q(six),
            "first_ko_games": len(first), "median_own_turns_to_first_ko": statistics.median(first) if first else None,
            "kos_per_own_turn": r(sum(t["kos"] for t in rows) / nt, 3), "endings": dict(collections.Counter(g["ending"] for g in games)),
            "payable_attack_share_end_of_turn": r(sum(1 for t in pay if t["payE"]) / len(pay), 3),
            "energy_attached_per_own_turn": r(sum(t["att"] for t in rows) / nt, 3),
            "goldfish": dict(gf)}


out = {}
for p in PILOTS:
    out[p] = {}
    for di, name in LISTS.items():
        f = OUT / f"{p}_P{di}_s{args.seed}.jsonl"
        if f.exists(): out[p][name] = summarize([json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()])
sb = [v["median_own_turns_to_six"] for v in out["simplebot"].values()]
lo = sum(1 for m in sb if m is not None and m <= 10); hi = sum(1 for m in sb if m is None or m >= 16)
out["band_simplebot"] = {"medians": sb, "lists_le_10": lo, "lists_ge_16": hi, "band": "R-interaction" if lo >= 3 else "R-flow" if hi >= 3 else "between"}
(OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for p in PILOTS:
    for name, v in out[p].items():
        print(p, name, "| n", v["games"], "err", v["errors"], "six", v["six_prizes_share"], "med", v["median_own_turns_to_six"], v["iqr_own_turns_to_six_q1_med_q3"],
              "| 1stKO", v["median_own_turns_to_first_ko"], f"({v['first_ko_games']})", "ko/t", v["kos_per_own_turn"], "| pay", v["payable_attack_share_end_of_turn"],
              "en/t", v["energy_attached_per_own_turn"], "|", v["endings"], "| gf", v["goldfish"])
print(out["band_simplebot"])
