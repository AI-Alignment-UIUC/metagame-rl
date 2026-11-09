"""C154 (runs/probe/C154-value-signal/record.md, with Amendment 1): a harness run with the focus seat's value logged at the start of its own
turns 2, 3 and 4 (notes/scripts/audit/c154_worker.js around env/remote_worker.js; log only). --arm D replays C145's cell D
(notes/scripts/c145_run.py: the loop's pilot on C127 s16's population, each deck against its 4 Energy -> 2 Oak + 2 Bill copy, 23 drawn
opponents, seed-91 deals); --arm L is C146's cell B design (notes/scripts/c142_run.py --groups draw --arm G with the loop's pilot: the
California lists against their draw -> Energy copies). The harness's own output and <out>.values.jsonl (one line a game). Read with
notes/scripts/c154_read.py.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c154_run.py --arm D --out runs/probe/C154-value-signal/D_s91.json [--limit 10] [--keep 5]
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
LOOP = "runs/screens/C127-R1-K-paired-ledger-s16/checkpoint.pt"
WORKER = str(ROOT / "notes/scripts/audit/c154_worker.js")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["D", "L"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--keep", type=int, default=0, help="logged states a worker that carry their observation (the acceptance)")
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    values = ROOT / (a.out[:-5] + ".values.jsonl" if a.out.endswith(".json") else a.out + ".values.jsonl")
    values.parent.mkdir(parents=True, exist_ok=True)
    values.unlink(missing_ok=True)
    os.environ["C154_OUT"], os.environ["C154_KEEP"] = str(values), str(a.keep)
    common = ["--seed", "91", "--games", "2", "--workers", str(a.workers), "--out", a.out] + (["--limit", str(a.limit)] if a.limit else [])
    if a.arm == "D":
        import c145_run as H
        sys.argv = ["c145_run.py", "--pilot", LOOP] + common
    else:
        import c142_run as H
        sys.argv = ["c142_run.py", "--groups", "draw", "--arm", "G", "--pilot", LOOP] + common
    _popen = subprocess.Popen                        # after the imports (a library subclasses Popen as it loads): only the game
    subprocess.Popen = lambda cmd, *x, **kw: _popen(  # workers are swapped, the harness's own node calls run as they are
        ["node", WORKER] if any("remote_worker" in str(c) for c in cmd) else cmd, *x, **kw)
    H.main()


if __name__ == "__main__":
    main()
