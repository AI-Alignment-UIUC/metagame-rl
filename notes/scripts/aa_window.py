"""A/A noise floor of a screen recipe (log #153, C29 / H98): per-run window readouts from log.jsonl and the population
snapshots, the pairwise per-iteration RMS between runs of one recipe, a pooled within-recipe SD over every recipe group
(df = runs - groups) with its one-sided 95% upper bound, Welch CIs between groups, and arm-minus-control differences
re-read against that SD. Evaluation only.

Readouts per run: top-12 distance from the human medians (screen_watch.py), the largest type at the turnovers
(log.jsonl `types`), decks moved by --select, the head's incoming entropy, and wall-core decks (holding both Chansey BS
and Snorlax JU) in each snapshot.

  .venv/Scripts/python notes/scripts/aa_window.py --group gated scr-gate479,scr-gate479-s3,scr-gate479-s4 \
      --group ungated scr-ctl479,scr-resetcap --arm scr-vs479:scr-ctl479 --window 490 499
"""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import torch
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
HUMAN = np.array([13.5, 28.0, 18.0])
WALL = ("Chansey BS", "Snorlax JU")


def rows(run: Path) -> dict:
    out = {}
    for x in (run / "log.jsonl").read_text().splitlines():
        if x.strip():
            r = json.loads(x)
            out[r["iter"]] = r                      # a resumed run's later row for an iteration wins
    return out


def dist(r: dict) -> float:
    sh = np.array(r["shapes"], dtype=float)
    z = np.array([np.nan if x is None else x for x in r["z"]], dtype=float)
    top = np.argsort(-np.nan_to_num(z, nan=-1))[:12]
    return float(np.abs(sh[top].mean(0) - HUMAN).sum())


def wall_core(run: Path, it: int):
    p = run / f"population_it{it:04d}.pt"
    if not p.exists():
        return None
    pop = torch.load(p, map_location="cpu", weights_only=False)["population"]
    return sum(all(w in x["deck"] for w in WALL) for x in pop)


def readouts(name: str, lo: int, hi: int, turns) -> dict:
    run = ROOT / "runs" / "screens" / name
    rs = rows(run)
    its = [i for i in range(lo, hi + 1) if i in rs]
    traj = {i: {"dist": dist(rs[i]), "moved": rs[i].get("select", {}).get("moved"),
                "h_in": rs[i].get("draft", {}).get("h_in"),
                "largest": max(rs[i]["types"]) if rs[i].get("types") else None} for i in sorted(rs)}
    walls = {t: wall_core(run, t) for t in turns}
    last = rs[max(rs)]
    med = np.median(np.array(last["shapes"], dtype=float), 0)

    def mean(key, it_list):
        v = [traj[i][key] for i in it_list if i in traj and traj[i][key] is not None]
        return float(np.mean(v)) if v else None
    return {"name": name, "its": its, "last": max(rs), "traj": traj, "walls": walls,
            "dist": mean("dist", its), "moved": mean("moved", its), "h_in": mean("h_in", its),
            "largest": mean("largest", [t for t in turns]),
            "wall": float(np.mean([w for w in walls.values() if w is not None]))
            if any(w is not None for w in walls.values()) else None,
            "median": med.tolist()}


def pooled(groups: dict, key: str):
    ss, df = 0.0, 0
    for runs in groups.values():
        v = np.array([r[key] for r in runs if r[key] is not None])
        if len(v) > 1:
            ss += ((v - v.mean()) ** 2).sum()
            df += len(v) - 1
    if df == 0:
        return None, None, 0
    s = np.sqrt(ss / df)
    return s, s * np.sqrt(df / stats.chi2.ppf(0.05, df)), df


