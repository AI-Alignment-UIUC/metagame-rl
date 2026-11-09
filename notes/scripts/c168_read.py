"""C168 (runs/probe/C168-long-fresh-turnover/record.md, with Amendments 1 and 2): reads of a screen at a saved iteration, for the population and its G1 set: TV (total variation between its and
the lists' shares of Trainer copies over the 42 Trainers), E (TV minus the mean TV against 1,000 label-permuted list vectors; the bands and stops read E), A7 (the share of the lists' Trainer copies
held by its 7 most-copied Trainers), how many of the lists' top 7 those are, effective Trainers (1 / sum of squared shares), rho_L (Spearman of its mean copies against the lists'), draw and T4
copies a deck, P/T/E, G1's mean of 5; from the ledger, the draw and T4 shares of proposed copies by 10-iteration window; deck ages; copies still in common with the deck's
generator root (the root's first saved form, an approximation: saves come every 5 iterations); and the survivors' paired change per 25 iterations in T4, draw and Trainers, SE over decks.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c168_read.py runs/screens/<run> [--iter I]
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c168_read.py --band [--iter 129]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
from rl.decks import Pool                   # noqa: E402
import aa_window as aw                      # noqa: E402
import c119_counts as cc                    # noqa: E402

D = ROOT / "runs/probe/C168-long-fresh-turnover"
ARMS = {"N": ("C168-N-s50", "C168-N-s51"), "W": ("C168-W-s50", "C168-W-s51")}
DRAW, T4 = ("Professor Oak", "Bill", "Gambler"), ("PlusPower", "Gust of Wind", "Item Finder", "Scoop Up")
POOL = Pool()
CARD = {c["fullName"]: c for c in POOL.cards}
TN = sorted({c["name"] for c in POOL.cards if POOL.allowed[c["id"]] and c["superType"] == 2})
TI = {n: k for k, n in enumerate(TN)}


def copies(deck):
    v = np.zeros(len(TN))
    for x in deck:
        if CARD[x]["superType"] == 2:
            v[TI[CARD[x]["name"]]] += 1
    return v


LISTS = np.mean([copies(d["cards"]) for d in json.loads((ROOT / "runs/probe/C163-draw-deck-field/L.json").read_text(encoding="utf-8"))], 0)
LISTS_SHARE = LISTS / LISTS.sum()
LISTS_TOP7 = set(np.argsort(-LISTS)[:7].tolist())
_rng = np.random.default_rng(168)
PERMS = [_rng.permutation(len(TN)) for _ in range(1000)]    # Amendment 2: the label-permuted list vectors


def ranks(x):
    x = np.asarray(x, dtype=float)
    o = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    r[o] = np.arange(len(x), dtype=float)
    for v in np.unique(x):
        r[x == v] = r[x == v].mean()
    return r


def set_reads(decks):
    """TV and its excess E over the label-permuted null, z, A7, of the lists' top 7, effective Trainers, rho_L, draw and T4 copies a deck, and shape, of a set of decks."""
    m = np.mean([copies(d) for d in decks], 0)
    share = m / m.sum()
    tv = float(0.5 * np.abs(share - LISTS_SHARE).sum())
    null = np.array([0.5 * np.abs(share - LISTS_SHARE[p]).sum() for p in PERMS])
    top = np.argsort(-m)[:7]
    shape = np.mean([[sum(CARD[x]["superType"] == k for x in d) for k in (1, 2, 3)] for d in decks], 0)
    return {"decks": len(decks), "TV": round(tv, 4), "null": round(float(null.mean()), 4), "E": round(tv - float(null.mean()), 4), "z": round((tv - float(null.mean())) / float(null.std()), 2),
            "A7": round(float(LISTS_SHARE[top].sum()), 4), "of_lists_top7": len(LISTS_TOP7 & set(top.tolist())), "effective_trainers": round(float(1 / (share ** 2).sum()), 1),
            "rho_L": round(float(np.corrcoef(ranks(m), ranks(LISTS))[0, 1]), 4), "draw": round(float(sum(m[TI[n]] for n in DRAW)), 3), "T4": round(float(sum(m[TI[n]] for n in T4)), 3),
            "pte": np.round(shape, 2).tolist()}


PN = sorted({c["name"] for c in POOL.cards if POOL.allowed[c["id"]] and c["superType"] == 1})
PI = {n: k for k, n in enumerate(PN)}


def name_counts(deck):
    v = np.zeros(len(PN))
    for x in deck:
        if CARD[x]["superType"] == 1:
            v[PI[CARD[x]["name"]]] += 1
    return v


