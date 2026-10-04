import sys, re
sys.path.insert(0, r"C:/Users/evanc/Desktop/333/Mon/Pokemon_TCG_RL/v4")
from ptcg_env import build_starmie_deck, build_lucario_deck, PokemonCard, EnergyType, MAX_BENCH

decks = build_starmie_deck() + build_lucario_deck()
V      = len({c.name for c in decks})                                  # union card vocabulary
P      = len({c.name for c in decks if isinstance(c, PokemonCard)})   # distinct Pokemon names
E      = len(EnergyType)
src    = open(r"C:/Users/evanc/Desktop/333/Mon/Pokemon_TCG_RL/v4/ptcg_env.py", encoding="utf-8").read()
T      = len(set(re.findall(r'"type":\s*"([a-z0-9_]+)"', src)))      # distinct pending_choice types
slots  = 2 + 2 * MAX_BENCH

lean_slot = {"identity one-hot": P, "hp fraction": 1, "energy by type": E, "total energy": 1,
             "has tool": 1, "retreat cost": 1, "ability ready": 1}
full_extra = {"status one-hot": 3, "cant attack": 1, "blocked attack flags": 2, "shadow bound": 1,
              "played this turn": 1, "ignition bonus": 1, "legacy energy": 1}
counts  = {"my hand": V, "my discard": V, "my remaining deck": V, "opp discard": V}
scalars = {"opp hand size":1,"my deck size":1,"opp deck size":1,"my KO":1,"opp KO":1,"energy used":1,
           "supporter used":1,"turn":1,"going first":1,"stadium one-hot":2,"black belt":1,
           "premium power":1,"items blocked":1,"had KO last turn":1}
choice  = {"choice type one-hot": T, "remaining picks": 1, "candidates by name": V}

def total(slot_feats):
    per = sum(slot_feats.values())
    return per, slots*per + sum(counts.values()) + sum(scalars.values()) + sum(choice.values())

print(f"V={V} card names, P={P} Pokemon names, E={E} energy types, T={T} pending-choice types, slots={slots}")
for name, sf in (("LEAN", lean_slot), ("FULL", {**lean_slot, **full_extra})):
    per, tot = total(sf)
    print(f"\n{name}: per-slot={per}  board={slots}x{per}={slots*per}  counts={sum(counts.values())}  "
          f"scalars={sum(scalars.values())}  choice={sum(choice.values())}  TOTAL={tot}")
    print("   per-slot:", sf)
print("\ncounts:", counts); print("scalars:", scalars); print("choice:", choice)
print("pending types:", sorted(set(re.findall(r'"type":\s*"([a-z0-9_]+)"', src))))
