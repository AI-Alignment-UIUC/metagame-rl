"""X1 and X4 (runs/probe/X1X4-prompts-pace/record.md; designs in log #234): why does the frozen pilot price the lists'
search, disrupt and tempo Trainers below a basic Energy? Evaluation only.

trainer_value.py's readout (each list against a copy with one Trainer group turned into its commonest basic Energy, one
pilot on both seats, both seats, the same deals in every arm), played by env/tools/probe_worker.js with its switches:
  G  the pilot answers everything (the control: with no switch the worker plays as env/remote_worker.js)
  U  X1: the seat's prompt answers inside its own Trainers drawn at random, other than cancel (--prompts random)
  A  X4: must attack if able: a pass with an attack on offer becomes the pilot's top-rated attack (--pace attack)
Readout: arm minus G by group, paired by list; endings, steps and turns a game; the workers' switch counts; the bands
of the record. The JSON is rewritten after each arm; a STOP file in the output folder stops before the next arm.

Run: PYTHONPATH=. RL_GPU_SHARE=0.5 RL_CPU_THREADS=8 .venv/Scripts/python.exe notes/scripts/probe_prompts_pace.py \
        --pilot runs/pilot/C49-sd/model_it00199.pt --games 32 --workers 6 --round-turns 20-45 --seed 91 \
        --out runs/probe/X1X4-prompts-pace/xprobe.json
"""
import argparse
import collections
import json
import subprocess
import sys
import threading
from pathlib import Path

import numpy as np
import torch

from rl import limits
from rl.decks import Pool, archived_decks
from rl.gpu_matrix import GpuMatrix, load_policy
from rl.remote import RemotePool
from rl.train import round_turns
from trainer_value import GROUPS, variants          # notes/scripts, beside this file

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "env" / "tools" / "probe_worker.js"
ARMS = {"G": [], "U": ["--prompts", "random"], "A": ["--pace", "attack"]}
THREE = ("search", "disrupt", "tempo")


class SwitchPool(RemotePool):
    """RemotePool over env/tools/probe_worker.js with the switches on its command line; keeps each reply's counts."""

    def __init__(self, n: int, switches: list):
        super().__init__(0)
        self.procs = [subprocess.Popen(["node", str(WORKER), *switches], cwd=ROOT, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, bufsize=0) for _ in range(n)]
        for i, p in enumerate(self.procs):
            threading.Thread(target=self._reader, args=(i, p), daemon=True).start()
        self.stats = []

    def collect(self, msgs, models, device):
        replies = super().collect(msgs, models, device)
        self.stats += [r["switchStats"] for r in replies if "switchStats" in r]
        return replies


def add_stats(stats: list) -> dict:
    tot = {}
    for s in stats:
        for k, v in s.items():
            if k != "byTrainer":
                tot[k] = tot.get(k, 0) + v
                continue
            for name, c in v.items():
                t = tot.setdefault("byTrainer", {}).setdefault(name, {})
                for q, x in c.items():
                    t[q] = t.get(q, 0) + x
    return tot


def play_arm(model, arm: str, decks: list, pairs: list, args, rounds, device: str) -> dict:
    rp = SwitchPool(args.workers, ARMS[arm])
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, args.workers, device=device)
        W, G, _ = gm.play(decks, args.games, args.seed, pairs=[(p["base"], p["variant"]) for p in pairs],
                          pair_keys=[p["base"] for p in pairs], round_turns=rounds)
    finally:
        rp.close()
    group_of = {p["variant"]: p["group"] for p in pairs}
    endings = collections.defaultdict(collections.Counter)
    for r in gm.results:
        for g in (group_of[r["j"]], "all"):
            endings[g][r.get("ending") or ("error" if r.get("error") else "none")] += 1
    n = len(gm.results)
    sw = add_stats(rp.stats)
    per_pair = [float(W[p["base"], p["variant"]] / max(G[p["base"], p["variant"]], 1)) for p in pairs]
    by_group = {}
    for g in args.groups:
        x = np.array([v for v, p in zip(per_pair, pairs) if p["group"] == g])
        if len(x):
            by_group[g] = {"pairs": len(x), "score": round(float(x.mean()), 4),
                           "se": round(float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else 0.5, 4)}
    return {"switches": ARMS[arm], "last": gm.last, "by_group": by_group, "per_pair": [round(v, 4) for v in per_pair],
            "endings": {g: dict(c) for g, c in endings.items()},
            "time_share": round(endings["all"]["time"] / max(n, 1), 4),
            "steps_per_game": round(float(np.mean([r["steps"] for r in gm.results])), 1),
            "turns_per_game": round(float(np.mean([r["turns"] for r in gm.results])), 2),
            "errors": int(sum(bool(r.get("error")) for r in gm.results)),
            "switch": sw, "per_game": {k: round(sw.get(k, 0) / max(n, 1), 3) for k in
                                       ("asked", "trainerPrompts", "randomized", "changed", "attackOffered", "attacked",
                                        "passes", "passWithAttack", "passToAttack")}}


def paired(arm: dict, ctl: dict, pairs: list, groups) -> dict:
    """Arm minus control, paired by list: each list's mean difference over its pairs in `groups`; mean and SE over
    lists (a list's pairs share deals, so lists, not pairs, are the independent units)."""
    by_list = collections.defaultdict(list)
    for a, c, p in zip(arm["per_pair"], ctl["per_pair"], pairs):
        if p["group"] in groups:
            by_list[p["base"]].append(a - c)
    d = np.array([np.mean(v) for v in by_list.values()])
    if not len(d):
        return {"lists": 0}
    se = float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else float("nan")
    return {"lists": len(d), "diff": round(float(d.mean()), 4), "se": round(se, 4)}


