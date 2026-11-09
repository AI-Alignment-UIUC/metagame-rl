"""C108 (runs/probe/C108-pluspower-policy/record.md): does the pilot's PlusPower decision respond to whether it can attack?
CPU only, evaluation only. Two stages:
  collect   P x P bench games (bench_matchups.json, round rule 20-45, deckoutWin 1) played by the start pilot on CPU through a
            RemotePool; every main-phase decision where "play PlusPower" (verb 5 on a PlusPower id) is legal is stored.
  readout   each pilot's logits recomputed offline on those stored observations -> readouts 1-3 and the bands.
Conversion flag (approximate, from the stored state and the seat's actual attack later that turn, not the engine's damage): the
attack's printed damage (numeric only), x2 on Weakness, -30 on Resistance, +10 per PlusPower already attached, against the
Defending Pokemon's HP left in the slots features; conversion = damage < left <= damage + 10.
  CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=. .venv/Scripts/python.exe notes/scripts/c108_probe.py [--minutes 15] [--skip-collect]
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
torch.set_num_threads(2)
from rl.gpu_matrix import load_policy                  # noqa: E402
from rl.remote import RemotePool, trim_inputs, TOKEN_INPUTS    # noqa: E402
from rl.rollouts import read_rollout                   # noqa: E402

OUT = ROOT / "runs/probe/C108-pluspower-policy"
PILOTS = {"start": "ar/data/start.pt", "arm0_s1": "runs/probe/BENCH/arm-arm0-s1/pilot.pt", "arm0_s2": "runs/probe/BENCH/arm-arm0-s2/pilot.pt"}
SHAPE = {"tok_card": 256, "tok_kind": 256, "tok_aux": 256, "glob": 82, "slots": 240, "cand": 768}
TRAINER, ATTACK, SLOT_F = 5, 7, 20
TABLE = json.load(open(ROOT / "notes/data/cards/pool.json", encoding="utf-8"))["cards"]
PP = {c["id"] for c in TABLE if c["name"] == "PlusPower"}
names = []
for c in TABLE:
    for a in list(c["attacks"]) + list(c["powers"]):
        if a["name"] not in names:
            names.append(a["name"])
NAME_ID = {n: i + 1 for i, n in enumerate(names)}       # as env/tokens.js numbers attack and Power names


def attack_damage(atk_card, name_id, def_card, left, plus):
    """Estimated damage of the named attack on the Defending Pokemon (None if the printed damage isn't a plain number)."""
    c = TABLE[atk_card - 1]
    a = [x for x in c["attacks"] if NAME_ID.get(x["name"]) == name_id]
    if not a or not str(a[0]["damageText"]).isdigit() or a[0]["damage"] <= 0:
        return None
    d = a[0]["damage"]
    t, dc = np.array(c["types"]), TABLE[def_card - 1]
    if (t * np.array(dc["weakness"])).sum() > 0:
        d *= 2
    if (t * np.array(dc["resistance"])).sum() > 0:
        d -= 30
    return max(0, d) + 10 * plus


def rows_of(path, gbase):
    """PlusPower-playable main-phase decisions of one rollout file."""
    r = read_rollout(path)
    T = len(r["action"])
    camel = {"tok_card": "tokCard", "tok_kind": "tokKind", "tok_aux": "tokAux", "glob": "glob", "slots": "slots", "cand": "cand"}
    o = {k: r["obs." + camel[k]].reshape(T, -1) for k in TOKEN_INPUTS if k != "n_cand"}
    o["n_cand"] = r["obs.nCand"].reshape(T)
    act, traj, off, ids = r["action"].astype(np.int64), r["traj"].astype(np.int64), r["legal_offsets"], r["legal_ids"]
    cand = o["cand"].reshape(T, -1, 6)
    glob = o["glob"]
    by_traj = {}
    for t in range(T):
        by_traj.setdefault(int(traj[t]), []).append(t)
    out = []
    for k, ts in by_traj.items():
        for j, t in enumerate(ts):
            if glob[t, 48] == 0:        # a prompt row (the "no prompt" flag is off), not the main phase
                continue
            legal = ids[off[t]:off[t + 1]].astype(np.int64)
            verbs, cards = cand[t, legal, 0], cand[t, legal, 1]
            pp = [i for i, (v, c) in enumerate(zip(verbs, cards)) if v == TRAINER and c in PP]
            if not pp:
                continue
            turn = int(glob[t, 0])
            atk_idx = [i for i, v in enumerate(verbs) if v == ATTACK]
            sl = o["slots"][t]
            def_card, hp, dm = int(o["tok_card"][t, 7]), int(sl[6 * SLOT_F + 2]) * 2.5, int(sl[6 * SLOT_F + 3]) * 2.5
            plus = int(((o["tok_kind"][t] == 5) & (o["tok_aux"][t] == 0) & np.isin(o["tok_card"][t], list(PP))).sum())
            conv, attacked = False, False
            for t2 in ts[j + 1:]:                 # the seat's actual attack later in this turn
                if int(o["glob"][t2, 0]) != turn:
                    break
                ch = cand[t2, act[t2]]
                if ch[0] == ATTACK:
                    attacked = True
                    d = attack_damage(int(ch[1]), int(ch[4]), def_card, hp - dm, plus) if def_card else None
                    conv = d is not None and d < hp - dm <= d + 10
                    break
            out.append({"i": t, "game": gbase + k // 2, "seat": k % 2, "turn": turn, "legal": legal, "pp_opt": pp[0],
                        "attack_present": bool(atk_idx), "attacked": attacked, "conv": conv, "plus_attached": plus,
                        "obs": {kk: o[kk][t] for kk in o}})
    return out


def collect(minutes):
    model, _ = load_policy(str(ROOT / PILOTS["start"]), "cpu")
    mt = json.loads((ROOT / "runs/probe/BENCH/bench_matchups.json").read_text(encoding="utf-8"))
    tmp = OUT / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    rows, t0, rnd, games = [], time.time(), 0, 0
    pool = RemotePool(2)
    try:
        while True:
            msgs = [{"cmd": "collect", "encoding": "tokens", "transitions": 3000, "concurrency": 24, "seed": 1000 + 10 * rnd + w,
                     "roundTurns": [20, 45], "deckoutWin": 1.0, "matchups": mt, "opponents": [{"spec": "self", "weight": 1.0}],
                     "out": str(tmp / f"roll{rnd}_{w}.bin"), "history": 0, "chain": 0, "canon": 0} for w in range(2)]
            rep = pool.collect(msgs, {0: model.eval()}, "cpu")
            for w, r in enumerate(rep):
                rows += rows_of(r["out"], (rnd * 2 + w) * 10**6)
            rnd += 1
            n_att = sum(r["attack_present"] for r in rows)
            print(f"round {rnd}: {len(rows)} PlusPower-playable, {n_att} attack-present, {(time.time() - t0) / 60:.1f} min", flush=True)
            if (len(rows) >= 400 and n_att >= 100 and time.time() - t0 > 60 * minutes * 0.5) or time.time() - t0 > 60 * minutes:
                break
    finally:
        pool.close()
    st = {"meta": {"minutes": (time.time() - t0) / 60, "rounds": rnd}, "rows": rows}
    torch.save(st, OUT / "states.pt")
    return st


def auc(y, s):
    o = np.argsort(s)
    ranks = np.empty(len(s)); ranks[o] = np.arange(1, len(s) + 1)
    for v in np.unique(s):                     # ties: average rank
        m = s == v
        if m.sum() > 1:
            ranks[m] = ranks[m].mean()
    n1, n0 = y.sum(), (1 - y).sum()
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")


def pilot_outputs(path, rows):
    """-> P(play PlusPower) per row and the pooled encoder state per row."""
    m, _ = load_policy(str(ROOT / path), "cpu")
    m.eval()
    P, Z = [], []
    with torch.no_grad():
        for s in range(0, len(rows), 64):
            ch = rows[s:s + 64]
            ins = [torch.from_numpy(np.stack([r["obs"][k] for r in ch])) for k in TOKEN_INPUTS]
            ins = trim_inputs(ins, m)
            lg = m(*ins)[0]
            x, mask = m.encode(*ins[:5])[:2]
            z = (x * mask[..., None]).sum(1) / mask.sum(1, keepdim=True)
            for i, r in enumerate(ch):
                P.append(float(lg[i, torch.from_numpy(r["legal"])].double().softmax(0)[r["pp_opt"]]))
            Z.append(z.float().numpy())
    return np.array(P), np.concatenate(Z)


def boot(game, f, n=2000, seed=0):
    """95% CI of f(index array) resampling games."""
    rng = np.random.default_rng(seed)
    ug = np.unique(game)
    idx = {g: np.where(game == g)[0] for g in ug}
    vals = []
    for _ in range(n):
        ii = np.concatenate([idx[g] for g in rng.choice(ug, len(ug))])
        v = f(ii)
        if v == v:
            vals.append(v)
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def mean_(a, ii):
    return float(a[ii].mean()) if len(ii) else float("nan")


def probe(Z, y, game):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    ug = np.unique(game)
    fold = {g: i % 5 for i, g in enumerate(np.random.default_rng(0).permutation(ug))}
    f = np.array([fold[g] for g in game])
    pred, sc = np.zeros(len(y)), np.zeros(len(y))
    for k in range(5):
        tr, te = f != k, f == k
        if len(np.unique(y[tr])) < 2:
            return None
        s = StandardScaler().fit(Z[tr])
        c = LogisticRegression(max_iter=2000, C=1.0).fit(s.transform(Z[tr]), y[tr])
        pred[te], sc[te] = c.predict(s.transform(Z[te])), c.decision_function(s.transform(Z[te]))
    return {"acc": float((pred == y).mean()), "auc": auc(y, sc), "majority_acc": float(max(y.mean(), 1 - y.mean()))}


def readout(rows):
    game = np.array([r["game"] for r in rows])
    att = np.array([r["attack_present"] for r in rows])
    conv = np.array([r["conv"] for r in rows])
    res = {"data": {"n": len(rows), "attack_present": int(att.sum()), "absent": int((~att).sum()), "games": int(len(np.unique(game))),
                    "attack_present_with_attack_taken": int(sum(r["attacked"] for r in rows if r["attack_present"])),
                    "conversion_states": int((att & conv).sum()), "seat0": int(sum(r["seat"] == 0 for r in rows))}, "pilots": {}}
    for name, path in PILOTS.items():
        P, Z = pilot_outputs(path, rows)
        d = lambda ii: (P[ii][att[ii]].mean() - P[ii][~att[ii]].mean()) if att[ii].any() and (~att[ii]).any() else float("nan")
        ii = np.arange(len(rows))
        r1 = {"p_attack_present": float(P[att].mean()), "p_attack_absent": float(P[~att].mean()), "diff": float(d(ii)), "diff_ci95": boot(game, d)}
        r2 = probe(Z, att.astype(int), game)
        a = np.where(att)[0]
        c1, c0 = a[conv[a]], a[~conv[a]]
        d3 = lambda jj: (P[jj][conv[jj]].mean() - P[jj][~conv[jj]].mean()) if conv[jj].any() and (~conv[jj]).any() else float("nan")
        r3 = {"n_conv": int(len(c1)), "n_rest": int(len(c0)), "p_conv": float(P[c1].mean()) if len(c1) else None,
              "p_rest": float(P[c0].mean()) if len(c0) else None,
              "diff": float(d3(a)), "diff_ci95": boot(game[a], lambda k: d3(a[k]))}
        at = [i for i in a if rows[i]["attacked"]]
        at = np.array(at, dtype=int)
        if len(at):
            r3["rest_among_attack_taken"] = {"n": int((~conv[at]).sum()), "p": float(P[at][~conv[at]].mean()) if (~conv[at]).any() else None}
        pr = r2["auc"] if r2 else None
        if r2 and r2["acc"] < 0.8:
            band = "R-representation"
        elif abs(r1["diff"]) < 0.05 and r2 and r2["acc"] > 0.9:
            band = "R-ignores"
        elif r1["diff"] >= 0.05 and (r1["p_attack_absent"] > 0.3 or (r3["p_conv"] is not None and r3["p_rest"] is not None and r3["p_conv"] <= r3["p_rest"])):
            band = "R-uses-wrongly"
        else:
            band = "none of the three (see numbers)"
        res["pilots"][name] = {"r1": r1, "r2_probe": r2, "r3": r3, "band": band}
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=15)
    ap.add_argument("--skip-collect", action="store_true")
    ap.add_argument("--pilot", nargs="+", help="name=path pilots to read in place of PILOTS (e.g. BENCH-P5's), with --skip-collect")
    ap.add_argument("--out", help="readout file (default runs/probe/C108-pluspower-policy/readout.json)")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.pilot:
        PILOTS.clear()
        PILOTS.update(x.split("=", 1) for x in a.pilot)
    st = torch.load(OUT / "states.pt", weights_only=False) if a.skip_collect else collect(a.minutes)
    res = readout(st["rows"])
    res["meta"] = st["meta"]
    Path(a.out or OUT / "readout.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
