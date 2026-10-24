"""A screen's population by deck type (log #130): types as rl/metagame.py deck_kinds groups them (best first, joined at
half the Pokemon), with each type's size, mean result and mean shape, and the Pokemon of its best deck. Evaluation only.

  .venv/Scripts/python notes/scripts/screen_types.py runs/screens/scr-reset/checkpoint.pt [--top 6]
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rl.decks import Pool, deck_shape
from rl.metagame import deck_kinds, recent_score


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("ckpt")
    ap.add_argument("--top", type=int, default=6)
    a = ap.parse_args(argv)
    pool = Pool()
    st = torch.load(a.ckpt, map_location="cpu", weights_only=False)
    pop = st["population"]
    decks = [pool.vector(x["deck"]) for x in pop]
    score = np.array([recent_score(x, 0.5) for x in pop])       # the judged score with --judge-search (log #148)
    kind, sizes = deck_kinds(pool, decks, score)
    pk = {c["id"] for c in pool.cards if c["superType"] == 1}
    print(f"iter {st.get('iter')}: {len(sizes)} types, sizes {sorted(sizes, reverse=True)[:12]}")
    for k in np.argsort(-np.array(sizes))[:a.top]:
        m = np.nonzero(kind == k)[0]
        sh = np.array([[s["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"]]
                       for s in (deck_shape(pool, decks[i]) for i in m)]).mean(0)
        b = m[np.argmax(score[m])]
        mons = Counter(n for n in pop[b]["deck"] if pool.vector([n]).nonzero()[0][0] in pk)
        print(f"  type of {len(m):3d}: result {score[m].mean():.2f}, shape {sh[0]:.1f}/{sh[1]:.1f}/{sh[2]:.1f}; best "
              f"#{pop[b]['id']} ({score[b]:.2f}): " + ", ".join(f"{n} {c}" for c, n in mons.most_common(6)))


if __name__ == "__main__":
    main()
