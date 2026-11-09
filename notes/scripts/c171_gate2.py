"""C171's Amendment 3 (runs/probe/C171-table-drafting/record.md), evaluation only, all under the start pilot C49-sd, plain tables only. --decks builds X (kappa 1) from each seed's plain table, and X and Y with uniform Trainers. --kappa reads X and Y on the drafted field (C127 s16's population at 29 for
seed 48, s17's for seed 49: the loop's human-free decks; the seeds' own W runs have none yet); a tie, the means under 2 SE apart, goes to kappa 1. --read reads the whole C170 gate at that kappa: points and decided wins on the lists at both seeds, the uniform-Trainers cell at both seeds, top names, share on the
lists' names, top-name-out. Reports only; research reads it before chosen.json is written.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c171_gate2.py --decks | --kappa | --read
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes/scripts"))
import c163_decks as K                # noqa: E402
import c167_read as C                 # noqa: E402
import c170_read as V                 # noqa: E402
import c171_gate as A                 # noqa: E402
from c139_read import r3              # noqa: E402

D = ROOT / "runs/probe/C171-table-drafting"
G = D / "gate"
SEEDS = (48, 49)


def pool_card():
    from rl.decks import Pool
    pool = Pool()
    return pool, {c["fullName"]: c for c in pool.cards}


def decks():
    pool, card = pool_card()
    lists = json.loads((ROOT / "runs/probe/C163-draw-deck-field/L.json").read_text(encoding="utf-8"))
    K.table_bodies(pool, card, lists, tables={f"s{s}": A.load("plain", s) for s in SEEDS}, kappas=(("X", 1.0),), where=G, seed=1711)
    rng = np.random.default_rng(1712)
    by = collections.defaultdict(list)
    for c in pool.cards:
        if pool.allowed[c["id"]] and c["superType"] == 2 and c["name"] not in K.DRAW:
            by[c["name"]].append(c["fullName"])
    names = sorted(by)
    for tag, src in [(f"{v}u_s{s}", G / f"{v}_s{s}.json") for v in "XY" for s in SEEDS] + [("Gu", V.C169 / "G.json")]:
        out = []
        for d in json.loads(src.read_text(encoding="utf-8")):
            keep = [x for x in d["cards"] if card[x]["superType"] != 2]
            used, new = collections.Counter(), []
            while len(new) < 60 - len(keep):
                m = names[int(rng.integers(len(names)))]
                if used[m] < 4:
                    used[m] += 1
                    new.append(by[m][int(rng.integers(len(by[m])))])
            assert pool.legal(pool.vector(keep + new))
            out.append({"name": d["name"] + "u", "src": d["src"], "cards": keep + new})
        (G / f"{tag}.json").write_text(json.dumps(out), encoding="utf-8")
    print("X and uniform-Trainer decks written")


def cell(key, deck_file, out_file):
    C.DECKS[key] = deck_file
    return C.read_cell(out_file, key)


def kappa():
    rng = np.random.default_rng(171)
    res, d = {}, {"X": [], "Y": []}
    for s in SEEDS:
        sg = V.scales(cell("G", V.C169 / "G.json", G / f"G_F{s}_C49.json"))
        res[f"G_F{s}"] = {"score": r3(sg["score_mean"]), "won": r3(sg["won_mean"])}
        for v in "XY":
            sv = V.scales(cell(f"{v}_s{s}", G / f"{v}_s{s}.json", G / f"{v}_s{s}_F_C49.json"))
            e = V.effect(sv, sg, "score", rng)
            res[f"{v}_s{s}_F"] = {"score": r3(sv["score_mean"]), "won": r3(sv["won_mean"]), "minus_G": e}
            d[v].append(e)
    mean = {v: float(np.mean([x["est"] for x in d[v]])) for v in "XY"}
    se = float(np.sqrt(sum(x["se"] ** 2 for v in "XY" for x in d[v])) / 2)
    choice = "Y" if mean["Y"] - mean["X"] >= 2 * se else "X"
    out = {"drafted_field": res, "means": {v: r3(mean[v]) for v in "XY"}, "difference_se": r3(se), "chosen": choice, "kappa": 3 if choice == "Y" else 1, "tie_goes_to_kappa_1": True}
    (G / "kappa.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out))
    return out


def read():
    rng = np.random.default_rng(1713)
    pool, card = pool_card()
    k = json.loads((G / "kappa.json").read_text(encoding="utf-8"))
    v = k["chosen"]
    lists = json.loads((ROOT / "runs/probe/C163-draw-deck-field/L.json").read_text(encoding="utf-8"))
    list_names = {card[x]["name"] for d in lists for x in d["cards"] if card[x]["superType"] == 1}
    sg = V.scales(cell("G", V.C169 / "G.json", G / "G_C49.json"))
    su = V.scales(cell("Gu", G / "Gu.json", G / "Gu_L_C49.json"))
    res = {"kappa": k["kappa"], "variant": v, "G": {"score": r3(sg["score_mean"]), "won": r3(sg["won_mean"]), "lost": r3(sg["lost"])}, "Gu": {"score": r3(su["score_mean"]), "won": r3(su["won_mean"]), "lost": r3(su["lost"])}, "seeds": {}}
    ok = True
    for s in SEEDS:
        key, f = f"{v}_s{s}", G / f"{v}_s{s}.json"
        c = cell(key, f, G / (f"{v}_s{s}_C49.json"))
        sv = V.scales(c)
        p, w = V.effect(sv, sg, "score", rng), V.effect(sv, sg, "won", rng)
        cu = cell(f"{v}u_s{s}", G / f"{v}u_s{s}.json", G / f"{v}u_s{s}_L_C49.json")
        suv = V.scales(cu)
        pu = V.effect(suv, su, "score", rng)
        ds = json.loads(f.read_text(encoding="utf-8"))
        top = collections.Counter(card[x]["name"] for d in ds for x in d["cards"] if card[x]["superType"] == 1).most_common(1)[0][0]
        holds = np.array([any(card[x]["name"] == top for x in d["cards"]) for d in ds])
        keep = ~holds[c["deck"]]
        out_top = {"top_name": top, "decks_left": int((~holds).sum()), "games_left": int(keep.sum()), "thin": int((~holds).sum()) < 24}
        if keep.sum() > 50:
            out_top["effect"] = V.effect(V.scales(c, keep), sg, "score", rng)
        passes = V.passes(p) and V.passes(w) and V.passes(pu)
        ok &= passes
        res["seeds"][str(s)] = {"score": r3(sv["score_mean"]), "won": r3(sv["won_mean"]), "lost": r3(sv["lost"]), "games": c["n"], "errors": c["errors"], "points_logit": p, "won_logit": w, "uniform_trainers": {"score": r3(suv["score_mean"]), "minus_Gu": pu},
                                "top_name_out": out_top, "composition": V.composition(f, A.load("plain", s), list_names, card), "passes": passes}
    res["passes"] = ok
    if (G / "E2_C49.json").exists():                     # research's addition: the lists' own Pokemon under the same pilot, beside the gate, not part of it
        se = V.scales(cell("E2", V.C169 / "E2.json", G / "E2_C49.json"))
        res["E2"] = {"score": r3(se["score_mean"]), "won": r3(se["won_mean"]), "lost": r3(se["lost"]), "minus_G": V.effect(se, sg, "score", rng)}
        for s in SEEDS:
            sv = V.scales(cell(f"{v}_s{s}", G / f"{v}_s{s}.json", G / f"{v}_s{s}_C49.json"))
            res["seeds"][str(s)]["minus_E2"] = {"points_logit": V.effect(sv, se, "score", rng), "won_logit": V.effect(sv, se, "won", rng), "full_wins_logit": V.effect(sv, se, "full", rng), "full_wins": {"variant": r3(sv["full_mean"]), "E2": r3(se["full_mean"])}}
    (G / "gate_full.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decks", action="store_true")
    ap.add_argument("--kappa", action="store_true")
    ap.add_argument("--read", action="store_true")
    a = ap.parse_args()
    if a.decks:
        decks()
    if a.kappa:
        kappa()
    if a.read:
        read()


if __name__ == "__main__":
    main()
