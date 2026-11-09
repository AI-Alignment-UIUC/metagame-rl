"""C185 (runs/probe/C185-judge-read/record.md): does D's strength survive a judge that didn't build it? D's top 12 at 29, both seeds, and the lists on G3's design under a judge; M, win share, full wins and losses, event points, with and without deck-outs; D - lists on M, the lists read on all 24 and on the same design. R-holds: at or above -0.05 at both seeds. R-judge: at or below -0.12 and 2 SE at both. Between otherwise. Beside it: D's Energy Removal copies against M by opponent, a deck's mean M against its copies, and by opponent list M for decks at 3+ copies against under 3.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c185_read.py [--judge arm0]
"""
import argparse
import json
from pathlib import Path

import numpy as np

from c139_read import r3
from g3_yardstick import reads
from probe_meta_premise import best_decks
from rl.decks import Pool

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "runs/probe/C185-judge-read"
card = {c["fullName"]: c for c in Pool().cards}
keep = ("games", "M", "se_pairs", "win_share_all_games", "full_wins", "full_losses", "no_winner_share", "event_points")


def row(rows):
    a, b = reads(rows), reads([x for x in rows if x.get("ending") != "deck-out"])
    out = {"all": {k: a[k] for k in keep}, "no_deck_outs": {k: b[k] for k in keep}}
    out["own_deck_out_losses"] = r3(sum(x.get("ending") == "deck-out" and x["winner"] in (1, 2) and x["winner"] != x["iSeat"] for x in rows) / len(rows))
    out["opp_deck_outs"] = r3(sum(x.get("ending") == "deck-out" and x["winner"] == x["iSeat"] for x in rows) / len(rows))
    return out


def er_read(f, seed):
    rows = json.loads(f.read_text(encoding="utf-8"))["results"]
    decks = best_decks(f"runs/screens/C182-D-s{seed}/population_it0029.pt", 12)
    er = [sum(card[c]["name"] == "Energy Removal" for c in d["cards"]) for d in decks]
    wins, dec = {}, {}
    for x in rows:
        k = (x["i"], x["j"])
        if x["winner"] in (1, 2):
            dec[k] = dec.get(k, 0) + 1
            wins[k] = wins.get(k, 0) + (x["winner"] == x["iSeat"])
    m = {k: wins.get(k, 0) / d for k, d in dec.items()}
    by_deck = [float(np.mean([v for (i, _), v in m.items() if i == q])) for q in range(12)]
    lists = [d["name"] for d in json.loads((ROOT / "runs/probe/C163-draw-deck-field/L.json").read_text(encoding="utf-8"))]
    by_opp = []
    for j in sorted({k[1] for k in m}):
        hi = [v for (i, q), v in m.items() if q == j and er[i] >= 3]
        lo = [v for (i, q), v in m.items() if q == j and er[i] < 3]
        by_opp.append((lists[j - 12], r3(float(np.mean(hi))) if hi else None, r3(float(np.mean(lo))) if lo else None))
    with_both = [x for x in by_opp if x[1] is not None and x[2] is not None]
    with_both.sort(key=lambda x: -(x[1] - x[2]))
    return {"er_copies": er, "deck_M": [r3(x) for x in by_deck], "corr_er_M": r3(float(np.corrcoef(er, by_deck)[0, 1])) if len(set(er)) > 1 else None, "decks_3_plus": int(sum(x >= 3 for x in er)), "M_3_plus": r3(float(np.mean([v for (i, _), v in m.items() if er[i] >= 3]))) if any(x >= 3 for x in er) else None, "M_under_3": r3(float(np.mean([v for (i, _), v in m.items() if er[i] < 3]))) if any(x < 3 for x in er) else None, "opponents_most_helped": with_both[:4], "opponents_least_helped": with_both[-4:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", default="arm0")
    a = ap.parse_args()
    j = a.judge
    out = {"judge": j}
    lists = json.loads((D / f"{j}_lists.json").read_text(encoding="utf-8"))
    out["lists"] = {**row(lists["results"]), "shape": lists["shape_mean"], "errors": lists["errors"], "draws_of_12": lists.get("draws_of_12")}
    lm = out["lists"]["all"]["M"]
    for s, tag in ((48, "d48"), (49, "d49")):
        f = D / f"{j}_{tag}.json"
        if not f.exists():
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        v = {**row(r["results"]), "shape": r["shape_mean"], "errors": r["errors"], "er": er_read(f, s)}
        v["D_minus_lists"] = r3(v["all"]["M"] - lm)
        v["se"] = r3((v["all"]["se_pairs"] ** 2 + out["lists"]["all"]["se_pairs"] ** 2) ** 0.5)
        v["D_minus_lists_no_deck_outs"] = r3(v["no_deck_outs"]["M"] - out["lists"]["no_deck_outs"]["M"])
        out[tag] = v
    if "d48" in out and "d49" in out:
        x = [out["d48"], out["d49"]]
        out["band"] = "R-holds" if all(q["D_minus_lists"] >= -0.05 for q in x) else "R-judge" if all(q["D_minus_lists"] <= -0.12 and q["D_minus_lists"] <= -2 * q["se"] for q in x) else "between"
    (D / f"summary_{j}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({"judge": j, "band": out.get("band")}))
    print("lists", json.dumps({k: out["lists"][k] for k in ("all", "no_deck_outs", "own_deck_out_losses", "opp_deck_outs", "shape", "draws_of_12")}))
    for t in ("d48", "d49"):
        if t in out:
            print(t, json.dumps({k: out[t][k] for k in out[t]}))


if __name__ == "__main__":
    main()
