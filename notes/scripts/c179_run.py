"""C179 with its Amendment 1 (runs/probe/C179-shape-dose/record.md), evaluation only: are the lists worse than copies moved to the loop's shape? --make-decks: for each of the 24 lists, 4 seeded copies at each arm. d6 and d14: D Trainers out, drawn in proportion to the list's own copies, into its own Pokemon up to the copy limit and its own basic Energy at about 8:6; a Pokemon slot the limit stops goes to Energy. d14n: the same draws of dose 14, with those stopped slots going to Basics from a plain table at kappa 3 (s48's on draws 0 and 1, s49's on 2 and 3). Games: each list and its copies against 12 other lists as printed, 2 deals, greedy (or --search, C135's set), round rule [20, 45], seed 91, the copies on the list's own deals. Read with notes/scripts/c179_read.py.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c179_run.py --make-decks
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c179_run.py --pilot runs/pilot/C49-sd/model_it00199.pt --out runs/probe/C179-shape-dose/G_C49.json
"""
import argparse
import collections
import json
import os
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "notes" / "scripts")]
D = ROOT / "runs/probe/C179-shape-dose"
LISTS = ROOT / "runs/probe/C163-draw-deck-field/L.json"
TABLES = ROOT / "runs/probe/C171-table-drafting"
KAPPA = 3.0
DRAWS = 4


def table_weights(seed):
    c = json.loads((TABLES / f"table-plain-s{seed}/table.json").read_text(encoding="utf-8"))
    v = np.array(list(c.values()), dtype=float)
    return {n: float(np.exp(KAPPA * (x - v.mean()) / v.std())) for n, x in c.items()}


