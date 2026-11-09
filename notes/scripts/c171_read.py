"""C171 (runs/probe/C171-table-drafting/record.md, with Amendment 1 and #772): a stage read for a screen (c168_read.stage, plus the table's Pokemon value, effective names, deck kinds in its top 12, colourless share, proposal share on the table's top 10, and the head's own share with the
bonus subtracted); the G3 probes (the top 12 against the 24 lists, under C49-sd for the band, the arm's own pilot beside it, and the common pilot C127 s16); the bands at an iteration. R-start: G3 B - W at +0.08 and E over Pokemon names B - W at -0.05 or lower, at both seeds. R-learns: R-start, and (B's
top 12 at the iteration minus its start population) - (the same for W) at +0.04 at both seeds under C127 s16. R-no-gain: G3 B - W under +0.04. R-walls: both B seeds stopped on the wall signature. R-narrow: under 3 deck kinds in B's top 12 at either seed, in place of R-start or R-learns.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c171_read.py --stage runs/screens/<run> [--iter I]
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c171_read.py --band 29
"""
import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes/scripts"))
import c168_read as R                     # noqa: E402
from rl.decks import Pool                 # noqa: E402
from rl.metagame import deck_kinds, recent_score   # noqa: E402

D = ROOT / "runs/probe/C171-table-drafting"
PY = str(ROOT / ".venv/Scripts/python.exe")
C49 = "runs/pilot/C49-sd/model_it00199.pt"
S16 = "runs/screens/C127-R1-K-paired-ledger-s16/checkpoint.pt"
POOL = Pool()
CARD = {c["fullName"]: c for c in POOL.cards}
SEEDS = (48, 49)


def table(seed):
    """The chosen table, or the plain one while B holds, so W's stage reads can carry a table value."""
    f = D / "chosen.json"
    if not (D / f"table-plain-s{seed}").exists():      # C184's seeds 50 and 51 have no table of their own: the stage's table value reads on s48's
        seed = 48
    path = ROOT / json.loads(f.read_text(encoding="utf-8"))[str(seed)] if f.exists() else D / f"table-plain-s{seed}" / "table.json"
    return json.loads(path.read_text(encoding="utf-8"))


def top12(run, it):
    pop = torch.load(run / f"population_it{it:04d}.pt", map_location="cpu", weights_only=False)["population"]
    return sorted(pop, key=lambda a: -recent_score(a, 0.0))[:12], pop


def body_extra(decks, coef):
    names = collections.Counter(CARD[x]["name"] for d in decks for x in d if CARD[x]["superType"] == 1)
    total = sum(names.values())
    share = np.array(list(names.values()), dtype=float) / total
    colour = [sum(not any(v for t, v in enumerate(CARD[x]["types"]) if t != 0) for x in d if CARD[x]["superType"] == 1) / max(1, sum(CARD[x]["superType"] == 1 for x in d)) for d in decks]
    return {"table_value_a_copy": round(sum(coef.get(n, 0.0) * k for n, k in names.items()) / total, 4), "effective_names": round(float(1 / (share ** 2).sum()), 1), "colourless_share": round(float(np.mean(colour)), 3),
            "top_5_names": [[n, round(k / total, 3)] for n, k in names.most_common(5)]}


def kinds(decks):
    v = [POOL.vector(d) for d in decks]
    _, sizes = deck_kinds(POOL, v, np.arange(len(v), 0, -1, dtype=float))
    return len(sizes)


def proposal_share(run, it, coef, width=10):
    top = set(sorted(coef, key=lambda n: -coef[n])[:10])
    bare = {str(i): n.rsplit(" ", 1)[0] for i, n in POOL.full_name.items()}
    t = collections.Counter()
    rows = sorted(R.aw.rows(run).values(), key=lambda x: x["iter"])
    for r in rows:
        if it - width < r["iter"] <= it:
            c = (r.get("select") or {}).get("card")
            for k, v in (c or {}).get("prop_in", {}).items():
                t["all"] += v
                t["top"] += v if bare[str(k)] in top else 0
    head = [r.get("table_head") for r in rows if r.get("table_head")]
    return {"share_on_table_top10": round(t["top"] / t["all"], 4) if t["all"] else None, "head_at_0": head[0] if head else None, "head_now": head[-1] if head else None}


def stage(run, it, seed):
    run = Path(run) if Path(run).is_absolute() else ROOT / run
    out = R.stage(run, it)
    out.pop("ledger_shares", None)
    coef = table(seed)
    best, pop = top12(run, it)
    decks = [a["deck"] for a in pop]
    out["population_body"] = body_extra(decks, coef)
    out["top12_body"] = body_extra([a["deck"] for a in best], coef)
    out["top12_kinds"] = kinds([a["deck"] for a in best])
    out["population_kinds"] = kinds(decks)
    out["deck_kinds_by_birth"] = dict(collections.Counter(str(a.get("kind")) for a in pop))
    out["proposals"] = proposal_share(run, it, coef)
    return out


