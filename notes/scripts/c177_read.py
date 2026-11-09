"""C177's read 3 (runs/probe/C177-g3-yardstick/record.md): W s49's top 12 at 59 and 74 and a draw of 12 lists against the 24 lists under C135's search, against each one's greedy read on the same pairs (not the same deals: 4 games a pair and 8 draw different seeds). M under search minus greedy's M, per pair, mean and SE over pairs. The band is on 59's top 12: R-survives, the change above -0.04 with 2 SE excluding -0.083; R-falls, at or under -0.083 and 2 SE; between otherwise. 74's and the lists' have no band.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c177_read.py
"""
import json
from pathlib import Path

import numpy as np

from g3_yardstick import reads

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "runs/probe/C177-g3-yardstick"
CELLS = {"w49_59": ("search59_*.json", "w49_0059.json"), "w49_74": ("search74_*.json", "w49_0074.json"), "lists": ("searchlists_*.json", "lists.json"), "D_s48_29": ("searchd48at29_*.json", "d48_0029.json"), "D_s49_29": ("searchd49at29_*.json", "d49_0029.json"), "D_s48_44": ("searchd48at44_*.json", "d48_0044.json"), "D_s49_44": ("searchd49at44_*.json", "d49_0044.json")}


def pair_m(rows):
    wins, dec = {}, {}
    for r in rows:
        k = (r["i"], r["j"])
        if r["winner"] in (1, 2):
            dec[k] = dec.get(k, 0) + 1
            wins[k] = wins.get(k, 0) + (r["winner"] == r["iSeat"])
    return {k: wins.get(k, 0) / d for k, d in dec.items()}


def read_cell(name, pattern, greedy_file, lists_of=None):
    rows = []
    meta = None
    for f in sorted(D.glob(pattern)):
        r = json.loads(f.read_text(encoding="utf-8"))
        rows += r["results"]
        meta = r
    if not rows:
        return None
    g = json.loads((D / greedy_file).read_text(encoding="utf-8"))
    grows = g["results"]
    if name == "lists":                                   # the draw's deck k is the list meta["picked"][k]; the greedy matrix has all 24, in list order
        picked = meta["picked"]
        rows_key = [{**r, "i": picked[r["i"]], "j": r["j"] - len(picked)} for r in rows]
        grows_key = [{**r, "j": r["j"] - 24} for r in grows if r["i"] in set(picked)]
    else:
        rows_key, grows_key = rows, grows
    keys = {(r["i"], r["j"], r["seed"]) for r in rows_key}
    pairs = {(r["i"], r["j"]) for r in rows_key}
    same = [r for r in grows_key if (r["i"], r["j"]) in pairs]     # the same pairs: a deal's seed goes by games a pair, so 4 games a pair and 8 share no deals
    ms, mg = pair_m(rows_key), pair_m(same)
    both = sorted(set(ms) & set(mg))
    d = np.array([ms[k] - mg[k] for k in both])
    return {"games": len(rows), "errors": meta.get("errors", 0), "shape_mean": meta["shape_mean"], "matched_deals": sum((r["i"], r["j"], r["seed"]) in keys for r in grows_key), "pairs_compared": len(both), "search": reads(rows), "greedy_same_pairs": reads(same) if same else None, "greedy_all": g["all"],
            "M_change": round(float(d.mean()), 4), "se_pairs": round(float(d.std(ddof=1) / np.sqrt(len(d))), 4)}


def main():
    out = {}
    for name, (pattern, greedy) in CELLS.items():
        if (D / greedy).exists():
            v = read_cell(name, pattern, greedy)
            if v:
                out[name] = v
    if "w49_59" in out:
        c, s = out["w49_59"]["M_change"], out["w49_59"]["se_pairs"]
        out["band_59"] = "R-survives" if c > -0.04 and c - 2 * s > -0.083 else "R-falls" if c <= -0.083 and c + 2 * s <= -0.083 else "between"
    (D / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("band_59", out.get("band_59"))
    for k, v in out.items():
        if isinstance(v, dict):
            print(k, json.dumps(v))


if __name__ == "__main__":
    main()
