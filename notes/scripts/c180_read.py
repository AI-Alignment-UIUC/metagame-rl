"""C180 with its Amendment 1 (runs/probe/C180-dose-by-practice/record.md): d14 - list on event points/3 under other pilots, on C179's decks, deals and seed. Stage 0: the replication, arm 0 s2 on C179's draws and arm 0 s1 on fresh draws, each at +0.03 or under, or stage 1 doesn't run; and C175's E2 factorial under arm 0, mean beta over the 42, R-set at -0.008 or under, R-skill at -0.004 or over, between otherwise, beside C49-sd's -0.0121. Stage 1, per pilot: R-practice, a human-free pilot's gain at +0.03 or under, and at least +0.04 and 2 SE below C49-sd's, paired by list; R-not, +0.06 or more; between otherwise. Beside it: win share, full wins and losses, endings, and gains on arm 0's 4 bench lists against the 20 held out, a thin read.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c180_read.py
"""
import json

import numpy as np

import c175_read as E
import c179_read as C
from c139_read import r3

D = C.ROOT / "runs/probe/C180-dose-by-practice"
BENCH = (1, 2, 3, 21)                                  # the lists in runs/probe/BENCH/bench_matchups.json, by index in L.json
REPLICATION = ("arm0s2", "arm0s1_fresh")


def paired(a, b, reps=4000):
    k = sorted(set(a) & set(b))
    d = np.array([a[q] - b[q] for q in k])
    rng = np.random.default_rng(180)
    return float(d.mean()), float(np.std([d[rng.integers(len(d), size=len(d))].mean() for _ in range(reps)]))


def factorial():
    f = D / "E2_arm0.json"
    if not f.exists():
        return None
    R = E.R
    R.OUT = E.D / "E2"
    ds = R.load_design()
    r = json.loads(f.read_text(encoding="utf-8"))
    a, b, y, err = E.arrays(r["results"])
    fit = R.Fit(ds, a, b, y)
    lam, _ = fit.choose_lambda()
    w = fit.solve(fit.pods, lam)
    tn = ds["tn"]
    target = R.lists_mean_copies(tn)
    groups = {"all_42": list(tn), "lists_top_12": [tn[i] for i in np.argsort(-target)[:12]], "T4": [n for n in R.T4 if n in tn], "draw": [n for n in R.DRAW if n in tn]}
    out = {"games": len(y), "errors": err, "lambda": lam, "pods": len(fit.pods), "mean_points": r3(float(y.mean() + 0.5)), "endings": r["last"]["endings"], "rho_L": r3(R.spearman(fit.beta(w), target)), "groups": {}}
    for g, names in groups.items():
        ix = [tn.index(n) for n in names]
        fn = lambda v, ix=ix: float(np.mean(fit.beta(v)[ix]))
        out["groups"][g] = {"mean": r3(fn(w)), "se": r3(float(fit.jackknife(lam, fn)))}
    m = out["groups"]["all_42"]["mean"]
    out["band"] = "R-set" if m <= -0.008 else "R-skill" if m >= -0.004 else "between"
    c49 = json.loads((E.D / "summary.json").read_text(encoding="utf-8"))["cells"]["E2"]["groups"]
    out["c49_sd"] = c49
    return out


def main():
    copies = json.loads((C.D / "decks.json").read_text(encoding="utf-8"))
    fresh = json.loads((D / "decks_fresh.json").read_text(encoding="utf-8")) if (D / "decks_fresh.json").exists() else None
    base = C.read(C.D / "G_C49.json", copies)["arms"]["d14"]["by_list"]
    arm1 = C.read(C.D / "G_arm0.json", copies)["arms"]["d14"]["by_list"]
    out = {"reference": {"C49": r3(float(np.mean(list(base.values())))), "arm0_s1": r3(float(np.mean(list(arm1.values()))))}, "pilots": {}}
    for f in sorted(D.glob("G_*.json")):
        name = f.stem[2:]
        v = C.read(f, fresh if name.endswith("_fresh") else copies)
        x = v["arms"]["d14"]
        by = x["by_list"]
        b, h = [by[str(k)] for k in BENCH if str(k) in by], [q for k, q in by.items() if int(k) not in BENCH]
        d, se = paired(by, base)
        row = {"pilot": v["pilot"], "games": v["games"], "errors": v["errors"], "games_per_s": v["games_per_s"], "endings": v["endings"], "list_side": v["list_side"], **{q: x[q] for q in ("change", "se_lists", "win", "full_win", "full_loss", "pts")},
               "minus_C49": r3(d), "se_minus_C49": r3(se), "bench_4": r3(float(np.mean(b))) if b else None, "held_out_20": r3(float(np.mean(h))) if h else None, "above_0": sum(q > 0 for q in by.values()), "by_list": by}
        if name not in REPLICATION:
            row["band"] = "R-practice" if x["change"] <= 0.03 and d <= -0.04 and d <= -2 * se else "R-not" if x["change"] >= 0.06 else "between"
        out["pilots"][name] = row
    if all(n in out["pilots"] for n in REPLICATION):
        out["replication_holds"] = all(out["pilots"][n]["change"] <= 0.03 for n in REPLICATION)
    out["factorial_E2_arm0"] = factorial()
    (D / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out["reference"]), "replication_holds", out.get("replication_holds"))
    for k, v in out["pilots"].items():
        print(k, {q: v[q] for q in v if q != "by_list"})
    print("factorial", json.dumps(out["factorial_E2_arm0"]))


if __name__ == "__main__":
    main()
