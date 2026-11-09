"""Research's asks after W s49's G3 at 59 (#839, #840), evaluation only: a yardstick for G3. probe_meta_premise.py's design (the same pilot on both seats, greedy, round rule 20-45, 8 games a pair, seats alternating, deals keyed by list), read four ways: M (the share of decisive games, per pair, as G3), win share over all games, full wins (a win that isn't on time, per game), and event points.
--lists: every list against all 24 lists; then draws of 12 lists from that matrix, as G3's 12 decks against the 24.
--pops: a population's top 12 against the 24, the same reads.
--search: full-width search on both seats (C135's set), a small read; --first-deck and --last-deck play part of the top 12, keeping its indices and deals, so a stage saves what it played.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/g3_yardstick.py --lists --out runs/probe/C177-g3-yardstick/lists.json
  PYTHONPATH=. .venv/Scripts/python notes/scripts/g3_yardstick.py --pop runs/screens/C171-W-s49/population_it0059.pt --out runs/probe/C177-g3-yardstick/w49_59.json
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "notes/scripts")]
from c139_read import pts                                                 # noqa: E402
from probe_meta_premise import best_decks                                 # noqa: E402
from rl import limits                                                     # noqa: E402
from rl.decks import Pool, archived_decks                                 # noqa: E402
from rl.gpu_matrix import GpuMatrix, load_policy                          # noqa: E402
from rl.remote import RemotePool                                          # noqa: E402

C49 = "runs/pilot/C49-sd/model_it00199.pt"


def reads(rows):
    """Rows: one result a game, deck i's view. M per pair as G3, the others per game."""
    wins, dec = {}, {}
    for r in rows:
        k = (r["i"], r["j"])
        if r["winner"] in (1, 2):
            dec[k] = dec.get(k, 0) + 1
            wins[k] = wins.get(k, 0) + (r["winner"] == r["iSeat"])
    share = np.array([wins.get(k, 0) / d for k, d in dec.items()])
    n = len(rows)
    won = [r for r in rows if r["winner"] == r["iSeat"]]
    lost = [r for r in rows if r["winner"] in (1, 2) and r["winner"] != r["iSeat"]]
    return {"games": n, "M": round(float(share.mean()), 4), "se_pairs": round(float(share.std(ddof=1) / np.sqrt(len(share))), 4), "win_share_all_games": round(len(won) / n, 4),
            "loss_share_all_games": round(len(lost) / n, 4), "no_winner_share": round(1 - (len(won) + len(lost)) / n, 4),
            "full_wins": round(sum(r.get("ending") != "time" for r in won) / n, 4), "full_losses": round(sum(r.get("ending") != "time" for r in lost) / n, 4),
            "event_points": round(float(np.mean([pts(r)[0] for r in rows])), 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lists", action="store_true")
    ap.add_argument("--lists-draw", type=int, default=0, help="a seeded draw of this many lists as the decks, for the search yardstick")
    ap.add_argument("--pop", default="")
    ap.add_argument("--ids-from", default="", help="C182: the decks of --pop with the same ids as this population's top 12, in its order, for frozen G3")
    ap.add_argument("--pilot", default=C49)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--games", type=int, default=8)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--seed", type=int, default=93)
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--search", action="store_true")
    ap.add_argument("--first-deck", type=int, default=0)
    ap.add_argument("--last-deck", type=int, default=999)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    workers = limits.cap_workers(a.workers)
    limits.apply(device, workers)
    pool = Pool()
    lists = [{"name": n, "cards": pool.names(v)} for n, v in archived_decks(pool)]
    picked = sorted(np.random.default_rng(93).choice(len(lists), a.lists_draw, replace=False).tolist()) if a.lists_draw else None
    mine = [lists[k] for k in picked] if picked else lists if a.lists else best_decks(a.pop, a.top)
    if a.ids_from:
        have = {d["name"]: d for d in best_decks(a.pop, 999)}
        mine = [have[d["name"]] for d in best_decks(a.ids_from, a.top) if d["name"] in have]
    decks = mine + lists
    pairs = [(i, len(mine) + j) for i in range(a.first_deck, min(a.last_deck, len(mine))) for j in range(len(lists))]
    if os.environ.get("C172_GPU_MEM"):
        torch.cuda.set_per_process_memory_fraction(float(os.environ["C172_GPU_MEM"]))
    model, _ = load_policy(a.pilot, device)
    search = None
    if a.search:
        from c139_run import SEARCH
        search = {**SEARCH, "k": 64, "allTrainers": False}
    rp = RemotePool(workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, workers, device=device)
        gm.play(decks, a.games, a.seed, pairs=pairs, pair_keys=[j for _, j in pairs], round_turns=[20, 45], search=search)
        rows = [{"i": r["i"], "j": r["j"], "seed": r["seed"], "iSeat": r["iSeat"], "winner": r["winner"], "ending": r.get("ending"), "error": r.get("error")} for r in gm.results]
        last = gm.last
    finally:
        rp.close()
    ok = [r for r in rows if not r.get("error")]
    shapes = [[sum(1 for c in d["cards"] if pool.cards[pool.id[c] - 1]["superType"] == s) for s in (1, 2, 3)] for d in mine]
    out = {"pilot": a.pilot, "search": search, "seed": a.seed, "errors": len(rows) - len(ok), "last": last, "all": reads(ok), "shape_mean": [round(float(x), 2) for x in np.mean(shapes, 0)], **({"picked": picked} if picked else {})}
    if a.lists:
        out["mirrors_out"] = reads([r for r in ok if r["i"] != r["j"] - len(mine)])
        rng = np.random.default_rng(93)
        draw = []
        for _ in range(a.draws):
            pick = set(rng.choice(len(lists), 12, replace=False).tolist())
            draw.append(reads([r for r in ok if r["i"] in pick]))
        out["draws_of_12"] = {k: {"mean": round(float(np.mean([d[k] for d in draw])), 4), "sd": round(float(np.std([d[k] for d in draw])), 4), "p5": round(float(np.percentile([d[k] for d in draw], 5)), 4), "p95": round(float(np.percentile([d[k] for d in draw], 95)), 4), "min": round(float(min(d[k] for d in draw)), 4), "max": round(float(max(d[k] for d in draw)), 4)} for k in ("M", "win_share_all_games", "full_wins", "event_points")}
    (ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / a.out).write_text(json.dumps({**out, "results": ok}), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "search"}), flush=True)


if __name__ == "__main__":
    main()
