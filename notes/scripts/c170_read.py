"""C170 (runs/probe/C170-table-bodies/record.md, with Amendment 1): do bodies picked by C165's Pokemon table (X: kappa 1, Y: kappa 3) stand up better than uniformly picked ones (G), with the list's own Pokemon (E2) as the ceiling? Scores in event points/3, with
logit differences and a cluster bootstrap over source lists, and the same for decided-win share (full + time wins); loss share beside it. Bands on the lists field at both C127 seeds: R-table-works needs X - G or Y - G at +0.40 and 2 SE on both scales, the same
variant at both seeds; R-table-fails is both under +0.15 at both; a pilot's cells are unreadable if G is under 0.05. C171's gate: kappa chosen on the drafted field alone (kappa 1 on a tie, a tie being under 2 SE apart), which must pass on the lists and at +0.40 and
2 SE with uniform Trainers under s16. Reported: X and Y with each variant's top name left out, top 5 names, effective names, share on the lists' names, colourless attackers' share, the rules-only field, arm 0.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c170_read.py [--check FILE --cell KEY]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np

import c167_read as C
from c139_read import r3

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C170-table-bodies"
C169 = ROOT / "runs/probe/C169-body-split"
C.DECKS.update({"G": C169 / "G.json", "E2": C169 / "E2.json"})
for t in ("X", "Y"):
    for p in ("s16", "s17"):
        C.DECKS[f"{t}_{p}"] = OUT / f"{t}_{p}.json"
for t in ("Gu", "Xu", "Yu"):
    C.DECKS[f"{t}_s16"] = OUT / f"{t}_s16.json"


def cell(deck_key, tag):
    """A cell's file: its own, or C169's where the same games exist."""
    reused = {("G", "L_arm0"): C169 / "G_L_arm0.json", ("E2", "L_arm0"): C169 / "E2_L_arm0.json", ("G", "F_s16"): C169 / "G_F_s16.json", ("G", "R_s16"): C169 / "G_s16.json"}
    return C.read_cell(reused.get((deck_key, tag), OUT / f"{deck_key.split('_')[0]}_{tag}.json"), deck_key)


def scales(c, keep=None):
    """Per-list means of the score and of decided-win share, optionally over the decks in keep."""
    s, w, l, fw = c["score"], (c["win"] == 1.0).astype(float), (c["win"] == 0.0).astype(float), c["full"]
    m = np.ones(len(s), dtype=bool) if keep is None else keep
    src = c["src"]
    return {"score": {x: float(s[m & (src == x)].mean()) for x in sorted(set(src[m].tolist()))}, "won": {x: float(w[m & (src == x)].mean()) for x in sorted(set(src[m].tolist()))}, "full": {x: float(fw[m & (src == x)].mean()) for x in sorted(set(src[m].tolist()))}, "full_mean": float(fw[m].mean()),
            "lost": float(l[m].mean()), "score_mean": float(s[m].mean()), "won_mean": float(w[m].mean())}


def effect(a, b, key, rng, reps=2000):
    """Logit(a) - logit(b) on key, with a bootstrap over the source lists both hold (the deck's own games differ, so this clusters; a deal bootstrap is usually smaller, C167)."""
    lists = sorted(set(a[key]) & set(b[key]))
    va, vb = np.array([a[key][x] for x in lists]), np.array([b[key][x] for x in lists])
    point = float(C.logit(a[f"{key}_mean"]) - C.logit(b[f"{key}_mean"]))
    draws = rng.integers(len(lists), size=(reps, len(lists)))
    boot = C.logit(va[draws].mean(1)) - C.logit(vb[draws].mean(1))
    return {"est": r3(point), "se": r3(float(boot.std(ddof=1))), "lists": len(lists)}


def passes(e, t=0.40):
    return e["est"] >= t and e["est"] >= 2 * e["se"]


def composition(deck_file, coef, list_names, card):
    ds = [d["cards"] for d in json.loads(Path(deck_file).read_text(encoding="utf-8"))]
    c = collections.Counter(card[x]["name"] for d in ds for x in d if card[x]["superType"] == 1)
    total = sum(c.values())
    share = np.array(list(c.values()), dtype=float) / total
    colourless = [sum(not any(v for t, v in enumerate(card[x]["types"]) if t != 0) for x in d if card[x]["superType"] == 1) / max(1, sum(card[x]["superType"] == 1 for x in d)) for d in ds]
    return {"top_5": [[n, r3(k / total)] for n, k in c.most_common(5)], "effective_names": r3(float(1 / (share ** 2).sum())), "share_on_list_names": r3(sum(k for n, k in c.items() if n in list_names) / total),
            "colourless_share": r3(float(np.mean(colourless))), "mean_table_value_a_copy": r3(sum(coef.get(n, 0) * k for n, k in c.items()) / total)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", default="")
    ap.add_argument("--cell", default="")
    a = ap.parse_args()
    if a.check:
        c = C.read_cell(a.check, a.cell)
        print(json.dumps({"cell": a.cell, "games": c["n"], "errors": c["errors"], "score": r3(float(c["score"].mean())), "won": r3(float((c["win"] == 1.0).mean())), "never_source": c["never_source"],
                          "last": {k: c["last"].get(k) for k in ("games", "seconds", "games_per_s")}}))
        sys.exit(0 if c["never_source"] and c["errors"] <= 0.02 * c["n"] else 3)
    from rl.decks import Pool
    card = {x["fullName"]: x for x in Pool().cards}
    tables = json.loads((ROOT / "runs/probe/C165-trainer-factorial/summary.json").read_text(encoding="utf-8"))["pilots"]
    lists = json.loads((ROOT / "runs/probe/C163-draw-deck-field/L.json").read_text(encoding="utf-8"))
    list_names = {card[x]["name"] for d in lists for x in d["cards"] if card[x]["superType"] == 1}
    rng = np.random.default_rng(170)
    out, read = {"pairs": {}}, {}
    pairs = {"s16_lists": ("L_s16", "s16", ("G", "X", "Y", "E2")), "s17_lists": ("L_s17", "s17", ("G", "X", "Y", "E2")), "arm0_lists": ("L_arm0", "s16", ("G", "X", "Y", "E2")),
             "s16_drafted": ("F_s16", "s16", ("G", "X", "Y")), "s17_drafted": ("F_s17", "s17", ("G", "X", "Y")), "s16_rules": ("R_s16", "s16", ("G", "X", "Y"))}
    for pair, (tag, table, cells) in pairs.items():
        cs = {k: cell(f"{k}_{table}" if k in "XY" else k, tag) for k in cells}
        sc = {k: scales(c) for k, c in cs.items()}
        row = {"cells": {k: {"games": cs[k]["n"], "errors": cs[k]["errors"], "score": r3(sc[k]["score_mean"]), "won": r3(sc[k]["won_mean"]), "lost": r3(sc[k]["lost"]), "endings": cs[k]["endings"], "never_source": cs[k]["never_source"],
                             "rate": cs[k]["last"].get("games_per_s")} for k in cells},
               "effects": {f"{k}-G": {"points_logit": effect(sc[k], sc["G"], "score", rng), "won_logit": effect(sc[k], sc["G"], "won", rng)} for k in cells if k != "G"},
               "G_under_0.05": sc["G"]["score_mean"] < 0.05}
        if "E2" in cells:
            row["effects"]["X-E2"] = {"points_logit": effect(sc["X"], sc["E2"], "score", rng)}
            row["effects"]["Y-E2"] = {"points_logit": effect(sc["Y"], sc["E2"], "score", rng)}
        if pair.endswith("lists"):                      # each variant with its top name left out
            for k in ("X", "Y"):
                ds = json.loads(C.DECKS[f"{k}_{table}"].read_text(encoding="utf-8"))
                top = collections.Counter(card[x]["name"] for d in ds for x in d["cards"] if card[x]["superType"] == 1).most_common(1)[0][0]
                holds = np.array([any(card[x]["name"] == top for x in d["cards"]) for d in ds])
                keep = ~holds[cs[k]["deck"]]
                row[f"{k}_without_top"] = {"top_name": top, "decks_left": int((~holds).sum()), "games_left": int(keep.sum()), "thin": int((~holds).sum()) < 24}
                if keep.sum() > 50:
                    row[f"{k}_without_top"]["effect"] = effect(scales(cs[k], keep), sc["G"], "score", rng)
        out["pairs"][pair] = row
        read[pair] = row
    # uniform Trainers on the lists under s16
    us = {k: scales(cell(f"{k}_s16", "L_s16"), None) for k in ("Gu", "Xu", "Yu")}
    out["uniform_trainers_s16"] = {"cells": {k: {"score": r3(v["score_mean"]), "won": r3(v["won_mean"]), "lost": r3(v["lost"])} for k, v in us.items()},
                                   "X-G": effect(us["Xu"], us["Gu"], "score", rng), "Y-G": effect(us["Yu"], us["Gu"], "score", rng)}
    # the band
    seeds = ("s16_lists", "s17_lists")
    unread = [p for p in seeds if read[p]["G_under_0.05"]]
    var_pass = {v: all(passes(read[p]["effects"][f"{v}-G"]["points_logit"]) and passes(read[p]["effects"][f"{v}-G"]["won_logit"]) for p in seeds) for v in "XY"}
    fails = all(read[p]["effects"][f"{v}-G"]["points_logit"]["est"] < 0.15 for p in seeds for v in "XY")
    out["band"] = "unreadable: G under 0.05 at " + ", ".join(unread) if unread else "R-table-works" if any(var_pass.values()) else "R-table-fails" if fails else "between"
    out["variant_passes"] = var_pass
    # C171's kappa, from the drafted field alone
    d = {v: [read[p]["effects"][f"{v}-G"]["points_logit"] for p in ("s16_drafted", "s17_drafted")] for v in "XY"}
    mean = {v: float(np.mean([x["est"] for x in d[v]])) for v in "XY"}
    se = float(np.sqrt(sum(x["se"] ** 2 for v in "XY" for x in d[v])) / 2)
    choice = "Y" if mean["Y"] - mean["X"] >= 2 * se else "X"     # kappa 1 on a tie
    out["C171_gate"] = {"drafted_means": {v: r3(mean[v]) for v in "XY"}, "difference_se": r3(se), "chosen": choice, "kappa": 3 if choice == "Y" else 1, "passes_on_lists": var_pass[choice],
                        "passes_uniform_trainers": passes(out["uniform_trainers_s16"][f"{choice}-G"]), "opens": var_pass[choice] and passes(out["uniform_trainers_s16"][f"{choice}-G"])}
    out["composition"] = {f"{k}_{p}": composition(C.DECKS[f"{k}_{p}"], tables[p]["pokemon"]["all"], list_names, card) for k in "XY" for p in ("s16", "s17")}
    out["composition"]["G"] = composition(C.DECKS["G"], tables["s16"]["pokemon"]["all"], list_names, card)
    out["composition"]["E2"] = composition(C.DECKS["E2"], tables["s16"]["pokemon"]["all"], list_names, card)
    (OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("band", out["band"], out["variant_passes"])
    print("C171 gate", out["C171_gate"])
    print("uniform", out["uniform_trainers_s16"])
    for p, v in out["pairs"].items():
        print(p, {k: (x["score"], x["won"], x["lost"]) for k, x in v["cells"].items()}, "G under 0.05:", v["G_under_0.05"])
        for k, e in v["effects"].items():
            print("  ", k, e)
        for k in ("X_without_top", "Y_without_top"):
            if k in v:
                print("  ", k, v[k])
    print(json.dumps(out["composition"])[:1800])


if __name__ == "__main__":
    main()
