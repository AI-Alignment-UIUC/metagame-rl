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

C99 (runs/probe/C99-cs-timing/record.md), with --timing-card NAME: two more arms and a follow-through log.
  T  the timing oracle (--timing-oracle 1): at a main-phase decision where playing the card is legal, the better of the
     pilot's pick and playing it (or the pilot's next pick, if its pick plays it), by re-dealt copies played to the end of the turn
  ST both oracles
Every arm logs each play of the card (the fetched card and its type, the discards, whether the fetched card is used the same turn,
the pilot's value before the play and at the seat's next decision after the turn): "follow" in the arm's JSON. The readout adds
"timing": each arm's price, T - G, ST - S and ST - G paired by list, the timing counts. --decks PATH reads the lists
from a JSON file ([{name, cards}], e.g. runs/probe/BENCH/decks_P.json) instead of the archived ones.

C109 (runs/probe/C109-opponent-strength/record.md): each side of a pair can have its own pilot and arm. --pilot-b plays the copies
(the variant decks) and --pilot the lists; --arm-a / --arm-b (G, S, T, ST) are the switch sets of the lists' side and the copies' side
(model slots 0 and 1 in the worker, joined by "--side-b"); with either, one arm "<a>|<b>" is played and --arms is ignored.
--copy-vs-copy plays each copy (side a) against a second copy of the same deck (side b), seats alternating. Unused: as before.

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
TIMING = ("tSearched", "tUnsearchable", "tPlays", "tHolds", "tGainSum")
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
        self.stats, self.ft, self.by, self.pp = [], [], {}, []

    def collect(self, msgs, models, device):
        replies = super().collect(msgs, models, device)
        self.stats += [r["switchStats"] for r in replies if "switchStats" in r]
        self.ft += [e for r in replies for e in r.get("switchStats", {}).pop("ft", [])]    # C99's log, not a count
        self.pp += [e for r in replies for e in r.get("switchStats", {}).pop("pp", [])]    # C106's damage hits
        for r in replies:                               # C102: prompts the oracle answered, by message
            for m, c in r.get("switchStats", {}).pop("oracleBy", {}).items():
                self.by[m] = self.by.get(m, 0) + c
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


def follow(ft: list) -> dict:
    """C99's follow-through of an arm's plays of the timing card (the worker's log, both seats): the same-turn use share,
    overall and by the fetched card's type, and the mean change of the pilot's value V (after - before) with its SE."""
    got = [e for e in ft if e["fetched"] is not None]
    share = lambda xs: {"n": len(xs), "used": sum(bool(e["used"]) for e in xs),
                        "share": round(sum(bool(e["used"]) for e in xs) / len(xs), 4) if xs else None}
    d = np.array([e["after"] - e["V"] for e in ft if e["V"] is not None and e["after"] is not None])
    return {"plays": len(ft), "no_fetch": len(ft) - len(got), "same_turn_use": share(got),
            "by_type": {t: share([e for e in got if e["type"] == t]) for t in ("Pokemon", "Trainer", "Energy")},
            "dV": {"n": len(d), "mean": round(float(d.mean()), 4) if len(d) else None,
                   "se": round(float(d.std(ddof=1) / np.sqrt(len(d))), 4) if len(d) > 1 else None},
            "log": ft}


def conversions(pp: list, plays: int, games: int) -> dict:
    """C106: the knockout-conversion counts from the worker's damage hits (the engine's own damage, both seats). A play's attack
    is a hit with PlusPower attached (plus > 0); a conversion is such a hit that knocked the Defending Pokemon out (koOff 0) and
    would not have without the +10s (dmg - 10 * plus < left). A missed conversion is a hit with a PlusPower in hand and none
    attached where +10 turns a hit that did damage (base > 0) into a knockout (dmg < left <= dmg + 10)."""
    played = [h for h in pp if h["plus"] > 0]
    ko = [h for h in played if h["koOff"] == 0]
    conv = [h for h in ko if h["base"] > 0 and h["dmg"] - 10 * h["plus"] < h["left"]]
    missed = [h for h in pp if h["plus"] == 0 and h["inHand"] > 0 and h["base"] > 0 and h["dmg"] < h["left"] <= h["dmg"] + 10]
    return {"plays": plays, "attacks_after_play": len(played), "ko_after_play": len(ko), "conversions": len(conv),
            "conversion_share": round(len(conv) / plays, 4) if plays else None, "hits": len(pp),
            "holds": sum(h["plus"] == 0 and h["inHand"] > 0 for h in pp), "missed": len(missed),
            "missed_per_game": round(len(missed) / max(games, 1), 4)}