def g3(run, it, pilot, tag, top=12, games=8, workers=3):
    """probe_meta_premise.py on the run's saved population; returns M. The file records each deck's M, to read the top name left out."""
    out = run / f"g3_{tag}_it{it:04d}.json"
    if not out.exists():
        rel = (run / f"population_it{it:04d}.pt").relative_to(ROOT).as_posix()
        subprocess.run([PY, "notes/scripts/probe_meta_premise.py", "--pilot", pilot, "--games", str(games), "--workers", str(workers), "--seed", "93", "--top", str(top), "--pops", rel, "--out", out.relative_to(ROOT).as_posix()],
                       cwd=ROOT, check=True, env={**__import__("os").environ, "PYTHONPATH": ".", "RL_GPU_SHARE": "0.15", "RL_CPU_THREADS": "6"}, capture_output=True, text=True)
    return json.loads(out.read_text(encoding="utf-8"))["pops"]


def g3_reads(run, it, start=False):
    """Under C49-sd (the band), the arm's own pilot, and C127 s16; at the start, the whole population under C127 s16 too. Returns M for each, and M with the top 12's most common name left out."""
    rel = (run / f"population_it{it:04d}.pt").relative_to(ROOT).as_posix()
    res = {}
    for tag, pilot in (("C49", C49), ("own", rel), ("s16", S16)):
        r = next(iter(g3(run, it, pilot, tag).values()))
        res[tag] = {"M": round(r["M"], 4), "se": round(r["se_pairs"], 4)}
        if tag == "C49":
            best, _ = top12(run, it)
            names = collections.Counter(n for a in best for n in {CARD[x]["name"] for x in a["deck"] if CARD[x]["superType"] == 1})
            top, _n = names.most_common(1)[0]
            keep = [m for a, m in zip(best, r["by_deck"]) if not any(CARD[x]["name"] == top for x in a["deck"])]
            res["top_name_left_out"] = {"name": top, "decks": len(keep), "M": round(float(np.mean(keep)), 4) if keep else None, "thin": len(keep) < 6}
    if start:
        r = next(iter(g3(run, it, S16, "s16_population", top=99, games=2).values()))
        res["population_s16"] = {"M": round(r["M"], 4), "se": round(r["se_pairs"], 4)}
    return res


def band(it):
    arms = {a: [ROOT / "runs/screens" / f"C171-{a}-s{s}" for s in SEEDS] for a in "BW"}
    ok = {a: [(r / f"population_it{it:04d}.pt").exists() for r in rs] for a, rs in arms.items()}
    if not all(ok["B"]) or not ok["W"][0]:
        return {"iter": it, "not_ready": ok}
    w_stand_in = not ok["W"][1]                          # taken by default (row 115): W s48 stands in until W s49 reaches the iteration
    rows = {}
    for k, s in enumerate(SEEDS):
        b, w = arms["B"][k], arms["W"][k if ok["W"][k] else 0]
        gb, gw = g3_reads(b, it), g3_reads(w, it)
        sb, sw = stage(b, it, s), stage(w, it, s)
        start_b, start_w = g3_reads(b, 0, start=True), g3_reads(w, 0, start=True)
        rows[s] = {"G3_B_minus_W": round(gb["C49"]["M"] - gw["C49"]["M"], 4), "G3": {"B": gb, "W": gw}, "names_E_B_minus_W": round(sb["body"]["names_E"] - sw["body"]["names_E"], 4),
                   "learn_B": round(gb["s16"]["M"] - start_b["population_s16"]["M"], 4), "learn_W": round(gw["s16"]["M"] - start_w["population_s16"]["M"], 4), "start": {"B": start_b, "W": start_w},
                   "top12_kinds_B": sb["top12_kinds"], "wall_B": sb["wall_share"], "wall_W": sw["wall_share"], "stage_B": sb, "stage_W": sw}
        rows[s]["learn_difference"] = round(rows[s]["learn_B"] - rows[s]["learn_W"], 4)
    narrow = any(r["top12_kinds_B"] < 3 for r in rows.values())
    start_ok = all(r["G3_B_minus_W"] >= 0.08 and r["names_E_B_minus_W"] <= -0.05 for r in rows.values())
    learns = start_ok and all(r["learn_difference"] >= 0.04 for r in rows.values())
    no_gain = all(r["G3_B_minus_W"] < 0.04 for r in rows.values())
    name = "R-narrow" if (narrow and start_ok) else "R-learns" if learns else "R-start" if start_ok else "R-no-gain" if no_gain else "between"
    out = {"iter": it, "band": name, "narrow_flag": narrow, "w_s48_stands_in_for_w_s49": w_stand_in, "seeds": rows}
    (D / f"band_it{it:04d}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="")
    ap.add_argument("--iter", type=int, default=None)
    ap.add_argument("--seed", type=int, default=48)
    ap.add_argument("--band", type=int, default=None)
    a = ap.parse_args()
    if a.band is not None:
        o = band(a.band)
        print(json.dumps({k: v for k, v in o.items() if k != "seeds"}))
        for s, r in o.get("seeds", {}).items():
            print(s, {k: v for k, v in r.items() if k not in ("stage_B", "stage_W", "G3", "start")}, "G3 B", r["G3"]["B"], "G3 W", r["G3"]["W"])
    else:
        print(json.dumps(stage(a.stage, a.iter if a.iter is not None else R.saved(ROOT / a.stage)[-1], a.seed)))


if __name__ == "__main__":
    main()
