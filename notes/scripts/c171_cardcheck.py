"""C171's printed-card check (runs/probe/C171-table-drafting/record.md; rule 9): the table's top names the lists barely run, each print in the pool against notes/data/cards/printed_reference.json. Compares HP, type, weakness,
resistance, retreat, attack names, costs, damage; prints the printed text beside the engine's for a by-eye read of effects. Effects aren't scripted here: the engine's code is read for each attack with text (see the log).
  .venv/Scripts/python notes/scripts/c171_cardcheck.py [names...]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMES = sys.argv[1:] or ["Tauros", "Lickitung", "Seaking", "Weepinbell", "Kangaskhan", "Snorlax"]
pool = json.loads((ROOT / "notes/data/cards/pool.json").read_text(encoding="utf-8"))["cards"]
ref = json.loads((ROOT / "notes/data/cards/printed_reference.json").read_text(encoding="utf-8"))
print("reference keys sample:", list(ref["cards"])[:3], "| type:", type(ref["cards"]).__name__)
print("reference entry sample:", json.dumps(next(iter(ref["cards"].values())))[:500] if isinstance(ref["cards"], dict) else json.dumps(ref["cards"][0])[:500])
print("pool entry attack sample:", json.dumps([c for c in pool if c["name"] == NAMES[0]][0])[:900])
for n in NAMES:
    for c in [x for x in pool if x["name"] == n]:
        print("\n==", c["fullName"], "| HP", c["hp"], "| stage", c["stage"], "| types", c["types"], "| weak", c.get("weakness"), "| resist", c.get("resistance"), "| retreat", c.get("retreat"))
        print("  engine attacks:", json.dumps(c.get("attacks"))[:700])
        print("  engine powers:", json.dumps(c.get("powers"))[:400])
        r = ref["cards"].get(c["fullName"]) if isinstance(ref["cards"], dict) else None
        print("  printed:", json.dumps(r)[:1000] if r else "NOT IN REFERENCE")
print("\nambiguous:", {k: v for k, v in ref.get("ambiguous", {}).items() if any(n in k for n in NAMES)} if isinstance(ref.get("ambiguous"), dict) else [x for x in ref.get("ambiguous", []) if any(n in str(x) for n in NAMES)])
print("missing:", [x for x in ref.get("missing", []) if any(n in str(x) for n in NAMES)])
print("dataset_conflicts:", [x for x in ref.get("dataset_conflicts", []) if any(n in str(x) for n in NAMES)])
