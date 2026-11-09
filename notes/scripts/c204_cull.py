"""C204 (runs/probe/C204-cull-end-causes/record.md): how do the decks that turnover culls lose? The loop keeps no per-game end causes,
so each cull's population just before it is replayed as the loop plays it: every deck against field_sample 4 of the same population
(C197's draw), --deals a pair with seats alternating, sampled play (greedy False, as rl/metagame.py's population games), the round
rule 20-45, under the run's own pilot (a fixed file, or the snapshot's net), with C199's per-seat counters (own turns, deck left at
the last own turn). Per group (culled at that turnover against kept): loss share by end cause (prizes, deck-out, no-pokemon, time,
cap = cut off with no ending, other), own turns a game, cards drawn per own turn ((47 - deck left) / own turns: 60 less the opening 7
and 6 Prizes; Trainer draws included, mulligans not), deck left at the end, and z's components (win, time-win, draw, loss).
Rule 9: on the replayed games, round_score against an independent round rule (win 1, time-win 2/3, draw 1/3, loss 0) and each time
ending's winner against the Prizes left (the winner fewer; a draw equal). Amendment 1: z with time-win 1 and time-loss 0, and which
decks either z would cull (bottom round(0.15 D) of those old enough, against the actual culls).
    PYTHONPATH=. .venv/Scripts/python notes/scripts/c204_cull.py --run C203-lists-b3-s48 --culls 49,54,59 --off 1 --pilot runs/probe/C197-judge-rerank/pilot_C171-W-s48_it44.pt --only-kind list --out b3
    PYTHONPATH=. .venv/Scripts/python notes/scripts/c204_cull.py --run C171-W-s48 --culls 19,24,29,34,39,44 --off 5 --pilot snap --out w48
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
sys.path.insert(0, str(ROOT))
from rl.decks import Pool                                # noqa: E402
from rl.train import round_score                         # noqa: E402

OUT = ROOT / "runs/probe/C204-cull-end-causes"
POOL = Pool()
FIELD, FIELD_SEED, ROUND = 4, 1970, [20, 45]
CAUSES = ("prizes", "deck-out", "no-pokemon", "time", "cap", "other")


def field_pairs(n):
    rng = np.random.default_rng(FIELD_SEED)
    return [(d, int(f)) for d in range(n) for f in rng.choice([e for e in range(n) if e != d], FIELD, replace=False)]


def rule(r, seat):
    w = r["winner"]
    if w == seat:
        return 2 / 3 if r.get("ending") == "time" else 1.0
    return 0.0 if w in (1, 2) else 1 / 3


def alt(r, seat):                                        # Amendment 1: time-win 1, time-loss 0, draws as they are
    w = r["winner"]
    return 1.0 if w == seat else 0.0 if w in (1, 2) else 1 / 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--culls", required=True)
    ap.add_argument("--off", type=int, default=1, help="the snapshot read is the cull's iteration minus this")
    ap.add_argument("--pilot", default="snap", help="a pilot file, or snap: the snapshot's own net")
    ap.add_argument("--only-kind", default="", help="compare only decks of this kind (list for C203's lists)")
    ap.add_argument("--deals", type=int, default=6)
    ap.add_argument("--protect", type=int, default=20)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from rl import limits
    from rl.gpu_matrix import GpuMatrix, load_policy
    from rl.remote import RemotePool
    import c190_split as C
    OUT.mkdir(exist_ok=True)
    run = ROOT / "runs/screens" / a.run
    L = C.log_rows(run)
    workers = limits.cap_workers(a.workers)
    limits.apply(a.device, workers)
    groups = {g: defaultdict(float) for g in ("culled", "kept")}
    counts = {g: Counter() for g in ("culled", "kept")}
    check = {"games": 0, "round_score_mismatch": 0, "time_wins": 0, "time_winner_not_ahead": 0, "time_draws": 0, "time_draw_unequal": 0,
             "prizes_left_missing": 0}
    amend, per_cull = [], []
    for t in [int(x) for x in a.culls.split(",")]:
        st = torch.load(run / f"population_it{t - a.off:04d}.pt", map_location="cpu", weights_only=False)
        pop = st["population"]
        outs = {x["out"] for x in (L.get(t) or {}).get("turnover") or []}
        if a.pilot == "snap":
            pf = OUT / f"pilot_{a.run}_it{t - a.off}.pt"
            if not pf.exists():
                torch.save({"config": st["config"], "model": st["net"]}, pf)
        else:
            pf = ROOT / a.pilot
        model, _ = load_policy(pf.relative_to(ROOT).as_posix(), a.device)
        decks = [{"name": f"{a.run} #{x['id']}", "cards": list(x["deck"]) if isinstance(x["deck"], list) else POOL.names(x["deck"])} for x in pop]
        n = len(decks)
        pairs = field_pairs(n)
        keys = [d * FIELD + k % FIELD for k, (d, _) in enumerate(pairs)]
        rp = RemotePool(workers)
        rp.pace = 0.25
        try:
            gm = GpuMatrix.attach(model, rp, workers, device=a.device, greedy=False)
            gm.play(decks, a.deals, 2040 + t, pairs=pairs, pair_keys=keys, round_turns=ROUND, trainer_play=True)
            res = list(gm.results)
            last = gm.last
        finally:
            rp.close()
        z, za, ng = np.zeros(n), np.zeros(n), np.zeros(n)
        for r in res:
            check["games"] += 1
            for d, seat in ((r["i"], r["iSeat"]), (r["j"], 3 - r["iSeat"])):
                s = round_score(r, seat, ROUND)
                check["round_score_mismatch"] += abs(s - rule(r, seat)) > 1e-12
                z[d] += s; za[d] += alt(r, seat); ng[d] += 1
                kind = pop[d].get("kind")
                if a.only_kind and kind != a.only_kind:
                    continue
                g = "culled" if pop[d]["id"] in outs else "kept"
                w, end = r["winner"], r.get("ending")
                cause = end if end in CAUSES else ("cap" if w not in (0, 1, 2) or end is None else "other")
                res_kind = "win" if w == seat and end != "time" else "time-win" if w == seat else "loss" if w in (1, 2) else "draw"
                counts[g][res_kind] += 1
                if res_kind == "loss":
                    counts[g]["loss:" + cause] += 1
                counts[g]["ended:" + cause] += 1
                ts = (r.get("turnSeat") or {}).get(str(seat)) or {}
                if ts.get("turns"):
                    groups[g]["turns"] += ts["turns"]; groups[g]["turn_games"] += 1
                    if ts.get("deckEnd") is not None:
                        groups[g]["deck_end"] += ts["deckEnd"]; groups[g]["drawn"] += 47 - ts["deckEnd"]; groups[g]["deck_games"] += 1
                groups[g]["z"] += round_score(r, seat, ROUND); groups[g]["z_alt"] += alt(r, seat); groups[g]["games"] += 1
            w, pl = r["winner"], r.get("prizesLeft")
            if r.get("ending") == "time":
                if not pl:
                    check["prizes_left_missing"] += 1
                else:
                    p1, p2 = (pl[0], pl[1]) if isinstance(pl, list) else (pl.get("1"), pl.get("2"))
                    if w in (1, 2):
                        check["time_wins"] += 1
                        mine, theirs = (p1, p2) if w == 1 else (p2, p1)
                        check["time_winner_not_ahead"] += not (mine < theirs)
                    elif w == 0:
                        check["time_draws"] += 1
                        check["time_draw_unequal"] += p1 != p2
        zm, zam = z / np.maximum(ng, 1), za / np.maximum(ng, 1)
        born = np.array([x.get("born", 0) for x in pop])
        old = [d for d in range(n) if t + 1 - born[d] >= a.protect]
        k = int(round(0.15 * n))
        cut_z = {pop[d]["id"] for d in sorted(old, key=lambda d: zm[d])[:k]}
        cut_a = {pop[d]["id"] for d in sorted(old, key=lambda d: zam[d])[:k]}
        amend.append({"cull": t, "actual": sorted(outs), "replay_z_bottom": sorted(cut_z), "alt_z_bottom": sorted(cut_a),
                      "actual_in_replay_z_bottom": len(outs & cut_z), "actual_surviving_alt": len(outs - cut_a), "k": k, "eligible": len(old)})
        per_cull.append({"cull": t, "snapshot": t - a.off, "games": last["games"], "errors": last["errors"], "seconds": last["seconds"],
                         "culled_in_snapshot": sum(x["id"] in outs for x in pop)})
        print(f"cull {t}: {last['games']} games, {last['errors']} errors, {last['seconds']} s", flush=True)
    out = {"run": a.run, "culls": a.culls, "pilot": a.pilot, "only_kind": a.only_kind, "deals": a.deals, "per_cull": per_cull, "rule9": check,
           "amendment1": amend, "groups": {}}
    for g in groups:
        c, x = counts[g], groups[g]
        games = max(x["games"], 1)
        losses = max(c["loss"], 1)
        out["groups"][g] = {"deck_games": int(x["games"]), "z": round(x["z"] / games, 4), "z_alt": round(x["z_alt"] / games, 4),
                            **{f"share_{q}": round(c[q] / games, 4) for q in ("win", "time-win", "draw", "loss")},
                            "loss_by_cause": {q: round(c["loss:" + q] / losses, 4) for q in CAUSES},
                            "ended_by_cause": {q: round(c["ended:" + q] / games, 4) for q in CAUSES},
                            "own_turns": round(x["turns"] / max(x["turn_games"], 1), 2),
                            "deck_left_end": round(x["deck_end"] / max(x["deck_games"], 1), 2),
                            "drawn_per_own_turn": round(x["drawn"] / max(x["turns"], 1), 3) if x["deck_games"] else None}
    (OUT / f"{a.out}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "amendment1"}, indent=1))
    print(json.dumps(out["amendment1"], indent=1))


if __name__ == "__main__":
    main()
