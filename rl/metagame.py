"""The metagame (logs #65-67): a population of decks, one pilot, one draft head.

Every iteration:
  1. the draft head reads every deck of the population through the pilot, against --field-sample other
     decks of the population (rl/draft.py)
  2. --games games between decks drawn at random from the population, seats at random; for every game
     each side draws a fresh deck from its population deck (--swaps cards replaced, chosen by the head)
  3. the pilot learns by PPO from --record of those games (both seats), with potential-based prize shaping
     that fades from --shaping to 0 over --shaping-iters (rl/train.py shape_rewards)
  4. the draft head takes one REINFORCE step on every draw's result (win 1, draw 0.5, loss 0) plus
     --draft-margin times the prize margin at the end ((opponent's prizes left - own) / 6), with a
     leave-one-out baseline over each deck's games; the margin tells draws apart in a matchup that is
     always lost (log #66)
  5. every population deck moves to one more draw
  6. every --turnover-every iterations the --turnover share of decks with the worst results over that
     period is replaced: by a fresh random deck (the format's rules only; with --turnover-wide a wide deck, log #127),
     or 1 in 4 by a deck of the best quarter with 10 cards replaced at random (log #67); with --protect K decks younger
     than K iterations are spared, so a new deck is drafted for a while before it is judged (log #127)
--season K > 1 (log #93): a deck's draws are practised before they count. At the start of a season every deck draws
--candidates draws, and every game of the season plays one of them, chosen at random; the pilot trains on all of them
by PPO, but only the season's last iteration feeds the draft head (step 4), whose leave-one-out baseline then compares
a deck's candidates after the same practice; at its end every deck moves to one of its candidates, chosen at random
(step 5). A deck that turnover brings in mid-season draws its candidates at once. --season 1 is the loop above.
--select (log #127): the deck itself is one of its candidates, played unchanged beside its --candidates draws (every
iteration with --season 1, else through the season), and at the move (step 5) the deck moves to whichever of them scored
best in its games, itself on a tie, instead of to a random draw. Without it a deck moves every iteration to a draw of
--swaps forced changes whatever their results, and once the head's incoming choice collapses onto one card every draw
adds that card until the copy limit stops it, so basic Energy, which has none, piles up (#127).
--select-z Z (log #138): a deck moves to its best candidate only if that candidate's mean beats the deck's own by more
than Z standard errors of the difference (binomial, its rate held within 0.15-0.85), else it stays. With 3 candidates at
about 10 games each, a simulation where every candidate is as good as the deck moved 73% of the decks an iteration, so
the decks followed the head's proposals rather than their results; 1 candidate at Z 1.0 moves about 15% under that null
and still takes a real +0.2 about 60% of the time. The select log row then gives the mean change in Pokémon, Trainers
and Energy over the moves taken ("acc") and over every candidate drawn ("prop"): what the games accept against what
the head proposes. A fork may start from a population snapshot (population_it*.pt), which carries no optimizer or random
state: Adam starts fresh, and --reseed is required.
--max-turns T (log #140): every game (population, practice) unfinished when game turn T + 1 begins, both players' turns
counted, ends there as a draw (env/game.js; ending 'time'): no win for either side, 0.5 to each deck. Without it a
game ends only by Prizes, no Pokémon in play or deck-out, so a deck that survives long enough wins by the opponent's
deck running out (the walls of #137-139, whose deck-out wins took a median of 61 turns). Evan (2026-10-21): "some turn
limit for draw", tried at a variety of limits up to a large one.
--lam-value L (log #145): the value head's targets use GAE lambda L (1: Monte Carlo returns, as DouZero's do), the
policy's advantages keep --lam. lambda 1 for the advantages carried a whole game's luck into every decision (#76-77);
for the value targets alone it is unbiased over long games, the literature review's third step (#144).
--draft-heads K > 1 (log #120): a league of K draft heads sharing the one pilot. Every deck belongs to one head, which
reads it, draws for it and learns from its games (steps 1, 2, 4, 5); all decks still play one another at random, and
turnover replaces each head's worst decks within its own share, with mutants from its own best quarter (step 6). A
source with fewer heads keeps its own as the first ones; the others start uniform (--draft-heads-init fresh) or as
copies of its first head (copy), and the decks are dealt to the heads round-robin. With --draft-exploit (log #123) the
heads after the first are exploiters, as in AlphaStar's league: still paired at random, but their REINFORCE step and their
decks' results (turnover, best decks) count only their games against the first head's decks.
Nothing human enters training: the archived lists and SimpleBot are for evaluation only
(rl/evaluate_agents.py). The one exception is a diagnosis, never a lab card or the main line: --fixed-decks (log #127)
puts fixed lists, such as the archived ones, on one side of a --fixed-share of the games, never drafted or turned over,
so a fork's pilot practises them and one can ask whether they would win once played well.
--practice-games N (log #127): N more games an iteration between two fresh random decks of a playable structure and no
strategy (rl/decks.py wide_deck, the kind pilot-v2 learned on), all recorded for PPO and outside the population and the
draft head, so the pilot keeps playing every kind of deck: a pilot trained only on its population's one deck type
played other types so badly that no other type could win a place (#127).
--practice-vs s (log #141): in a share s of the practice games the second deck is one of the population's best quarter
(by its results this window), played by the same pilot under model slot 3, whose decisions PPO drops: the pilot
practises beating the incumbent type with decks of every structure, and only from the challenger's side. Wide-against-wide
practice never shows it the walls (#137-139), against which its play of other decks draws itself out or loses the
prize race, so no other type can win a place; AlphaStar's exploiters train against the main agent in the same way.
The log's practice row gives these games' count and the challengers' score. The challenger is a wide deck, or with
--practice-vs-from pop a population deck from outside the best quarter (wide challengers won 0 of 20 against the best
walls at 479, too rare a win for PPO to learn from).
--judge-explore e (log #128): the games not recorded for PPO are played at the pilot's top option, sampling only a share
e of decisions (0: greedy), and only they judge decks (step 4, --select, turnover, the best decks). Sampled play, which PPO
needs, erases most of what a Trainer is worth in the moves after it (log #79-80), so decks judged by it under-rate Trainers.
--judge-pilot P (log #132): a second pilot, frozen (a checkpoint such as pilot-v2, which learned on wide random decks and
never on the population), plays both seats of a --judge-share of the games not recorded for PPO, and those results judge
decks like the rest (the draft head's reward, --select, turnover, the best decks). The population's own pilot rates the
decks drafted for it highly and pilot-v2 rates them far below the human lists (log #131-132): a deck has to win under
both to rise, not only under the pilot that has learned its one type.
--judge-search S (log #148, the literature review's first step, #144): S of the games not recorded for PPO (nor
played by --judge-pilot) are played with one-turn policy-guided search on both seats (env/agents.js PolicySearchAgent:
--judge-search-k of the pilot's most likely moves, each in --judge-search-dets copies with the hidden cards re-dealt,
played on greedily to the end of the turn, at most --judge-search-steps decisions, and scored by the pilot's value),
served by the learner like every other decision (rl/remote.py's top-k reply, env/remote_worker.js RemotePilot). They
count apart (ssum / sn beside sum / n), and a deck's or a candidate's score for --select, turnover and the best quarter is
judged below: with --judge-score min its greedy mean, lowered where its searched mean, shrunk toward the greedy one by
--judge-search-prior games, sits more than --judge-search-z standard errors below it (a deck must hold up under both
judges, as in Mahlmann et al.'s judges of several skills; a plain min of the two lowered on noise alone, and only the
decks that drew searched games), with search the shrunk searched mean alone; --select-z takes each score's own games.
The greedy mean is the greedy games' only with --judge-explore, which --judge-search requires. A checkpoint keeps each
deck's judged score ('judged') for the tools that rank its best decks (recent_score). Every population pilot rates the
walls 0.68-0.75 against the human lists; under search on both sides they win the prize race far less often and score
0.57, and 0.44-0.46 with a 50-60 turn draw limit (#139, #146-147), so the searched games are meant to run with
--max-turns. The draft head's reward takes the searched games like any judged game. The log's judge_search row gives the
searched games, the workers' search counts and how many --select choices and turnover places the searched games changed,
beside the mean number changed when the searched results are redrawn at each deck's greedy rate (null_searched: what
noise alone changes).
--anchor P (log #135): on the decisions of the practice games (--practice-games, played under model slot 2, the same
pilot, so the rollouts mark them), PPO also lowers --anchor-w times KL(P || pilot), toward a frozen pilot such as pilot-v2,
which learned on wide random decks only. Every pilot grown in the population plays the human lists 27-45 Elo worse than
pilot-v2, its starting point (#134): it forgets how to play other deck types while it specialises in its own.
--type-cap C (log #129): no deck type keeps more than a share C of the population. At a turnover the decks are grouped
into types as rl/lab.py counts them (best first, each joining the first type whose founding deck shares at least half its
Pokémon, rl/decks.py pokemon_overlap); if the largest holds more than C, its worst decks are replaced first (still
--turnover of the population a time, the young spared), and the mutants come from the other types' best quarter. A
population of one type trains a pilot that plays every other type badly, so no other type can win a place (#127); the cap
keeps the rest of the population for other types, which the pilot then plays and the draft head drafts. Fitness sharing
(a result over its type's size) was tried first on paper: every fresh deck is a type of one, so sharing would have
replaced the main type's decks until fresh decks that never win held most of the places.

Run: .venv/Scripts/python -m rl.metagame --run runs/meta-99 --decks 99 --init-from runs/pilot-v2/model_it00349.pt

The lab (rl/lab.py, notes/plan-lab.md) runs this loop as its main line and its branches: --fork-from continues another
run's whole state (pilot, optimizer, draft head, population, random state) in a new run, --pilot-opts grows the pilot
by new modules that start as the identity or at zero (rl/train.py load_grown), --reseed draws the fork's pairings and
deals afresh (the A/A test), --freeze-pilot skips PPO (meta-only screens), --stop-file ends the run cleanly after
an iteration.
"""
import argparse
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from rl import limits
from rl.decks import Pool, deck_shape, pokemon_overlap, random_deck, wide_deck
from rl.draft import Drafter, random_changes, rloo
from rl.remote import RemotePool
from rl.rollouts import concat, read_rollout, subset
from rl.train import (advantages, aux_targets, load_grown, model_inputs, ppo_update, probe_targets, remap_adam,
                      round_score, round_turns, shape_rewards, token_net)

