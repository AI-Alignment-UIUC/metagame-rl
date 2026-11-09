"""C175's Amendment 1 (runs/probe/C175-trainers-strong-bodies/record.md): Y, G and E2 bodies against a common field, C162's rules-only decks as printed. C49-sd, greedy, round rule [20, 45], seed 175: pods 0-5 of the class's decks, 1,000 games a pod, each round every deck meeting a random field deck, the seats split at random. Saved after every pod. Read by c175_read.py: C165's fit with the field's decks in the design.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c175_field.py --cell Y --workers 4 --out runs/probe/C175-trainers-strong-bodies/Y/field_games.json
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
D = ROOT / "runs/probe/C175-trainers-strong-bodies"
FIELD = ROOT / "runs/probe/C163-draw-deck-field/R.json"
POD, PODS, ROUNDS, SEED = 200, 6, 5, 175


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True)
    ap.add_argument("--pilot", default="runs/pilot/C49-sd/model_it00199.pt")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--pods", type=int, default=PODS)
    ap.add_argument("--rounds", type=int, default=ROUNDS)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import rl.remote as R
    from rl.gpu_matrix import GpuMatrix, load_policy
    decks = json.loads((D / a.cell / "decks.json").read_text(encoding="utf-8"))
    field = [{"name": d["name"], "cards": list(d["cards"])} for d in json.loads(FIELD.read_text(encoding="utf-8"))]
    n = len(decks)
    if os.environ.get("C172_GPU_MEM"):
        import torch
        torch.cuda.set_per_process_memory_fraction(float(os.environ["C172_GPU_MEM"]))
    model, _ = load_policy(a.pilot, a.device)
    rp = R.RemotePool(a.workers)
    rp.pace = 0.25
    res, games, secs, errors, endings = [], 0, 0.0, 0, {}
    try:
        gm = GpuMatrix.attach(model, rp, a.workers, device=a.device)
        for pod in range(a.pods):
            rng = np.random.default_rng(SEED * 1000 + pod)
            sub = decks[pod * POD:(pod + 1) * POD] + field
            pairs = []
            for _ in range(a.rounds):
                for k in range(POD):
                    o = POD + int(rng.integers(len(field)))
                    pairs.append((k, o) if rng.random() < 0.5 else (o, k))
            gm.play(sub, 1, SEED + pod, pairs=pairs, round_turns=[20, 45])
            for x in gm.results:
                to = lambda i: i + pod * POD if i < POD else n + i - POD     # the design: class decks first, then the field
                res.append({"i": to(x["i"]), "j": to(x["j"]), "seed": x["seed"], "iSeat": x["iSeat"], "winner": x["winner"], "ending": x.get("ending"), "error": x.get("error")})
            games += gm.last["games"]
            secs += gm.last["seconds"]
            errors += gm.last["errors"]
            for k, v in gm.last["endings"].items():
                endings[k] = endings.get(k, 0) + v
            print(f"pod {pod}: {gm.last['games']} games, {gm.last['seconds']} s, errors {gm.last['errors']}", flush=True)
            Path(ROOT / a.out).write_text(json.dumps({"pilot": a.pilot, "cell": a.cell, "last": {"games": games, "seconds": round(secs, 1), "games_per_s": round(games / max(secs, 1e-9), 1), "errors": errors, "endings": endings}, "results": res}), encoding="utf-8")
    finally:
        rp.close()
    print("C175 field", a.cell, {"games": games, "seconds": round(secs, 1), "games_per_s": round(games / max(secs, 1e-9), 1), "errors": errors, "endings": endings}, flush=True)


if __name__ == "__main__":
    main()
