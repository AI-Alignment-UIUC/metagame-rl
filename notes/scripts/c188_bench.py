"""C188 stage 1, cut down (runs/probe/C188-head-out-signal/record.md, Amendment 1): at calibrated noise, how far does the out bonus alone get, and what size of real signal would W's movement need? Ported from the auditor's audit_entropy.py (A164). A fresh head.out replayed on W's saved decks and encoders with simulated results, no games, GPU hidden; decks don't respond to the replayed head, the bench's main limit.
The out layer's gradient is exact without the in side: out_lp doesn't read the in logits, Adam is per parameter, and W's grad norm never reaches the clip (logged under 0.3). The one approximation is a group change's size, which the real sample caps by the incoming card: here left[j], capped at 3 copies.
  PYTHONPATH=".;notes/scripts" .venv/Scripts/python notes/scripts/c188_bench.py --views      H for W's decks at every saved iteration (#912's fields), once
  ... --calibrate   the out layer's share of the whole head's gradient on simulated results, so W's logged norm gives the out norm to match
  ... --all [--procs 6] [--seeds 3]   every row of ROWS, a finished replay skipped; ... --read   the fidelity gate, the record's bands, results.csv
Noise knobs: rho, a candidate's game copies its paired unchanged game with that chance, as the paired slots share a deal, a plant's mean shift kept by raising it to delta / (1 - rho) on the games that don't copy; a negative rho means tau = -rho, a per-candidate shift of its win chance, N(0, tau^2).
"""
import argparse
import csv
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
import numpy as np
import torch

import c188_stage0 as S0
from c184_neutral_test import ROOT, card_kinds
from c187_caps import LEAD, deck_tokens, load_weights
from rl.decks import Pool
from rl.draft import DraftHead, Drafter, rloo
from rl.remote import RemotePool

OUT = S0.OUT / "stage1"
RUNS = ("C171-W-s48", "C171-W-s49")
SAVED = (0, 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54)     # W's own read to 54 at both seeds, for k's trajectory
STEPS = 55                                               # W's population at it has had it + 1 updates
READS = (34, 39, 44)
GAMES = 20                                               # a side, candidate and unchanged: W's about 20.2 a candidate
SWAPS, GROUP_P, LR, BETA = 6, 0.3, 3e-4, 0.01            # W's recipe
W_A = {"C171-W-s48": 1.367, "C171-W-s49": 1.444}         # #912's A cell
W_G = {"C171-W-s48": (-0.671, 0.009), "C171-W-s49": (-0.979, 0.011)}   # stage 0's gamma, SE
W_H = {"C171-W-s48": 3.0168, "C171-W-s49": 3.0448}       # W's logged h_out at iteration 0
W_NORM = {"C171-W-s48": 0.185, "C171-W-s49": 0.205}      # W's logged whole-head grad norm, mean over 0-44
# arm, bonus, plant, plant size, rho. Z is the auditor's zero-advantage arm: the bonus with no noise at all.
ARMS = {"N": ("entropy", None, 0), "N0": ("none", None, 0), "NK": ("kl", None, 0), "Z": ("entropy", "zero", 0),
        "PoT": ("entropy", "T", 0.005), "PoE": ("entropy", "E", -0.005), "Pg": ("entropy", "g", -0.012),
        "PoT2": ("entropy", "T", 0.01), "PoE2": ("entropy", "E", -0.01), "PoT0": ("none", "T", 0.005), "PoE0": ("none", "E", -0.005), "Pg0": ("none", "g", -0.012),
        "PoT02": ("none", "T", 0.01), "PoE02": ("none", "E", -0.01), "Pg7": ("entropy", "g", -0.007), "Pg70": ("none", "g", -0.007)}
RECORD_ARMS = ("N", "N0", "NK", "PoT", "PoE", "Pg")
W_K = {"C171-W-s48": {44: -0.99, 49: -1.32, 54: -1.60}, "C171-W-s49": {44: -1.03, 54: -1.29}}   # A165's fitted k


def views_path(run_name):
    return OUT / "views" / f"{run_name}_H.pt"


