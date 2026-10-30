"""BENCH evaluation of one pilot against the start pilot (runs/probe/BENCH/record.md, readouts 1, 2 and 4).

Orchestration only: runs the existing tools as subprocesses and gathers their JSON into <out>/bench_eval.json.
 1. Trainer prices: trainer_value.py on decks_P.json, one group per Trainer kind in P (decks.json's trainer_kinds), the
    pilot on both seats; per list and pooled (pooled per card = trainer_value's own score and CI).
 2. dG_B: a1_replay.py on O_B's raw probes (skipped if the file is missing). Pooled only: the raw probes do not record
    which list a game used.
 4. Play strength: each P list's mirror, the pilot against the start, and P against O; A's share and binomial SE.
Every "pooled" number is the mean over the P lists with the SE across lists. Evaluation only.

Run:  RL_GPU_SHARE=0.1 PYTHONPATH=. .venv/Scripts/python notes/scripts/bench_eval.py --pilot <pilot.pt> [--only 1,2,4]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BENCH = "runs/probe/BENCH"
PY, TOOLS = sys.executable, "notes/scripts"


def call(script, *args):
    cmd = [PY, f"{TOOLS}/{script}", *map(str, args)]
    print("$", " ".join(cmd[1:]), flush=True)
    r = subprocess.run(cmd, cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": str(ROOT)})
    if r.returncode:
        raise SystemExit(f"{script} failed ({r.returncode})")


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def pool(xs):
    """(mean, SE across the values)."""
    xs = np.asarray(xs, float)
    return float(xs.mean()), float(xs.std(ddof=1) / np.sqrt(len(xs))) if len(xs) > 1 else float("nan")


def share(p, n):
    return {"share": round(p, 4), "se": round(float(np.sqrt(p * (1 - p) / n)), 4), "games": n}


def readout1(a, lists, out):
    kinds = sorted({k for d in lists for k in d["trainer_kinds"]})
    res = f"{out}/tv.json"
    call("trainer_value.py", "--decks", f"{BENCH}/decks_P.json", "--players", a.pilot, "--games", a.games(64),
         "--workers", 4, "--round-turns", "20-45", "--seed", 91, "--groups", *kinds, "--out", res)
    tv = load(res)["players"][a.pilot]
    by_pair = {}
    for p, v in zip(load(res)["pairs"], tv["per_pair"]):
        by_pair[(p["base"], p["group"])] = v
    per = []
    for i, d in enumerate(lists):
        pr = {k: round(by_pair[(i, k)], 4) for k in d["trainer_kinds"] if (i, k) in by_pair}
        v = list(pr.values())
        per.append({"name": d["name"], "price": pr, "mean": round(float(np.mean(v)), 4), "min": min(v),
                    "computer_search": pr.get("Computer Search")})
    m, se = pool([x["mean"] for x in per])
    pooled = {"price": tv["by_group"], "mean": round(m, 4), "mean_se": round(se, 4),
              "min": min(r["score"] for r in tv["by_group"].values()),
              "computer_search": tv["by_group"].get("Computer Search")}
    return {"per_list": per, "pooled": pooled, "games_per_pair": a.games(64)}


FOCUS = ("PlusPower", "Gust of Wind", "Item Finder", "Scoop Up", "Computer Search")   # Amendment 8 (4 before): 256 games a pair


def readout1f(a, lists, out):
    """Amendments 4 and 8: the focus cards (FOCUS) at 256 games a pair, per list and pooled."""
    kinds = [k for k in FOCUS if any(k in d["trainer_kinds"] for d in lists)]
    res = f"{out}/tv256.json"
    call("trainer_value.py", "--decks", f"{BENCH}/decks_P.json", "--players", a.pilot, "--games", a.games(256),
         "--workers", 4, "--round-turns", "20-45", "--seed", 91, "--groups", *kinds, "--out", res)
    tv = load(res)["players"][a.pilot]
    by_pair = {(p["base"], p["group"]): v for p, v in zip(load(res)["pairs"], tv["per_pair"])}
    per = [{"name": d["name"], **{k: round(by_pair[(i, k)], 4) for k in kinds if (i, k) in by_pair}}
           for i, d in enumerate(lists)]
    return {"games_per_pair": a.games(256), "pooled": {k: tv["by_group"][k] for k in kinds}, "per_list": per}


def readout2(a, out):
    raw = ROOT / a.ob
    if not raw.exists():
        return {"skipped": f"{a.ob} does not exist yet"}
    call("a1_replay.py", "--pilot", a.pilot, "--start", a.start, "--raw", a.ob, "--out", f"{out}/a1_replay.json")
    return load(f"{out}/a1_replay.json")


def readout4(a, lists, out):
    mirrors = []
    for i, d in enumerate(lists):
        g = a.games(128)
        call("probe_matchups.py", "--a", f"{BENCH}/decks_P{i}.json", "--b", f"{BENCH}/decks_P{i}.json", "--pilot", a.pilot,
             "--pilot-b", a.start, "--games", g, "--round-turns", "20-45", "--out", f"{out}/mirror_P{i}.json")
        mirrors.append({"name": d["name"], **share(load(f"{out}/mirror_P{i}.json")["mean"], g)})
    g = a.games(64)
    call("probe_matchups.py", "--a", f"{BENCH}/decks_P.json", "--b", f"{BENCH}/decks_O.json", "--pilot", a.pilot,
         "--pilot-b", a.start, "--games", g, "--round-turns", "20-45", "--out", f"{out}/vs_O.json")
    vo = load(f"{out}/vs_O.json")
    n_o = len(vo["b"])
    vs_o = [{"name": n, **share(x, g * n_o)} for n, x in zip(vo["a"], vo["a_mean"])]
    res = {"mirror": mirrors, "vs_O": vs_o,
           "mirror_pooled": dict(zip(("share", "se"), pool([x["share"] for x in mirrors]))),
           "vs_O_pooled": dict(zip(("share", "se"), pool([x["share"] for x in vs_o])))}
    if a.ref:                                            # Amendment 4 (3): against the reference pilot (arm 0, same seed)
        ref = []
        for i, d in enumerate(lists):
            g = a.games(128)
            call("probe_matchups.py", "--a", f"{BENCH}/decks_P{i}.json", "--b", f"{BENCH}/decks_P{i}.json", "--pilot",
                 a.pilot, "--pilot-b", a.ref, "--games", g, "--round-turns", "20-45", "--out", f"{out}/ref_P{i}.json")
            ref.append({"name": d["name"], **share(load(f"{out}/ref_P{i}.json")["mean"], g)})
        res.update({"ref": a.ref, "mirror_vs_ref": ref,
                    "mirror_vs_ref_pooled": dict(zip(("share", "se"), pool([x["share"] for x in ref])))})
    return res


def table(res):
    print("\n== BENCH eval:", res["pilot"], "vs start", res["start"])
    r = res.get("readout1")
    if r:
        print(f"\n1. Trainer prices (target: every p >= 0.50), {r['games_per_pair']} games a pair")
        for x in r["per_list"]:
            print(f"  {x['name'][:36]:36s} mean {x['mean']:.3f}  min {x['min']:.3f}  Computer Search {x['computer_search']}")
        p = r["pooled"]
        print(f"  {'pooled':36s} mean {p['mean']:.3f} (SE {p['mean_se']:.3f})  min {p['min']:.3f}  Computer Search "
              f"{p['computer_search']['score'] if p['computer_search'] else None}")
        for k, v in p["price"].items():
            print(f"    {k:26s} {v['score']:.3f}  CI {v['ci']}  ({v['decks']} lists)")
    r = res.get("readout1_focus")
    if r:
        print(f"\n1f. Focus prices, {r['games_per_pair']} games a pair (Amendment 4)")
        for k, v in r["pooled"].items():
            print(f"    {k:26s} {v['score']:.3f}  CI {v['ci']}  ({v['decks']} lists)  per list "
                  f"{[x.get(k) for x in r['per_list']]}")
    r = res.get("readout2")
    if r:
        print("\n2. dG_B:", r["skipped"] if "skipped" in r else {k: r[k] for k in ("valid", "decisions", "prompts_all", "main")
                                                                  if k in r})
    r = res.get("readout4")
    if r:
        print("\n4. Play strength (share of the pilot, SE binomial; pooled SE across lists)")
        for k, lab in (("mirror", "mirror vs start"), ("vs_O", "vs O (start-piloted)"), ("mirror_vs_ref", "mirror vs ref")):
            if k not in r:
                continue
            for x in r[k]:
                print(f"  {lab:22s} {x['name'][:36]:36s} {x['share']:.3f} +- {x['se']:.3f}  ({x['games']} games)")
            q = r[k + "_pooled"]
            print(f"  {lab:22s} {'pooled':36s} {q['share']:.3f} +- {q['se']:.3f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--start", default="ar/data/start.pt")
    ap.add_argument("--ob", default=f"{BENCH}/O_B.json.probes.json.gz", help="O_B's raw probes (readout 2)")
    ap.add_argument("--only", default="1,2,4", help="1 (with the 256-game focus pricing), 1f (focus only), 2, 4")
    ap.add_argument("--ref", help="a reference pilot for extra P mirrors (Amendment 4: arm 0's pilot of the same seed)")
    ap.add_argument("--games-scale", type=float, default=1.0, help="multiplies every game count (smoke tests)")
    ap.add_argument("--out", help="default runs/probe/BENCH/eval-<pilot folder>-<pilot name>")
    a = ap.parse_args()
    a.games = lambda n: max(2, round(n * a.games_scale / 2) * 2)          # even: seats alternate
    pilot = Path(a.pilot).resolve()
    out = a.out or f"{BENCH}/eval-{pilot.parent.name}-{pilot.stem}"
    (ROOT / out).mkdir(parents=True, exist_ok=True)
    dk = load(f"{BENCH}/decks.json")
    lists = dk["P"]
    assert [d["name"] for d in load(f"{BENCH}/decks_P.json")] == [d["name"] for d in lists]
    only = set(a.only.split(","))
    res = {"pilot": a.pilot, "start": a.start, "games_scale": a.games_scale}
    if "1" in only:
        res["readout1"] = readout1(a, lists, out)
    if "1" in only or "1f" in only:
        res["readout1_focus"] = readout1f(a, lists, out)
    if "2" in only:
        res["readout2"] = readout2(a, out)
    if "4" in only:
        res["readout4"] = readout4(a, lists, out)
    (ROOT / out / "bench_eval.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    table(res)
    print("wrote", ROOT / out / "bench_eval.json")


if __name__ == "__main__":
    main()
