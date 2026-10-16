"""Length x coverage 2x2 (log #75/#76): the pre-registered statistics, from the evaluation outputs and training logs.

mix-sN and len-sN resume base (N = 1) / base-s2 (N = 2) from it79 to T-1, half on rules-only random decks (mix) or
on the population decks alone (len). Readout snapshots K = {T-41, T-21, T-1}, R = T-1. The archived lists and
SimpleBot are evaluation only.
  P1       archived SimpleBot (lm_sb, deal seed 78): mix - len paired by game index, D_s = mean over K; bootstrap
           over game indices (2000 resamples, seed 0, one index draw for every seed and K)
  P2       archived pilot-vs-pilot (lm_pairs_archived): mix vs len pooled over K (H_s), and over both seeds
  NI       held-out pilot-vs-pilot (lm_pairs_heldout) mix vs len pooled >= 0.46
  verdict  NEGATIVE, NULL, COVERAGE-POSITIVE, TRADE-OFF, WEAK-POSITIVE, else INCONCLUSIVE (first match)
  length   len-s@R against base(-s2)@79: ladder score (lm_ladder) and archived SimpleBot gain (lm_sb - gate0)
  also     Elo, curves, the gain per archived list against its Trainer count (Spearman), training health per arm,
           the pilot of record, the interim check and the random panel (report only)
A seed pair without every K snapshot (an arm killed early) is left out of the verdict, with a note; missing files
are skipped. Writes <dir>/length_mix_report.json.

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/length_mix_report.py [--T 220] [--dir runs/abl]
"""
import argparse
import json
import re
import warnings
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SEEDS = (1, 2)
BASE = {1: "base@79", 2: "base-s2@79"}
ARMS = ("mix-s1", "len-s1", "mix-s2", "len-s2")
SB_SEED = {"archived": 78, "heldout": 79, "random": 80}
INPUTS = ("gate0", "lm_ladder", "lm_pairs_heldout", "lm_pairs_random", "lm_pairs_archived", "lm_curve", "lm_sb",
          "lm_sb_heldout", "lm_sb_random", "lm_sb_fresh", "lm_interim")
BOOT = 2000
KINDS = ("PP", "PR", "RR")
HEALTH = ("ev_mc", "ev_open", "kl_last", "grad_norm", "entropy", "kl", "steps_per_game")


def slug(label):
    return re.sub(r"[^A-Za-z0-9@._-]", "_", label)


def jload(path):
    """A JSON object, or None (missing, cut off or not an object)."""
    try:
        x = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return x if isinstance(x, dict) else None


def rnd(x, k=4):
    return None if x is None or not np.isfinite(x) else round(float(x), k)


