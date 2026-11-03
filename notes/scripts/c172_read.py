"""C172 (runs/probe/C172-offlist-names/record.md, with Amendment 1): the bands read the pooled price of the four names; a search fall under 0.015 needs an SE of 0.015 or less, or the read is unresolved; per-name bands only where a name's own fall SE is 0.015 or less; the price split by whether the swapped card was
the list's most-copied Basic; s4 and the B rule. Also per name, the price of the swap (copy - list, event points/3, paired by deal), SE by a bootstrap over lists, greedy under C127 s16 and arm 0 s1 and C139's search under arm 0 s1; the bands; the replaced attackers; the checks. Seaking and
Weepinbell have no price here, only C171's trace read. Also from existing games: C170 Y's score per opponent list against G's, under C127 s16 and s17.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c172_read.py
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from c139_read import pts, r3
import c167_read as C
import c170_read as V

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C172-offlist-names"
NAMES = ("Tauros", "Lickitung", "Kangaskhan", "Snorlax")


def per_deal(path):
    r = json.loads(Path(path).read_text(encoding="utf-8"))
    by = {(x["i"], x["j"], x["seed"]): x for x in r["results"] if not x.get("error")}
    deals = defaultdict(dict)
    unpaired, seats = 0, True
    for m in r["meta"]:
        seeds = {s for (i, j, s) in by if i == m["list"] and j == m["opp"]}
        for name, c in m["copies"].items():
            for s in seeds:
                g = by.get((c, m["opp"], s))
                if g is None:
                    unpaired += 1
                    continue
                b = by[(m["list"], m["opp"], s)]
                seats &= g["iSeat"] == b["iSeat"]
                deals[name][(m["list"], m["opp"], s)] = pts(g)[0] - pts(b)[0]
    return r, deals, {"unpaired": unpaired, "seats_equal": seats, "errors": sum(1 for x in r["results"] if x.get("error")), "games": len(r["results"])}


def paralysis(path):
    """Research's addition: per turn a player's Active is Paralyzed, was Full Heal or Switch held, and was it played? Retreating isn't legal, so any retreat would be a fault."""
    rows = [json.loads(x) for x in open(str(path) + ".paralyzed.jsonl", encoding="utf-8")] if Path(str(path) + ".paralyzed.jsonl").exists() else []
    turns = defaultdict(list)
    for r in rows:
        turns[(r["seed"], r["turn"])].append(r)
    out = {"turns_paralyzed": len(turns), "actions": len(rows), "types": dict(Counter(str(r["type"]) for r in rows).most_common(8))}
    for key, label in (("fullHeal", "Full Heal"), ("sw", "Switch")):
        held = [v for v in turns.values() if any(r[key] for r in v)]
        played = [v for v in held if any(r["card"] == label for r in v)]
        out[label] = {"turns_held": len(held), "turns_played": len(played), "rate": r3(len(played) / len(held)) if held else None}
    out["retreats_while_paralyzed"] = sum(1 for r in rows if "RETREAT" in str(r["type"]).upper())
    out["attacks_while_paralyzed"] = sum(1 for r in rows if "ATTACK" in str(r["type"]).upper())
    return out


def paralysis_all(fs):
    each = [paralysis(f) for f in fs]
    out = {"turns_paralyzed": sum(e["turns_paralyzed"] for e in each), "retreats_while_paralyzed": sum(e["retreats_while_paralyzed"] for e in each), "attacks_while_paralyzed": sum(e["attacks_while_paralyzed"] for e in each)}
    for label in ("Full Heal", "Switch"):
        h, p = sum(e[label]["turns_held"] for e in each), sum(e[label]["turns_played"] for e in each)
        out[label] = {"turns_held": h, "turns_played": p, "rate": r3(p / h) if h else None}
    return out


def boot_lists(d, rng, reps=2000):
    per = defaultdict(list)
    for (k, _, _), x in d.items():
        per[k].append(x)
    means = np.array([np.mean(v) for v in per.values()])
    draws = rng.integers(len(means), size=(reps, len(means)))
    return float(means[draws].mean(1).std(ddof=1)), len(means)