@torch.no_grad()
def h_of(net, deck, field):
    ids = np.nonzero(deck)[0]
    width = LEAD + len(ids) + 1 + max(int((o > 0).sum()) for o in field)
    rows = [deck_tokens(ids, deck[ids], width, np.nonzero(o)[0], o[np.nonzero(o)[0]]) for o in field]
    card, kind, aux = (torch.from_numpy(np.stack(x)) for x in zip(*rows))
    B = card.shape[0]
    x = net.encode(card, kind, aux, torch.zeros(B, net.glob_f, dtype=torch.uint8), torch.zeros(B, 12 * net.slot_f, dtype=torch.uint8))[0].float()
    return ids, x[:, LEAD:LEAD + len(ids)].mean(0).clone()


def build_views():
    torch.set_num_threads(4)
    pool = Pool()
    rp = RemotePool(1)
    info = rp.ask_all([{"cmd": "info"}])[0]
    rp.close()
    (OUT / "views").mkdir(parents=True, exist_ok=True)
    for name in RUNS:
        run = ROOT / "runs/screens" / name
        cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
        res, d_model = {}, None
        for it in SAVED:
            st, net, _ = load_weights(run, it, pool, info, cfg)
            d_model = st["config"]["d"]
            rng = np.random.default_rng(1873 + it)
            decks = [np.array(pool.vector(x["deck"])) for x in st["population"]]
            rows = []
            for d, a in enumerate(st["population"]):
                others = [e for e in range(len(decks)) if e != d]
                ids, H = h_of(net, decks[d], [decks[e] for e in rng.choice(others, cfg["field_sample"], replace=False)])
                rows.append((a["id"], ids, decks[d][ids].astype(np.int64), H))
            res[it] = rows
        torch.save({"d": d_model, "views": res}, views_path(name))
        print(name, "saved", flush=True)


def read_cell(out, rows, kinds):
    cell = []
    with torch.no_grad():
        for aid, ids, cnt, H in rows:
            cell.append((aid, ids, cnt.astype(float), kinds[ids], out(H).squeeze(-1).numpy().astype(np.float64)))
    r = S0.ratios(cell, lambda c, k, s: s)
    g, ot, oe = S0.fit(cell)
    return {"P": float(r[0]), "T": float(r[1]), "E": float(r[2]), "gamma": float(g), "T_minus_E": float(ot - oe)}


def draw_out(cnt, sn, rng):
    """The out half of Drafter.sample: picks, the left vector before each, and copies moved by group changes."""
    left = cnt.astype(np.float64).copy()
    js, lefts, group = [], [], 0
    for _ in range(SWAPS):
        ok = left > 0
        if not ok.any():
            break
        lw = np.where(ok, np.log(np.maximum(left, 1)) + sn, -np.inf)
        p = np.exp(lw - lw.max())
        p /= p.sum()
        j = int(rng.choice(len(p), p=p))
        js.append(j)
        lefts.append(left.copy())
        left[j] -= 1
        if rng.random() < GROUP_P:
            n = min(left[j], 3)
            left[j] -= n
            group += int(n)
    return js, lefts, group, cnt - left