_L_MONS = np.mean([name_counts(d["cards"]) for d in json.loads((ROOT / "runs/probe/C163-draw-deck-field/L.json").read_text(encoding="utf-8"))], 0)
_L_SHARE = _L_MONS / _L_MONS.sum()
_rng2 = np.random.default_rng(169)
PERMS_P = [_rng2.permutation(len(PN)) for _ in range(1000)]


def body_reads(decks):
    """C169's body facts a deck, and E over the Pokemon names (the same permutation null as the Trainers', research's addition for C168)."""
    rows = []
    for d in decks:
        mons = [CARD[x] for x in d if CARD[x]["superType"] == 1]
        names = {m["name"]: m for m in mons}
        evolved = [m for m in mons if m["stage"] != 2]
        types = {t for m in mons for t, v in enumerate(m["types"]) if v}
        basics = [CARD[x] for x in d if CARD[x]["superType"] == 3 and CARD[x]["energyType"] == 0]
        rows.append([len(mons), len(mons) - len(evolved), len(names), len(mons) / max(1, len(names)), len(evolved),
                     sum(m.get("evolvesFrom") not in names for m in evolved), len({e["name"] for e in basics}),
                     np.mean([any(e["provides"][t] for t in types) for e in basics]) if basics else np.nan,
                     sum(CARD[x]["superType"] == 3 and CARD[x]["energyType"] != 0 for x in d)])
    m = np.nanmean(np.array(rows, dtype=float), 0)
    p = np.mean([name_counts(d) for d in decks], 0)
    s = p / p.sum()
    tv = float(0.5 * np.abs(s - _L_SHARE).sum())
    null = np.array([0.5 * np.abs(s - _L_SHARE[q]).sum() for q in PERMS_P])
    keys = ("pokemon", "basic", "names", "copies_a_name", "evolved", "orphan_evolved", "basic_energy_types", "on_type_basic_share", "special_energy")
    return {**{k: round(float(v), 2) for k, v in zip(keys, m)}, "names_TV": round(tv, 4), "names_E": round(tv - float(null.mean()), 4), "names_z": round((tv - float(null.mean())) / float(null.std()), 2)}


def wall_share(decks):
    """Amendment 3: the share of decks with an on-type basic share under 0.3 and 8 or more special Energy. No card named."""
    n = 0
    for d in decks:
        types = {t for x in d if CARD[x]["superType"] == 1 for t, v in enumerate(CARD[x]["types"]) if v}
        basics = [CARD[x] for x in d if CARD[x]["superType"] == 3 and CARD[x]["energyType"] == 0]
        on = np.mean([any(e["provides"][t] for t in types) for e in basics]) if basics else 0.0
        n += on < 0.3 and sum(CARD[x]["superType"] == 3 and CARD[x]["energyType"] != 0 for x in d) >= 8
    return n / len(decks)


def snapshot(run, it):
    return torch.load(run / f"population_it{it:04d}.pt", map_location="cpu", weights_only=False)["population"]


def saved(run):
    return sorted(int(p.stem[-4:]) for p in run.glob("population_it*.pt"))


def survivors(run, it, span=25):
    """Decks present (same id) at it - span and it: the paired change in T4, draw and Trainers, per span iterations, SE over decks."""
    prev = it - span
    if prev not in saved(run):
        return None
    a, b = {x["id"]: x for x in snapshot(run, prev)}, {x["id"]: x for x in snapshot(run, it)}
    both = sorted(set(a) & set(b))
    out = {"from": prev, "to": it, "decks": len(both)}
    if len(both) < 2:
        return out
    d = np.array([copies(b[k]["deck"]) - copies(a[k]["deck"]) for k in both])
    for name, row in (("T4", d[:, [TI[n] for n in T4]].sum(1)), ("draw", d[:, [TI[n] for n in DRAW]].sum(1)), ("trainers", d.sum(1))):
        out[name] = {"change": round(float(row.mean()), 3), "se": round(float(row.std(ddof=1) / len(row) ** 0.5), 3)}
    return out


def ledger_shares(run, width=10):
    """The draw and T4 shares of proposed copies, by window of iterations (the ledger's prop_in)."""
    bare = {str(i): n.rsplit(" ", 1)[0] for i, n in POOL.full_name.items()}
    win, seen = {}, {}
    for r in sorted(aw.rows(run).values(), key=lambda x: x["iter"]):
        c = (r.get("select") or {}).get("card")
        if not c:
            continue
        w = r["iter"] // width * width
        t = win.setdefault(w, Counter())
        for k, v in c["prop_in"].items():
            t["all"] += v
            t["draw"] += v if bare[str(k)] in DRAW else 0
            t["T4"] += v if bare[str(k)] in T4 else 0
    return {f"{w}-{w + width - 1}": {g: round(t[g] / t["all"], 4) for g in ("draw", "T4")} for w, t in sorted(win.items()) if t["all"]}


