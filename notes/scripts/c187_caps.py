"""C187's CPU read (runs/probe/C187-head-off/record.md): does D's proposal decline mean anything, or are its Trainer names simply capped? By saved iteration, on a sample of decks, with the run's own pilot and head: the Trainer mass the 4-copy cap blocks, the Trainer mass in and out, and from simulated draws at the run's own recipe, how much Trainer mass group moves carry. The simulated net is checked against the run's logged select.prop.
  CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c187_caps.py --run C182-D-s48 [--decks 16] [--draws 30]
--split (A155, C187's record): is the out-choice blunt, or does it target junk? Out share / copy share by the plain two-seed table's top 12 against the other 30, every deck of each saved population, early (0-14) and late (30-44). A group's ratio is its mean out share over its mean copy share; SEs by bootstrap over deck ids, since a deck can be in several saved populations. Bands at late, both seeds: R-targets, the low 30's ratio at least 0.2 and 2 SE above the top 12's; R-blunt, the gap under 0.1 with SE excluding 0.2.
  CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c187_caps.py --split [--runs C171-W-s48,C171-W-s49]
"""
import argparse
import json
import os
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
import numpy as np
import torch

from c184_neutral_test import ROOT, card_kinds, shape, table_bonus
from rl.decks import Pool
from rl.draft import LEAD, Drafter, deck_tokens
from rl.remote import RemotePool
from rl.train import token_net

OUT = ROOT / "runs/probe/C187-head-off/caps"


def softmax_rows(y):
    q = np.exp(y - y.max(1, keepdims=True))
    return q / q.sum(1, keepdims=True)


def masses(vw, pool, kinds, bonus):
    """Per deck, weighted by the out-choice: Trainer mass in if nothing were capped, the capped part of it, and in as sampled from legal cards. Floor left out, as it doesn't bind on these heads."""
    po = np.log(vw.counts) + vw.s
    po = np.exp(po - po.max())
    po /= po.sum()
    legal = vw.base.cpu().numpy()
    free = np.tile(np.asarray(pool.allowed, dtype=bool), (len(vw.ids), 1))
    free[:, 0] = False
    free[np.arange(len(vw.ids)), vw.ids] = False
    x = vw.b0np + vw.logits + (0 if bonus is None else bonus)
    qf = softmax_rows(np.where(free, x, -np.inf))
    ql = softmax_rows(np.where(legal, x, -np.inf))
    t = kinds == 2
    capped = free & ~legal & t
    return {"T_in_uncapped": float(po @ qf[:, t].sum(1)), "T_capped_mass": float(po @ (qf * capped).sum(1)),
            "T_in_legal": float(po @ ql[:, t].sum(1)), "T_out": float(po[kinds[vw.ids] == 2].sum()),
            "T_ids_capped_share": float(capped.sum(1).mean() / max((free & t).sum(1).mean(), 1))}


def trace(dr, vw, pool, kinds, draws, rng):
    """Copies of Trainers moved per candidate, by the pick and by the group change beside it."""
    s = dict(net=0.0, pick_in=0.0, pick_out=0.0, group_in=0.0, group_out=0.0)
    for _ in range(draws):
        x = dr.sample(vw, rng)
        s["net"] += shape(pool, x["deck"])[1] - shape(pool, vw.deck)[1]
        for j, c, n in zip(x["ev_j"], x["ev_c"], x["ev_n"]):
            out_t, in_t = kinds[vw.ids[j]] == 2, kinds[c] == 2
            s["pick_in"] += in_t
            s["pick_out"] += out_t
            s["group_in"] += n * in_t
            s["group_out"] += n * out_t
    return {k: v / draws for k, v in s.items()}


def logged(run, it, width=5):
    p = []
    for line in open(ROOT / "runs/screens" / run / "log.jsonl", encoding="utf-8"):
        d = json.loads(line)
        i = d.get("iter")
        if i is not None and it - width < i <= it and (d.get("select") or {}).get("prop"):
            p.append(d["select"]["prop"])
    return np.round(np.mean(p, 0), 3).tolist() if p else None


