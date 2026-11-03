"""C173 Amendment 1 item 3b (runs/probe/C173-search-table/record.md; the #648-#649 lesson): is the pilot with C139's search actually stronger than itself greedy? One seat each, the 24 California lists in their own mirrors, --games deals a mirror alternating the seats (so both seat orders equally), round rule [20, 45], on win share.
The greedy seat is slot 0, the search with k 1 and no Trainer candidates, so it plays the pilot's top choice; the search seat is slot 1, C139's settings. --aa puts k 1 on both seats, the mirror null. Search must reach 0.57 win share, or a null read at this pilot is void.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c173_h2h.py --pilot runs/pilot/C49-sd/model_it00199.pt --games 8 --out runs/probe/C173-search-table/h2h_C49.json
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import torch                                      # noqa: E402
import rl.remote as R                             # noqa: E402
from rl.gpu_matrix import GpuMatrix, load_policy  # noqa: E402
from c139_read import boot, pts, r3               # noqa: E402
from c139_run import SEARCH                       # noqa: E402

GREEDY = {"k": 1, "dets": 1, "maxSteps": 40, "crn": True, "trainerOnly": True, "allTrainers": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--games", type=int, default=8, help="deals a mirror (even: both seat orders equally)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--aa", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = subprocess.run(["node", "-e", "const {archivedDecks}=require('./env/decks.js');console.log(JSON.stringify(archivedDecks()))"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    decks = json.loads(out.stdout)[:a.limit or None]
    n = len(decks)
    alld = decks + [{"name": d["name"] + " (S)", "cards": d["cards"]} for d in decks]
    if os.environ.get("C172_GPU_MEM"):
        torch.cuda.set_per_process_memory_fraction(float(os.environ["C172_GPU_MEM"]))
    model, _ = load_policy(a.pilot, a.device)
    search = {**GREEDY, "bySlot": {1: {} if a.aa else {k: SEARCH[k] for k in ("k", "dets", "maxSteps", "crn", "trainerOnly", "allTrainers")}}}
    rp = R.RemotePool(a.workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, a.workers, device=a.device)
        gm.play(alld, a.games, a.seed, pairs=[(i, n + i) for i in range(n)], slots=[0] * n + [1] * n, models={0: model, 1: model}, round_turns=[20, 45], search=search)
        print("C173 h2h", a.pilot, gm.last, flush=True)
        res = gm.results
    finally:
        rp.close()
    ok = [r for r in res if not r.get("error")]
    side = lambda r: {**r, "iSeat": 3 - r["iSeat"]}   # the search seat is deck j = n + i
    ws = [pts(side(r))[1] for r in ok]
    by_seat = {s: [pts(side(r))[1] for r in ok if 3 - r["iSeat"] == s] for s in (1, 2)}
    summ = {"pilot": a.pilot, "aa": a.aa, "games": len(res), "errors": len(res) - len(ok), "win_share": r3(sum(ws) / len(ws)), "win_se": r3(boot(ws)), "gate_0.57": sum(ws) / len(ws) >= 0.57,
            "by_seat": {s: {"games": len(v), "win_share": r3(sum(v) / len(v)) if v else None} for s, v in by_seat.items()}, "endings": gm.last.get("endings"), "games_per_s": gm.last.get("games_per_s")}
    print(json.dumps(summ), flush=True)
    Path(ROOT / a.out).write_text(json.dumps({**summ, "search": search, "results": res}), encoding="utf-8")


if __name__ == "__main__":
    main()
