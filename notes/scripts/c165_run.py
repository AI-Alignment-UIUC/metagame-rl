"""C165 (runs/probe/C165-trainer-factorial/record.md): a factorial read of every Trainer's value per copy, evaluation only. --make-decks writes 4,000
concentrated rules-only decks (rl.decks.wide_deck, seed 165) in 20 pods of 200 and checks them. The games stay within a pod: each round is a random perfect
matching of its 200 decks, greedy, round rule [20, 45], one deal a pair, no copies and no pairing. A deal seed is unique to its pod, round and pair, and the
same under every pilot; deck i takes seat 1, and which deck is i is random. 10 rounds is about 20,000 games, each deck in 10. Read with notes/scripts/c165_read.py.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c165_run.py --make-decks
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c165_run.py --pilot runs/probe/BENCH/arm-arm0-s1/pilot.pt --rounds 1 --out runs/probe/C165-trainer-factorial/pilot_arm0.json
--seed S --dir D (C171): the same design at another seed, its decks in another folder.
--search --first-pod A --last-pod B (C173's stage B1): C139's search on both seats, pods A to B - 1, saved after every pod, so a stop keeps what's played. C172_GPU_MEM in the environment lowers the memory cap alone.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "runs/probe/C165-trainer-factorial"
PODS, POD, SEED = 20, 200, 165


def schedule(pod, rounds):
    """Pairs of pod-local deck indices: `rounds` random perfect matchings of the pod, the same for every pilot."""
    rng = np.random.default_rng(SEED * 1000 + pod)
    pairs = []
    for _ in range(rounds):
        p = rng.permutation(POD)
        pairs += [(int(p[k]), int(p[k + 1])) for k in range(0, POD, 2)]
    return pairs


def make_decks(concentrated=True):
    from rl.decks import Pool, deck_shape, wide_deck
    pool = Pool()
    card = {c["fullName"]: c for c in pool.cards}
    rng = np.random.default_rng(SEED)
    decks, shapes = [], []
    for n in range(PODS * POD):
        v = wide_deck(pool, rng, concentrated=concentrated)
        assert pool.legal(v) and int(v.sum()) == 60
        cards = pool.names(v)
        assert not concentrated or not any(card[x]["superType"] == 3 and card[x]["energyType"] != 0 for x in cards), "special Energy"
        s = deck_shape(pool, v)
        shapes.append((s["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"]))
        decks.append({"name": f"P{n // POD}.{n % POD}", "cards": cards})
    (OUT / "decks.json").write_text(json.dumps(decks), encoding="utf-8")
    sh = np.array(shapes, dtype=float)
    held = {}
    for d in decks:
        for name in {card[x]["name"] for x in d["cards"] if card[x]["superType"] == 2}:
            held[name] = held.get(name, 0) + 1
    print(f"{len(decks)} decks, all legal, 60 cards{', no special Energy' if concentrated else ''}; mean P/T/E {np.round(sh.mean(0), 2).tolist()}, SD {np.round(sh.std(0), 2).tolist()}; "
          f"Trainers {len(held)}, fewest decks holding one {min(held.values())}")
    assert len(held) == 42 and min(held.values()) >= 100, "a Trainer in under 100 decks"


def main():
    global OUT, SEED
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-decks", action="store_true")
    ap.add_argument("--plain", action="store_true", help="C171's Amendment 1: --make-decks with standard wide decks, special Energy allowed")
    ap.add_argument("--pilot", default="")
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", default="")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--dir", default="", help="C171: the folder for decks.json, instead of C165's")
    ap.add_argument("--search", action="store_true", help="C173: C139's search on both seats")
    ap.add_argument("--full-width", action="store_true", help="C173's Amendment 3: with --search, C135's set instead: every legal move at Trainer-playable decisions")
    ap.add_argument("--sampled", action="store_true", help="C176: sampled play, as the loop's population games (rl/metagame.py), on the same decks, pairs and deals")
    ap.add_argument("--caps", action="store_true", help="C173, after #827: greedy games through the log-only worker, MAX_TURN_STEPS hits to OUT.caps")
    ap.add_argument("--first-pod", type=int, default=0)
    ap.add_argument("--last-pod", type=int, default=PODS)
    a = ap.parse_args()
    SEED = a.seed
    if a.dir:
        OUT = ROOT / a.dir
        OUT.mkdir(parents=True, exist_ok=True)
    if a.make_decks:
        return make_decks(not a.plain)
    import rl.remote as R
    from rl.gpu_matrix import GpuMatrix, load_policy
    decks = json.loads((OUT / "decks.json").read_text(encoding="utf-8"))
    search = None
    if a.caps and not a.search:
        _popen = R.subprocess.Popen
        R.subprocess.Popen = lambda cmd, **kw: _popen(["node", str(ROOT / "notes/scripts/audit/c173_dose_worker.js")], **kw)
        caps = ROOT / (a.out + ".caps")
        caps.unlink(missing_ok=True)
        os.environ["C173_CAPS"] = str(caps)
    if a.search:
        _popen = R.subprocess.Popen                      # research's #806: a log-only worker counts searched decisions per game
        R.subprocess.Popen = lambda cmd, **kw: _popen(["node", str(ROOT / "notes/scripts/audit/c173_dose_worker.js")], **kw)
        dose = ROOT / (a.out + ".dose.jsonl")
        dose.unlink(missing_ok=True)
        os.environ["C173_DOSE"] = str(dose)
        sys.path.insert(0, str(ROOT / "notes" / "scripts"))
        from c139_run import SEARCH
        search = {**SEARCH, "k": 64, "allTrainers": False} if a.full_width else SEARCH
    if os.environ.get("C172_GPU_MEM"):
        import torch
        torch.cuda.set_per_process_memory_fraction(float(os.environ["C172_GPU_MEM"]))
    model, _ = load_policy(a.pilot, a.device)
    rp = R.RemotePool(a.workers)
    rp.pace = 0.25
    res, n, secs, errors, endings = [], 0, 0.0, 0, {}
    try:
        gm = GpuMatrix.attach(model, rp, a.workers, device=a.device, greedy=not a.sampled)
        for pod in range(a.first_pod, a.last_pod):
            pairs = schedule(pod, a.rounds)
            gm.play(decks[pod * POD:(pod + 1) * POD], 1, SEED + pod, pairs=pairs, round_turns=[20, 45], search=search)
            for x in gm.results:
                res.append({"i": x["i"] + pod * POD, "j": x["j"] + pod * POD, "seed": x["seed"], "iSeat": x["iSeat"], "winner": x["winner"], "ending": x.get("ending"),
                            "error": x.get("error")})
            n += gm.last["games"]
            secs += gm.last["seconds"]
            errors += gm.last["errors"]
            for k, v in gm.last["endings"].items():
                endings[k] = endings.get(k, 0) + v
            print(f"pod {pod}: {gm.last['games']} games, {gm.last['seconds']} s, errors {gm.last['errors']}", flush=True)
            if a.search or a.last_pod - a.first_pod > 1:  # a slow arm keeps every finished pod, and a stage's kill keeps them too
                Path(ROOT / a.out).write_text(json.dumps({"pilot": a.pilot, "rounds": a.rounds, "search": search, "pods_done": pod + 1 - a.first_pod, "last": {"games": n, "seconds": round(secs, 1), "games_per_s": round(n / max(secs, 1e-9), 1), "errors": errors, "endings": endings}, "results": res}), encoding="utf-8")
    finally:
        rp.close()
    last = {"games": n, "seconds": round(secs, 1), "games_per_s": round(n / max(secs, 1e-9), 1), "errors": errors, "endings": endings}
    print("C165", a.pilot, last, flush=True)
    Path(ROOT / a.out).write_text(json.dumps({"pilot": a.pilot, "rounds": a.rounds, "last": last, "results": res}), encoding="utf-8")


if __name__ == "__main__":
    main()