def gust(ft: list) -> dict:
    """C107: the Gust plays' targets (the chosen Pokemon's bench slot, card, HP left) and how many were knocked out the same turn
    (koOff 0) or the opponent's next turn (koOff 1)."""
    t = [e for e in ft if e.get("target")]
    cnt = lambda xs: {k: sum(x == k for x in xs) for k in sorted(set(xs), key=str)}
    return {"plays": len(ft), "targets": len(t), "ko_same_turn": sum(e["koOff"] == 0 for e in t),
            "ko_next_turn": sum(e["koOff"] == 1 for e in t), "by_slot": cnt([e["target"]["slot"] for e in t]),
            "by_card": cnt([e["target"]["card"] for e in t]),
            "mean_left": round(float(np.mean([e["target"]["left"] for e in t])), 2) if t else None}


def play_arm(model, switches: list, decks: list, pairs: list, args, rounds, device: str, sides: dict = None) -> dict:
    rp = OraclePool(args.workers, switches)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, args.workers, device=device)
        W, G, _ = gm.play(decks, args.games, args.seed, pairs=[(p["base"], p["variant"]) for p in pairs],
                          pair_keys=[p["base"] for p in pairs], round_turns=rounds, **(sides or {}))
    finally:
        rp.close()
    n = len(gm.results)
    sw = add_stats(rp.stats)
    sw["oracleBy"] = rp.by
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
    extra = {}
    if "--timing-card" in switches:                     # C99: the arm's follow-through and timing counts
        extra["follow"], extra["sec_per_game"] = follow(rp.ft), round(gm.last["seconds"] / max(n, 1), 2)
        if args.timing_card == "PlusPower":
            extra["follow"]["conversions"], extra["follow"]["pp_log"] = conversions(rp.pp, len(rp.ft), n), rp.pp
        if args.timing_card == "Gust of Wind":
            extra["follow"]["gust"] = gust(rp.ft)
        if "--timing-oracle" in switches:
            extra["timing"] = {k: round(sw.get(k, 0), 4) for k in TIMING}
    return {"switches": switches, "last": gm.last, **extra, "by_group": by_group, "per_pair": [round(v, 4) for v in per_pair],
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


def timing_readout(arms: dict, pairs: list, groups: list) -> dict:
    """C99: each arm's price over `groups` (by list), T - G, ST - S and ST - G paired by list, the timing counts."""
    rd = {"price": {a: {g: level(r, pairs, (g,)) for g in groups} | {"all": level(r, pairs, groups)} for a, r in arms.items()}}
    for name, (a, b) in {"T-G": ("T", "G"), "ST-S": ("ST", "S"), "ST-G": ("ST", "G")}.items():
        if a in arms and b in arms:
            rd[name] = {g: paired(arms[a], arms[b], pairs, (g,)) for g in groups} | {"all": paired(arms[a], arms[b], pairs, groups)}
    rd["timing"] = {a: arms[a]["timing"] for a in ("T", "ST") if a in arms}
    rd["follow"] = {a: {k: v for k, v in r["follow"].items() if k not in ("log", "pp_log")} for a, r in arms.items() if "follow" in r}
    return rd


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True, help="a learned pilot checkpoint (.pt), on both seats, greedy")
    ap.add_argument("--pilot-b", default=None, help="C109: the pilot (.pt) of the copies' side (default: --pilot)")
    ap.add_argument("--arm-a", default=None, choices=["G", "S", "T", "ST"], help="C109: the lists' side arm (with --arm-b, one arm a|b)")
    ap.add_argument("--arm-b", default=None, choices=["G", "S", "T", "ST"], help="C109: the copies' side arm")
    ap.add_argument("--copy-vs-copy", action="store_true", help="C109: each copy (side a) against a second copy of it (side b)")
    ap.add_argument("--arms", nargs="+", default=["G", "S"], choices=["G", "S", "T", "ST"])
    ap.add_argument("--timing-card", default=None, help='C99: log this card\'s plays, e.g. "Computer Search"; arms T and ST need it')
    ap.add_argument("--decks", default=None, help="a JSON file of lists [{name, cards}] instead of the archived ones")
    ap.add_argument("--groups", nargs="+", default=["draw", *THREE],
                    help=f"groups ({', '.join(GROUPS)}) or single card names, e.g. \"Computer Search\" (C98)")
    ap.add_argument("--lists", type=int, default=0, help="only the first N archived lists (smoke tests); 0 all 24")
    ap.add_argument("--games", type=int, default=16, help="games per pair (both seats)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--round-turns", default="20-45", help='the 2000 round rule, "T" or "A-B"; "0" off')
    ap.add_argument("--cap", type=int, default=8, help="options searched a prompt at most (the pilot's most likely)")
    ap.add_argument("--dets", type=int, default=4, help="re-dealt copies a prompt, the same for every option")
    ap.add_argument("--max-steps", type=int, default=60, help="a line's steps at most, then scored by the value")
    ap.add_argument("--oracle-check", type=int, default=0, help="1: check each searched prompt's replay (smoke)")
    ap.add_argument("--oracle-prompts", default="all", choices=["all", "fetch", "discard"],
                    help="C102: the oracle answers only CHOOSE_CARD_TO_HAND (fetch) or CHOOSE_CARD_TO_DISCARD (discard) prompts")
    ap.add_argument("--oracle-trainer", default=None,
                    help='C107: the oracle answers only prompts opened while this Trainer is resolving, e.g. "Gust of Wind"; combines with --oracle-prompts')
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    rounds = round_turns(args.round_turns)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    limits.apply(device, args.workers)
    pool = Pool()
    decks = json.loads(Path(args.decks).read_text()) if args.decks else [{"name": n, "cards": pool.names(v)} for n, v in archived_decks(pool)]
    if args.lists:
        decks = decks[:args.lists]
    alld, pairs = variants(pool, decks, args.groups)
    model, enc = load_policy(args.pilot, device)
    assert enc == "tokens", "the oracle worker needs the token encoding"
    sided = bool(args.pilot_b or args.arm_a or args.arm_b or args.copy_vs_copy)
    if sided:                                           # C109: slot 0 plays side a, slot 1 side b
        model_b, enc_b = load_policy(args.pilot_b or args.pilot, device)
        assert enc_b == "tokens", "the oracle worker needs the token encoding"
        if args.copy_vs_copy:                           # the copies against second copies of themselves
            first = len(alld)
            alld = alld + [alld[p["variant"]] for p in pairs]
            pairs = [{**p, "base": p["variant"], "variant": first + k} for k, p in enumerate(pairs)]
        sides = {"models": {0: model, 1: model_b}, "slots": [0] * len(alld)}
        for p in pairs:
            sides["slots"][p["variant"]] = 1
    arms = {"G": [], "S": ["--prompts", "search", "--cap", str(args.cap), "--dets", str(args.dets),
                           "--max-steps", str(args.max_steps), "--oracle-check", str(args.oracle_check)]}
    if args.oracle_prompts != "all":
        arms["S"] += ["--oracle-prompts", args.oracle_prompts]
    if args.oracle_trainer:
        arms["S"] += ["--oracle-trainer", args.oracle_trainer]
    assert args.timing_card or not {"T", "ST"} & set(args.arms), "arms T and ST need --timing-card"
    if args.timing_card:
        tc = ["--timing-card", args.timing_card]
        arms = {"G": tc, "S": arms["S"] + tc, "T": tc + ["--timing-oracle", "1"], "ST": arms["S"] + tc + ["--timing-oracle", "1"]}
    if sided:                                           # one arm, each side with its own switches
        a_arm, b_arm = args.arm_a or "G", args.arm_b or "G"
        assert args.timing_card or not {"T", "ST"} & {a_arm, b_arm}, "arms T and ST need --timing-card"
        name = f"{a_arm}|{b_arm}"
        arms[name] = [*arms[a_arm], "--side-b", *arms[b_arm]]
        args.arms = [name]
    out_path = ROOT / args.out
    res = {"pilot": args.pilot, "games": args.games, "seed": args.seed, "round_turns": args.round_turns,
           "lists": len(decks), "oracle_prompts": args.oracle_prompts,
           **({"oracle_trainer": args.oracle_trainer} if args.oracle_trainer else {}), "device": device, "workers": args.workers, "pairs": pairs, "arms": {},
           **({"sides": {"a": {"pilot": args.pilot, "arm": a_arm}, "b": {"pilot": args.pilot_b or args.pilot, "arm": b_arm},
                         "copy_vs_copy": args.copy_vs_copy}} if sided else {})}
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
        r = play_arm(model, arms[arm], alld, pairs, args, rounds, device, sides if sided else None)
        res["arms"][arm] = r
        res["readout"] = readout(res["arms"], pairs, args.groups)
        if args.timing_card:
            res["readout"]["timing"] = timing_readout(res["arms"], pairs, args.groups)
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
