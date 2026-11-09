"""C162 (runs/probe/C162-draw-shape/record.md): the draw price (copy with 2 Oak + 2 Bill for 4 basic Energy - deck, event points/3,
paired by deal; c145_read.per_deal) on the 99 shape-bounded rules-only wide decks under arm 0 s1, with a bootstrap SE (c139_read.boot),
C145's checks (c142_read's, the copy limit, copy differs by exactly the recorded cards), the record's bands against C145 C's +0.014,
each deck's own price against its P, T and E (correlation and slope over decks), the set's mean shape and its decks' own draw copies.
Writes summary.json.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c162_read.py [--file C_s91.json]
"""
import argparse
import json
from pathlib import Path

import numpy as np

import c142_read as C142
from c139_read import boot, r3
from c145_read import copy_checks, per_deal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C162-draw-shape"
C145_C = 0.014
DRAW = ("Professor Oak", "Bill", "Gambler")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="C_s91.json")
    a = ap.parse_args()
    p = OUT / a.file
    s = C142.read([p])
    r, d = per_deal(p, "oakbill", -1)
    xs = list(d.values())
    price, se = sum(xs) / len(xs), boot(xs)
    decks = json.loads((OUT / "decks.json").read_text(encoding="utf-8"))
    lst = {m["key"]: m["list"] for m in r["meta"]}
    per = {}
    for (key, _), x in d.items():
        per.setdefault(lst[key], []).append(x)
    ks = sorted(per)
    y = np.array([np.mean(per[k]) for k in ks])
    pte = np.array([decks[k]["pte"] for k in ks], dtype=float)
    shape = {}
    for i, n in enumerate(("pokemon", "trainer", "energy")):
        x = pte[:, i]
        shape[n] = {"corr": r3(float(np.corrcoef(x, y)[0, 1])), "slope_per_card": r3(float(np.polyfit(x, y, 1)[0]))}
    from rl.decks import Pool
    card = {c["fullName"]: c for c in Pool().cards}
    own = [sum(card[x]["name"] in DRAW for x in dk["cards"]) for dk in decks]
    band = ("R-shape" if price >= 0.04 and price - C145_C >= 0.03 else "R-not-shape" if price < 0.025 else "between")
    out = {"pilot": r["pilot"], "deals": len(xs), "errors": s["errors"], "price": r3(price), "se": r3(se), "band": band,
           "vs_C145_C": r3(price - C145_C), "decks_with_copy": len(r["variants"]), "per_deck_price_sd": r3(float(y.std())),
           "checks": {**s["checks"], **copy_checks(r)}, "added": {f"{n} {c}": sum(1 for v in r["variants"] if v["added"].get(c) == n)
                                                                   for c in ("Professor Oak", "Bill") for n in (1, 2)},
           "mean_pte": np.round(np.mean([dk["pte"] for dk in decks], 0), 2).tolist(), "own_draw_copies_mean": r3(float(np.mean(own))),
           "price_vs_shape": shape}
    (OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
