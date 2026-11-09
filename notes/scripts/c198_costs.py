"""C198 Part B (runs/probe/C198-typed-cost-check/record.md): the cost structure of decks' attacks, from pool.json, copy-weighted over
each deck's Pokemon cards and their attacks. B1 the Colourless share of cost symbols (cost[0] over all), B2 the share of attacks
payable with Colourless only (no typed symbol), B3 the typed share (1 - B1). Beside them, the deck's on-type basic Energy share (its
basic Energy copies whose type is one of its Pokemon's types) and its number of basic Energy types. Per deck, then the mean and
median over a set: W s48 and W s49 at 44 (all 99, and the top 24 by recent_score) and the 24 lists. CPU, seconds.
    PYTHONPATH=. .venv/Scripts/python notes/scripts/c198_costs.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "ar"))
from rl.metagame import recent_score   # noqa: E402

CARD = {c["fullName"]: c for c in json.load(open(ROOT / "notes/data/cards/pool.json", encoding="utf-8"))["cards"]}


def deck_costs(cards):
    cnt = Counter(cards)
    col = sym = atk = atk_col = 0.0
    ptypes, basics = set(), Counter()
    for f, k in cnt.items():
        c = CARD[f]
        if c["superType"] == 1:
            ptypes |= {i for i, v in enumerate(c["types"]) if v and i != 0}
            for a in c.get("attacks") or []:
                cost = a["cost"]
                n = sum(cost)
                col += k * cost[0]; sym += k * n
                atk += k; atk_col += k * (sum(cost[1:]) == 0)
        elif c["superType"] == 3 and c["energyType"] == 0:
            basics[next(i for i, v in enumerate(c["provides"]) if v)] += k
    nb = sum(basics.values())
    return {"B1": col / sym if sym else None, "B2": atk_col / atk if atk else None, "B3": 1 - col / sym if sym else None,
            "on_type": sum(v for t, v in basics.items() if t in ptypes) / nb if nb else None, "basic_types": len(basics)}


def summ(decks):
    rows = [deck_costs(d) for d in decks]
    out = {"decks": len(rows)}
    for k in ("B1", "B2", "B3", "on_type", "basic_types"):
        v = np.array([r[k] for r in rows if r[k] is not None], dtype=float)
        out[k] = {"mean": round(float(v.mean()), 4), "median": round(float(np.median(v)), 4)}
    return out


def main():
    import fixed
    ev = json.loads((fixed.DATA / "eval_decks.json").read_text(encoding="utf-8"))
    lists = [ev["decks"][i]["cards"] for i in sorted({p[0] for p in ev["pairs"]})]
    res = {"lists": summ(lists)}
    for run in ("C171-W-s48", "C171-W-s49"):
        pop = torch.load(ROOT / f"runs/screens/{run}/population_it0044.pt", map_location="cpu", weights_only=False)["population"]
        res[run] = {"all": summ([a["deck"] for a in pop]),
                    "top24": summ([a["deck"] for a in sorted(pop, key=lambda a: -recent_score(a, 0.0))[:24]])}
    for run in ("C171-W-s48", "C171-W-s49"):
        res[run]["B3_over_lists"] = round(res[run]["all"]["B3"]["mean"] / res["lists"]["B3"]["mean"], 3)
    out = ROOT / "runs/probe/C198-typed-cost-check/partB.json"
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
