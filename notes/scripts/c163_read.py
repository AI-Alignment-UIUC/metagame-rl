"""C163 (runs/probe/C163-draw-deck-field/record.md, with Amendment 1): the crossed deck x field draw price. Each cell's price (copy - base in event
points/3, paired by deal), on the points and logit scales, with a bootstrap SE over deals (cells resampled independently), its base deck's score and
endings, and the acceptance checks. Then the hard floor from the full run's base scores, G, D, F, I, the slope b of per-deck price on base Energy (RR,
RL, pooled), the Energy gap between the L and R bases, D_c and G_c = effect - max(b, 0) * gap (at 4x on the logit scale; b is RR's slope when RL's full-run
base score is under 0.25, pooled otherwise, Amendment 2; the other is reported as D_c_alt and G_c_alt), the provisional flags (a base
score under 0.25 or over 0.75) and the bands, which read D_c and G_c; a provisional effect passes only if its logit version also does. Also LL per list
split into the 4 bench lists and the 20 held out, the swap direction (RR against C162, LL per copy against C144), price by opponent in LL and RL, and RL's
and RR's per-deck price against the deck's base score and two coherence proxies (exploratory, no band; reconstructed from #657's description: evo_complete
is the share of evolved Pokemon copies whose pre-evolution is in the deck, energy_match the share of basic Energy typed like a Pokemon in the deck).
  --stage pilot reads the timed pilot's files and writes pilot.json (logged, not used for the floor). --check CELL --file F checks one file against the
  record's kill rule (exit 3). --seed 92 reads arm 0 s2's files; --tag m1_ reads M1's (seed 91). --pattern 'pilot_{k}.json' tests the reader, writing nothing.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c163_read.py [--stage pilot] [--seed 91] [--tag m1_]
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

import c142_read as C142
from c139_read import boot, pts, r3
from c145_read import copy_checks, per_deal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C163-draw-deck-field"
CELLS = ("LL", "LR", "RL", "RR")
DRAW = ("Professor Oak", "Bill", "Gambler")
C162_RR, C144_LL, C144_COPIES = 0.0091, 0.0954, 5.92
FLOOR, CEILING = 0.15, 0.85
SOFT_LOW, SOFT_HIGH = 0.25, 0.75
LOGIT_AT_HALF = 4                                      # +0.04 points is +0.16 logit at a score of 0.5


def cell(path):
    """A cell's price, per-deal values, base score, endings and checks."""
    from rl.decks import Pool
    pool = Pool()
    card = {c["fullName"]: c for c in pool.cards}
    s = C142.read([path])
    r, d = per_deal(path, "oakbill", -1)
    base = {v["base"] for v in r["variants"]}
    games = [x for x in r["results"] if not x.get("error") and x["i"] in base]
    cards, names = r["deck_cards"], r["deck_names"]
    hit = lambda x: card[x]["name"] in DRAW
    legal = lambda c: len(c) == 60 and pool.legal(pool.vector(c))
    src = {k: names[k].removesuffix("-base") for k in base}
    checks = {**s["checks"], **copy_checks(r),
              "all_legal": all(legal(cards[v[k]]) for v in r["variants"] for k in ("base", "variant")),
              "base_no_draw": all(not any(hit(x) for x in cards[v["base"]]) for v in r["variants"]),
              "copy_is_2_oak_2_bill": all(v["replaced"] == 4 and v["added"] == {"Professor Oak": 2, "Bill": 2}
                                          and Counter(card[x]["name"] for x in cards[v["variant"]] if hit(x)) == Counter({"Professor Oak": 2, "Bill": 2})
                                          for v in r["variants"]),
              "never_itself": all(names[m["opp"]] != src[m["list"]] for m in r["meta"])}
    ok = all(v == 0 if k == "unpaired" else bool(v) for k, v in checks.items())
    xs = list(d.values())
    n = len(r["results"])
    by = defaultdict(dict)
    for x in r["results"]:
        if not x.get("error"):
            by[(x["i"], x["j"])][x["seed"]] = x
    deck, b0, c0 = [], [], []
    for m in r["meta"]:
        bg, cg = by[(m["list"], m["opp"])], by[(m["copies"]["oakbill"], m["opp"])]
        for sd in sorted(set(bg) & set(cg)):
            deck.append(m["list"])
            b0.append(pts(bg[sd])[0])
            c0.append(pts(cg[sd])[0])
    assert abs(float(np.mean(c0)) - float(np.mean(b0)) - sum(xs) / len(xs)) < 1e-9     # the same price as c145_read.per_deal
    energy = {v["base"]: sum(card[x]["superType"] == 3 for x in cards[v["base"]]) for v in r["variants"]}
    return {"r": r, "d": d, "xs": xs, "price": sum(xs) / len(xs), "se": boot(xs), "deals": len(xs), "base_score": sum(pts(x)[0] for x in games) / len(games),
            "endings": dict(Counter(x.get("ending") for x in games)), "errors": s["errors"], "error_rate": s["errors"] / max(1, n), "checks": checks, "ok": ok,
            "last": r.get("last", {}), "deck": np.array(deck), "b0": np.array(b0, dtype=float), "c0": np.array(c0, dtype=float), "energy": energy}