def nanmean(arrs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmean(np.stack(arrs), 0)


def ab(key, e):
    """A pairs entry's pilots (from its fields, else its key "A vs B")."""
    return (e["a"], e["b"]) if "a" in e and "b" in e else tuple(key.split(" vs ", 1))


def labels(outs):
    """{run: {iteration}} for every run@N an evaluation output names."""
    found = set()
    for o in filter(None, outs.values()):
        found |= set(o.get("simplebot") or {})
        found |= set((o.get("ladder") or {}).get("pilots") or [])
        for key, e in (o.get("pairs") or {}).items():
            found |= set(ab(key, e))
        for run, c in (o.get("curve") or {}).items():
            found |= {f"{run}@{int(k)}" for k in c if str(k).isdigit()}
    its = {}
    for lab in found:
        m = re.fullmatch(r"(.+)@(\d+)", str(lab))
        if m:
            its.setdefault(m[1], set()).add(int(m[2]))
    return its


def find_rows(d, ref, sub, default):
    """A rows file: by name under <dir>/<sub> first (so a copied directory works), then as recorded."""
    cands = [d / sub / Path(ref).name] if ref else []
    cands += [d / sub / default] + ([d / ref, ROOT / ref] if ref else [])
    return next((c for c in cands if c.is_file()), None)


def sb_entry(outs, stem, label, kind):
    return (((outs.get(stem) or {}).get("simplebot") or {}).get(label) or {}).get(kind)


def sb_games(d, outs, stem, label, kind):
    """SimpleBot games of `label` on set `kind` from <stem>.json: {game index: row}, index = deal seed - SEED * 1000003."""
    e = sb_entry(outs, stem, label, kind)
    f = e and find_rows(d, e.get("rows"), "sb_rows", f"{stem}__{slug(label)}__{kind}.json")
    r = jload(f) if f else None
    if not r or not r.get("rows"):
        return None
    base = int(e.get("seed", SB_SEED[kind])) * 1000003
    return {int(x["seed"]) - base: x for x in r["rows"]}


def paired(a, b):
    """{index: (a xWins - b xWins, xDeck)} over the game indices both have (the same deal and deck)."""
    return {i: (a[i]["xWins"] - b[i]["xWins"], a[i]["xDeck"]) for i in sorted(a.keys() & b.keys())}


def paired_diff(a, b):
    if not a or not b:
        return None
    p = paired(a, b)
    return {"d": rnd(np.mean([x for x, _ in p.values()])), "n": len(p)} if p else None


def pair_score(outs, stem, a, b):
    """(wins of a, games) from <stem>.json's pairs, in either order, or None."""
    for key, e in ((outs.get(stem) or {}).get("pairs") or {}).items():
        x = ab(key, e)
        if x in ((a, b), (b, a)) and e.get("games"):
            w = e["wins_a"] if "wins_a" in e else e["score_a"] * e["games"]
            return (w if x == (a, b) else e["games"] - w), e["games"]
    return None


def pooled(outs, stem, pairs):
    got = [x for x in (pair_score(outs, stem, a, b) for a, b in pairs) if x]
    g = sum(x[1] for x in got)
    return {"score": sum(x[0] for x in got) / g, "games": int(g), "pairs": len(got)} if g else None


def boot_means(cells):
    """Each cell's mean diff in BOOT resamples of the game indices, one draw for all cells (seed 0): {cell: [BOOT]}."""
    idx = sorted(set().union(*cells.values()))
    pos = {i: n for n, i in enumerate(idx)}
    draw = np.random.default_rng(0).integers(len(idx), size=(BOOT, len(idx)))
    w = np.apply_along_axis(np.bincount, 1, draw, minlength=len(idx)).astype(float)
    out = {}
    for c, v in cells.items():
        x, m = np.zeros(len(idx)), np.zeros(len(idx))
        for i, (dx, _) in v.items():
            x[pos[i]], m[pos[i]] = dx, 1
        with np.errstate(invalid="ignore", divide="ignore"):
            out[c] = (w @ x) / (w @ m)               # nan where the draw holds none of this cell's games
    return out


def ci(x):
    x = x[np.isfinite(x)]
    return {"80": [rnd(v) for v in np.percentile(x, [10, 90])],
            "95": [rnd(v) for v in np.percentile(x, [2.5, 97.5])]} if len(x) else None


def ranks(x):
    """Ranks from 0, ties averaged."""
    x = np.asarray(x, float)
    r = np.empty(len(x))
    r[np.argsort(x, kind="stable")] = np.arange(len(x))
    for v in np.unique(x):
        r[x == v] = r[x == v].mean()
    return r


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    return None if len(x) < 3 or rx.std() == 0 or ry.std() == 0 else float(np.corrcoef(rx, ry)[0, 1])


def trainer_counts():
    """Trainer count of each archived list (via Node), or None."""
    try:
        from rl.decks import Pool, archived_decks, deck_shape
        pool = Pool()
        return {n: deck_shape(pool, v)["trainer"] for n, v in archived_decks(pool)}
    except Exception:
        return None


def log_rows(d, arm, start=80):
    """An arm's training rows from iteration `start` on (a resumed run may repeat an iteration: keep the last)."""
    f, rows = d / arm / "log.jsonl", {}
    if not f.is_file():
        return []
    for line in open(f, encoding="utf-8"):
        if '"transitions"' in line:
            try:
                r = json.loads(line)
            except ValueError:                           # a line cut off mid-write
                continue
            if r.get("iteration", -1) >= start:
                rows[r["iteration"]] = r
    return [rows[k] for k in sorted(rows)]


def rates(parts):
    """Pooled {games, endings, steps, errors, cut} -> cut and error rates, mean steps, deck-out share of endings."""
    g = sum(p.get("games", 0) for p in parts)
    if not g:
        return None
    ends = Counter()
    for p in parts:
        ends.update(p.get("endings") or {})
    return {"games": int(g), "cut": rnd(sum(p.get("cut", 0) for p in parts) / g),
            "errors": rnd(sum(p.get("errors", 0) for p in parts) / g),
            "steps": rnd(sum(p.get("steps", 0) * p.get("games", 0) for p in parts) / g, 1),
            "deck_out": rnd(ends.get("deck-out", 0) / max(sum(ends.values()), 1), 3)}


def means(rows):
    out = {}
    for k in HEALTH:
        v = [r[k] for r in rows if isinstance(r.get(k), (int, float))]
        out[k] = rnd(np.mean(v)) if v else None
    return out


def health(rows):
    if not rows:
        return None
    whole = [{"games": r["games"], "endings": r.get("endings"), "steps": r.get("steps_per_game", 0), "errors": r.get("errors", 0),
              "cut": r["cut"] if "cut" in r else max((r.get("endings") or {}).get("none", 0) - r.get("errors", 0), 0)}
             for r in rows]
    return {"iterations": [rows[0]["iteration"], rows[-1]["iteration"]], "rows": len(rows),
            "s_per_iter": rnd(np.mean([r.get("collect_s", 0) + r.get("train_s", 0) for r in rows]), 1),
            "lr_last": rows[-1].get("lr"), "all": rates(whole),
            "by_kind": {k: rates([r["endings_by_kind"][k] for r in rows if k in (r.get("endings_by_kind") or {})]) for k in KINDS},
            "it80_99": means([r for r in rows if r["iteration"] <= 99]), "last20": means(rows[-20:])}


def verdict(D, up80, H, p1, p2, ni):
    """The pre-registered verdict, first match wins; (verdict, reason)."""
    if D is None or H is None:
        return "INCONCLUSIVE", "P1 or P2 inputs missing"
    if D <= -0.03 or H <= 0.47:
        return "NEGATIVE", "mean D <= -0.03 or pooled H <= 0.47"
    if (D < 0.02 and H < 0.52) or up80 < 0.04:
        return "NULL", "mean D < +0.02 and pooled H < 0.52, or the upper 80% bound of mean D < +0.04"
    if ni is None:
        return "INCONCLUSIVE", "NI inputs missing"
    if p1 and p2:
        return ("COVERAGE-POSITIVE", "P1, P2 and NI pass") if ni else ("TRADE-OFF", "P1 and P2 pass, NI fails")
    if p1 != p2 and (D > 0 if p2 else H > 0.5) and ni:
        return "WEAK-POSITIVE", "one of P1/P2 passes, the other has the same sign, NI passes"
    return "INCONCLUSIVE", "no rule matched"


def report(d, T):
    K, R = (T - 41, T - 21, T - 1), T - 1
    outs = {k: jload(d / f"{k}.json") for k in INPUTS}
    notes = []
    rep = {"T": T, "K": list(K), "R": R, "dir": str(d), "missing": [f"{k}.json" for k, v in outs.items() if v is None]}

    # Seed pairs: complete when both arms have every K snapshot (a model file, or a label some evaluation recorded).
    seen = labels(outs)
    snaps = {a: {int(p.stem[-5:]) for p in (d / a).glob("model_it*.pt")} | seen.get(a, set()) for a in ARMS}
    lacks = {s: [f"{a}-s{s}@{k}" for a in ("mix", "len") for k in K if k not in snaps[f"{a}-s{s}"]] for s in SEEDS}
    used = [s for s in SEEDS if not lacks[s]]
    for s in SEEDS:
        if lacks[s]:
            notes.append(f"seed {s} pair lacks {', '.join(lacks[s])}: left out of the verdict")
    if not used:
        notes.append("no complete seed pair")
    rep["complete_seeds"] = used

    # P1: archived SimpleBot, deal-paired.
    cells = {}
    for s in SEEDS:
        for k in K:
            a = sb_games(d, outs, "lm_sb", f"mix-s{s}@{k}", "archived")
            b = sb_games(d, outs, "lm_sb", f"len-s{s}@{k}", "archived")
            if a and b and a.keys() & b.keys():
                cells[s, k] = paired(a, b)
            elif s in used:
                notes.append(f"P1: no paired lm_sb archived rows for mix-s{s}@{k} / len-s{s}@{k}")
    bm = boot_means(cells) if cells else {}
    Ds, Db, P1 = {}, {}, {"seeds": {}}
    for s in SEEDS:
        ks = [k for k in K if (s, k) in cells]
        if not ks:
            continue
        dk = {k: float(np.mean([x for x, _ in cells[s, k].values()])) for k in ks}
        Ds[s], Db[s] = float(np.mean(list(dk.values()))), nanmean([bm[s, k] for k in ks])
        P1["seeds"][s] = {"D": rnd(Ds[s]), "ci": ci(Db[s]), "d": {k: rnd(v) for k, v in dk.items()},
                          "n": {k: len(cells[s, k]) for k in ks}, "complete": s in used,
                          "win": {f"{a}-s{s}@{k}": (sb_entry(outs, "lm_sb", f"{a}-s{s}@{k}", "archived") or {}).get("win")
                                  for k in ks for a in ("mix", "len")}}
    ds = [s for s in used if s in Ds]
    D = float(np.mean([Ds[s] for s in ds])) if ds else None
    Dci = ci(nanmean([Db[s] for s in ds])) if ds else None
    p1 = None if D is None else D >= 0.05 and all(Ds[s] > 0 for s in ds)
    P1.update({"seeds_used": ds, "mean_D": rnd(D), "ci": Dci, "pass": p1})
    rep["P1"] = P1

    # P2: archived pilot-vs-pilot; NI: held-out pilot-vs-pilot.
    def by_seed(stem, ks):
        per = {s: pooled(outs, stem, [(f"mix-s{s}@{k}", f"len-s{s}@{k}") for k in ks]) for s in SEEDS}
        for s in used:
            if (per[s] or {}).get("pairs", 0) < len(ks) and outs[stem]:
                notes.append(f"{stem}: seed {s} has {(per[s] or {}).get('pairs', 0)} of {len(ks)} mix-vs-len pairs")
        both = pooled(outs, stem, [(f"mix-s{s}@{k}", f"len-s{s}@{k}") for s in used for k in ks])
        return {"seeds": {s: v and {**v, "score": rnd(v["score"])} for s, v in per.items()}, "pooled": both}, per
    P2, per = by_seed("lm_pairs_archived", K)
    H = P2["pooled"]["score"] if P2["pooled"] else None
    hs = [per[s]["score"] for s in used if per[s]]
    p2 = None if H is None else H >= 0.55 and len(hs) == len(used) and all(h > 0.52 for h in hs)
    P2.update({"seeds_used": used, "pass": p2})
    if P2["pooled"]:
        P2["pooled"]["score"] = rnd(H)
    rep["P2"] = P2
    NI, _ = by_seed("lm_pairs_heldout", K)
    ni_s = NI["pooled"]["score"] if NI["pooled"] else None
    NI.update({"pass": None if ni_s is None else ni_s >= 0.46,
               "sb_heldout_mix_minus_len": {s: paired_diff(sb_games(d, outs, "lm_sb_heldout", f"mix-s{s}@{R}", "heldout"),
                                                           sb_games(d, outs, "lm_sb_heldout", f"len-s{s}@{R}", "heldout"))
                                            for s in SEEDS}})
    if NI["pooled"]:
        NI["pooled"]["score"] = rnd(ni_s)
    rep["NI"] = NI
    up80 = Dci["80"][1] if Dci else None
    rep["verdict"], rep["verdict_reason"] = verdict(D, up80, H, p1, p2, NI["pass"]) if used else \
        ("INCONCLUSIVE", "no complete seed pair")
    if used and len(used) < len(SEEDS):
        notes.append(f"verdict from seed {used[0]} only")

    # Length: len-s@R against base(-s2)@79.
    lad = (outs["lm_ladder"] or {}).get("ladder") or {}
    pil, mat = lad.get("pilots") or [], lad.get("matrix") or lad
    L = {"seeds": {}}
    lw = lg = 0
    for s in SEEDS:
        a, b = f"len-s{s}@{R}", BASE[s]
        x = {}
        if a in pil and b in pil and mat.get("games"):
            w, g = mat["wins"][pil.index(a)][pil.index(b)], mat["games"][pil.index(a)][pil.index(b)]
            if g:
                x.update({"ladder_score": rnd(w / g), "ladder_games": int(g)})
                lw, lg = lw + w, lg + g
        gain = paired_diff(sb_games(d, outs, "lm_sb", a, "archived"), sb_games(d, outs, "gate0", b, "archived"))
        if gain:
            x.update({"archived_gain": gain["d"], "archived_n": gain["n"]})
        if x:
            L["seeds"][s] = x
    L["pooled_ladder_score"] = rnd(lw / lg) if lg else None
    gains = [v.get("archived_gain") for v in L["seeds"].values() if "ladder_score" in v]
    L["call"] = None if not lg else "spent" if lw / lg < 0.55 else \
        "large" if lw / lg >= 0.60 and len(gains) == len(SEEDS) and all(x is not None and x >= 0.05 for x in gains) else "partial"
    rep["length"] = L
    rep["elo"] = {k: [lad["elo"][k], (lad.get("elo_se") or {}).get(k)] for k in lad.get("elo") or {}}
    rep["curve"] = (outs["lm_curve"] or {}).get("curve") or {}
    g0 = outs["gate0"] or {}
    rep["gate0"] = {"elo": {k: [v, ((g0.get("ladder") or {}).get("elo_se") or {}).get(k)]
                            for k, v in ((g0.get("ladder") or {}).get("elo") or {}).items()},
                    "simplebot_archived": {k: (v.get("archived") or {}).get("win") for k, v in (g0.get("simplebot") or {}).items()}}

    # Dose-response: gain per archived list (pooled over seeds and K) against its Trainer count.
    use = [c for c in cells if c[0] in (ds or Ds)]
    per_deck = {}
    for c in use:
        for x, deck in cells[c].values():
            per_deck.setdefault(deck, []).append(x)
    tc = trainer_counts() if per_deck else None
    dose = {"seeds": sorted({c[0] for c in use}), "decks": {k: {"gain": rnd(np.mean(v)), "n": len(v), "trainers": (tc or {}).get(k)}
                                                       for k, v in sorted(per_deck.items())}}
    both = [(v["gain"], v["trainers"]) for v in dose["decks"].values() if v["trainers"] is not None and v["gain"] is not None]
    dose["spearman"] = rnd(spearman(*zip(*both))) if len(both) >= 3 else None
    if per_deck and tc is None:
        notes.append("dose-response: archived Trainer counts unavailable (rl.decks.archived_decks failed)")
    elif per_deck and len(both) < len(per_deck):
        notes.append(f"dose-response: {len(per_deck) - len(both)} lists not matched to an archived deck")
    rep["dose_response"] = dose

    rep["health"] = {a: health(log_rows(d, a)) for a in ARMS}

    # Pilot of record: the mix seed if coverage-positive, else the len seed, with the higher archived mean over K
    # (complete seed pairs first; the arm must have reached R).
    kind = "mix" if rep["verdict"] == "COVERAGE-POSITIVE" else "len"
    arch = {}
    for s in used or SEEDS:
        v = [e["win"] for e in (sb_entry(outs, "lm_sb", f"{kind}-s{s}@{k}", "archived") for k in K) if e and e.get("win") is not None]
        if v and R in snaps[f"{kind}-s{s}"]:
            arch[s] = float(np.mean(v))
    if arch:
        s = max(arch, key=arch.get)
        lab = f"{kind}-s{s}@{R}"
        e78, e81 = sb_entry(outs, "lm_sb", lab, "archived") or {}, sb_entry(outs, "lm_sb_fresh", lab, "archived") or {}
        rep["pilot_of_record"] = {"pilot": lab, "archived_mean_over_K": rnd(arch[s]), "means": {k: rnd(v) for k, v in arch.items()},
                                  "seed78": [e78.get("win"), e78.get("ci95")], "seed81_fresh": [e81.get("win"), e81.get("ci95")],
                                  "note": "selected on the archived lists (seed-78 deals): its seed-78 score is optimistic; "
                                          "seed 81 is fresh deals on the same lists"}
    else:
        rep["pilot_of_record"] = None
    rep["fresh"] = {f"{a}-s{s}@{R}": [(sb_entry(outs, "lm_sb", f"{a}-s{s}@{R}", "archived") or {}).get("win"),
                                      (sb_entry(outs, "lm_sb_fresh", f"{a}-s{s}@{R}", "archived") or {}).get("win")]
                    for s in SEEDS for a in ("mix", "len")}

    # Report only: the interim check, the random panel (in distribution for mix, out of it for len and base).
    rep["interim"] = {lab: (sb_entry(outs, "lm_interim", lab, "archived") or {}).get("win") for lab in (f"mix-s1@{R}", f"len-s1@{R}")}
    rep["interim"]["mix_minus_len"] = paired_diff(sb_games(d, outs, "lm_interim", f"mix-s1@{R}", "archived"),
                                                  sb_games(d, outs, "lm_interim", f"len-s1@{R}", "archived"))
    rnd_sb = {}
    for lab in [f"{a}-s{s}@{R}" for s in SEEDS for a in ("mix", "len")] + list(BASE.values()):
        e = sb_entry(outs, "lm_sb_random", lab, "random")
        if e:
            rnd_sb[lab] = {"win": e.get("win"), "ci95": e.get("ci95"), "games": e.get("games"),
                           "panel": "in distribution" if lab.startswith("mix") else "out of distribution"}
    rep["random_panel"] = {
        "simplebot": rnd_sb,
        "simplebot_mix_minus_len": {s: paired_diff(sb_games(d, outs, "lm_sb_random", f"mix-s{s}@{R}", "random"),
                                                   sb_games(d, outs, "lm_sb_random", f"len-s{s}@{R}", "random")) for s in SEEDS},
        "pairs_mix_vs_len": by_seed("lm_pairs_random", K)[0]["seeds"]}
    rep["archived_vs_pilot_v2"] = {lab: v and {**v, "score": rnd(v["score"])}
                                   for lab in [f"{a}-s{s}@{R}" for s in SEEDS for a in ("mix", "len")]
                                   for v in [pooled(outs, "lm_pairs_archived", [(lab, "pilot-v2")])]}
    rep["notes"] = notes
    return rep


def show(rep):
    def sg(x):
        return "n/a" if x is None else f"{x:+.3f}"

    def sc(x):
        return "n/a" if x is None else f"{x:.3f}"

    def cis(c):
        return "" if not c else f"  80% [{sg(c['80'][0])}, {sg(c['80'][1])}]  95% [{sg(c['95'][0])}, {sg(c['95'][1])}]"

    def pool(v):
        return "n/a" if not v else f"{v['score']:.3f} ({v['games']} games, {v['pairs']} pairs)"

    def elo(es):
        return "  ".join(f"{k} {'n/a' if e is None else f'{e:+.0f}'} (se {se or 0:.0f})" for k, (e, se) in es.items())

    print(f"length x coverage, T = {rep['T']}: K = {rep['K']}, R = {rep['R']} ({rep['dir']})")
    if rep["missing"]:
        print("  missing:", " ".join(rep["missing"]))
    print(f"  complete seed pairs: {rep['complete_seeds'] or 'none'}")
    P1 = rep["P1"]
    print("P1  archived SimpleBot, mix - len, deal-paired (lm_sb, seed 78)")
    for s, v in P1["seeds"].items():
        cells = "  ".join(f"@{k} {sg(x)} (n {v['n'][k]})" for k, x in v["d"].items())
        print(f"  s{s}: {cells}  D_{s} {sg(v['D'])}{cis(v['ci'])}{'' if v['complete'] else '  (incomplete pair)'}")
    print(f"  mean D {sg(P1['mean_D'])}{cis(P1['ci'])}  seeds {P1['seeds_used']}  pass {P1['pass']}")
    for name in ("P2", "NI"):
        v = rep[name]
        print(f"{name}  {'archived' if name == 'P2' else 'held-out'} pilot-vs-pilot, mix vs len: "
              + "  ".join(f"s{s} {pool(x)}" for s, x in v["seeds"].items()) + f"  pooled {pool(v['pooled'])}  pass {v['pass']}")
    print("    SimpleBot held-out mix@R - len@R: "
          + "  ".join(f"s{s} {sg(x and x['d'])}" for s, x in rep["NI"]["sb_heldout_mix_minus_len"].items()))
    print(f"VERDICT  {rep['verdict']}  ({rep['verdict_reason']})")
    L = rep["length"]
    print(f"length  len-s@R vs base@79: pooled ladder {sc(L['pooled_ladder_score'])}  call {L['call']}")
    for s, v in L["seeds"].items():
        print(f"  s{s}: ladder {sc(v.get('ladder_score'))} ({v.get('ladder_games', 0)} games)  "
              f"archived gain {sg(v.get('archived_gain'))} (n {v.get('archived_n', 0)})")
    if rep["elo"]:
        print("  Elo (lm_ladder):", elo(rep["elo"]))
    if rep["gate0"]["elo"]:
        print("  Elo (gate0):", elo(rep["gate0"]["elo"]))
    for run, c in rep["curve"].items():
        print(f"  curve {run}: " + " ".join(f"{int(k)}:{v:.3f}" for k, v in c.items()))
    dr = rep["dose_response"]
    if dr["decks"]:
        print(f"dose-response  gain per archived list vs Trainer count (seeds {dr['seeds']}): Spearman {sg(dr['spearman'])}")
        for k, v in sorted(dr["decks"].items(), key=lambda kv: -(kv[1]["gain"] or 0)):
            print(f"  {sg(v['gain'])} (n {v['n']:4d}, {v['trainers']} Trainers)  {k}")
    print("health  it >= 80: kind games cut errors steps deck-out | it80-99 / last 20: ev_mc kl_last grad_norm entropy")
    for a, h in rep["health"].items():
        if not h:
            print(f"  {a}: no log rows")
            continue
        print(f"  {a}: it{h['iterations'][0]}-{h['iterations'][1]} ({h['rows']} rows, {h['s_per_iter']} s/iter, lr {h['lr_last']})")
        for k, v in [("all", h["all"])] + list(h["by_kind"].items()):
            if v:
                print(f"    {k:3s} {v['games']:7d} {v['cut']:.4f} {v['errors']:.4f} {v['steps']:6.1f} {sc(v['deck_out'])}")
        for w in ("it80_99", "last20"):
            m = h[w]
            print(f"    {w:7s} " + " ".join(f"{k} {'n/a' if m[k] is None else m[k]}" for k in ("ev_mc", "kl_last", "grad_norm", "entropy")))
    p = rep["pilot_of_record"]
    if p:
        print(f"pilot of record  {p['pilot']}: archived mean over K {sc(p['archived_mean_over_K'])}, "
              f"seed 78 {sc(p['seed78'][0])}, seed 81 (fresh deals) {sc(p['seed81_fresh'][0])}; {p['note']}")
    fr = {k: v for k, v in rep["fresh"].items() if v[1] is not None}
    if fr:
        print("archived SimpleBot @R, seed 78 / 81: " + "  ".join(f"{k} {sc(a)} / {sc(b)}" for k, (a, b) in fr.items()))
    av = {k: v for k, v in rep["archived_vs_pilot_v2"].items() if v}
    if av:
        print("archived vs pilot-v2: " + "  ".join(f"{k} {pool(v)}" for k, v in av.items()))
    it = rep["interim"]
    if any(v is not None for v in it.values()):
        print("interim  " + "  ".join(f"{k} {sc(v) if not isinstance(v, dict) else sg(v['d'])}" for k, v in it.items()))
    rp = rep["random_panel"]
    if rp["simplebot"]:
        print("random panel SimpleBot (report only): "
              + "  ".join(f"{k} {sc(v['win'])} ({v['panel']})" for k, v in rp["simplebot"].items()))
    if any(rp["pairs_mix_vs_len"].values()):
        print("random panel mix vs len: " + "  ".join(f"s{s} {pool(v)}" for s, v in rp["pairs_mix_vs_len"].items()))
    for n in rep["notes"]:
        print("note:", n)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--T", type=int, default=220, help="the arms' iterations: readout snapshots T-41, T-21, T-1")
    ap.add_argument("--dir", default="runs/abl", help="evaluation outputs and arm runs (relative to the repo root)")
    args = ap.parse_args(argv)
    d = Path(args.dir) if Path(args.dir).is_absolute() else ROOT / args.dir
    if not d.is_dir():
        ap.error(f"no directory {d}")
    rep = report(d, args.T)
    (d / "length_mix_report.json").write_text(json.dumps(rep, indent=1))
    show(rep)
    print("wrote", d / "length_mix_report.json")


if __name__ == "__main__":
    main()
