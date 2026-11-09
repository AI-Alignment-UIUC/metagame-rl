"""C180's Amendment 1, the shed dose on C167's decks that break a list apart (runs/probe/C180-dose-by-practice/record.md), evaluation only. B (list's Trainers, rules-only body), T (list's body, random Trainers), C (list's body, other Trainers at the list's counts), all draw-free, from runs/probe/C164-list-knockout. A, the draw-free lists, is the comparator, 4 draws a list (research's #862, before any game). --make-decks: each deck's copy with 8 Trainers out, so it lands at about 14, W's shape, by C179's rule, into its own Pokemon up to the copy limit and its own basic Energy at about 8:6. Games: a deck and its copy against 12 lists as printed, not its source, 2 deals, greedy, round rule [20, 45], seed 91, the copy on the deck's own deals. --read: copy - deck on event points/3, by source list, bootstrap over lists; arm 0 - C49-sd on that gain, paired by list. No band: arm 0's edge says where it sits, against A. Only on true lists is whole-list familiarity or the set; on B is skill with those Trainers; on T or C is the bodies.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c180_parts.py --make-decks
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c180_parts.py --type B --pilot runs/pilot/C49-sd/model_it00199.pt --out runs/probe/C180-dose-by-practice/P_B_C49.json
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c180_parts.py --read
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
D = ROOT / "runs/probe/C180-dose-by-practice"
C164 = ROOT / "runs/probe/C164-list-knockout"
LISTS = ROOT / "runs/probe/C163-draw-deck-field/L.json"
DOSE = 8


def load(kind):
    if kind == "A":
        base = json.loads((ROOT / "runs/probe/C163-draw-deck-field/L_base.json").read_text(encoding="utf-8"))
        return [d for d in base for _ in range(4)]
    return json.loads((C164 / f"{kind}.json").read_text(encoding="utf-8"))


def make_decks():
    from rl.decks import Pool
    pool = Pool()
    card = {c["fullName"]: c for c in pool.cards}
    for kind in "ABTC":
        decks = load(kind)
        out = []
        for m, d in enumerate(decks):
            rng = random.Random(180000 + ord(kind) * 1000 + m)
            ts = [x for x in d["cards"] if card[x]["superType"] == 2]
            ps = [x for x in d["cards"] if card[x]["superType"] == 1]
            es = [x for x in d["cards"] if card[x]["superType"] == 3 and card[x]["energyType"] == 0]
            assert es, d["name"]
            if len(ts) < DOSE:                         # draw-free decks can hold under 14 Trainers: skipped, and counted
                out.append(None)
                continue
            tr = list(ts)
            rng.shuffle(tr)
            cards = list(d["cards"])
            for x in tr[:DOSE]:
                cards.remove(x)
            limit = lambda x: sum(card[y]["name"] == card[x]["name"] for y in cards) < 4
            added_p, stopped = [], 0
            for _ in range(round(DOSE * 8 / 14)):
                free = [x for x in ps if limit(x)]
                if free:
                    x = rng.choice(free)
                    cards.append(x)
                    added_p.append(x)
                else:
                    stopped += 1
            added_e = [rng.choice(es) for _ in range(60 - len(cards))]
            cards += added_e
            assert len(cards) == 60 and pool.legal(pool.vector(cards)), d["name"]
            out.append({"name": d["name"] + "-d8", "src": d["src"], "cards": cards, "trainers_out": tr[:DOSE], "added_pokemon": added_p, "added_energy": added_e, "stopped_to_energy": stopped})
        (D / f"parts_{kind}.json").write_text(json.dumps(out), encoding="utf-8")
        kept = [x for x in out if x]
        sh = lambda cs: [round(float(q), 2) for q in np.mean([[sum(card[c]["superType"] == s for c in x["cards"]) for s in (1, 2, 3)] for x in cs], 0)]
        print(kind, "decks", len(out), "skipped", len(out) - len(kept), "deck", sh([d for d, x in zip(decks, out) if x]), "copy", sh(kept), "stopped", round(float(np.mean([x["stopped_to_energy"] for x in kept])), 2))


def read():
    from c139_read import pts, r3
    lists = [d["name"] for d in json.loads(LISTS.read_text(encoding="utf-8"))]
    out, gains = {}, {}
    for f in sorted(D.glob("P_*.json")):
        _, kind, pilot = f.stem.split("_")
        decks = load(kind)
        n = len(decks)
        r = json.loads(f.read_text(encoding="utf-8"))
        deals = collections.defaultdict(dict)
        for x in r["results"]:
            if not x.get("error"):
                deals[x["seed"]][x["i"]] = x
        by, by_wo = collections.defaultdict(list), collections.defaultdict(list)
        dq = 0
        side = {"deck": collections.Counter(), "copy": collections.Counter()}
        count = collections.Counter()
        for g in deals.values():
            base = [x for i, x in g.items() if 24 <= i < 24 + n]
            copy = [x for i, x in g.items() if i >= 24 + n]
            if not base or not copy:
                continue
            k = lists.index(decks[base[0]["i"] - 24]["src"])
            by[k].append(pts(copy[0])[0] - pts(base[0])[0])
            b0 = base[0]
            lost_out = b0.get("ending") == "deck-out" and b0["winner"] in (1, 2) and b0["winner"] != b0["iSeat"]
            dq += lost_out
            if not lost_out:                            # research's #860: the gain without the deals the deck lost by deck-out
                by_wo[k].append(pts(copy[0])[0] - pts(base[0])[0])
            for t, x in (("deck", base[0]), ("copy", copy[0])):
                count[t] += 1
                side[t]["win"] += x["winner"] == x["iSeat"]
                side[t]["full_win"] += x["winner"] == x["iSeat"] and x.get("ending") != "time"
                side[t]["full_loss"] += x["winner"] in (1, 2) and x["winner"] != x["iSeat"] and x.get("ending") != "time"
                side[t]["pts"] += pts(x)[0]
        m = {k: float(np.mean(v)) for k, v in by.items()}
        vals = np.array(list(m.values()))
        rng = np.random.default_rng(180)
        gains[(kind, pilot)] = m
        out.setdefault(kind, {})[pilot] = {"games": r["last"]["games"], "errors": r["last"]["errors"], "games_per_s": r["last"]["games_per_s"], "change": r3(float(vals.mean())), "se_lists": r3(float(np.std([vals[rng.integers(len(vals), size=len(vals))].mean() for _ in range(4000)]))), "lists": len(vals), "above_0": int((vals > 0).sum()), "deck_lost_by_deck_out": r3(dq / max(1, count["deck"])), "change_without_those": r3(float(np.mean([np.mean(v) for v in by_wo.values()]))),
                                           "deck": {k: r3(side["deck"][k] / max(1, count["deck"])) for k in ("win", "full_win", "full_loss", "pts")}, "copy": {k: r3(side["copy"][k] / max(1, count["copy"])) for k in ("win", "full_win", "full_loss", "pts")}}
    for kind in out:
        if (kind, "arm0") in gains and (kind, "C49") in gains:
            a, b = gains[(kind, "arm0")], gains[(kind, "C49")]
            k = sorted(set(a) & set(b))
            d = np.array([a[q] - b[q] for q in k])
            rng = np.random.default_rng(180)
            out[kind]["arm0_minus_C49"] = {"diff": r3(float(d.mean())), "se": r3(float(np.std([d[rng.integers(len(d), size=len(d))].mean() for _ in range(4000)])))}
    (D / "summary_parts.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-decks", action="store_true")
    ap.add_argument("--read", action="store_true")
    ap.add_argument("--type", default="")
    ap.add_argument("--pilot", default="")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0, help="the first N decks, for a smoke")
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.make_decks:
        return make_decks()
    if a.read:
        return read()
    import torch
    import rl.remote as R
    from rl.gpu_matrix import GpuMatrix, load_policy
    lists = [{"name": d["name"], "cards": list(d["cards"])} for d in json.loads(LISTS.read_text(encoding="utf-8"))]
    decks = load(a.type)
    copies = json.loads((D / f"parts_{a.type}.json").read_text(encoding="utf-8"))
    n0, n = len(lists), len(decks)
    alld = lists + [{"name": d["name"], "cards": d["cards"]} for d in decks] + [{"name": c["name"], "cards": c["cards"]} if c else {"name": d["name"], "cards": d["cards"]} for c, d in zip(copies, decks)]
    names = [d["name"] for d in lists]
    rng = random.Random(180)
    pairs, keys = [], []
    for m, d in enumerate(decks[:a.limit or n]):
        if not copies[m]:
            continue
        src = names.index(d["src"])
        for o in sorted(rng.sample([x for x in range(n0) if x != src], 12)):
            key = m * n0 + o
            pairs += [(n0 + m, o), (n0 + n + m, o)]
            keys += [key, key]
    if os.environ.get("C172_GPU_MEM"):
        torch.cuda.set_per_process_memory_fraction(float(os.environ["C172_GPU_MEM"]))
    model, _ = load_policy(a.pilot, a.device)
    rp = R.RemotePool(a.workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, a.workers, device=a.device)
        gm.play(alld, 2, a.seed, pairs=pairs, pair_keys=keys, round_turns=[20, 45])
        print("C180 parts", a.type, a.pilot, gm.last, flush=True)
        rows = [{"i": r["i"], "j": r["j"], "seed": r["seed"], "iSeat": r["iSeat"], "winner": r["winner"], "ending": r.get("ending"), "error": r.get("error")} for r in gm.results]
        Path(ROOT / a.out).write_text(json.dumps({"pilot": a.pilot, "type": a.type, "seed": a.seed, "last": gm.last, "results": rows}), encoding="utf-8")
    finally:
        rp.close()


if __name__ == "__main__":
    main()