ROOT = Path(__file__).resolve().parent.parent
PILOT = {"d": 256, "layers": 4, "heads": 8, "count_features": True, "cross_layers": 1, "cand_self": 0}   # pilot-v2's shape
PPO = {"model": "tokens", "amp": True, "epochs": 3, "minibatch": 4096, "micro_batch": 1024, "clip": 0.2, "vf": 0.5,
       "ent": 0.01, "max_grad_norm": 0.5, "gpu_load": 0.7}                                            # tourn-3's settings
MUTANT_SHARE, MUTANT_CHANGES = 0.25, 10
NULL_REPS = 20                                  # --judge-search's noise baseline: redraws a choice (log #148)


def assign_heads(pop: list, K: int, keep: bool):
    """Each deck's draft head: kept when the source had K heads (keep), else dealt round-robin by position."""
    if not keep or any(a.get("head", K) >= K for a in pop):
        for d, a in enumerate(pop):
            a["head"] = d % K


def judged(x: dict, mode: str = "min", prior: float = 4.0, z: float = 1.5):
    """A deck's or candidate's score (--judge-search, log #148) and the games behind it, from its greedy results
    (sum / n) and its searched ones (ssum / sn). The searched mean is shrunk toward the greedy one by `prior` games; with
    mode 'search' the score is that shrunk mean, with 'min' the greedy mean, lowered only where the shrunk mean plus z
    of its standard errors (its difference from the greedy mean's) is lower still, and then to that. A plain min of the
    two lowered a score by ~0.05 on noise alone (search exactly as strong as greedy), and only the scores that drew
    searched games, so --select and turnover moved on noise (the #148 review); at z 1.5 noise costs ~0.004. The games
    are n for the greedy mean and pq / variance for the shrunk one (--select-z's error). Without searched games it is
    (sum / n, n), exactly the score without --judge-search; with searched games only, their mean and count; with none,
    None. z 0 is the plain min."""
    n, sn = x.get("n", 0), x.get("sn", 0)
    if not n and not sn:
        return None
    if not n:
        return x["ssum"] / sn, sn
    g = x["sum"] / n
    if not sn:
        return g, n
    s = (x["ssum"] + prior * g) / (sn + prior)
    ns = (sn + prior) ** 2 / (sn + prior ** 2 / n)           # pq over the shrunk mean's variance
    if mode != "min":
        return s, ns
    p = min(0.85, max(0.15, (x["sum"] + x["ssum"]) / (n + sn)))   # the binomial error as --select-z takes it
    u = s + z * sn / (sn + prior) * (p * (1 - p) * (1 / sn + 1 / n)) ** 0.5
    return (g, n) if g <= u else (u, ns)


def judged_mean(x: dict, mode: str = "min", prior: float = 4.0, default=None, z: float = 1.5):
    """judged's score (--judge-search, log #148), or `default` for a deck or candidate with no games."""
    j = judged(x, mode, prior, z)
    return default if j is None else j[0]


def null_searched(x: dict, rng) -> dict:
    """x with its searched results redrawn as if search were exactly as strong as greedy: ssum ~ Binomial(sn, sum / n)
    (--judge-search's noise baseline, log #148). Draws and cut games make real results less noisy than this, so the
    baseline errs high."""
    if not x.get("sn") or not x.get("n"):
        return x
    return {**x, "ssum": float(rng.binomial(x["sn"], min(1.0, max(0.0, x["sum"] / x["n"]))))}


def recent_score(a: dict, default: float = 0.0) -> float:
    """A checkpoint's population deck by its recent results, as rl/evaluate_agents.py, rl/lab.py deck_types and the
    probe scripts rank its best decks: with --judge-search the judged score the run last held (a['judged'], log #148;
    None in a fresh window), else its mean this window, else the last window's."""
    if a.get("judged") is not None:
        return a["judged"]
    return a["sum"] / a["n"] if a.get("n") else a.get("last", default)


def judge_search_row(games: list, replies: list, select: dict, turn_flips) -> dict:
    """The log's judge_search row (log #148): the searched games (count, errors, endings, mean turns and decisions), the
    workers' searches (decisions searched, the share the search moved off the pilot's top option, lines, lines ended by
    an engine error or cut at the step limit, the slowest worker's seconds in its searched Runner), and how many --select
    choices (select_flips) and, at a turnover, places in the bottom --turnover share and the best quarter the searched
    games changed against the greedy games alone, each beside the mean number changed by searched results redrawn at the
    greedy rate (_null: noise alone), with the mean judged-minus-greedy score of the decks searched."""
    sg = [r for r in games if r.get("search")]
    st = [r["searchStats"] for r in replies if r.get("searchStats")]
    tot = {q: sum(s[q] for s in st) for q in ("searches", "changed", "lines", "lineErrors", "capped")}
    return {"games": len(sg), "errors": sum(1 for r in sg if r.get("error")),
            "endings": {e: sum(1 for r in sg if (r.get("ending") or "none") == e) for e in {r.get("ending") or "none" for r in sg}},
            "turns": round(float(np.mean([r["turns"] for r in sg])), 1) if sg else None,
            "steps_per_game": round(float(np.mean([r["steps"] for r in sg])), 1) if sg else None,
            "searches": tot["searches"], "changed": round(tot["changed"] / max(tot["searches"], 1), 4),
            "lines": tot["lines"], "line_errors": tot["lineErrors"], "capped": tot["capped"],
            "seconds": round(max((s["seconds"] for s in st), default=0.0), 1),
            **({"select_flips": select["flips"], "select_flips_null": select["flips_null"],
                "searched_per_candidate": select["searched_per_candidate"]} if "flips" in select else {}),
            **({"turnover": turn_flips} if turn_flips else {})}


