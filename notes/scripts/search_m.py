"""C96 (runs/probe/C96-search-M/record.md): ar/'s M with and without test-time search on both seats, the same seeds and
deals in both conditions. Evaluation only; orchestration around existing code: fixed.evaluate's M part (eval_decks.json
pairs, deals keyed by the list, the round rule, the lists' share of the decisive games a pair) with GpuMatrix.play's
search option (probe_matchups.search_spec). The pilot plays both seats.

  PYTHONPATH=. .venv/Scripts/python notes/scripts/search_m.py --lists 24 --games 32 --seeds 1 2 \
      --out runs/probe/C96-search-M/m.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ar"))
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
sys.path.insert(0, str(ROOT))
import fixed                                            # noqa: E402
from probe_matchups import search_spec                  # noqa: E402
from rl import limits                                   # noqa: E402
from rl.gpu_matrix import GpuMatrix, load_policy        # noqa: E402
from rl.remote import RemotePool                        # noqa: E402


def m_of(gm, pairs) -> dict:
    wins, dec = {}, {}
    for r in gm.results:
        k = (r["i"], r["j"])
        if r["winner"] in (1, 2):
            dec[k] = dec.get(k, 0) + 1
            wins[k] = wins.get(k, 0) + (r["winner"] == r["iSeat"])
    share = [wins.get(k, 0) / dec[k] for k in pairs if dec.get(k)]
    return {"M": round(float(np.mean(share)), 4),
            "M_se": round(float(np.std(share, ddof=1) / np.sqrt(len(share))), 4) if len(share) > 1 else None,
            "pairs": len(share), "share": [round(x, 4) for x in share], "draws": int(sum(g for g in [
                sum(1 for r in gm.results if (r["i"], r["j"]) == k) - dec.get(k, 0) for k in pairs])),
            "errors": gm.last["errors"], "games": gm.last["games"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default="ar/data/start.pt")
    ap.add_argument("--lists", type=int, default=24, help="the first N lists (each against its 4 copies)")
    ap.add_argument("--games", type=int, default=fixed.EVAL_GAMES)
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2])
    ap.add_argument("--search", default="4:4:crn")
    ap.add_argument("--search-conc", type=int, default=16)
    ap.add_argument("--conditions", default="greedy,search")
    ap.add_argument("--workers", type=int, default=fixed.EVAL_WORKERS)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ev = json.loads((fixed.DATA / "eval_decks.json").read_text(encoding="utf-8"))
    lists = sorted({p[0] for p in ev["pairs"]})[:a.lists]  # deck indices of the lists (each list is followed by its copies)
    pairs = [tuple(p) for p in ev["pairs"] if p[0] in lists]
    device = "cuda"
    workers = limits.cap_workers(a.workers)
    limits.apply(device, workers)
    model, _ = load_policy(a.pilot, device)
    rp = RemotePool(workers)
    rp.pace = 0.25
    out = {"pilot": a.pilot, "lists": a.lists, "pairs": len(pairs), "games": a.games, "search": a.search, "runs": []}
    try:
        gm = GpuMatrix.attach(model, rp, workers, device=device)
        for seed in a.seeds:
            for cond in a.conditions.split(","):
                t0 = time.time()
                gm.play(ev["decks"], a.games, seed, pairs=pairs, pair_keys=[i for i, _ in pairs],
                        round_turns=fixed.GAME["roundTurns"],
                        search=search_spec(a.search, a.search_conc) if cond == "search" else None)
                r = {"seed": seed, "condition": cond, **m_of(gm, pairs), "seconds": round(time.time() - t0, 1)}
                out["runs"].append(r)
                print(json.dumps({k: v for k, v in r.items() if k != "share"}), flush=True)
                (ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
                (ROOT / a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    finally:
        rp.close()


if __name__ == "__main__":
    main()
