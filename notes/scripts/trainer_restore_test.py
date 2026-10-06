"""Does the value-built deck of 2000s result #1 lose anything by dropping Trainers for Energy? (log #36)
Four 60-card variants, from the built deck (34 Energy) to Chris Graham's list (22 Energy): the pilot's
start-of-game value against the 24 archived lists (16 deals each) beside real games (100 per pair).

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/trainer_restore_test.py [pilot.pt] (default: result #1's pilot)
"""
import json, sys, numpy as np
from rl.decks import Pool, archived_decks
from rl.gpu_matrix import GpuMatrix
pool = Pool()
arch = archived_decks(pool)
pop = json.load(open("results/2000s-result-1/data/value/population.json", encoding="utf-8"))
built = [x for x in pop if x["name"].startswith("value5-0")][0]["cards"]
graham = pool.names([v for n, v in arch if "Graham" in n][0])
def swap(cards, out, add):
    cards = list(cards)
    for name, k in out:
        for _ in range(k): cards.remove(name)
    for name, k in add: cards += [name] * k
    assert len(cards) == 60
    return cards
half = swap(built, [("Lightning Energy BS", 6)], [("PlusPower BS", 3), ("Gust of Wind BS", 2), ("Professor Oak BS", 1)])
back = swap(built, [("Lightning Energy BS", 12)], [("PlusPower BS", 3), ("Gust of Wind BS", 2), ("Scoop Up BS", 2),
            ("Energy Retrieval BS", 2), ("Professor Oak BS", 1), ("Super Energy Removal BS", 1), ("Scyther JU", 1)])
variants = [("built (34 Energy)", built), ("built, 6 Lightning -> PlusPower 3, Gust 2, Oak 1", half),
            ("built, 12 Lightning -> Graham's Trainers", back), ("Graham's list (22 Energy)", graham)]
for _, c in variants: assert pool.legal(pool.vector(c)), _
field = [{"name": n, "cards": pool.names(v)} for n, v in arch]
decks = field + [{"name": n, "cards": c} for n, c in variants]
F, V = len(field), len(variants)
gm = GpuMatrix(sys.argv[1] if len(sys.argv) > 1 else "results/2000s-result-1/pilot/model_it00014.pt", 14)
try:
    vals = gm.values(decks, [(F + k, j) for k in range(V) for j in range(F)], 16, 5).reshape(V, F)
    W, G, _ = gm.play(decks, 100, 17, pairs=[(F + k, j) for k in range(V) for j in range(F)] +
                      [(F + a, F + b) for a in range(V) for b in range(a + 1, V)])
    print(gm.last)
finally:
    gm.close()
P = W / np.maximum(G, 1)
print(f"{'variant':52s} value-predicted  real vs field (24 lists x 100)")
for k, (n, _) in enumerate(variants):
    print(f"{n:52s} {0.5 + 0.5 * vals[k].mean():.3f}           {P[F + k, :F].mean():.3f} ± {1.96 * np.sqrt(0.25 / (F * 100)):.3f}")
print("head to head (row beats column, 100 games):")
for a in range(V):
    print("  " + variants[a][0][:40].ljust(42) + " ".join(f"{P[F + a, F + b]:.2f}" if a != b else " -- " for b in range(V)))