def readout(arms: dict, pairs: list, groups: list) -> dict:
    out = {}
    if "G" not in arms:
        return out
    G = arms["G"]
    for a in ("U", "A"):
        if a not in arms:
            continue
        rd = {g: paired(arms[a], G, pairs, (g,)) for g in groups}
        rd["three"] = paired(arms[a], G, pairs, THREE)
        rd["time_share_change"] = round(arms[a]["time_share"] - G["time_share"], 4)
        # the endings' shares (all games) and steps a game, arm minus G (the spec's X4 readout)
        share = lambda arm, e: arm["endings"].get("all", {}).get(e, 0) / max(sum(arm["endings"].get("all", {}).values()), 1)
        rd["ending_share_change"] = {e: round(share(arms[a], e) - share(G, e), 4)
                                     for e in ("time", "prizes", "deck-out", "no-pokemon")}
        rd["steps_change"] = round(arms[a]["steps_per_game"] - G["steps_per_game"], 1)
        out[f"{a}-G"] = rd
    if "U-G" in out:                              # X1 bands (record.md)
        r, sw = out["U-G"], arms["U"]["switch"]
        ch = sw.get("changed", 0) / max(sw.get("randomized", 0), 1)
        ctl, s = r.get("draw", {}).get("diff"), r.get("search", {}).get("diff")
        # the control's two halves: the switch never answers for a draw card (a count, must be 0), and the draw
        # pairs' |U-G| <= 0.02; control_within_2se beside it (at 32 games a pair the 0.02 bar is about 1 SE; record.md)
        r["draw_card_prompts"] = sum(c.get("prompts", 0) for n, c in sw.get("byTrainer", {}).items()
                                     if any(n.startswith(d + " ") for d in GROUPS["draw"]))
        band = ("inert (random answers differ from the pilot's in under 10% of prompts)" if ch < 0.10
                else "no reading (the switch answered a draw card's prompt)" if r["draw_card_prompts"]
                else "no reading (draw control leaks: |U-G| > 0.02)" if ctl is None or abs(ctl) > 0.02
                else "no reading (no search pairs)" if s is None
                else "competent" if s <= -0.05 else "misdirected" if s >= 0.03 else "untrained" if abs(s) <= 0.02
                else "between (disrupt and tempo decide)")
        r["changed_share"] = round(ch, 4)
        r["band"] = band
        dr = r.get("draw", {})
        r["control_within_2se"] = bool(dr.get("lists") and abs(dr["diff"]) <= 2 * dr["se"])
    if "A-G" in out:                              # X4 bands (record.md)
        r, pg = out["A-G"], arms["A"]["per_game"]
        m, dt = r["three"].get("diff"), r["time_share_change"]
        band = ("inert (under 0.5 passes a game turned into attacks, or time endings fell by under 5 points)"
                if pg["passToAttack"] < 0.5 or dt > -0.05
                else "no reading (no search, disrupt or tempo pairs)" if m is None
                else "pace-bound" if m >= 0.04 else "not pace-bound" if abs(m) <= 0.02 else "between")
        r["band"] = band
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True, help="a learned pilot checkpoint (.pt), on both seats, greedy")
    ap.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(ARMS))
    ap.add_argument("--groups", nargs="+", default=["draw", *THREE], choices=list(GROUPS))
    ap.add_argument("--lists", type=int, default=0, help="only the first N archived lists (smoke tests); 0 all 24")
    ap.add_argument("--games", type=int, default=32, help="games per pair (both seats)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--round-turns", default="20-45", help='the 2000 round rule, "T" or "A-B"; "0" off')
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    rounds = round_turns(args.round_turns)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    limits.apply(device, args.workers)
    pool = Pool()
    decks = [{"name": n, "cards": pool.names(v)} for n, v in archived_decks(pool)]
    if args.lists:
        decks = decks[:args.lists]
    alld, pairs = variants(pool, decks, args.groups)
    model, enc = load_policy(args.pilot, device)
    assert enc == "tokens", "the probe worker's switches need the token encoding"
    out_path = ROOT / args.out
    res = {"pilot": args.pilot, "games": args.games, "seed": args.seed, "round_turns": args.round_turns,
           "lists": len(decks), "device": device, "workers": args.workers, "pairs": pairs, "arms": {}}
    for arm in args.arms:
        if (out_path.parent / "STOP").exists():
            print("STOP file: stopping before arm", arm, flush=True)
            break
        r = play_arm(model, arm, alld, pairs, args, rounds, device)
        res["arms"][arm] = r
        res["readout"] = readout(res["arms"], pairs, args.groups)
        out_path.write_text(json.dumps(res, indent=1))
        print(arm, json.dumps({k: r[k] for k in ("last", "by_group", "time_share", "steps_per_game", "turns_per_game",
                                                  "per_game")}), flush=True)
        if r["errors"] > 0.01 * r["last"]["games"]:
            print(f"KILL: {r['errors']} errors in {r['last']['games']} games (over 1%) in arm {arm}", flush=True)
            sys.exit(2)
    print("readout", json.dumps(res.get("readout", {})), flush=True)


if __name__ == "__main__":
    main()
