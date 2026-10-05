#!/usr/bin/env python3
"""Field-by-field check of ryuu-play card classes against PokemonTCG/pokemon-tcg-data.

For every Pokémon class in the chosen ryuu-play set folders, compares HP, type, stage,
evolvesFrom, Weakness, Resistance, retreat cost, attacks (name, cost, damage) and
Pokémon Power names with the card database, and prints the mismatches. Trainer and
Energy cards are only checked for existence in the database.

Examples (Windows: use the `py` launcher):
  py ryuu_card_data_check.py --ryuu C:/path/to/ryuu-play
  py ryuu_card_data_check.py --ryuu C:/path/to/ryuu-play --sets BS:base1,JU:base2,FO:base3,TR:base5,RS:ex1,SS:ex2,RG:ex6

--sets maps ryuu-play set codes (the `set` field of a card class) to pokemon-tcg-data set ids.
A class whose fullName ends in its set code plus a number (e.g. 'Pikachu PR4') is matched to
that card number; otherwise the first printing with that name is used (e.g. 'Mewtwo PR' -> #3).
Card database files are cached under notes/data/cache/tcgdata/ (shared with meta_aggregate.py).
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

TCGDATA_URL = "https://raw.githubusercontent.com/PokemonTCG/pokemon-tcg-data/master/cards/en/{}.json"
DEFAULT_SETS = "BS:base1,JU:base2,FO:base3,TR:base5,PR:basep"
TYPE = {"COLORLESS": "Colorless", "GRASS": "Grass", "FIGHTING": "Fighting", "PSYCHIC": "Psychic", "WATER": "Water",
        "LIGHTNING": "Lightning", "FIRE": "Fire", "DARK": "Darkness", "METAL": "Metal", "DRAGON": "Dragon", "FAIRY": "Fairy"}
STAGE = {"BASIC": "Basic", "STAGE_1": "Stage 1", "STAGE_2": "Stage 2"}
QUOTE_PLACEHOLDER = "\u0001"


def norm(s: str) -> str:
    s = s.replace("\u2019", "'").replace("\u00e9", "e").replace("\u2642", " male").replace("\u2640", " female").replace("!", "")
    return re.sub(r"\s+", " ", s).strip().lower()


def fetch_set(sid: str, cache: Path) -> list[dict]:
    f = cache / (sid + ".json")
    if not f.exists() or f.stat().st_size == 0:
        cache.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(TCGDATA_URL.format(sid), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            f.write_bytes(resp.read())
    return json.loads(f.read_text(encoding="utf-8"))


def types_in(block: str) -> list[str]:
    return [TYPE[t] for t in re.findall(r"CardType[.]([A-Z]+)", block)]


def block(src: str, field: str) -> str | None:
    m = re.search(r"public " + field + r"\s*(?::[^=]+)?=\s*(\[.*?\]);", src, re.S)
    return m.group(1) if m else None


def unq(s: str) -> str:
    return s.replace(QUOTE_PLACEHOLDER, "'")


def check(ryuu: Path, setmap: dict[str, str], cache: Path) -> int:
    data: dict[tuple[str, str], dict] = {}
    by_number: dict[tuple[str, str], dict] = {}
    for code, sid in setmap.items():
        for c in fetch_set(sid, cache):
            data.setdefault((code, norm(c["name"])), c)      # first printing wins (holo/non-holo duplicates)
            by_number[(code, str(c.get("number", "")))] = c
    numbered = 0
    mism, checked, pokemon, files = [], Counter(), 0, 0
    for f in sorted((ryuu / "packages" / "sets" / "src").rglob("*.ts")):
        if f.name == "index.ts" or f.name.endswith(".spec.ts"):
            continue
        src = f.read_text(encoding="utf-8", errors="replace").replace(chr(92) + "'", QUOTE_PLACEHOLDER)
        name = re.search(r"name:\s*string\s*=\s*'([^']*)'", src)
        code = re.search(r"set:\s*string\s*=\s*'([A-Za-z0-9]+)'", src)
        if not name or not code or code.group(1) not in setmap:
            continue
        files += 1
        nm, cd = unq(name.group(1)), code.group(1)
        d = data.get((cd, norm(nm)))
        full = re.search(r"fullName:\s*string\s*=\s*'([^']*)'", src)
        num = re.search(r"\s" + re.escape(cd) + r"(\d+)$", unq(full.group(1))) if full else None
        if num:
            d = by_number.get((cd, num.group(1)))
            if d is not None and norm(d["name"]) != norm(nm):
                mism.append((cd, nm, "name@#" + num.group(1), nm, d["name"]))
            numbered += 1
        if d is None:
            mism.append((cd, nm, "NOT IN DATABASE", "", ""))
            continue
        if "extends PokemonCard" not in src:
            continue
        pokemon += 1

        def add(field, got, exp):
            checked[field] += 1
            if got != exp:
                mism.append((cd, nm, field, got, exp))

        hp = re.search(r"hp:\s*number\s*=\s*(\d+)", src)
        add("hp", int(hp.group(1)) if hp else None, int(d["hp"]))
        ct = block(src, "cardTypes") or block(src, "cardType")
        add("type", types_in(ct) if ct else [], d.get("types", []))
        st = re.search(r"public stage[^=]*=\s*Stage[.](BASIC|STAGE_1|STAGE_2)", src)
        add("stage", STAGE.get(st.group(1)) if st else None,
            next((s for s in ("Basic", "Stage 1", "Stage 2") if s in d.get("subtypes", [])), None))
        ev = re.search(r"evolvesFrom[^=]*=\s*'([^']*)'", src)
        add("evolvesFrom", norm(unq(ev.group(1))) if ev else "", norm(d.get("evolvesFrom", "")))
        wk, rs, rt = block(src, "weakness"), block(src, "resistance"), block(src, "retreat")
        add("weakness", types_in(wk) if wk else [], [w["type"] for w in d.get("weaknesses", [])])
        add("resistance", types_in(rs) if rs else [], [r["type"] for r in d.get("resistances", [])])
        add("retreat", len(types_in(rt)) if rt else 0, len(d.get("retreatCost", [])))
        got = []
        for m in re.finditer(r"\{\s*name:\s*'([^']*)'(.*?)\}", block(src, "attacks") or "[]", re.S):
            body = m.group(2)
            cost = re.search(r"cost:\s*\[(.*?)\]", body, re.S)
            dmg = re.search(r"damage:\s*'([^']*)'", body)
            got.append((norm(unq(m.group(1))), sorted(types_in(cost.group(1))) if cost else [],
                        (dmg.group(1) if dmg else "").replace("\u00d7", "x").lower()))
        exp = [(norm(a["name"]), sorted(a.get("cost", [])), a.get("damage", "").replace("\u00d7", "x").lower())
               for a in d.get("attacks", [])]
        add("attacks", got, exp)
        add("powers", sorted(norm(unq(x)) for x in re.findall(r"name:\s*'([^']*)'", block(src, "powers") or "[]")),
            sorted(norm(a["name"]) for a in d.get("abilities", [])))

    print(f"card files: {files}   Pokémon compared: {pokemon}   field checks: {sum(checked.values())}   mismatches: {len(mism)}")
    print("checks per field:", dict(checked), f"  matched by card number: {numbered}")
    for cd, nm, field, got, exp in mism:
        print(f"  {cd} {nm:24} {field:14} ryuu={got}  data={exp}")
    print("note: a damage string of '' vs '?' is cosmetic (variable-damage attacks); the database itself has occasional typos.")
    return 0


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ryuu", type=Path, required=True, help="path to a ryuu-play checkout")
    ap.add_argument("--sets", default=DEFAULT_SETS, help="ryuu set code -> pokemon-tcg-data set id pairs")
    ap.add_argument("--cache", type=Path, default=Path(__file__).resolve().parent.parent / "data" / "cache" / "tcgdata")
    args = ap.parse_args(argv)
    setmap = dict(pair.split(":") for pair in args.sets.split(",") if ":" in pair)
    return check(args.ryuu, setmap, args.cache)


if __name__ == "__main__":
    sys.exit(main())
