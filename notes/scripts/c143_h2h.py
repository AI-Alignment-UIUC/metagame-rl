"""C143 (runs/probe/C143-strength-ladder/record.md) strength check: R3 (arm 0 s1 with C139's search candidates at horizon 3, dets 4, maxSteps 120) against
R2 (C139's S: horizon 1, dets 2), one seat each, the 24 California lists in their own mirrors, --games deals a mirror alternating the
seats (so both seat orders equally), round rule [20, 45]. R2 is model slot 0 and R3 slot 1 (the same pilot twice), each with its own
search settings (env/remote_worker.js judgeSearch bySlot). Scores R3 in event points over 3 (c139_read.pts) with a bootstrap SE over
games, overall and by R3's seat; the record's gate is 0.53.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c143_h2h.py --games 8 --out runs/probe/C143-strength-ladder/h2h_s91.json
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import rl.remote as R                             # noqa: E402
from rl.gpu_matrix import GpuMatrix, load_policy  # noqa: E402
from c139_read import boot, pts, r3               # noqa: E402
from c139_run import SEARCH                       # noqa: E402

R3 = {"horizon": 3, "dets": 4, "maxSteps": 120}            # C132b raised maxSteps to 120 at horizon 3 so no line is cut


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default="runs/probe/BENCH/arm-arm0-s1/pilot.pt")
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--games", type=int, default=8, help="deals a mirror (even: both seat orders equally)")
    ap.add_argument("--limit", type=int, default=0, help="the first N lists only (the smoke)")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--aa", action="store_true", help="acceptance: both seats R2 (an A/A check of the per-slot settings)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = subprocess.run(["node", "-e", "const {archivedDecks}=require('./env/decks.js');console.log(JSON.stringify(archivedDecks()))"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    decks = json.loads(out.stdout)[:a.limit or None]
    n = len(decks)
    alld = decks + [{"name": d["name"] + " (R3)", "cards": d["cards"]} for d in decks]
    model, _ = load_policy(a.pilot, a.device)
    search = {**SEARCH, "bySlot": {1: {} if a.aa else R3}}
    rp = R.RemotePool(a.workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, a.workers, device=a.device)
        gm.play(alld, a.games, a.seed, pairs=[(i, n + i) for i in range(n)], slots=[0] * n + [1] * n, models={0: model, 1: model},
                round_turns=[20, 45], search=search)
        print("C143 h2h", a.seed, gm.last, flush=True)
        res = gm.results
    finally:
        rp.close()
    ok = [r for r in res if not r.get("error")]
    for r in ok:                                      # R3 is deck j = n + i, so its points are the list's points from the j side
        r["r3"] = pts({**r, "iSeat": 3 - r["iSeat"]})[0]
    by_seat = {s: [r["r3"] for r in ok if 3 - r["iSeat"] == s] for s in (1, 2)}
    xs = [r["r3"] for r in ok]
    ws = [pts({**r, "iSeat": 3 - r["iSeat"]})[1] for r in ok]       # #648: a mirror's event points sum to under 1, so also these
    r2 = sum(pts(r)[0] for r in ok)
    summ = {"games": len(res), "errors": len(res) - len(ok), "r3_points": r3(sum(xs) / len(xs)), "se": r3(boot(xs)),
            "r3_win_share": r3(sum(ws) / len(ws)), "win_se": r3(boot(ws)), "r3_points_share": r3(sum(xs) / (sum(xs) + r2)),
            "by_r3_seat": {s: {"games": len(v), "points": r3(sum(v) / len(v)) if v else None} for s, v in by_seat.items()},
            "gate_0_53": sum(xs) / len(xs) >= 0.53, "search": search, "last": gm.last}
    print(json.dumps({k: v for k, v in summ.items() if k != "last"}), flush=True)
    Path(ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(ROOT / a.out).write_text(json.dumps({**summ, "pilot": a.pilot, "seed": a.seed, "deals": a.games, "deck_names": [d["name"] for d in alld],
                                              "results": res}), encoding="utf-8")


if __name__ == "__main__":
    main()