@torch.no_grad()
def out_scores(head, net, deck, field):
    """The out-choice alone: it reads only Drafter.view's plain deck rows, so a whole population is cheap."""
    ids = np.nonzero(deck)[0]
    width = LEAD + len(ids) + 1 + max(int((o > 0).sum()) for o in field)
    rows = [deck_tokens(ids, deck[ids], width, np.nonzero(o)[0], o[np.nonzero(o)[0]]) for o in field]
    card, kind, aux = (torch.from_numpy(np.stack(x)) for x in zip(*rows))
    B = card.shape[0]
    x = net.encode(card, kind, aux, torch.zeros(B, net.glob_f, dtype=torch.uint8), torch.zeros(B, 12 * net.slot_f, dtype=torch.uint8))[0].float()
    return ids, head.out(x[:, LEAD:LEAD + len(ids)].mean(0)).squeeze(-1).numpy().astype(np.float64)


def split_run(run_name, pool, info, top, boots=2000):
    """Each deck's out share and copy share by group, at each saved iteration."""
    run = ROOT / "runs/screens" / run_name
    cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
    group = np.full(pool.n, -1)
    names = sorted({c["name"] for c in pool.cards if c["superType"] == 2 and pool.allowed[c["id"]]})
    for c in pool.cards:
        if c["superType"] == 2 and pool.allowed[c["id"]]:
            group[c["id"]] = 0 if c["name"] in top else 1
    name_of = {c["id"]: c["name"] for c in pool.cards}
    out = {"run": run_name, "groups": {"top": len([n for n in names if n in top]), "low": len([n for n in names if n not in top])}}
    for tag, lo, hi in (("early", 0, 14), ("late", 30, 44)):
        rows, per_name, checked = [], {}, None
        for it in [0] + list(range(4, hi + 1, 5)):
            f = run / f"population_it{it:04d}.pt"
            if not (lo <= it <= hi and f.exists()):
                continue
            st = torch.load(f, map_location="cpu", weights_only=False)
            net = token_net(st["config"], info)
            net.load_state_dict(st["net"])
            net.eval()
            c0 = st["config"]
            dr = Drafter(pool, c0["d"], c0["heads"], cfg["swaps"], 0.0, "cpu", base=cfg["draft_base"], base_ent=cfg["draft_base_ent"])
            dr.head.load_state_dict(st["drafter"]["head"])
            rng = np.random.default_rng(1871 + it)
            decks = [np.array(pool.vector(x["deck"])) for x in st["population"]]
            for d, a in enumerate(st["population"]):
                others = [e for e in range(len(decks)) if e != d]
                field = [decks[e] for e in rng.choice(others, cfg["field_sample"], replace=False)]
                ids, sc = out_scores(dr.head, net, decks[d], field)
                if checked is None:                      # the same scores as the full view, on one deck
                    checked = float(np.abs(dr.view(net, decks[d], field).s - sc).max())
                c = decks[d][ids].astype(float)
                po = np.log(c) + sc
                po = np.exp(po - po.max())
                po /= po.sum()
                rows.append((a["id"], *[po[group[ids] == g].sum() for g in (0, 1)], *[c[group[ids] == g].sum() / c.sum() for g in (0, 1)]))
                for i, cid in enumerate(ids):
                    if group[cid] >= 0:
                        x = per_name.setdefault(name_of[cid], [0.0, 0.0])
                        x[0] += po[i]
                        x[1] += c[i] / c.sum()
        if not rows:
            continue
        a = np.array(rows, dtype=float)
        ratio = lambda m: (m[:, 1].mean() / m[:, 3].mean(), m[:, 2].mean() / m[:, 4].mean(), m[:, 1:3].sum(1).mean() / m[:, 3:5].sum(1).mean())
        top_r, low_r, all_r = ratio(a)
        by_id = [a[a[:, 0] == i] for i in np.unique(a[:, 0])]
        rng = np.random.default_rng(1872)
        gaps, tops, lows = [], [], []
        for _ in range(boots):
            m = np.concatenate([by_id[i] for i in rng.integers(len(by_id), size=len(by_id))])
            t, l, _a = ratio(m)
            tops.append(t)
            lows.append(l)
            gaps.append(l - t)
        n_decks = len(rows)
        out[tag] = {"decks": n_decks, "deck_ids": len(by_id), "same_as_full_view": checked,
                    "top12": {"ratio": round(top_r, 3), "se": round(float(np.std(tops)), 3), "out": round(float(a[:, 1].mean()), 4), "copies": round(float(a[:, 3].mean()), 4)},
                    "low30": {"ratio": round(low_r, 3), "se": round(float(np.std(lows)), 3), "out": round(float(a[:, 2].mean()), 4), "copies": round(float(a[:, 4].mean()), 4)},
                    "all_T_ratio": round(all_r, 3), "gap_low_minus_top": round(low_r - top_r, 3), "gap_se": round(float(np.std(gaps)), 3),
                    "by_name": {n: {"ratio": round(v[0] / v[1], 2), "copies_a_deck": round(60 * v[1] / n_decks, 2)} for n, v in sorted(per_name.items(), key=lambda kv: -kv[1][1])[:20]}}
    return out


