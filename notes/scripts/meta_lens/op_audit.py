"""Operator composition audit (evaluation only, no games): for a saved metagame snapshot, sample draws from the saved
draft head under several operator variants and report the mean change in Pokemon / Trainer / Energy per draw, plus the
kind shares of the cards cut (out) and added (in) per change. Validates against the logged 'prop' of the next iteration.
Given a pilot checkpoint instead (no population), it audits fresh heads on 99 fresh wide decks, C51's start (log #195);
the Nf variant is H110's features base measure (rl/draft.py base="features"). Card kinds are read here only.
"""
import os
import sys
import json
from pathlib import Path
import numpy as np
import torch

ROOT = "C:/Users/evanc/Desktop/333/metagame-rl"
sys.path.insert(0, ROOT)
from rl import limits  # noqa: E402
from rl.decks import Pool, deck_shape, wide_deck  # noqa: E402
from rl.draft import DeckView, Drafter  # noqa: E402
from rl.gpu_matrix import load_policy  # noqa: E402

snap = sys.argv[1]
M = int(sys.argv[2]) if len(sys.argv) > 2 else 60
ND = int(sys.argv[3]) if len(sys.argv) > 3 else 99
dev = "cuda"
limits.apply(dev, 4, watch=False)
pool = Pool()
kind = np.zeros(pool.n, dtype=np.int64)          # 0 none, 1 Pokemon, 2 Trainer, 3 Energy
for c in pool.cards:
    kind[c["id"]] = c["superType"]
st = torch.load(f"{ROOT}/{snap}", map_location="cpu", weights_only=False)
net, _ = load_policy(snap, dev)
cfg = st["config"]
rng = np.random.default_rng(7)
wide = "population" not in st                    # a pilot checkpoint: fresh wide decks as rl.metagame --init-wide makes
if wide:
    w = np.random.default_rng(3)
    allpop = [wide_deck(pool, w) for _ in range(99)]
else:
    allpop = [pool.vector(a["deck"]) for a in st["population"]]
pop = allpop[:ND]


def make(floor, group, fresh=False, base="uniform", base_ent=3.0):
    dr = Drafter(pool, cfg["d"], cfg["heads"], 6, 3e-4, dev, h_in_floor=floor, group_p=group, base=base,
                 base_ent=base_ent)
    if not fresh:
        dr.load(st["drafter"])
    return dr


# a saved head is scored under its own run's base measure (the run folder's config.json; uniform before #195)
run_cfg = Path(f"{ROOT}/{snap}").parent / "config.json"
run_cfg = json.loads(run_cfg.read_text()) if run_cfg.exists() else {}
rb, re_ = run_cfg.get("draft_base", "uniform"), run_cfg.get("draft_base_ent", 3.0)
variants = ({} if wide else {"as_run(f3,g.3)": make(3.0, 0.3, base=rb, base_ent=re_), "T1(f0,g.3)": make(0.0, 0.3, base=rb, base_ent=re_),
                             "f3,g0": make(3.0, 0.0, base=rb, base_ent=re_)})
variants.update({"uniform(g.3)": make(0.0, 0.3, fresh=True), "uniform(f3,g.3)": make(3.0, 0.3, fresh=True),
                 "Nf(f3,g.3)": make(3.0, 0.3, fresh=True, base="features")})
# AUDIT_BASE_ENTS="1.5,2": fresh Nf heads at other base entropies (the dose lever, log #196)
for b in [float(x) for x in os.environ.get("AUDIT_BASE_ENTS", "").split(",") if x]:
    variants[f"Nf{b:g}(f3,g.3)"] = make(3.0, 0.3, fresh=True, base="features", base_ent=b)
res = {k: {"d": [], "out": np.zeros(4), "inn": np.zeros(4)} for k in variants}
hin = []
for i, deck in enumerate(pop):
    others = [e for e in range(len(allpop)) if e != i]
    field = [allpop[e] for e in rng.choice(others, 4, replace=False)]
    base = None
    for name, dr in variants.items():
        vw = dr.view(net, deck, field) if base is None else None
        if base is None:
            base = vw
        else:                                      # same reading, this head's scores (and base measure)
            vw = DeckView(base.deck, base.ids, base.counts, base.H, base.h0, base.E, base.base)
            dr.set_base(vw)
            dr.refresh(vw)
        s0 = deck_shape(pool, deck)
        s0 = np.array([s0["pokemon"], s0["trainer"], s0["basic_energy"] + s0["special_energy"]])
        for _ in range(M):
            x = dr.sample(vw, rng)
            s = deck_shape(pool, x["deck"])
            s = np.array([s["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"]])
            res[name]["d"].append(s - s0)
            for j, c in zip(x["ev_j"], x["ev_c"]):
                res[name]["out"][kind[int(vw.ids[j])]] += 1
                res[name]["inn"][kind[c]] += 1
    if i % 20 == 0:
        print("deck", i, flush=True)
out = {}
for name, r in res.items():
    d = np.array(r["d"])
    o = r["out"][1:] / r["out"][1:].sum()
    n_ = r["inn"][1:] / r["inn"][1:].sum()
    out[name] = {"prop_PTE": np.round(d.mean(0), 3).tolist(), "se": np.round(d.std(0) / np.sqrt(len(d)), 3).tolist(),
                 "out_share_PTE": np.round(o, 3).tolist(), "in_share_PTE": np.round(n_, 3).tolist()}
    print(name, out[name])
shapes = np.array([[deck_shape(pool, v)[k] for k in ("pokemon", "trainer")] + [deck_shape(pool, v)["basic_energy"] + deck_shape(pool, v)["special_energy"]] for v in pop])
print("pop mean shape", np.round(shapes.mean(0), 2).tolist(), "copy shares", np.round(shapes.mean(0) / 60, 3).tolist())
json.dump(out, open(sys.argv[4] if len(sys.argv) > 4 else "op_audit_out.json", "w"), indent=1)
