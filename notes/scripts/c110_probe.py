"""C110 (runs/probe/C110-ko-math/record.md): does the pilot's state encode knockout math (attack damage against the Defender's HP left)?
CPU only, evaluation only. Two stages:
  collect   as C108 (P x P bench games under the start pilot, RemotePool on CPU), with the worker's log-only flag koMath
            (env/remote_worker.js koCatch): at each attack-available PlusPower-playable decision every legal attack is played on a clone
            of the game (no PlusPower newly played) and the engine's PutDamageEffect on the Defending Pokemon is read (damage after
            Weakness, Resistance and PlusPowers already attached; HP left before the hit). States are stored as c108_probe does.
  readout   readouts 1-3 per pilot and pooled, and the record's bands.
Label per state: KO-anyway if some attack's damage >= HP left (also when conversion applies; the overlap is counted); else conversion
if some attack's damage is in [left - 10, left); else no-KO. Coin flips: the clone carries a clone of the game's RNG, so the flip
lands as it will in the game (one copy, no expectation); counted per attack. Choices: a prompt after the attack is answered with its
first option; counted.
  CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=. .venv/Scripts/python.exe notes/scripts/c110_probe.py [--minutes 15] [--skip-collect]
"""
import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
import numpy as np
import torch
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
torch.set_num_threads(2)
spec = importlib.util.spec_from_file_location("c108", ROOT / "notes/scripts/c108_probe.py")
c108 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c108)
from rl.gpu_matrix import load_policy        # noqa: E402
from rl.remote import RemotePool             # noqa: E402

OUT = ROOT / "runs/probe/C110-ko-math"
PILOTS = {"start": "ar/data/start.pt", "arm0_s1": "runs/probe/BENCH/arm-arm0-s1/pilot.pt",
          "p5_s1": "runs/probe/BENCH/arm-p5-s1/pilot.pt", "p5_s2": "runs/probe/BENCH/arm-p5-s2/pilot.pt"}


def label(atk):
    """-> (label, both, stats) from the per-attack engine readings."""
    hit = [a for a in atk if a["left"] is not None]
    ko = any(a["dmg"] >= a["left"] for a in hit)
    cv = any(a["left"] - 10 <= a["dmg"] < a["left"] for a in hit)
    return ("ko" if ko else "conv" if cv else "noko"), ko and cv


def collect(minutes, target):
    model, _ = load_policy(str(ROOT / c108.PILOTS["start"]), "cpu")
    mt = json.loads((ROOT / "runs/probe/BENCH/bench_matchups.json").read_text(encoding="utf-8"))
    tmp = OUT / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    rows, t0, rnd = [], time.time(), 0
    pool = RemotePool(2)
    try:
        while True:
            msgs = [{"cmd": "collect", "encoding": "tokens", "transitions": 1500, "concurrency": 24, "seed": 5000 + 10 * rnd + w,
                     "roundTurns": [20, 45], "deckoutWin": 1.0, "matchups": mt, "opponents": [{"spec": "self", "weight": 1.0}],
                     "out": str(tmp / f"roll{rnd}_{w}.bin"), "history": 0, "chain": 0, "canon": 0, "koMath": True} for w in range(2)]
            rep = pool.collect(msgs, {0: model.eval()}, "cpu")
            for w, r in enumerate(rep):
                ko = {x["k"]: x["atk"] for x in r["koMath"]}
                for row in c108.rows_of(r["out"], (rnd * 2 + w) * 10**6):
                    row["atk"] = ko.get(row["i"])
                    if row["attack_present"] and row["atk"] is not None:
                        row["label"], row["both"] = label(row["atk"])
                    rows.append(row)
            rnd += 1
            n = sum("label" in r for r in rows)
            print(f"round {rnd}: {len(rows)} PlusPower-playable, {n} labelled attack-available, {(time.time() - t0) / 60:.1f} min", flush=True)
            torch.save({"meta": {"minutes": (time.time() - t0) / 60, "rounds": rnd}, "rows": rows}, OUT / "states.pt")
            if n >= target or time.time() - t0 > 60 * minutes:
                break
    finally:
        pool.close()
    return {"meta": {"minutes": (time.time() - t0) / 60, "rounds": rnd}, "rows": rows}


