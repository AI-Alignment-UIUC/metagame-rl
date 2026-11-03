"""C152 (runs/probe/C152-deck-counts/record.md, Amendment 1): the count-features arm (cf) against the control (c), both arm 0's recipe from
start, 30 minutes, seed 1. Readouts: cf's head-to-head win share against c on the California mirrors (c147_h2h.py, slot 1 = cf), with the
record's bands; each arm's draw-group price on C144's California pairs (c142_run.py --groups draw --arm G, as C146's cells) and cf - c paired
on the same deals; each arm's pp@b10 (C135's harness, notes/scripts/audit/c135_games.py --arm G --pilot). Writes summary.json.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c152_read.py [--dir runs/probe/C152b-count-features-rep --tag 2]
C152b: --dir and --tag (the pp@b10 files' tag) read the second training seed's run the same way.
"""
import argparse
import json
from pathlib import Path

from c139_read import boot, r3
from c145_read import per_deal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C152-deck-counts"
C135 = ROOT / "runs/probe/C135-fullwidth-pp"


def pp_b10(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")] if path.exists() else []
    b10 = [x for x in rows if x["b10state"] and x["ppHand"] + x["pp"] >= 1]
    return {"b10_states": len(b10), "pp@b10": r3(sum(x["pp"] >= 1 for x in b10) / len(b10)) if b10 else None}


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(OUT))
    ap.add_argument("--tag", default="", help="C152b: the pp@b10 files' tag after c152<arm>")
    a = ap.parse_args()
    OUT = Path(a.dir) if Path(a.dir).is_absolute() else ROOT / a.dir
    out = {}
    h = OUT / "h2h_s91.json"
    if h.exists():
        s = json.loads(h.read_text(encoding="utf-8"))
        ws, se = s["slot1_win_share"], s["se"]
        out["h2h"] = {k: s[k] for k in ("games", "errors", "slot1_win_share", "se", "by_slot1_seat", "slot1_wins", "slot0_wins", "draws")}
        out["band"] = ("R-input" if ws >= 0.53 and ws >= 0.5 + 2 * se else "Harm" if ws < 0.47 else
                       "R-null" if abs(ws - 0.5) <= 2 * se else "between")
    d = {}
    for arm in ("c", "cf"):
        p = OUT / f"draw_{arm}_s91.json"
        if p.exists():
            _, d[arm] = per_deal(p, "draw", 1)
            xs = list(d[arm].values())
            out[f"draw_{arm}"] = {"deals": len(xs), "price": r3(sum(xs) / len(xs)), "se": r3(boot(xs))}
        out[f"pp_b10_{arm}"] = pp_b10(C135 / f"G_s91_c152{arm}{a.tag}.jsonl")
    if "c" in d and "cf" in d:
        keys = sorted(set(d["c"]) & set(d["cf"]))
        xs = [d["cf"][k] - d["c"][k] for k in keys]
        out["draw_cf_minus_c"] = {"deals": len(keys), "mean": r3(sum(xs) / len(xs)), "se": r3(boot(xs))}
    (OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
