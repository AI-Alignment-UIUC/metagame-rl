"""BENCH-P1 block 2 mechanism readout, R-bind (runs/probe/BENCH/P1/record.md): count-shuffle TV on fetches. On the stored
deck-search prompt rows (CHOOSE_CARD_TO_HAND) of an oracle run, permute the copy counts among the listed cards' tokens and
measure the policy's total variation over the legal options, averaged over --perms random permutations a row. The research
report measured 0.009 for start.pt (counts barely matter; permuting card ids moves it 0.967). Any pilot; CPU; evaluation only.

  PYTHONPATH=. .venv/Scripts/python notes/scripts/count_shuffle.py --pilots ar/data/start.pt runs/probe/BENCH/P1/T0.pt \
      --out runs/probe/BENCH/P1/count_shuffle_T0.json
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.gpu_matrix import load_policy  # noqa: E402
from rl.remote import trim_inputs      # noqa: E402

DT = {"tok_card": np.int16, "tok_kind": np.uint8, "tok_aux": np.uint8, "glob": np.uint8, "slots": np.uint8, "cand": np.int16}
PROMPT = 12


def listed(kind, aux):
    """Tokens carrying a listed card's copy count: PROMPT tokens (aux = copies), or zone tokens flagged listed (canon, bit 32)."""
    return ((kind == PROMPT) & (aux < 32)) | ((kind >= 6) & (kind <= 10) & ((aux & 32) > 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilots", nargs="+", required=True)
    ap.add_argument("--raw", default="runs/probe/BENCH/O_B.json.probes.json.gz")
    ap.add_argument("--perms", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    torch.set_num_threads(4)
    probes = [p for p in json.loads(gzip.open(ROOT / a.raw, "rt").read())["probes"]
              if p.get("prompt") and p.get("message") == "CHOOSE_CARD_TO_HAND"]
    rows = []
    for p in probes:
        o = {k: np.array(p["obs"][k], dtype=DT[k]) for k in DT}
        idx = np.nonzero(listed(o["tok_kind"].astype(int), o["tok_aux"].astype(int)))[0]
        if len(idx) >= 2:
            rows.append((p, o, idx))
    res = {"raw": a.raw, "rows": len(rows), "perms": a.perms, "pilots": {}}
    for path in a.pilots:
        m, _ = load_policy(path, "cpu")
        m.eval()
        rng = np.random.default_rng(a.seed)
        tv, distinct = [], []
        with torch.no_grad():
            for p, o, idx in rows:
                cnt = o["tok_aux"][idx] & 31
                batch = [o]
                for _ in range(a.perms):
                    q = {k: v.copy() for k, v in o.items()}
                    q["tok_aux"][idx] = (o["tok_aux"][idx] & ~np.uint8(31)) | rng.permutation(cnt)
                    batch.append(q)
                ins = [torch.from_numpy(np.stack([b[k] for b in batch])) for k in DT]
                ins.append(torch.full((len(batch),), int(p["obs"]["n_cand"]), dtype=torch.int32))
                lg = m(*trim_inputs(ins, m))[0][:, np.array(p["legal"])].double().softmax(-1)
                tv.append(float((0.5 * (lg[1:] - lg[0]).abs().sum(-1)).mean()))
                distinct.append(len(set(cnt.tolist())) > 1)
        tv, distinct = np.array(tv), np.array(distinct)
        res["pilots"][path] = {"tv_mean": float(tv.mean()), "tv_se": float(tv.std(ddof=1) / np.sqrt(len(tv))),
                               "tv_mean_distinct_counts": float(tv[distinct].mean()) if distinct.any() else None,
                               "rows_distinct_counts": int(distinct.sum())}
        print(f"{path}: count-shuffle TV {tv.mean():.4f} (SE {res['pilots'][path]['tv_se']:.4f}, {len(tv)} rows; "
              f"rows with distinct counts {int(distinct.sum())}: {res['pilots'][path]['tv_mean_distinct_counts']})", flush=True)
    Path(ROOT / a.out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
