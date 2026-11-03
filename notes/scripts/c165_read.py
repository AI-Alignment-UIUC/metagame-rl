"""C165 (runs/probe/C165-trainer-factorial/record.md): the per-copy value of every Trainer from the factorial games. For a game between decks A (deck i) and B, y is A's
event points/3 minus 0.5, on an intercept, the 42 Trainers' count differences (beta, unpenalised), the shape differences (P, P^2, T^2, PT, centred on the sample's means) and
the Pokemon name count differences (ridge, lambda by leave-one-pod-out). T's linear term is the sum of the Trainers' counts, so it's absorbed in beta, and basic Energy is the
omitted category: beta is a copy of a Trainer against a basic Energy at the mean shape. SEs by jackknife over pods. Reads per pilot: r_sh (odd against even pods), rho_L
(Spearman with the lists' mean copies, permutation p), the shape optimum (grid over the sampled range, jackknife CI, games with both decks at P 8-24), the logistic fit's rho_L,
the Trainers above +2 SE, group means, adjusted score by Energy bin; A7 (the lists' Trainer copies held by the table's top 7, with a permutation 95th percentile); the calibrations
(arm 0 against C163 RR, C127 s16 against C145 D); arm 0's predicted base scores against C163's, split into Trainer, shape and Pokemon parts; the bands and C166's gates
(Amendment 1). --synth checks the fit recovers planted values (a non-zero mean beta) on the real schedule and projects the SE. --pilot-read reads the timed pilot's residual SD.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c165_read.py [--synth] [--pilot-read FILE]
"""
import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from c139_read import pts, r3
from c165_run import OUT, POD, PODS, ROOT, schedule

sys.path.insert(0, str(ROOT))
PILOTS = {"s16": "games_s16.json", "s17": "games_s17.json", "K1m": "games_K1m.json", "arm0": "games_arm0.json"}
PRIMARY, REFS = ("s16", "s17"), ("K1m", "arm0")
GRID = (1, 3, 10, 30, 100, 300, 1000, 3000, 10000)
DRAW, T4 = ("Professor Oak", "Bill", "Gambler"), ("PlusPower", "Gust of Wind", "Item Finder", "Scoop Up")


def load_design():
    from rl.decks import Pool
    card = {c["fullName"]: c for c in Pool().cards}
    decks = json.loads((OUT / "decks.json").read_text(encoding="utf-8"))
    tn = sorted({card[x]["name"] for d in decks for x in d["cards"] if card[x]["superType"] == 2})
    pn = sorted({card[x]["name"] for d in decks for x in d["cards"] if card[x]["superType"] == 1})
    ti, pi = {n: k for k, n in enumerate(tn)}, {n: k for k, n in enumerate(pn)}
    T, M = np.zeros((len(decks), len(tn))), np.zeros((len(decks), len(pn)))
    for k, d in enumerate(decks):
        for x in d["cards"]:
            c = card[x]
            if c["superType"] == 2:
                T[k, ti[c["name"]]] += 1
            elif c["superType"] == 1:
                M[k, pi[c["name"]]] += 1
    return {"tn": tn, "pn": pn, "T": T, "M": M, "P": M.sum(1), "Tn": T.sum(1)}


def features(ds, a, b, p0, t0):
    """Per-game rows: intercept, the 42 Trainer differences, 4 shape differences, the Pokemon name differences (penalised, last)."""
    P, Tn = ds["P"] - p0, ds["Tn"] - t0
    shape = np.stack([P, P ** 2, Tn ** 2, P * Tn], 1)
    return np.hstack([np.ones((len(a), 1)), ds["T"][a] - ds["T"][b], shape[a] - shape[b], ds["M"][a] - ds["M"][b]])


