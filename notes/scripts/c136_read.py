"""C136 (runs/probe/C136-pp-price-search/record.md): PlusPower's paired price against an Energy under the pilot's own full-width search.
Per arm (G, SPP, ST): the list's price against its PlusPower -> Energy copy as notes/scripts/c113_read.py's "points" (the list's event
points over both sides': full win 3, win on time 2, draw 1 each, loss 0), per list and pooled, and its "share" (wins, draws half); the
paired differences SPP - G and ST - SPP on the same deals (list, copy, seed), with SEs from a paired bootstrap over deals (2,000); pp@b10 (among the list's b10 states with PlusPower available, the share where it
was played first; c136_worker.js's rows); knockouts per damaging attack; Oak or Bill played on own turns that start with one in hand
(C114's trace, both seats). Then the record's bands. Writes summary.json.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c136_read.py [--seed 91] [--tag ""]
"""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C136-pp-price-search"
r3 = lambda x: None if x is None else round(x, 3)


def points(g):                                       # (the list's points, the copy's), c113_read.py's event points
    timeout, win, draw = g.get("ending") == "time", g["winner"] == g["iSeat"], g["winner"] not in (1, 2)
    lp = 1 if draw else (2 if timeout else 3) if win else 0
    cp = 1 if draw else 0 if win else (2 if timeout else 3)
    return lp, cp


def ratio(vals):
    l, s = sum(v[0] for v in vals), sum(v[0] + v[1] for v in vals)
    return l / s if s else None


def share(vals):
    return sum(0.5 if v[0] == v[1] else 1.0 if v[0] > v[1] else 0.0 for v in vals) / len(vals) if vals else None


def mse(xs):
    n = len(xs)
    if not n:
        return None, None
    m = sum(xs) / n
    return m, (math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1) / n) if n > 1 else None)


def arm(name, tag, seed):
    base = OUT / f"{name}_s{seed}{tag}"
    r = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))
    pairs = {(p["base"], p["variant"]) for p in r["pairs"]}
    names = r["deck_names"]
    per = {}
    for g in r["results"]:
        if (g["i"], g["j"]) in pairs and not g.get("error"):
            per[(g["i"], g["j"], g["seed"])] = points(g)
    by_list = {}
    for (i, j, s), v in per.items():
        by_list.setdefault(names[i], []).append(v)
    b10 = [json.loads(l) for l in base.with_suffix(".b10.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    st = [x for x in b10 if x["b10state"] and x["ppHand"] + x["pp"] >= 1]
    dmg = [x for x in b10 if x["base"] is not None and x["base"] > 0]
    turns = [t for l in base.with_suffix(".trace.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()
             for t in json.loads(l)["turns"]]
    held = [t for t in turns if t["ob"]]
    return per, {"games": len(per), "price": r3(ratio(list(per.values()))), "share": r3(share(list(per.values()))),
                 "by_list": {k: r3(ratio(v)) for k, v in by_list.items()},
                 "pp@b10": r3(sum(x["pp"] >= 1 for x in st) / len(st)) if st else None, "b10_states": len(st),
                 "ko_per_damaging_attack": r3(sum(x["ko"] for x in dmg) / len(dmg)) if dmg else None,
                 "ob_played_when_held": r3(sum(1 for t in held if t["obp"]) / len(held)) if held else None,
                 "search": r.get("last", {}).get("search")}


def diff(a, b, reps=2000):                            # the points-price difference on the same deals, with a paired bootstrap SE
    import random
    keys = sorted(set(a) & set(b))
    d = lambda ks: ratio([a[k] for k in ks]) - ratio([b[k] for k in ks])
    rng = random.Random(136)
    boot = [d([keys[rng.randrange(len(keys))] for _ in keys]) for _ in range(reps)]
    m = sum(boot) / reps
    return {"n": len(keys), "mean": r3(d(keys)), "se": r3((sum((x - m) ** 2 for x in boot) / (reps - 1)) ** 0.5)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    per, out = {}, {}
    for name in ("G", "SPP", "ST"):
        if (OUT / f"{name}_s{a.seed}{a.tag}.json").exists():
            per[name], out[name] = arm(name, a.tag, a.seed)
    if len(per) == 3:
        d1, d2 = diff(per["SPP"], per["G"]), diff(per["ST"], per["SPP"])
        out["SPP_minus_G"], out["ST_minus_SPP"] = d1, d2
        b1, b2 = d1["mean"] >= 0.04, d2["mean"] >= 0.04
        out["band"] = ("R-both" if b1 and b2 else "R-timing" if b1 and abs(d2["mean"]) < 0.04 else "R-flow" if b2 else
                       "R-flat" if not b1 and not b2 and abs(d2["mean"]) < 0.04 else "between")
    (OUT / f"summary{a.tag}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
