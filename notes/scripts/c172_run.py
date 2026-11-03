"""C172 (runs/probe/C172-offlist-names/record.md, with Amendment 1): are the table's off-list colourless Basics as good as the lists' own attackers? For each list, its most-copied Basic with no evolution in the deck (and an attack that does damage; ties by name) replaced by Tauros,
Lickitung, Kangaskhan or Snorlax at the same copies, one copy a name a list, the rest of the list unchanged; a list already holding the name, or with no such Basic, is skipped for it, and each variant records whether the swapped card was the list's most-copied Basic. Each list and its copies play the same 12 other lists on the same deals (one key a list and opponent), 2 deals. --arm G is greedy on
both seats; --arm S is C139's search on both seats. Seaking and Weepinbell need a line and typed Energy, so they get no price here, only C171's trace read. Read with notes/scripts/c172_read.py.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c172_run.py --pilot runs/probe/BENCH/arm-arm0-s1/pilot.pt --arm G --out runs/probe/C172-offlist-names/G_arm0.json
"""
import argparse
import collections
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import torch                                      # noqa: E402
import rl.remote as R                             # noqa: E402
from rl.decks import Pool                         # noqa: E402
from rl.gpu_matrix import GpuMatrix, load_policy  # noqa: E402
from c139_run import SEARCH                       # noqa: E402

NAMES = {"Tauros": "Tauros JU", "Lickitung": "Lickitung JU", "Kangaskhan": "Kangaskhan JU", "Snorlax": "Snorlax JU"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--arm", choices=["G", "S"], required=True)
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--games", type=int, default=2)
    ap.add_argument("--opps", type=int, default=12)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--part", default="", help="K/N: only the keys with index K mod N, so a slow arm keeps what it has played")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    worker = str(ROOT / "notes/scripts/audit/c172_worker.js")   # log only: what a player does while its Active is Paralyzed
    _popen = R.subprocess.Popen
    R.subprocess.Popen = lambda cmd, **kw: _popen(["node", worker], **kw)
    trace = ROOT / (a.out + ".paralyzed.jsonl")
    trace.unlink(missing_ok=True)
    os.environ["C172_OUT"] = str(trace)
    pool = Pool()
    card = {c["fullName"]: c for c in pool.cards}
    lists = [{"name": d["name"], "cards": list(d["cards"])} for d in json.loads((ROOT / "runs/probe/C163-draw-deck-field/L.json").read_text(encoding="utf-8"))]
    n0 = len(lists)
    alld, vp, dropped = list(lists), [], []
    for k, d in enumerate(lists):
        mons = collections.Counter(card[x]["name"] for x in d["cards"] if card[x]["superType"] == 1)
        is_basic = lambda n: any(c["name"] == n and c["stage"] == 2 for c in card.values())
        attacks = lambda n: any(c["name"] == n and any(t.get("damage", 0) > 0 for t in c.get("attacks", [])) for c in card.values())
        evolved_from = {card[x].get("evolvesFrom") for x in d["cards"] if card[x]["superType"] == 1}
        all_basics = sorted((n for n in mons if is_basic(n)), key=lambda n: (-mons[n], n))
        free = [n for n in all_basics if n not in evolved_from and attacks(n)]
        if not free:
            dropped.append(d["name"])
            continue
        target = free[0]
        for name, full in NAMES.items():
            if name in mons:
                continue
            cards = [full if card[x]["name"] == target else x for x in d["cards"]]
            assert len(cards) == 60 and pool.legal(pool.vector(cards)), d["name"]
            vp.append({"base": k, "variant": len(alld), "group": name, "replaced": mons[target], "target": target, "is_top_basic": target == all_basics[0]})
            alld.append({"name": f"{d['name']}-{name}", "cards": cards})
    rng = random.Random(172)
    pairs, keys, meta = [], [], []
    for k in range(n0):
        cs = [v for v in vp if v["base"] == k]
        if not cs:
            continue
        for o in sorted(rng.sample([x for x in range(n0) if x != k], a.opps)):
            key = k * n0 + o
            pairs += [(k, o)] + [(v["variant"], o) for v in cs]
            keys += [key] * (1 + len(cs))
            meta.append({"key": key, "list": k, "opp": o, "copies": {v["group"]: v["variant"] for v in cs}})
    if a.limit:
        keep = {m["key"] for m in meta[::max(1, len(meta) // a.limit)][:a.limit]}
        sel = [k in keep for k in keys]
        pairs, keys = [p for p, s in zip(pairs, sel) if s], [k for k, s in zip(keys, sel) if s]
        meta = [m for m in meta if m["key"] in keep]
    if a.part:
        k, parts = (int(x) for x in a.part.split("/"))
        keep = {m["key"] for i, m in enumerate(meta) if i % parts == k}
        sel = [x in keep for x in keys]
        pairs, keys = [q for q, t in zip(pairs, sel) if t], [x for x, t in zip(keys, sel) if t]
        meta = [m for m in meta if m["key"] in keep]
    if os.environ.get("C172_GPU_MEM"):                   # RL_GPU_SHARE sets the pace and the memory cap together; this lowers only the cap, row 73's 80% with W beside it
        torch.cuda.set_per_process_memory_fraction(float(os.environ["C172_GPU_MEM"]))
    model, _ = load_policy(a.pilot, a.device)
    rp = R.RemotePool(a.workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, a.workers, device=a.device)
        search = SEARCH if a.arm == "S" else None
        gm.play(alld, a.games, a.seed, pairs=pairs, pair_keys=keys, round_turns=[20, 45], search=search)
        print("C172", a.pilot, a.arm, gm.last, flush=True)
        res = {"pilot": a.pilot, "arm": a.arm, "seed": a.seed, "games": a.games, "search": search, "last": gm.last, "meta": meta, "variants": vp, "dropped_lists": dropped, "deck_names": [d["name"] for d in alld],
               "deck_cards": [d["cards"] for d in alld], "results": gm.results}
    finally:
        rp.close()
    Path(ROOT / a.out).write_text(json.dumps(res), encoding="utf-8")


if __name__ == "__main__":
    main()
