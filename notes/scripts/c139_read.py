"""C139 (runs/probe/C139-pp-field-price/record.md): PlusPower's price against a field, per arm (G, S): over paired deals (a list and its
PlusPower -> Energy copy against the same opponent, seed and seat), the mean difference list - copy in event points over 3 (full win 1,
win on time 2/3, draw 1/3, loss 0) with a bootstrap SE over deals (2,000), the same in win share (draws half), and per list. With both
arms, S - G on the same deals, and the record's bands. Checks: copies hold no PlusPower and as many cards, and every key's list and copy
games share their seeds and seats. Writes summary.json.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c139_read.py [--seed 91] [--tag ""]
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C139-pp-field-price"
bare = lambda n: str(n).rsplit(" ", 1)[0]
r3 = lambda x: None if x is None else round(x, 4)


WDL = False                                           # C140 S-off: an untimed game scores win 1, draw 0.5, loss 0


def pts(r):                                          # deck i's event points over 3 (or WDL), and its win share
    win, draw = r["winner"] == r["iSeat"], r["winner"] not in (1, 2)
    p = (0.5 if draw else 1.0 if win else 0.0) if WDL else 1 / 3 if draw else (2 / 3 if r.get("ending") == "time" else 1.0) if win else 0.0
    return p, 0.5 if draw else 1.0 if win else 0.0


def boot(xs, reps=2000):
    rng = random.Random(139)
    n = len(xs)
    ms = [sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(reps)]
    m = sum(ms) / reps
    return (sum((x - m) ** 2 for x in ms) / (reps - 1)) ** 0.5


def arm(path):
    r = json.loads(path.read_text(encoding="utf-8"))
    names, cards = r["deck_names"], r["deck_cards"]
    checks = {"copies_without_pp": all(not any(bare(c) == "PlusPower" for c in cards[v["variant"]]) for v in r["variants"]),
              "same_card_count": all(len(cards[v["variant"]]) == len(cards[v["base"]]) for v in r["variants"])}
    by = {(x["i"], x["j"], x["seed"]): x for x in r["results"] if not x.get("error")}
    diffs, wins, per_list, seat_ok, n_err = {}, {}, defaultdict(list), True, sum(1 for x in r["results"] if x.get("error"))
    for m in r["meta"]:
        seeds_l = {s for (i, j, s) in by if i == m["list"] and j == m["opp"]}
        seeds_c = {s for (i, j, s) in by if i == m["copy"] and j == m["opp"]}
        for s in seeds_l & seeds_c:
            gl, gc = by[(m["list"], m["opp"], s)], by[(m["copy"], m["opp"], s)]
            seat_ok &= gl["iSeat"] == gc["iSeat"]
            (pl, wl), (pc, wc) = pts(gl), pts(gc)
            diffs[(m["key"], s)] = pl - pc
            wins[(m["key"], s)] = wl - wc
            per_list[names[m["list"]]].append(pl - pc)
        checks.setdefault("unpaired_keys", 0)
        checks["unpaired_keys"] += len(seeds_l ^ seeds_c)
    checks["paired_seats_equal"] = seat_ok
    xs, ws = list(diffs.values()), list(wins.values())
    return diffs, {"deals": len(xs), "errors": n_err, "price": r3(sum(xs) / len(xs)) if xs else None, "se": r3(boot(xs)) if xs else None,
                   "win_share_diff": r3(sum(ws) / len(ws)) if ws else None,
                   "by_list": {k: r3(sum(v) / len(v)) for k, v in sorted(per_list.items())}, "checks": checks,
                   "search": r.get("last", {}).get("search")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--tag", default="")
    ap.add_argument("--arms", nargs="*", default=["G", "S"], help="C140: e.g. S60 Soff (files <arm>_s<seed><tag>.json)")
    ap.add_argument("--wdl", action="store_true", help="C140 S-off: win 1, draw 0.5, loss 0")
    a = ap.parse_args()
    global WDL
    WDL = a.wdl
    d, out = {}, {}
    for name in a.arms:
        p = OUT / f"{name}_s{a.seed}{a.tag}.json"
        if p.exists():
            d[name], out[name] = arm(p)
    if "G" in d and "S" in d:
        keys = sorted(set(d["G"]) & set(d["S"]))
        xs = [d["S"][k] - d["G"][k] for k in keys]
        out["S_minus_G"] = {"deals": len(keys), "mean": r3(sum(xs) / len(xs)), "se": r3(boot(xs))}
        s, g, sg = out["S"]["price"], out["G"]["price"], out["S_minus_G"]["mean"]
        out["band"] = "R-search-favors" if s >= 0.04 and sg >= 0.04 else "R-parity" if abs(s) < 0.04 else "between"
        out["R_greedy_under"] = g <= -0.04
    (OUT / f"summary{a.tag}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
