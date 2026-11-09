"""C187 (runs/probe/C187-head-off/record.md): H0, W's recipe with the head frozen, against W (C171), seeds 48 and 49. Bands on Trainers proposed a candidate over iterations 35-44: R-head, at or above -0.2 at both seeds; R-not-head, within 0.2 of W's at both; between otherwise. Beside it: median Trainers and G1 against W, survivors by high and low table, accepted - proposed, the head's mass in and out against the deck's copies, and whether the head stayed frozen (0 against the last saved population).
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c187_read.py [--it 44]
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c187_read.py --mass       (research's #905: out share / copy share and the head's own Trainer mass, H0, DN, ND, WR, by stage)
"""
import argparse
import json

import numpy as np
import torch

import c182_read as C
from c139_read import r3
from c184_read import head_mass, rows, window

ROOT = C.ROOT
D = ROOT / "runs/probe/C187-head-off"


def frozen(run, it):
    a, b = (torch.load(run / f"population_it{i:04d}.pt", map_location="cpu", weights_only=False)["drafter"]["head"] for i in (0, it))
    return all(torch.equal(a[k], b[k]) for k in a)


def side(name, stages, it, hi, lo, top):
    run = ROOT / "runs/screens" / name
    st = C.stage(stages, name, it) if stages.exists() else None
    out = {"proposed_35_44": window(run, 35, 44), "accepted_35_44": window(run, 35, 44, "acc"), "proposed_0_9": window(run, 0, 9), "head_mass_last_5": head_mass(run, it - 4, it)}
    if st:
        out.update({"median": st["median_pte"], "population": st["population"]["pte"], "G1_mean5": st["G1_mean5"], "T4": st["population"]["T4"], "survivors": st["survivors"], "errors": st["errors"], "games": st["games"], "ledger": C.ledger(run, it, top)})
        if st.get("survivors"):
            out["high_low"] = C.survivors(run, it, hi, lo)
    return out


def mass_stages(run):
    """By stage, from head_mass in log.jsonl: Trainers' share of the out-choice over their share of copies, and the head's own incoming Trainer mass."""
    r, out = rows(run), {}
    for a, b in ((0, 14), (15, 29), (30, 44)):
        x = [r[i]["head_mass"] for i in range(a, b + 1) if i in r and r[i].get("head_mass")]
        if x:
            out[f"{a}-{b}"] = {"iters": len(x), "out_over_copies": r3(float(np.mean([v["out"][1] / v["copies"][1] for v in x]))), "own_T": r3(float(np.mean([v["own"][1] for v in x])))}
    return out


def mass_table():
    """H0, DN, ND and WR at each stage, research's #905. W logged no head_mass: its row is the sampled caps read, 16 decks a saved iteration."""
    out = {}
    for n in ("C188-W0-s48", "C188-W0-s49", "C188-W0S-s48", "C188-W0S-s49", "C188-WK-s48", "C188-WK-s49", "C187-H0-s48", "C187-H0-s49", "C184-DN-s50", "C184-DN-s51", "C184-ND-s48", "C184-ND-s49", "C184-WR-s50", "C184-WR-s51"):
        out[n] = mass_stages(ROOT / "runs/screens" / n)
    for s in (48, 49):
        f = D / f"caps/C171-W-s{s}.json"
        if f.exists():
            c = json.loads(f.read_text(encoding="utf-8"))
            out[f"W-s{s} (sampled)"] = {f"{a}-{b}": {"iters": len(x), "out_over_copies": r3(float(np.mean([v["own"]["T_out"] / (v["T"] / 60) for v in x]))), "own_T": r3(float(np.mean([v["own"]["T_in_legal"] for v in x])))} for a, b in ((0, 14), (15, 29), (30, 44)) for x in [[v for v in c if a <= v["it"] <= b]]}
    (D / "mass_stages.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--it", type=int, default=44)
    ap.add_argument("--mass", action="store_true", help="the out ratio and the head's own Trainer mass by stage")
    a = ap.parse_args()
    if a.mass:
        return mass_table()
    hi, lo, top = C.groups()
    out = {"iter": a.it}
    t = {}
    for s in (48, 49):
        h = side(f"C187-H0-s{s}", D / "stages.jsonl", a.it, hi, lo, top)
        w = side(f"C171-W-s{s}", C.W_STAGES, a.it, hi, lo, top)
        run = ROOT / f"runs/screens/C187-H0-s{s}"
        if (run / f"population_it{a.it:04d}.pt").exists():
            h["head_frozen"] = frozen(run, a.it)
        out[f"s{s}"] = {"H0": h, "W": w}
        if h["proposed_35_44"] and w["proposed_35_44"] and h["proposed_35_44"]["iters"] == 10:
            t[s] = (h["proposed_35_44"]["pte"][1], w["proposed_35_44"]["pte"][1])
    if len(t) == 2:
        out["T_proposed_H0_W"] = t
        out["band"] = "R-head" if all(x >= -0.2 for x, _ in t.values()) else "R-not-head" if all(abs(x - y) <= 0.2 for x, y in t.values()) else "between"
    (D / f"read_{a.it}.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, default=float))


if __name__ == "__main__":
    main()
