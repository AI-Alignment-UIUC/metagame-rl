"""C154's acceptance (runs/probe/C154-value-signal/record.md): the logged V matches a direct evaluation of the same state. Reads the first
--n logged states that carry their encoded observation (notes/scripts/audit/c154_worker.js with --keep) from a smoke's .values.jsonl,
evaluates the loop's pilot on them as rl/remote.py's server does (the seven token arrays, batch first, the same dtypes), and reports the
largest |V_logged - V_direct| (the record: within 1e-4).
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c154_accept.py runs/probe/C154-value-signal/D_smoke.values.jsonl
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.gpu_matrix import load_policy             # noqa: E402

FIELDS = (("tokCard", np.int16), ("tokKind", np.uint8), ("tokAux", np.uint8), ("glob", np.uint8), ("slots", np.uint8),
          ("cand", np.int16), ("nCand", np.int32))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("values")
    ap.add_argument("--pilot", default="runs/screens/C127-R1-K-paired-ledger-s16/checkpoint.pt")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()
    states = [o for l in open(a.values, encoding="utf-8") for o in json.loads(l).get("obs", [])][:a.n]
    model, _ = load_policy(a.pilot, a.device)
    inputs = [torch.from_numpy(np.array([s[k] for s in states], dtype=dt)).to(a.device) for k, dt in FIELDS]
    inputs[-1] = inputs[-1].view(-1)
    with torch.no_grad():
        _, value = model(*inputs)
    direct = value.float().cpu().numpy().reshape(-1)
    logged = np.array([s["value"] for s in states], dtype=np.float64)
    diff = np.abs(direct - logged)
    print(json.dumps({"states": len(states), "logged": np.round(logged, 6).tolist(), "direct": np.round(direct, 6).tolist(),
                      "max_abs_diff": float(diff.max()), "within_1e-4": bool(diff.max() <= 1e-4)}))


if __name__ == "__main__":
    main()
