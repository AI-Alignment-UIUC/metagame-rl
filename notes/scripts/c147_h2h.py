"""C147 (runs/probe/C147-loop-pilot-draw/record.md) part (a): the loop's pilot (model slot 1) against arm 0 s1 (slot 0) on each California
list's own mirror, one seat each, --games deals a mirror alternating the seats (both seat orders equally), greedy, round rule [20, 45].
Reads the loop pilot's win share (draws half; #649: not event points) with a bootstrap SE over games, by its seat, and the endings.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c147_h2h.py --games 48 --out runs/probe/C147-loop-pilot-draw/h2h_s91.json
"""
import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import rl.remote as R                             # noqa: E402
from rl.gpu_matrix import GpuMatrix, load_policy  # noqa: E402
from c139_read import boot, pts, r3               # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot0", default="runs/probe/BENCH/arm-arm0-s1/pilot.pt", help="slot 0 (arm 0 s1)")
    ap.add_argument("--pilot1", default="runs/screens/C127-R1-K-paired-ledger-s16/checkpoint.pt", help="slot 1 (the loop's pilot)")
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--games", type=int, default=48, help="deals a mirror (even: both seat orders equally)")
    ap.add_argument("--limit", type=int, default=0, help="the first N lists only (the smoke)")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = subprocess.run(["node", "-e", "const {archivedDecks}=require('./env/decks.js');console.log(JSON.stringify(archivedDecks()))"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    decks = json.loads(out.stdout)[:a.limit or None]
    n = len(decks)
    alld = decks + [{"name": d["name"] + " (slot 1)", "cards": d["cards"]} for d in decks]
    m0, _ = load_policy(a.pilot0, a.device)
    m1, _ = load_policy(a.pilot1, a.device)
    rp = R.RemotePool(a.workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(m0, rp, a.workers, device=a.device)
        gm.play(alld, a.games, a.seed, pairs=[(i, n + i) for i in range(n)], slots=[0] * n + [1] * n, models={0: m0, 1: m1},
                round_turns=[20, 45])
        print("C147 h2h", a.seed, gm.last, flush=True)
        res = gm.results
    finally:
        rp.close()
    ok = [r for r in res if not r.get("error")]
    side1 = lambda r: {**r, "iSeat": 3 - r["iSeat"]}            # slot 1 is deck j = n + i, so it sits in the other seat
    ws = [pts(side1(r))[1] for r in ok]
    by_seat = {s: [pts(side1(r))[1] for r in ok if 3 - r["iSeat"] == s] for s in (1, 2)}
    summ = {"games": len(res), "errors": len(res) - len(ok), "slot1_win_share": r3(sum(ws) / len(ws)), "se": r3(boot(ws)),
            "by_slot1_seat": {s: {"games": len(v), "win_share": r3(sum(v) / len(v)) if v else None} for s, v in by_seat.items()},
            "slot1_wins": sum(1 for r in ok if r["winner"] == 3 - r["iSeat"]), "slot0_wins": sum(1 for r in ok if r["winner"] == r["iSeat"]),
            "draws": sum(1 for r in ok if r["winner"] not in (1, 2)), "endings": dict(Counter(r.get("ending") for r in ok)),
            "pilot0": a.pilot0, "pilot1": a.pilot1}
    wsm, se = summ["slot1_win_share"], summ["se"]
    summ["band"] = "R-general-weak" if wsm <= 0.45 and wsm <= 0.5 - 2 * se else "R-even" if abs(wsm - 0.5) <= 0.03 else "between"
    print(json.dumps(summ), flush=True)
    Path(ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(ROOT / a.out).write_text(json.dumps({**summ, "seed": a.seed, "deals": a.games, "deck_names": [d["name"] for d in alld],
                                              "results": res}), encoding="utf-8")


if __name__ == "__main__":
    main()
