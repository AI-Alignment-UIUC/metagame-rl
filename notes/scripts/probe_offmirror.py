"""X3 (log #234; record runs/probe/X3-offmirror/record.md): the lists' search, disrupt and tempo Trainers priced off
the mirror. Evaluation only: the 24 human lists are probe decks, nothing trains.

trainer_value.py prices a Trainer group by a list against its own Energy copy (a self-mirror, one pilot on both seats).
Here each list i and its copy c_i (search + disrupt + tempo together turned into its commonest basic Energy, by
trainer_value.variants) play the OTHER lists, both seats, one pilot on every seat, on the same deals per opponent: the
base game i-j and the copy games c_i-j and i-c_j share the pair key of {i, j}, so the same seeds, seats and round
lengths. Card positions match too (the copy swaps cards in place), so a copy game deals the same hand with Energy where
the Trainers were.

  off_i = mean over j != i of score(i vs j) - score(c_i vs j)     (the Trainers' price against the human field)
  mir_i = score(i vs c_i) - 0.5                                    (the mirror price, same tooling, trainer_value's keys)

A score counts a win 1, a loss 0, a draw or a game cut at time 0.5 (a win on Prizes at time is a win), as in
trainer_value. The mean of score(i vs j) over all lists and opponents is 0.5 exactly, so mean(off) = 0.5 - the copies'
mean score against the field, and the SE over lists is conservative for that mean.

Run: runs/probe/X3-offmirror/chain.sh. Smoke (CPU): --device cpu --lists 2 --games 2 --mirror-games 2 --workers 2
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

from rl import limits
from rl.decks import Pool, archived_decks
from rl.gpu_matrix import GpuMatrix, load_policy
from rl.remote import RemotePool
from rl.train import round_turns

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trainer_value as tv  # noqa: E402  (read only: its groups and variants)

ROOT = Path(__file__).resolve().parents[2]
GROUP = "sdt"
tv.GROUPS[GROUP] = tv.GROUPS["search"] + tv.GROUPS["disrupt"] + tv.GROUPS["tempo"]   # in this process only


def stat(x) -> dict:
    x = np.asarray(x, float)
    se = float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else float("nan")
    return {"mean": round(float(x.mean()), 4), "se": round(se, 4), "n": int(len(x))}


def score(r: dict, deck: int) -> float:
    """deck's score in one game result (as GpuMatrix.play counts it)."""
    seat = r["iSeat"] if r["i"] == deck else 3 - r["iSeat"]
    return 1.0 if r["winner"] == seat else 0.0 if r["winner"] in (1, 2) else 0.5


