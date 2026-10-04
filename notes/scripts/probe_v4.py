"""Probe the v4 env: how often do the encoding caps bite, and how much
identity information is hidden from the agent by the positional encoding?"""
import sys, time
from collections import Counter, defaultdict
import numpy as np
sys.path.insert(0, r"C:/Users/evanc/Desktop/333/Mon/Pokemon_TCG_RL/v4")
from ptcg_env import (PokemonTCGEnv, StateEncoder, ActionMapper, ActionType,
                      PokemonCard, TrainerCard, EnergyCard, CardType, Stage,
                      EnergyType, MAX_HAND, compute_legal_mask, HeuristicAgent)

def full_option_count(me, t):
    if t in ("ultra_ball_discard1", "ultra_ball_discard2"):
        return len(me.hand), [type(c).__name__ + ":" + getattr(c, "name", "?") for c in me.hand]
    if t == "ultra_ball_pick":
        cs = [c for c in me.deck if isinstance(c, PokemonCard)]
    elif t == "poke_pad_pick":
        cs = [c for c in me.deck if isinstance(c, PokemonCard) and not c.is_ex]
    elif t in ("poffin_pick1", "poffin_pick2"):
        cs = [c for c in me.deck if isinstance(c, PokemonCard) and c.stage == Stage.BASIC and c.hp <= 70]
    elif t == "night_stretcher_pick":
        cs = [c for c in me.discard if isinstance(c, PokemonCard) or (isinstance(c, EnergyCard) and c.special_effect is None)]
    elif t == "hilda_evo_pick":
        cs = [c for c in me.deck if isinstance(c, PokemonCard) and c.stage != Stage.BASIC]
    elif t == "hilda_energy_pick":
        cs = [c for c in me.deck if isinstance(c, EnergyCard)]
    elif t == "fighting_gong_pick":
        cs = [c for c in me.deck if (isinstance(c, EnergyCard) and c.energy_type == EnergyType.FIGHTING and c.special_effect is None)
              or (isinstance(c, PokemonCard) and c.stage == Stage.BASIC and c.pokemon_type == EnergyType.FIGHTING)]
    elif t == "petrel_pick":
        cs = [c for c in me.deck if isinstance(c, TrainerCard)]
    elif t == "last_ditch_catch_pick":
        cs = [c for c in me.deck if isinstance(c, TrainerCard) and c.card_type == CardType.SUPPORTER]
    elif t == "pokegear_pick":
        cs = [c for c in me.deck[:7] if isinstance(c, TrainerCard) and c.card_type == CardType.SUPPORTER]
    else:
        return None, None
    return len(cs), [c.name for c in cs]

def run(policy_name, n_games, seed0):
    env = PokemonTCGEnv(seed=seed0)
    rng = np.random.default_rng(seed0)
    heur = HeuristicAgent() if policy_name == "heuristic" else None
    st = Counter(); maxes = defaultdict(int)
    t_step = 0.0; t_mask = 0.0; t_enc = 0.0
    for g in range(n_games):
        env.reset(seed=seed0 + g)
        steps = 0
        while not env.gs.game_over and steps < 4000:
            gs = env.gs; me = gs.current()
            st["decisions"] += 1
            h = len(me.hand)
            maxes["max_hand"] = max(maxes["max_hand"], h)
            if h > MAX_HAND:
                st["hand_over_cap"] += 1
                # cards that are unplayable purely because of their hand index
                st["cards_beyond_cap"] += h - MAX_HAND
            pc = me.pending_choice
            if pc is not None:
                t = pc["type"]; st["choice:" + t] += 1
                full, names = full_option_count(me, t)
                if full is not None:
                    if full > ActionMapper.CHOOSE_COUNT:
                        st["truncated:" + t] += 1
                        st["truncated_total"] += 1
                    # option slots spent on duplicate identities
                    shown = names[:ActionMapper.CHOOSE_COUNT]
                    st["opt_slots_shown"] += len(shown)
                    st["opt_distinct_shown"] += len(set(shown))
                    # identities unreachable because of truncation
                    lost = set(names) - set(shown)
                    if lost:
                        st["identities_lost_by_truncation"] += 1
            else:
                # Blind-hand decisions: legal actions of the same verb that point at
                # different card identities (indistinguishable in the 234-vector)
                t0 = time.perf_counter(); mask = compute_legal_mask(gs); t_mask += time.perf_counter() - t0
                legal = np.flatnonzero(mask)
                by_verb = defaultdict(set)
                for a in legal:
                    at, p = ActionMapper.decode(int(a))
                    if at in (ActionType.PLAY_POKEMON, ActionType.USE_ITEM, ActionType.USE_SUPPORTER,
                              ActionType.EVOLVE, ActionType.ATTACH_TOOL, ActionType.USE_STADIUM):
                        hi = p["hand_idx"]
                        if hi < len(me.hand):
                            c = me.hand[hi]
                            if not isinstance(c, EnergyCard):
                                by_verb[at.name].add(c.name)
                for verb, ids in by_verb.items():
                    if len(ids) >= 2:
                        st["blind_choice:" + verb] += 1
                        st["blind_choice_any"] += 1
            t0 = time.perf_counter(); StateEncoder.encode(gs); t_enc += time.perf_counter() - t0
            if heur is not None:
                a = heur.act(env)
            else:
                legal = env.get_legal_actions()
                a = int(rng.choice(legal))
            t0 = time.perf_counter(); env.step(a); t_step += time.perf_counter() - t0
            steps += 1
        st["games"] += 1
        st["turns"] += env.gs.turn_number
        st["win_reason:" + (env.gs.win_reason or "none")] += 1
        if not env.gs.game_over: st["unfinished"] += 1
    d = st["decisions"]
    print(f"\n=== policy={policy_name} games={n_games} ===")
    print(f"decisions={d}  avg turns/game={st['turns']/max(1,st['games']):.1f}  avg decisions/game={d/max(1,st['games']):.0f}")
    print(f"timing per decision: step={1e6*t_step/d:.0f}us  legal_mask={1e6*t_mask/d:.0f}us  encode={1e6*t_enc/d:.0f}us")
    print(f"max hand size seen={maxes['max_hand']}  decisions with hand>{MAX_HAND}: {st['hand_over_cap']} ({100*st['hand_over_cap']/d:.1f}%)  unplayable card-slots total={st['cards_beyond_cap']}")
    print(f"blind-hand decisions (>=2 legal same-verb actions on different card identities): {st['blind_choice_any']} ({100*st['blind_choice_any']/d:.1f}% of decisions)")
    for k in sorted(k for k in st if k.startswith("blind_choice:")): print(f"   {k}: {st[k]}")
    print(f"pending-choice decisions: {sum(v for k,v in st.items() if k.startswith('choice:'))}; truncated (>12 options): {st['truncated_total']}; identities unreachable: {st['identities_lost_by_truncation']}")
    for k in sorted(k for k in st if k.startswith("choice:")):
        t = k.split(":",1)[1]; print(f"   {t:24s} n={st[k]:6d}  truncated={st['truncated:'+t]}")
    if st["opt_slots_shown"]:
        print(f"option slots shown={st['opt_slots_shown']}  distinct identities among them={st['opt_distinct_shown']}  -> {100*(1-st['opt_distinct_shown']/st['opt_slots_shown']):.0f}% of slots are duplicates")
    for k in sorted(k for k in st if k.startswith("win_reason:")): print(f"   {k}: {st[k]}")
    if st["unfinished"]: print(f"unfinished (hit step cap): {st['unfinished']}")

if __name__ == "__main__":
    run("random", 200, 1000)
    run("heuristic", 200, 5000)