class Fit:
    """Normal equations per pod, so the jackknife and the odd-even fits just add them up."""

    def __init__(self, ds, a, b, y, keep=None):
        self.ds = ds
        self.p0, self.t0 = float(ds["P"].mean()), float(ds["Tn"].mean())
        pod = a // POD
        self.pods = sorted(set(pod.tolist()))
        k = len(ds["tn"])
        self.n_free = 1 + k + 4
        self.A, self.b, self.yy, self.n = {}, {}, {}, {}
        for p in self.pods:
            m = pod == p
            if keep is not None:
                m = m & keep
            X = features(ds, a[m], b[m], self.p0, self.t0)
            self.A[p], self.b[p] = X.T @ X, X.T @ y[m]
            self.yy[p], self.n[p] = float(y[m] @ y[m]), int(m.sum())
        self.dim = X.shape[1]

    def solve(self, pods, lam):
        A = sum(self.A[p] for p in pods)
        b = sum(self.b[p] for p in pods)
        D = np.zeros(self.dim)
        D[self.n_free:] = lam
        return np.linalg.solve(A + np.diag(D) + 1e-9 * np.eye(self.dim), b)

    def choose_lambda(self):
        best, score = None, np.inf
        for lam in GRID:
            sse = 0.0
            for p in self.pods:
                w = self.solve([q for q in self.pods if q != p], lam)
                sse += self.yy[p] - 2 * w @ self.b[p] + w @ self.A[p] @ w
            if sse < score:
                best, score = lam, sse
        return best, score / sum(self.n.values())

    def beta(self, w):
        return w[1:1 + len(self.ds["tn"])]

    def residual_sd(self, w):
        A, b = sum(self.A.values()), sum(self.b.values())
        yy, n = sum(self.yy.values()), sum(self.n.values())
        return float(((yy - 2 * w @ b + w @ A @ w) / n) ** 0.5)

    def jackknife(self, lam, fn):
        vals = np.array([fn(self.solve([q for q in self.pods if q != p], lam)) for p in self.pods])
        n = len(self.pods)
        return float(((n - 1) / n * ((vals - vals.mean(0)) ** 2).sum()) ** 0.5) if vals.ndim == 1 else ((n - 1) / n * ((vals - vals.mean(0)) ** 2).sum(0)) ** 0.5


def ranks(x):
    """Average ranks (the lists' copies tie a lot)."""
    x = np.asarray(x, dtype=float)
    o = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    r[o] = np.arange(len(x), dtype=float)
    for v in np.unique(x):
        m = x == v
        r[m] = r[m].mean()
    return r


def spearman(x, y):
    return float(np.corrcoef(ranks(x), ranks(y))[0, 1])


def perm_p(beta, target, reps=10000, seed=165):
    rng = np.random.default_rng(seed)
    rb, rt = ranks(beta), ranks(target)
    obs = float(np.corrcoef(rb, rt)[0, 1])
    rb0, rt0 = rb - rb.mean(), rt - rt.mean()
    den = float((rb0 @ rb0 * (rt0 @ rt0)) ** 0.5)
    hits = sum(float(rng.permutation(rb0) @ rt0) / den >= obs for _ in range(reps))
    return obs, (hits + 1) / (reps + 1)


