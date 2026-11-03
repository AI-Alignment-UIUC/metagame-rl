"""C182's Amendment 3 reads at 44 (runs/probe/C182-trainer-table-drafting/record.md). Frozen G3: the top 12 at 44 that were in the population at 0 against their own iteration-0 versions, paired by deck, same deals, C49-sd, greedy, so it's edits alone (g3_yardstick.py --ids-from). G2: answer_key's archetypes and staples on the top 12, against W's at the same iteration. The top 12's table value, the mean z a Trainer copy and the sum a deck, at 0, 29 and 44, against W's. Whose deck-outs: c177_deckout.py.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c182_amend3.py
"""
import json
from pathlib import Path

import numpy as np

from c139_read import r3
from probe_meta_premise import best_decks
from rl.answer_key import archetypes, staples
from rl.decks import Pool, archived_decks

ROOT = Path(__file__).resolve().parents[2]
Y = ROOT / "runs/probe/C177-g3-yardstick"
pool = Pool()
card = {c["fullName"]: c for c in pool.cards}
table = json.loads((ROOT / "runs/probe/C182-trainer-table-drafting/table.json").read_text(encoding="utf-8"))
v = np.array(list(table.values()))
z = {n: float((x - v.mean()) / v.std()) for n, x in table.items()}


def by_deck(rows):
    wins, dec = {}, {}
    for x in rows:
        k = (x["i"], x["j"])
        if x["winner"] in (1, 2):
            dec[k] = dec.get(k, 0) + 1
            wins[k] = wins.get(k, 0) + (x["winner"] == x["iSeat"])
    return {k: wins.get(k, 0) / d for k, d in dec.items()}


def frozen(s):
    f, g = Y / f"frozen_d{s}.json", Y / f"d{s}_0044.json"
    if not (f.exists() and g.exists()):
        return None
    run = f"runs/screens/C182-D-s{s}/"
    now = best_decks(run + "population_it0044.pt", 12)
    then = best_decks(run + "population_it0000.pt", 999)
    ids = {d["name"]: d for d in then}
    kept = [d["name"] for d in now if d["name"] in ids]
    a, b = by_deck(json.loads(g.read_text(encoding="utf-8"))["results"]), by_deck(json.loads(f.read_text(encoding="utf-8"))["results"])
    names_now = [d["name"] for d in now]
    diffs = []
    for k, name in enumerate(kept):
        i_now = names_now.index(name)
        pairs = [(a[(i_now, 12 + j)], b[(k, len(kept) + j)]) for j in range(24) if (i_now, 12 + j) in a and (k, len(kept) + j) in b]
        diffs.append({"deck": name, "now": r3(float(np.mean([p[0] for p in pairs]))), "at_0": r3(float(np.mean([p[1] for p in pairs]))), "cards_changed": int(sum(abs(np.array(pool.vector(now[i_now]["cards"])) - np.array(pool.vector(ids[name]["cards"])))) // 2)})
    d = np.array([x["now"] - x["at_0"] for x in diffs])
    return {"of_12": len(kept), "M_now": r3(float(np.mean([x["now"] for x in diffs]))) if diffs else None, "M_at_0": r3(float(np.mean([x["at_0"] for x in diffs]))) if diffs else None, "edits_gain": r3(float(d.mean())) if len(d) else None, "se_decks": r3(float(d.std(ddof=1) / len(d) ** 0.5)) if len(d) > 1 else None, "decks": diffs}


def value(decks):
    t = [[z.get(card[c]["name"]) for c in d["cards"] if card[c]["superType"] == 2 and card[c]["name"] in z] for d in decks]
    return {"mean_z_a_copy": r3(float(np.mean([np.mean(x) for x in t if x]))), "sum_z_a_deck": r3(float(np.mean([np.sum(x) for x in t]))), "trainers": r3(float(np.mean([len(x) for x in t])))}


def g2(path):
    decks = best_decks(path, 12)
    vecs = [np.array(pool.vector(d["cards"])) for d in decks]
    w = np.ones(len(vecs)) / len(vecs)
    field = archived_decks(pool)
    st = staples(pool, vecs, w, [x for _, x in field], 0.75)
    ar = archetypes(vecs, [d["name"] for d in decks], w, [x for _, x in field], [n for n, _ in field], 0.5)
    return {"staples": {k: st[k] for k in ("staples", "recall", "count_agreement") if k in st}, "archetypes": {"total": ar["archetypes"], "rediscovered_at_0.5": ar["rediscovered"], "best": [(x["archetype"], r3(float(x["best_overlap"]))) for x in ar["rows"][:4]]}}


def main():
    out = {}
    for s in (48, 49):
        r = f"runs/screens/C182-D-s{s}/population_it"
        w = f"runs/screens/C171-W-s{s}/population_it"
        out[str(s)] = {"frozen": frozen(s), "table_value": {"D_0": value(best_decks(r + "0000.pt", 12)), "D_29": value(best_decks(r + "0029.pt", 12)), "D_44": value(best_decks(r + "0044.pt", 12)), "W_44": value(best_decks(w + "0044.pt", 12))}, "G2": {"D_44": g2(r + "0044.pt"), "W_44": g2(w + "0044.pt")}}
    (ROOT / "runs/probe/C182-trainer-table-drafting/amend3.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, default=float))


if __name__ == "__main__":
    main()
