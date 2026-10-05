"""Side-by-side summary of two evaluation sets from env/tools/evaluate.js (A4.2 vs A4.1).

  python -m rl.compare --a a4 --b a4tok     # reads notes/data/eval/<tag>_{mirror,field}_simplebot.json
                                            # and <b>_vs_<a>_{mirror,field}.json if present
"""
import argparse
import collections
import json
import math
from pathlib import Path

EVAL = Path(__file__).resolve().parent.parent / "notes" / "data" / "eval"


def per_deck(path: Path) -> dict:
    r = json.load(open(path))
    c = collections.defaultdict(lambda: [0.0, 0])
    for row in r["rows"]:
        c[row["xDeck"]][0] += row["xWins"]
        c[row["xDeck"]][1] += 1
    return {"all": r["all"], "decks": {k: w / n for k, (w, n) in c.items()}, "n_deck": {k: n for k, (_, n) in c.items()}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="a4")
    ap.add_argument("--b", default="a4tok")
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    out = {}
    for kind in ("mirror", "field"):
        A, B = per_deck(EVAL / f"{args.a}_{kind}_simplebot.json"), per_deck(EVAL / f"{args.b}_{kind}_simplebot.json")
        decks = sorted(A["decks"])
        diffs = [B["decks"][d] - A["decks"][d] for d in decks]
        print(f"\nvs SimpleBot, {kind}: {args.a} {100 * A['all']['xWinRate']:.1f}% ± {100 * A['all']['ci95']:.1f}   "
              f"{args.b} {100 * B['all']['xWinRate']:.1f}% ± {100 * B['all']['ci95']:.1f}")
        print(f"  {'deck':52s} {args.a:>6s} {args.b:>6s}  diff")
        for d, x in zip(decks, diffs):
            print(f"  {d[:52]:52s} {100 * A['decks'][d]:5.0f}% {100 * B['decks'][d]:5.0f}%  {100 * x:+4.0f}")
        better = sum(x > 0 for x in diffs); worse = sum(x < 0 for x in diffs)
        print(f"  {args.b} better on {better} decks, worse on {worse}; "
              f"lowest deck {args.a} {100 * min(A['decks'].values()):.0f}%, {args.b} {100 * min(B['decks'].values()):.0f}%")
        out[kind] = {"a": A["all"], "b": B["all"], "a_decks": A["decks"], "b_decks": B["decks"], "better": better, "worse": worse}
        h = EVAL / f"{args.b}_vs_{args.a}_{kind}.json"
        if h.exists():
            H = per_deck(h)
            p, n = H["all"]["xWinRate"], H["all"]["n"]
            z = (p - 0.5) / math.sqrt(0.25 / n)
            print(f"  head to head ({kind}): {args.b} wins {100 * p:.1f}% ± {100 * H['all']['ci95']:.1f} of {n} (z = {z:+.1f}); "
                  f"decks where {args.b} wins > 50%: {sum(v > 0.5 for v in H['decks'].values())}/{len(H['decks'])}")
            out[f"h2h_{kind}"] = {"all": H["all"], "decks": H["decks"]}
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