def welch(a, b):
    a, b = np.array(a, float), np.array(b, float)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = np.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    d = a.mean() - b.mean()
    h = stats.t.ppf(0.975, df) * se
    return d, d - h, d + h, df


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", nargs=2, action="append", metavar=("NAME", "RUNS"), required=True,
                    help="a recipe group: name and comma-separated screen runs")
    ap.add_argument("--arm", action="append", default=[], help="arm:control, re-read against the pooled SD")
    ap.add_argument("--window", nargs=2, type=int, default=[490, 499])
    ap.add_argument("--turns", default="484,489,494,499", help="turnover / snapshot iterations")
    ap.add_argument("--traj", nargs=2, type=int, default=[480, 499], help="iterations for the per-iteration RMS")
    a = ap.parse_args(argv)
    lo, hi = a.window
    turns = [int(x) for x in a.turns.split(",")]
    cache = {}

    def get(n):
        if n not in cache:
            cache[n] = readouts(n, lo, hi, turns)
        return cache[n]

    groups = {g: [get(n) for n in runs.split(",")] for g, runs in a.group}
    keys = ["dist", "largest", "wall", "moved", "h_in"]
    print(f"window {lo}-{hi}; turnovers {turns}")
    for g, runs in groups.items():
        print(f"== {g}")
        for r in runs:
            ws = " ".join("-" if r["walls"][t] is None else str(r["walls"][t]) for t in turns)
            lg = " ".join("-" if r["traj"].get(t, {}).get("largest") is None else str(r["traj"][t]["largest"]) for t in turns)
            print(f"  {r['name']:18s} to {r['last']}  dist {r['dist']:5.2f}  largest [{lg}] mean {r['largest']:5.1f}  "
                  f"wall-core [{ws}] mean {r['wall']:5.1f}  moved {r['moved']:5.1f}  h_in {r['h_in']:4.2f}  "
                  f"median {'/'.join(f'{x:.0f}' for x in r['median'])}")
    print("== pairwise per-iteration RMS (within groups)")
    t0, t1 = a.traj
    for g, runs in groups.items():
        for x, y in itertools.combinations(runs, 2):
            out = []
            for k in ["dist", "moved", "h_in"]:
                d = [x["traj"][i][k] - y["traj"][i][k] for i in range(t0, t1 + 1)
                     if i in x["traj"] and i in y["traj"] and x["traj"][i][k] is not None and y["traj"][i][k] is not None]
                out.append(f"{k} {np.sqrt(np.mean(np.square(d))):5.2f} (n {len(d)})")
            for k, src in [("largest", "traj"), ("wall", "walls")]:
                if src == "traj":
                    d = [x["traj"][t]["largest"] - y["traj"][t]["largest"] for t in turns
                         if x["traj"].get(t, {}).get("largest") is not None and y["traj"].get(t, {}).get("largest") is not None]
                else:
                    d = [x["walls"][t] - y["walls"][t] for t in turns if x["walls"][t] is not None and y["walls"][t] is not None]
                out.append(f"{k} {np.sqrt(np.mean(np.square(d))) if d else float('nan'):5.1f} (n {len(d)})")
            print(f"  {g}: {x['name']} vs {y['name']}: " + ", ".join(out))
    print("== pooled within-recipe SD of the window readouts (one-sided 95% upper bound)")
    sd = {}
    for k in keys:
        s, u, df = pooled(groups, k)
        sd[k] = (s, u)
        if s is not None:
            print(f"  {k:8s} SD {s:6.2f}  upper {u:6.2f}  df {df}")
    if len(groups) >= 2:
        (ga, ra), (gb, rb) = list(groups.items())[:2]
        print(f"== Welch 95% CI, {ga} - {gb}")
        for k in keys:
            va, vb = [r[k] for r in ra if r[k] is not None], [r[k] for r in rb if r[k] is not None]
            if len(va) > 1 and len(vb) > 1:
                d, l, h, df = welch(va, vb)
                print(f"  {k:8s} {d:7.2f} [{l:7.2f}, {h:7.2f}]  df {df:.1f}")
    if a.arm:
        print("== arms minus control over the iterations both reached, against 2*sqrt(2)*SD (point / upper)")
        for pair in a.arm:
            arm, ctl = (get(n) for n in pair.split(":"))
            its = [i for i in arm["its"] if i in ctl["its"]]
            tts = [t for t in turns if arm["traj"].get(t, {}).get("largest") is not None
                   and ctl["traj"].get(t, {}).get("largest") is not None]
            sns = [t for t in turns if arm["walls"][t] is not None and ctl["walls"][t] is not None]
            diff = {"dist": np.mean([arm["traj"][i]["dist"] - ctl["traj"][i]["dist"] for i in its]) if its else None,
                    "largest": np.mean([arm["traj"][t]["largest"] - ctl["traj"][t]["largest"] for t in tts]) if tts else None,
                    "wall": np.mean([arm["walls"][t] - ctl["walls"][t] for t in sns]) if sns else None}
            out = [f"its {its[0]}-{its[-1]}, turnovers {','.join(map(str, tts))}" if its else "no common iterations"]
            for k in ["dist", "largest", "wall"]:
                if diff[k] is None or sd[k][0] is None:
                    continue
                d = diff[k]
                bar, bar_u = 2 * np.sqrt(2) * sd[k][0], 2 * np.sqrt(2) * sd[k][1]
                tag = "beyond" if abs(d) > bar_u else ("past point bar" if abs(d) > bar else "inside")
                out.append(f"{k} {d:+6.1f} ({tag}; bars {bar:.1f}/{bar_u:.1f})")
            print(f"  {arm['name']:16s} - {ctl['name']:16s} to {arm['last']}: " + ", ".join(out))


if __name__ == "__main__":
    main()
