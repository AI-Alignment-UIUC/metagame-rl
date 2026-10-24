"""Boundary crowding around the wall cluster (copy-weighted overlap on copy-limited cards), evaluation only."""
import sys
import numpy as np
import torch
ROOT = "C:/Users/evanc/Desktop/333/metagame-rl"
sys.path.insert(0, ROOT)
from rl.decks import Pool  # noqa
from rl.metagame import recent_score  # noqa
pool = Pool()
lim = ~pool.basic_energy.copy(); lim[0] = False
def wover(a, b):
    return float(np.minimum(a[lim], b[lim]).sum()) / max(a[lim].sum(), b[lim].sum(), 1)
for snap in sys.argv[1:]:
    st = torch.load(f"{ROOT}/{snap}", map_location="cpu", weights_only=False)
    decks = [pool.vector(a["deck"]) for a in st["population"]]
    score = np.array([recent_score(a, 0.5) for a in st["population"]])
    founder = decks[int(np.argmax(score))]
    # wall cluster = decks with overlap >= 0.5 to the best deck's founder chain: use the largest cluster's founder
    founders, members = [], []
    for i in np.argsort(-score, kind="stable"):
        k = next((t for t, f in enumerate(founders) if wover(f, decks[i]) >= 0.5), None)
        if k is None:
            founders.append(decks[i]); members.append([]); k = len(founders) - 1
        members[k].append(i)
    big = int(np.argmax([len(m) for m in members]))
    cen = np.mean([decks[i] for i in members[big]], 0)
    ov = np.array([float(np.minimum(v[lim], cen[lim]).sum() / max(v[lim].sum(), cen[lim].sum(), 1)) for v in decks])
    inb = np.zeros(len(decks), bool); inb[members[big]] = True
    out = ov[~inb]
    print(snap.split('/')[-2], snap.split('/')[-1], "wall cluster", inb.sum(), "| non-wall n", (~inb).sum(),
          "overlap-to-centroid non-wall mean %.2f" % out.mean() if len(out) else "", "| in [0.35,0.5):", int(((out >= 0.35) & (out < 0.5)).sum()),
          "| <0.25:", int((out < 0.25).sum()), "| wall members mean %.2f" % ov[inb].mean())