def band(off: dict, mir: dict) -> str:
    """The pre-written bands of record.md, on the means; 'provisional' when a mean is within 2 SE of a band edge."""
    if mir["mean"] >= 0:
        b = "no-mirror-deficit: the combined copy does not win the mirror (groups need not add); report off, claim no band"
    elif off["mean"] >= 0.03:
        b = "mirror-specific: off >= +0.03 while the mirror reads below 0"
    elif off["mean"] < 0:
        b = "general: both below 0"
    else:
        b = "between: 0 <= off < +0.03"
    near = abs(mir["mean"]) < 2 * mir["se"] or any(abs(off["mean"] - e) < 2 * off["se"] for e in (0.0, 0.03))
    return b + (" (provisional: a mean within 2 SE of a band edge)" if near else "")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default="runs/pilot/C49-sd/model_it00199.pt")
    ap.add_argument("--lists", type=int, default=0, help="the first N archived lists only (smoke); 0 = all 24")
    ap.add_argument("--games", type=int, default=12, help="games per off-mirror pair (both seats; even)")
    ap.add_argument("--mirror-games", type=int, default=64, help="games per mirror pair, list vs its copy")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--round-turns", default="20-45", help='the 2000 round rule, "T" or "A-B"; "0" for none')
    ap.add_argument("--device", default="", help="cuda or cpu; default cuda when available")
    ap.add_argument("--mirror-ref", default="runs/probe/C67-fixab/t49fix.json",
                    help="trainer_value's per-group mirror cell for the same pilot and rule, for comparison")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    assert args.games % 2 == 0 and args.mirror_games % 2 == 0, "even games: both seats equally"
    rounds = round_turns(args.round_turns)
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    workers = limits.cap_workers(args.workers)
    limits.apply(device, workers)
    print("device", device, "workers", workers, flush=True)

    pool = Pool()
    lists = [{"name": n, "cards": pool.names(v)} for n, v in archived_decks(pool)]
    lists = lists[:args.lists] if args.lists else lists
    n = len(lists)
    decks, vp = tv.variants(pool, lists, [GROUP])
    copy = {p["base"]: p["variant"] for p in vp}
    replaced = {p["base"]: p["replaced"] for p in vp}
    L = sorted(copy)                                         # lists with a copy (all of them unless one has no basic)

    # Off-mirror cell: every base pair once, and each copy against every other list in its base's seat, same key.
    base = [(a, b) for a in range(n) for b in range(a + 1, n)]
    key = {pr: k for k, pr in enumerate(base)}
    pairs, keys = list(base), list(range(len(base)))
    for i in L:
        for j in range(n):
            if j != i:
                pairs.append((copy[i], j) if i < j else (j, copy[i]))
                keys.append(key[(min(i, j), max(i, j))])
    mpairs, mkeys = [(i, copy[i]) for i in L], L             # mirror cell: trainer_value's pairs and keys

    model, enc = load_policy(args.pilot, device)
    rp = RemotePool(workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, workers, encoding=enc, device=device)
        W, G, _ = gm.play(decks, args.games, args.seed, pairs=pairs, pair_keys=keys, round_turns=rounds)
        run_off, res_off = gm.last, gm.results
        print("off-mirror", json.dumps(run_off), flush=True)
        W2, G2, _ = gm.play(decks, args.mirror_games, args.seed, pairs=mpairs, pair_keys=mkeys, round_turns=rounds)
        run_mir = gm.last
        print("mirror", json.dumps(run_mir), flush=True)
    finally:
        rp.close()

    rate = lambda M, N, a, b: float(M[a, b] / max(N[a, b], 1))
    rows = []
    for i in L:
        opp = [j for j in range(n) if j != i]
        b = [rate(W, G, i, j) for j in opp]
        c = [rate(W, G, copy[i], j) for j in opp]
        off, mir = float(np.mean(b) - np.mean(c)), rate(W2, G2, i, copy[i]) - 0.5
        rows.append({"list": lists[i]["name"], "replaced": replaced[i], "base_vs_field": round(float(np.mean(b)), 4),
                     "copy_vs_field": round(float(np.mean(c)), 4), "off": round(off, 4), "mirror": round(mir, 4),
                     "off_minus_mirror": round(off - mir, 4)})

    # Pairing check: base and copy outcomes on the same deal and opponent (same seed), correlated if the keys pair.
    by = {}
    for r in res_off:
        by[(r["i"], r["j"], r["seed"])] = r
    xs, ys = [], []
    for i in L:
        for j in range(n):
            if j == i:
                continue
            a, b = (i, j) if i < j else (j, i)
            ca, cb = (copy[i], j) if i < j else (j, copy[i])
            for g in range(args.games):
                s = args.seed * 1000003 + key[(a, b)] * args.games + g
                if (a, b, s) in by and (ca, cb, s) in by:
                    xs.append(score(by[(a, b, s)], i))
                    ys.append(score(by[(ca, cb, s)], copy[i]))
    rho = float(np.corrcoef(xs, ys)[0, 1]) if len(xs) > 2 and np.std(xs) > 0 and np.std(ys) > 0 else float("nan")

    summ = {k: stat([r[k] for r in rows]) for k in ("off", "mirror", "off_minus_mirror", "copy_vs_field")}
    errors = run_off["errors"] + run_mir["errors"]
    games = run_off["games"] + run_mir["games"]
    summ["band"] = band(summ["off"], summ["mirror"])
    summ["errors_share"] = round(errors / max(games, 1), 4)
    summ["pairing"] = {"games": len(xs), "rho": round(rho, 3), "same_outcome": round(float(np.mean(
        np.array(xs) == np.array(ys))), 3) if xs else None}
    ref = None
    if args.mirror_ref and (ROOT / args.mirror_ref).exists():
        t = json.load(open(ROOT / args.mirror_ref, encoding="utf-8"))
        ref = {g: v for p, x in t["players"].items() for g, v in x["by_group"].items()}
    out = {"pilot": args.pilot, "lists": n, "group": "search+disrupt+tempo", "games": args.games,
           "mirror_games": args.mirror_games, "seed": args.seed, "round_turns": args.round_turns, "device": device,
           "summary": summ, "mirror_ref": {"file": args.mirror_ref, "by_group": ref},
           "run": {"off_mirror": run_off, "mirror": run_mir}, "per_list": rows}
    print("summary", json.dumps(summ), flush=True)
    if ref:
        print("mirror_ref", json.dumps({g: v["score"] for g, v in ref.items()}), flush=True)
    if args.out:
        Path(ROOT / args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
