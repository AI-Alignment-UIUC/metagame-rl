"""C154 (runs/probe/C154-value-signal/record.md, with Amendment 1): is the pilot's value a lower-noise signal for a deck change than the
outcome? Per paired slot (a deck and its copy against the same opponent, seed and seat): y, the outcome difference in event points/3
(c145_read.per_deal), and v_t, the focus seat's value difference at the start of its own turn t = 2, 3, 4 (the engine's end reward where
the game ended first; notes/scripts/audit/c154_worker.js). Both signed so that positive means the draw cards beat the Energy: arm D (C145's
cell D) copy-with-draw - deck, arm L (C146's cell B design) list - draw->Energy copy. Readouts: SNR = mean / sd over the slots with a
bootstrap 95% CI, per arm and t; arm D's per-deck correlation of mean v_3 with mean y; arm L's mean v_3 with its CI and the per-list
Spearman correlation of mean v_3 with the per-list price; the bands on t = 3 (R-value-biased from arm L only when its v_3 CI isn't above 0 or its Spearman is under
+0.1; a bias failure and R-no-gain are both reported). Writes summary.json.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c154_read.py
"""
import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

from c145_read import per_deal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C154-value-signal"
ARMS = {"D": ("oakbill", -1), "L": ("draw", 1)}


def slots(arm):
    g, sign = ARMS[arm]
    r, y = per_deal(OUT / f"{arm}_s91.json", g, sign)
    vals = {}
    for l in open(OUT / f"{arm}_s91.values.jsonl", encoding="utf-8"):
        x = json.loads(l)
        vals[(x["i"], x["j"], x["seed"])] = {t: x["v"].get(str(t), x["end"]) for t in (2, 3, 4)}
    rows, missing = [], 0
    for m in r["meta"]:
        c = m["copies"][g]
        for (key, s), yy in y.items():
            if key != m["key"]:
                continue
            a, b = vals.get((m["list"], m["opp"], s)), vals.get((c, m["opp"], s))
            if a is None or b is None:
                missing += 1
                continue
            # sign: +1 (L) list - copy; -1 (D) copy - deck, as y
            rows.append({"deck": m["list"], "y": yy, **{f"v{t}": sign * (a[t] - b[t]) for t in (2, 3, 4)}})
    return r, rows, missing


def snr(xs, reps=2000):
    xs = np.asarray(xs, dtype=np.float64)
    rng = random.Random(154)
    n = len(xs)
    f = lambda v: float(v.mean() / v.std(ddof=1)) if v.std(ddof=1) > 0 else 0.0
    bs = sorted(f(xs[[rng.randrange(n) for _ in range(n)]]) for _ in range(reps))
    return {"mean": round(float(xs.mean()), 5), "sd": round(float(xs.std(ddof=1)), 5), "snr": round(f(xs), 4),
            "snr_ci": [round(bs[int(0.025 * reps)], 4), round(bs[int(0.975 * reps)], 4)]}


def mean_ci(xs, reps=2000):
    xs = np.asarray(xs, dtype=np.float64)
    rng = random.Random(155)
    n = len(xs)
    bs = sorted(float(xs[[rng.randrange(n) for _ in range(n)]].mean()) for _ in range(reps))
    return {"mean": round(float(xs.mean()), 5), "ci": [round(bs[int(0.025 * reps)], 5), round(bs[int(0.975 * reps)], 5)]}


def ranks(x):
    o = np.argsort(x)
    r = np.empty(len(x))
    r[o] = np.arange(len(x))
    return r


def main():
    out = {}
    per = {}
    for arm in ("D", "L"):
        if not (OUT / f"{arm}_s91.values.jsonl").exists():
            continue
        r, rows, missing = slots(arm)
        per[arm] = rows
        out[arm] = {"slots": len(rows), "unpaired": missing, "y": snr([x["y"] for x in rows]),
                    **{f"v{t}": snr([x[f"v{t}"] for x in rows]) for t in (2, 3, 4)}}
        by = defaultdict(list)
        for x in rows:
            by[x["deck"]].append(x)
        my = np.array([np.mean([x["y"] for x in v]) for v in by.values()])
        mv = np.array([np.mean([x["v3"] for x in v]) for v in by.values()])
        out[arm]["decks"] = len(by)
        out[arm]["corr_v3_y_pearson"] = round(float(np.corrcoef(mv, my)[0, 1]), 4)
        out[arm]["corr_v3_y_spearman"] = round(float(np.corrcoef(ranks(mv), ranks(my))[0, 1]), 4)
        if arm == "L":
            out[arm]["v3_mean_ci"] = mean_ci([x["v3"] for x in rows])
    if "D" in out:
        d = out["D"]
        sy, sv = d["y"]["snr"], d["v3"]["snr"]
        ratio = abs(sv) / abs(sy) if sy else float("inf")
        same = np.sign(sv) == np.sign(sy)
        L = out.get("L")
        l_signal = bool(L) and L["v3_mean_ci"]["ci"][0] > 0 and L["corr_v3_y_spearman"] >= 0.3
        l_biased = (not L) or L["v3_mean_ci"]["ci"][0] <= 0 or L["corr_v3_y_spearman"] < 0.1
        out["read"] = {"snr_ratio_v3_y": round(ratio, 3), "same_sign": bool(same), "corr_D": d["corr_v3_y_pearson"],
                       "L_signal": bool(l_signal), "L_biased": bool(l_biased)}
        if ratio >= 3 and same and d["corr_v3_y_pearson"] >= 0.3 and l_signal:
            out["band"] = "R-value-signal"
        else:                                        # research (16:5x): a bias failure and R-no-gain are both reported
            labels = (["R-value-biased"] if (ratio >= 3 and not same) or d["corr_v3_y_pearson"] < 0.1 or l_biased else []) +                      (["R-no-gain"] if ratio < 1.5 else [])
            out["band"] = " + ".join(labels) if labels else "between"
    (OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
