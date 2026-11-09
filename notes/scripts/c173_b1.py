"""C173's stage B1 (runs/probe/C173-search-table/record.md, Amendments 2 and 3): what are the Trainers worth under search? C49-sd on concentrated rules-only decks at seed 48 (C171's table-s48 decks), up to 12 pods at 1,000 games: greedy (C171's own games on those pods, the same decks, pairs and deals), full width (C135's set: every legal move at Trainer-playable decisions; the primary if it runs at a usable SE) and C139's set. The fit is C165's, one lambda, chosen on greedy.
Primary: mean beta over the 42 Trainers, search - greedy, paired by pod (jackknife), read against greedy's mean gap as well. R-trainers-rise: +0.003 or more and 2 SE. R-trainers-flat: under +0.0015, and its SE excludes +0.003; a mean under +0.0015 whose SE can't exclude +0.003 reads unresolved. Between otherwise. A rise only under C139's set reads no claim. A claim needs seed 49. Stop-after-the-first: clear beyond +0.003 on the pods' degrees of freedom.
Beside it, no band: the lists' top 12 Trainers' mean, T4 and draw means, rho_L, the shape optimum, adjusted score by Energy bin. The rival check: the same fit, greedy, under W s48's own net at 54 and 29, on pods 0-5. R-spiral: mean beta at or below -0.0078 - 2 SE. R-no-spiral: at or above -0.0065. Between otherwise.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c173_b1.py --synth [--sd-game 0.32]
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c173_b1.py --read
Amendment 4 (--seed 49, its games in B1-s49, the greedy games table-s49's on the same deals): the lists' top 12 by mean copies, fixed below before any seed 49 game. R-list-cards-rise: their rise at +0.002 and 2 SE, and at least +0.002 and 2 SE above the other 30's rise, paired by pod. R-no: their rise under +0.001. Between otherwise. Required too (the tightening): the Spearman of per-card rise against the lists' copies over all 42 at +0.25 or more, permutation p at most 0.05. T4, PlusPower, rho_L, all 42 against the gap, partial correlations given greedy beta and given C161's underplay, the t interval, and the Trainers clearing Energy by 2 SE beside it. On seed 48 the same read is post hoc and no claim.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

import c165_read as R
import c165_run as F
from c139_read import pts, r3

ROOT = R.ROOT
D = ROOT / "runs/probe/C173-search-table/B1"
TABLE = ROOT / "runs/probe/C171-table-drafting/table-s48"
F.SEED = 48
R.schedule = F.schedule
R.OUT = TABLE
GAP = -0.0078
A4_TOP12 = ("Professor Oak", "PlusPower", "Computer Search", "Gust of Wind", "Bill", "Item Finder", "Energy Removal", "Super Energy Removal", "Scoop Up", "Rocket's Sneak Attack", "Energy Retrieval", "Nightly Garbage Run")
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201}


def arrays(res):
    ok = [x for x in res if not x.get("error")]
    a = np.array([x["i"] for x in ok])
    b = np.array([x["j"] for x in ok])
    assert (a // R.POD == b // R.POD).all(), "a game across pods"
    y = np.array([pts(x)[0] - 0.5 for x in ok])
    return a, b, y, len(res) - len(ok)


def load(pattern):
    res = []
    for f in sorted(D.glob(pattern)):
        res += json.loads(f.read_text(encoding="utf-8"))["results"]
    return res


def jack(fit_s, fit_g, lam, fn):
    pods = sorted(set(fit_s.pods) & set(fit_g.pods))
    vals = np.array([fn(fit_s.beta(fit_s.solve([q for q in pods if q != p], lam))) - fn(fit_g.beta(fit_g.solve([q for q in pods if q != p], lam))) for p in pods])
    n = len(pods)
    return float(((n - 1) / n * ((vals - vals.mean()) ** 2).sum()) ** 0.5)


def beside(ds, f, x, b_, y, lam):
    """Shape optimum and adjusted score by Energy bin."""
    k = len(ds["tn"])
    keep = (ds["P"][x] >= 8) & (ds["P"][x] <= 24) & (ds["P"][b_] >= 8) & (ds["P"][b_] <= 24)
    fp = R.Fit(ds, x, b_, y, keep)
    opt = R.optimum(fp.solve(fp.pods, lam), ds, fp.p0, fp.t0, k)
    opts = np.array([R.optimum(fp.solve([q for q in fp.pods if q != p], lam), ds, fp.p0, fp.t0, k) for p in fp.pods])
    n = len(fp.pods)
    se_opt = ((n - 1) / n * ((opts - opts.mean(0)) ** 2).sum(0)) ** 0.5
    tlo, thi = np.percentile(ds["Tn"], [1, 99])
    w_ = f.solve(f.pods, lam)
    X = R.features(ds, x, b_, f.p0, f.t0)
    mm = w_.copy()
    mm[1:1 + k] -= float(f.beta(w_).mean())
    mm[1 + k:1 + k + 4] = 0
    adj = y - X @ mm
    E = 60 - ds["P"] - ds["Tn"]
    bins = {}
    for lo in range(8, 36, 4):
        q = (E[x] >= lo) & (E[x] < lo + 4)
        if q.sum() >= 50:
            bins[f"{lo}-{lo + 3}"] = {"games": int(q.sum()), "adjusted": r3(float(adj[q].mean()))}
    return {"shape_optimum": {"P": r3(float(opt[0])), "T": r3(float(opt[1])), "E": r3(float(opt[2])), "se": [r3(float(v)) for v in se_opt], "T_range_sampled": [r3(float(tlo)), r3(float(thi))]}, "by_energy_bin": bins}


def partial(x, y, z, reps=2000, seed=173):
    """Rank partial correlation of x and y given z, with a one-sided p from permuting x's residual."""
    rx, ry, rz = R.ranks(x), R.ranks(y), R.ranks(z)
    res = lambda v: v - np.polyval(np.polyfit(rz, v, 1), rz)
    ex, ey = res(rx), res(ry)
    obs = float(np.corrcoef(ex, ey)[0, 1])
    rng = np.random.default_rng(seed)
    hits = sum(float(np.corrcoef(rng.permutation(ex), ey)[0, 1]) >= obs for _ in range(reps))
    return obs, (hits + 1) / (reps + 1)


