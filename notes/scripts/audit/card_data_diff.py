"""Engine audit step 3 (log #484): the engine's card data (notes/data/cards/pool.json, generated from the engine's card
definitions) against research's printed reference (notes/data/cards/printed_reference.json, pokemon-tcg-data). Per card:
HP, types, Weakness and Resistance (type and value), retreat count, stage and evolves-from, attack names, costs (by type),
damage strings, and Power names. Pokémon and Energy first; lists' cards ranked by impact. Evaluation only, CPU.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/audit/card_data_diff.py
"""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TYPES = ["Colorless", "Grass", "Fighting", "Psychic", "Water", "Lightning", "Metal", "Darkness", "Fire", "Dragon", "Fairy"]


def vec_types(v):
    return sorted(TYPES[i] for i, x in enumerate(v or []) if x)


def main():
    pool = {c["fullName"]: c for c in json.loads((ROOT / "notes/data/cards/pool.json").read_text(encoding="utf-8"))["cards"]}
    ref = json.loads((ROOT / "notes/data/cards/printed_reference.json").read_text(encoding="utf-8"))["cards"]
    inv = json.loads((ROOT / "runs/probe/AUDIT-engine/inventory.json").read_text(encoding="utf-8"))
    impact = {r["fullName"]: r["impact"] for r in inv["in_lists"]}
    faults = []
    for name, c in pool.items():
        if c["superType"] != 1 or name not in ref:
            continue
        r = ref[name]
        d = []
        if c.get("hp") != int(r.get("hp") or 0):
            d.append(("hp", c.get("hp"), r.get("hp")))
        if vec_types(c.get("types")) != sorted(r.get("types") or []):
            d.append(("types", vec_types(c.get("types")), r.get("types")))
        ew, rw = vec_types(c.get("weakness")), sorted(w["type"] for w in r.get("weaknesses") or [])
        if ew != rw:
            d.append(("weakness", ew, rw))
        er, rr = vec_types(c.get("resistance")), sorted(x["type"] for x in r.get("resistances") or [])
        if er != rr:
            d.append(("resistance", er, rr))
        rv = {x.get("value") for x in r.get("resistances") or []}
        if rr and rv - {"-30"}:
            d.append(("resistance_value", "-30 (engine default)", sorted(rv)))
        if c.get("retreat") != int(r.get("convertedRetreatCost") or 0):
            d.append(("retreat", c.get("retreat"), r.get("convertedRetreatCost")))
        if (c.get("evolvesFrom") or "") != (r.get("evolvesFrom") or ""):
            d.append(("evolvesFrom", c.get("evolvesFrom"), r.get("evolvesFrom")))
        ea = [(a["name"], tuple(sorted(TYPES[i] for i, n in enumerate(a.get("cost") or []) for _ in range(n))), str(a.get("damageText") or a.get("damage") or ""))
              for a in c.get("attacks", [])]
        ra = [(a["name"], tuple(sorted(a.get("cost") or [])), str(a.get("damage") or "").replace("×", "x")) for a in r.get("attacks") or []]
        ea = [(n, cost, dm.replace("×", "x")) for n, cost, dm in ea]
        if [a[0] for a in ea] != [a[0] for a in ra]:
            d.append(("attack_names", [a[0] for a in ea], [a[0] for a in ra]))
        for x, y in zip(ea, ra):
            if x[1] != y[1]:
                d.append((f"cost:{x[0]}", x[1], y[1]))
            if x[2] != y[2] and not (x[2] in ("0", "") and y[2] == ""):
                d.append((f"damage:{x[0]}", x[2], y[2]))
        ep = [p["name"] for p in c.get("powers", [])]
        rp = [a["name"] for a in r.get("abilities") or []]
        if ep != rp:
            d.append(("powers", ep, rp))
        if d:
            faults.append({"fullName": name, "impact": impact.get(name, 0), "in_lists": name in impact, "diffs": d})
    faults.sort(key=lambda f: (-f["impact"], f["fullName"]))
    out = ROOT / "runs/probe/AUDIT-engine/card_data_diff.json"
    out.write_text(json.dumps(faults, indent=1, default=list), encoding="utf-8")
    kinds = collections.Counter(k[0].split(":")[0] for f in faults for k in f["diffs"])
    print(f"Pokémon checked: {sum(1 for c in pool.values() if c['superType'] == 1 and c['fullName'] in ref)}; with any diff: {len(faults)}; "
          f"in the lists: {sum(f['in_lists'] for f in faults)}; diff kinds: {dict(kinds)}")
    for f in faults[:40]:
        print(f["impact"], f["fullName"], f["diffs"])


if __name__ == "__main__":
    main()
