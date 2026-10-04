import sys
from collections import Counter
sys.path.insert(0, r"C:/Users/evanc/Desktop/333/Mon/Pokemon_TCG_RL/v4")
from ptcg_env import (build_starmie_deck, build_lucario_deck, PokemonCard, TrainerCard,
                      EnergyCard, CardType, Stage, EnergyType)

def kind(c):
    if isinstance(c, PokemonCard): return "pokemon"
    if isinstance(c, EnergyCard): return "energy"
    return c.card_type.name.lower()

allnames = set()
for label, deck in (("Starmie", build_starmie_deck()), ("Lucario", build_lucario_deck())):
    names = Counter(c.name for c in deck)
    bykind = Counter()
    for n in names:
        c = next(x for x in deck if x.name == n)
        bykind[kind(c)] += 1
    allnames |= set(names)
    print(f"{label}: {len(deck)} cards, {len(names)} distinct names -> {dict(bykind)}")
    # max distinct candidates a search effect could ever offer (deck untouched)
    poke = {c.name for c in deck if isinstance(c, PokemonCard)}
    nonex = {c.name for c in deck if isinstance(c, PokemonCard) and not c.is_ex}
    evo = {c.name for c in deck if isinstance(c, PokemonCard) and c.stage != Stage.BASIC}
    basic = {c.name for c in deck if isinstance(c, PokemonCard) and c.stage == Stage.BASIC}
    trainers = {c.name for c in deck if isinstance(c, TrainerCard)}
    supp = {c.name for c in deck if isinstance(c, TrainerCard) and c.card_type == CardType.SUPPORTER}
    energy = {c.name for c in deck if isinstance(c, EnergyCard)}
    print(f"   distinct search candidates: any Pokemon(UltraBall)={len(poke)}  non-ex(PokePad)={len(nonex)}  "
          f"evo(Hilda)={len(evo)}  basic={len(basic)}  trainer(Petrel)={len(trainers)}  supporter(Meowth/Pokegear)={len(supp)}  energy={len(energy)}")
    # identity-indexed flat action space for this deck (verb x card-name x target slot)
    n_energy, n_basic, n_evo = len(energy), len(basic), len(evo)
    n_item = sum(1 for n in trainers if next(x for x in deck if x.name == n).card_type == CardType.ITEM)
    n_supp = len(supp)
    n_tool = sum(1 for n in trainers if next(x for x in deck if x.name == n).card_type == CardType.TOOL)
    n_stad = sum(1 for n in trainers if next(x for x in deck if x.name == n).card_type == CardType.STADIUM)
    slots = 6
    total = (1 + n_energy*slots + n_basic + n_item + n_supp + n_evo*slots + 2 + 5 + 5 + n_tool*slots + 6 + n_stad
             + len(names))   # CHOOSE over the deck's vocabulary (covers every search/discard choice)
    print(f"   identity-indexed flat action space ≈ {total}  (energy {n_energy}x{slots}, basics {n_basic}, items {n_item}, "
          f"supporters {n_supp}, evolutions {n_evo}x{slots}, tools {n_tool}x{slots}, stadiums {n_stad}, choose-by-name {len(names)})")
print(f"union vocabulary across both decks: {len(allnames)} distinct card names")