def lineage(run, it):
    """Mean copies a deck still shared with its generator root (the first saved form of the root deck, following parents), and the share of decks whose root is a generator deck."""
    first, parent, kind = {}, {}, {}
    for s in saved(run):
        if s > it:
            break
        for x in snapshot(run, s):
            first.setdefault(x["id"], x["deck"])
            parent[x["id"]] = x.get("parent")
            kind[x["id"]] = x.get("kind")

    def root(k):
        seen = set()
        while parent.get(k) is not None and parent[k] in first and k not in seen:
            seen.add(k)
            k = parent[k]
        return k
    shared, n = [], 0
    for x in snapshot(run, it):
        r = root(x["id"])
        shared.append(sum((Counter(x["deck"]) & Counter(first[r])).values()))
        n += 1
    return {"mean_copies_shared_with_root": round(float(np.mean(shared)), 2), "decks": n}


def stage(run, it=None):
    run = Path(run) if Path(run).is_absolute() else ROOT / run
    it = saved(run)[-1] if it is None else it
    pop = snapshot(run, it)
    rows = aw.rows(run)
    r = rows.get(it, {})
    tail = [aw.dist(rows[i]) for i in range(it - 4, it + 1) if i in rows]
    out = {"run": run.name, "iter": it, "population": set_reads([x["deck"] for x in pop]), "body": body_reads([x["deck"] for x in pop]), "wall_share": round(wall_share([x["deck"] for x in pop]), 3), "G1_last": round(aw.dist(r), 2) if r else None,
           "G1_mean5": round(float(np.mean(tail)), 2) if tail else None, "median_pte": [r["shape_quartiles"][k][1] for k in ("pokemon", "trainer", "energy")] if r else None,
           "age": {"mean": round(float(np.mean([it + 1 - x["born"] for x in pop])), 1), "median": float(np.median([it + 1 - x["born"] for x in pop]))},
           "errors": sum(x.get("errors", 0) for x in rows.values()), "games": sum(x.get("games", 0) for x in rows.values()),
           "turnover_kinds": dict(Counter(t["kind"] for x in rows.values() for t in (x.get("turnover") or []))),
           "survivors": survivors(run, it), "ledger_shares": ledger_shares(run), "lineage": lineage(run, it)}
    try:
        decks, _, _ = cc.g1_set(run, it)
        out["g1_set"] = set_reads(decks)
    except Exception as e:                       # a snapshot the log's top 12 can't be mapped onto
        out["g1_set"] = {"unavailable": repr(e)[:80]}
    return out


def band(it=129):
    """The record's band on population E and the ground-truth reads, at iteration it, for each seed pair."""
    runs = {a: [ROOT / "runs/screens" / n for n in names] for a, names in ARMS.items()}
    s = {a: [stage(r, it) for r in rs] for a, rs in runs.items()}
    d = [s["N"][k]["population"]["E"] - s["W"][k]["population"]["E"] for k in (0, 1)]
    if all(x <= -0.05 for x in d):
        b = "R-unpinned"
    elif all(abs(x) < 0.025 for x in d):
        b = "R-not-pinned"
    else:
        b = "between"
    gain = lambda f: [f(s["N"][k]) - f(s["W"][k]) for k in (0, 1)]
    g1 = gain(lambda x: x["G1_mean5"])
    t4 = gain(lambda x: x["g1_set"].get("T4", float("nan")))
    dr = gain(lambda x: x["g1_set"].get("draw", float("nan")))
    return {"iter": it, "band": b, "N_minus_W_E": [round(x, 4) for x in d], "G1_diff": [round(x, 2) for x in g1], "G1_gain": all(x <= -3.75 for x in g1),
            "T4_diff": [round(x, 3) for x in t4], "T4_gain": all(x >= 1.0 for x in t4), "draw_diff": [round(x, 3) for x in dr], "draw_gain": all(x >= 1.0 for x in dr),
            "W_TV": [s["W"][k]["population"]["TV"] for k in (0, 1)], "W_E": [s["W"][k]["population"]["E"] for k in (0, 1)], "fresh_at_29": {"TV": 0.606, "E": -0.024}, "stages": s}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", nargs="?")
    ap.add_argument("--iter", type=int, default=None)
    ap.add_argument("--band", action="store_true")
    a = ap.parse_args()
    if a.band:
        out = band(a.iter if a.iter is not None else 129)
        (D / f"band_it{out['iter']:04d}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(json.dumps({k: v for k, v in out.items() if k != "stages"}))
    else:
        print(json.dumps(stage(a.run, a.iter)))


if __name__ == "__main__":
    main()
