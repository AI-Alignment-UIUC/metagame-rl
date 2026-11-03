"""C156 (runs/probe/C156-concentrated-practice/record.md): the two practice sets the bench arms train on, written as bench_train.py
--matchups files. W: 128 standard wide decks (rl/decks.py wide_deck); K: 128 concentrated ones (wide_deck(..., concentrated=True)), the
same RNG seed. Each set's 2,048 matchups (the start pilot's own practice size) are every deck's mirror plus 1,920 cross pairs drawn
uniformly (ordered, distinct decks). Rules-only: no human list enters.
C158 (runs/probe/C158-fixed-deck-practice/record.md, Amendment 2; a diagnostic, never the method): --select-draw N keeps, in seed
order from --seed, the concentrated decks holding N or more draw copies (Professor Oak, Bill, Gambler) until 128 are kept (set M,
C156's matchup design), and F is the first 4 kept (their 4 mirrors and 12 cross pairs); the kept decks' order numbers and draw copies
are printed, and both sets written to --out.
C162 (runs/probe/C162-draw-shape/record.md; evaluation decks only): --shape P0-P1,T0-T1,E0-E1 keeps, in seed order from --seed, the
standard wide decks (not concentrated) whose Pokemon, Trainers and Energy (basic and special) fall in those bounds until --n are
kept, and writes them to --out/decks.json as [{name, cards}].
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c156_decks.py
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c156_decks.py --select-draw 2 --seed 158 --out runs/probe/C158-fixed-deck-practice
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c156_decks.py --shape 12-15,26-30,16-20 --n 99 --seed 162 --out runs/probe/C162-draw-shape
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.decks import Pool, deck_shape, wide_deck  # noqa: E402

OUT = ROOT / "runs/probe/C156-concentrated-practice"
N, M, SEED = 128, 2048, 156


DRAW = ("Professor Oak", "Bill", "Gambler")


def matchups(decks, rng, m):
    pairs = [(k, k) for k in range(len(decks))]
    while len(pairs) < m:
        a, b = (int(x) for x in rng.choice(len(decks), 2, replace=False))
        pairs.append((a, b))
    return [[decks[a], decks[b]] for a, b in pairs]


def select_draw(pool, n_min, seed, out):
    """C158: concentrated decks in seed order, kept when they hold n_min or more draw copies, until N are kept."""
    rng, kept, tried = np.random.default_rng(seed), [], 0
    draw = np.isin(pool.name, DRAW)
    while len(kept) < N:
        v = wide_deck(pool, rng, concentrated=True)
        tried += 1
        d = int(v[draw].sum())
        if d >= n_min:
            assert pool.legal(v)
            s = deck_shape(pool, v)
            kept.append({"order": tried, "draw": d, "pte": [s["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"]], "v": v})
    print(f"seed {seed}: {tried} concentrated decks drawn, {len(kept)} kept with {n_min}+ draw copies "
          f"(draw copies a kept deck: mean {np.mean([k['draw'] for k in kept]):.2f}, min {min(k['draw'] for k in kept)})")
    for k, x in enumerate(kept[:4]):
        names = [(pool.name[i], int(x["v"][i])) for i in np.nonzero(x["v"])[0] if draw[i]]
        print(f"  F{k}: order {x['order']}, draw copies {x['draw']} {names}, P/T/E {x['pte']}")
    out.mkdir(parents=True, exist_ok=True)
    decks = [{"name": f"M{k}", "cards": pool.names(x["v"])} for k, x in enumerate(kept)]
    f = decks[:4]
    (out / "F_matchups.json").write_text(json.dumps([[a, b] for a in f for b in f]), encoding="utf-8")
    (out / "M_matchups.json").write_text(json.dumps(matchups(decks, np.random.default_rng(seed), M)), encoding="utf-8")
    (out / "decks.json").write_text(json.dumps([{"order": x["order"], "draw": x["draw"], "pte": x["pte"]} for x in kept]), encoding="utf-8")
    print("F matchups", 16, "| M matchups", M, "| written to", out)


def select_shape(pool, bounds, n, seed, out):
    """C162: standard wide decks in seed order, kept when their P/T/E fall in the bounds, until n are kept."""
    lo_hi = [tuple(int(x) for x in b.split("-")) for b in bounds.split(",")]
    rng, kept, tried = np.random.default_rng(seed), [], 0
    while len(kept) < n:
        v = wide_deck(pool, rng)
        tried += 1
        s = deck_shape(pool, v)
        pte = [s["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"]]
        if all(a <= x <= b for x, (a, b) in zip(pte, lo_hi)):
            assert pool.legal(v)
            kept.append({"name": f"S{len(kept)}", "cards": pool.names(v), "order": tried, "pte": pte})
    print(f"seed {seed}: {tried} wide decks drawn, {len(kept)} kept in {bounds}; mean P/T/E "
          f"{np.round(np.mean([k['pte'] for k in kept], 0), 2).tolist()}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "decks.json").write_text(json.dumps(kept), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--select-draw", type=int, default=0)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--shape", default="")
    ap.add_argument("--n", type=int, default=99)
    a = ap.parse_args()
    pool = Pool()
    if a.shape:
        return select_shape(pool, a.shape, a.n, a.seed, ROOT / a.out if not Path(a.out).is_absolute() else Path(a.out))
    if a.select_draw:
        return select_draw(pool, a.select_draw, a.seed, ROOT / a.out if not Path(a.out).is_absolute() else Path(a.out))
    OUT.mkdir(parents=True, exist_ok=True)
    for arm, conc in (("W", False), ("K", True)):
        rng = np.random.default_rng(SEED)
        decks = [{"name": f"{arm}{k}", "cards": pool.names(wide_deck(pool, rng, concentrated=conc))} for k in range(N)]
        pairs = [(k, k) for k in range(N)]
        while len(pairs) < M:
            a, b = (int(x) for x in rng.choice(N, 2, replace=False))
            pairs.append((a, b))
        mus = [[decks[a], decks[b]] for a, b in pairs]
        (OUT / f"{arm}_matchups.json").write_text(json.dumps(mus), encoding="utf-8")
        print(arm, "decks", N, "matchups", len(mus), "mirrors", sum(a == b for a, b in pairs))


if __name__ == "__main__":
    main()
