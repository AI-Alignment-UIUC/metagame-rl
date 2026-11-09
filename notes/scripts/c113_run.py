"""C113 (runs/probe/C113-end-rule/record.md): the lists against their Energy copies under one end rule, with every game kept.
Pairs as trainer_value.py: M's copies (energy+6#0..3: 6 random Trainers -> the list's basic Energy) and the four focus cards
(PlusPower, Gust of Wind, Item Finder, Scoop Up), each turned into Energy; the same pilot on both sides, pair-keyed deals.
--rule cap ([20, 45] game turns, the Prize lead wins at time), untimed (to completion) or T (a fixed cap of T game turns).
Writes <out>: {"results": per game (i, j, iSeat, winner, ending, turns, ...), "pairs", "decks"}. Evaluation only.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c113_run.py --pilot runs/probe/BENCH/arm-arm0-s1/pilot.pt --rule cap --seed 91 --out <json>
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
from rl.decks import Pool                       # noqa: E402
from rl.gpu_matrix import GpuMatrix, load_policy  # noqa: E402
from rl.remote import RemotePool                # noqa: E402
from trainer_value import variants              # noqa: E402

GROUPS = [f"energy+6#{r}" for r in range(4)] + ["PlusPower", "Gust of Wind", "Item Finder", "Scoop Up"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--rule", required=True, help="cap, untimed, or an integer T")
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--games", type=int, default=256)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    decks = json.loads((ROOT / "runs/probe/BENCH/decks_P.json").read_text(encoding="utf-8"))
    alld, pairs = variants(Pool(), decks, GROUPS)
    rounds = [20, 45] if a.rule == "cap" else 0 if a.rule == "untimed" else int(a.rule)
    model, _ = load_policy(a.pilot, a.device)
    rp = RemotePool(a.workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, a.workers, device=a.device)
        gm.play(alld, a.games, a.seed, pairs=[(p["base"], p["variant"]) for p in pairs], pair_keys=[p["base"] for p in pairs],
                round_turns=rounds)
        print(a.rule, gm.last, flush=True)
        res = {"pilot": a.pilot, "rule": a.rule, "round_turns": rounds, "seed": a.seed, "games": a.games, "last": gm.last,
               "pairs": pairs, "deck_names": [d["name"] for d in alld], "results": gm.results}
    finally:
        rp.close()
    Path(ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(ROOT / a.out).write_text(json.dumps(res), encoding="utf-8")


if __name__ == "__main__":
    main()
