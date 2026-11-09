"""C199's rule-9 replay and Amendment 1's (c) - (a) read (runs/probe/C199-offtype-replace/record.md). CPU, seconds.
--rule9: setA-rule9/ and setB-rule9/ replay the greedy cells (offa, offb) with per-seat counts, and set{A,B}/cells_greedy-offc_s1.json
adds arm (c). Checks the replay matches the saved greedy games, then per dir, variant seat (3 - iSeat) against the original,
per game: Trainer plays and play rate (turns played / turns legal), the added names' plays and play rate against the same
names in the original, own turns with no Energy in hand, attacks a turn, passes with an attack legal, Energy sent to the
own discard by Trainers (and by which), and the ending mix. Means over lists (each list's games averaged first), SE over lists.
Research's reading (#1018): (b) raising no-Energy turns and lowering attacks with play rates normal is starvation; large
Trainer discards, or high play rates where playing loses, is misplay.
--paired: (c) - (a) on the same deals, greedy and h2: per (list, v) the decisive variant shares' difference, averaged over v then
lists; SE with the lists fixed (C193 Amendment 3). Bands (Amendment 1): R-saturated >= -0.01; R-price-persists <= -0.03 with
the difference at least 2 SE below 0 (taken by default, row 115, for "at 2 SE"); between otherwise.
    py notes/scripts/c199_rule9.py --rule9 | --paired
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "runs/probe/C199-offtype-replace"
SETS = ("setA", "setB")
bare = lambda n: re.sub(r" [A-Z0-9]+$", "", n)


def load(f):
    f = D / f
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    return d if d.get("complete") else None


def over_lists(vals):
    """vals: list -> per-game values; mean of list means, SE over lists."""
    m = np.array([np.mean(v) for v in vals.values() if v])
    return [round(float(m.mean()), 4), round(float(m.std(ddof=1) / np.sqrt(len(m))), 4) if len(m) > 1 else None, len(m)] if len(m) else None


def rule9():
    out = {}
    for st in SETS:
        rep, old, offc = load(f"{st}-rule9/cells_greedy_s1.json"), load(f"{st}/cells_greedy_s1.json"), load(f"{st}/cells_greedy-offc_s1.json")
        if not rep:
            print(f"{st}: rule-9 replay not complete"); continue
        V = {(x["list"], x["dir"], x["v"]): x for x in json.loads((D / f"{st}/variants_s1.json").read_text(encoding="utf-8"))}
        key = lambda r: (r["list"], r["dir"], r["v"], r["seed"], r["iSeat"])
        ow = {key(r): r["winner"] for r in old["results"]}
        same = sum(ow.get(key(r)) == r["winner"] for r in rep["results"])
        o = {"replay_matches_greedy": [same, len(rep["results"])]}
        rows = rep["results"] + (offc["results"] if offc else [])
        for dr in ("offa", "offb", "offc"):
            R = [r for r in rows if r["dir"] == dr and r.get("turnSeat")]
            if not R:
                continue
            acc = defaultdict(lambda: defaultdict(list))   # metric -> list -> per-game values
            ends, trn = Counter(), Counter()
            for r in R:
                vs, os_ = str(3 - r["iSeat"]), str(r["iSeat"])
                added = {bare(c) for c in V[(r["list"], dr, r["v"])]["in"] if bare(c) in bare_trainers}
                for lab, s in (("var", vs), ("orig", os_)):
                    tp, ts = r["tplaySeat"].get(s, {}), r["turnSeat"].get(s, {"turns": 0, "noE": 0, "atk": 0, "atkUnused": 0, "trE": {}})
                    held, played = sum(x[0] for x in tp.values()), sum(x[1] for x in tp.values())
                    acc[f"{lab}_trainer_plays"][r["list"]].append(played)
                    if held:
                        acc[f"{lab}_play_rate"][r["list"]].append(played / held)
                    ah, ap = sum(tp.get(n, [0, 0])[0] for n in added), sum(tp.get(n, [0, 0])[1] for n in added)
                    if added:
                        acc[f"{lab}_added_names_plays"][r["list"]].append(ap)
                        if ah:
                            acc[f"{lab}_added_names_rate"][r["list"]].append(ap / ah)
                    if ts["turns"]:
                        acc[f"{lab}_noE_share"][r["list"]].append(ts["noE"] / ts["turns"])
                        acc[f"{lab}_attacks_a_turn"][r["list"]].append(ts["atk"] / ts["turns"])
                        acc[f"{lab}_unused_attack_a_turn"][r["list"]].append(ts["atkUnused"] / ts["turns"])
                    acc[f"{lab}_own_turns"][r["list"]].append(ts["turns"])
                    acc[f"{lab}_trainer_E_discard"][r["list"]].append(sum(x[1] for x in ts["trE"].values()))
                    if lab == "var":
                        for n, x in ts["trE"].items():
                            trn[n] += x[1]
                ends[r["ending"] or "?"] += 1
                if r["winner"] == r["iSeat"]:
                    ends["var_lost_" + (r["ending"] or "?")] += 1
            o[dr] = {k: over_lists(v) for k, v in sorted(acc.items())}
            for k in [k for k in o[dr] if k.startswith("var_")]:     # variant - original, per game, over lists
                kk = k[4:]
                if f"orig_{kk}" in o[dr] and o[dr][k] and o[dr][f"orig_{kk}"]:
                    o[dr][f"diff_{kk}"] = round(o[dr][k][0] - o[dr][f"orig_{kk}"][0], 4)
            o[dr]["games"] = len(R)
            o[dr]["endings"] = dict(ends)
            o[dr]["var_trainer_E_discard_by_name"] = dict(trn.most_common(8))
        out[st] = o
    (D / "rule9_read.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


def cell_shares(d, dr):
    c = defaultdict(lambda: [0, 0])
    for r in d["results"]:
        if r["dir"] == dr and r["winner"] in (1, 2):
            a = c[(r["list"], r["v"])]; a[0] += r["winner"] == 3 - r["iSeat"]; a[1] += 1
    return {k: w / n for k, (w, n) in c.items() if n}


def paired():
    out = {}
    for pl, fa, fc in (("greedy", "cells_greedy_s1.json", "cells_greedy-offc_s1.json"), ("h2", "cells_search_s1.json", "cells_search-offc_s1.json")):
        per = {}
        for st in SETS:
            a, c = load(f"{st}/{fa}"), load(f"{st}/{fc}")
            if not (a and c):
                continue
            sa, sc = cell_shares(a, "offa"), cell_shares(c, "offc")
            by = defaultdict(list)
            for k in sc:
                if k in sa:
                    by[k[0]].append(sc[k] - sa[k])
            lm = np.array([np.mean(v) for v in by.values()])
            var_w = sum(np.var(v, ddof=1) / len(v) for v in by.values() if len(v) > 1)
            S = lambda s: float(np.mean([np.mean([x for (l2, _), x in s.items() if l2 == l]) for l in by]))
            per[st] = {"diff": round(float(lm.mean()), 4), "se_lists_fixed": round(float(np.sqrt(var_w) / len(lm)), 4),
                       "se_over_lists": round(float(lm.std(ddof=1) / np.sqrt(len(lm))), 4), "lists": len(lm), "S_c": round(S(sc), 4), "S_a_same_lists": round(S(sa), 4)}
        if not per:
            continue
        o = {"sets": per}
        if len(per) == 2:
            x = [per[s]["diff"] for s in SETS]
            m, se = float(np.mean(x)), float(np.hypot(*[per[s]["se_lists_fixed"] for s in SETS]) / 2)
            o["pooled"] = {"diff": round(m, 4), "se": round(se, 4), "same_side_of_-0.02": (x[0] + 0.02) * (x[1] + 0.02) > 0}
            o["band"] = "R-saturated" if m >= -0.01 else "R-price-persists" if m <= -0.03 and m <= -2 * se else "between"
        out[pl] = o
    (D / "paired_c_a.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


sys.path.insert(0, str(ROOT))
from rl.decks import Pool                                # noqa: E402
bare_trainers = {bare(c["fullName"]) for c in Pool().cards if c["superType"] == 2}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule9", action="store_true")
    ap.add_argument("--paired", action="store_true")
    a = ap.parse_args()
    if a.rule9:
        rule9()
    if a.paired:
        paired()
