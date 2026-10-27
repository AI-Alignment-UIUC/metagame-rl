"""X1b (runs/probe/X1b-prompt-oracle/record.md): if the prompts inside the seats' own Trainers were answered well, would
the lists' search, disrupt and tempo Trainers be worth more than a basic Energy? Evaluation only.

C68 (log #241) found the pilot answers those prompts no better than random. This is the ceiling: trainer_value's readout
(each list against a copy with one Trainer group turned into its commonest basic Energy, one pilot on both seats, both
seats, the same deals in every arm), played by env/tools/probe_oracle_worker.js:
  G  the pilot answers everything (no switch: the worker plays as env/remote_worker.js)
  S  the prompt oracle (--prompts search): at a prompt inside the seat's own Trainer, the option with the best mean
     score over re-dealt copies, each played on by the pilot to the end of the turn and scored by its value
Readout: S - G by group, paired by list; S's own scores; the oracle's counts; the bands of the record. The JSON is
rewritten after each arm; a STOP file in the output folder stops before the next arm.

Run: see runs/probe/X1b-prompt-oracle/chain.sh.
"""
import argparse
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import torch

from rl import limits
from rl.decks import Pool, archived_decks
from rl.gpu_matrix import GpuMatrix, load_policy
from rl.remote import RemotePool
from rl.train import round_turns
from trainer_value import GROUPS, variants                    # notes/scripts, beside this file
from probe_prompts_pace import THREE, add_stats, paired       # C68's helpers (read only)

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "env" / "tools" / "probe_oracle_worker.js"
COUNTS = ("asked", "trainerPrompts", "searched", "unsearchable", "changed", "flat", "clear", "gainSum", "lines", "lineAsked",
          "lineErrors", "capped", "replayExact", "replayDiff", "acts", "oracleRounds", "searchCalls", "oracleMs", "cpuMs", "wallMs")
C68_LAUNCH = ROOT / "runs" / "probe" / "X1X4-prompts-pace" / "launch.log"


def engine_stamp() -> dict:
    """The compiled engine the workers load (ryuu-play's dist/cjs, as ar/fixed.py hashes it): files and newest mtime. Another
    session edits the engine sources; a rebuild between the arms would put G and S on different engines, and one before
    launch ends G's A/A with C68 (same_as_c68: no build file newer than C68's start)."""
    files = [f for d in ("common", "sets") for f in (ROOT / "ryuu-play" / "packages" / d / "dist" / "cjs").rglob("*") if f.is_file()]
    newest = max((f.stat().st_mtime for f in files), default=0.0)
    out = {"files": len(files), "newest": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(newest))}
    try:                                                # "X1X4 start 2026-10-24 17:01:50"
        start = C68_LAUNCH.read_text().split("\n")[0].split("start ")[1].strip()
        out["same_as_c68"] = out["newest"] < start
    except (OSError, IndexError):
        out["same_as_c68"] = None
    return out


class OraclePool(RemotePool):
    """RemotePool over env/tools/probe_oracle_worker.js with the switches on its command line; keeps each reply's counts."""

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


def level(arm: dict, pairs: list, groups) -> dict:
    """An arm's own score over `groups`, by list: each list's mean over its pairs in `groups`, then mean and SE over lists."""
    by_list = {}
    for a, p in zip(arm["per_pair"], pairs):
        if p["group"] in groups:
            by_list.setdefault(p["base"], []).append(a)
    d = np.array([np.mean(v) for v in by_list.values()])
    if not len(d):
        return {"lists": 0}
    se = float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else float("nan")
    return {"lists": len(d), "score": round(float(d.mean()), 4), "se": round(se, 4)}


def play_arm(model, switches: list, decks: list, pairs: list, args, rounds, device: str) -> dict:
    rp = OraclePool(args.workers, switches)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, args.workers, device=device)
        W, G, _ = gm.play(decks, args.games, args.seed, pairs=[(p["base"], p["variant"]) for p in pairs],
                          pair_keys=[p["base"] for p in pairs], round_turns=rounds)
    finally:
        rp.close()
    n = len(gm.results)
    sw = add_stats(rp.stats)
    per_pair = [float(W[p["base"], p["variant"]] / max(G[p["base"], p["variant"]], 1)) for p in pairs]
    by_group = {}
    for g in args.groups:
        x = np.array([v for v, p in zip(per_pair, pairs) if p["group"] == g])
        if len(x):
            by_group[g] = {"pairs": len(x), "score": round(float(x.mean()), 4),
                           "se": round(float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else 0.5, 4)}
    endings = {}
    for r in gm.results:
        e = r.get("ending") or ("error" if r.get("error") else "none")
        endings[e] = endings.get(e, 0) + 1
    return {"switches": switches, "last": gm.last, "by_group": by_group, "per_pair": [round(v, 4) for v in per_pair],
            "endings": endings, "steps_per_game": round(float(np.mean([r["steps"] for r in gm.results])), 1),
            "turns_per_game": round(float(np.mean([r["turns"] for r in gm.results])), 2),
            "errors": int(sum(bool(r.get("error")) for r in gm.results)), "switch": sw,
            "per_game": {k: round(sw.get(k, 0) / max(n, 1), 3) for k in COUNTS}}


