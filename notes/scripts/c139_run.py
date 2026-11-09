"""C139 (runs/probe/C139-pp-field-price/record.md): PlusPower's price against a field. Each California list with PlusPower (env/decks.js
archivedDecks; notes/scripts/trainer_value.py variants: every PlusPower turned into the list's commonest basic Energy) and its copy play
every other California list on the same deals (rl/gpu_matrix.py pair_keys: list-against-opponent and copy-against-opponent share a key,
so the same seeds and seats), --games deals a pair, round rule [20, 45], arm 0 s1 on both seats. --arm G greedy; S both seats with C138's
search (env/agents.js PolicySearchAgent at Trainer-playable decisions, the policy's top 3 plus every legal Trainer play, dets 2, CRN,
horizon 1, scored by V; env/remote_worker.js judgeSearch). Read with notes/scripts/c139_read.py.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c139_run.py --arm S --games 2 --out runs/probe/C139-pp-field-price/S_s91.json
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
from rl.decks import Pool                         # noqa: E402
from rl.gpu_matrix import GpuMatrix, load_policy  # noqa: E402
from trainer_value import variants                # noqa: E402

SEARCH = {"k": 3, "dets": 2, "maxSteps": 40, "crn": True, "trainerOnly": True, "allTrainers": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default="runs/probe/BENCH/arm-arm0-s1/pilot.pt")
    ap.add_argument("--arm", choices=["G", "S"], required=True)
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--games", type=int, default=2, help="deals a (list or copy, opponent) pair")
    ap.add_argument("--limit", type=int, default=0, help="the first N paired keys only (the timed pilot and smoke)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--round-turns", default="20-45", help='C140: the round clock in game turns, "A-B", "T" or "off"')
    ap.add_argument("--max-turns", type=int, default=0, help="C140: the safety turn cap (with --round-turns off: 200)")
    ap.add_argument("--score", choices=["value", "prizes"], default="value",
                    help="C141: judgeSearch's line score (prizes: C132's 10 x Prizes + V; an evaluation-only oracle, row 86)")
    ap.add_argument("--horizon", type=int, default=1, help="C143: the search's horizon in game turns (R3: 3)")
    ap.add_argument("--dets", type=int, default=SEARCH["dets"], help="C143: the search's determinizations (R3: 4)")
    ap.add_argument("--max-steps", type=int, default=SEARCH["maxSteps"], help="C143: a line's step cap (R3: 120, C132b's, so no line is cut)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = subprocess.run(["node", "-e", "const {archivedDecks}=require('./env/decks.js');console.log(JSON.stringify(archivedDecks()))"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    decks = json.loads(out.stdout)
    n0 = len(decks)
    alld, vp = variants(Pool(), decks, ["PlusPower"])
    pairs, keys, meta = [], [], []
    for v in vp:                                          # v: {base, variant, group}
        for o in range(n0):
            if o == v["base"]:
                continue
            key = v["base"] * n0 + o
            pairs += [(v["base"], o), (v["variant"], o)]
            keys += [key, key]
            meta.append({"key": key, "list": v["base"], "copy": v["variant"], "opp": o})
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
        rt = 0 if a.round_turns == "off" else [int(x) for x in a.round_turns.split("-")] if "-" in a.round_turns else int(a.round_turns)
        search = {**SEARCH, **({"score": "prizes"} if a.score == "prizes" else {}),
                  **({"horizon": a.horizon} if a.horizon != 1 else {}), "dets": a.dets, "maxSteps": a.max_steps} if a.arm == "S" else None
        gm.play(alld, a.games, a.seed, pairs=pairs, pair_keys=keys, round_turns=rt, search=search,
                max_turns=a.max_turns)
        print(a.arm, a.seed, gm.last, flush=True)
        res = {"pilot": a.pilot, "arm": a.arm, "seed": a.seed, "games": a.games, "round_turns": rt, "max_turns": a.max_turns, "search": search,
               "last": gm.last, "meta": meta, "variants": vp, "deck_names": [d["name"] for d in alld],
               "deck_cards": [d["cards"] for d in alld], "results": gm.results}
    finally:
        rp.close()
    Path(ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(ROOT / a.out).write_text(json.dumps(res), encoding="utf-8")


if __name__ == "__main__":
    main()
