"""C142 (runs/probe/C142-tempo-package/record.md): does the tempo package pay more than the sum of its cards? C139's field design and S
search (notes/scripts/c139_run.py: both seats, V-scored, the policy's top 3 plus every legal Trainer play) with more copies a list: one
single for each tempo card it runs (that card's copies turned into its commonest basic Energy; trainer_value.py variants), and one joint
copy with all four turned into Energy for lists running at least two. Each list and all its copies play every other California list
on the same deals (one pair key per list and opponent, so the same seeds and seats). Read with notes/scripts/c142_read.py.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c142_run.py --games 2 --out runs/probe/C142-tempo-package/S_s91.json
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import rl.remote as R                             # noqa: E402
import trainer_value as TV                        # noqa: E402
from rl.decks import Pool                         # noqa: E402
from rl.gpu_matrix import GpuMatrix, load_policy  # noqa: E402
from c139_run import SEARCH                       # noqa: E402

TEMPO = ("PlusPower", "Gust of Wind", "Item Finder", "Scoop Up")
TV.GROUPS["tempo4"] = TEMPO                       # the joint copy's group


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default="runs/probe/BENCH/arm-arm0-s1/pilot.pt")
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--games", type=int, default=2, help="deals a (list or copy, opponent) pair")
    ap.add_argument("--limit", type=int, default=0, help="the first N (list, opponent) keys only (the timed pilot and smoke)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--horizon", type=int, default=1, help="C143: the search's horizon in game turns (R3: 3)")
    ap.add_argument("--dets", type=int, default=SEARCH["dets"], help="C143: the search's determinizations (R3: 4)")
    ap.add_argument("--max-steps", type=int, default=SEARCH["maxSteps"], help="C143: a line's step cap (R3: 120, C132b's, so no line is cut)")
    ap.add_argument("--joint-only", action="store_true", help="C143: only the joint copies (and their lists)")
    ap.add_argument("--groups", nargs="+", default=None, help="C144: price these trainer_value GROUPS (e.g. draw) instead of the tempo four")
    ap.add_argument("--arm", choices=["G", "S"], default="S", help="C144: G plays both seats greedy (no search)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = subprocess.run(["node", "-e", "const {archivedDecks}=require('./env/decks.js');console.log(JSON.stringify(archivedDecks()))"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    decks = json.loads(out.stdout)
    n0 = len(decks)
    alld, vp = TV.variants(Pool(), decks, a.groups or list(TEMPO) + ["tempo4"])
    singles = {}
    for v in vp:
        if v["group"] != "tempo4":
            singles.setdefault(v["base"], []).append(v["group"])
    vp = [v for v in vp if v["group"] != "tempo4" or len(singles.get(v["base"], [])) >= 2]
    if a.joint_only:
        vp = [v for v in vp if v["group"] == "tempo4"]
        singles = {k: g for k, g in singles.items() if any(v["base"] == k for v in vp)}
    pairs, keys, meta = [], [], []
    for k in sorted(singles):                             # a list with at least one tempo card, its copies, each opponent
        for o in range(n0):
            if o == k:
                continue
            key = k * n0 + o
            cs = [v for v in vp if v["base"] == k]
            pairs += [(k, o)] + [(v["variant"], o) for v in cs]
            keys += [key] * (1 + len(cs))
            meta.append({"key": key, "list": k, "opp": o, "copies": {v["group"]: v["variant"] for v in cs}})
    if a.limit:
        keep = {m["key"] for m in meta[:a.limit]}
        sel = [k in keep for k in keys]
        pairs, keys = [p for p, s in zip(pairs, sel) if s], [k for k, s in zip(keys, sel) if s]
        meta = [m for m in meta if m["key"] in keep]
    model, _ = load_policy(a.pilot, a.device)
    rp = R.RemotePool(a.workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, a.workers, device=a.device)
        search = {**SEARCH, **({"horizon": a.horizon} if a.horizon != 1 else {}), "dets": a.dets, "maxSteps": a.max_steps}             if a.arm == "S" else None
        gm.play(alld, a.games, a.seed, pairs=pairs, pair_keys=keys, round_turns=[20, 45], search=search)
        print("C142", a.seed, gm.last, flush=True)
        res = {"pilot": a.pilot, "seed": a.seed, "games": a.games, "round_turns": [20, 45], "search": search, "tempo": TEMPO,
               "arm": a.arm, "groups": a.groups,
               "last": gm.last, "meta": meta, "variants": vp, "deck_names": [d["name"] for d in alld],
               "deck_cards": [d["cards"] for d in alld], "results": gm.results}
    finally:
        rp.close()
    Path(ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(ROOT / a.out).write_text(json.dumps(res), encoding="utf-8")


if __name__ == "__main__":
    main()