def lists_mean_copies(tn):
    from rl.decks import Pool
    card = {c["fullName"]: c for c in Pool().cards}
    out = subprocess.run(["node", "-e", "const {archivedDecks}=require('./env/decks.js');console.log(JSON.stringify(archivedDecks()))"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    lists = json.loads(out.stdout)
    c = Counter(card[x]["name"] for d in lists for x in d["cards"] if card[x]["superType"] == 2)
    return np.array([c.get(n, 0) / len(lists) for n in tn], dtype=float)


def lists_mean_name_copies(pn):
    from rl.decks import Pool
    card = {c["fullName"]: c for c in Pool().cards}
    lists = json.loads((ROOT / "runs/probe/C163-draw-deck-field/L.json").read_text(encoding="utf-8"))
    c = Counter(card[x]["name"] for d in lists for x in d["cards"] if card[x]["superType"] == 1)
    return np.array([c.get(n, 0) / len(lists) for n in pn], dtype=float)


def a7(beta, target, reps=10000, seed=165):
    """The share of the lists' Trainer copies held by the table's top 7 cards, and that share's 95th percentile over random sets of 7."""
    rng = np.random.default_rng(seed)
    total = float(target.sum())
    obs = float(target[np.argsort(-beta)[:7]].sum()) / total
    null = [float(target[rng.choice(len(target), 7, replace=False)].sum()) / total for _ in range(reps)]
    return obs, float(np.percentile(null, 95))


def predicted(ds, w, base_shape):
    """Arm 0's predicted scores of L and R bases against the two fields, from the fit, against C163's LR, RR and RL, split into Trainer, shape and Pokemon parts.
    The lists may lie outside the sample's range, and the ridge shrinks the Pokemon part."""
    from rl.decks import Pool
    card = {c["fullName"]: c for c in Pool().cards}
    k = len(ds["tn"])
    ti, pi = {n: x for x, n in enumerate(ds["tn"])}, {n: x for x, n in enumerate(ds["pn"])}
    c163 = ROOT / "runs/probe/C163-draw-deck-field"
    missing = Counter()

    def parts(name):
        T, M, shape = [], [], []
        for d in json.loads((c163 / f"{name}.json").read_text(encoding="utf-8")):
            t, m = np.zeros(k), np.zeros(len(ds["pn"]))
            for x in d["cards"]:
                c = card[x]
                if c["superType"] == 2:
                    t[ti[c["name"]]] += 1
                elif c["superType"] == 1:
                    if c["name"] in pi:
                        m[pi[c["name"]]] += 1
                    else:
                        missing[c["name"]] += 1
            T.append(t)
            M.append(m)
            P, Tn = sum(card[x]["superType"] == 1 for x in d["cards"]) - base_shape[0], t.sum() - base_shape[1]
            shape.append([P, P ** 2, Tn ** 2, P * Tn])
        return np.mean(T, 0), np.mean(M, 0), np.mean(shape, 0)
    S = {n: parts(n) for n in ("L_base", "R_base", "L", "R")}
    b, sh, po = w[1:1 + k], w[1 + k:1 + k + 4], w[1 + k + 4:]

    def score(a, f):
        tr, shape, pok = float(b @ (S[a][0] - S[f][0])), float(sh @ (S[a][2] - S[f][2])), float(po @ (S[a][1] - S[f][1]))
        return {"predicted": r3(0.5 + float(w[0]) + tr + shape + pok), "trainer": r3(tr), "shape": r3(shape), "pokemon": r3(pok)}
    out = {"LR": score("L_base", "R"), "RR": score("R_base", "R"), "RL": score("R_base", "L"), "observed": {"LR": 0.722, "RR": 0.385, "RL": 0.070}, "observed_gap": 0.336}
    out["predicted_gap"] = r3(out["LR"]["predicted"] - out["RR"]["predicted"])
    out["gap_parts"] = {x: r3(out["LR"][x] - out["RR"][x]) for x in ("trainer", "shape", "pokemon")}
    out["deep_round_on_no_signal"] = out["predicted_gap"] < 0.17
    out["pokemon_names_outside_sample"] = dict(missing)
    return out


def optimum(w, ds, p0, t0, k):
    """The fitted quadratic's best shape over the sampled range (P 8-24; T's 1st to 99th percentile), with T's slope the mean beta, as (P*, T*, E*)."""
    b = w[1:1 + k]
    a_p, q_pp, q_tt, q_pt = w[1 + k:1 + k + 4]
    tlo, thi = np.percentile(ds["Tn"], [1, 99])
    Pg, Tg = np.meshgrid(np.arange(8, 24.01, 0.25), np.arange(tlo, thi + 0.01, 0.25), indexing="ij")
    pp, tt = Pg - p0, Tg - t0
    f = a_p * pp + float(b.mean()) * tt + q_pp * pp ** 2 + q_tt * tt ** 2 + q_pt * pp * tt
    i, j = np.unravel_index(int(np.argmax(f)), f.shape)
    return np.array([Pg[i, j], Tg[i, j], 60 - Pg[i, j] - Tg[i, j]])


def logistic(ds, a, b, w, p0, t0, lam, iters=12):
    X = features(ds, a, b, p0, t0)
    k = 1 + len(ds["tn"]) + 4
    D = np.zeros(X.shape[1])
    D[k:] = lam
    th = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(X @ th, -30, 30)))
        s = np.maximum(p * (1 - p), 1e-6)
        H = (X * s[:, None]).T @ X + np.diag(D) + 1e-9 * np.eye(X.shape[1])
        th = th + np.linalg.solve(H, X.T @ (w - p) - D * th)
    return th[1:1 + len(ds["tn"])]


