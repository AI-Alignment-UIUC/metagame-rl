"""Selection's lean (S37, log #204): accepted minus proposed Pokemon / Trainers / Energy a move, per window.

Reads the `select` records (`acc`, `prop`) of a metagame run's log.jsonl and prints, for each window of iterations
counted from the run's first logged iteration, the mean and the SE over iterations.

    .venv/Scripts/python notes/scripts/select_lean.py C53-h20.fju-c49sd199-s1 scr-ctl479 [--window 10]

--cards (C127, runs with `rl.metagame --card-ledger`): from each row's `select.card`, per card group, the lean
lambda = acc_net / n_acc - prop_net / n_prop (copies a move; mean and SE over iterations), the group's share of all
prop_in copies, and its gross prop_in. The integrity check rebuilds each row's acc and prop from the ledger by supertype
(rl.decks.deck_shape) and must match to rounding; a row that fails voids the readout.
"""
import argparse
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
GROUPS = {"T4": ["PlusPower", "Gust of Wind", "Item Finder", "Scoop Up"], "D3": ["Computer Search", "Professor Oak", "Bill"],
          "ER": ["Energy Removal"]}


def lean(path):
    rows = []
    for line in open(path / "log.jsonl"):
        d = json.loads(line)
        s = d.get("select") or {}
        if "acc" in s and "prop" in s:
            rows.append((d.get("iter"), [a - p for a, p in zip(s["acc"], s["prop"])]))
    return rows


def cards(path):
    """C127's per-group readout from select.card; returns (groups, integrity failures, iterations)."""
    sys.path.insert(0, str(ROOT))
    import numpy as np
    from rl.decks import Pool, deck_shape
    pool = Pool()
    bare = {i: n.rsplit(" ", 1)[0] for i, n in pool.full_name.items()}
    ids = {g: [i for i, b in bare.items() if b in names] for g, names in GROUPS.items()}
    ids["basic Energy"] = [int(i) for i in np.flatnonzero(pool.basic_energy)]
    vec = lambda sp: np.bincount([int(k) for k in sp], weights=[v for v in sp.values()], minlength=pool.n) if sp else np.zeros(pool.n)
    shape = lambda v: np.array([(s := deck_shape(pool, v))["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"]])
    lam, gross, bad, its = {g: [] for g in ids}, {g: 0.0 for g in ids}, [], []
    for line in open(path / "log.jsonl"):
        d = json.loads(line)
        c = (d.get("select") or {}).get("card")
        if not c:
            continue
        its.append(d.get("iter"))
        V = {k: np.rint(vec(c[k])).astype(np.int64) for k in ("prop_net", "prop_in", "acc_net")}
        for key, n in (("acc", c["n_acc"]), ("prop", c["n_prop"])):
            want, got = d["select"].get(key), shape(V[key + "_net"]) / n if n else None
            if (want is None) != (got is None) or (got is not None and np.abs(np.round(got, 3) - np.array(want)).max() > 1e-6):
                bad.append((d.get("iter"), key, want, None if got is None else np.round(got, 3).tolist()))
        tot_in = V["prop_in"].sum()
        for g, gi in ids.items():
            if c["n_acc"] and c["n_prop"]:
                lam[g].append(V["acc_net"][gi].sum() / c["n_acc"] - V["prop_net"][gi].sum() / c["n_prop"])
            gross[g] += V["prop_in"][gi].sum()
        gross["_all"] = gross.get("_all", 0.0) + tot_in
    out = {}
    for g in ids:
        xs, n = lam[g], len(lam[g])
        m = sum(xs) / n if n else float("nan")
        se = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1) / n) if n > 1 else float("nan")
        out[g] = {"lambda": m, "se": se, "n_iters": n, "prop_in": gross[g], "share_in": gross[g] / gross["_all"] if gross.get("_all") else float("nan")}
    return out, bad, its


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="run folders, or names under runs/screens")
    ap.add_argument("--window", type=int, default=10)
    ap.add_argument("--cards", action="store_true", help="C127's per-card-group readout from select.card (--card-ledger runs)")
    args = ap.parse_args()
    for r in args.runs:
        path = pathlib.Path(r)
        if not path.exists():
            path = pathlib.Path("runs/screens") / r
        if args.cards:
            out, bad, its = cards(path)
            print(f"== {path.name}: {len(its)} iterations with select.card ({its[0] if its else None}-{its[-1] if its else None})")
            if not its:
                print("  integrity: no rows (no select.card in this log; not a --card-ledger run)")
                continue
            print(f"  integrity: {'FAIL' if bad else 'PASS'} ({len(bad)} mismatches{': ' + str(bad[:3]) if bad else ''})")
            for g, o in out.items():
                print(f"  {g:12s} lambda {o['lambda']:+.3f} (SE {o['se']:.3f}, n {o['n_iters']}); prop_in {o['prop_in']:.0f} copies, "
                      f"share {o['share_in']:.1%}")
            continue
        rows = lean(path)
        print(f"== {path.name}: {len(rows)} iterations with select records")
        for w in range(0, len(rows), args.window):
            chunk = rows[w:w + args.window]
            n = len(chunk)
            cells = []
            for k in range(3):
                xs = [x[k] for _, x in chunk]
                m = sum(xs) / n
                se = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1) / n) if n > 1 else float("nan")
                cells.append(f"{m:+.2f} ({se:.2f})")
            print(f"  iters {chunk[0][0]}-{chunk[-1][0]} (n {n}): P / T / E  " + " / ".join(cells))


if __name__ == "__main__":
    main()