def replay(arm, run_name, seed, rho):
    torch.set_num_threads(1)
    pool = Pool()
    kinds = card_kinds(pool)
    data = torch.load(views_path(run_name), map_location="cpu", weights_only=False)
    bonus, plant, size = ARMS[arm]
    torch.manual_seed(1880 + seed)                       # the same fresh head across arms, by replay seed
    out = DraftHead(pool.n, data["d"], 4).out
    opt = torch.optim.Adam(out.parameters(), lr=LR)
    rng = np.random.default_rng([1880, list(ARMS).index(arm), RUNS.index(run_name), seed, round(rho * 100) % 1000])
    res = {"arm": arm, "run": run_name, "seed": seed, "rho": rho, "bonus": bonus, "plant": plant, "size": size, "traj": [], "reads": {}}
    for t in range(STEPS):
        pop = data["views"][max(i for i in SAVED if i <= t)]
        if t == 0:
            res["step0"] = read_cell(out, pop, kinds)
        store, advs = [], []
        for aid, ids, cnt, H in pop:
            s = out(H).squeeze(-1)
            js, lefts, group, moved = draw_out(cnt, s.detach().numpy().astype(np.float64), rng)
            kind = kinds[ids]
            delta = 0.0
            if plant == "T":
                delta = size * moved[kind == 2].sum()
            elif plant == "E":
                delta = size * moved[kind == 3].sum()
            elif plant == "g":
                delta = size * (len(js) + group)                # Amendment 4: per copy moved, picks and group changes
            if plant == "zero":
                z = np.zeros(2 * GAMES)
            else:
                u = rng.integers(0, 2, GAMES).astype(np.float64)
                tau, copy = max(-rho, 0.0), max(rho, 0.0)
                fresh = rng.binomial(1, float(np.clip(0.5 + delta / (1 - copy) + tau * rng.normal(), 0, 1)), GAMES).astype(np.float64)
                z = np.r_[np.where(rng.random(GAMES) < copy, u, fresh), u]
            advs.append(rloo(z, np.zeros(len(z))))
            store.append((s, np.array(js), np.array(lefts), cnt))
        allv = np.concatenate(advs)
        scale = allv.std() if allv.std() > 0 else 1.0
        n = allv.size
        loss_r, loss_b = 0.0, 0.0
        h_out = 0.0
        for (s, js, lefts, cnt), adv in zip(store, advs):
            L_ = torch.from_numpy(lefts).float()
            lw = torch.where(L_ > 0, torch.log(L_.clamp(min=1)) + s[None], torch.full_like(L_, -1e9))
            lp = (lw.gather(1, torch.from_numpy(js)[:, None]).squeeze(1) - torch.logsumexp(lw, 1)).sum()
            c = torch.from_numpy(cnt).float()
            po = torch.log_softmax(s + torch.log(c), 0)
            ho = -(po.exp() * po).sum()
            h_out += float(ho.detach()) / len(pop)
            term = -(po.exp() * (po - torch.log(c / c.sum()))).sum() if bonus == "kl" else ho if bonus == "entropy" else 0.0 * ho
            loss_r = loss_r - float(adv[:GAMES].sum() / scale) * lp / n      # the unchanged half has lp 0
            loss_b = loss_b - BETA * term / len(pop)
        params = list(out.parameters())
        g_r = torch.autograd.grad(loss_r, params, retain_graph=True, allow_unused=True) if isinstance(loss_r, torch.Tensor) else [None] * len(params)
        g_b = torch.autograd.grad(loss_b, params, retain_graph=True, allow_unused=True)
        flat = lambda gs: torch.cat([(torch.zeros_like(p) if x is None else x).flatten() for p, x in zip(params, gs)])
        fr, fb = flat(g_r), flat(g_b)
        cos = float(torch.nn.functional.cosine_similarity(fr, fb, dim=0)) if fr.norm() > 0 and fb.norm() > 0 else 0.0
        opt.zero_grad()
        for p, x, y in zip(params, g_r, g_b):
            p.grad = (torch.zeros_like(p) if x is None else x.clone()) + (torch.zeros_like(p) if y is None else y)
        opt.step()
        res["traj"].append({"t": t, "h_out": round(h_out, 4), "reinforce": round(float(fr.norm()), 5), "bonus": round(float(fb.norm()), 5), "cos": round(cos, 4)})
        if t in SAVED:
            res["reads"][t] = read_cell(out, data["views"][t], kinds)
    res["A_T"] = float(np.mean([res["reads"][t]["T"] for t in READS]))
    res["A_E"] = float(np.mean([res["reads"][t]["E"] for t in READS]))
    res["A_gamma"] = float(np.mean([res["reads"][t]["gamma"] for t in READS]))
    res["out_norm"] = float(out[-1].weight.norm())
    (OUT / "replays").mkdir(parents=True, exist_ok=True)
    (OUT / "replays" / f"{arm}_{run_name}_{seed}_rho{rho}.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return arm, run_name, seed, rho, round(res["A_T"], 3), round(res["A_gamma"], 3)


def calibrate():
    """The out layer's share of the whole head's squared gradient, on simulated results with the real update: 12 decks at 0 and 44 of each W seed, 8 batches a cell, own head, rho 0."""
    torch.set_num_threads(4)
    pool = Pool()
    rp = RemotePool(1)
    info = rp.ask_all([{"cmd": "info"}])[0]
    rp.close()
    res = []
    for name in RUNS:
        run = ROOT / "runs/screens" / name
        cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
        for it in (0, 44):
            st, net, _ = load_weights(run, it, pool, info, cfg)
            dr = Drafter(pool, st["config"]["d"], st["config"]["heads"], cfg["swaps"], cfg["draft_lr"], "cpu", h_in_floor=cfg["draft_h_in_floor"], group_p=cfg["draft_group_p"], base=cfg["draft_base"], base_ent=cfg["draft_base_ent"])
            dr.head.load_state_dict(st["drafter"]["head"])
            rng = np.random.default_rng(1881 + it)
            decks = [np.array(pool.vector(x["deck"])) for x in st["population"]]
            views = []
            for d in rng.choice(len(decks), 12, replace=False):
                others = [e for e in range(len(decks)) if e != d]
                views.append(dr.view(net, decks[d], [decks[e] for e in rng.choice(others, cfg["field_sample"], replace=False)]))
            params = list(dr.head.parameters())
            ids_out = {id(p) for p in dr.head.out.parameters()}
            shares, norms = [], []
            for _ in range(8):
                batch = []
                for vw in views:
                    x = dr.sample(vw, rng)
                    same = {"deck": vw.deck, "ev_j": [], "ev_c": [], "ev_mask": [], "ev_left": [], "ev_T": [], "logp": 0.0}
                    z = rng.integers(0, 2, 2 * GAMES).astype(np.float64)
                    batch.append((vw, [x] * GAMES + [same] * GAMES, rloo(z, np.zeros(len(z)))))
                sd = np.concatenate([a for _, _, a in batch]).std()
                n = sum(len(a) for _, _, a in batch)
                dr.opt.zero_grad()
                for vw, samples, a in batch:
                    lp = dr.log_prob(vw, samples)[0]
                    (-(torch.tensor(a / sd, dtype=torch.float32) * lp).sum() / n).backward()
                o2 = sum(float(p.grad.pow(2).sum()) for p in params if id(p) in ids_out and p.grad is not None)
                a2 = sum(float(p.grad.pow(2).sum()) for p in params if p.grad is not None)
                shares.append(o2 / a2)
                norms.append(a2 ** .5)
            res.append({"run": name, "it": it, "out_share_of_squared": float(np.mean(shares)), "se": float(np.std(shares) / len(shares) ** .5), "whole_norm_12_decks": float(np.mean(norms))})
            print(res[-1], flush=True)
    (OUT / "calibrate.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


def run_all(procs, seeds, arms, rhos):
    jobs = [(a, r, s, h) for h in rhos for a in arms for r in RUNS for s in range(1, seeds + 1) if not (OUT / "replays" / f"{a}_{r}_{s}_rho{h}.json").exists()]
    print(len(jobs), "replays", flush=True)
    with ProcessPoolExecutor(max_workers=procs) as ex:
        for f in as_completed({ex.submit(replay, *j): j for j in jobs}):
            print(time.strftime("%H:%M:%S"), *f.result(), flush=True)


def read_all():
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in (OUT / "replays").glob("*.json")]
    groups = {}
    for v in rows:
        groups.setdefault((v["rho"], v["arm"], v["run"]), []).append(v)
    se = lambda v: float(np.std(v, ddof=1) / len(v) ** .5) if len(v) > 1 else float("nan")
    tab = {}
    for (rho, arm, run), x in sorted(groups.items()):
        T, E, G = [v["A_T"] for v in x], [v["A_E"] for v in x], [v["A_gamma"] for v in x]
        tab[rho, arm, run] = {"rho": rho, "arm": arm, "run": run, "bonus": x[0]["bonus"], "plant": x[0]["plant"], "size": x[0]["size"], "replays": len(x), "T": np.mean(T), "T_se": se(T), "E": np.mean(E), "gamma": np.mean(G), "gamma_se": se(G),
                              "h_out_0": np.mean([v["traj"][0]["h_out"] for v in x]), "h_out_44": np.mean([v["traj"][44]["h_out"] for v in x]), **{f"k_{it}": np.mean([v["reads"][str(it)]["gamma"] for v in x]) for it in (14, 29, 44, 54)}, "reinforce_norm": np.mean([t["reinforce"] for v in x for t in v["traj"]]), "bonus_norm": np.mean([t["bonus"] for v in x for t in v["traj"]]),
                              "cos": np.mean([t["cos"] for v in x for t in v["traj"]]), "out_norm": np.mean([v["out_norm"] for v in x]), "step0_T": np.mean([v["step0"]["T"] for v in x])}
    with open(OUT / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(next(iter(tab.values()))))
        w.writeheader()
        for v in tab.values():
            w.writerow({k: round(float(x), 4) if isinstance(x, (float, np.floating)) else x for k, x in v.items()})
    cal = json.loads((OUT / "calibrate.json").read_text(encoding="utf-8"))
    target = {r: W_NORM[r] * float(np.mean([c["out_share_of_squared"] for c in cal if c["run"] == r])) ** .5 for r in RUNS}
    rungs = sorted({k[0] for k in tab if all((k[0], "N", r) in tab for r in RUNS)})
    gap = {h: sum(abs(tab[h, "N", r]["reinforce_norm"] - target[r]) for r in RUNS) for h in rungs}
    best = min(gap, key=gap.get)
    print("target out norm", {r[-3:]: round(target[r], 4) for r in RUNS}, "N's by rung", {h: [round(float(tab[h, "N", r]["reinforce_norm"]), 4) for r in RUNS] for h in rungs}, "calibrated rung", best)
    out = {"calibrated_rung": best}
    for rho in sorted({k[0] for k in tab}):
        T = lambda a, r: tab[rho, a, r]["T"]
        if not all((rho, a, r) in tab for a in RECORD_ARMS for r in RUNS):
            continue
        gate = all(abs(tab[rho, a, r]["step0_T"] - 1) <= 0.005 for a in RECORD_ARMS for r in RUNS) and all(abs(tab[rho, "N", r]["h_out_0"] - W_H[r]) <= 0.03 for r in RUNS)
        if all(abs(T("N", r) - W_A[r]) <= 0.10 and T("N0", r) <= 1.08 and T("NK", r) <= 1.08 for r in RUNS):
            band = "R-entropy"
        elif all(T("N0", r) >= 1.20 for r in RUNS):
            band = "R-noise"
        elif all(T("N", r) <= 1.08 and T("N0", r) <= 1.08 and T("NK", r) <= 1.08 and max(T(p, r) for p in ("PoT", "PoE", "Pg")) >= 1.20 for r in RUNS):
            band = "R-signal"
        else:
            band = "R-unexplained"
        out[str(rho)] = {"gate": gate, "band": band, "plants_landing": [p for p in ("PoT", "PoE", "Pg") if all(abs(T(p, r) - W_A[r]) <= 0.10 and abs(tab[rho, p, r]["gamma"] - W_G[r][0]) <= 2 * max(W_G[r][1], tab[rho, p, r]["gamma_se"]) for r in RUNS)]}
    print(json.dumps(out))
    print("W's k", W_K)
    for k in sorted(tab, key=str):
        v = tab[k]
        print(k[0], k[1], k[2][-3:], f"T {v['T']:.3f} ({v['T_se']:.3f}) E {v['E']:.3f} k {v['gamma']:.3f} ({v['gamma_se']:.3f}) k14,29,44,54 {v['k_14']:.2f} {v['k_29']:.2f} {v['k_44']:.2f} {v['k_54']:.2f} h_out {v['h_out_0']:.3f}->{v['h_out_44']:.3f} reinforce {v['reinforce_norm']:.4f} bonus {v['bonus_norm']:.4f} cos {v['cos']:+.3f} norm {v['out_norm']:.3f}")
    (OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--views", action="store_true")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--time", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--arms", default=",".join(RECORD_ARMS))
    ap.add_argument("--rhos", default="0.0")
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--read", action="store_true")
    a = ap.parse_args()
    if a.views:
        return build_views()
    if a.calibrate:
        return calibrate()
    if a.time:
        t0 = time.time()
        print(replay("N", RUNS[0], 1, 0.0), f"{time.time() - t0:.0f} s")
        return
    if a.all:
        return run_all(a.procs, a.seeds, a.arms.split(","), [float(x) for x in a.rhos.split(",")])
    if a.read:
        return read_all()


if __name__ == "__main__":
    main()
