"""C180's deck-out trace: the lists' games on C179's deals (24 lists, 12 opponents, 2 deals, greedy, seed 91), under C49-sd, arm 0 s1 and W s49's last net, through audit/c180_trace_worker.js, log only. Is a list's deck-out overdrawing or a long game? Per pilot: games, game length, the decked player's deck and hand at the end; per card, plays a game, deck size when played, the share played at a thin deck, and whether a pass was legal; in games lost by deck-out: the last draw or search Trainer's deck size, and how many cards went beyond the natural draw of one a turn.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c180_trace_read.py
"""
import collections
import json
from pathlib import Path

import numpy as np

from c139_read import r3

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "runs/probe/C180-dose-by-practice"
BURN = ("Professor Oak", "Bill", "Computer Search", "Energy Search", "Poké Ball", "Pokémon Trader", "Gambler", "Item Finder", "Pokédex", "Mysterious Fossil", "Imposter Oak's Revenge", "Impostor Professor Oak")
THIN = 10
START_DECK = 47                                        # 60 less 7 in hand and 6 Prizes, before mulligans


def read(tag):
    r = json.loads((D / f"trace_{tag}.json").read_text(encoding="utf-8"))
    res = {x["seed"]: x for x in r["results"] if not x.get("error")}
    plays, ends = collections.defaultdict(list), {}
    for line in open(D / f"trace_{tag}.jsonl", encoding="utf-8"):
        if line.strip():
            x = json.loads(line)
            if x[0] == "T":
                x[4] = x[4].rsplit(" ", 1)[0]                 # the key carries the set code: "Professor Oak BS"
                plays[x[1]].append(x[2:])
            else:
                ends[x[1]] = x
    n = len(res)
    turns = np.array([ends[s][2] for s in res if s in ends])
    decked = [s for s, x in res.items() if x.get("ending") == "deck-out" and s in ends]
    by_card = collections.defaultdict(list)
    for s, p in plays.items():
        if s in res:
            for turn, pl, card, deck, hand, opts, has_pass in p:
                by_card[card].append((deck, hand, has_pass))
    cards = {c: {"plays_a_game": r3(len(v) / n), "deck_mean": r3(float(np.mean([q[0] for q in v]))), "deck_median": float(np.median([q[0] for q in v])), "share_at_deck_le_10": r3(float(np.mean([q[0] <= THIN for q in v]))), "hand_mean": r3(float(np.mean([q[1] for q in v]))), "pass_legal": r3(float(np.mean([bool(q[2]) for q in v])))} for c, v in by_card.items() if len(v) >= 10}
    # games lost by deck-out: who ran out, and how
    last_burn, beyond, own_turns, oak_counts, bill_counts, loser_hand, winner_deck, card_in_decked = [], [], [], [], [], [], [], collections.Counter()
    for s in decked:
        e = ends[s]
        sizes = {q[0]: q for q in e[3]}
        lo = min(sizes.values(), key=lambda q: q[1])          # the player out of cards
        hi = max(sizes.values(), key=lambda q: q[1])
        loser_hand.append(lo[2])
        winner_deck.append(hi[1])
        mine = [x for x in plays.get(s, []) if x[1] == lo[0]]
        burn = [x for x in mine if x[2] in BURN]
        last_burn.append(burn[-1][3] if burn else None)
        t = e[2] / 2
        own_turns.append(t)
        beyond.append(START_DECK - t)
        oak_counts.append(sum(x[2] == "Professor Oak" for x in mine))
        bill_counts.append(sum(x[2] == "Bill" for x in mine))
        card_in_decked.update(x[2] for x in mine)
    lb = [x for x in last_burn if x is not None]
    other = [s for s in res if s not in set(decked)]
    out = {"pilot": r["pilot"], "games": n, "errors": r["last"]["errors"], "endings": r["last"]["endings"], "deck_out_share": r3(len(decked) / max(1, n)),
           "turns_at_end": {"mean": r3(float(turns.mean())), "median": float(np.median(turns)), "p90": float(np.percentile(turns, 90))},
           "turns_in_deck_out_games": r3(float(np.mean([ends[s][2] for s in decked]))) if decked else None, "turns_in_other_games": r3(float(np.mean([ends[s][2] for s in other if s in ends]))),
           "oak_plays_a_game": r3(sum(x[2] == "Professor Oak" for s in res for x in plays.get(s, [])) / n), "bill_plays_a_game": r3(sum(x[2] == "Bill" for s in res for x in plays.get(s, [])) / n),
           "pass_legal_at_burn_plays": r3(float(np.mean([bool(q[2]) for c in BURN for q in by_card.get(c, [])]))) if any(by_card.get(c) for c in BURN) else None}
    if decked:
        out["deck_out_games"] = {"count": len(decked), "own_turns_mean": r3(float(np.mean(own_turns))), "cards_beyond_one_a_turn_mean": r3(float(np.mean(beyond))), "loser_hand_at_end_mean": r3(float(np.mean(loser_hand))), "winner_deck_at_end_mean": r3(float(np.mean(winner_deck))),
                                 "last_burn_deck_median": float(np.median(lb)) if lb else None, "last_burn_deck_mean": r3(float(np.mean(lb))) if lb else None, "last_burn_at_deck_le_10": r3(float(np.mean([x <= THIN for x in lb]))) if lb else None, "oak_plays_by_the_loser": r3(float(np.mean(oak_counts))), "bill_plays_by_the_loser": r3(float(np.mean(bill_counts))), "loser_trainers_top": card_in_decked.most_common(8)}
    out["cards"] = dict(sorted(cards.items(), key=lambda kv: -kv[1]["plays_a_game"]))
    return out


def main():
    out = {t: read(t) for t in ("C49", "arm0", "W49") if (D / f"trace_{t}.json").exists()}
    (D / "trace_summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, json.dumps({q: v[q] for q in v if q != "cards"}))
        print("  cards", json.dumps({c: x for c, x in list(v["cards"].items())[:9]}))


if __name__ == "__main__":
    main()