def make_decks(offset=0, out_path=None):
    from rl.decks import Pool
    pool = Pool()
    card = {c["fullName"]: c for c in pool.cards}
    lists = [{"name": d["name"], "cards": list(d["cards"])} for d in json.loads(LISTS.read_text(encoding="utf-8"))]
    basics = [c for c in pool.cards if pool.allowed[c["id"]] and c["superType"] == 1 and c["stage"] == 2]
    tw = {48: table_weights(48), 49: table_weights(49)}
    is_t = lambda x: card[x]["superType"] == 2
    is_p = lambda x: card[x]["superType"] == 1
    is_be = lambda x: card[x]["superType"] == 3 and card[x]["energyType"] == 0
    limit = lambda cards, x: sum(card[y]["name"] == card[x]["name"] for y in cards) < 4
    out = []
    for k, d in enumerate(lists):
        ts = [x for x in d["cards"] if is_t(x)]
        ps = [x for x in d["cards"] if is_p(x)]
        es = [x for x in d["cards"] if is_be(x)]
        assert es, d["name"]
        for dose in (6, 14):
            n_p = round(dose * 8 / 14)
            for r in range(DRAWS):
                rng = random.Random(179000 + offset + k * 100 + dose * 10 + r)
                tr = list(ts)
                rng.shuffle(tr)
                out_t = tr[:dose]                     # a uniform draw over copies is in proportion to the list's own copies
                rest = list(d["cards"])
                for x in out_t:
                    rest.remove(x)
                arms = {f"d{dose}": list(rest)}
                if dose == 14:
                    arms["d14n"] = list(rest)
                state = rng.getstate()
                for arm, cards in arms.items():
                    rng.setstate(state)               # the same draws in both dose-14 arms, until a slot is stopped
                    added_p, added_new, stopped = [], [], 0
                    for _ in range(n_p):
                        free = [x for x in ps if limit(cards, x)]
                        if free:
                            x = rng.choice(free)      # in proportion to the list's own copies, among names under the limit
                            cards.append(x)
                            added_p.append(x)
                        elif arm == "d14n":
                            w = tw[48 if r < 2 else 49]
                            cand = [c["fullName"] for c in basics if limit(cards, c["fullName"]) and c["name"] in w]
                            x = rng.choices(cand, weights=[w[card[y]["name"]] for y in cand])[0]
                            cards.append(x)
                            added_new.append(x)
                        else:
                            stopped += 1
                    added_e = []
                    for _ in range(60 - len(cards)):
                        x = rng.choice(es)            # in proportion to the list's own basic Energy
                        cards.append(x)
                        added_e.append(x)
                    assert len(cards) == 60 and pool.legal(pool.vector(cards)), (d["name"], arm, r)
                    assert sum(is_t(x) for x in cards) == len(ts) - dose, (d["name"], arm, r)
                    out.append({"name": f"{d['name']}-{arm}-{r}", "list": k, "arm": arm, "draw": r, "cards": cards, "trainers_out": out_t, "added_pokemon": added_p, "added_new": added_new, "added_energy": added_e, "stopped_to_energy": stopped})
    (out_path or D / "decks.json").write_text(json.dumps(out), encoding="utf-8")
    shape = collections.defaultdict(list)
    for x in out:
        shape[x["arm"]].append([sum(card[c]["superType"] == s for c in x["cards"]) for s in (1, 2, 3)])
    print("copies", len(out), {a: [round(float(q), 2) for q in np.mean(v, 0)] for a, v in shape.items()}, "stopped to Energy, mean", {a: round(float(np.mean([x["stopped_to_energy"] for x in out if x["arm"] == a])), 2) for a in shape}, "new names, mean", {a: round(float(np.mean([len(x["added_new"]) for x in out if x["arm"] == a])), 2) for a in shape})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-decks", action="store_true")
    ap.add_argument("--draw-offset", type=int, default=0, help="C180: fresh draws, the same rule")
    ap.add_argument("--decks", default="", help="C180: a copies file instead of C179's")
    ap.add_argument("--pilot", default="")
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--games", type=int, default=2)
    ap.add_argument("--opps", type=int, default=12)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--lists", type=int, default=24, help="the first N lists, for a smoke")
    ap.add_argument("--search", action="store_true")
    ap.add_argument("--trace", action="store_true", help="C180: the log-only trace worker, to OUT with .jsonl for .json")
    ap.add_argument("--arms", default="", help="C180: only these copy arms, comma-separated; the deals don't change")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.make_decks:
        return make_decks(a.draw_offset, ROOT / a.decks if a.decks else None)
    import torch
    import rl.remote as R
    from rl.gpu_matrix import GpuMatrix, load_policy
    if a.trace:
        _popen = R.subprocess.Popen
        R.subprocess.Popen = lambda cmd, **kw: _popen(["node", str(ROOT / "notes/scripts/audit/c180_trace_worker.js")], **kw)
        tr = ROOT / (a.out[:-5] + ".jsonl")
        tr.unlink(missing_ok=True)
        os.environ["C180_TRACE"] = str(tr)
    lists = [{"name": d["name"], "cards": list(d["cards"])} for d in json.loads(LISTS.read_text(encoding="utf-8"))]
    copies = json.loads((ROOT / a.decks if a.decks else D / "decks.json").read_text(encoding="utf-8"))
    n0 = len(lists)
    alld = lists + [{"name": c["name"], "cards": c["cards"]} for c in copies]
    by = collections.defaultdict(list)
    keep = set(a.arms.split(",")) if a.arms else None
    for v, c in enumerate(copies):
        if keep is None or c["arm"] in keep:
            by[c["list"]].append(n0 + v)
    rng = random.Random(179)
    pairs, keys = [], []
    for k in range(min(a.lists, n0)):
        for o in sorted(rng.sample([x for x in range(n0) if x != k], a.opps)):
            key = k * n0 + o
            pairs += [(k, o)] + [(v, o) for v in by[k]]
            keys += [key] * (1 + len(by[k]))
    if os.environ.get("C172_GPU_MEM"):
        torch.cuda.set_per_process_memory_fraction(float(os.environ["C172_GPU_MEM"]))
    model, _ = load_policy(a.pilot, a.device)
    search = None
    if a.search:
        from c139_run import SEARCH
        search = {**SEARCH, "k": 64, "allTrainers": False}
    rp = R.RemotePool(a.workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, a.workers, device=a.device)
        gm.play(alld, a.games, a.seed, pairs=pairs, pair_keys=keys, round_turns=[20, 45], search=search)
        print("C179", a.pilot, gm.last, flush=True)
        rows = [{"i": r["i"], "j": r["j"], "seed": r["seed"], "iSeat": r["iSeat"], "winner": r["winner"], "ending": r.get("ending"), "error": r.get("error")} for r in gm.results]
        Path(ROOT / a.out).write_text(json.dumps({"pilot": a.pilot, "search": search, "seed": a.seed, "last": gm.last, "n_lists": n0, "results": rows}), encoding="utf-8")
    finally:
        rp.close()


if __name__ == "__main__":
    main()
