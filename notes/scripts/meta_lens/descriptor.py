"""How a copy-weighted descriptor on copy-limited cards groups populations, against deck_kinds (evaluation only)."""
import sys
import numpy as np
import torch

ROOT = "C:/Users/evanc/Desktop/333/metagame-rl"
sys.path.insert(0, ROOT)
from rl.decks import Pool  # noqa: E402
from rl.metagame import deck_kinds, recent_score  # noqa: E402

pool = Pool()
limited = ~pool.basic_energy.copy()
limited[0] = False
cs = [pool.id.get("Chansey BS"), pool.id.get("Snorlax JU")]
cs_name = {pool.name_of[c] for c in cs if c}


def wover(a, b):
    """Copy-weighted overlap of the copy-limited cards: shared copies / the larger count."""
    return float(np.minimum(a[limited], b[limited]).sum()) / max(a[limited].sum(), b[limited].sum(), 1)


def kinds_w(decks, score, link=0.5):
    founders, sizes = [], []
    for i in np.argsort(-score, kind="stable"):
        k = next((t for t, f in enumerate(founders) if wover(f, decks[i]) >= link), None)
        if k is None:
            founders.append(decks[i])
            sizes.append(0)
            k = len(founders) - 1
        sizes[k] += 1
    return sorted(sizes, reverse=True)


for snap in sys.argv[1:]:
    st = torch.load(f"{ROOT}/{snap}", map_location="cpu", weights_only=False)
    decks = [pool.vector(a["deck"]) for a in st["population"]]
    score = np.array([recent_score(a, 0.5) for a in st["population"]])
    _, s0 = deck_kinds(pool, decks, score)
    both = sum(1 for v in decks if all(v[[c for c in range(pool.n) if pool.name_of[c] == pool.name_of[x]]].sum() > 0 for x in cs))
    out = {}
    for link in (0.4, 0.5, 0.6):
        out[link] = kinds_w(decks, score, link)[:6]
    print(snap, "deck_kinds", sorted(s0, reverse=True)[:6], "| weighted@0.4/0.5/0.6", out[0.4], out[0.5], out[0.6], "| C+S", both)