def main():
    rng = np.random.default_rng(172)
    files = {"G_s16": [OUT / "G_s16.json"], "G_arm0": [OUT / "G_arm0.json"], "S_arm0": sorted(OUT.glob("S_arm0_p*.json"))}
    res, deals = {}, {}
    for tag, fs in files.items():
        fs = [f for f in fs if f.exists()]
        if not fs:
            continue
        d, chk, r = defaultdict(dict), Counter(), None
        for f in fs:
            r1, d1, c1 = per_deal(f)
            r = r1 if r is None else r
            for n, v in d1.items():
                d[n].update(v)
            chk.update({k: v for k, v in c1.items() if k != "seats_equal"})
            chk["seats_unequal_files"] += 0 if c1["seats_equal"] else 1
        chk = dict(chk)
        deals[tag] = d
        f = fs[0]
        rows = {}
        for n in NAMES:
            xs = d.get(n, {})
            if not xs:
                continue
            se, lists = boot_lists(xs, rng)
            rows[n] = {"price": r3(float(np.mean(list(xs.values())))), "se": r3(se), "deals": len(xs), "lists": lists}
        res[tag] = {"checks": chk, "parts": len(fs), "last": r.get("last"), "prices": rows, "replaced": dict(Counter(v["target"] for v in r["variants"])), "paralysis": paralysis_all(fs)}
    # the top-basic flag per (list, name), for the split
    top = {}
    for tag, fs in files.items():
        for f in [x for x in fs if x.exists()]:
            for v in json.loads(f.read_text(encoding="utf-8"))["variants"]:
                top[(v["base"], v["group"])] = v.get("is_top_basic", True)

    def pooled(tag, keep=None):
        """All four names' deals, by list; keep picks (list, name) pairs."""
        x = {(n, *k): v for n in NAMES for k, v in deals.get(tag, {}).get(n, {}).items() if keep is None or keep(k[0], n)}
        if not x:
            return None
        per = defaultdict(list)
        for (n, k, o, sd), v in x.items():
            per[k].append(v)
        means = np.array([np.mean(v) for v in per.values()])
        draws = rng.integers(len(means), size=(2000, len(means)))
        return {"price": r3(float(np.mean(list(x.values())))), "se": r3(float(means[draws].mean(1).std(ddof=1))), "deals": len(x), "lists": len(means)}

    unchanged = lambda k, n: top.get((k, n), True)
    changed = lambda k, n: not top.get((k, n), True)
    pool_read = {t: {"all": pooled(t), "swapped_most_copied_basic": pooled(t, unchanged), "swapped_a_lesser_basic": pooled(t, changed)} for t in deals}
    fall = None
    if "S_arm0" in deals and "G_arm0" in deals:
        d = {}
        for n in NAMES:
            s_, g_ = deals["S_arm0"].get(n, {}), deals["G_arm0"].get(n, {})
            for k in set(s_) & set(g_):
                d[(n, *k)] = s_[k] - g_[k]
        if d:
            per = defaultdict(list)
            for (n, k, o, sd), v in d.items():
                per[k].append(v)
            means = np.array([np.mean(v) for v in per.values()])
            draws = rng.integers(len(means), size=(2000, len(means)))
            fall = {"search_minus_greedy": r3(float(np.mean(list(d.values())))), "se": r3(float(means[draws].mean(1).std(ddof=1))), "deals": len(d), "lists": len(means)}

    def read_band(g16, g0, f):
        if not g16 or not g0:
            return "not read yet"
        below = all(x["price"] <= -0.04 and x["price"] <= -2 * x["se"] for x in (g16, g0))
        if below:
            return "R-below"
        at = g16["price"] >= -0.02 and g0["price"] >= -0.02
        if not at:
            return "between"
        if f is None:
            return "at or above under greedy; search not read yet"
        m, se = -f["search_minus_greedy"], f["se"]
        if m >= 0.03 and m >= 2 * se:
            return "R-easy-to-pilot"
        if m < 0.015 and se <= 0.015:
            return "R-pipeline-signal"
        return "unresolved"

    g16, g0 = pool_read.get("G_s16", {}), pool_read.get("G_arm0", {})
    band_all = read_band(g16.get("all"), g0.get("all"), fall)
    # R-at-or-above can't rest on the changed lists alone: the unchanged lists must meet it too
    u16, u0 = g16.get("swapped_most_copied_basic"), g0.get("swapped_most_copied_basic")
    unchanged_ok = bool(u16 and u0 and u16["price"] >= -0.02 and u0["price"] >= -0.02)
    if band_all in ("R-easy-to-pilot", "R-pipeline-signal") and not unchanged_ok:
        band_all = "unresolved (the unchanged lists don't meet at-or-above)"
    # s4: the four names' share of Pokemon copies in the plain Y decks
    from rl.decks import Pool
    card = {c["fullName"]: c for c in Pool().cards}
    gate = ROOT / "runs/probe/C171-table-drafting/gate"
    s4 = {}
    for sd in (48, 49):
        for v in "XY":
            f = gate / f"{v}_s{sd}.json"
            if f.exists():
                c = Counter(card[x]["name"] for d_ in json.loads(f.read_text(encoding="utf-8")) for x in d_["cards"] if card[x]["superType"] == 1)
                s4[f"{v}_s{sd}"] = r3(sum(c[n] for n in NAMES) / sum(c.values()))
    bands = {}
    for n in NAMES:
        one = lambda t: res.get(t, {}).get("prices", {}).get(n)
        f1 = None
        if "S_arm0" in deals and n in deals["S_arm0"]:
            s_, g_ = deals["S_arm0"][n], deals["G_arm0"].get(n, {})
            both = {k: s_[k] - g_[k] for k in set(s_) & set(g_)}
            if both:
                se, _ = boot_lists(both, rng)
                f1 = {"search_minus_greedy": r3(float(np.mean(list(both.values())))), "se": r3(se), "deals": len(both)}
        bands[n] = {"greedy_s16": one("G_s16"), "greedy_arm0": one("G_arm0"), "search_arm0": one("S_arm0"), "fall": f1, "band": read_band(one("G_s16"), one("G_arm0"), f1) if f1 and f1["se"] <= 0.015 else "no band: its fall SE is over 0.015 or not read"}
    dropped = json.loads(files["G_arm0"][0].read_text(encoding="utf-8")).get("dropped_lists") if files["G_arm0"][0].exists() else None
    out = {"pooled_band": band_all, "pooled": pool_read, "pooled_fall": fall, "unchanged_lists_meet_at_or_above": unchanged_ok, "s4": s4, "dropped_lists": dropped,
           "B_holds_if_chosen_variant_s4_at_least_0.5": band_all in ("R-easy-to-pilot", "R-pipeline-signal"), "bands": bands, "pilots": res,
           "no_price": {"Seaking": "needs a line and typed Energy: trace read only (C171, trace_read.json)", "Weepinbell": "needs a line and typed Energy: trace read only (C171, trace_read.json)"}}
    # C170 Y against G, by opponent list, under the two loop pilots
    v = {}
    for p in ("s16", "s17"):
        G, Y = V.cell("G", f"L_{p}"), V.cell(f"Y_{p}", f"L_{p}")
        rows = {}
        for o in sorted(set(G["opp"].tolist())):
            rows[o] = {"G": r3(float(G["score"][G["opp"] == o].mean())), "Y": r3(float(Y["score"][Y["opp"] == o].mean()))}
        gaps = np.array([r["Y"] - r["G"] for r in rows.values()])
        v[p] = {"opponents": len(rows), "opponents_where_Y_beats_G": int((gaps > 0).sum()), "gap_mean": r3(float(gaps.mean())), "gap_sd": r3(float(gaps.std())), "worst": sorted(rows.items(), key=lambda t: t[1]["Y"] - t[1]["G"])[:3], "best": sorted(rows.items(), key=lambda t: -(t[1]["Y"] - t[1]["G"]))[:3], "rows": rows}
    out["C170_Y_by_opponent"] = v
    (OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("pooled_band", "pooled", "pooled_fall", "unchanged_lists_meet_at_or_above", "s4", "dropped_lists", "B_holds_if_chosen_variant_s4_at_least_0.5", "no_price")}))
    print(json.dumps(bands))
    for tag, x in res.items():
        print(tag, x["prices"], x["checks"], x["replaced"])
        print("   paralysis", x["paralysis"])
    for p, x in v.items():
        print(p, {k: x[k] for k in ("opponents", "opponents_where_Y_beats_G", "gap_mean", "gap_sd", "worst", "best")})


if __name__ == "__main__":
    main()