def readout(arms: dict, pairs: list, groups: list) -> dict:
    if "G" not in arms or "S" not in arms:
        return {}
    G, S = arms["G"], arms["S"]
    rd = {g: paired(S, G, pairs, (g,)) for g in groups}
    rd["three"] = paired(S, G, pairs, THREE)
    rd["S_three"], rd["G_three"] = level(S, pairs, THREE), level(G, pairs, THREE)
    sw = S["switch"]
    ch = sw.get("changed", 0) / max(sw.get("searched", 0), 1)
    # the control: the oracle never answers for a draw card (a count, must be 0), and the draw pairs' S - G near 0. Not
    # a pure null: the other Trainers of both decks are searched too, and the list with its draw cards reaches more.
    rd["draw_card_prompts"] = sum(c.get("prompts", 0) for n, c in sw.get("byTrainer", {}).items()
                                  if any(n.startswith(d + " ") for d in GROUPS["draw"]))
    dr = rd.get("draw", {})
    rd["control_ok"] = bool(dr.get("lists") and (abs(dr["diff"]) <= 0.02 or abs(dr["diff"]) <= 2 * dr["se"]))
    m, s3 = rd["three"].get("diff"), rd["S_three"].get("score")
    rd["changed_share"] = round(ch, 4)
    rd["unsearchable_share"] = round(sw.get("unsearchable", 0) / max(sw.get("trainerPrompts", 0), 1), 4)
    n = max(sw.get("searched", 0), 1)    # how sure the oracle is: all candidates tied, changes clear of 2 SE, mean gain
    rd["flat_share"], rd["clear_share_of_changed"] = round(sw.get("flat", 0) / n, 4), round(sw.get("clear", 0) / max(sw.get("changed", 0), 1), 4)
    rd["mean_gain"] = round(sw.get("gainSum", 0) / n, 4)
    copies = sum(sw.get("tier_" + t, 0) for t in ("full", "oppHandSeen", "ownDeckSeen", "bothSeen", "none"))
    rd["tier_shares"] = {t: round(sw.get("tier_" + t, 0) / max(copies, 1), 4)
                         for t in ("full", "oppHandSeen", "ownDeckSeen", "bothSeen", "none")}
    rd["band"] = ("inert (the oracle's pick differs from the pilot's in under 5% of searched prompts)" if ch < 0.05
                  else "no reading (the oracle answered a draw card's prompt)" if rd["draw_card_prompts"]
                  else "no reading (no search, disrupt or tempo pairs)" if m is None
                  else "prompt play is the cause" if m >= 0.05 and s3 >= 0.50
                  else "partial" if m >= 0.02
                  else "no lift" if m > -0.02
                  else "negative (S below G: check the oracle before reading)")
    return rd


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True, help="a learned pilot checkpoint (.pt), on both seats, greedy")
    ap.add_argument("--arms", nargs="+", default=["G", "S"], choices=["G", "S"])
    ap.add_argument("--groups", nargs="+", default=["draw", *THREE], choices=list(GROUPS))
    ap.add_argument("--lists", type=int, default=0, help="only the first N archived lists (smoke tests); 0 all 24")
    ap.add_argument("--games", type=int, default=16, help="games per pair (both seats)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--round-turns", default="20-45", help='the 2000 round rule, "T" or "A-B"; "0" off')
    ap.add_argument("--cap", type=int, default=8, help="options searched a prompt at most (the pilot's most likely)")
    ap.add_argument("--dets", type=int, default=4, help="re-dealt copies a prompt, the same for every option")
    ap.add_argument("--max-steps", type=int, default=60, help="a line's steps at most, then scored by the value")
    ap.add_argument("--oracle-check", type=int, default=0, help="1: check each searched prompt's replay (smoke)")
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
    assert enc == "tokens", "the oracle worker needs the token encoding"
    arms = {"G": [], "S": ["--prompts", "search", "--cap", str(args.cap), "--dets", str(args.dets),
                           "--max-steps", str(args.max_steps), "--oracle-check", str(args.oracle_check)]}
    out_path = ROOT / args.out
    res = {"pilot": args.pilot, "games": args.games, "seed": args.seed, "round_turns": args.round_turns,
           "lists": len(decks), "device": device, "workers": args.workers, "pairs": pairs, "arms": {}}
    res["engine"] = engine_stamp()
    print("engine", json.dumps(res["engine"]), flush=True)
    for arm in args.arms:
        if (out_path.parent / "STOP").exists():
            print("STOP file: stopping before arm", arm, flush=True)
            break
        if engine_stamp() != res["engine"]:             # each arm's workers load the engine when they start
            print(f"KILL: the compiled engine changed before arm {arm} ({json.dumps(engine_stamp())}); the arms would not "
                  "be on one engine", flush=True)
            sys.exit(3)
        r = play_arm(model, arms[arm], alld, pairs, args, rounds, device)
        res["arms"][arm] = r
        res["readout"] = readout(res["arms"], pairs, args.groups)
        c68 = C68_LAUNCH.parent / "xprobe.json"            # G's A/A with C68's G (the same deals at C68's settings)
        if arm == "G" and c68.exists():
            ref = json.loads(c68.read_text())
            if all(ref.get(k) == res[k] for k in ("games", "seed", "round_turns", "lists", "pairs")) and "G" in ref["arms"]:
                d = np.abs(np.array(r["per_pair"]) - np.array(ref["arms"]["G"]["per_pair"]))
                res["aa_c68"] = {"max_abs_pair": round(float(d.max()), 4), "pairs_differing": int((d > 1e-9).sum()),
                                 "three": paired(r, ref["arms"]["G"], pairs, THREE), "engine": res["engine"]["same_as_c68"]}
                print("aa_c68", json.dumps(res["aa_c68"]), flush=True)
        out_path.write_text(json.dumps(res, indent=1))
        print(arm, json.dumps({k: r[k] for k in ("last", "by_group", "steps_per_game", "turns_per_game", "per_game")}),
              flush=True)
        if r["errors"] > 0.01 * r["last"]["games"]:
            print(f"KILL: {r['errors']} errors in {r['last']['games']} games (over 1%) in arm {arm}", flush=True)
            sys.exit(2)
    print("readout", json.dumps(res.get("readout", {})), flush=True)


if __name__ == "__main__":
    main()
