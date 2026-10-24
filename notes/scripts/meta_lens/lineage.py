"""Do decks join the wall cluster by drift (same id, moved by accepted proposals) or by replacement (turnover)?"""
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
s0 = torch.load(f"{ROOT}/runs/screens/scr-resetcap/population_it0479.pt", map_location="cpu", weights_only=False)
d0 = {a["id"]: pool.vector(a["deck"]) for a in s0["population"]}
sc0 = {a["id"]: recent_score(a, 0.5) for a in s0["population"]}
# wall centroid at 479 from the largest weighted cluster
ids = sorted(d0, key=lambda i: -sc0[i]); founders, mem = [], []
for i in ids:
    k = next((t for t, f in enumerate(founders) if wover(f, d0[i]) >= 0.5), None)
    if k is None: founders.append(d0[i]); mem.append([]); k = len(founders) - 1
    mem[k].append(i)
big = int(np.argmax([len(m) for m in mem])); cen = np.mean([d0[i] for i in mem[big]], 0)
def cov(v): return float(np.minimum(v[lim], cen[lim]).sum() / max(v[lim].sum(), cen[lim].sum(), 1))
wall0 = {i for i in d0 if cov(d0[i]) >= 0.5}
print("479: wall (overlap to 479 wall centroid >= 0.5):", len(wall0), "of", len(d0))
for snap in sys.argv[1:]:
    st = torch.load(f"{ROOT}/{snap}", map_location="cpu", weights_only=False)
    pop = st["population"]
    wall = [a for a in pop if cov(pool.vector(a["deck"])) >= 0.5]
    same_id_wall_before = sum(1 for a in wall if a["id"] in d0 and a["id"] in wall0)
    same_id_converted = sum(1 for a in wall if a["id"] in d0 and a["id"] not in wall0)
    new = [a for a in wall if a["id"] not in d0]
    new_kind = {}
    for a in new: new_kind[a.get("kind")] = new_kind.get(a.get("kind"), 0) + 1
    nonwall_survivors = sum(1 for a in pop if a["id"] in d0 and a["id"] not in wall0 and cov(pool.vector(a["deck"])) < 0.5)
    left_wall = sum(1 for a in pop if a["id"] in wall0 and cov(pool.vector(a["deck"])) < 0.5)
    print(snap.split('/')[-2], snap.split('/')[-1], "| wall now", len(wall), "| same id, wall at 479:", same_id_wall_before,
          "| same id, converted non-wall->wall:", same_id_converted, "| new ids in wall:", len(new), new_kind,
          "| 479 non-walls still non-wall:", nonwall_survivors, "| 479 walls that left:", left_wall)
