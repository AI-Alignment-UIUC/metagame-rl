"""C171's table choice and gate (runs/probe/C171-table-drafting/record.md, Amendment 1 items 2-3, and research's #770). Spearman(plain, concentrated) per seed against the concentrated pair's own Spearman across seeds. Plain is used if it's at least 0.8 at both seeds, or at
least 0.65 at both and within 0.05 of that across-seed value; otherwise B holds, and it goes to Evan as a ruling. --decks builds a Y cell (kappa 3, seed 171) from each chosen table, and --read reads Y - G on the lists under the start pilot at C170's bar: +0.40 logit and 2 SE, on
points and on decided wins, at each seed. Writes chosen.json only on a pass.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c171_gate.py --choose [--decks] [--read]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes/scripts"))
import c165_read as R                 # noqa: E402
import c163_decks as K                # noqa: E402
import c167_read as C                 # noqa: E402
import c170_read as V                 # noqa: E402
from c139_read import r3              # noqa: E402

D = ROOT / "runs/probe/C171-table-drafting"
SEEDS = (48, 49)


def load(kind, s):
    return json.loads((D / (f"table-s{s}" if kind == "conc" else f"table-plain-s{s}") / "table.json").read_text(encoding="utf-8"))


def spear(a, b):
    both = sorted(set(a) & set(b))
    return R.spearman([a[n] for n in both], [b[n] for n in both])


def choose():
    conc = {s: load("conc", s) for s in SEEDS}
    plain = {s: load("plain", s) for s in SEEDS}
    within = {s: spear(plain[s], conc[s]) for s in SEEDS}
    across = spear(conc[48], conc[49])
    across_plain = spear(plain[48], plain[49])
    by_08 = all(v >= 0.8 for v in within.values())
    by_near = all(v >= 0.65 for v in within.values()) and all(abs(v - across) <= 0.05 or v >= across for v in within.values())
    out = {"plain_vs_conc": {str(s): r3(v) for s, v in within.items()}, "conc_across_seeds": r3(across), "plain_across_seeds": r3(across_plain), "use_plain_by_0.8": by_08, "use_plain_by_within_0.05": by_near,
           "choice": "plain" if by_08 or by_near else "hold: goes to Evan as a ruling", "fits": {f"{k}{s}": json.loads((D / (f"table-s{s}" if k == "conc" else f"table-plain-s{s}") / "fit.json").read_text(encoding="utf-8")) for k in ("conc", "plain") for s in SEEDS}}
    (D / "table_choice.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "fits"}))
    for k, f in out["fits"].items():
        print(k, {x: f[x] for x in ("games", "errors", "lambda", "residual_sd", "r_sh_pokemon", "r_sh_trainers", "spearman_with_s16_table")}, f["top"][:8])
    return out


def decks():
    from rl.decks import Pool
    pool = Pool()
    card = {c["fullName"]: c for c in pool.cards}
    lists = json.loads((ROOT / "runs/probe/C163-draw-deck-field/L.json").read_text(encoding="utf-8"))
    g = D / "gate"
    g.mkdir(exist_ok=True)
    K.table_bodies(pool, card, lists, tables={**{f"s{s}": load("plain", s) for s in SEEDS}, **{f"cs{s}": load("conc", s) for s in SEEDS}}, kappas=(("Y", 3.0),), where=g, seed=171)


def read():
    g = D / "gate"
    rng = np.random.default_rng(171)
    C.DECKS.update({"G": V.C169 / "G.json", **{f"Y_{t}": g / f"Y_{t}.json" for t in ("s48", "s49", "cs48", "cs49")}})
    gc = C.read_cell(g / "G_C49.json", "G")
    sg = V.scales(gc)
    res = {"G": {"score": r3(sg["score_mean"]), "won": r3(sg["won_mean"]), "lost": r3(sg["lost"]), "games": gc["n"], "errors": gc["errors"]}}
    for t in ("s48", "s49", "cs48", "cs49"):
        yc = C.read_cell(g / f"Y_{t}_C49.json", f"Y_{t}")
        sy = V.scales(yc)
        p, w = V.effect(sy, sg, "score", rng), V.effect(sy, sg, "won", rng)
        res[f"Y_{t}"] = {"score": r3(sy["score_mean"]), "won": r3(sy["won_mean"]), "lost": r3(sy["lost"]), "games": yc["n"], "errors": yc["errors"], "points_logit": p, "won_logit": w, "passes": V.passes(p) and V.passes(w),
                         "composition": V.composition(g / f"Y_{t}.json", load("conc" if t.startswith("c") else "plain", int(t[-2:])), set(), {x["fullName"]: x for x in __import__("rl.decks", fromlist=["Pool"]).Pool().cards})}
    ok = res["Y_s48"]["passes"] and res["Y_s49"]["passes"]
    res["plain_passes"], res["concentrated_passes"] = ok, res["Y_cs48"]["passes"] and res["Y_cs49"]["passes"]
    choice = json.loads((D / "table_choice.json").read_text(encoding="utf-8"))["choice"]
    res["table_choice"] = choice
    (g / "gate.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))
    return res


def write_chosen():
    """Amendment 2: after research has the gate's read, B uses the plain tables if plain cleared the gate at both seeds. Never written by the read itself."""
    res = json.loads((D / "gate" / "gate.json").read_text(encoding="utf-8"))
    assert res["plain_passes"], "plain didn't clear the gate: no chosen.json"
    (D / "chosen.json").write_text(json.dumps({str(s): f"runs/probe/C171-table-drafting/table-plain-s{s}/table.json" for s in SEEDS}), encoding="utf-8")
    print("chosen.json written: the plain tables")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--choose", action="store_true")
    ap.add_argument("--decks", action="store_true")
    ap.add_argument("--read", action="store_true")
    ap.add_argument("--write-chosen", action="store_true")
    a = ap.parse_args()
    if a.write_chosen:
        return write_chosen()
    if a.choose:
        choose()
    if a.decks:
        decks()
    if a.read:
        read()


if __name__ == "__main__":
    main()
