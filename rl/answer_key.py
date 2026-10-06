"""The answer key (plan item A5): an agent's metagame, scored against the archived field.

The agent's meta is a deck population with its matchup matrix (from PSRO, ideally started from
random decks on the full pool, so it has never seen the archived lists) and the population's
Nash mixture. The archived field is only used here, to score it, in three tiers:

  1. staples     cards nearly every archived deck plays (in at least --staple-share of them).
                 Recall: share of staples the agent's mixture plays (weighted inclusion >= 0.5);
                 count agreement: the agent's median count within 1 of the field's. Also listed:
                 cards the agent treats as staples that the field rarely plays.
  2. archetypes  for each archived archetype, the best card overlap with a deck in the
                 equilibrium support; rediscovered if at least --overlap.
  3. meta        the counter table: each deck's best counter in the population, its win rate,
                 and the deck's exploitability (that win rate). Matchup directions against era
                 write-ups are read off the same matrix.

  python -m rl.answer_key --matrix notes/data/eval/matrix_simplebot.json                (archived decks)
  python -m rl.answer_key --matrix runs/a5/matrix.json --decks runs/a5/population.json  (an agent's meta)
"""
import argparse
import collections
import json
import re
from pathlib import Path

import numpy as np

from rl.decks import Pool, archived_decks, overlap
from rl.nash import solve


def label_of(name: str) -> str:
    m = re.search(r"\(([^)]*)\)\s*$", name)
    return m.group(1) if m else name


def win_matrix(m: dict) -> np.ndarray:
    W, G = np.array(m["wins"], float), np.array(m["games"], float)
    P = np.where(G > 0, W / np.maximum(G, 1), 0.5)
    np.fill_diagonal(P, 0.5)
    return P


def counters(P: np.ndarray, names: list) -> list:
    """Each deck's best counter among the others, and its win rate (the deck's exploitability)."""
    out = []
    for j in range(len(names)):
        col = P[:, j].copy()
        col[j] = -1
        i = int(col.argmax())
        out.append({"deck": names[j], "best_counter": names[i], "counter_win": float(P[i, j])})
    return sorted(out, key=lambda r: r["counter_win"])


def staples(pool: Pool, agent: list, weights: np.ndarray, field: list, share: float) -> dict:
    names = sorted(pool.name_index, key=pool.name_index.get)
    A = np.array([pool.name_counts(v) for v in agent])
    F = np.array([pool.name_counts(v) for v in field])
    f_in = (F > 0).mean(0)
    a_in = ((A > 0) * weights[:, None]).sum(0)

    def wmedian(col, w):
        m = (col > 0) & (w > 0)
        if not m.any():
            return 0.0
        order = np.argsort(col[m])
        c, ww = col[m][order], w[m][order]
        return float(c[np.searchsorted(np.cumsum(ww), ww.sum() / 2)])

    rows = []
    for k, n in enumerate(names):
        if f_in[k] >= share or a_in[k] >= share:
            rows.append({"card": n, "field_share": float(f_in[k]), "field_median": float(np.median(F[F[:, k] > 0, k])) if f_in[k] else 0.0,
                         "agent_share": float(a_in[k]), "agent_median": wmedian(A[:, k], weights)})
    st = [r for r in rows if r["field_share"] >= share]
    found = [r for r in st if r["agent_share"] >= 0.5]
    agree = [r for r in found if abs(r["agent_median"] - r["field_median"]) <= 1]
    extra = [r for r in rows if r["agent_share"] >= share and r["field_share"] < 0.25]
    return {"staples": len(st), "recall": len(found) / max(len(st), 1), "count_agreement": len(agree) / max(len(found), 1),
            "agent_only": [r["card"] for r in extra], "rows": sorted(rows, key=lambda r: -r["field_share"])}


def archetypes(agent: list, agent_names: list, weights: np.ndarray, field: list, field_names: list, threshold: float) -> dict:
    support = [i for i in range(len(agent)) if weights[i] > 0.01]
    best = {}
    for v, n in zip(field, field_names):
        lab = label_of(n)
        o = max((overlap(agent[i], v), agent_names[i]) for i in support) if support else (0.0, None)
        if lab not in best or o[0] > best[lab][0]:
            best[lab] = o
    rows = [{"archetype": k, "best_overlap": v[0], "closest_support_deck": v[1]} for k, v in best.items()]
    found = sum(r["best_overlap"] >= threshold for r in rows)
    return {"archetypes": len(rows), "rediscovered": found, "rows": sorted(rows, key=lambda r: -r["best_overlap"])}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", required=True, help="matrix.js output for the agent's population")
    ap.add_argument("--decks", help="the population ([{name, cards}]); default: the archived decks")
    ap.add_argument("--staple-share", type=float, default=0.75)
    ap.add_argument("--overlap", type=float, default=0.5)
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    pool = Pool()
    field = archived_decks(pool)
    m = json.load(open(args.matrix))
    if args.decks:
        pop = json.load(open(args.decks))
        names, vecs = [d["name"] for d in pop], [pool.vector(d["cards"]) for d in pop]
    else:
        by = dict(field)
        names, vecs = list(m["decks"]), [by[n] for n in m["decks"]]
    assert len(names) == len(m["decks"]), "matrix and decks differ in size"
    P = win_matrix(m)
    w, value = solve(P)
    st = staples(pool, vecs, w, [v for _, v in field], args.staple_share)
    ar = archetypes(vecs, names, w, [v for _, v in field], [n for n, _ in field], args.overlap)
    co = counters(P, names)
    print(f"population {len(names)} decks; Nash support: " + ", ".join(f"{names[i]} {w[i]:.2f}" for i in np.argsort(-w) if w[i] > 0.01))
    print(f"\n1. staples (in >= {args.staple_share:.0%} of archived decks): {st['staples']}; agent plays "
          f"{st['recall']:.0%} of them, counts within 1 for {st['count_agreement']:.0%}")
    for r in st["rows"]:
        print(f"   {r['card']:26s} field {r['field_share']:4.0%} x{r['field_median']:.1f}   agent {r['agent_share']:4.0%} x{r['agent_median']:.1f}")
    if st["agent_only"]:
        print("   agent-only staples: " + ", ".join(st["agent_only"]))
    print(f"\n2. archetypes rediscovered (overlap >= {args.overlap}): {ar['rediscovered']}/{ar['archetypes']}")
    for r in ar["rows"]:
        print(f"   {r['archetype'][:34]:34s} {r['best_overlap']:.2f}  {r['closest_support_deck']}")
    print("\n3. counters (hardest to exploit first): deck <- best counter, win rate")
    for r in co:
        print(f"   {100 * r['counter_win']:5.1f}%  {r['deck'][:46]:46s} <- {r['best_counter']}")
    if args.json:
        json.dump({"nash": dict(zip(names, map(float, w))), "staples": st, "archetypes": ar, "counters": co},
                  open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
