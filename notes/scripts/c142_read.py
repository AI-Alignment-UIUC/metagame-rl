"""C142 (runs/probe/C142-tempo-package/record.md, with Amendment 1): over paired deals (a list and each of its copies against the same
opponent, seed and seat), each single's price (list - copy in event points over 3; c139_read.pts), the joint price J, the sum of the
list's singles Sigma, and the complementarity C = J - Sigma per deal, with bootstrap SEs over deals (c139_read.boot, 2,000) and the
record's bands. Per-list values too, and SE(C) projected to more deals a pair (it scales as 1/sqrt(deals)). Checks: every copy holds 60
cards and none of its swapped cards, and every key's list and copy games share their seeds and seats. Several --file (stages on
other seeds, so other deals) pool their deals. Writes summary<tag>.json.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c142_read.py [--file S_s91.json S_s92.json] [--tag ""]
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from c139_read import bare, boot, pts, r3
from c142_run import TV

OUT = Path(__file__).resolve().parents[2] / "runs/probe/C142-tempo-package"
mean = lambda xs: sum(xs) / len(xs) if xs else None


def band(p, se):                                      # C144's bands on a group's price (read on S)
    return ("R-above" if p >= 0.04 and p >= 2 * se else "R-below" if p <= -0.04 and p <= -2 * se else
            "R-parity" if abs(p) < 2 * se and se <= 0.02 else "between")


def read(paths):
    r = json.loads(paths[0].read_text(encoding="utf-8"))
    for q in paths[1:]:                               # another stage: the same lists, copies and keys on another seed
        r2 = json.loads(q.read_text(encoding="utf-8"))
        assert r2["meta"] == r["meta"] and r2["variants"] == r["variants"] and r2["seed"] != r["seed"] and r2.get("arm") == r.get("arm")
        r["results"] += r2["results"]
        r["games"] += r2["games"]
    names, cards = r["deck_names"], r["deck_cards"]
    swapped = lambda g: TV.GROUPS.get(g, (g,))                  # tempo4 and C144's groups, or a single card's name
    checks = {"sixty_cards": all(len(cards[v["variant"]]) == 60 == len(cards[v["base"]]) for v in r["variants"]),
              "swapped_absent": all(not any(bare(c) in swapped(v["group"]) for c in cards[v["variant"]]) for v in r["variants"]),
              "unpaired": 0, "paired_seats_equal": True}
    by = {(x["i"], x["j"], x["seed"]): x for x in r["results"] if not x.get("error")}
    single, joint, sig, cc, per = defaultdict(list), [], [], [], defaultdict(lambda: defaultdict(list))
    n_rep, copies = {v["variant"]: v["replaced"] for v in r["variants"]}, defaultdict(list)   # C144: copies replaced, per deal
    for m in r["meta"]:
        seeds = {s for (i, j, s) in by if i == m["list"] and j == m["opp"]}
        for g, c in m["copies"].items():
            checks["unpaired"] += len(seeds ^ {s for (i, j, s) in by if i == c and j == m["opp"]})
        for s in sorted(seeds):
            gl = by[(m["list"], m["opp"], s)]
            d = {}
            for g, c in m["copies"].items():
                gc = by.get((c, m["opp"], s))
                if gc is None:
                    continue
                checks["paired_seats_equal"] &= gl["iSeat"] == gc["iSeat"]
                d[g] = pts(gl)[0] - pts(gc)[0]
                copies[g].append(n_rep[c])
            for g, x in d.items():
                (joint if g == "tempo4" else single[g]).append(x)
                per[names[m["list"]]][g].append(x)
            if "tempo4" in m["copies"] and len(d) == len(m["copies"]):
                sg = sum(x for g, x in d.items() if g != "tempo4")
                sig.append(sg)
                cc.append(d["tempo4"] - sg)
    out = {"errors": sum(1 for x in r["results"] if x.get("error")), "games": len(r["results"]), "deals_a_pair": r["games"],
           "singles": {g: {"deals": len(xs), "price": r3(mean(xs)), "se": r3(boot(xs)), "copies_mean": r3(mean(copies[g])),
                           "copies_max": max(copies[g]), "per_copy": r3(mean(xs) / mean(copies[g])), "band": band(mean(xs), boot(xs))}
                       for g, xs in sorted(single.items())},
           "J": {"deals": len(joint), "price": r3(mean(joint)), "se": r3(boot(joint)) if joint else None},
           "Sigma": {"deals": len(sig), "mean": r3(mean(sig)), "se": r3(boot(sig)) if sig else None},
           "C": {"deals": len(cc), "mean": r3(mean(cc)), "se": r3(boot(cc)) if cc else None,
                 "sd": r3((sum((x - mean(cc)) ** 2 for x in cc) / (len(cc) - 1)) ** 0.5) if len(cc) > 1 else None},
           "by_list": {k: {g: r3(mean(xs)) for g, xs in sorted(v.items())} for k, v in sorted(per.items())},
           "checks": checks, "search": r.get("last", {}).get("search")}
    if cc:                                            # SE(C) at full size (every joint list, 23 opponents) and g deals a pair
        n_joint = sum(1 for v in r["variants"] if v["group"] == "tempo4")
        sd = out["C"]["sd"]
        out["C"]["se_projected"] = {g: r3(sd / (n_joint * 23 * g) ** 0.5) for g in (2, 4, 6, 7, 8, 10)}
        c, se, j = out["C"]["mean"], out["C"]["se"], out["J"]["price"]
        out["band"] = ("R-complement" if c >= 0.04 and c >= 2 * se and j >= 0.04 else
                       "R-anti" if c <= -0.04 and c <= -2 * se else
                       "R-additive" if abs(c) < 2 * se and se <= 0.02 else "between")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", nargs="+", default=["S_s91.json"])
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    out = read([OUT / f for f in a.file])
    (OUT / f"summary{a.tag}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        if k != "by_list":
            print(k, v)


if __name__ == "__main__":
    main()
