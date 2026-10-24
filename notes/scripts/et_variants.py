"""C56 (log #211): what a basic Energy is worth against a Trainer, by field and player (evaluation only).

make: fresh wide decks from the loop's own generator (`rl.decks.wide_deck`, the `--init-wide` start) at a fixed seed,
24 parents and 16 more as the field U. Each parent gets two variants by card supertype alone: "+E" (3 Trainer copies
drawn at random become its commonest basic Energy) and "-E" (3 of that Energy become copies of its own Trainers, drawn
at random among those with room). Writes parents.json, variants.json (+E, -E per parent, in parent order) and
field_u.json into --out.

read: Delta_ET from probe_matchups.py outputs run with --a variants.json: per parent (score of +E - score of -E) / 2
against the whole B field, then the mean and SE over parents. Positive means Energy pays.

    .venv/Scripts/python notes/scripts/et_variants.py make --out runs/probe/C56-etprice
    .venv/Scripts/python notes/scripts/et_variants.py read runs/probe/C56-etprice/g49_u.json [...]
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.decks import MAX_COPIES, Pool, deck_shape, wide_deck  # noqa: E402


def variants(pool: Pool, v: np.ndarray, rng, k: int = 3):
    trainer = np.zeros(pool.n, dtype=bool)
    trainer[[c["id"] for c in pool.cards if c["superType"] == 2]] = True
    if v[pool.basic_energy].sum() == 0:
        return None
    fill = int(np.argmax(np.where(pool.basic_energy, v, -1)))
    copies = [i for i in np.nonzero((v > 0) & trainer)[0] for _ in range(int(v[i]))]
    if len(copies) < k or v[fill] < k:
        return None
    plus = v.copy()
    for i in rng.choice(copies, size=k, replace=False):
        plus[i] -= 1
    plus[fill] += k
    minus = v.copy()
    minus[fill] -= k
    for _ in range(k):
        room = [i for i in np.nonzero((minus > 0) & trainer)[0]
                if pool.name_counts(np.where(pool.basic_energy, 0, minus))[pool.name_of[i]] < MAX_COPIES]
        if not room:
            return None
        minus[room[rng.integers(len(room))]] += 1
    return (plus, minus) if pool.legal(plus) and pool.legal(minus) else None


def make(args):
    pool, rng = Pool(), np.random.default_rng(args.seed)
    parents, out_v, field = [], [], []
    while len(parents) < args.parents:
        v = wide_deck(pool, rng)
        pm = variants(pool, v, rng)
        if pm:
            k = len(parents)
            parents.append({"name": f"p{k}", "cards": pool.names(v), **deck_shape(pool, v)})
            out_v += [{"name": f"p{k}+E", "cards": pool.names(pm[0])}, {"name": f"p{k}-E", "cards": pool.names(pm[1])}]
    while len(field) < args.field:
        v = wide_deck(pool, rng)
        field.append({"name": f"u{len(field)}", "cards": pool.names(v), **deck_shape(pool, v)})
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    for name, x in (("parents", parents), ("variants", out_v), ("field_u", field)):
        (out / f"{name}.json").write_text(json.dumps(x, indent=1))
    shape = np.array([[p["pokemon"], p["trainer"], p["basic_energy"] + p["special_energy"]] for p in parents])
    print(f"{len(parents)} parents, median P / T / E {np.median(shape, 0).tolist()}; {len(out_v)} variants; "
          f"{len(field)} field decks -> {out}")


def deltas(f, first=0):
    a = json.load(open(ROOT / f))["a_mean"]
    d = np.array([(a[2 * k] - a[2 * k + 1]) / 2 for k in range(len(a) // 2)])
    return d[:first] if first else d


def read(args):
    for f in args.files:
        r = json.load(open(ROOT / f))
        a = r["a_mean"][:2 * args.first] if args.first else r["a_mean"]
        d = deltas(f, args.first)
        if args.minus:  # paired by parent: this cell minus another cell on the same parents (stage 2's P band)
            d = d - deltas(args.minus, len(d))
        m = float(np.mean(d))
        se = float(np.std(d, ddof=1) / math.sqrt(len(d)))
        extra = f", sts {r['sts']}" if "sts" in r else ""
        print(f"{f}: Delta_ET {m:+.4f} (SE {se:.4f}, {len(d)} parents); +E {np.mean(a[0::2]):.4f}, -E {np.mean(a[1::2]):.4f}; "
              f"{r.get('games')} games, errors {r.get('errors')}, endings {r.get('endings')}{extra}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--out", required=True)
    m.add_argument("--seed", type=int, default=56)
    m.add_argument("--parents", type=int, default=24)
    m.add_argument("--field", type=int, default=16)
    r = sub.add_parser("read")
    r.add_argument("files", nargs="+")
    r.add_argument("--first", type=int, default=0, help="only the first N parents (a stage-2 subset)")
    r.add_argument("--minus", default="", help="another readout: print the per-parent difference, paired")
    args = ap.parse_args(argv)
    make(args) if args.cmd == "make" else read(args)


if __name__ == "__main__":
    main()
