"""C182 with its Amendment 1 (runs/probe/C182-trainer-table-drafting/record.md): arm D against W at the same seed and iteration. Primary, at 29 and 44: survivors' Trainers per 25 iterations and median Trainers. Band at 44, both seeds: R-holds, survivors' Trainers at least +2 per 25 above W's and median Trainers at least +3 above W's; R-no, survivors' within 1 of W's or median within 1; between otherwise. Stop at 29: median Trainers at or below W's at both seeds. Beside it: G1, P/T/E, draw, T4, E, A7, rho_L, per-card copies against the lists'; Amendment 1, by the plain two-seed table's top 12 against the other 30: high and low copies on survivors and the slope of a deck's recent score per copy on each (given P), against W's, and from the ledger, accepted against proposed share for high-table cards, and the head's share with the bonus subtracted (D only: W logs no bonus). Seeds are replicates, not pairs. Past 44 W s48 is censored, so an extension compares with W s49 only. Amendment 2: the deck-out share in D's own games at it against iterations 0-6, with survivors' draw copies, R-learns-discipline or R-penalised. G3 without deck-outs and under search at 0 and 44 are g3_yardstick.py runs, read by c177_deckout.py.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c182_read.py [--it 29]
"""
import argparse
import json
from pathlib import Path

import numpy as np

import c165_read as C165
import c168_read as R
from c139_read import r3
from rl.decks import Pool
from rl.metagame import recent_score

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "runs/probe/C182-trainer-table-drafting"
W_STAGES = ROOT / "runs/probe/C171-table-drafting/stages.jsonl"
pool = Pool()


def stage(path, run, it):
    row = None
    for line in open(path, encoding="utf-8"):
        x = json.loads(line)
        if x["run"] == run and x["iter"] == it:
            row = x
    return row


def groups():
    c = json.loads((D / "table.json").read_text(encoding="utf-8"))
    top = sorted(c, key=lambda n: -c[n])[:12]
    return [R.TI[n] for n in top if n in R.TI], [R.TI[n] for n in c if n not in top and n in R.TI], top


def survivors(run, it, hi, lo, span=25):
    a, b = {x["id"]: x for x in R.snapshot(run, it - span)}, {x["id"]: x for x in R.snapshot(run, it)}
    both = sorted(set(a) & set(b))
    if len(both) < 2:
        return {"decks": len(both)}
    d = np.array([R.copies(b[k]["deck"]) - R.copies(a[k]["deck"]) for k in both])
    f = lambda ix: {"change": r3(float(d[:, ix].sum(1).mean())), "se": r3(float(d[:, ix].sum(1).std(ddof=1) / len(both) ** 0.5))}
    level = np.array([R.copies(b[k]["deck"]) for k in both])
    return {"decks": len(both), "high": f(hi), "low": f(lo), "high_copies": r3(float(level[:, hi].sum(1).mean())), "low_copies": r3(float(level[:, lo].sum(1).mean()))}


def slope(run, it, hi, lo):
    pop = R.snapshot(run, it)
    c = np.array([R.copies(x["deck"]) for x in pop])
    p = np.array([sum(R.CARD[q]["superType"] == 1 for q in x["deck"]) for x in pop], dtype=float)
    y = np.array([recent_score(x, 0.0) for x in pop], dtype=float)
    X = np.c_[np.ones(len(pop)), c[:, hi].sum(1), c[:, lo].sum(1), p - p.mean()]
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ b
    cov = np.linalg.pinv(X.T @ X) * res.var(ddof=X.shape[1])
    return {"high": r3(float(b[1])), "se_high": r3(float(cov[1, 1] ** 0.5)), "low": r3(float(b[2])), "se_low": r3(float(cov[2, 2] ** 0.5)), "decks": len(pop)}