def underplay():
    """C161's search-minus-greedy play rate per Trainer, for the cards it covers."""
    s_ = json.loads((ROOT / "runs/probe/C161-search-disagreement/summary.json").read_text(encoding="utf-8"))
    return {x["trainer"].replace("Poke Ball", "Poké Ball"): x["search_plays"] - x["greedy_plays"] for x in s_["trainers"]}


def amendment4(fs, fg, bs, bg, tn, lam, target, df):
    """Amendment 4 and its tightening: the fixed top 12's rise, its rise above the other 30's paired by pod, and the Spearman of per-card rise against the lists' copies over all 42 (required). Beside it: partial correlations, the t interval, and the Trainers clearing Energy."""
    ix = [tn.index(n) for n in A4_TOP12]
    jx = [i for i in range(len(tn)) if i not in ix]
    top = lambda b: float(np.mean(b[ix]))
    con = lambda b: float(np.mean(b[ix]) - np.mean(b[jx]))
    d, se = top(bs) - top(bg), jack(fs, fg, lam, top)
    dc, sec = con(bs) - con(bg), jack(fs, fg, lam, con)
    rise = bs - bg
    rho, p = R.perm_p(rise, target)
    group = d >= 0.002 and d >= 2 * se and dc >= 0.002 and dc >= 2 * sec
    conj = rho >= 0.25 and p <= 0.05
    band = "R-list-cards-rise" if group and conj else "R-no" if d < 0.001 else "between"
    t = T975.get(df, 2.0)
    up = underplay()
    cov = [i for i, n in enumerate(tn) if n in up]
    u = np.array([up[tn[i]] for i in cov])
    pg, pg_p = partial(rise, target, bg)
    pu, pu_p = partial(rise[cov], target[cov], u)
    clear = {}
    for arm, f, b in (("greedy", fg, bg), ("search", fs, bs)):
        sd = f.jackknife(lam, f.beta)
        n2, nt = int((b - 2 * sd > 0).sum()), int((b - t * sd > 0).sum())
        clear[arm] = {"cards_by_2se": n2, "copies_at_4": 4 * n2, "cards_by_t": nt, "against_lists_trainers": 28}
    return {"post_hoc": F.SEED == 48, "top_12_rise": r3(d), "se": r3(se), "t_interval": [r3(d - t * se), r3(d + t * se)], "above_other_30": r3(dc), "se_above": r3(sec), "t_interval_above": [r3(dc - t * sec), r3(dc + t * sec)],
            "rise_vs_lists_spearman": r3(rho), "perm_p": r3(p), "group_passes": bool(group), "spearman_passes": bool(conj), "band": band,
            "partial": {"given_greedy_beta": {"rho": r3(pg), "p": r3(pg_p)}, "given_underplay": {"cards": len(cov), "rho_same_cards": r3(R.spearman(rise[cov], target[cov])), "rho": r3(pu), "p": r3(pu_p)}}, "clear_energy": clear}


