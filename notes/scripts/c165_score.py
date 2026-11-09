"""C165's two follow-up reads (research, #758; CPU, no games): under C127 s16's fit, (1) predicted against observed on C167's cells (A 0.707, R 0.391), split into Trainer, shape and Pokemon parts; (2) each population's
additive Trainer, shape and Pokemon parts, mean and SD over decks, measured from the mean of the 4,000 factorial decks: the lists, C162's rules-only decks, C127 s16 and s17 at 29, scr-round479 at 499 (all, and age 200 or more).
A part is the fit's coefficients on a deck's counts. Special Energy counts as the omitted category, as in the fit. The ridge shrinks the Pokemon part, and these decks may lie outside the sample's range. Writes score_s16.json.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c165_score.py
"""
import json
from pathlib import Path

import numpy as np
import torch

import c165_read as R
from c139_read import r3

ROOT = R.ROOT
OUT = R.OUT


def main():
    from rl.decks import Pool
    card = {c["fullName"]: c for c in Pool().cards}
    ds = R.load_design()
    _, a, b, y, _, _ = R.games(OUT / R.PILOTS["s16"])
    f = R.Fit(ds, a, b, y)
    lam, _ = f.choose_lambda()
    w = f.solve(f.pods, lam)
    k = len(ds["tn"])
    beta, sh, po = w[1:1 + k], w[1 + k:1 + k + 4], w[1 + k + 4:]
    ti, pi = {n: x for x, n in enumerate(ds["tn"])}, {n: x for x, n in enumerate(ds["pn"])}
    outside = {}

    def parts(cards):
        t, m = np.zeros(k), np.zeros(len(ds["pn"]))
        for x in cards:
            c = card[x]
            if c["superType"] == 2:
                t[ti[c["name"]]] += 1
            elif c["superType"] == 1:
                if c["name"] in pi:
                    m[pi[c["name"]]] += 1
                else:
                    outside[c["name"]] = outside.get(c["name"], 0) + 1
        P, Tn = sum(card[x]["superType"] == 1 for x in cards) - f.p0, t.sum() - f.t0
        return float(beta @ t), float(sh @ np.array([P, P ** 2, Tn ** 2, P * Tn])), float(po @ m)

    # the zero: the 4,000 factorial decks
    P, Tn = ds["P"] - f.p0, ds["Tn"] - f.t0
    zero = np.array([float((ds["T"] @ beta).mean()), float((np.stack([P, P ** 2, Tn ** 2, P * Tn], 1) @ sh).mean()), float((ds["M"] @ po).mean())])

    def group(decks):
        rows = np.array([parts(d) for d in decks]) - zero
        total = rows.sum(1)
        return {"decks": len(decks), "trainer": {"mean": r3(float(rows[:, 0].mean())), "sd": r3(float(rows[:, 0].std()))}, "shape": {"mean": r3(float(rows[:, 1].mean())), "sd": r3(float(rows[:, 1].std()))},
                "pokemon": {"mean": r3(float(rows[:, 2].mean())), "sd": r3(float(rows[:, 2].std()))}, "total": {"mean": r3(float(total.mean())), "sd": r3(float(total.std()))}}

    c163 = ROOT / "runs/probe/C163-draw-deck-field"
    load = lambda p: [d["cards"] for d in json.loads(Path(p).read_text(encoding="utf-8"))]
    snap = lambda run, it: torch.load(ROOT / "runs/screens" / run / f"population_it{it:04d}.pt", map_location="cpu", weights_only=False)["population"]
    old = snap("scr-round479", 499)
    groups = {"lists": load(c163 / "L.json"), "lists_draw_free": load(c163 / "L_base.json"), "C162_rules_only": load(c163 / "R.json"), "C162_draw_free": load(c163 / "R_base.json"),
              "factorial_4000_sample": [x for x in load(OUT / "decks.json")[:400]], "C127_s16_at_29": [x["deck"] for x in snap("C127-R1-K-paired-ledger-s16", 29)],
              "C127_s17_at_29": [x["deck"] for x in snap("C127-R1-K-paired-ledger-s17", 29)], "scr_round479_at_499": [x["deck"] for x in old],
              "scr_round479_at_499_age_200_plus": [x["deck"] for x in old if 500 - x["born"] >= 200]}
    out = {"pilot": "C127 s16", "lambda": lam, "populations": {n: group(d) for n, d in groups.items()}}
    pred = R.predicted(ds, w, (f.p0, f.t0))
    out["item_7"] = {"A_on_rules_field": pred["LR"], "R_on_rules_field": pred["RR"], "observed": {"A": 0.707, "R": 0.391, "gap": 0.316}, "predicted_gap": pred["predicted_gap"], "gap_parts": pred["gap_parts"]}
    out["pokemon_names_outside_sample"] = outside
    (OUT / "score_s16.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out["item_7"]))
    for n, v in out["populations"].items():
        print(n, v)
    print("names outside the fit", outside)


if __name__ == "__main__":
    main()
