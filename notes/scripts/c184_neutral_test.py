"""C184 Amendment 2's acceptance, CPU only (runs/probe/C184-recovery-arm/record.md): at a matched start, the same decks, pilot and head, are Trainers proposed per candidate under --table-neutral within noise of no bonus, per supertype, with and without --draft-group-p and the entropy floor? D's plain bonus beside it, as the fault it should remove. Also: each pick's supertype mass against no bonus, log_prob against sample's logp under the shift, the gradient, and C187's --draft-lr 0 leaving the head unchanged.
  CUDA_VISIBLE_DEVICES= PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c184_neutral_test.py --run runs/screens/C184-WR-s50 --it 4 [--decks 12] [--draws 60] [--out f.json]
"""
import argparse
import json
import os
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = ""
import numpy as np
import torch

from rl.decks import Pool, deck_shape
from rl.draft import Drafter, floor_temperature, group_neutral
from rl.remote import RemotePool
from rl.train import token_net

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "runs/probe/C182-trainer-table-drafting/table.json"
KINDS = ("P", "T", "E")


def table_bonus(pool, kappa=1.0):
    """As rl/metagame.py builds it: z of the plain table on Trainer names, every other card 0."""
    coef = json.loads(TABLE.read_text(encoding="utf-8"))
    vals = np.array(list(coef.values()), dtype=float)
    z = {n: float((c - vals.mean()) / vals.std()) for n, c in coef.items()}
    b = np.zeros(pool.n)
    for c in pool.cards:
        if c["superType"] == 2 and c["name"] in z:
            b[c["id"]] = kappa * z[c["name"]]
    return b


def card_kinds(pool):
    k = np.zeros(pool.n, dtype=np.int64)
    for c in pool.cards:
        k[c["id"]] = c["superType"]
    return k


def shape(pool, v):
    s = deck_shape(pool, v)
    return np.array([s["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"]], dtype=float)


def net_per_deck(drafter, vw, pool, draws, seed):
    """The mean P/T/E change of a candidate on this deck."""
    rng = np.random.default_rng(seed)
    s0 = shape(pool, vw.deck)
    return np.mean([shape(pool, drafter.sample(vw, rng)["deck"]) - s0 for _ in range(draws)], 0)