def deck_kinds(pool: Pool, decks: list, score: np.ndarray, link: float = 0.5):
    """Each deck's type and every type's size (--type-cap, log #129), as rl/lab.py deck_types counts them: best first, a
    deck joins the first type whose founding deck shares at least `link` of its Pokémon with it (rl/decks.py
    pokemon_overlap), else it founds one. The 24 human lists make types of 9, 7 and 4 and four of one."""
    founders, sizes, kind_of = [], [], np.zeros(len(decks), dtype=np.int64)
    for i in np.argsort(-score, kind="stable"):
        k = next((t for t, f in enumerate(founders) if pokemon_overlap(pool, f, decks[i]) >= link), None)
        if k is None:
            founders.append(decks[i])
            sizes.append(0)
            k = len(founders) - 1
        sizes[k] += 1
        kind_of[i] = k
    return kind_of, sizes


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--decks", type=int, default=99, help="population size")
    ap.add_argument("--init-from", default="", help="pilot checkpoint to start from; empty = random init")
    ap.add_argument("--iters", type=int, default=150)
    ap.add_argument("--games", type=int, default=2000, help="games an iteration")
    ap.add_argument("--record", type=int, default=500, help="games an iteration recorded for PPO")
    ap.add_argument("--ppo-transitions", type=int, default=64000, help="PPO cap an iteration (0 = all recorded)")
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--swaps", type=int, default=3, help="cards a draw replaces")
    ap.add_argument("--field-sample", type=int, default=4, help="decks of the field each deck is read against")
    ap.add_argument("--draft-lr", type=float, default=1e-3)
    ap.add_argument("--draft-ent", type=float, default=0.01)
    ap.add_argument("--draft-h-in-floor", type=float, default=0.0,
                    help="a floor in nats on the entropy the incoming card is drawn with: a choice below it is drawn at "
                         "the temperature that reaches it (log #109)")
    ap.add_argument("--draft-group-p", type=float, default=0.0,
                    help="chance that a change of a draw is a group change: all of the card's remaining copies (log #127)")
    ap.add_argument("--draft-base", choices=["uniform", "features"], default="uniform",
                    help="the incoming draw's base measure: uniform over legal cards (R0), or features: H110's Nf, "
                         "exp(cos of the pilot's readings of the card in and the card out / tau) (log #193)")
    ap.add_argument("--draft-base-ent", type=float, default=3.0,
                    help="with --draft-base features: tau is set per deck so the base measure's mean entropy is this (nats)")
    ap.add_argument("--draft-heads", type=int, default=1,
                    help="draft heads, each drafting its share of the population with the one pilot (a league, log #120)")
    ap.add_argument("--draft-heads-init", choices=["fresh", "copy"], default="fresh",
                    help="heads a source does not have: uniform at the start (fresh) or copies of its first head (copy)")
    ap.add_argument("--draft-exploit", action="store_true",
                    help="heads after the first are exploiters: their draws and decks count only the games against the "
                         "first head's decks (log #123)")
    ap.add_argument("--draft-margin", type=float, default=0.5,
                    help="weight of the end-of-game prize margin in the draft head's reward (0 = result only)")
    ap.add_argument("--shaping", type=float, default=0.0, help="prize-shaping weight at iteration 0")
    ap.add_argument("--shaping-iters", type=int, default=100, help="iterations over which the shaping fades to 0")
    ap.add_argument("--season", type=int, default=1,
                    help="iterations a deck's draws are played before their results count (1 = a fresh draw every game)")
    ap.add_argument("--candidates", type=int, default=4, help="--season > 1 or --select: draws per deck per season")
    ap.add_argument("--select", action="store_true",
                    help="a deck moves to the best-scoring of itself and its candidates, not to a random draw (log #127)")
    ap.add_argument("--max-turns", type=int, default=0, help="a game unfinished at this turn is a draw (0: none; log #140)")
    ap.add_argument("--search-distill", type=float, default=0.0,
                    help="soft search targets on the recorded decisions (rl/train.py, C49, log #169/#174): the weight of "
                         "KL(target || pilot) over the searched moves, averaged over all rows (0 off)")
    ap.add_argument("--probe-p", type=float, default=0.05)
    ap.add_argument("--probe-k", type=int, default=4)
    ap.add_argument("--probe-dets", type=int, default=4)
    ap.add_argument("--distill-tau", type=float, default=0.1)
    ap.add_argument("--distill-clip", type=float, default=1.0)
    ap.add_argument("--round-turns", type=round_turns, default=0,
                    help='the 2000 round rule in every game (log #160): "T" or "A-B" (T drawn per deal); an unfinished game '
                         'goes to the side with more Prizes taken; PPO rewards and deck scores are the event points')
    ap.add_argument("--select-z", type=float, default=0.0,
                    help="--select: move only on a gain above this many standard errors (0: any gain; log #138)")
    ap.add_argument("--turnover-every", type=int, default=10)
    ap.add_argument("--turnover", type=float, default=0.15, help="share of the population replaced at a turnover")
    ap.add_argument("--init-wide", action="store_true", help="a new population starts from wide decks (log #127)")
    ap.add_argument("--protect", type=int, default=0,
                    help="a deck younger than this many iterations is not replaced at a turnover (log #127)")
    ap.add_argument("--turnover-wide", action="store_true",
                    help="turnover's fresh decks are wide decks (Pokemon lines with their Energy, rl/decks.py), not "
                         "rules-only random ones, which are Pokemon piles that never win a place (log #127)")
    ap.add_argument("--judge-pilot", default="",
                    help="a frozen second pilot (a checkpoint) that plays both seats of a --judge-share of the games "
                         "not recorded for PPO; their results judge decks like the rest (log #132)")
    ap.add_argument("--judge-share", type=float, default=0.5)
    ap.add_argument("--anchor", default="",
                    help="a frozen pilot (a checkpoint) whose choices PPO stays near on the practice games' decisions, "
                         "by KL(anchor || pilot) at --anchor-w (log #135)")
    ap.add_argument("--anchor-w", type=float, default=0.1)
    ap.add_argument("--draft-reset", action="store_true",
                    help="a fork's draft heads start new (uniform choices) instead of from the source's (log #130)")
    ap.add_argument("--type-cap", type=float, default=0.0,
                    help="a turnover replaces the worst decks of a type holding more than this share of the population "
                         "first, with mutants of the other types' best (0: off; log #129)")
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--save-every", type=int, default=25)
    ap.add_argument("--fork-from", default="", help="a metagame checkpoint whose whole state this run continues")
    ap.add_argument("--pilot-opts", default="", help='JSON architecture options added to the pilot, e.g. {"value_query": 4}')
    ap.add_argument("--reseed", type=int, default=None, help="at a fork: pairings and deals from this seed")
    ap.add_argument("--freeze-pilot", action="store_true", help="no PPO: the pilot plays and reads decks, unchanged")
    ap.add_argument("--ent", type=float, default=PPO["ent"])
    ap.add_argument("--epochs", type=int, default=PPO["epochs"])
    ap.add_argument("--micro-batch", type=int, default=PPO["micro_batch"])
    ap.add_argument("--lam", type=float, default=0.95, help="GAE lambda")
    ap.add_argument("--gamma", type=float, default=1.0,
                    help="discount per decision of a player (1: none); below 1 a sooner win is worth more (log #131)")
    ap.add_argument("--lam-value", type=float, default=None,
                    help="GAE lambda of the value targets only (default --lam; 1 = Monte Carlo returns, DouZero's; log #145)")
    ap.add_argument("--lam-turn", type=float, default=None,
                    help="GAE lambda between decisions of the same game turn (log #96; default: --lam everywhere)")
    ap.add_argument("--aux", type=float, default=0.0, help="weight of the auxiliary heads' loss (pilot aux_heads)")
    ap.add_argument("--distill", type=float, default=0.0,
                    help="expert iteration (log #96): weight of the cross-entropy toward a turn-level search's best option")
    ap.add_argument("--search-p", type=float, default=0.1, help="--distill: share of recorded main-phase decisions searched")
    ap.add_argument("--search-max", type=int, default=2, help="--distill: searched decisions a game at most")
    ap.add_argument("--search-options", type=int, default=6, help="--distill: options a search plays at most")
    ap.add_argument("--search-lines", type=int, default=2, help="--distill: lines an option (copies, hidden cards re-dealt)")
    ap.add_argument("--search-prize", type=float, default=0.0, help="--distill: a line's score per prize taken in the turn")
    ap.add_argument("--search-horizon", type=int, default=1,
                    help="--distill: turns a line is played before it is scored (1: the end of the turn; 2: after the reply)")
    ap.add_argument("--search-margin", type=float, default=0.02,
                    help="--distill: a search sets a target only if its best and worst options differ by more than this")
    ap.add_argument("--search-lethal", action="store_true",
                    help="--distill: targets only where an option won the game in every line (no value in the target; "
                         "the played option if it is one of them), log #106")
    ap.add_argument("--practice-games", type=int, default=0,
                    help="games an iteration between fresh wide random decks, for PPO only (log #127)")
    ap.add_argument("--practice-vs", type=float, default=0.0,
                    help="share of practice games against a best-quarter population deck, its side not trained (log #141)")
    ap.add_argument("--practice-vs-from", choices=["wide", "pop"], default="wide",
                    help="--practice-vs: the challenger, a wide deck or a population deck outside the best quarter")
    ap.add_argument("--judge-explore", type=float, default=None,
                    help="the games not recorded for PPO are played at the pilot's top option except at this share of "
                         "decisions, which are sampled (0: greedy), and only they judge decks: the draft head's reward, "
                         "--select, turnover and the best decks (log #128)")
    ap.add_argument("--judge-search", type=int, default=0,
                    help="games an iteration, of those not recorded for PPO, played with one-turn policy-guided search on "
                         "both seats; decks are scored by judged_mean (log #148); needs --judge-explore")
    ap.add_argument("--judge-search-k", type=int, default=4, help="--judge-search: the pilot's moves a search tries")
    ap.add_argument("--judge-search-dets", type=int, default=4, help="--judge-search: copies a move (hidden cards re-dealt)")
    ap.add_argument("--judge-search-steps", type=int, default=40, help="--judge-search: decisions a line at most")
    ap.add_argument("--judge-search-conc", type=int, default=0,
                    help="--judge-search: searched games a worker plays at once (0: the plain games' concurrency)")
    ap.add_argument("--judge-score", choices=["min", "search"], default="min",
                    help="--judge-search: a deck's score, the lower of its greedy and (shrunk) searched means, or the "
                         "searched one alone")
    ap.add_argument("--judge-search-prior", type=float, default=4.0,
                    help="--judge-search: games of the greedy mean the searched mean is shrunk toward it by")
    ap.add_argument("--judge-search-z", type=float, default=1.5,
                    help="--judge-score min: a score is lowered only to the shrunk searched mean plus this many of its "
                         "standard errors (0: the plain min, which noise alone lowers)")
    ap.add_argument("--fixed-decks", default="", help="diagnosis only (log #127): a JSON [{name, cards}] of fixed decks")
    ap.add_argument("--fixed-share", type=float, default=0.3, help="--fixed-decks: share of games with one on one side")
    ap.add_argument("--stop-file", default="", help="end cleanly after the iteration in which this file appears")
    args = ap.parse_args(argv)
    D, K = args.decks, args.draft_heads
    assert D >= 2 and K >= 1
    assert not (args.max_turns and args.round_turns), "--max-turns (a plain draw) or --round-turns (the round rule), not both"
    assert not (args.search_distill and args.distill), "--search-distill (soft) or --distill (hard targets), not both"

    run = ROOT / args.run
    run.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    limits.apply(device, args.workers)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    pool = Pool()

    rp = RemotePool(args.workers)
    rp.pace = 0.25
    info = rp.ask_all([{"cmd": "info"}] * args.workers)[0]
    prize_glob = info["tokens"]["prizeGlob"]
    ckpt = run / "checkpoint.pt"
    st = torch.load(ckpt, map_location=device, weights_only=False) if args.resume and ckpt.exists() else None
    fork = torch.load(ROOT / args.fork_from, map_location=device, weights_only=False) if args.fork_from and not st else None
    init = (torch.load(ROOT / args.init_from, map_location=device, weights_only=False)
            if args.init_from and not (st or fork) else None)
    opts = json.loads(args.pilot_opts) if args.pilot_opts else {}
    # The architecture: a resumed run's own (any --pilot-opts are already in it), else the source's plus --pilot-opts.
    c0 = st["config"] if st else {**(fork or init or {"config": PILOT})["config"], **opts}
    net = token_net(c0, info).to(device)
    def frozen(path):
        """A frozen pilot from a checkpoint, sized to the workers' bounds."""
        s = torch.load(ROOT / path, map_location=device, weights_only=False)
        m = token_net(s["config"], info).to(device)
        m.load_state_dict(s["model"] if "model" in s else s["net"])
        return m.eval()
    jnet = frozen(args.judge_pilot) if args.judge_pilot else None      # --judge-pilot: a second judge (log #132)
    assert not (args.judge_search and getattr(net, "memory", "none") != "none"), \
        "--judge-search: a pilot with memory cannot judge searched games (its search lines have no memory states)"
    assert not args.judge_search or args.judge_explore is not None, \
        "--judge-search needs --judge-explore (0: greedy), else the score it is set against is sampled play's"
    def jscore(x, default=None):
        """A deck's or candidate's score: judged_mean with --judge-search (log #148), else its mean as before (any
        searched results a forked or resumed state carries are then ignored)."""
        if not args.judge_search:
            return x["sum"] / x["n"] if x["n"] else default
        return judged_mean(x, args.judge_score, args.judge_search_prior, default, args.judge_search_z)

    def jcount(x):
        """The games behind jscore's score (--judge-search, log #148): n for the greedy mean, else the shrunk mean's."""
        j = judged(x, args.judge_score, args.judge_search_prior, args.judge_search_z)
        return j[1] if j else 0

    def tally(x):
        """(sum, n) of a deck's or candidate's results, the searched ones too with --judge-search."""
        return (x["sum"] + x.get("ssum", 0.0), x["n"] + x.get("sn", 0)) if args.judge_search else (x["sum"], x["n"])
    anet = frozen(args.anchor) if args.anchor and not args.freeze_pilot else None   # --anchor (log #135)
    if init:
        load_grown(net, init["model"])
    net.eval()
    opt = torch.optim.Adam(net.parameters(), lr=args.lr, eps=1e-5)
    drafters = [Drafter(pool, c0["d"], c0["heads"], args.swaps, args.draft_lr, device, h_in_floor=args.draft_h_in_floor,
                        group_p=args.draft_group_p, base=args.draft_base, base_ent=args.draft_base_ent)
                for _ in range(K)]
    targs = SimpleNamespace(**{**PPO, "ent": args.ent, "epochs": args.epochs, "micro_batch": args.micro_batch,
                               "aux": args.aux, "distill": args.distill, "anchor_w": args.anchor_w,
                               "search_distill": args.search_distill, "distill_tau": args.distill_tau,
                               "distill_clip": args.distill_clip})

    start, deal_seed, cands = 0, args.seed, {}          # cands (--season > 1): deck id -> its draws this season
    if st or fork:
        src = st or fork
        if st:
            net.load_state_dict(st["net"])
            opt.load_state_dict(st["opt"])
        elif load_grown(net, fork["net"]):              # new modules: Adam's moments carried over by name
            if "opt" in fork:                            # a population snapshot has none: Adam starts fresh
                old = [n for n, _ in token_net(fork["config"], info).named_parameters()]
                opt.load_state_dict(remap_adam(fork["opt"], old, net))
        elif "opt" in fork:
            opt.load_state_dict(fork["opt"])
        for g in opt.param_groups:                       # --lr wins over the saved one (a lab card may change it)
            g["lr"] = args.lr
        src_heads = src.get("drafters") or [src["drafter"]]
        assert len(src_heads) <= K, f"the source has {len(src_heads)} draft heads, more than --draft-heads {K}"
        for h, dr in enumerate(drafters):
            if fork and args.draft_reset:                # --draft-reset: a fork's heads start as new ones
                continue
            if h < len(src_heads):
                dr.load(src_heads[h])
            elif args.draft_heads_init == "copy":
                dr.load(src_heads[0])
        pop = [{**a, "deck": pool.vector(a["deck"])} for a in src["population"]]
        if not args.judge_search:                        # a --judge-search source's judged scores would go stale
            for a in pop:                                # (recent_score prefers them; log #148)
                a.pop("judged", None)
        assign_heads(pop, K, keep=len(src_heads) == K)
        next_id, start = src.get("next_id", max(a["id"] for a in src["population"]) + 1), src["iter"] + 1
        assert "rng" in src or args.reseed is not None, "a population snapshot has no random state: give --reseed"
        if "rng" in src:
            rng.bit_generator.state = src["rng"]
        deal_seed = src.get("deal_seed", args.seed)
        cands = (src.get("season") or {}).get("cands", {}) if args.season > 1 or args.select else {}
        if fork and args.reseed is not None:
            rng, deal_seed = np.random.default_rng(args.reseed), args.reseed
            torch.manual_seed(args.reseed)
    if not st:
        (run / "config.json").write_text(json.dumps({**vars(args), "pilot": net.config(), "ppo": vars(targs),
                                                    "device": device}, indent=1))
    if not (st or fork):
        pop = [{"id": i, "deck": (wide_deck if args.init_wide else random_deck)(pool, rng), "born": 0, "parent": None,
                "kind": "initial", "sum": 0.0, "n": 0}
               for i in range(D)]
        assign_heads(pop, K, keep=False)
        next_id = D
    D = len(pop)                                         # a fork or resume keeps its own population size
    fixed = [pool.vector(x["cards"]) for x in json.load(open(ROOT / args.fixed_decks, encoding="utf-8"))] if args.fixed_decks else []
    assert D >= K, f"{D} decks for {K} draft heads"
    log = open(run / "log.jsonl", "a")

    try:
        for it in range(start, args.iters):
            t0 = time.time()
            lam = args.shaping * max(0.0, 1.0 - it / max(args.shaping_iters, 1))
            season = args.season > 1 or args.select
            counted = it % args.season == args.season - 1                # the draft head learns from this iteration
            if season and it % args.season == 0:
                cands = {}
            # 1. read every deck against a sample of the field
            views = []
            for d in range(D):
                others = [e for e in range(D) if e != d]
                field = [pop[e]["deck"] for e in rng.choice(others, min(args.field_sample, len(others)), replace=False)]
                views.append(drafters[pop[d]["head"]].view(net, pop[d]["deck"], field))
            t1 = time.time()
            # 2. games: random pairs, a fresh draw for each side (in a season: one of the side's candidates)
            if season:
                for d in range(D):
                    if pop[d]["id"] not in cands:
                        held = ([{"deck": pop[d]["deck"].copy(), "ev_j": [], "ev_c": [], "ev_mask": [], "ev_left": [],
                                  "ev_T": [], "logp": 0.0}] if args.select else [])     # the deck itself, unchanged
                        held += [drafters[pop[d]["head"]].sample(views[d], rng) for _ in range(args.candidates)]
                        for x in held:
                            x["sum"], x["n"] = 0.0, 0
                        cands[pop[d]["id"]] = held
            shards = [{"decks": [], "jobs": [], "slots": []} for _ in range(args.workers)]
            games_meta, draws, unjudged, judged2, searched = {}, {}, set(), 0, 0
            rec_share = 0.0 if args.freeze_pilot else min(1.0, args.record / max(args.games, 1))
            for g in range(args.games):
                k, l = (int(x) for x in rng.choice(D, 2, replace=False))
                if fixed and rng.random() < args.fixed_share:   # a fixed deck f on l's side, as l = -1 - f
                    l = -1 - int(rng.integers(len(fixed)))
                k_seat, seed = 1 + int(rng.integers(2)), (deal_seed * 100_000 + it) * 1_000_003 + g
                sh = shards[g % args.workers]
                for a in (k, l):
                    if a < 0:
                        draws[g, a] = {"deck": fixed[-1 - a]}
                    elif season:
                        held = cands[pop[a]["id"]]
                        draws[g, a] = held[int(rng.integers(len(held)))]
                    else:
                        draws[g, a] = drafters[pop[a]["head"]].sample(views[a], rng)
                    sh["decks"].append({"name": f"g{g}d{a}", "cards": pool.names(draws[g, a]["deck"])})
                i = len(sh["decks"]) - 2
                rec = bool(rng.random() < rec_share)
                j2 = jnet is not None and not rec and rng.random() < args.judge_share     # --judge-pilot plays both seats
                sh["slots"] += [1, 1] if j2 else [0, 0]
                judged2 += j2
                sh["jobs"].append({"i": i, "j": i + 1, "iSeat": k_seat, "seed": seed, "rec": rec})
                if not rec and not j2 and searched < args.judge_search:   # --judge-search: the first S such games
                    sh["jobs"][-1]["search"] = True                           # (no random draw: the rest is unchanged)
                    searched += 1
                games_meta[seed] = (g, k, l, k_seat)
                if rec and args.judge_explore is not None:       # played sampled for PPO: judges no deck
                    unjudged.add(seed)
            if args.practice_vs:                                 # --practice-vs: the incumbents, the best quarter so far
                now = np.array([jscore(a, a.get("last", 0.5)) for a in pop])   # judged_mean (--judge-search, log #148)
                best_q = np.argsort(-now)[:max(1, D // 4)]
                rest_q = np.argsort(-now)[max(1, D // 4):]
            vs_seeds = set()
            for g in range(args.games, args.games + (0 if args.freeze_pilot else args.practice_games)):
                seed = (deal_seed * 100_000 + it) * 1_000_003 + g    # practice: two wide decks, recorded, nobody's draw
                sh = shards[g % args.workers]
                vs = bool(args.practice_vs) and rng.random() < args.practice_vs
                sh["decks"] += [{"name": f"p{g}a", "cards": pool.names(pop[int(rng.choice(rest_q))]["deck"]
                                                                       if vs and args.practice_vs_from == "pop" else wide_deck(pool, rng))},
                                {"name": f"p{g}b", "cards": pool.names(pop[int(rng.choice(best_q))]["deck"] if vs
                                                                       else wide_deck(pool, rng))}]
                sh["slots"] += [2 if anet is not None else 0, 3 if vs else 2 if anet is not None else 0]   # --anchor: slot 2 marks them
                if vs:
                    vs_seeds.add(seed)
                i = len(sh["decks"]) - 2
                sh["jobs"].append({"i": i, "j": i + 1, "iSeat": 1 + int(rng.integers(2)), "seed": seed, "rec": True})
                games_meta[seed] = None
            t2 = time.time()
            search = args.distill > 0 and not args.freeze_pilot
            extra = ({"cmd": "tsearch", "probeP": args.search_p, "maxProbes": args.search_max, "maxOptions": args.search_options,
                      "lines": args.search_lines, "prizeWeight": args.search_prize, "horizon": args.search_horizon} if search else {})
            msgs = [{"cmd": "games", "encoding": "tokens", "greedy": False, "deckoutWin": 1, "maxTurns": args.max_turns,
                     **({"roundTurns": args.round_turns} if args.round_turns else {}),
                     **({"probe": {"p": args.probe_p, "k": args.probe_k, "dets": args.probe_dets, "maxSteps": 40,
                                   "seed": (deal_seed * 100_000 + it) * 17 + w}} if args.search_distill else {}),
                     **({"judgeExplore": args.judge_explore} if args.judge_explore is not None else {}),
                     "concurrency": max(8, min(48, len(sh["jobs"]))), "out": str(run / f"rollout_w{w}.bin"),
                     "decks": sh["decks"], "jobs": sh["jobs"],
                     **({"slots": sh["slots"]} if jnet is not None or anet is not None or args.practice_vs else {}),
                     "history": int(net.config().get("history", 0) or 0),      # a pilot's action-history tokens (#76)
                     **({"judgeSearch": {"k": args.judge_search_k, "dets": args.judge_search_dets,
                                         "maxSteps": args.judge_search_steps, "concurrency": args.judge_search_conc,
                                         "seed": (deal_seed * 100_000 + it) * 31 + w}}
                        if any(j.get("search") for j in sh["jobs"]) else {}),
                     **extra, **({"seed": (deal_seed * 100_000 + it) * 31 + w} if search else {})}
                    for w, sh in enumerate(shards) if sh["jobs"]]
            models = {0: net, **({1: jnet} if jnet is not None else {}), **({2: net} if anet is not None else {}),
                      **({3: net} if args.practice_vs else {})}
            replies = rp.collect(msgs, models, device)
            t3 = time.time()

            # 3. PPO on the recorded games
            recorded, ppo = 0, {}
            if not args.freeze_pilot:
                rolls = [read_rollout(r["out"]) for r in replies]
                batch = concat(rolls)
                recorded = len(batch["action"])
                sd_row = None
                if args.search_distill:                      # soft search targets (log #174): moves and mean scores
                    batch["probe_c"], batch["probe_q"], sd_row = probe_targets(replies, rolls, args.probe_k)
                if search:                                   # each searched decision's target: its best-scoring option
                    batch["search_target"] = np.full(recorded, -1, dtype=np.int32)
                    off, n_t, n_moved = 0, 0, 0
                    verbs = {"target": {}, "played": {}}         # where the two differ: the kind of move each is
                    for r, ro in zip(replies, rolls):
                        for pr in r.get("probes", []):
                            sc = [x for x in pr["score"] if x is not None]
                            won = [i for i, (w, n) in enumerate(zip(pr.get("won", []), pr["n"])) if n and w == n]
                            if args.search_lethal:
                                bi = next((i for i in won if pr["probed"][i] == pr["chosen"]), won[0] if won else None)
                            elif len(sc) >= 2 and max(sc) - min(sc) > args.search_margin:
                                bi = max((x, i) for i, x in enumerate(pr["score"]) if x is not None)[1]
                            else:
                                bi = None
                            if bi is not None:
                                best = pr["probed"][bi]
                                batch["search_target"][off + pr["k"]] = best
                                n_t += 1
                                if best != pr["chosen"]:
                                    n_moved += 1
                                    if "keys" in pr:
                                        for side, key in (("target", pr["keys"][bi]), ("played", pr["chosenKey"])):
                                            v = key.split("|")[0]
                                            verbs[side][v] = verbs[side].get(v, 0) + 1
                        off += len(ro["action"])
                    search_stats = {"probes": sum(len(r.get("probes", [])) for r in replies), "targets": n_t,
                                    "differs": n_moved, "lines": sum(r.get("lines", 0) for r in replies),
                                    "line_errors": sum(r.get("lineErrors", 0) for r in replies),
                                    "seconds": round(max((r.get("searchSeconds", 0) for r in replies), default=0), 1),
                                    "verbs": verbs}
                if net.config().get("aux_heads"):
                    batch["aux_target"] = aux_targets(batch)        # before the shaping: the unshaped result
                batch["reward"] = shape_rewards(batch, lam, prize_glob)
                batch["adv"], batch["ret"] = advantages(batch, args.gamma, args.lam, args.lam_turn)
                if args.lam_value is not None and args.lam_value != args.lam:   # --lam-value: the value's own targets
                    batch["ret"] = advantages(batch, args.gamma, args.lam_value)[1]
                if args.practice_vs:                         # the incumbents' side (slot 3) is not trained; advantages
                    batch = subset(batch, np.flatnonzero(np.asarray(batch["slot"]) != 3))   # are per player, so unchanged
                n_b = len(batch["action"])
                if args.ppo_transitions and n_b > args.ppo_transitions:
                    batch = subset(batch, np.sort(rng.choice(n_b, args.ppo_transitions, replace=False)))
                batch["inputs"] = model_inputs(batch, "tokens")
                if anet is not None:                         # --anchor: the practice games' decisions (slot 2)
                    batch["anchor_row"] = np.asarray(batch["slot"]) == 2
                net.train()
                ppo = {q: round(v, 5) for q, v in ppo_update(net, opt, batch, SimpleNamespace(**vars(targs), anchor=anet),
                                                             device).items()}
                net.eval()
            t4 = time.time()

            # 4. REINFORCE for the draft head on every draw
            practice = [r for rep in replies for r in rep["results"] if games_meta[r["seed"]] is None]
            vs_games = [r for r in practice if r["seed"] in vs_seeds]          # --practice-vs: the challenger is deck i
            games = [r for rep in replies for r in rep["results"] if games_meta[r["seed"]] is not None]
            per = {d: {"samples": [], "z": [], "margin": [], "searched": []} for d in range(D)}
            vs0 = [[] for _ in range(K)]                     # each head's results against head 0's decks
            fixed_z = [[] for _ in fixed]                    # --fixed-decks: each fixed deck's results
            for r in games:
                if r["seed"] in unjudged:                    # --judge-explore: a sampled PPO game
                    continue
                g, k, l, k_seat = games_meta[r["seed"]]
                zk, zl = round_score(r, k_seat, args.round_turns), round_score(r, 3 - k_seat, args.round_turns)
                left = r.get("prizesLeft") or {}
                mk = (left.get(str(3 - k_seat), 0) - left.get(str(k_seat), 0)) / 6.0
                for a, b, z, m in ((k, l, zk, mk), (l, k, zl, -mk)):
                    if a < 0:
                        fixed_z[-1 - a].append(z)
                        continue
                    if b >= 0 and pop[b]["head"] == 0:
                        vs0[pop[a]["head"]].append(z)
                    elif args.draft_exploit and pop[a]["head"] > 0:   # an exploiter counts only games against head 0
                        continue
                    per[a]["samples"].append(draws[g, a])
                    per[a]["z"].append(z)
                    per[a]["margin"].append(m)
                    per[a]["searched"].append(bool(r.get("search")))
                    if season and r.get("search"):           # --judge-search: a searched game counts apart (log #148)
                        draws[g, a]["ssum"] = draws[g, a].get("ssum", 0.0) + z
                        draws[g, a]["sn"] = draws[g, a].get("sn", 0) + 1
                    elif season:                             # each candidate's results this season (--select)
                        draws[g, a]["sum"] += z
                        draws[g, a]["n"] += 1
            batch_d, z_iter = [[] for _ in range(K)], np.full(D, np.nan)      # each head learns from its own decks
            for d in range(D):
                if not per[d]["z"]:
                    continue
                z, m = np.array(per[d]["z"]), np.array(per[d]["margin"])
                if counted:
                    batch_d[pop[d]["head"]].append((views[d], per[d]["samples"], rloo(z + args.draft_margin * m, np.zeros(len(z)))))
                z_iter[d] = z.mean()
                s = np.array(per[d]["searched"], dtype=bool)
                if s.any():                                  # --judge-search: the searched games count apart (log #148)
                    pop[d]["ssum"] = pop[d].get("ssum", 0.0) + float(z[s].sum())
                    pop[d]["sn"] = pop[d].get("sn", 0) + int(s.sum())
                    z = z[~s]
                pop[d]["sum"] += float(z.sum())
                pop[d]["n"] += len(z)
            parts = [dr.update(b, args.draft_ent) for dr, b in zip(drafters, batch_d)] if counted else []
            draft = (parts[0] if K == 1 else {**{q: round(float(np.mean([p[q] for p in parts])), 4) for q in parts[0]},
                                              "heads": parts}) if parts else {}
            t5 = time.time()

            # 5. every population deck moves to one more draw (in a season, at its end: to one of its practised candidates;
            #    with --select to the best-scoring of them, the deck itself first among equals)
            select = {}
            nrng = np.random.default_rng([deal_seed, it, 148]) if args.judge_search else None   # null_searched's own
            if not season:
                for d in range(D):
                    pop[d]["deck"] = drafters[pop[d]["head"]].sample(views[d], rng)["deck"]
            elif counted:
                moved, gain, held_back, acc, prop, flips, flips_null = 0, [], 0, [], [], 0, 0.0
                def pick(held, score, games=None):
                    """The candidate a deck moves to under `score`, and whether --select-z held it back; `games`
                    (--judge-search): the games behind each score, for --select-z's error."""
                    mean = [score(x) for x in held]
                    k = max(range(len(held)), key=lambda q: (mean[q], -q))
                    if k > 0 and args.select_z > 0:              # --select-z: only a clear gain moves the deck
                        # (with --judge-search the rate takes the searched games too, the error each score's own
                        # games: n for a greedy mean, fewer or more for a shrunk searched one, log #148)
                        (s0, n0), (sk, nk) = tally(held[0]), tally(held[k])
                        pb = min(0.85, max(0.15, (s0 + sk) / max(n0 + nk, 1)))
                        if games:
                            n0, nk = games(held[0]), games(held[k])
                        if not (n0 and nk) or mean[k] - mean[0] <= args.select_z * (pb * (1 - pb) * (1 / n0 + 1 / nk)) ** 0.5:
                            return mean, 0, True
                    return mean, k, False
                for d in range(D):
                    held = cands[pop[d]["id"]]
                    if args.select:
                        mean, k, back = pick(held, lambda x: jscore(x, -1.0), jcount if args.judge_search else None)
                        held_back += back
                        if args.judge_search:                    # would the greedy games alone have chosen otherwise?
                            kg = pick(held, lambda x: x["sum"] / x["n"] if x["n"] else -1.0, lambda x: x["n"])[1]
                            flips += kg != k                     # and how often would noise alone (null_searched)?
                            flips_null += np.mean([pick([null_searched(x, nrng) for x in held], lambda x: jscore(x, -1.0),
                                                        jcount)[1] != kg for _ in range(NULL_REPS)])
                        sh = [deck_shape(pool, x["deck"]) for x in held]
                        sh = [np.array([s["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"]]) for s in sh]
                        prop += [s - sh[0] for s in sh[1:]]
                        if k > 0:
                            acc.append(sh[k] - sh[0])
                        moved += k > 0
                        if k > 0 and tally(held[0])[1]:
                            gain.append(mean[k] - mean[0])
                    else:
                        k = int(rng.integers(len(held)))
                    pop[d]["deck"] = held[k]["deck"].copy()
                if args.select:
                    select = {"moved": moved, "gain": round(float(np.mean(gain)), 4) if gain else None,
                              "games_per_candidate": round(float(np.mean([x["n"] for h in cands.values() for x in h])), 2),
                              "held_back": held_back,             # --select-z (log #138): P / T / E change, taken and drawn
                              "acc": np.round(np.mean(acc, 0), 3).tolist() if acc else None,
                              "prop": np.round(np.mean(prop, 0), 3).tolist() if prop else None,
                              **({"flips": flips, "flips_null": round(float(flips_null), 2),   # --judge-search
                                  "searched_per_candidate": round(float(np.mean(
                                      [x.get("sn", 0) for h in cands.values() for x in h])), 2)} if args.judge_search else {})}
                cands = {}

            # 6. turnover
            turnover, type_sizes, turn_flips = [], None, None
            if args.turnover_every and (it + 1) % args.turnover_every == 0:
                score = np.array([jscore(a, 0.5) for a in pop])          # --judge-search: judged_mean (log #148)
                if args.judge_search:                    # the bottom --turnover share and the best quarter that the
                    plain = np.array([a["sum"] / a["n"] if a["n"] else 0.5 for a in pop])   # greedy games alone pick
                    nb, nt = int(round(args.turnover * D)), max(1, D // 4)
                    def changed(sc):
                        """Places in the bottom share and the best quarter under `sc` that `plain` would not give."""
                        return (nb - len(set(np.argsort(sc, kind="stable")[:nb].tolist())
                                         & set(np.argsort(plain, kind="stable")[:nb].tolist())),
                                nt - len(set(np.argsort(-sc, kind="stable")[:nt].tolist())
                                         & set(np.argsort(-plain, kind="stable")[:nt].tolist())))
                    null = np.mean([changed(np.array([jscore(null_searched(a, nrng), 0.5) for a in pop]))
                                    for _ in range(NULL_REPS)], 0)           # noise alone (null_searched)
                    nb_flips, nt_flips = changed(score)
                    turn_flips = {"bottom": nb_flips, "top": nt_flips,
                                  "bottom_null": round(float(null[0]), 2), "top_null": round(float(null[1]), 2),
                                  "gap": round(float(np.mean([jscore(a) - a["sum"] / a["n"] for a in pop
                                                              if a.get("sn") and a["n"]] or [0.0])), 4)}
                for h in range(K):                               # each head's share, so a head is never crowded out
                    mine = np.array([d for d in range(D) if pop[d]["head"] == h])
                    order = mine[np.argsort(score[mine])]
                    top = order[-max(1, len(mine) // 4):]
                    old = [d for d in order if it + 1 - pop[d]["born"] >= args.protect]    # --protect: the young stay
                    if args.type_cap:                            # --type-cap: an overfull type's worst go first
                        kind_of, sizes = deck_kinds(pool, [pop[d]["deck"] for d in mine], score[mine])
                        kind = dict(zip(mine.tolist(), kind_of.tolist()))
                        big = int(np.argmax(sizes))
                        type_sizes = sorted(sizes, reverse=True)[:8]
                        if sizes[big] > args.type_cap * len(mine):
                            first = [d for d in old if kind[d] == big][:sizes[big] - int(args.type_cap * len(mine))]
                            old = first + [d for d in old if d not in first]
                            rest = [d for d in order if kind[d] != big]
                            if rest:                             # mutants of the other types' best quarter
                                top = np.array(rest[-max(1, len(rest) // 4):])
                    for d in old[:int(round(args.turnover * len(mine)))]:
                        if rng.random() < MUTANT_SHARE:
                            p = int(rng.choice(top))
                            new = {"deck": random_changes(pool, pop[p]["deck"], MUTANT_CHANGES, rng), "parent": pop[p]["id"],
                                   "kind": "mutant"}
                        else:
                            new = {"deck": (wide_deck if args.turnover_wide else random_deck)(pool, rng), "parent": None,
                                   "kind": "wide" if args.turnover_wide else "random"}
                        turnover.append({"out": pop[d]["id"], "score": round(float(score[d]), 4), "in": next_id,
                                         "kind": new["kind"], **({"head": h} if K > 1 else {})})
                        pop[d] = {"id": next_id, "born": it + 1, "sum": 0.0, "n": 0, "head": h, **new}
                        next_id += 1
                for a, sc in zip(pop, score):                    # a fresh window for everyone
                    if a["born"] <= it:
                        a["last"] = round(float(sc), 4)          # the window's result, for rl/evaluate_agents.py
                    a["sum"], a["n"] = 0.0, 0
                    if args.judge_search:
                        a["ssum"], a["sn"] = 0.0, 0
            if args.judge_search:                                # each deck's judged score as it stands, for the
                for a in pop:                                    # checkpoint's readers (recent_score; None in a
                    a["judged"] = jscore(a)                      # fresh window, which then read 'last'; log #148)

            shapes = np.array([[s["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"]]
                               for s in (deck_shape(pool, a["deck"]) for a in pop)])
            best = [int(d) for d in np.argsort(-np.nan_to_num(z_iter, nan=-1))[:3]]
            cut = sum(1 for r in games if r["winner"] not in (1, 2))
            row = {"iter": it, "lam": round(lam, 5), "games": len(games), "errors": sum(1 for r in games if r.get("error")),
                   "cut_off": cut, "steps_per_game": round(float(np.mean([r["steps"] for r in games])), 1),
                   "endings": {e: sum(1 for r in games if (r.get("ending") or "none") == e) for e in {r.get("ending") or "none" for r in games}},
                   "recorded": recorded, "ppo": ppo, "draft": draft, "counted": counted,
                   **({"judged": sum(1 for r in games if r["seed"] not in unjudged)} if args.judge_explore is not None else {}),
                   **({"select": select} if select else {}),
                   **({"types": type_sizes} if type_sizes else {}),
                   **({"judged2": judged2} if jnet is not None else {}),
                   **({"practice": {"games": len(practice), "errors": sum(1 for r in practice if r.get("error")),
                                    "steps_per_game": round(float(np.mean([r["steps"] for r in practice])), 1),
                                    **({"vs": len(vs_games), "vs_score": round(float(np.mean(
                                        [1.0 if r["winner"] == r["iSeat"] else 0.0 if r["winner"] in (1, 2) else 0.5
                                         for r in vs_games])), 4) if vs_games else None} if args.practice_vs else {})}}
                      if practice else {}),
                   **({"search": search_stats} if search and not args.freeze_pilot and recorded else {}),
                   **({"search_distill": {**(sd_row or {}), **{q: ppo.get(q) for q in ("sd_kl", "sd_agree")}}}
                      if args.search_distill and not args.freeze_pilot else {}),
                   **({"judge_search": judge_search_row(games, replies, select, turn_flips)} if args.judge_search else {}),
                   "margin_abs": round(float(np.mean([abs(m) for d in range(D) for m in per[d]["margin"]])), 4),
                   "shape_quartiles": {k: np.percentile(shapes[:, i], [25, 50, 75]).tolist()
                                       for i, k in enumerate(("pokemon", "trainer", "energy"))},
                   "z": [None if np.isnan(x) else round(float(x), 3) for x in z_iter],
                   "ids": [a["id"] for a in pop], "shapes": shapes.tolist(),
                   "best": [{"id": pop[d]["id"], "z": round(float(z_iter[d]), 3), "kind": pop[d]["kind"], "born": pop[d]["born"],
                             **({"head": pop[d]["head"]} if K > 1 else {}),
                             **deck_shape(pool, pop[d]["deck"]), **drafters[pop[d]["head"]].summary(views[d])} for d in best],
                   **({"heads": [{"decks": len(mine), "z": round(float(np.nanmean(z_iter[mine])), 3) if mine else None,
                                  "median": np.median(shapes[mine], 0).tolist() if mine else None,
                                  "vs0": round(float(np.mean(vs0[h])), 3) if vs0[h] else None}
                                 for h, mine in enumerate([d for d in range(D) if pop[d]["head"] == h] for h in range(K))]}
                      if K > 1 else {}),
                   "turnover": turnover,
                   **({"fixed": {"games": sum(map(len, fixed_z)), "z": round(float(np.mean([x for f in fixed_z for x in f])), 4)
                                 if any(fixed_z) else None,
                                 "by_deck": [round(float(np.mean(f)), 3) if f else None for f in fixed_z]}} if fixed else {}),
                   "seconds": {"read": round(t1 - t0, 1), "draw": round(t2 - t1, 1), "play": round(t3 - t2, 1),
                               "ppo": round(t4 - t3, 1), "draft": round(t5 - t4, 1), "total": round(time.time() - t0, 1)}}
            log.write(json.dumps(row) + "\n")
            log.flush()
            q = row["shape_quartiles"]
            print(f"it {it}: {len(games)} games in {row['seconds']['play']}s ({row['seconds']['total']}s), cut {cut}, "
                  f"recorded {recorded}, lam {lam:.3f}; median P/T/E {q['pokemon'][1]:.0f}/{q['trainer'][1]:.0f}/{q['energy'][1]:.0f}; "
                  "best " + ", ".join(f"#{b['id']} {b['z']:.2f} {b['pokemon']}/{b['trainer']}/{b['basic_energy'] + b['special_energy']}"
                                      for b in row["best"])
                  + (f"; turnover {len(turnover)}" if turnover else ""), flush=True)

            state = {"net": net.state_dict(), "opt": opt.state_dict(), "drafter": drafters[0].state(),
                     **({"drafters": [dr.state() for dr in drafters]} if K > 1 else {}), "config": net.config(),
                     "population": [{**a, "deck": pool.names(a["deck"])} for a in pop], "next_id": next_id,
                     "iter": it, "round": it, "rng": rng.bit_generator.state, "deal_seed": deal_seed,
                     "season": {"cands": cands} if season else None,
                     "agents": [{"id": a["id"], "deck": pool.names(a["deck"])} for a in pop]}
            tmp = ckpt.with_suffix(".tmp")
            torch.save(state, tmp)
            os.replace(tmp, ckpt)
            if args.save_every and (it + 1) % args.save_every == 0:
                torch.save({k: state[k] for k in ("net", "drafter", "drafters", "config", "population", "agents", "iter", "round")
                            if k in state},
                           run / f"population_it{it:04d}.pt")
            for f in run.glob("rollout_w*.bin"):
                f.unlink(missing_ok=True)
            if args.stop_file and Path(args.stop_file).exists():
                print(f"stop file {args.stop_file}: ending after iteration {it}", flush=True)
                break
    finally:
        rp.close()
        log.close()


if __name__ == "__main__":
    main()
