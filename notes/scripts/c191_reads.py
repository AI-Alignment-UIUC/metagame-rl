"""C191 CPU reads for research's interim (#1054). CPU, seconds.
--best RUN IT[,IT...]: the 12 best decks by recent_score (as c190_split's top 12) at each snapshot: median P/T/E, the Pokemon
    names (copies over the 12 decks), the basic Energy by card, and Double Colorless per deck.
--drift RUN: C191's edit drift d(it) = select.moved x select.acc[E] / D (log.jsonl; a resumed run's later row wins) by window,
    with SE over the window's iterations, and the population mean E (log.jsonl's shapes) over the same iterations.
    py notes/scripts/c191_reads.py --best C191-WL-s52 44,59,74
    py notes/scripts/c191_reads.py --drift C184-WR-s50
--g3merge A.json B.json: G3 under search run in halves, pooled (#1071).
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.decks import Pool                                # noqa: E402
from rl.metagame import recent_score                     # noqa: E402

P = Pool()
CARD = {c["fullName"]: c for c in P.cards}
DCE = "Double Colorless Energy BS"


def best(run, its):
    out = {}
    for it in its:
        pop = torch.load(ROOT / f"runs/screens/{run}/population_it{it:04d}.pt", map_location="cpu", weights_only=False)["population"]
        top = sorted(pop, key=lambda a: -recent_score(a, 0.0))[:12]
        decks = [list(a["deck"]) for a in top]
        pte = np.array([[sum(CARD[c]["superType"] == k for c in d) for k in (1, 2, 3)] for d in decks])
        mons = Counter(CARD[c]["name"] for d in decks for c in d if CARD[c]["superType"] == 1)
        basics = Counter(c for d in decks for c in d if CARD[c]["superType"] == 3 and CARD[c]["energyType"] == 0)
        out[it] = {"median_pte": np.median(pte, 0).tolist(), "mean_pte": np.round(pte.mean(0), 2).tolist(),
                   "z": [round(recent_score(a, 0.0), 3) for a in top], "pokemon_names": dict(mons.most_common(15)),
                   "distinct_pokemon_names": len(mons), "basic_energy": dict(basics.most_common()),
                   "dce_a_deck": round(float(np.mean([d.count(DCE) for d in decks])), 2), "decks_with_dce": sum(DCE in d for d in decks)}
    return out


def drift(run, windows=((0, 14), (15, 29), (30, 44), (45, 59), (60, 74))):
    rows = {}
    for l in open(ROOT / f"runs/screens/{run}/log.jsonl", encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            rows[r["iter"]] = r
    out = {}
    for lo, hi in windows:
        its = [i for i in range(lo, hi + 1) if i in rows]
        if not its:
            continue
        d = [rows[i]["select"]["moved"] * rows[i]["select"]["acc"][2] / len(rows[i]["shapes"])
             for i in its if (rows[i].get("select") or {}).get("acc")]
        e = [float(np.mean([s[2] for s in rows[i]["shapes"]])) for i in its]
        out[f"{lo}-{hi}"] = {"iters": len(its), "drift_mean": round(float(np.mean(d)), 4) if d else None,
                             "drift_se": round(float(np.std(d, ddof=1) / np.sqrt(len(d))), 4) if len(d) > 1 else None,
                             "counted": len(d), "mean_E": round(float(np.mean(e)), 2)}
    return out


def g3merge(files):
    """#1071: G3 under search in halves (g3_yardstick.py --first-deck/--last-deck): pool the halves' games, then g3_yardstick's reads."""
    sys.path.insert(0, str(ROOT / "notes" / "scripts"))
    from g3_yardstick import reads
    ds = [json.loads((ROOT / f).read_text(encoding="utf-8")) for f in files]
    rows = [r for d in ds for r in d["results"]]
    return {"files": files, "errors": sum(d["errors"] for d in ds), "decks": len({r["i"] for r in rows}), **reads(rows)}


if __name__ == "__main__":
    if "--g3merge" in sys.argv:
        print(json.dumps(g3merge(sys.argv[sys.argv.index("--g3merge") + 1:]), indent=1))
        sys.exit(0)
    if "--best" in sys.argv:
        i = sys.argv.index("--best")
        print(json.dumps(best(sys.argv[i + 1], [int(x) for x in sys.argv[i + 2].split(",")]), indent=1))
    if "--drift" in sys.argv:
        print(json.dumps(drift(sys.argv[sys.argv.index("--drift") + 1]), indent=1))
