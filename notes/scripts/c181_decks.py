"""C181 with its Amendment 1 (runs/probe/C181-table-practice/record.md): the table-weighted practice decks, no training here. The two-seed mean of the plain fits' Trainer coefficients (c181_ranks.py, no card named, no list used), scaled z = (c - mean) / SD; 128 standard wide decks with each Trainer pick weighted exp(kappa z), kappa 1, Pokemon, Energy and special Energy picks unchanged (a special Energy's weight is 1), C156's matchup design. Reported: draw copies (Oak, Bill, Gambler) and Energy Removal copies a deck, and P/T/E, against W's and M's own decks, read from their matchups files. rl/decks.py isn't touched: wide_deck's plain branch is reproduced here with the one weighted line.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c181_decks.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "notes" / "scripts")]
from c156_decks import DRAW, M, N, matchups                             # noqa: E402
from rl.decks import DECK_SIZE, MAX_COPIES, Pool                        # noqa: E402

D = ROOT / "runs/probe/C181-table-practice"
SEED, KAPPA = 181, 1.0


def weighted_wide(pool, rng, lim_w):
    """wide_deck's plain branch (rl/decks.py), its limited pick weighted."""
    ok = [c for c in pool.cards if pool.allowed[c["id"]]]
    basics = [c for c in ok if c["superType"] == 1 and c["stage"] == 2]
    evolves = {}
    for c in ok:
        if c["superType"] == 1 and c.get("evolvesFrom"):
            evolves.setdefault(c["evolvesFrom"], []).append(c)
    limited = [c["id"] for c in ok if c["superType"] == 2 or (c["superType"] == 3 and c["energyType"] != 0)]
    energy = [c for c in ok if c["superType"] == 3 and c["energyType"] == 0]
    w = np.array([lim_w.get(pool.name[cid], 1.0) for cid in limited], dtype=float)
    w /= w.sum()

    def room(v, cid):
        return MAX_COPIES - int(pool.name_counts(np.where(pool.basic_energy, 0, v))[pool.name_of[cid]])

    def add(v, c, k):
        v[c["id"]] += max(0, min(k, room(v, c["id"])))

    while True:
        v = np.zeros(pool.n, dtype=np.int32)
        types = set()
        for i in rng.choice(len(basics), size=int(rng.integers(1, 5)), replace=False):
            b = basics[i]
            add(v, b, int(rng.integers(1, 5)))
            types |= {t for t, x in enumerate(b["types"]) if x}
            s1 = evolves.get(b["name"], [])
            if s1 and rng.random() < 0.6:
                e1 = s1[rng.integers(len(s1))]
                add(v, e1, int(rng.integers(1, 4)))
                s2 = evolves.get(e1["name"], [])
                if s2 and rng.random() < 0.5:
                    add(v, s2[rng.integers(len(s2))], int(rng.integers(1, 3)))
        typed = [e for e in energy if any(e["provides"][t] for t in types)] or energy
        for _ in range(int(rng.integers(8, 35))):
            pick = typed if rng.random() < 0.75 else energy
            v[pick[rng.integers(len(pick))]["id"]] += 1
        for _ in range(2000):
            if v.sum() >= DECK_SIZE:
                break
            cid = limited[rng.choice(len(limited), p=w)]
            if room(v, cid) > 0:
                v[cid] += 1
        if pool.legal(v):
            return v


def stats(pool, card, decks):
    name = lambda x: card[x]["name"]
    rows = np.array([[sum(card[c]["superType"] == s for c in d["cards"]) for s in (1, 2, 3)] for d in decks])
    draw = [sum(name(c) in DRAW for c in d["cards"]) for d in decks]
    return {"decks": len(decks), "P_T_E": [round(float(x), 2) for x in rows.mean(0)], "draw_copies": round(float(np.mean(draw)), 2), "oak": round(float(np.mean([sum(name(c) == "Professor Oak" for c in d["cards"]) for d in decks])), 2), "bill": round(float(np.mean([sum(name(c) == "Bill" for c in d["cards"]) for d in decks])), 2), "energy_removal": round(float(np.mean([sum(name(c) == "Energy Removal" for c in d["cards"]) for d in decks])), 2), "decks_with_2_plus_draw": round(float(np.mean([x >= 2 for x in draw])), 3)}


def first_decks(path):
    seen, out = set(), []
    for a, b in json.loads(Path(path).read_text(encoding="utf-8")):
        for d in (a, b):
            if d["name"] not in seen:
                seen.add(d["name"])
                out.append(d)
    return out


def main():
    pool = Pool()
    card = {c["fullName"]: c for c in pool.cards}
    r = json.loads((D / "ranks.json").read_text(encoding="utf-8"))
    a, b = r["48"]["coefficients"], r["49"]["coefficients"]
    names = sorted(set(a) & set(b))
    c = np.array([(a[n] + b[n]) / 2 for n in names])
    z = (c - c.mean()) / c.std()
    weight = {n: float(np.exp(KAPPA * x)) for n, x in zip(names, z)}
    rng = np.random.default_rng(SEED)
    decks = [{"name": f"T{k}", "cards": pool.names(weighted_wide(pool, rng, weight))} for k in range(N)]
    (D / "T_decks.json").write_text(json.dumps(decks), encoding="utf-8")
    pair_rng = np.random.default_rng(SEED + 1)
    (D / "T_matchups.json").write_text(json.dumps(matchups(decks, pair_rng, M)), encoding="utf-8")
    assert all(len(d["cards"]) == DECK_SIZE and pool.legal(pool.vector(d["cards"])) for d in decks)
    out = {"table_top_8": sorted(((n, round(float(x), 2), round(weight[n], 2)) for n, x in zip(names, z)), key=lambda t: -t[1])[:8], "ranks_on_the_mean_table": {n: int(1 + sum(y > z[names.index(n)] for y in z)) for n in ("Professor Oak", "Energy Removal", "Bill")},
           "T": stats(pool, card, decks), "W": stats(pool, card, first_decks(ROOT / "runs/probe/C156-concentrated-practice/W_matchups.json")), "M": stats(pool, card, first_decks(ROOT / "runs/probe/C158-fixed-deck-practice/M_matchups.json"))}
    (D / "deck_stats.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