def games(path):
    r = json.loads(Path(path).read_text(encoding="utf-8"))
    ok = [x for x in r["results"] if not x.get("error")]
    a = np.array([x["i"] for x in ok])
    b = np.array([x["j"] for x in ok])
    assert (a // POD == b // POD).all(), "a game across pods"
    y = np.array([pts(x)[0] - 0.5 for x in ok])
    win = np.array([pts(x)[1] for x in ok])
    return r, a, b, y, win, len(r["results"]) - len(ok)


def full_schedule(rounds, pods=PODS):
    a, b = [], []
    for pod in range(pods):
        for i, j in schedule(pod, rounds):
            a.append(i + pod * POD)
            b.append(j + pod * POD)
    return np.array(a), np.array(b)


def synth(ds, sd_game, sd_deck, reps=5, seed=165, pods=PODS):
    """Plant known values on the real 10-round schedule, with deck-level noise; do the fit and its jackknife recover them, and what SE does the design give?"""
    a, b = full_schedule(10, pods)
    rng = np.random.default_rng(seed)
    k = len(ds["tn"])
    p0, t0 = float(ds["P"].mean()), float(ds["Tn"].mean())
    X = features(ds, a, b, p0, t0)
    out = []
    for _ in range(reps):
        w = np.r_[-0.12, rng.normal(0.005, 0.02, k), 0.002, -0.0005, -0.0005, 0.0002, rng.normal(0, 0.01, X.shape[1] - k - 5)]
        u = rng.normal(0, sd_deck, ds["T"].shape[0])
        y = X @ w + u[a] - u[b] + rng.normal(0, sd_game, len(a))
        f = Fit(ds, a, b, y)
        lam, _ = f.choose_lambda()
        pods = f.pods
        est = f.beta(f.solve(pods, lam))
        se = f.jackknife(lam, f.beta)
        z = (est - w[1:1 + k]) / se
        out.append({"lambda": lam, "within_2se": int((np.abs(z) <= 2).sum()), "of": k, "se_mean": float(se.mean()), "se_max": float(se.max()),
                    "corr": float(np.corrcoef(est, w[1:1 + k])[0, 1]), "rmse": float(((est - w[1:1 + k]) ** 2).mean() ** 0.5)})
    return out


def read(ds, name, target):
    r, a, b, y, win, err = games(OUT / PILOTS[name])
    f = Fit(ds, a, b, y)
    lam, cv = f.choose_lambda()
    pods = f.pods
    w = f.solve(pods, lam)
    beta, se = f.beta(w), f.jackknife(lam, f.beta)
    odd, even = [p for p in pods if p % 2], [p for p in pods if p % 2 == 0]
    r_sh = spearman(f.beta(f.solve(odd, lam)), f.beta(f.solve(even, lam)))
    rho, p = perm_p(beta, target)
    keep = (ds["P"][a] >= 8) & (ds["P"][a] <= 24) & (ds["P"][b] >= 8) & (ds["P"][b] <= 24)
    fs = Fit(ds, a, b, y, keep)
    k = len(ds["tn"])
    opt = optimum(fs.solve(pods, lam), ds, fs.p0, fs.t0, k)
    opts = np.array([optimum(fs.solve([q for q in pods if q != x], lam), ds, fs.p0, fs.t0, k) for x in pods])
    n = len(pods)
    opt_se = ((n - 1) / n * ((opts - opts.mean(0)) ** 2).sum(0)) ** 0.5
    lb = logistic(ds, a, b, win, f.p0, f.t0, lam)
    rho_log = spearman(lb, target)
    tn = ds["tn"]
    ix = {n_: i for i, n_ in enumerate(tn)}
    group = lambda names: (float(np.mean([beta[ix[x]] for x in names])),
                           f.jackknife(lam, lambda v: float(np.mean([f.beta(v)[ix[x]] for x in names]))))
    d, t4 = group(DRAW), group(T4)
    calib = (2 * beta[ix["Professor Oak"]] + 2 * beta[ix["Bill"]],
             f.jackknife(lam, lambda v: float(2 * f.beta(v)[ix["Professor Oak"]] + 2 * f.beta(v)[ix["Bill"]])))
    above = [tn[i] for i in range(k) if beta[i] >= 2 * se[i]]
    share7, share7_p95 = a7(beta, target)
    # Reported, no band (the ridge shrinks these, so read the order rather than the size): the Pokemon names' coefficients against the lists' mean copies of each name
    theta = w[1 + k + 4:]
    list_mons = lists_mean_name_copies(ds["pn"])
    held = list_mons > 0
    pokemon = {"rho_L": r3(spearman(theta, list_mons)), "mean_rank_of_list_names": r3(float(ranks(theta)[held].mean())), "names": len(theta), "list_names": int(held.sum()),
               "mean_coef_list_names": r3(float(theta[held].mean())), "mean_coef_other_names": r3(float(theta[~held].mean())),
               "top": [{"name": ds["pn"][i], "coef": r3(float(theta[i])), "lists_copies": r3(float(list_mons[i]))} for i in np.argsort(-theta)[:15]],
               "bottom": [{"name": ds["pn"][i], "coef": r3(float(theta[i])), "lists_copies": r3(float(list_mons[i]))} for i in np.argsort(theta)[:5]],
               "all": {ds["pn"][i]: r3(float(theta[i])) for i in np.argsort(-theta)}}
    # the score by Energy bin, net of the Trainers' identities and the Pokemon names, keeping the shape effects
    X = features(ds, a, b, f.p0, f.t0)
    m = w.copy()
    m[1:1 + k] -= float(beta.mean())
    m[1 + k:1 + k + 4] = 0
    adj = y - X @ m
    E = 60 - ds["P"] - ds["Tn"]
    bins = {}
    for lo in range(8, 36, 4):
        s = (E[a] >= lo) & (E[a] < lo + 4)
        if s.sum() >= 50:
            bins[f"{lo}-{lo + 3}"] = {"games": int(s.sum()), "adjusted": r3(float(adj[s].mean()))}
    table = sorted(({"trainer": tn[i], "beta": r3(float(beta[i])), "se": r3(float(se[i])), "lists_copies": r3(float(target[i])), "beta_logit": r3(float(lb[i]))} for i in range(k)),
                   key=lambda t: -t["beta"])
    for q, t in enumerate(table):
        t["rank"] = q + 1
    return {"pilot": r["pilot"], "games": len(y), "errors": err, "error_rate": r3(err / max(1, len(r["results"]))), "games_per_s": r["last"]["games_per_s"], "endings": r["last"]["endings"],
            "lambda": lam, "cv_mse": r3(cv), "residual_sd": r3(f.residual_sd(w)), "intercept": r3(float(w[0])), "r_sh": r3(r_sh), "rho_L": r3(rho), "rho_p": r3(p), "rho_L_logit": r3(rho_log),
            "logit_flag": abs(rho - rho_log) > 0.15, "beta_se_mean": r3(float(se.mean())), "beta_se_max": r3(float(se.max())),
            "shape_optimum": {"P": r3(float(opt[0])), "T": r3(float(opt[1])), "E": r3(float(opt[2])), "se": [r3(float(x)) for x in opt_se],
                              "E_ci": [r3(float(opt[2] - 2 * opt_se[2])), r3(float(opt[2] + 2 * opt_se[2]))]},
            "draw_mean": [r3(d[0]), r3(d[1])], "t4_mean": [r3(t4[0]), r3(t4[1])], "oak2_bill2": [r3(float(calib[0])), r3(float(calib[1]))],
            "above_2se": above, "above_2se_copies_at_4": 4 * len(above), "A7": r3(share7), "A7_p95": r3(share7_p95), "by_energy_bin": bins, "table": table, "pokemon": pokemon,
            "predicted": predicted(ds, w, (f.p0, f.t0)) if name == "arm0" else None}, (rho, p, r_sh)


def band(res):
    p1, p2 = res[PRIMARY[0]], res[PRIMARY[1]]
    if p1["r_sh"] < 0.5 or p2["r_sh"] < 0.5:
        return "R-noise"
    if all(res[x]["rho_L"] >= 0.40 and res[x]["rho_p"] <= 0.01 and res[x]["A7"] > res[x]["A7_p95"] for x in PRIMARY):
        return "R-signal"
    if all(res[x]["rho_L"] < 0.20 for x in PRIMARY):
        clear = any(x in res and res[x]["rho_L"] >= 0.40 and res[x]["rho_p"] <= 0.01 for x in REFS)
        return "R-pilot-gap" if clear else "R-no-signal"
    return "between"


def shape_band(res):
    o = [res[x]["shape_optimum"] for x in PRIMARY]
    if all(x["E"] <= 21 and x["E_ci"][1] <= 23 for x in o):
        return "S-lists"
    if all(x["E"] >= 23 and x["E_ci"][0] >= 21 for x in o):
        return "S-energy"
    return "S-between"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth", action="store_true")
    ap.add_argument("--sd-game", type=float, default=0.40, help="--synth: a game's residual SD, net of the deck-level noise")
    ap.add_argument("--sd-deck", type=float, default=0.15, help="--synth: the record's assumed between-deck SD")
    ap.add_argument("--pilot-read", default="")
    a = ap.parse_args()
    ds = load_design()
    if a.synth:
        out = synth(ds, a.sd_game, a.sd_deck)
        print(json.dumps({"sd_game": a.sd_game, "sd_deck": a.sd_deck, "reps": out}, indent=1))
        ok = all(x["within_2se"] >= 37 for x in out)
        print("synthetic acceptance (at least 37 of 42 within 2 SE, each draw):", "PASS" if ok else "FAIL")
        sys.exit(0 if ok else 3)
    if a.pilot_read:
        r, x, z, y, _, err = games(a.pilot_read)
        f = Fit(ds, x, z, y)
        lam, _ = f.choose_lambda()
        w = f.solve(f.pods, lam)
        print(json.dumps({"games": len(y), "errors": err, "games_per_s": r["last"]["games_per_s"], "endings": r["last"]["endings"], "lambda": lam, "y_sd": r3(float(y.std())),
                          "residual_sd": r3(f.residual_sd(w)), "mean_points": r3(float(y.mean() + 0.5))}, indent=1))
        return
    target = lists_mean_copies(ds["tn"])
    res = {}
    for name in PILOTS:
        if (OUT / PILOTS[name]).exists():
            res[name], _ = read(ds, name, target)
    out = {"band": band(res) if all(x in res for x in PRIMARY) else None, "shape_band": shape_band(res) if all(x in res for x in PRIMARY) else None, "pilots": res}
    if "arm0" in res:
        c, s = res["arm0"]["oak2_bill2"]
        out["calibration"] = {"oak2_bill2": c, "se": s, "C163_RR": 0.027, "flag": c < 0 or abs(c - 0.027) > 0.02}
    if "s16" in res:
        c, s = res["s16"]["oak2_bill2"]
        out["calibration_s16"] = {"oak2_bill2": c, "se": s, "C145_D": 0.028, "flag": abs(c - 0.028) > 0.03}
    if all(x in res for x in PRIMARY) and "calibration" in out:
        out["C166_gates"] = {"five_above_2se_at_both": all(len(res[x]["above_2se"]) >= 5 for x in PRIMARY), "not_S_energy": out["shape_band"] != "S-energy",
                             "calibrations_pass": not out["calibration"]["flag"] and not out["calibration_s16"]["flag"],
                             "still_needed": "the paired spot check of the top 3 and bottom 3; a design reaching the required share, handling immigration"}
    (OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "pilots"}))
    for n, v in res.items():
        print(n, {k: v[k] for k in ("games", "errors", "games_per_s", "lambda", "residual_sd", "r_sh", "rho_L", "rho_p", "rho_L_logit", "logit_flag", "A7", "A7_p95", "beta_se_mean", "beta_se_max", "shape_optimum",
                                     "draw_mean", "t4_mean", "oak2_bill2", "above_2se_copies_at_4", "predicted")})


if __name__ == "__main__":
    main()
