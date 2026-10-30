"""BENCH Amendment 5: the bench goal per card. From an arm's bench_eval.json (and arm 0's of the same seed as --ref): each
Trainer kind's pooled price with its 95% CI, its goal status (clearly above: p - 2SE >= 0.50; meets: p + 2SE >= 0.50;
misses), and its change over arm 0. Item Finder and Computer Search first, at 256 games (readout 1f); the rest at 64.

  PYTHONPATH=. .venv/Scripts/python notes/scripts/bench_cards.py --arm runs/probe/BENCH/eval-p2-s2 --ref runs/probe/BENCH/eval-arm0-s2
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOCUS = ("PlusPower", "Gust of Wind", "Item Finder", "Scoop Up", "Computer Search")   # Amendment 8


def prices(folder: Path) -> dict:
    """card -> (p, se, games a pair) from a bench_eval.json, the 256-game focus prices overriding the 64-game ones."""
    r = json.loads((folder / "bench_eval.json").read_text(encoding="utf-8"))
    out = {}
    for key in ("readout1", "readout1_focus"):
        x = r.get(key)
        if not x:
            continue
        price = x["pooled"]["price"] if key == "readout1" else x["pooled"]
        for k, v in price.items():
            out[k] = (v["score"], (v["ci"][1] - v["ci"][0]) / 3.92, x["games_per_pair"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--ref", help="arm 0's bench_eval folder of the same seed (and a 256-game eval256-* folder if separate)")
    ap.add_argument("--ref-focus", help="a folder with arm 0's 256-game focus prices, if not in --ref")
    a = ap.parse_args()
    arm = prices(ROOT / a.arm)
    ref = prices(ROOT / a.ref) if a.ref else {}
    if a.ref_focus:
        ref.update(prices(ROOT / a.ref_focus))
    order = [k for k in FOCUS if k in arm] + sorted(k for k in arm if k not in FOCUS)
    rows = []
    for k in order:
        p, se, g = arm[k]
        status = "clearly above" if p - 2 * se >= 0.5 else "meets" if p + 2 * se >= 0.5 else "misses"
        d = None if k not in ref else round(p - ref[k][0], 4)
        rows.append({"card": k, "p": round(p, 4), "ci": [round(p - 1.96 * se, 4), round(p + 1.96 * se, 4)], "games": g,
                     "status": status, "vs_arm0": d})
        print(f"{k:24s} {p:.3f} [{p - 1.96 * se:.3f}, {p + 1.96 * se:.3f}] ({g} games)  {status:13s}  "
              f"vs arm 0 {'' if d is None else f'{d:+.3f}'}")
    (ROOT / a.arm / "cards.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