def logit(p):
    p = np.clip(p, 1e-3, 1 - 1e-3)
    return np.log(p / (1 - p))


def slope_points(c, cn, pick):
    """A cell's per-deck price against the deck's base Energy, as (x, y), for the deals in pick."""
    deck, diff = c[cn]["deck"][pick], c[cn]["c0"][pick] - c[cn]["b0"][pick]
    n = np.bincount(deck)
    tot = np.bincount(deck, weights=diff)
    ks = np.nonzero(n)[0]
    return np.array([c[cn]["energy"][int(k)] for k in ks], dtype=float), tot[ks] / n[ks]


def forms(g, rl_out, lr_out):
    """G and whichever D, F and I forms the floor rule allows, from four cell values."""
    out = {"G": g["LL"] - g["RR"]}
    if rl_out:
        out.update(D=g["LR"] - g["RR"], F=g["LL"] - g["LR"])
    elif lr_out:
        out.update(D=g["LL"] - g["RL"], F=g["RL"] - g["RR"])
    else:
        out.update(D=0.5 * ((g["LL"] - g["RL"]) + (g["LR"] - g["RR"])), F=0.5 * ((g["LL"] - g["LR"]) + (g["RL"] - g["RR"])),
                   I=(g["LL"] - g["LR"]) - (g["RL"] - g["RR"]))
    return out


def relied(rl_out, lr_out):
    """Which cells each effect rests on, under the floor rule."""
    four = set(CELLS)
    return {"G": {"LL", "RR"}, "D": {"LR", "RR"} if rl_out else {"LL", "RL"} if lr_out else four,
            "F": {"LL", "LR"} if rl_out else {"RL", "RR"} if lr_out else four, "I": four}


def estimate(c, picks, gap, rl_out, lr_out, use_rr):
    pts_cell = {k: float(c[k]["c0"][picks[k]].mean() - c[k]["b0"][picks[k]].mean()) for k in CELLS}
    log_cell = {k: float(logit(c[k]["c0"][picks[k]].mean()) - logit(c[k]["b0"][picks[k]].mean())) for k in CELLS}
    pp, ll = forms(pts_cell, rl_out, lr_out), forms(log_cell, rl_out, lr_out)
    xr, yr = slope_points(c, "RR", picks["RR"])
    xl, yl = slope_points(c, "RL", picks["RL"])
    fit = lambda x, y: float(np.polyfit(x, y, 1)[0]) if len(set(x.tolist())) > 1 else 0.0
    b_rr, b_rl, b = fit(xr, yr), fit(xl, yl), fit(np.r_[xr, xl], np.r_[yr, yl])
    out = {f"cell_{k}": pts_cell[k] for k in CELLS} | {f"logit_{k}": log_cell[k] for k in CELLS} | {"b_RR": b_rr, "b_RL": b_rl, "b": b}
    out.update(pp)
    out.update({f"{k}_logit": v for k, v in ll.items()})
    band_b, alt_b = (b_rr, b) if use_rr else (b, b_rr)                # Amendment 2: a floored RL's slope would shrink the correction
    out["band_b"] = band_b
    fix = max(band_b, 0.0) * gap
    out.update({"D_c": pp["D"] - fix, "G_c": pp["G"] - fix, "D_c_logit": ll["D"] - LOGIT_AT_HALF * fix, "G_c_logit": ll["G"] - LOGIT_AT_HALF * fix,
                "D_c_alt": pp["D"] - max(alt_b, 0.0) * gap, "G_c_alt": pp["G"] - max(alt_b, 0.0) * gap})
    return out