def pick_mass(drafter, vw, bonus, kinds):
    """Every row's supertype mass, neutral against no bonus, at this drafter's floor: the largest absolute gap."""
    base = vw.base.cpu().numpy()
    worst, warm, rows = 0.0, 0, 0
    for j in range(len(vw.ids)):
        m = base[j]
        if not m.any():
            continue
        b = None if vw.b0np is None else vw.b0np[j]
        x = np.where(m, vw.logits[j] + bonus, -np.inf)
        x0 = np.where(m, vw.logits[j], -np.inf)
        T, T0 = floor_temperature(x, drafter.h_in_floor, b), floor_temperature(x0, drafter.h_in_floor, b)
        y0 = (x0 - x0.max()) / T0 if b is None else b + x0 / T0
        y = group_neutral((x - x.max()) / T if b is None else b + x / T, y0, kinds)
        q, q0 = np.exp(y - y.max()), np.exp(y0 - y0.max())
        q, q0 = q / q.sum(), q0 / q0.sum()
        worst = max(worst, max(abs(q[kinds == k].sum() - q0[kinds == k].sum()) for k in (1, 2, 3)))
        warm += T > 1 or T0 > 1
        rows += 1
    return worst, warm, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="runs/screens/C184-WR-s50")
    ap.add_argument("--it", type=int, default=4)
    ap.add_argument("--decks", type=int, default=12)
    ap.add_argument("--draws", type=int, default=60)
    ap.add_argument("--field", type=int, default=2)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--seed", type=int, default=184)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    pool = Pool()
    rp = RemotePool(1)
    info = rp.ask_all([{"cmd": "info"}])[0]
    rp.close()
    st = torch.load(ROOT / a.run / f"population_it{a.it:04d}.pt", map_location="cpu", weights_only=False)
    cfg = json.loads((ROOT / a.run / "config.json").read_text(encoding="utf-8"))
    net = token_net(st["config"], info)
    net.load_state_dict(st["net"])
    net.eval()
    c0 = st["config"]
    dr = Drafter(pool, c0["d"], c0["heads"], cfg["swaps"], 0.0, "cpu", h_in_floor=cfg["draft_h_in_floor"], group_p=cfg["draft_group_p"], base=cfg["draft_base"], base_ent=cfg["draft_base_ent"])
    dr.head.load_state_dict(st["drafter"]["head"])
    rng = np.random.default_rng(a.seed)
    decks = [np.array(pool.vector(x["deck"])) for x in st["population"]]
    pick = rng.choice(len(decks), min(a.decks, len(decks)), replace=False)
    views = []
    for d in pick:
        others = [e for e in range(len(decks)) if e != d]
        field = [decks[e] for e in rng.choice(others, a.field, replace=False)]
        views.append(dr.view(net, decks[d], field))
    bonus, kinds = table_bonus(pool), card_kinds(pool)
    out = {"run": a.run, "it": a.it, "decks": len(views), "draws_each": a.draws, "start_pte": np.round(np.mean([shape(pool, v.deck) for v in views], 0), 2).tolist(), "variants": {}}

    for name, floor, group in (("recipe: floor 3, group 0.3", cfg["draft_h_in_floor"], cfg["draft_group_p"]), ("floor only", cfg["draft_h_in_floor"], 0.0), ("group only", 0.0, cfg["draft_group_p"]), ("neither", 0.0, 0.0), ("binding floor 5.3, group 0.3", 5.3, cfg["draft_group_p"]), ("binding floor 5.3, no group", 5.3, 0.0)):
        dr.h_in_floor, dr.group_p = floor, group
        res = {}
        for arm, b, g in (("none", None, None), ("plain", bonus, None), ("neutral", bonus, kinds)):
            rows = []
            for i, vw in enumerate(views):
                vw.bonus, vw.bonus_groups = b, g
                rows.append(net_per_deck(dr, vw, pool, a.draws, a.seed + 1000 * i + {"none": 1, "plain": 2, "neutral": 3}[arm]))
            res[arm] = np.array(rows)
        row = {arm: dict(zip(KINDS, np.round(res[arm].mean(0), 3).tolist())) for arm in res}
        for arm in ("plain", "neutral"):
            d = res[arm] - res["none"]
            row[f"{arm}_minus_none"] = dict(zip(KINDS, np.round(d.mean(0), 3).tolist()))
            row[f"{arm}_se"] = dict(zip(KINDS, np.round(d.std(0, ddof=1) / len(d) ** 0.5, 3).tolist()))
        for vw in views:
            vw.bonus, vw.bonus_groups = bonus, kinds
        pm = [pick_mass(dr, vw, bonus, kinds) for vw in views]
        row["pick_mass_gap_max"] = float(max(x[0] for x in pm))
        row["rows_with_floor_binding"] = round(sum(x[1] for x in pm) / sum(x[2] for x in pm), 3)
        out["variants"][name] = row

    # log_prob against sample's logp, the gradient, under the recipe
    dr.h_in_floor, dr.group_p = cfg["draft_h_in_floor"], cfg["draft_group_p"]
    gaps = {}
    for arm, b, g in (("none", None, None), ("plain", bonus, None), ("neutral", bonus, kinds)):
        vw = views[0]
        vw.bonus, vw.bonus_groups = b, g
        r = np.random.default_rng(a.seed)
        samples = [dr.sample(vw, r) for _ in range(20)]
        lp = dr.log_prob(vw, samples)[0]
        gaps[arm] = float(np.abs(lp.detach().numpy() - np.array([x["logp"] for x in samples])).max())
        if arm == "neutral":
            dr.head.zero_grad()
            lp.sum().backward()
            grad = sum(float(p.grad.abs().sum()) for p in dr.head.parameters() if p.grad is not None)
            out["neutral_grad_sum"] = grad
            out["neutral_grad_finite"] = bool(np.isfinite(grad) and grad > 0)
    out["logp_gap_max"] = gaps

    # C187: --draft-lr 0 leaves the head unchanged through one real update
    before = {k: v.clone() for k, v in dr.head.state_dict().items()}
    vw = views[0]
    vw.bonus, vw.bonus_groups = None, None
    r = np.random.default_rng(a.seed)
    samples = [dr.sample(vw, r) for _ in range(8)]
    info_up = dr.update([(vw, samples, r.normal(size=8))], 0.01)
    out["lr0_head_unchanged"] = all(torch.equal(before[k], v) for k, v in dr.head.state_dict().items())
    out["lr0_update_keys"] = {k: (round(float(v), 4) if isinstance(v, (int, float)) else None) for k, v in info_up.items()}
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
