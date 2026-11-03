"""C175 (runs/probe/C175-trainers-strong-bodies/record.md): C165's Trainer factorial on fixed bodies. Three classes, each against itself: Y (Pokemon from C171's plain-table Y decks, human-free), G (from C169's uniform G decks), E2 (the lists' own Pokemon, a reference only). Each deck takes one body from its set at random; its Trainers are drawn as wide_deck's concentrated decks draw them (6-8 distinct Trainers uniformly at 3-4 copies), independent of the body; basic Energy fills to 60, drawn from the body's own basic Energy,
a draw whose Energy count falls outside 8-34 drawn again. 12 pods of 200 decks a class, seed 175. Asserts 60 legal cards and no special Energy, and prints the spread of Trainer counts and their correlation with the body's Pokemon count.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c175_decks.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.decks import Pool    # noqa: E402

D = ROOT / "runs/probe/C175-trainers-strong-bodies"
SOURCES = {"Y": [ROOT / "runs/probe/C171-table-drafting/gate/Y_s48.json", ROOT / "runs/probe/C171-table-drafting/gate/Y_s49.json"], "G": [ROOT / "runs/probe/C169-body-split/G.json"], "E2": [ROOT / "runs/probe/C169-body-split/E2.json"]}
PODS, POD = 12, 200


def main():
    pool = Pool()
    card = {c["fullName"]: c for c in pool.cards}
    trainers = [c for c in pool.cards if pool.allowed[c["id"]] and c["superType"] == 2]
    for k, (cls, files) in enumerate(SOURCES.items()):
        rng = np.random.default_rng(175 + k)
        bodies = []
        for f in files:
            for d in json.loads(f.read_text(encoding="utf-8")):
                mons = [x for x in d["cards"] if card[x]["superType"] == 1]
                es = [x for x in d["cards"] if card[x]["superType"] == 3 and card[x]["energyType"] == 0]
                bodies.append((mons, es))
        decks, rows = [], []
        while len(decks) < PODS * POD:
            mons, es = bodies[int(rng.integers(len(bodies)))]
            n_t = int(rng.integers(6, 9))
            cards = list(mons)
            for j in rng.choice(len(trainers), size=n_t, replace=False):
                cards += [trainers[int(j)]["fullName"]] * int(rng.integers(3, 5))
            n_e = 60 - len(cards)
            if not 8 <= n_e <= 34:
                continue
            cards += [es[int(j)] for j in rng.integers(len(es), size=n_e)]
            assert len(cards) == 60 and pool.legal(pool.vector(cards))
            n = len(decks)
            decks.append({"name": f"{cls}{n // POD}.{n % POD}", "cards": cards})
            rows.append((len(mons), len(cards) - len(mons) - n_e, n_e))
        out = D / cls
        out.mkdir(exist_ok=True)
        (out / "decks.json").write_text(json.dumps(decks), encoding="utf-8")
        a = np.array(rows, dtype=float)
        print(f"{cls}: {len(decks)} decks from {len(bodies)} bodies, legal, 60 cards; mean P/T/E {np.round(a.mean(0), 2).tolist()}, SD {np.round(a.std(0), 2).tolist()}; corr(T, P) {np.corrcoef(a[:, 1], a[:, 0])[0, 1]:.3f}")


if __name__ == "__main__":
    main()