def effects(c, gap, rl_out, lr_out, use_rr, reps=2000):
    """Every estimate with its SE, resampling each cell's deals independently, so the SE carries the slope's own noise."""
    rng = np.random.default_rng(163)
    point = estimate(c, {k: np.arange(len(c[k]["b0"])) for k in CELLS}, gap, rl_out, lr_out, use_rr)
    runs = defaultdict(list)
    for _ in range(reps):
        picks = {k: rng.integers(len(c[k]["b0"]), size=len(c[k]["b0"])) for k in CELLS}
        for k, v in estimate(c, picks, gap, rl_out, lr_out, use_rr).items():
            runs[k].append(v)
    return {k: {"est": v, "se": float(np.std(runs[k], ddof=1))} for k, v in point.items()}


def band(e, prov, rl_out, lr_out):
    """The record's bands, reading D_c and G_c. A provisional effect passes a threshold only if its logit version does too (the threshold times 4)."""
    if rl_out and lr_out:
        return "R-floor"
    tag = {"G_c": "G", "D_c": "D", "F": "F"}

    def big(name, t):
        ok = e[name]["est"] >= t and e[name]["est"] >= 2 * e[name]["se"]
        if ok and prov[tag[name]]:
            lg = e[f"{name}_logit"]
            ok = lg["est"] >= LOGIT_AT_HALF * t and lg["est"] >= 2 * lg["se"]
        return ok

    def under(name, t):
        return e[name]["est"] < t and (not prov[tag[name]] or e[f"{name}_logit"]["est"] < LOGIT_AT_HALF * t)
    if not big("G_c", 0.03):
        return "R-no-gap"
    if big("D_c", 0.04) and under("F", 0.02):
        return "R-deck"
    if big("F", 0.04) and under("D_c", 0.02):
        return "R-field"
    if big("D_c", 0.02) and big("F", 0.02):
        return "R-both"
    return "between"


def per_deck(c):
    """Per-deck (and per-opponent) prices of a cell."""
    r, d = c["r"], c["d"]
    deck, opp, names = defaultdict(list), defaultdict(list), r["deck_names"]
    lst = {m["key"]: m for m in r["meta"]}
    for (key, _), x in d.items():
        deck[lst[key]["list"]].append(x)
        opp[names[lst[key]["opp"]]].append(x)
    return deck, opp


def proxies(cards, card):
    mons = [card[x] for x in cards if card[x]["superType"] == 1]
    have = {m["name"] for m in mons}
    evo = [m for m in mons if m.get("evolvesFrom")]
    types = {t for m in mons for t, v in enumerate(m["types"]) if v}
    es = [card[x] for x in cards if card[x]["superType"] == 3 and card[x]["energyType"] == 0]
    return (sum(m["evolvesFrom"] in have for m in evo) / len(evo) if evo else 1.0,
            sum(any(e["provides"][t] for t in types) for e in es) / len(es) if es else 0.0)