def auc(y, s):
    n1, n0 = int(y.sum()), int(len(y) - y.sum())
    if not n1 or not n0:
        return float("nan")
    return float((rankdata(s)[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def oof_scores(Z, y, game):
    """5-fold-by-game logistic probe -> out-of-fold decision scores."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    ug = np.unique(game)
    fold = {g: i % 5 for i, g in enumerate(np.random.default_rng(0).permutation(ug))}
    f = np.array([fold[g] for g in game])
    sc = np.zeros(len(y))
    for k in range(5):
        tr, te = f != k, f == k
        s = StandardScaler().fit(Z[tr])
        c = LogisticRegression(max_iter=2000, C=1.0).fit(s.transform(Z[tr]), y[tr])
        sc[te] = c.decision_function(s.transform(Z[te]))
    return sc


def boot_games(game, fs, n=500, seed=0):
    """fs: list of f(index array) -> values; resample games, returns [n x len(fs)]."""
    rng = np.random.default_rng(seed)
    ug = np.unique(game)
    idx = {g: np.where(game == g)[0] for g in ug}
    out = []
    for _ in range(n):
        ii = np.concatenate([idx[g] for g in rng.choice(ug, len(ug))])
        out.append([f(ii) for f in fs])
    return np.array(out)


def ci(v):
    v = v[~np.isnan(v)]
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


def band(a1, c1, a2):
    if a1 >= 0.85 and c1[0] > 0.8:
        return "R-encoded"
    if a1 < 0.70 and a2 >= 0.85:
        return "R-not-encoded"
    return "between"


def readout(rows):
    rows = [r for r in rows if "label" in r]
    lab = np.array([r["label"] for r in rows])
    game = np.array([r["game"] for r in rows])
    atks = [a for r in rows for a in r["atk"]]
    res = {"data": {"n": len(rows), "games": int(len(np.unique(game))), "conversion": int((lab == "conv").sum()),
                    "ko_anyway": int((lab == "ko").sum()), "no_ko": int((lab == "noko").sum()), "both_conv_and_ko": int(sum(r["both"] for r in rows)),
                    "attacks": len(atks), "attacks_with_coin_flip": int(sum(a["coins"] > 0 for a in atks)),
                    "attacks_with_choice_prompt": int(sum(a["choice"] for a in atks)), "attacks_with_error": int(sum("error" in a for a in atks)),
                    "attacks_no_damage_to_defender": int(sum(a["left"] is None for a in atks)),
                    "states_with_a_coin_or_choice_attack": int(sum(any(a["coins"] > 0 or a["choice"] for a in r["atk"]) for r in rows)),
                    "seat0": int(sum(r["seat"] == 0 for r in rows))}, "pilots": {}}
    m1, m0 = (lab == "conv") | (lab == "noko"), lab == "noko"
    y1 = (lab == "conv").astype(int)
    y2 = (lab == "ko").astype(int)
    conv_i, noko_i = np.where(lab == "conv")[0], np.where(lab == "noko")[0]
    sel = np.concatenate([conv_i, noko_i])
    aucs1, aucs2, diffs, all_f = [], [], [], []
    for name, path in PILOTS.items():
        P, Z = c108.pilot_outputs(path, rows)
        s1 = np.full(len(rows), np.nan)
        s1[m1] = oof_scores(Z[m1], y1[m1], game[m1])
        s2 = oof_scores(Z, y2, game)
        f1 = lambda ii, s1=s1: auc(y1[ii][m1[ii]], s1[ii][m1[ii]])
        f2 = lambda ii, s2=s2: auc(y2[ii], s2[ii])
        f3 = lambda ii, P=P: (P[ii][lab[ii] == "conv"].mean() - P[ii][lab[ii] == "noko"].mean()) if (lab[ii] == "conv").any() and (lab[ii] == "noko").any() else float("nan")
        all_f.append((f1, f2, f3))
        ii = np.arange(len(rows))
        res["pilots"][name] = {"p_pp_conv": float(P[conv_i].mean()), "p_pp_noko": float(P[noko_i].mean()),
                               "r1_auc": f1(ii), "r2_auc": f2(ii), "r3_diff": f3(ii)}
        aucs1.append(f1(ii)); aucs2.append(f2(ii)); diffs.append(f3(ii))
    fs = [f for t in all_f for f in t]
    B = boot_games(game, fs)
    for j, name in enumerate(PILOTS):
        p = res["pilots"][name]
        p["r1_ci95"], p["r2_ci95"], p["r3_ci95"] = ci(B[:, 3 * j]), ci(B[:, 3 * j + 1]), ci(B[:, 3 * j + 2])
        p["band"] = band(p["r1_auc"], p["r1_ci95"], p["r2_auc"])
    pool = {"r1_auc": float(np.mean(aucs1)), "r2_auc": float(np.mean(aucs2)), "r3_diff": float(np.mean(diffs)),
            "r1_ci95": ci(B[:, 0::3].mean(1)), "r2_ci95": ci(B[:, 1::3].mean(1)), "r3_ci95": ci(B[:, 2::3].mean(1))}
    pool["band"] = band(pool["r1_auc"], pool["r1_ci95"], pool["r2_auc"])
    res["pooled_mean_over_pilots"] = pool
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=15)
    ap.add_argument("--target", type=int, default=3000, help="stop once this many attack-available labelled states")
    ap.add_argument("--skip-collect", action="store_true")
    ap.add_argument("--pilot", nargs="+", help="name=path pilots in place of PILOTS (e.g. BENCH-P5b's), with --skip-collect")
    ap.add_argument("--out", help="readout file (default runs/probe/C110-ko-math/readout.json)")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.pilot:
        PILOTS.clear()
        PILOTS.update(x.split("=", 1) for x in a.pilot)
    st = torch.load(OUT / "states.pt", weights_only=False) if a.skip_collect else collect(a.minutes, a.target)
    res = readout(st["rows"])
    res["meta"] = st["meta"]
    Path(a.out or OUT / "readout.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
