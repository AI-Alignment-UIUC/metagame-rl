"""C156 (runs/probe/C156-concentrated-practice/record.md): per training seed, the W and K pilots' draw-group price on the California lists
(c145_read.per_deal on c142_run.py --groups draw --arm G, C146's cell design, seed-91 deals) with the paired K - W difference and its
bootstrap SE (c139_read.boot); each pilot's head-to-head win share against arm 0 (c147_h2h.py); each arm's training iterations; and the
record's bands. Writes summary.json.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c156_read.py
"""
import json
from pathlib import Path

from c139_read import boot, r3
from c145_read import per_deal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C156-concentrated-practice"


def practice_shapes() -> dict:
    """Each practice set's distinct decks: mean P / T / E and mean distinct Trainers a deck (C156 Amendment 1)."""
    import sys
    import numpy as np
    sys.path.insert(0, str(ROOT))
    from rl.decks import Pool, deck_shape
    pool = Pool()
    card = {c["id"]: c for c in pool.cards}
    out = {}
    for arm in ("W", "K"):
        f = OUT / f"{arm}_matchups.json"
        if not f.exists():
            continue
        decks = {d["name"]: d["cards"] for m in json.loads(f.read_text(encoding="utf-8")) for d in m}
        sh, nt = [], []
        for cards in decks.values():
            v = pool.vector(cards)
            s = deck_shape(pool, v)
            sh.append([s["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"]])
            nt.append(sum(1 for i in np.nonzero(v)[0] if card[int(i)]["superType"] == 2))
        out[arm] = {"decks": len(decks), "mean_pte": np.round(np.mean(sh, 0), 2).tolist(), "distinct_trainers": round(float(np.mean(nt)), 2)}
    return out


def main():
    out, diffs = {"seeds": {}}, {}
    for s in (1, 2):
        row, d = {}, {}
        for arm in ("W", "K"):
            p = OUT / f"draw_{arm}{s}_s91.json"
            if not p.exists():
                continue
            _, d[arm] = per_deal(p, "draw", 1)
            xs = list(d[arm].values())
            h = json.loads((OUT / f"h2h_{arm}{s}.json").read_text()) if (OUT / f"h2h_{arm}{s}.json").exists() else {}
            tr = json.loads((OUT / f"arm-{arm}{s}" / "result.json").read_text()).get("train", {}) if (OUT / f"arm-{arm}{s}" / "result.json").exists() else {}
            row[arm] = {"price": r3(sum(xs) / len(xs)), "se": r3(boot(xs)), "deals": len(xs), "h2h_vs_arm0": h.get("slot1_win_share"),
                        "h2h_se": h.get("se"), "iterations": tr.get("iterations"), "games": tr.get("games")}
        if "W" in d and "K" in d:
            keys = sorted(set(d["W"]) & set(d["K"]))
            xs = [d["K"][k] - d["W"][k] for k in keys]
            row["K_minus_W"] = {"mean": r3(sum(xs) / len(xs)), "se": r3(boot(xs)), "deals": len(keys)}
            diffs[s] = (row["K_minus_W"]["mean"], row["K"]["price"])
        out["seeds"][s] = row
    if len(diffs) == 2:
        learns = all(kw >= 0.03 and k >= 0.06 for kw, k in diffs.values())
        nott = all(abs(kw) < 0.03 for kw, _ in diffs.values())
        out["band"] = "R-learns-draw" if learns else "R-not" if nott else "between"
    out["references"] = {"start_pilot": 0.028, "arm0": 0.095}
    out["practice_sets"] = practice_shapes()             # Amendment 1: K's decks also carry more Pokemon, so both sets' shapes
    (OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
