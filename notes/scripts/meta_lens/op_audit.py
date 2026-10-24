"""Operator composition audit (evaluation only, no games): for a saved metagame snapshot, sample draws from the saved
draft head under several operator variants and report the mean change in Pokemon / Trainer / Energy per draw, plus the
kind shares of the cards cut (out) and added (in) per change. Validates against the logged 'prop' of the next iteration.
"""
import sys
import json
import numpy as np
import torch

ROOT = "C:/Users/evanc/Desktop/333/metagame-rl"
sys.path.insert(0, ROOT)
from rl import limits  # noqa: E402
from rl.decks import Pool, deck_shape  # noqa: E402
from rl.draft import Drafter  # noqa: E402
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
pop = [pool.vector(a["deck"]) for a in st["population"]][:ND]
allpop = [pool.vector(a["deck"]) for a in st["population"]]


def make(floor, group, fresh=False):
    dr = Drafter(pool, cfg["d"], cfg["heads"], 6, 3e-4, dev, h_in_floor=floor, group_p=group)
    if not fresh:
        dr.load(st["drafter"])
    return dr


variants = {"as_run(f3,g.3)": make(3.0, 0.3), "T1(f0,g.3)": make(0.0, 0.3), "f3,g0": make(3.0, 0.0),
            "uniform(g.3)": make(0.0, 0.3, fresh=True)}
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
        else:                                      # same reading, this head's scores
            from rl.draft import DeckView
            vw = DeckView(base.deck, base.ids, base.counts, base.H, base.h0, base.E, base.base)
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
