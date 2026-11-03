"""C145 (runs/probe/C145-draw-context/record.md) cells C and D: the drafting loop's own decks (C127 s16's population_it0029.pt) each
against a copy with 4 of its basic Energy (commonest first) turned into 2 Professor Oak and 2 Bill, fewer of either where the copy
limit of 4 binds (the count is recorded). Each deck and its copy play the same --opps opponents drawn from the population (seeded,
without replacement) on the same deals (one pair key a deck and opponent), greedy on both seats, round rule [20, 45]. --pilot is
arm 0 s1 (C) or the loop's own checkpoint (D). Cells A and B are notes/scripts/c142_run.py --groups draw --arm G. Read with
notes/scripts/c145_read.py (positive means the draw copy beats its deck).
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c145_run.py --pilot runs/probe/BENCH/arm-arm0-s1/pilot.pt --out runs/probe/C145-draw-context/C_s91.json
--decks FILE (C162): a [{name, cards}] deck set in place of the population, opponents drawn from it the same way.
--field FILE (C163): opponents drawn from this [{name, cards}] set instead, never the entry named by the deck's own "src".
--spread (C163's timed pilot): --limit keeps evenly spaced keys across the decks, not the first N.
--no-copies (C167): only the decks' own games, on the same keys and deals as a run with copies.
--search (C173): C139's search on both seats. --worker FILE: a log-only worker in place of env/remote_worker.js, writing to OUT.trace.jsonl. C172_GPU_MEM in the environment lowers the memory cap alone.
"""
import argparse
import collections
import json
import os
import random
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import rl.remote as R                             # noqa: E402
from rl.decks import Pool                         # noqa: E402
from rl.gpu_matrix import GpuMatrix, load_policy  # noqa: E402

POP = "runs/screens/C127-R1-K-paired-ledger-s16/population_it0029.pt"
ADD = {"Professor Oak": 2, "Bill": 2}


def draw_copy(card, by_name, cards):
    """The deck with up to 2 Oak and 2 Bill (under the copy limit of 4) in place of as many basic Energy, commonest first."""
    basics = [e for e, _ in collections.Counter(x for x in cards if card[x]["superType"] == 3 and card[x]["energyType"] == 0).most_common()]
    out, added = list(cards), {}
    pool = [e for e in basics for _ in range(cards.count(e))]       # the deck's basic Energy, commonest kind first
    for name, k in ADD.items():
        have = sum(1 for x in out if card[x]["name"] == name)
        for _ in range(min(k, 4 - have)):
            if not pool:
                break
            out[out.index(pool.pop(0))] = by_name[name]
            added[name] = added.get(name, 0) + 1
    return out, added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--population", default=POP)
    ap.add_argument("--decks", default="", help="C162: a [{name, cards}] JSON deck set in place of --population")
    ap.add_argument("--field", default="", help="C163: a [{name, cards}] opponent set, unmodified")
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--games", type=int, default=2, help="deals a (deck or copy, opponent) pair")
    ap.add_argument("--opps", type=int, default=23, help="opponents a deck, drawn from the population")
    ap.add_argument("--limit", type=int, default=0, help="the first N (deck, opponent) keys only (the smoke)")
    ap.add_argument("--spread", action="store_true", help="C163: --limit keeps evenly spaced keys, not the first N")
    ap.add_argument("--no-copies", action="store_true", help="C167: only the decks' own games, on the same keys and deals")
    ap.add_argument("--search", action="store_true", help="C173: C139's search on both seats")
    ap.add_argument("--worker", default="", help="C173: a log-only worker, writing to OUT.trace.jsonl")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pool = Pool()
    card = {c["fullName"]: c for c in pool.cards}
    by_name = {}
    for c in pool.cards:                          # Oak and Bill as the population decks print them (Base Set)
        if c["name"] in ADD and c["fullName"].endswith(" BS"):
            by_name[c["name"]] = c["fullName"]
    if a.decks:
        decks = [{"name": d["name"], "cards": list(d["cards"]), "src": d.get("src")} for d in json.loads((ROOT / a.decks).read_text(encoding="utf-8"))]
    else:
        pop = torch.load(ROOT / a.population, map_location="cpu", weights_only=False)["population"]
        decks = [{"name": f"pop{p['id']}", "cards": list(p["deck"])} for p in pop]
    n0 = len(decks)
    alld, vp = list(decks), []
    for k, d in enumerate(decks):
        cards, added = draw_copy(card, by_name, d["cards"])
        if added:
            vp.append({"base": k, "variant": len(alld), "group": "oakbill", "replaced": sum(added.values()), "added": added})
            alld.append({"name": d["name"] + "-oakbill", "cards": cards})
    rng = random.Random(145)
    pairs, keys, meta = [], [], []
    field = [{"name": d["name"], "cards": list(d["cards"])} for d in json.loads((ROOT / a.field).read_text(encoding="utf-8"))] if a.field else []
    f0 = len(alld)                                # where a --field sits in alld
    alld += field
    for v in vp:
        k = v["base"]
        cand = [f0 + x for x, f in enumerate(field) if f["name"] != decks[k]["src"]] if field else [x for x in range(n0) if x != k]
        for o in sorted(rng.sample(cand, a.opps)):
            key = k * (len(alld) if field else n0) + o
            pairs += [(k, o)] if a.no_copies else [(k, o), (v["variant"], o)]
            keys += [key] if a.no_copies else [key, key]
            meta.append({"key": key, "list": k, "opp": o, "copies": {"oakbill": v["variant"]}})
    if a.limit:
        keep = {m["key"] for m in (meta[::max(1, len(meta) // a.limit)][:a.limit] if a.spread else meta[:a.limit])}
        sel = [k in keep for k in keys]
        pairs, keys = [p for p, s in zip(pairs, sel) if s], [k for k, s in zip(keys, sel) if s]
        meta = [m for m in meta if m["key"] in keep]
    if os.environ.get("C172_GPU_MEM"):
        torch.cuda.set_per_process_memory_fraction(float(os.environ["C172_GPU_MEM"]))
    if a.worker:
        _popen = R.subprocess.Popen
        R.subprocess.Popen = lambda cmd, **kw: _popen(["node", str(ROOT / a.worker)], **kw)
        trace = ROOT / (a.out + ".trace.jsonl")
        trace.unlink(missing_ok=True)
        os.environ["C173_OUT"] = str(trace)
    model, _ = load_policy(a.pilot, a.device)
    rp = R.RemotePool(a.workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, a.workers, device=a.device)
        search = None
        if a.search:
            sys.path.insert(0, str(ROOT / "notes" / "scripts"))
            from c139_run import SEARCH
            search = SEARCH
        gm.play(alld, a.games, a.seed, pairs=pairs, pair_keys=keys, round_turns=[20, 45], search=search)
        print("C145", a.pilot, a.seed, gm.last, flush=True)
        res = {"pilot": a.pilot, "population": a.decks or a.population, "seed": a.seed, "games": a.games, "round_turns": [20, 45], "search": search,
               "arm": "G", "groups": ["oakbill"], "last": gm.last, "meta": meta, "variants": vp, "deck_names": [d["name"] for d in alld],
               "deck_cards": [d["cards"] for d in alld], "results": gm.results}
    finally:
        rp.close()
    Path(ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(ROOT / a.out).write_text(json.dumps(res), encoding="utf-8")


if __name__ == "__main__":
    main()
