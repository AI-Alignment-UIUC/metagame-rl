"""The Worlds 2005 legal card pool (2004-05 Modified), from set codes, and how much of it the engine has.

Legal at the 2005 World Championships (San Diego, 19-21 Aug 2005), per the format's set list
(pokumon.com/2005-pokemon-world-championships, after Bulbapedia's 2004-05 Modified format page):
EX Ruby & Sapphire, Sandstorm, Dragon, Team Magma vs Team Aqua, Hidden Legends, FireRed & LeafGreen,
Team Rocket Returns, Deoxys, Emerald; POP Series 1; EX Trainer Kit (Latias, Latios); Nintendo Black
Star Promos 1-27.
EX Trainer Kit 2 (Plusle & Minun) is on that list too, but it was released in March 2006, after Worlds,
so it is left out (TK2_BY_DATE below; it only adds Plusle and Minun, the rest are reprints).

Each legal printing (a pokemon-tcg-data card) is classed against the engine:
  exact    the engine has this name in the same printed set (per printing: a set with three
           Arons needs three engine Arons)
  reprint  the engine has a card of this name whose own printing plays identically (same
           signature as in ryuu_coverage_season.py: HP, types, attacks, Powers, rules text ...)
  missing  otherwise
A card is "in the engine" when exact or reprint. Distinct cards = distinct signatures (a reprint in a
Trainer Kit or Emerald is the same card in play).

  .venv/Scripts/python notes/scripts/ryuu_legal_pool_2005.py [--json notes/data/eval/legal_pool_2005.json]
  (RYUU_PLAY=<engine checkout> to read another engine tree, e.g. a worktree)
"""
import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ryuu_coverage_season as cov  # noqa: E402  (norm, signature, tcg_set, engine_cards, ENGINE_SET)

# Card identity here keeps the symbols the coverage script drops (decklists write "Rayquaza" for
# Rayquaza Star): Rayquaza Star is not Rayquaza, and Nidoran female is not Nidoran male.
_norm = cov.norm
cov.norm = lambda s: _norm(s.replace("★", " star").replace("♀", " female").replace("♂", " male"))

LEGAL_SETS = ["ex1", "ex2", "ex3", "ex4", "ex5", "ex6", "ex7", "ex8", "ex9", "pop1", "tk1a", "tk1b"]
PROMOS = ("np", 1, 27)                       # Nintendo Black Star Promos #1-27
TK2_BY_DATE = ["tk2a", "tk2b"]               # released March 2006: not legal at Worlds 2005
SET_NAMES = {"ex1": "Ruby & Sapphire", "ex2": "Sandstorm", "ex3": "Dragon", "ex4": "Team Magma vs Team Aqua",
             "ex5": "Hidden Legends", "ex6": "FireRed & LeafGreen", "ex7": "Team Rocket Returns", "ex8": "Deoxys",
             "ex9": "Emerald", "pop1": "POP Series 1", "tk1a": "EX Trainer Kit (Latias)",
             "tk1b": "EX Trainer Kit (Latios)", "np": "Nintendo Black Star Promos 1-27"}


def legal_cards() -> list:
    cards = [c for sid in LEGAL_SETS for c in cov.tcg_set(sid)]
    sid, lo, hi = PROMOS
    cards += [c for c in cov.tcg_set(sid) if c["number"].isdigit() and lo <= int(c["number"]) <= hi]
    return cards


def engine_legal_fullnames() -> list:
    """fullNames of the engine's cards printed in a 2005-legal set (what a 2005 format registers)."""
    import glob
    import os
    import re
    legal = set(LEGAL_SETS) | {PROMOS[0]}
    engine = Path(os.environ.get("RYUU_PLAY") or cov.ROOT / "ryuu-play")
    out = []
    for f in glob.glob(str(engine / "packages/sets/src/**/*.ts"), recursive=True):
        t = open(f, encoding="utf-8").read()
        fm = re.search(r"public fullName: string = '((?:[^'\\]|\\.)*)'", t)
        sm = re.search(r"public set: string = '([^']*)'", t)
        if fm and sm and cov.ENGINE_SET.get(sm.group(1).upper()) in legal:
            out.append(fm.group(1).replace("\\'", "'"))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    args = ap.parse_args()
    cards = legal_cards()
    eng = cov.engine_cards()                                  # norm(name) -> [set id per engine card file]
    # Engine printings available per (set, name), used up one per legal printing.
    left = collections.Counter((s, n) for n, sets in eng.items() for s in sets if s)
    # Signatures of every printing the engine has a card for (for reprints).
    by_set_name = collections.defaultdict(list)
    for s in {s for sets in eng.values() for s in sets if s}:
        for c in cov.tcg_set(s):
            by_set_name[(s, cov.norm(c["name"]))].append(c)
    eng_sigs = collections.defaultdict(set)
    for n, sets in eng.items():
        for s in set(sets):
            if s:
                eng_sigs[n] |= {cov.signature(c) for c in by_set_name.get((s, n), [])}
    rows = []
    for c in sorted(cards, key=lambda c: (c["id"].split("-")[0], int("".join(ch for ch in c["number"] if ch.isdigit()) or 0))):
        sid, n = c["id"].split("-")[0], cov.norm(c["name"])
        if left[(sid, n)] > 0:
            left[(sid, n)] -= 1
            status = "exact"
        elif cov.signature(c) in eng_sigs.get(n, ()):
            status = "reprint"
        else:
            status = "missing"
        rows.append({"id": c["id"], "name": c["name"], "set": sid, "supertype": c.get("supertype"),
                     "subtypes": c.get("subtypes", []), "status": status, "signature": cov.signature(c)})
    have = [r for r in rows if r["status"] != "missing"]
    sigs = {r["signature"] for r in rows}
    sigs_have = {r["signature"] for r in have}
    print(f"2005 legal pool: {len(rows)} printings, {len(sigs)} distinct cards (by signature)")
    print(f"in the engine:   {len(have)} printings ({sum(r['status'] == 'exact' for r in rows)} exact, "
          f"{sum(r['status'] == 'reprint' for r in rows)} reprint), {len(sigs_have)} distinct cards; "
          f"{len(rows) - len(have)} printings missing")
    per = collections.defaultdict(collections.Counter)
    for r in rows:
        per[r["set"]][r["status"]] += 1
    for sid in LEGAL_SETS + [PROMOS[0]]:
        t = per[sid]
        print(f"  {sid:5s} {SET_NAMES[sid]:32s} {sum(t.values()):4d} printings: exact {t['exact']:3d}  "
              f"reprint {t['reprint']:3d}  missing {t['missing']:3d}")
    by_type = collections.Counter((r["supertype"], r["status"] != "missing") for r in rows)
    print("  by supertype (have/total): " + ", ".join(
        f"{st} {by_type[(st, True)]}/{by_type[(st, True)] + by_type[(st, False)]}" for st in sorted({r['supertype'] for r in rows})))
    print(f"engine cards printed in a legal set (fullNames, for a 2005 format): {len(engine_legal_fullnames())}")
    if args.json:
        out = {"format": "2004-05 Modified (Worlds 2005)", "sets": LEGAL_SETS, "promos": list(PROMOS),
               "excluded_by_date": TK2_BY_DATE, "printings": len(rows), "distinct_cards": len(sigs),
               "engine_printings": len(have), "engine_distinct_cards": len(sigs_have),
               "engine_legal_fullnames": engine_legal_fullnames(),
               "cards": [{k: v for k, v in r.items() if k != "signature"} for r in rows]}
        Path(args.json).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
