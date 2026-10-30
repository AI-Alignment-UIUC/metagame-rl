"""Build an outside printed-card table for every card in pool.json, from the PokemonTCG/pokemon-tcg-data dataset.

Usage: py -I build.py <download_dir> <pool.json> <out.json> <commit>
The dataset is untrusted input: it is only parsed as JSON, never executed.
"""
import json
import re
import sys
import unicodedata

SETS = {"BS": "base1", "JU": "base2", "FO": "base3", "TR": "base5", "PR": "basep"}


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = s.replace("♀", "f").replace("♂", "m")
    return re.sub(r"[^a-z0-9]", "", s)


def norm_name(s):
    # Nidoran's gender signs survive NFKD as nothing, so map them before stripping
    s = s.replace("♀", " female").replace("♂", " male")
    return norm(s)


def sig(c):
    k = keep(c)
    for f in ("id", "number", "rarity"):
        k.pop(f)
    return json.dumps(k, sort_keys=True)


def keep(c):
    out = {
        "id": c["id"], "name": c["name"], "supertype": c.get("supertype"), "subtypes": c.get("subtypes", []),
        "hp": int(c["hp"]) if c.get("hp", "").isdigit() else c.get("hp"), "types": c.get("types", []),
        "evolvesFrom": c.get("evolvesFrom", ""), "weaknesses": c.get("weaknesses", []),
        "resistances": c.get("resistances", []), "retreatCost": c.get("retreatCost", []),
        "convertedRetreatCost": c.get("convertedRetreatCost", 0),
        "abilities": c.get("abilities", []), "rules": c.get("rules", []),
        "attacks": [{k: a.get(k) for k in ("name", "cost", "convertedEnergyCost", "damage", "text")}
                    for a in c.get("attacks", [])],
        "number": c.get("number"), "rarity": c.get("rarity"),
    }
    return out


def main(dl, pool_path, out_path, commit):
    pool = json.load(open(pool_path, encoding="utf-8"))["cards"]
    data = {code: json.load(open(f"{dl}/{sid}.json", encoding="utf-8")) for code, sid in SETS.items()}
    table, ambiguous, missing, dataset_conflicts = {}, {}, [], {}
    for p in pool:
        cards = data.get(p["set"], [])
        hits = [c for c in cards if norm_name(c["name"]) == norm_name(p["name"])]
        if not hits:
            missing.append(p["fullName"])
            continue
        alts = []
        if len(hits) > 1:
            sigs = {sig(c) for c in hits}
            if len(sigs) > 1:
                # different gameplay text: identity tie-break by pool.json's HP and attack names, else listed as ambiguous
                pa = sorted(a["name"] for a in p.get("attacks", []))
                pick = [c for c in hits if str(c.get("hp", "")) == str(p.get("hp", ""))
                        and sorted(a["name"] for a in c.get("attacks", [])) == pa]
                if not pick:
                    ambiguous[p["fullName"]] = [keep(c) for c in hits]
                    continue
                conflict = sorted({f for c in pick[1:] for f, v in keep(c).items()
                                   if f not in ("id", "number", "rarity") and v != keep(pick[0])[f]})
                hits = pick + [c for c in hits if c not in pick]
                if conflict:
                    # same name, HP and attack names, but the dataset's prints disagree: check these fields on a scan
                    dataset_conflicts[p["fullName"]] = {"fields": conflict, "prints": [keep(c) for c in pick]}
            alts = [c["id"] for c in hits[1:]]
        row = keep(hits[0])
        row["alternate_prints"] = alts
        table[p["fullName"]] = row
    meta = {
        "source": "https://github.com/PokemonTCG/pokemon-tcg-data (the dataset behind api.pokemontcg.io), cards/en/"
                  + ",".join(SETS.values()) + ".json",
        "commit": commit,
        "set_map": SETS,
        "note": "Outside reference for the engine audit; pool.json is generated from the engine, so it is not one. "
                "Matched by set code and normalised name. Where one name has several prints in a set, pool.json's HP "
                "picks the print (identity only); unresolved ones are in 'ambiguous'. Errata are not applied.",
        "counts": {"pool": len(pool), "matched": len(table), "ambiguous": len(ambiguous), "missing": len(missing),
                   "dataset_conflicts": len(dataset_conflicts)},
    }
    json.dump({"_meta": meta, "cards": table, "ambiguous": ambiguous, "missing": missing,
               "dataset_conflicts": dataset_conflicts},
              open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(meta["counts"]), "missing:", missing, "ambiguous:", list(ambiguous),
          "conflicts:", {k: v["fields"] for k, v in dataset_conflicts.items()})


if __name__ == "__main__":
    main(*sys.argv[1:5])