def corr(x, y):
    return r3(float(np.corrcoef(x, y)[0, 1])) if len(set(x)) > 1 and len(set(y)) > 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="full", choices=["full", "pilot"])
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--check", default="")
    ap.add_argument("--file", default="", help="with --check: the file to check")
    ap.add_argument("--tag", default="", help="m1_: M1's files")
    ap.add_argument("--pattern", default="", help="a test of the reader on other files, e.g. pilot_{k}.json; writes nothing")
    a = ap.parse_args()
    if a.check:
        c = cell(Path(a.file) if a.file else OUT / f"{a.check}_{a.tag}s{a.seed}.json")
        print(json.dumps({"cell": a.check, "deals": c["deals"], "base_score": r3(c["base_score"]), "price": r3(c["price"]), "se": r3(c["se"]),
                          "error_rate": r3(c["error_rate"]), "ok": c["ok"], "last": {k: c["last"].get(k) for k in ("games", "seconds", "games_per_s")},
                          "checks": c["checks"]}))
        sys.exit(0 if c["ok"] and c["error_rate"] <= 0.02 else 3)
    if a.stage == "pilot":
        out = {}
        for k in CELLS:
            c = cell(OUT / f"pilot_{k}.json")
            out[k] = {"deals": c["deals"], "base_score": r3(c["base_score"]), "price": r3(c["price"]), "se": r3(c["se"]), "games_per_s": c["last"].get("games_per_s"),
                      "outside_0.15_0.85": not FLOOR <= c["base_score"] <= CEILING, "endings": c["endings"], "errors": c["errors"], "ok": c["ok"], "checks": c["checks"]}
        (OUT / "pilot.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(json.dumps(out, indent=1))
        return
    c = {k: cell(OUT / (a.pattern.format(k=k) if a.pattern else f"{k}_{a.tag}s{a.seed}.json")) for k in CELLS}
    hard = {k: not FLOOR <= c[k]["base_score"] <= CEILING for k in CELLS}          # Amendment 1: read from the full run
    rl_out, lr_out = hard["RL"], hard["LR"]
    en_l, en_r = list(c["LL"]["energy"].values()), list(c["RR"]["energy"].values())
    gap = float(np.mean(en_l) - np.mean(en_r))
    use_rr = c["RL"]["base_score"] < SOFT_LOW
    e = effects(c, gap, rl_out, lr_out, use_rr)
    soft = {k: not SOFT_LOW <= c[k]["base_score"] <= SOFT_HIGH for k in CELLS}
    prov = {k: any(soft[x] for x in v) for k, v in relied(rl_out, lr_out).items() if k in e}
    b = band(e, prov, rl_out, lr_out)
    from rl.decks import Pool
    card = {x["fullName"]: x for x in Pool().cards}
    bench = {d["name"] for m in json.loads((ROOT / "runs/probe/BENCH/bench_matchups.json").read_text(encoding="utf-8")) for d in m}
    deck_ll, opp_ll = per_deck(c["LL"])
    _, opp_rl = per_deck(c["RL"])
    names = c["LL"]["r"]["deck_names"]
    split = {"bench": [], "held": []}
    for k, xs in deck_ll.items():
        split["bench" if names[k].removesuffix("-base") in bench else "held"] += xs
    exploratory = {}
    for cn in ("RL", "RR"):
        deck, _ = per_deck(c[cn])
        r = c[cn]["r"]
        score = defaultdict(list)
        for x in r["results"]:
            if not x.get("error") and x["i"] in deck:
                score[x["i"]].append(pts(x)[0])
        ks = sorted(deck)
        y = [float(np.mean(deck[k])) for k in ks]
        pr = [proxies(r["deck_cards"][k], card) for k in ks]
        exploratory[cn] = {"base_score": corr([float(np.mean(score[k])) for k in ks], y), "evo_complete": corr([p[0] for p in pr], y), "energy_match": corr([p[1] for p in pr], y)}
    out = {"seed": a.seed, "tag": a.tag, "pilot": c["LL"]["r"]["pilot"], "band": b, "rl_unreadable": rl_out, "lr_unreadable": lr_out,
           "cells": {k: {"deals": c[k]["deals"], "price": r3(c[k]["price"]), "se": r3(c[k]["se"]), "logit_price": r3(e[f"logit_{k}"]["est"]), "logit_se": r3(e[f"logit_{k}"]["se"]),
                         "base_score": r3(c[k]["base_score"]), "copy_score": r3(float(c[k]["c0"].mean())), "endings": c[k]["endings"],
                         "errors": c[k]["errors"], "ok": c[k]["ok"], "games_per_s": c[k]["last"].get("games_per_s")} for k in CELLS},
           "band_slope": "RR" if use_rr else "pooled", "hard_unreadable": hard, "soft_provisional_cells": soft, "provisional": prov, "ll_or_rr_unreadable": hard["LL"] or hard["RR"],
           "effects": {k: {"est": r3(v["est"]), "se": r3(v["se"])} for k, v in e.items()},
           "energy": {"L_mean": r3(float(np.mean(en_l))), "R_mean": r3(float(np.mean(en_r))), "gap": r3(gap), "R_range": [min(en_r), max(en_r)],
                      "L_share_inside_R_range": r3(float(np.mean([min(en_r) <= x <= max(en_r) for x in en_l])))},
           "ll_split": {k: {"deals": len(v), "price": r3(float(np.mean(v))), "se": r3(boot(v))} for k, v in split.items()},
           "swap": {"RR_minus_C162": r3(c["RR"]["price"] - C162_RR), "LL_per_copy": r3(c["LL"]["price"] / 4), "C144_per_copy": r3(C144_LL / C144_COPIES)},
           "by_opponent": {cn: {k: r3(float(np.mean(v))) for k, v in sorted(o.items(), key=lambda t: -np.mean(t[1]))} for cn, o in (("LL", opp_ll), ("RL", opp_rl))},
           "exploratory_per_deck_corr": exploratory, "checks": {k: c[k]["checks"] for k in CELLS}}
    if not a.pattern:
        (OUT / f"summary_{a.tag}s{a.seed}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