def split_main(runs):
    pool = Pool()
    rp = RemotePool(1)
    info = rp.ask_all([{"cmd": "info"}])[0]
    rp.close()
    table = json.loads((ROOT / "runs/probe/C182-trainer-table-drafting/table.json").read_text(encoding="utf-8"))
    top = set(sorted(table, key=lambda n: -table[n])[:12])
    res = {"top12_names": sorted(top), "runs": [split_run(r, pool, info, top) for r in runs]}
    late = [r["late"] for r in res["runs"] if "late" in r]
    if len(late) == 2:
        res["band"] = "R-targets" if all(x["gap_low_minus_top"] >= 0.2 and x["gap_low_minus_top"] >= 2 * x["gap_se"] for x in late) else "R-blunt" if all(x["gap_low_minus_top"] < 0.1 and x["gap_low_minus_top"] + 2 * x["gap_se"] < 0.2 for x in late) else "between"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "split.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", action="store_true")
    ap.add_argument("--runs", default="C171-W-s48,C171-W-s49")
    ap.add_argument("--run", default="")
    ap.add_argument("--decks", type=int, default=16)
    ap.add_argument("--draws", type=int, default=30)
    ap.add_argument("--field", type=int, default=2)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--last", type=int, default=44)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    if a.split:
        return split_main(a.runs.split(","))
    pool = Pool()
    rp = RemotePool(1)
    info = rp.ask_all([{"cmd": "info"}])[0]
    rp.close()
    run = ROOT / "runs/screens" / a.run
    cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
    bonus = table_bonus(pool) if cfg.get("table") else None
    kinds = card_kinds(pool)
    rows = []
    OUT.mkdir(parents=True, exist_ok=True)
    for it in [0] + list(range(4, a.last + 1, 5)):
        f = run / f"population_it{it:04d}.pt"
        if not f.exists():
            continue
        st = torch.load(f, map_location="cpu", weights_only=False)
        net = token_net(st["config"], info)
        net.load_state_dict(st["net"])
        net.eval()
        c0 = st["config"]
        dr = Drafter(pool, c0["d"], c0["heads"], cfg["swaps"], 0.0, "cpu", h_in_floor=cfg["draft_h_in_floor"], group_p=cfg["draft_group_p"], base=cfg["draft_base"], base_ent=cfg["draft_base_ent"])
        dr.head.load_state_dict(st["drafter"]["head"])
        rng = np.random.default_rng(1870 + it)
        decks = [np.array(pool.vector(x["deck"])) for x in st["population"]]
        pick = rng.choice(len(decks), min(a.decks, len(decks)), replace=False)
        own, tilted, tr, t0 = [], [], [], []
        for d in pick:
            others = [e for e in range(len(decks)) if e != d]
            vw = dr.view(net, decks[d], [decks[e] for e in rng.choice(others, a.field, replace=False)])
            t0.append(shape(pool, vw.deck)[1])
            own.append(masses(vw, pool, kinds, None))
            if bonus is not None:
                tilted.append(masses(vw, pool, kinds, bonus))
            vw.bonus = bonus
            tr.append(trace(dr, vw, pool, kinds, a.draws, rng))
        mean = lambda xs: {k: round(float(np.mean([x[k] for x in xs])), 4) for k in xs[0]}
        o, t = mean(own), mean(tr)
        moved = t["pick_in"] + t["pick_out"] + t["group_in"] + t["group_out"]
        row = {"it": it, "decks": len(pick), "draws_each": a.draws, "T": round(float(np.mean(t0)), 2), "own": o, "with_bonus": mean(tilted) if tilted else None, "trace": t,
               "group_share_of_T_moved": round((t["group_in"] + t["group_out"]) / max(moved, 1e-9), 3),
               "net_by_pick": round(t["pick_in"] - t["pick_out"], 3), "net_by_group": round(t["group_in"] - t["group_out"], 3),
               "logged_prop_window": logged(a.run, it)}
        rows.append(row)
        print(json.dumps({k: row[k] for k in ("it", "T", "own", "with_bonus", "group_share_of_T_moved", "net_by_pick", "net_by_group", "logged_prop_window")}), flush=True)
        (OUT / f"{a.run}.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
