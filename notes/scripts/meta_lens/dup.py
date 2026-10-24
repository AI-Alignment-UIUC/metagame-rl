"""Candidate uniqueness among K=3 draws of the saved head (evaluation only)."""
import sys
import numpy as np
import torch
ROOT = "C:/Users/evanc/Desktop/333/metagame-rl"
sys.path.insert(0, ROOT)
from rl import limits  # noqa
from rl.decks import Pool  # noqa
from rl.draft import Drafter  # noqa
from rl.gpu_matrix import load_policy  # noqa
dev = "cuda"; limits.apply(dev, 4, watch=False)
pool = Pool()
for snap in sys.argv[1:]:
    st = torch.load(f"{ROOT}/{snap}", map_location="cpu", weights_only=False)
    net, _ = load_policy(snap, dev); cfg = st["config"]
    dr = Drafter(pool, cfg["d"], cfg["heads"], 6, 3e-4, dev, h_in_floor=3.0, group_p=0.3); dr.load(st["drafter"])
    rng = np.random.default_rng(3)
    pop = [pool.vector(a["deck"]) for a in st["population"]]
    dup_first, dup_any_in, R = 0, 0, 20
    for i, deck in enumerate(pop):
        others = [e for e in range(len(pop)) if e != i]
        vw = dr.view(net, deck, [pop[e] for e in rng.choice(others, 4, replace=False)])
        for _ in range(R):
            xs = [dr.sample(vw, rng) for _ in range(3)]
            firsts = [x["ev_c"][0] for x in xs]
            dup_first += len(set(firsts)) < 3
            ins = [set(x["ev_c"]) for x in xs]
            dup_any_in += any(len(ins[a] & ins[b]) > 0 for a in range(3) for b in range(a + 1, 3))
    n = len(pop) * R
    print(snap, "P(some pair of the 3 candidates shares its first incoming card) = %.3f" % (dup_first / n),
          "| P(some pair shares any incoming card) = %.3f" % (dup_any_in / n))
