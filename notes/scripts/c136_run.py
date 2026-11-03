"""C136 (runs/probe/C136-pp-price-search/record.md; copy of c122_run.py): bench lists with PlusPower (3, 1, 21: decks_P 0-2) against
their PlusPower -> basic Energy copies (C111's pairs), arm 0 s1 on both seats, round rule [20, 45], --arm G (greedy), SPP (C135's full-
width search, k 64, dets 2, CRN, horizon 1, scored by V, only where a PlusPower play is legal: env/agents.js searchKey) or ST (the same
at every Trainer-playable decision), both seats. Through notes/scripts/audit/c136_worker.js (C114's trace with the search-copy guard,
and per-attack b10 rows). Output: --out (results), <out>.trace.jsonl, <out>.b10.jsonl.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c136_run.py --arm SPP --seed 91 --games 256 --out runs/probe/C136-pp-price-search/SPP_s91.json
C122's notes follow.
C122 stage A (runs/probe/C122-L-search/record.md): M and the four focus prices with the pilot's own decision-time search at
Trainer-playable main-phase decisions (arm S) against the same pilot greedy (arm G), on the same deals. Evaluation only.
C113's pairs (energy+6#0..3 and the four focus cards, each list against its copy), the same pilot on both sides, the cap
[20, 45]. Arm S: both seats are env/agents.js PolicySearchAgent with trainerOnly and includeTrainer (C122's options): at a
main-phase decision where a Trainer play is legal, the top 3 options by the policy with a Trainer play always among them, on
2 CRN copies to the turn's end scored by the pilot's value, the best taken; every other decision is the pilot's greedy one.
--trace writes C114's per-turn trace (notes/scripts/audit/pace_worker2.js, log only) for the play readouts. Read with
notes/scripts/c113_read.py (event points) and notes/scripts/c122_read.py.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c122_run.py --arm S --seed 91 --games 128 --out runs/probe/C122-L-search/S_s91.json
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import rl.remote as R                           # noqa: E402
from rl.decks import Pool                       # noqa: E402
from rl.gpu_matrix import GpuMatrix, load_policy  # noqa: E402
from trainer_value import variants              # noqa: E402

GROUPS = ["PlusPower"]
FULL = {"k": 64, "dets": 2, "maxSteps": 40, "crn": True, "includeTrainer": False}
SEARCH = {"SPP": {**FULL, "searchKey": "trainer|PlusPower"}, "ST": {**FULL, "trainerOnly": True}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default="runs/probe/BENCH/arm-arm0-s1/pilot.pt")
    ap.add_argument("--arm", choices=["G", "SPP", "ST"], required=True)
    ap.add_argument("--lists", type=int, nargs="*", default=[0, 1, 2])
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--games", type=int, default=128, help="games a pair")
    ap.add_argument("--groups", nargs="*", default=GROUPS)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--trace", help="a jsonl for C114's per-turn trace (pace_worker2.js)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    decks = json.loads((ROOT / "runs/probe/BENCH/decks_P.json").read_text(encoding="utf-8"))
    alld, pairs = variants(Pool(), decks, a.groups)
    pairs = [p for p in pairs if p["base"] in a.lists]
    worker = str(ROOT / "notes/scripts/audit/c136_worker.js")          # after the decks: R.subprocess is the subprocess module
    _popen = R.subprocess.Popen
    R.subprocess.Popen = lambda cmd, **kw: _popen(["node", worker], **kw)
    out = Path(ROOT / a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for suffix, env in ((".trace.jsonl", "PACE_TRACE_OUT"), (".b10.jsonl", "C136_B10")):
        f = out.with_suffix(suffix)
        f.unlink(missing_ok=True)
        os.environ[env] = str(f)
    model, _ = load_policy(a.pilot, a.device)
    rp = R.RemotePool(a.workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, a.workers, device=a.device)
        gm.play(alld, a.games, a.seed, pairs=[(p["base"], p["variant"]) for p in pairs], pair_keys=[p["base"] for p in pairs],
                round_turns=[20, 45], search=SEARCH.get(a.arm))
        print(a.arm, a.seed, gm.last, flush=True)
        res = {"pilot": a.pilot, "arm": a.arm, "rule": "cap", "round_turns": [20, 45], "seed": a.seed, "games": a.games,
               "search": SEARCH.get(a.arm), "last": gm.last, "pairs": pairs, "deck_names": [d["name"] for d in alld],
               "results": gm.results}
    finally:
        rp.close()
    Path(ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(ROOT / a.out).write_text(json.dumps(res), encoding="utf-8")


if __name__ == "__main__":
    main()
