"""C03 (plan item 11, log #162): checks of search served by the GPU learner (rl/gpu_matrix.py play(search=...), env/
remote_worker.js judgeSearch, env/agents.js PolicySearchAgent). Evaluation only.

  1. identity: k = 1 plays exactly the greedy games, deal by deal (winner, ending, turns, steps)
  2. cost: J2 (k 4, dets 4, maxSteps 40) on both seats with and without CRN on the same deals: games a second and ms a
     searched decision, against the CPU path's 864-874 ms a search (log #159)
  3. gross check (arm (a)): J2 on the resetcap-499 walls against all 24 lists, flagged if more than 0.15 from the CPU
     path's 0.607 (#156; other deals, so only a gross check)

  .venv/Scripts/python -I notes/scripts/c03_check.py --out runs/probe/C03 [--lock runs/pilot/C45/look.lock]
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes/scripts"))
from rl import limits  # noqa: E402
from rl.decks import Pool  # noqa: E402
from rl.gpu_matrix import GpuMatrix  # noqa: E402
from rl.remote import RemotePool  # noqa: E402
from rl.train import token_net  # noqa: E402
from probe_matchups import group  # noqa: E402

PILOT = "runs/screens/scr-resetcap/checkpoint.pt"


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--games", type=int, default=8, help="games a wall-list pair in step 3")
    ap.add_argument("--conc", type=int, default=16)
    ap.add_argument("--lock", default="")
    ap.add_argument("--steps", default="1,2,3")
    a = ap.parse_args(argv)
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    lock = ROOT / a.lock if a.lock else None
    while lock is not None:                              # share the GPU with the C45 looks one at a time
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL)); break
        except FileExistsError:
            time.sleep(30)
    try:
        run(a, out)
    finally:
        if lock is not None:
            lock.unlink(missing_ok=True)


def run(a, out):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    workers = limits.cap_workers(a.workers)
    limits.apply(device, workers)
    pool = Pool()
    A, B = group("runs/probe/walls_resetcap499.json", pool), group("archived", pool)
    decks = A + B
    pairs = [(i, len(A) + j) for i in range(len(A)) for j in range(len(B))]
    rp = RemotePool(workers)
    rp.pace = 0.25
    info = rp.ask_all([{"cmd": "info"}] * workers)[0]
    st = torch.load(ROOT / PILOT, map_location=device, weights_only=False)
    net = token_net(st["config"], info).to(device)
    net.load_state_dict(st["model"] if "model" in st else st["net"])
    net.eval()
    gm = GpuMatrix.attach(net, rp, workers, device=device)
    gm.greedy = True
    res = {}
    steps = [int(x) for x in a.steps.split(",")]

    def play(games, seed, search):
        t0 = time.time()
        gm.play(decks, games, seed, pairs=pairs, search=search)
        return {(r["seed"], r["i"], r["j"]): r for r in gm.results}, dict(gm.last), time.time() - t0

    def j2(crn):
        return {"k": 4, "dets": 4, "maxSteps": 40, "concurrency": a.conc, "crn": crn}

    try:
        if 1 in steps:
            g, lg, _ = play(2, 5, None)
            s, ls, _ = play(2, 5, {"k": 1, "dets": 1, "maxSteps": 40, "concurrency": a.conc})
            diff = [k for k in g if any(g[k][f] != s[k].get(f) for f in ("winner", "ending", "turns", "steps"))]
            res["identity"] = {"games": len(g), "differ": len(diff), "search": ls.get("search"),
                               "first_diffs": [[str(k), {f: (g[k][f], s[k].get(f)) for f in ("winner", "turns", "steps")}]
                                               for k in diff[:5]]}
            print("identity:", json.dumps(res["identity"]), flush=True)
        if 2 in steps:
            for crn in (False, True):
                _, l2, secs = play(1, 7, j2(crn))
                srch = l2.get("search") or {}
                res[f"cost_crn{int(crn)}"] = {"games": l2["games"], "seconds": round(secs, 1),
                                              "games_per_s": round(l2["games"] / secs, 3), "search": srch,
                                              "ms_per_search_wall": round(1000 * secs / max(1, srch.get("searches", 0)), 1),
                                              "endings": l2.get("endings")}
                print(f"cost crn={crn}:", json.dumps(res[f"cost_crn{int(crn)}"]), flush=True)
        if 3 in steps:
            r3, l3, secs = play(a.games, 11, j2(False))
            P = np.zeros((len(A), len(B))); G = np.zeros_like(P)
            for r in r3.values():
                i, j = r["i"], r["j"] - len(A)
                P[i, j] += 1.0 if r["winner"] == r["iSeat"] else 0.0 if r["winner"] in (1, 2) else 0.5
                G[i, j] += 1
            m = float((P / np.maximum(G, 1)).mean())
            res["gross"] = {"games": len(r3), "mean": round(m, 4), "cpu": 0.607, "flag": abs(m - 0.607) > 0.15,
                            "seconds": round(secs, 1), "search": l3.get("search"), "endings": l3.get("endings")}
            print("gross:", json.dumps(res["gross"]), flush=True)
    finally:
        rp.close()
        (out / "check.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