def ledger(run, it, names, span=15):
    bare = {i: n.rsplit(" ", 1)[0] for i, n in pool.full_name.items()}
    ids = {str(i) for i, b in bare.items() if b in names}
    trainers = {str(c["id"]) for c in pool.cards if c["superType"] == 2}
    acc, prop, own, bonus, n = 0.0, 0.0, [], [], 0
    acc_t, prop_t = 0.0, 0.0
    for line in open(run / "log.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if not it - span < d.get("iter", -1) <= it:
            continue
        c = (d.get("select") or {}).get("card")
        if c:
            pi, ai = c.get("prop_in", {}), c.get("acc_in", c.get("acc_net", {}))
            prop += sum(v for k, v in pi.items() if k in ids)
            prop_t += sum(v for k, v in pi.items() if k in trainers)
            acc += sum(max(v, 0) for k, v in ai.items() if k in ids)
            acc_t += sum(max(v, 0) for k, v in ai.items() if k in trainers)
            n += 1
        t = d.get("table_head")
        if t:
            own.append(t["own"])
            bonus.append(t["with_bonus"])
    return {"iterations": n, "proposed_share_of_trainers": r3(prop / max(1.0, prop_t)), "accepted_share_of_trainers": r3(acc / max(1.0, acc_t)), "head_own": r3(float(np.mean(own))) if own else None, "head_with_bonus": r3(float(np.mean(bonus))) if bonus else None}


def deck_out_share(run, lo, hi):
    tot, seen = {}, {}
    for line in open(run / "log.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if lo <= d.get("iter", -1) <= hi and d.get("endings"):
            seen[d["iter"]] = d["endings"]
    for e in seen.values():
        for k, v in e.items():
            tot[k] = tot.get(k, 0) + v
    return tot.get("deck-out", 0) / max(1, sum(tot.values())), len(seen)


def discipline(run, it, st):
    """Amendment 2 (#879): the deck-out share in a run's own games at it (the 5 iterations up to it) against iterations 0-6, with survivors' draw copies. R-learns-discipline: the share at or under half of 0-6's, with draw not falling by more than 1 per 25. R-penalised: the share not under three quarters of it, with draw falling 1.5 per 25 or more. Between otherwise."""
    s0, n0 = deck_out_share(run, 0, 6)
    s1, n1 = deck_out_share(run, it - 4, it)
    draw = st["survivors"]["draw"]["change"] if st.get("survivors") else None
    band = None
    if draw is not None:
        band = "R-learns-discipline" if s1 <= 0.5 * s0 and draw >= -1 else "R-penalised" if s1 >= 0.75 * s0 and draw <= -1.5 else "between"
    trail = [r3(deck_out_share(run, a, a + 4)[0]) for a in range(0, it - 3, 5)]
    return {"share_0_6": r3(s0), "share_at_it": r3(s1), "iterations": [n0, n1], "draw_on_survivors_per_25": draw, "band": band, "by_5_iterations": trail}


def per_card(run, it, top):
    pop = R.snapshot(run, it)
    c = np.array([R.copies(x["deck"]) for x in pop]).mean(0)
    target = C165.lists_mean_copies(R.TN)
    order = np.argsort(-c)[:10]
    return {"top_10": [(R.TN[i], r3(float(c[i])), r3(float(target[i]))) for i in order], "rho_with_lists": r3(C165.spearman(c, target)), "high_copies_a_deck": r3(float(sum(c[R.TI[n]] for n in top if n in R.TI)))}


def read(it):
    hi, lo, top = groups()
    out = {"iter": it, "seeds": {}}
    for s in (48, 49):
        d_run, w_run = ROOT / f"runs/screens/C182-D-s{s}", ROOT / f"runs/screens/C171-W-s{s}"
        ds, ws = stage(D / "stages.jsonl", f"C182-D-s{s}", it), stage(W_STAGES, f"C171-W-s{s}", it)
        if not ds or not ws:
            out["seeds"][s] = {"not_ready": {"D": bool(ds), "W": bool(ws)}}
            continue
        row = {}
        for tag, st in (("D", ds), ("W", ws)):
            row[tag] = {"median": st["median_pte"], "population": st["population"]["pte"], "G1_mean5": st["G1_mean5"], "T4": st["population"]["T4"], "draw": st["population"]["draw"], "E": st["population"]["E"], "A7": st["population"].get("A7"), "rho_L": st["population"].get("rho_L"), "wall": st.get("wall_share"), "survivors": st["survivors"], "errors": st["errors"], "games": st["games"]}
        sd, sw = ds["survivors"]["trainers"]["change"], ws["survivors"]["trainers"]["change"]
        row["survivors_D_minus_W"] = r3(sd - sw)
        row["median_T_D_minus_W"] = ds["median_pte"][1] - ws["median_pte"][1]
        row["discipline"] = {"D": discipline(d_run, it, ds), "W": discipline(w_run, it, ws)}
        row["beside"] = {"D": {"survivors": survivors(d_run, it, hi, lo), "slope": slope(d_run, it, hi, lo), "ledger": ledger(d_run, it, top), "cards": per_card(d_run, it, top)},
                         "W": {"survivors": survivors(w_run, it, hi, lo), "slope": slope(w_run, it, hi, lo), "ledger": ledger(w_run, it, top), "cards": per_card(w_run, it, top)}}
        out["seeds"][s] = row
    both = [out["seeds"][s] for s in (48, 49) if "survivors_D_minus_W" in out["seeds"][s]]
    if len(both) == 2:
        if it == 29:
            out["stop_at_29"] = all(x["median_T_D_minus_W"] <= 0 for x in both)
        if it == 44:
            holds = all(x["survivors_D_minus_W"] >= 2 and x["median_T_D_minus_W"] >= 3 for x in both)
            no = all(abs(x["survivors_D_minus_W"]) <= 1 or abs(x["median_T_D_minus_W"]) <= 1 for x in both)
            out["band"] = "R-holds" if holds else "R-no" if no else "between"
    (D / f"read_{it}.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--it", type=int, default=29)
    a = ap.parse_args()
    print(json.dumps(read(a.it), default=float))


if __name__ == "__main__":
    main()