def arm_read(ds, tn, target, groups, res, g_all, name):
    done = sorted({x["i"] // R.POD for x in res})
    g = [x for x in g_all if x["i"] // R.POD in done]
    keys = {(x["i"], x["j"], x["seed"], x["iSeat"]) for x in g}
    same = sum((x["i"], x["j"], x["seed"], x["iSeat"]) in keys for x in res)
    ga, gb, gy, ge = arrays(g)
    sa, sb, sy, se = arrays(res)
    fg, fs = R.Fit(ds, ga, gb, gy), R.Fit(ds, sa, sb, sy)
    lam, _ = fg.choose_lambda()
    wg, ws = fg.solve(fg.pods, lam), fs.solve(fs.pods, lam)
    bg, bs = fg.beta(wg), fs.beta(ws)
    out = {"arm": name, "pods": done, "df": len(done) - 1, "games": {"greedy": len(ga), "search": len(sa)}, "errors": {"greedy": ge, "search": se}, "lambda": lam, "residual_sd": {"greedy": r3(fg.residual_sd(wg)), "search": r3(fs.residual_sd(ws))},
           "mean_points": {"greedy": r3(float(gy.mean() + 0.5)), "search": r3(float(sy.mean() + 0.5))}, "rho_L": {"greedy": r3(R.spearman(bg, target)), "search": r3(R.spearman(bs, target))}, "groups": {}}
    for gname, names in groups.items():
        ix = [tn.index(n) for n in names]
        fn = lambda b: float(np.mean(b[ix]))
        out["groups"][gname] = {"greedy": r3(fn(bg)), "search": r3(fn(bs)), "search_minus_greedy": r3(fn(bs) - fn(bg)), "se_paired": r3(jack(fs, fg, lam, fn)), "se_search": r3(float(fs.jackknife(lam, lambda v: fn(fs.beta(v)))))}
    m = out["groups"]["all_42"]
    d, se_d = m["search_minus_greedy"], m["se_paired"]
    t = T975.get(out["df"], 2.0)
    out["band"] = ("R-trainers-rise" if d >= 0.003 and d >= 2 * se_d else ("R-trainers-flat" if d + 2 * se_d < 0.003 else "unresolved: its SE can't exclude +0.003") if d < 0.0015 else "between")
    out["clear_beyond_0.003"] = {"t": t, "low": r3(d - t * se_d), "clear": d - t * se_d > 0.003}
    out["against_the_gap"] = {"greedy_mean_here": m["greedy"], "gap_used": GAP, "share_of_gap_closed": r3(d / -GAP)}
    out["same_deals"] = {"matched": same, "of": len(res)}
    out["amendment_4"] = amendment4(fs, fg, bs, bg, tn, lam, target, out["df"])
    out["table"] = sorted(({"trainer": tn[i], "greedy": r3(float(bg[i])), "search": r3(float(bs[i])), "lists_copies": r3(float(target[i]))} for i in range(len(tn))), key=lambda t_: -t_["search"])
    out["beside"] = {"greedy": beside(ds, fg, ga, gb, gy, lam), "search": beside(ds, fs, sa, sb, sy, lam)}
    return out


def dose(ds, pattern):
    """Research's #806: searched decisions per game for each deck, against its Trainer count, per stage file: the bins and the slope."""
    out = {}
    for f in sorted(D.glob(pattern)):
        d = Path(str(f) + ".dose.jsonl")
        if not d.exists():
            continue
        r = json.loads(f.read_text(encoding="utf-8"))["results"]
        side = {}
        for x in r:
            if not x.get("error"):
                side[x["seed"]] = (x["i"], x["j"]) if x["iSeat"] == 1 else (x["j"], x["i"])
        count = {}
        for line in open(d, encoding="utf-8"):
            sd, p = json.loads(line)
            if sd in side:
                count[(sd, p)] = count.get((sd, p), 0) + 1
        xs, ys = [], []
        for sd, (seat1, seat2) in side.items():
            for p, deck in ((1, seat1), (2, seat2)):
                xs.append(ds["Tn"][deck])
                ys.append(count.get((sd, p), 0))
        xs, ys = np.array(xs), np.array(ys, dtype=float)
        bins = {}
        for lo, hi in ((0, 19), (20, 23), (24, 27), (28, 31), (32, 60)):
            q = (xs >= lo) & (xs <= hi)
            if q.sum() >= 20:
                bins[f"{lo}-{hi}"] = {"deck_games": int(q.sum()), "searched_per_game": r3(float(ys[q].mean()))}
        out[f.stem] = {"deck_games": len(xs), "searched_per_game": r3(float(ys.mean())), "slope_per_trainer": r3(float(np.polyfit(xs, ys, 1)[0])), "corr": r3(float(np.corrcoef(xs, ys)[0, 1])), "bins": bins}
    return out


def rival(ds, tn, f):
    res = json.loads(f.read_text(encoding="utf-8"))
    a, b, y, err = arrays(res["results"])
    fit = R.Fit(ds, a, b, y)
    lam, _ = fit.choose_lambda()
    fn = lambda v: float(fit.beta(v).mean())
    m, se = fn(fit.solve(fit.pods, lam)), float(fit.jackknife(lam, fn))
    band = "R-spiral" if m <= GAP - 2 * se else "R-no-spiral" if m >= -0.0065 else "between"
    return {"pilot": res["pilot"], "games": len(y), "errors": err, "pods": len(fit.pods), "lambda": lam, "mean_beta": r3(m), "se": r3(se), "band": band, "line_spiral": r3(GAP - 2 * se), "rate": res["last"]["games_per_s"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth", action="store_true")
    ap.add_argument("--pods", type=int, default=6)
    ap.add_argument("--sd-game", type=float, default=0.32)
    ap.add_argument("--sd-deck", type=float, default=0.15)
    ap.add_argument("--read", action="store_true")
    ap.add_argument("--seed", type=int, default=48)
    ap.add_argument("--drop", default="", help="research's with-and-without read: a JSON list of deal seeds to leave out of both arms; writes summary_without.json")
    a = ap.parse_args()
    global D, TABLE
    if a.seed != 48:
        F.SEED = a.seed
        TABLE = ROOT / f"runs/probe/C171-table-drafting/table-s{a.seed}"
        D = ROOT / f"runs/probe/C173-search-table/B1-s{a.seed}"
        R.OUT = TABLE
    ds = R.load_design()
    if a.synth:
        out = R.synth(ds, a.sd_game, a.sd_deck, pods=a.pods)
        print(json.dumps({"schedule": f"{a.pods} pods at 1,000 games", "sd_game": a.sd_game, "sd_deck": a.sd_deck, "reps": out}, indent=1))
        ok = all(x["within_2se"] >= 37 for x in out)
        print("planted-value acceptance (at least 37 of 42 within 2 SE, each draw):", "PASS" if ok else "FAIL")
        sys.exit(0 if ok else 3)
    drop = set(json.loads(Path(a.drop).read_text(encoding="utf-8"))) if a.drop else set()
    g_all = [x for x in json.loads((TABLE / "games.json").read_text(encoding="utf-8"))["results"] if x["seed"] not in drop]
    tn = ds["tn"]
    target = R.lists_mean_copies(tn)
    groups = {"all_42": list(tn), "lists_top_12": [tn[i] for i in np.argsort(-target)[:12]], "T4": list(R.T4), "draw": list(R.DRAW), "PlusPower": ["PlusPower"]}
    assert set(groups["lists_top_12"]) == set(A4_TOP12), "Amendment 4's fixed group changed"
    groups["other_30"] = [n for n in tn if n not in A4_TOP12]
    out = {"arms": {}, "rival": {}}
    for arm, pattern in (("full_width", "full_p*.json"), ("c139", "c139_p*.json")):
        res = [x for x in load(pattern) if x["seed"] not in drop]
        if res:
            out["arms"][arm] = arm_read(ds, tn, target, groups, res, g_all, arm)
            out["arms"][arm]["dose"] = dose(ds, pattern)
    for tag in ("54", "29"):
        f = D / f"rival_{tag}.json"
        if f.exists():
            out["rival"][tag] = rival(ds, tn, f)
    a_ = out["arms"]
    fw, c1 = a_.get("full_width"), a_.get("c139")
    if fw and c1:
        rise_f, rise_c = fw["band"] == "R-trainers-rise", c1["band"] == "R-trainers-rise"
        out["read"] = "R-trainers-rise under both sets" if rise_f and rise_c else "a rise only under C139's set: no claim" if rise_c else f"full width {fw['band']}; C139's set {c1['band']}"
    out["dropped_deals"] = len(drop)
    (D / ("summary_without.json" if drop else "summary.json")).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("read", out.get("read"))
    # a flat full width stands on its own, with C139's set held (#804, #806)
    for arm, v in a_.items():
        print(arm, {k: v[k] for k in ("pods", "games", "errors", "same_deals", "residual_sd", "mean_points", "rho_L", "band", "clear_beyond_0.003", "against_the_gap", "amendment_4")})
        for g_, x in v["groups"].items():
            print("  ", g_, x)
        print("   shape", {k: v["beside"][k]["shape_optimum"] for k in ("greedy", "search")})
        print("   top 8 under search", [(t["trainer"], t["search"], t["greedy"]) for t in v["table"][:8]])
        print("   dose", v["dose"])
    print("rival", out["rival"])


if __name__ == "__main__":
    main()
