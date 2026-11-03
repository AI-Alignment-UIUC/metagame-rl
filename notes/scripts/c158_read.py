"""C158 (runs/probe/C158-fixed-deck-practice/record.md, Amendment 2): per training seed, the F and M pilots' draw-group price on the 20
held-out California lists (the 24 minus the 4 bench lists arm 0 trained on; c145_read.per_deal on c142_run.py --groups draw --arm G,
seed-91 deals, a deal kept when its list is held out), the paired F - M difference with a bootstrap SE (c139_read.boot), and M - K1m with
C156's K1m re-read on the same 20; each pilot's head to head against arm 0 and its training iterations; the record's bands. Writes
summary.json.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c158_read.py
"""
import json
from pathlib import Path

from c139_read import boot, r3
from c145_read import per_deal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C158-fixed-deck-practice"
K1M = ROOT / "runs/probe/C156-concentrated-practice/draw_K1m_s91.json"
BENCH = {d["name"] for m in json.loads((ROOT / "runs/probe/BENCH/bench_matchups.json").read_text(encoding="utf-8")) for d in m}


def held(path):
    """The per-deal prices of the deals whose list is one of the 20 held out."""
    r, d = per_deal(path, "draw", 1)
    names = r["deck_names"]
    keep = {m["key"] for m in r["meta"] if names[m["list"]] not in BENCH}
    return {k: v for k, v in d.items() if k[0] in keep}


def paired(a, b):
    keys = sorted(set(a) & set(b))
    xs = [a[k] - b[k] for k in keys]
    return {"mean": r3(sum(xs) / len(xs)), "se": r3(boot(xs)), "deals": len(keys)}


def main():
    out, diffs = {"seeds": {}}, {}
    k1m = held(K1M) if K1M.exists() else None
    if k1m:
        out["K1m_held_out_price"] = r3(sum(k1m.values()) / len(k1m))
    for s in (1, 2):
        row, d = {}, {}
        for arm in ("F", "M"):
            p = OUT / f"draw_{arm}{s}_s91.json"
            if not p.exists():
                continue
            d[arm] = held(p)
            xs = list(d[arm].values())
            h = json.loads((OUT / f"h2h_{arm}{s}.json").read_text()) if (OUT / f"h2h_{arm}{s}.json").exists() else {}
            res = OUT / f"arm-{arm}{s}" / "result.json"
            tr = json.loads(res.read_text()).get("train", {}) if res.exists() else {}
            row[arm] = {"price": r3(sum(xs) / len(xs)), "se": r3(boot(xs)), "deals": len(xs), "h2h_vs_arm0": h.get("slot1_win_share"),
                        "h2h_se": h.get("se"), "iterations": tr.get("iterations"), "games": tr.get("games")}
        if "F" in d and "M" in d:
            row["F_minus_M"] = paired(d["F"], d["M"])
            diffs[s] = row["F_minus_M"]
        if "M" in d and k1m:
            row["M_minus_K1m"] = paired(d["M"], k1m)
        out["seeds"][s] = row
    if len(diffs) == 2:
        rep = all(x["mean"] >= 0.03 and x["mean"] >= 2 * x["se"] for x in diffs.values())
        norep = all(abs(x["mean"]) < 0.03 for x in diffs.values())
        out["band"] = "R-repetition" if rep else "R-no-repetition" if norep else "between"
    out["held_out_lists"] = 24 - len(BENCH)
    out["practice_sets"] = json.loads((OUT / "decks.json").read_text())[:4] if (OUT / "decks.json").exists() else None
    (OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
