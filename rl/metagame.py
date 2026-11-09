"""The metagame (logs #65-67): a population of decks, one pilot, one draft head.

Every iteration:
  1. the draft head reads every deck of the population through the pilot, against --field-sample other
     decks of the population (rl/draft.py)
  2. --games games between decks drawn at random from the population, seats at random; in every game each side plays
     one of its population deck's candidates (below), chosen at random
  3. the pilot learns by PPO from --record of those games (both seats), with potential-based prize shaping
     that fades from --shaping to 0 over --shaping-iters (rl/train.py shape_rewards)
  4. the draft head takes one REINFORCE step on every draw's result (win 1, draw 0.5, loss 0) plus
     --draft-margin times the prize margin at the end ((opponent's prizes left - own) / 6), with a
     leave-one-out baseline over each deck's games; the margin tells draws apart in a matchup that is
     always lost (log #66)
  5. at a season's end every population deck moves to one of its candidates (below)
  6. every --turnover-every iterations the --turnover share of decks with the worst results over that
     period is replaced: by a fresh random deck (the format's rules only; with --turnover-wide a wide deck, log #127),
     or 1 in 4 by a deck of the best quarter with 10 cards replaced at random (log #67); with --protect K decks younger
     than K iterations are spared, so a new deck is drafted for a while before it is judged (log #127)
--season K (log #93): a deck's draws are practised before they count. At the start of a season every deck draws
--candidates draws (--swaps cards replaced, chosen by the head), and every game of the season plays one of them, chosen
at random; the pilot trains on all of them by PPO, but only the season's last iteration feeds the draft head (step 4),
whose leave-one-out baseline then compares a deck's candidates after the same practice; at its end every deck moves to
one of its candidates, chosen at random (step 5). A deck that turnover brings in mid-season draws its candidates at once.
--select (log #127): the deck itself is one of its candidates, played unchanged beside its --candidates draws (every
iteration with --season 1, else through the season), and at the move (step 5) the deck moves to whichever of them scored
best in its games, itself on a tie, instead of to a random one. A run needs --select or --season > 1: the forced draws
without either (every deck moving every iteration to a draw of --swaps changes whatever their results, R0) are gone;
under them, once the head's incoming choice collapsed onto one card, every draw added that card until the copy limit
stopped it, so basic Energy, which has none, piled up (#127). The select log row gives the mean change in Pokémon,
Trainers and Energy over the moves taken ("acc") and over every candidate drawn ("prop"): what the games accept against
what the head proposes. A fork may start from a population snapshot (population_it*.pt), which carries no optimizer or
random state: Adam starts fresh, and --reseed is required.
--select-paired (log C90): a deck and its entries play the same scheduled games (one opponent entry, seat and deal, an
entry each); the move takes the entry with the best mean paired difference from the deck, if above its SE, else stays.
Nothing human enters training: the archived lists and SimpleBot are for evaluation only (rl/evaluate_agents.py).
--practice-games N (log #127): N more games an iteration between two fresh random decks of a playable structure and no
strategy (rl/decks.py wide_deck, the kind pilot-v2 learned on), all recorded for PPO and outside the population and the
draft head, so the pilot keeps playing every kind of deck: a pilot trained only on its population's one deck type
played other types so badly that no other type could win a place (#127).
--type-cap C (log #129): no deck type keeps more than a share C of the population. At a turnover the decks are grouped
into types as rl/lab.py counts them (best first, each joining the first type whose founding deck shares at least half its
Pokémon, rl/decks.py pokemon_overlap); if the largest holds more than C, its worst decks are replaced first (still
--turnover of the population a time, the young spared), and the mutants come from the other types' best quarter. A
population of one type trains a pilot that plays every other type badly, so no other type can win a place (#127); the cap
keeps the rest of the population for other types, which the pilot then plays and the draft head drafts. Fitness sharing
(a result over its type's size) was tried first on paper: every fresh deck is a type of one, so sharing would have
replaced the main type's decks until fresh decks that never win held most of the places.

Run: .venv/Scripts/python -m rl.metagame --run runs/meta-99 --decks 99 --init-from runs/pilot-v2/model_it00349.pt --select

The lab (rl/lab.py, notes/plan-lab.md) ran this loop as its main line and its branches: --fork-from continues another
run's whole state (pilot, optimizer, draft head, population, random state) in a new run, --pilot-opts grows the pilot
by new modules that start as the identity or at zero (rl/train.py load_grown), --reseed draws the fork's pairings and
deals afresh (the A/A test), --stop-file ends the run cleanly after an iteration.
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
from rl.train import (advantages, load_grown, model_inputs, ppo_update, probe_targets, remap_adam, round_score, round_turns,
                      shape_rewards, token_net)

ROOT = Path(__file__).resolve().parent.parent
PILOT = {"d": 256, "layers": 4, "heads": 8, "count_features": True, "cross_layers": 1, "cand_self": 0}   # pilot-v2's shape
PPO = {"model": "tokens", "amp": True, "epochs": 3, "minibatch": 4096, "micro_batch": 1024, "clip": 0.2, "vf": 0.5,
       "ent": 0.01, "max_grad_norm": 0.5, "gpu_load": 0.7}                                            # tourn-3's settings
MUTANT_SHARE, MUTANT_CHANGES = 0.25, 10


def recent_score(a: dict, default: float = 0.0) -> float:
    """A checkpoint's population deck by its recent results, as rl/evaluate_agents.py, rl/lab.py deck_types and the
    probe scripts rank its best decks: the judged score an old --judge-search run last held (a['judged'], log #148;
    None in a fresh window), else its mean this window, else the last window's."""
    if a.get("judged") is not None:
        return a["judged"]
    return a["sum"] / a["n"] if a.get("n") else a.get("last", default)


def table_head_share(views: list, bonus: np.ndarray, top: np.ndarray, allowed: np.ndarray) -> dict:
    """C171: the head's mean incoming probability on the table's top 10 names, over the decks, without the table's offset (own) and with it."""
    own, both = [], []
    mask = np.isin(np.flatnonzero(allowed), top)
    for vw in views:
        if vw.logits is None:
            continue
        x = vw.logits[:, allowed]
        for out, y in ((own, x), (both, x + bonus[allowed])):
            q = np.exp(y - y.max(1, keepdims=True))
            q /= q.sum(1, keepdims=True)
            out.append(float(q[:, mask].sum(1).mean()))
    return {"own": round(float(np.mean(own)), 4), "with_bonus": round(float(np.mean(both)), 4)} if own else {}


def head_mass(views: list, kinds: np.ndarray, bonus: np.ndarray = None) -> dict:
    """C184: the incoming mass by supertype (1 Pokemon, 2 Trainer, 3 Energy), over the decks, each row weighted by its out-choice, on the base measure, before
    the floor and any bonus (own): the learning signal. with_bonus adds the plain offset, which --table-neutral doesn't sample. out is the out-choice's mass by supertype, copies the deck's share:
    out over copies is what the head prefers to take out (C187's caps read: W's Trainers fall by this, not by the incoming mass)."""
    own, both, outs, copies = [], [], [], []
    for vw in views:
        po = np.log(vw.counts) + vw.s
        po = np.exp(po - po.max())
        po /= po.sum()
        outs.append([po[kinds[vw.ids] == k].sum() for k in (1, 2, 3)])
        copies.append([vw.counts[kinds[vw.ids] == k].sum() / vw.counts.sum() for k in (1, 2, 3)])
        base = vw.base.cpu().numpy()
        x = vw.logits if vw.b0np is None else vw.b0np + vw.logits
        for out, y in ((own, x),) + (((both, x + bonus),) if bonus is not None else ()):
            y = np.where(base, y, -np.inf)
            q = np.exp(y - y.max(1, keepdims=True))
            q /= q.sum(1, keepdims=True)
            inc = (po[:, None] * q).sum(0)
            out.append([inc[kinds == k].sum() for k in (1, 2, 3)])
    r = {"own": np.round(np.mean(own, 0), 4).tolist(), "out": np.round(np.mean(outs, 0), 4).tolist(), "copies": np.round(np.mean(copies, 0), 4).tolist()}
    return {**r, "with_bonus": np.round(np.mean(both, 0), 4).tolist()} if both else r


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


def win_speed(reward: np.ndarray, turn: np.ndarray, cost: float, floor: float) -> np.ndarray:
    """--win-turn-cost (C130): a full win (reward exactly +1) pays max(1 - cost * game turn, floor); time wins (+1/3),
    draws and losses are unchanged. cost 0 returns the rewards untouched."""
    if not cost:
        return reward
    paid = np.maximum(1.0 - cost * turn.astype(np.float32), floor).astype(reward.dtype)
    return np.where(reward == 1.0, paid, reward)


def clock_payout(reward: np.ndarray, tw: float, d: float) -> np.ndarray:
    """--clock-payout TW,D (C131): the round rule's clock outcomes in the pilot's reward, a time win (+1/3 scaled) paid
    2 TW - 1 and a draw (-1/3) 2 D - 1; wins and losses unchanged."""
    out = np.where(np.isclose(reward, 1 / 3), 2 * tw - 1, reward)
    return np.where(np.isclose(reward, -1 / 3), 2 * d - 1, out).astype(reward.dtype)


def size_neutral(batch: list, hist: list) -> dict:
    """C188 (--draft-size-neutral): the batch's candidates' mean advantage fitted on the copies each moved, a = alpha + lam m. lam's mean over the last 5
    iterations, times (m - mean m), comes off each candidate's games, in place, so the head's credit doesn't see edit size. Moves and selection don't change."""
    rows = []
    for _, samples, adv in batch:
        e = np.array([bool(x["ev_j"]) for x in samples])
        if e.any():
            x = samples[int(np.argmax(e))]
            rows.append((len(x["ev_j"]) + sum(x["ev_n"]), float(adv[e].mean()), adv, e))
    if not rows:
        return {}
    m, a = np.array([r[0] for r in rows], dtype=np.float64), np.array([r[1] for r in rows])
    lam = float(np.polyfit(m, a, 1)[0]) if m.std() > 0 else 0.0
    hist.append(lam)
    bar = float(np.mean(hist[-5:]))
    for r in rows:
        r[2][r[3]] -= bar * (r[0] - m.mean())
    return {"size_lambda": round(lam, 5), "size_lambda_bar": round(bar, 5), "size_m": round(float(m.mean()), 3)}


def paired_move(vs: list):
    """--select-paired: (entry, complete slots): the entry q >= 1 with the largest mean of z(q) - z(0) over the slots, if
    that mean exceeds its SE (sd with ddof 1 / sqrt(n), n >= 2), else 0."""
    v = np.array([x for x in vs if not np.isnan(x).any()])
    if len(v) < 2:
        return 0, len(v)
    d = v[:, 1:] - v[:, :1]
    m, se = d.mean(0), d.std(0, ddof=1) / np.sqrt(len(v))
    q = int(np.argmax(m))
    return (q + 1 if m[q] > se[q] else 0), len(v)


TD_NAMES = ("PlusPower", "Gust of Wind", "Item Finder", "Scoop Up", "Professor Oak", "Bill", "Gambler")   # C150's readout only


def thompson_fit(slots: list, n: int, tau: float):
    """--thompson-share (C150): the posterior of a first-order per-card model of a paired slot's difference, y ~ sum_c beta_c
    dcount_c + noise, with prior beta_c ~ N(0, tau^2) and the noise sd from the data (the residual of the previous fit, twice).
    slots: [(card ids, count changes, y)]. Returns (posterior mean, posterior precision, noise sd)."""
    A, b = np.zeros((n, n)), np.zeros(n)
    for ids, vals, y in slots:
        i, v = np.asarray(ids, dtype=np.int64), np.asarray(vals, dtype=np.float64)
        A[np.ix_(i, i)] += np.outer(v, v)
        b[i] += v * y
    ys = np.array([y for _, _, y in slots], dtype=np.float64)
    sig2 = float(ys.var()) if len(ys) > 1 else 1.0
    for _ in range(3):
        P = A / sig2 + np.eye(n) / tau ** 2
        mu = np.linalg.solve(P, b / sig2)
        if len(ys) < 2:
            break
        res = ys - np.array([float(np.dot(np.asarray(v, dtype=np.float64), mu[np.asarray(i, dtype=np.int64)])) for i, v, _ in slots])
        sig2 = max(float(np.mean(res ** 2)), 1e-6)
    return mu, P, sig2 ** 0.5


def thompson_draw(mu: np.ndarray, L: np.ndarray, rng) -> np.ndarray:
    """One posterior sample: mu + L^-T z, with L the Cholesky factor of the posterior precision (P = L L^T), so its covariance is
    P^-1."""
    return mu + np.linalg.solve(L.T, rng.standard_normal(len(mu)))


def thompson_swap(pool: Pool, v0: np.ndarray, beta: np.ndarray, swaps: int) -> np.ndarray:
    """--thompson-share (C150): the deck changed by `swaps` copies, greedily the swap with the highest beta(in) - beta(out) each
    time: a copy of the original deck out (the last Basic Pokemon stays), any addable card in except the one taken out."""
    v, left = v0.copy(), v0.copy()
    for _ in range(swaps):
        best = None
        for r in np.nonzero(left > 0)[0]:
            if pool.basic_pokemon[r] and v[pool.basic_pokemon].sum() <= 1:
                continue
            v[r] -= 1
            m = pool.addable(v)
            m[r] = False
            if m.any():
                a = int(np.argmax(np.where(m, beta, -np.inf)))
                if best is None or beta[a] - beta[r] > best[0]:
                    best = (beta[a] - beta[r], int(r), a)
            v[r] += 1
        if best is None:
            break
        _, r, a = best
        v[r] -= 1
        left[r] -= 1
        v[a] += 1
    assert pool.legal(v), "a Thompson deck is not legal"
    return v


def thompson_stats(pool: Pool, cands: dict, fit, n_slots: int) -> dict:
    """--thompson-share: the Thompson and head proposals' incoming copies that are tempo or draw cards (C150's R-proposes), and the
    posterior mean and SD of each such card (readouts only; no proposal reads a card's name)."""
    td = np.isin(pool.name, TD_NAMES)
    tot, seen, pte = {"thompson": [0, 0, 0], "head": [0, 0, 0]}, {"thompson": set(), "head": set()}, {"thompson": [], "head": []}
    for held in cands.values():
        for x in held[1:]:
            inc = np.maximum(x["deck"] - held[0]["deck"], 0)
            k = "thompson" if x.get("thompson") else "head"
            s = tot[k]
            s[0] += 1
            s[1] += int(inc.sum())
            s[2] += int(inc[td].sum())
            seen[k].update(np.nonzero(inc)[0].tolist())
            s1, s0 = deck_shape(pool, x["deck"]), deck_shape(pool, held[0]["deck"])     # Amendment 1: the P / T / E change
            pte[k].append([s1["pokemon"] - s0["pokemon"], s1["trainer"] - s0["trainer"],
                           s1["basic_energy"] + s1["special_energy"] - s0["basic_energy"] - s0["special_energy"]])
    mu, P, sigma = fit
    cov = np.linalg.inv(P)
    return {"slots": n_slots, "sigma": round(sigma, 4),
            **{k: {"proposals": a, "copies_in": b, "td_in": c, "td_share": round(c / b, 4) if b else None, "distinct_in": len(seen[k]),
                   "pte": np.round(np.mean(pte[k], 0), 3).tolist() if pte[k] else None} for k, (a, b, c) in tot.items()},
            "beta": {pool.full_name[i]: [round(float(mu[i]), 4), round(float(cov[i, i]) ** 0.5, 4)] for i in np.nonzero(td)[0]}}


def budget_move(vs: list, evaluated: bool, rng):
    """--select-budget (C155): (entry, log) for one deck. A deck not evaluated this iteration stays: (0, None). An evaluated deck's
    complete slots split at random into halves A and B; the entry q >= 1 with the largest half-A mean of z(q) - z(0) is kept if that
    mean exceeds 2 SE (else 0), and half B's mean and SE for that entry are logged, so B never decides."""
    if not evaluated:
        return 0, None
    v = np.array([x for x in vs if not np.isnan(x).any()])
    if len(v) < 4:
        return 0, {"n": len(v), "kept": False, "entry": None}
    perm = rng.permutation(len(v))
    a, b = v[perm[:len(v) // 2]], v[perm[len(v) // 2:]]
    da, db = a[:, 1:] - a[:, :1], b[:, 1:] - b[:, :1]
    ma, sa = da.mean(0), da.std(0, ddof=1) / np.sqrt(len(a))
    q = int(np.argmax(ma))
    kept = bool(ma[q] > 2 * sa[q])
    return (q + 1 if kept else 0), {"n": len(v), "nA": len(a), "nB": len(b), "mA": round(float(ma[q]), 4), "seA": round(float(sa[q]), 4),
                                     "mB": round(float(db[:, q].mean()), 4), "seB": round(float(db[:, q].std(ddof=1) / np.sqrt(len(b))), 4),
                                     "kept": kept, "entry": q + 1}


def retest_summary(rt_log: list, n_rt: int, pending: int) -> dict:
    """--select-retest (C151): this iteration's re-tests (mean differences, None where no slot completed), and the next's."""
    played = [x for x in rt_log if x is not None]
    pos = sum(x > 0 for x in played)
    return {"read": len(rt_log), "played": len(played), "kept": pos, "positive_share": round(pos / len(played), 3) if played else None,
            "mean_diff": round(float(np.mean(played)), 4) if played else None, "games": 2 * n_rt, "pending": pending}


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
    ap.add_argument("--draft-out-bonus", choices=["entropy", "none", "kl"], default="entropy",
                    help="the out choice's term under --draft-ent: entropy over names, none, or -KL from copy shares (C188)")
    ap.add_argument("--edit-slots", action="store_true",
                    help="write edit_slots.jsonl: each candidate's picks and its paired results (C188; no decision reads it; required by the two flags beside it)")
    ap.add_argument("--draft-size-neutral", action="store_true",
                    help="the head's credit doesn't see edit size: fit each candidate's advantage on the copies it moved, and take the last 5 iterations' mean slope off (C188)")
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
    ap.add_argument("--draft-margin", type=float, default=0.5,
                    help="weight of the end-of-game prize margin in the draft head's reward (0 = result only)")
    ap.add_argument("--shaping", type=float, default=0.0, help="prize-shaping weight at iteration 0")
    ap.add_argument("--shaping-iters", type=int, default=100, help="iterations over which the shaping fades to 0")
    ap.add_argument("--season", type=int, default=1,
                    help="iterations a deck's candidates are played before their results count (1: one iteration, with --select)")
    ap.add_argument("--candidates", type=int, default=4, help="--season > 1 or --select: draws per deck per season")
    ap.add_argument("--select", action="store_true",
                    help="a deck moves to the best-scoring of itself and its candidates, not to a random one (log #127); "
                         "a run needs it or --season > 1")
    ap.add_argument("--select-paired", action="store_true",
                    help="with --select: a deck and each of its entries play the same scheduled games (opponent entry, seat, "
                         "deal); the move takes the best mean paired difference if above its SE, else stays (C90); "
                         "--games becomes games // (1 + --candidates) slots")
    ap.add_argument("--select-z", type=float, default=0.0,
                    help="--select: move only on a gain above this many standard errors (0: any gain; log #138, restored C91)")
    ap.add_argument("--select-margin", type=float, default=0.0,
                    help="--select-paired: the move rule's entry score is the round result plus this times the Prize margin "
                         "(opponent's Prizes left minus own, / 6); 0 is the result alone. Only the move changes (C128)")
    ap.add_argument("--search-distill", type=float, default=0.0,
                    help="PPO: weight of the search-target term (C49's soft KL, or with --distill-margin C137's hard CE); "
                         "0: off, nothing searched")
    ap.add_argument("--probe-p", type=float, default=0.05, help="--search-distill: share of recorded main-phase decisions searched")
    ap.add_argument("--probe-k", type=int, default=4, help="--search-distill: the pilot's most likely moves searched (64: all)")
    ap.add_argument("--probe-dets", type=int, default=4, help="--search-distill: re-dealt copies shared by the moves (CRN)")
    ap.add_argument("--probe-trainer-only", action="store_true",
                    help="--search-distill: only decisions where a Trainer play is legal (C137)")
    ap.add_argument("--distill-tau", type=float, default=0.1, help="--search-distill, soft: target pi * exp(clip((q - mean q) / tau))")
    ap.add_argument("--distill-clip", type=float, default=1.0, help="--search-distill, soft: the clip of (q - mean q) / tau")
    ap.add_argument("--distill-margin", type=float, default=None,
                    help="--search-distill: C137's hard target, the best-scored searched move where it beats the pilot's top-1 by "
                         "this or more (rl/train.py ppo_update); unset: C49's soft target")
    ap.add_argument("--loop-search", choices=["S", "V"], default=None,
                    help="C138: every population game played with the pilot's own search at Trainer-playable decisions (env/remote_worker.js "
                         "LoopSearchAgent: the top --loop-search-k plus every legal Trainer play, V-scored). S: the recorded share enters PPO with "
                         "the searched decisions as sampled 0 (value only); V: no population game is recorded, and PPO trains on the practice "
                         "games plus --unsearched-record separate unsearched games, outside selection and the head")
    ap.add_argument("--loop-search-k", type=int, default=3, help="--loop-search: the policy's top k, plus every legal Trainer play")
    ap.add_argument("--loop-search-dets", type=int, default=2, help="--loop-search: re-dealt copies a candidate (CRN)")
    ap.add_argument("--unsearched-record", type=int, default=500, help="--loop-search V: the separate unsearched recorded games")
    ap.add_argument("--card-ledger", action="store_true",
                    help="--select: also log select.card, per-card sums of each candidate's change from its deck (prop_net, "
                         "prop_in) and of the moves taken (acc_net), with n_prop and n_acc; logging only (C127)")
    ap.add_argument("--round-turns", type=round_turns, default=0,
                    help='the 2000 round rule in every game (log #160): "T" or "A-B" (T drawn per deal); an unfinished game '
                         'goes to the side with more Prizes taken; PPO rewards and deck scores are the event points')
    ap.add_argument("--turnover-every", type=int, default=10)
    ap.add_argument("--turnover", type=float, default=0.15, help="share of the population replaced at a turnover")
    ap.add_argument("--init-wide", action="store_true", help="a new population starts from wide decks (log #127)")
    ap.add_argument("--protect", type=int, default=0,
                    help="a deck younger than this many iterations is not replaced at a turnover (log #127)")
    ap.add_argument("--table", default="",
                    help="C171: a {name: coefficient} JSON of Pokemon values from the run's own factorial games; off by default")
    ap.add_argument("--table-kappa", type=float, default=3.0, help="C171: exp(kappa z) on wide-deck picks, kappa z on the head's logits; z is c/SD(c), centred")
    ap.add_argument("--init-t-range", default="", help="C184: LO-HI, wide decks at init and turnover rejection-sampled to this many Trainers; off by default")
    ap.add_argument("--init-e-range", default="", help="C191: LO-HI, wide decks at init and turnover rejection-sampled to this many basic plus special Energy; off by default")
    ap.add_argument("--table-neutral", action="store_true", help="C184: the table's bonus moves picks only inside a supertype; each supertype's total proposal mass is what it'd be with no bonus, at each pick")
    ap.add_argument("--table-scope", choices=["all", "proposals", "trainers"], default="all", help="C171: all is initial and turnover wide decks plus proposals; proposals is the head alone. C182: trainers is all of those for a Trainer table")
    ap.add_argument("--pop-lists", action="store_true", help="C203 (b): with --fork-from, the population is the 24 archived lists "
                    "(a bench diagnostic, pilot and head frozen by --lr 0 --draft-lr 0, checked by hash; nothing seeds from it); off by default")
    ap.add_argument("--lists-age", type=int, default=0, help="C203 Amendment 2: with --pop-lists, the lists start this many iterations old "
                    "(born = start - N), so --protect doesn't shield them while entrants keep it; 0 by default")
    ap.add_argument("--save-first", action="store_true", help="C171: also save the population after iteration 0, for a read of the start decks")
    ap.add_argument("--turnover-mutant", action="store_true",
                    help="C168: a turnover always replaces with a mutant of the best quarter, never a fresh deck")
    ap.add_argument("--turnover-wide", action="store_true",
                    help="turnover's fresh decks are wide decks (Pokemon lines with their Energy, rl/decks.py), not "
                         "rules-only random ones, which are Pokemon piles that never win a place (log #127)")
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
    ap.add_argument("--epochs", type=int, default=PPO["epochs"])
    ap.add_argument("--micro-batch", type=int, default=PPO["micro_batch"])
    ap.add_argument("--lam", type=float, default=0.95, help="GAE lambda")
    ap.add_argument("--lam-turn", type=float, default=None,
                    help="GAE lambda between decisions of the same game turn (log #96; default: --lam everywhere)")
    ap.add_argument("--gamma-turn", type=float, default=None,
                    help="GAE discount per game turn between a seat's decisions (C121: 0.98; default: none)")
    ap.add_argument("--win-turn-cost", type=float, default=0.0,
                    help="PPO only: a full win (+1) pays max(1 - this x the game turn, --win-floor); time wins, draws and "
                         "losses unchanged; selection and the head keep the real scoring (C130; 0: off)")
    ap.add_argument("--win-floor", type=float, default=0.5, help="--win-turn-cost: the least a full win pays (C130)")
    ap.add_argument("--clock-payout", type=lambda s: tuple(float(x) for x in s.split(",")), default=None,
                    help='PPO only, "TW,D": a time win pays 2 TW - 1 and a draw 2 D - 1 in the pilot\'s reward (the round '
                         'rule: 2/3 and 1/3, so +1/3 and -1/3); selection and the head keep the real scoring (C131)')
    ap.add_argument("--select-retest", action="store_true",
                    help="--select-paired: an entry that passes the paired rule is re-tested next iteration on as many fresh "
                         "paired slots (fresh opponents and deals, unrecorded, outside the head), and the deck moves to it only "
                         "if that mean difference is above 0, else it stays (C151)")
    ap.add_argument("--thompson-share", type=float, default=0.0,
                    help="--select-paired: this share of decks draws its candidates from a Thompson sample of a pooled per-card model "
                         "of the paired slots' differences (the last --thompson-window iterations) instead of the head; 0 off (C150)")
    ap.add_argument("--thompson-bonus", type=float, default=0.0,
                    help="--select-paired: add K x a per-deck posterior sample of C150's per-card model, standardised by each card's "
                         "posterior SD, to the head's incoming logits (before its base measure and floor); the head samples and "
                         "learns as before, its log-probs including the bonus; 0 off (C153)")
    ap.add_argument("--thompson-window", type=int, default=5, help="--thompson-share: iterations of paired slots the model fits")
    ap.add_argument("--thompson-tau", type=float, default=0.02, help="--thompson-share: the prior SD of a card's effect")
    ap.add_argument("--select-budget", type=int, default=0,
                    help="--select-paired: each iteration only M decks (in rotation) are evaluated, every paired slot goes to them, "
                         "and each moves on half A of its slots at 2 SE, half B held out and logged; the rest stay; 0 off (C155)")
    ap.add_argument("--practice-games", type=int, default=0,
                    help="games an iteration between fresh wide random decks, for PPO only (log #127)")
    ap.add_argument("--practice-from-pop", type=float, default=0.0,
                    help="this share of the practice games pairs two decks of the population's top quarter by recent_score "
                         "instead of two wide decks, still for PPO only, outside selection and the head; 0 off (C148)")
    ap.add_argument("--practice-rotation", type=int, default=0,
                    help="every practice deck is concentrated with R focus Trainers forced in at 3-4 copies, the pool's Trainers "
                         "taken R an iteration round-robin in a fixed shuffled order; card-neutral; 0 off (C159)")
    ap.add_argument("--practice-curriculum", type=int, default=0,
                    help="every practice deck is concentrated with the K Trainers of lowest play rate (turns played over turns a play "
                         "was legal, in the last iteration's population games; ties to fewer turns) forced in at 3 copies; 0 off (C160)")
    ap.add_argument("--stop-file", default="", help="end cleanly after the iteration in which this file appears")
    args = ap.parse_args(argv)
    D = args.decks
    assert D >= 2
    assert args.select or args.season > 1, "--select or --season > 1 (the forced draws without either are gone)"

    run = ROOT / args.run
    run.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    paired = args.select_paired
    H = 1 + args.candidates if paired else 1                # games a slot plays: the deck's entries, one opponent entry
    assert not paired or (args.select and args.workers >= H), "--select-paired needs --select and --workers >= 1 + --candidates"
    assert not (paired and args.select_z > 0), "--select-paired and --select-z are separate selection rules"
    assert not args.select_retest or paired, "--select-retest re-tests --select-paired moves"
    assert args.edit_slots or (args.draft_out_bonus == "entropy" and not args.draft_size_neutral), "C188's record requires --edit-slots of --draft-out-bonus none or kl and of --draft-size-neutral"
    assert not args.edit_slots or paired, "--edit-slots reads --select-paired's slots"
    assert not args.draft_size_neutral or args.candidates == 1, "--draft-size-neutral fits one candidate a deck"
    assert not args.select_budget or (paired and not args.select_retest), "--select-budget needs --select-paired, not --select-retest"
    assert not (args.thompson_share or args.thompson_bonus) or paired, "--thompson-share and --thompson-bonus fit --select-paired slots"
    limits.apply(device, args.workers)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    pool = Pool()
    rot = [int(x) for x in np.random.default_rng(159).permutation(       # C159: the fixed order, the same at every seed
        [c["id"] for c in pool.cards if pool.allowed[c["id"]] and c["superType"] == 2])]
    tr_id = {str(pool.name[c]): c for c in rot}                         # C160: a Trainer's bare name -> its pool id
    assert not (args.practice_rotation and args.practice_curriculum), "--practice-rotation or --practice-curriculum, not both"

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

    def mean_score(x, default=None):
        """A deck's or candidate's score: its mean result this window (default without games)."""
        return x["sum"] / x["n"] if x["n"] else default
    if init:
        load_grown(net, init["model"])
    net.eval()
    opt = torch.optim.Adam(net.parameters(), lr=args.lr, eps=1e-5)
    drafter = Drafter(pool, c0["d"], c0["heads"], args.swaps, args.draft_lr, device, h_in_floor=args.draft_h_in_floor,
                      group_p=args.draft_group_p, base=args.draft_base, base_ent=args.draft_base_ent, out_bonus=args.draft_out_bonus)
    targs = SimpleNamespace(**{**PPO, "epochs": args.epochs, "micro_batch": args.micro_batch,
                               **({"search_distill": args.search_distill, "distill_tau": args.distill_tau,     # C137; off: absent
                                   "distill_clip": args.distill_clip, "distill_margin": args.distill_margin}
                                  if args.search_distill else {})})

    start, deal_seed, cands = 0, args.seed, {}          # cands: deck id -> its candidates this season
    pairs = {}                                           # --select-paired: deck id -> its focus slots' vectors of results
    retest = {}                                          # --select-retest: deck id -> {deck, n}, an entry to re-test this iteration
    thompson_hist = []                                   # --thompson-share: [iteration, slots] of the last --thompson-window iterations
    tplay = {}                                           # --practice-curriculum: Trainer -> [turns legal, turns played], last iteration
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
        drafter.load(src["drafter"])                     # a league source's 'drafter' is its first head (log #120)
        pop = [{**a, "deck": pool.vector(a["deck"])} for a in src["population"]]
        for a in pop:                                    # an old --judge-search source's judged scores would go stale
            a.pop("judged", None)                        # (recent_score prefers them; log #148)
        next_id, start = src.get("next_id", max(a["id"] for a in src["population"]) + 1), src["iter"] + 1
        assert "rng" in src or args.reseed is not None, "a population snapshot has no random state: give --reseed"
        if "rng" in src:
            rng.bit_generator.state = src["rng"]
        deal_seed = src.get("deal_seed", args.seed)
        season = src.get("season") or {}                 # mid-season: so a pause doesn't change selection
        cands = {i: h for i, h in season.get("cands", {}).items()      # --select-paired plays entry q < H: a fork's
                 if not paired or len(h) == H}                           # other --candidates draws that deck's anew
        pairs = {i: v for i, v in season.get("pairs", {}).items() if paired and i in cands}   # older: none
        retest = {i: {"deck": pool.vector(v["deck"]), "n": v["n"]} for i, v in season.get("retest", {}).items()}
        thompson_hist = season.get("thompson", [])
        tplay = season.get("tplay", {})
        if fork and args.reseed is not None:
            rng, deal_seed = np.random.default_rng(args.reseed), args.reseed
            torch.manual_seed(args.reseed)
        if fork and args.pop_lists:                      # C203 (b): the forked nets on a population of the 24 lists, fresh scores
            from rl.decks import archived_decks
            pop = [{"id": i, "deck": v, "born": start - args.lists_age, "parent": None, "kind": "list", "sum": 0.0, "n": 0}
                   for i, (_, v) in enumerate(archived_decks(pool))]
            next_id, cands, pairs, retest, thompson_hist = len(pop), {}, {}, {}, []
            for g in drafter.opt.param_groups:           # drafter.load restored the saved lr (W's 3e-4); --draft-lr wins here, as --lr does
                g["lr"] = args.draft_lr
    if not st:
        (run / "config.json").write_text(json.dumps({**vars(args), "pilot": net.config(), "ppo": vars(targs),
                                                    "device": device}, indent=1))
    card_kind = np.zeros(pool.n, dtype=np.int64)
    for c in pool.cards:
        card_kind[c["id"]] = c["superType"]
    table_weight, trainer_weight, table_bonus, table_top, table_groups = None, None, None, None, None
    if args.table:                                       # C171: Pokemon names only; every other card gets 0, so P/T/E don't shift by construction
        coef = json.loads(Path(args.table).read_text(encoding="utf-8"))
        vals = np.array(list(coef.values()), dtype=float)
        z = {n: float((c - vals.mean()) / vals.std()) for n, c in coef.items()}
        table_bonus = np.zeros(pool.n)
        kind = 2 if args.table_scope == "trainers" else 1      # C182: a Trainer table, every other card 0
        for c in pool.cards:
            if c["superType"] == kind and c["name"] in z:
                table_bonus[c["id"]] = args.table_kappa * z[c["name"]]
        table_groups = card_kind if args.table_neutral else None
        names_top = sorted(z, key=lambda n: -z[n])[:10]
        table_top = np.array([c["id"] for c in pool.cards if c["superType"] == kind and c["name"] in names_top])
        if args.table_scope == "all":
            table_weight = {n: float(np.exp(args.table_kappa * v)) for n, v in z.items()}
        if args.table_scope == "trainers":
            trainer_weight = {n: float(np.exp(args.table_kappa * v)) for n, v in z.items()}
        print(f"table: {len(z)} names, kappa {args.table_kappa}, scope {args.table_scope}", flush=True)
    t_range = tuple(int(x) for x in args.init_t_range.split("-")) if args.init_t_range else None
    e_range = tuple(int(x) for x in args.init_e_range.split("-")) if args.init_e_range else None

    def fresh_wide():
        while True:                                      # C184, C191: the generator otherwise, kept only inside the ranges
            v = wide_deck(pool, rng, name_weight=table_weight, trainer_weight=trainer_weight)
            s = deck_shape(pool, v)
            if (t_range is None or t_range[0] <= s["trainer"] <= t_range[1]) and \
               (e_range is None or e_range[0] <= s["basic_energy"] + s["special_energy"] <= e_range[1]):
                return v

    if not (st or fork):
        pop = [{"id": i, "deck": (fresh_wide() if args.init_wide else random_deck(pool, rng)), "born": 0, "parent": None,
                "kind": "initial", "sum": 0.0, "n": 0}
               for i in range(D)]
        next_id = D
    D = len(pop)                                         # a fork or resume keeps its own population size
    lam_hist = []                                        # --draft-size-neutral: lambda by iteration, carried over a resume
    if args.draft_size_neutral and (run / "log.jsonl").exists():
        lam_hist = [r["draft"]["size_lambda"] for r in map(json.loads, open(run / "log.jsonl", encoding="utf-8")) if "size_lambda" in (r.get("draft") or {})]
    log = open(run / "log.jsonl", "a")

    try:
        for it in range(start, args.iters):
            t0 = time.time()
            lam = args.shaping * max(0.0, 1.0 - it / max(args.shaping_iters, 1))
            counted = it % args.season == args.season - 1                # the draft head learns from this iteration
            if it % args.season == 0:
                cands, pairs = {}, {}
            # 1. read every deck against a sample of the field
            views = []
            for d in range(D):
                others = [e for e in range(D) if e != d]
                field = [pop[e]["deck"] for e in rng.choice(others, min(args.field_sample, len(others)), replace=False)]
                views.append(drafter.view(net, pop[d]["deck"], field))
            t1 = time.time()
            fit_t = L_t = None                               # --thompson-share (C150): this iteration's posterior and its factor
            n_fit = 0
            if args.thompson_share or args.thompson_bonus:
                fit_slots = [s for _, sl in thompson_hist for s in sl]
                n_fit = len(fit_slots)
                fit_t = thompson_fit(fit_slots, pool.n, args.thompson_tau)
                L_t = np.linalg.cholesky(fit_t[1])
            if args.thompson_bonus:                          # C153: each deck's own sample, standardised, on the head's logits
                sd_t = np.sqrt(np.diag(np.linalg.inv(fit_t[1])))
                for d in range(D):
                    views[d].bonus = args.thompson_bonus * thompson_draw(fit_t[0], L_t, rng) / sd_t
            if table_bonus is not None:                      # C171: the same offset for every deck, through the C153 path
                for d in range(D):
                    views[d].bonus, views[d].bonus_groups = table_bonus, table_groups
            # 2. games: random pairs, each side playing one of its candidates this season
            for d in range(D):
                if pop[d]["id"] not in cands:
                    held = ([{"deck": pop[d]["deck"].copy(), "ev_j": [], "ev_c": [], "ev_mask": [], "ev_left": [],
                              "ev_T": [], "logp": 0.0}] if args.select else [])     # the deck itself, unchanged
                    if L_t is not None and rng.random() < args.thompson_share:   # C150: Thompson's swap, not the head's, from a
                        held += [{"deck": thompson_swap(pool, pop[d]["deck"], thompson_draw(fit_t[0], L_t, rng), args.swaps),
                                  "ev_j": [], "ev_c": [], "ev_mask": [], "ev_left": [], "ev_T": [], "logp": 0.0, "thompson": True}
                                 for _ in range(args.candidates)]               # posterior sample of its own (Amendment 1)
                    else:
                        held += [drafter.sample(views[d], rng) for _ in range(args.candidates)]
                    for x in held:
                        x["sum"], x["n"] = 0.0, 0
                    cands[pop[d]["id"]] = held
            shards = [{"decks": [], "jobs": []} for _ in range(args.workers)]
            games_meta, draws, pair = {}, {}, {}                 # keyed by seed, or with --select-paired by (shard, job i)
            rec_share = min(1.0, args.record / max(args.games, 1))
            focus = [(it * args.select_budget + m) % D for m in range(args.select_budget)] if args.select_budget else []   # C155
            for g in range(args.games // H * H):
                q = g % H                                                # with --select-paired: slot g // H, entry q
                if q == 0 and focus:                                     # C155: the slot's focus is one of this iteration's M decks
                    k = focus[(g // H) % len(focus)]
                    l = int(rng.choice([x for x in range(D) if x != k]))
                elif q == 0:
                    k, l = (int(x) for x in rng.choice(D, 2, replace=False))
                if q == 0:
                    k_seat, seed = 1 + int(rng.integers(2)), (deal_seed * 100_000 + it) * 1_000_003 + g // H
                    eo = int(rng.integers(len(cands[pop[l]["id"]]))) if paired else 0     # l's one entry in the slot
                w = (g // H + q) % args.workers      # the paired jobs share a seed: one shard each (remote_worker.js bySeed)
                sh = shards[w]
                i = len(sh["decks"])
                for a in (k, l):
                    held = cands[pop[a]["id"]]
                    draws[(w, i) if paired else g, a] = held[(q if a == k else eo) if paired else int(rng.integers(len(held)))]
                    sh["decks"].append({"name": f"g{g}d{a}", "cards": pool.names(draws[(w, i) if paired else g, a]["deck"])})
                rec = bool(rng.random() < rec_share)
                if args.loop_search == "V":                  # C138-V: searched population games aren't recorded
                    rec = False
                sh["jobs"].append({"i": i, "j": i + 1, "iSeat": k_seat, "seed": seed, "rec": rec,
                                   **({"lsearch": True} if args.loop_search else {})})
                games_meta[(w, i) if paired else seed] = ((w, i) if paired else g, k, l, k_seat)
                pair[w, i] = (g // H, q)
            rt_meta, n_rt = {}, 0                            # --select-retest (C151): (shard, job i) -> (deck id, slot, entry, seat)
            at = {a["id"]: d for d, a in enumerate(pop)} if args.select_retest else {}
            for did, rt in retest.items():
                if did not in at:
                    continue                                 # turnover replaced the deck
                d = at[did]
                for s in range(rt["n"]):                     # the deck (q 0) and its entry (q 1) on a fresh opponent, seat and deal
                    l = int(rng.choice([x for x in range(D) if x != d]))
                    k_seat, seed = 1 + int(rng.integers(2)), (deal_seed * 100_000 + it) * 1_000_003 + 500_000 + n_rt
                    n_rt += 1
                    for q, deck in enumerate((pop[d]["deck"], rt["deck"])):
                        w = (n_rt + q) % args.workers        # the pair shares a seed: one shard each
                        sh = shards[w]
                        i = len(sh["decks"])
                        sh["decks"] += [{"name": f"rt{n_rt}q{q}", "cards": pool.names(deck)},
                                        {"name": f"rt{n_rt}o", "cards": pool.names(pop[l]["deck"])}]
                        sh["jobs"].append({"i": i, "j": i + 1, "iSeat": k_seat, "seed": seed, "rec": False})
                        games_meta[(w, i)] = None
                        rt_meta[(w, i)] = (did, s, q, k_seat)
            if args.loop_search == "V":                      # C138-V: PPO's unsearched games, drawn as the loop draws, outside selection
                for g in range(args.unsearched_record):
                    k, l = (int(x) for x in rng.choice(D, 2, replace=False))
                    seed = (deal_seed * 100_000 + it) * 1_000_003 + 2_000_000 + g
                    sh = shards[g % args.workers]
                    for a in (k, l):
                        held = cands[pop[a]["id"]]
                        sh["decks"].append({"name": f"u{g}d{a}", "cards": pool.names(held[int(rng.integers(len(held)))]["deck"])})
                    i = len(sh["decks"]) - 2
                    sh["jobs"].append({"i": i, "j": i + 1, "iSeat": 1 + int(rng.integers(2)), "seed": seed, "rec": True})
                    games_meta[(g % args.workers, i) if paired else seed] = None
            top_q = (sorted(range(D), key=lambda d: -recent_score(pop[d]))[:max(2, D // 4)]   # C148: the top quarter
                     if args.practice_from_pop else [])
            n_pop = 0
            p_focus = {rot[(it * args.practice_rotation + j) % len(rot)] for j in range(args.practice_rotation)}   # C159
            cur = sorted(tplay, key=lambda n: (tplay[n][1] / tplay[n][0], tplay[n][0]))[:args.practice_curriculum]   # C160
            p_focus |= {tr_id[n] for n in cur}
            for g in range(args.games, args.games + args.practice_games):
                seed = (deal_seed * 100_000 + it) * 1_000_003 + g    # practice: two wide decks, recorded, nobody's draw
                sh = shards[g % args.workers]
                if top_q and rng.random() < args.practice_from_pop:  # C148: two of the population's best decks instead
                    a, b = (int(x) for x in rng.choice(top_q, 2, replace=False))
                    sh["decks"] += [{"name": f"p{g}a", "cards": pool.names(pop[a]["deck"])},
                                    {"name": f"p{g}b", "cards": pool.names(pop[b]["deck"])}]
                    n_pop += 1
                elif p_focus:                                        # C159: both decks concentrated around this iteration's focus
                    sh["decks"] += [{"name": f"p{g}{x}", "cards": pool.names(wide_deck(pool, rng, concentrated=True, focus=p_focus,
                                                                                    focus_copies=3 if cur else 0))} for x in "ab"]
                else:
                    sh["decks"] += [{"name": f"p{g}a", "cards": pool.names(wide_deck(pool, rng))},
                                    {"name": f"p{g}b", "cards": pool.names(wide_deck(pool, rng))}]
                i = len(sh["decks"]) - 2
                sh["jobs"].append({"i": i, "j": i + 1, "iSeat": 1 + int(rng.integers(2)), "seed": seed, "rec": True})
                games_meta[(g % args.workers, i) if paired else seed] = None
            t2 = time.time()
            msgs = [{"cmd": "games", "encoding": "tokens", "greedy": False, "deckoutWin": 1,
                     **({"roundTurns": args.round_turns} if args.round_turns else {}),
                     "concurrency": max(8, min(48, len(sh["jobs"]))), "out": str(run / f"rollout_w{w}.bin"),
                     "decks": sh["decks"], "jobs": sh["jobs"],
                     "history": int(net.config().get("history", 0) or 0),     # a pilot's action-history tokens (#76)
                     "chain": int(net.config().get("chain", 0) or 0),         # and its chain rows (the chain head)
                     **({"trainerPlay": True} if args.practice_curriculum else {}),   # C160: per-game Trainer play counts
                     "canon": int(net.config().get("state_canon", 0) or 0),   # and its one-token-per-card-per-zone encoding
                     **({"probe": {"p": args.probe_p, "k": args.probe_k, "dets": args.probe_dets, "maxSteps": 40,   # C137
                                   "seed": args.seed * 7919 + it, "trainerOnly": args.probe_trainer_only,
                                   "log": str(run / "probe_summary.jsonl")}}   # log only: each probe's top-1, best and margin
                        if args.search_distill else {}),
                     **({"loopSearch": {"k": args.loop_search_k, "dets": args.loop_search_dets, "maxSteps": 40,   # C138
                                        "seed": args.seed * 7919 + it}} if args.loop_search else {})}
                    for w, sh in enumerate(shards) if sh["jobs"]]
            replies = rp.collect(msgs, {0: net}, device)
            for w, rep_ in zip([w for w, sh in enumerate(shards) if sh["jobs"]], replies):    # replies align with msgs
                for r in rep_["results"]:
                    r["key"] = (w, r["i"]) if paired else r["seed"]
            t3 = time.time()

            # 3. PPO on the recorded games
            rolls = [read_rollout(r["out"]) for r in replies]
            batch = concat(rolls)
            recorded = len(batch["action"])
            distill = None
            if args.search_distill:                      # C137: the workers' search targets, per transition (rl/train.py)
                batch["probe_c"], batch["probe_q"], distill = probe_targets(replies, rolls, args.probe_k)
            if args.win_turn_cost:                       # --win-turn-cost (C130): sooner full wins pay more; off skips it
                batch["reward"] = win_speed(batch["reward"], batch["obs.glob"].reshape(recorded, -1)[:, 0],
                                            args.win_turn_cost, args.win_floor)
            if args.clock_payout:                        # --clock-payout (C131): the clock outcomes' training payout
                batch["reward"] = clock_payout(batch["reward"], *args.clock_payout)
            batch["reward"] = shape_rewards(batch, lam, prize_glob)
            batch["adv"], batch["ret"] = advantages(batch, 1.0, args.lam, args.lam_turn, args.gamma_turn)
            n_b = len(batch["action"])
            if args.ppo_transitions and n_b > args.ppo_transitions:
                batch = subset(batch, np.sort(rng.choice(n_b, args.ppo_transitions, replace=False)))
            batch["inputs"] = model_inputs(batch, "tokens")
            net.train()
            ppo = {q: round(v, 5) for q, v in ppo_update(net, opt, batch, SimpleNamespace(**vars(targs)), device).items()}
            net.eval()
            t4 = time.time()

            # 4. REINFORCE for the draft head on every draw
            practice = [r for rep in replies for r in rep["results"] if games_meta[r["key"]] is None and r["key"] not in rt_meta]
            games = [r for rep in replies for r in rep["results"] if games_meta[r["key"]] is not None]
            if args.practice_curriculum:                     # C160: next iteration's curriculum from these population games
                tp_used = [{"name": n, "rate": round(tplay[n][1] / tplay[n][0], 4), "turns": tplay[n][0]} for n in cur]
                tplay = {}
                for r in games:
                    for n, (a, b) in (r.get("tplay") or {}).items():
                        x = tplay.setdefault(n, [0, 0])
                        x[0] += a
                        x[1] += b
            rt_vec = {}                                      # --select-retest: deck id -> slot -> [the deck's score, its entry's]
            for r in (r for rep in replies for r in rep["results"] if r["key"] in rt_meta):
                did, s, q, k_seat = rt_meta[r["key"]]
                left = r.get("prizesLeft") or {}
                margin = (left.get(str(3 - k_seat), 0) - left.get(str(k_seat), 0)) / 6.0
                rt_vec.setdefault(did, {}).setdefault(s, [np.nan, np.nan])[q] = (round_score(r, k_seat, args.round_turns)
                                                                                 + args.select_margin * margin)
            per = {d: {"samples": [], "z": [], "margin": []} for d in range(D)}
            vec = {}
            for r in games:
                g, k, l, k_seat = games_meta[r["key"]]
                zk, zl = round_score(r, k_seat, args.round_turns), round_score(r, 3 - k_seat, args.round_turns)
                left = r.get("prizesLeft") or {}
                mk = (left.get(str(3 - k_seat), 0) - left.get(str(k_seat), 0)) / 6.0
                if paired:                                   # the focus deck's results by entry, per slot
                    s_, q_ = pair[r["key"]]                  # --select-margin W: the move rule scores zk + W * mk (C128)
                    vec.setdefault((k, s_), np.full(H, np.nan))[q_] = zk + args.select_margin * mk if args.select_margin else zk
                for a, z, m in ((k, zk, mk), (l, zl, -mk)):
                    per[a]["samples"].append(draws[g, a])
                    per[a]["z"].append(z)
                    per[a]["margin"].append(m)
                    draws[g, a]["sum"] += z                  # each candidate's results this season
                    draws[g, a]["n"] += 1
            batch_d, z_iter = [], np.full(D, np.nan)
            for d in range(D):
                if not per[d]["z"]:
                    continue
                z, m = np.array(per[d]["z"]), np.array(per[d]["margin"])
                if counted:
                    batch_d.append((views[d], per[d]["samples"], rloo(z + args.draft_margin * m, np.zeros(len(z)))))
                z_iter[d] = z.mean()
                pop[d]["sum"] += float(z.sum())
                pop[d]["n"] += len(z)
            if args.edit_slots:                              # C188: each candidate's picks and its paired results, for reads; no decision reads it
                by_deck = {}
                for (d, s_), v in vec.items():
                    by_deck.setdefault(d, []).append((s_, v))
                with open(run / "edit_slots.jsonl", "a", encoding="utf-8") as f:
                    for d, slots in by_deck.items():
                        for q in range(1, H):
                            x = cands[pop[d]["id"]][q]
                            f.write(json.dumps({"iter": it, "deck": pop[d]["id"], "parent": pop[d].get("parent"), "entry": q,
                                                "picks": [[pool.full_name[int(views[d].ids[j])], int(lf[j]), int(n), pool.full_name[int(c)]]   # out name, its copies at the pick, copies a group change moved beside it, in name
                                                          for j, c, n, lf in zip(x["ev_j"], x["ev_c"], x["ev_n"], x["ev_left"])],
                                                "slots": [[int(s_), round(float(v[0]), 4), round(float(v[q]), 4)] for s_, v in slots   # slot, the deck's result, the candidate's
                                                          if not (np.isnan(v[0]) or np.isnan(v[q]))]}) + "\n")
            size_read = size_neutral(batch_d, lam_hist) if args.draft_size_neutral and counted else {}
            for (d, _), v in vec.items():
                pairs.setdefault(pop[d]["id"], []).append(v)
            if args.thompson_share or args.thompson_bonus:   # C150: each paired slot's card-count change and result difference
                sl = []
                for (d, _), v in vec.items():
                    held = cands[pop[d]["id"]]
                    for q in range(1, H):
                        if not (np.isnan(v[0]) or np.isnan(v[q])):
                            dv = held[q]["deck"] - held[0]["deck"]
                            nz = np.nonzero(dv)[0]
                            sl.append((nz.tolist(), dv[nz].tolist(), float(v[q] - v[0])))
                thompson_hist = (thompson_hist + [[it, sl]])[-args.thompson_window:]
                with open(run / "thompson_slots.jsonl", "a") as f:
                    f.write(json.dumps({"iter": it, "slots": sl}) + "\n")
            draft = {**drafter.update(batch_d, args.draft_ent), **size_read} if counted else {}
            t5 = time.time()

            # 5. at a season's end every population deck moves to one of its practised candidates: with --select to the
            #    best-scoring of them, the deck itself first among equals, else to one at random
            select = {}
            if counted:
                moved, gain, acc, prop, slots, held_back = 0, [], [], [], [], 0
                retest_next, rt_log = {}, []                 # --select-retest: next iteration's re-tests; this one's mean differences
                bud_log = []                                 # --select-budget: the evaluated decks' halves (C155)
                draw_m, t4_m = np.isin(pool.name, TD_NAMES[4:]), np.isin(pool.name, TD_NAMES[:4])
                led = {"prop_net": 0, "prop_in": 0, "acc_net": 0}   # --card-ledger: per-card sums (C127); no decision reads it
                for d in range(D):
                    held = cands[pop[d]["id"]]
                    kept = None                                  # --select-retest: the re-tested entry the deck moves to
                    if args.select:
                        mean = [mean_score(x, -1.0) for x in held]
                        k = max(range(len(held)), key=lambda q: (mean[q], -q))
                        if paired:
                            k, n_ = paired_move(pairs.get(pop[d]["id"], []))
                            slots.append(n_)
                            if args.select_budget:               # C155: only this iteration's M decks move, on half A at 2 SE
                                k, bud = budget_move(pairs.get(pop[d]["id"], []), d in focus, rng)
                                if bud is not None:
                                    if bud["entry"] is not None:
                                        dv = held[bud["entry"]]["deck"] - held[0]["deck"]
                                        s1, s0 = deck_shape(pool, held[bud["entry"]]["deck"]), deck_shape(pool, held[0]["deck"])
                                        bud.update({"d_draw": int(dv[draw_m].sum()), "d_T4": int(dv[t4_m].sum()),
                                                    "d_pte": [s1["pokemon"] - s0["pokemon"], s1["trainer"] - s0["trainer"],
                                                              s1["basic_energy"] + s1["special_energy"] - s0["basic_energy"] - s0["special_energy"]]})
                                    bud_log.append({"id": pop[d]["id"], **bud})
                            if args.select_retest:               # C151: last iteration's winner moves only on a positive re-test,
                                did = pop[d]["id"]               # and this iteration's waits for its own
                                if did in retest:
                                    v = [x for x in rt_vec.get(did, {}).values() if not np.isnan(x).any()]
                                    dm = float(np.mean([b - a for a, b in v])) if v else None
                                    rt_log.append(dm)
                                    if dm is not None and dm > 0:
                                        kept = retest[did]["deck"]
                                if kept is None and k > 0:
                                    retest_next[did] = {"deck": held[k]["deck"].copy(), "n": n_}
                                k = 0
                        if k > 0 and args.select_z > 0:          # --select-z: only a clear gain moves the deck (log #138)
                            (s0, n0), (sk, nk) = (held[0]["sum"], held[0]["n"]), (held[k]["sum"], held[k]["n"])
                            pb = min(0.85, max(0.15, (s0 + sk) / max(n0 + nk, 1)))
                            if not (n0 and nk) or mean[k] - mean[0] <= args.select_z * (pb * (1 - pb) * (1 / n0 + 1 / nk)) ** 0.5:
                                k, held_back = 0, held_back + 1
                        sh = [deck_shape(pool, x["deck"]) for x in held]
                        sh = [np.array([s["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"]]) for s in sh]
                        prop += [s - sh[0] for s in sh[1:]]
                        if k > 0:
                            acc.append(sh[k] - sh[0])
                        if args.card_ledger:
                            dv = [x["deck"] - held[0]["deck"] for x in held]
                            for q in range(1, len(held)):
                                led["prop_net"] = led["prop_net"] + dv[q]
                                led["prop_in"] = led["prop_in"] + np.maximum(dv[q], 0)
                            if k > 0:
                                led["acc_net"] = led["acc_net"] + dv[k]
                        moved += k > 0
                        if k > 0 and held[0]["n"]:
                            gain.append(mean[k] - mean[0])
                    else:
                        k = int(rng.integers(len(held)))
                    if kept is not None:                         # C151: the re-tested move, logged as a move
                        s_k, s_0 = deck_shape(pool, kept), deck_shape(pool, held[0]["deck"])
                        acc.append(np.array([s_k["pokemon"] - s_0["pokemon"], s_k["trainer"] - s_0["trainer"],
                                             s_k["basic_energy"] + s_k["special_energy"] - s_0["basic_energy"] - s_0["special_energy"]]))
                        if args.card_ledger:
                            led["acc_net"] = led["acc_net"] + (kept - held[0]["deck"])
                        moved += 1
                        pop[d]["deck"] = kept.copy()
                    else:
                        pop[d]["deck"] = held[k]["deck"].copy()
                if args.select:                                  # P / T / E change, taken and drawn
                    select = {"moved": moved, "gain": round(float(np.mean(gain)), 4) if gain else None,
                              "games_per_candidate": round(float(np.mean([x["n"] for h in cands.values() for x in h])), 2),
                              "acc": np.round(np.mean(acc, 0), 3).tolist() if acc else None,
                              "prop": np.round(np.mean(prop, 0), 3).tolist() if prop else None,
                              **({"paired": {"slots": round(float(np.mean(slots)), 2),
                                             "stay_low_n": sum(1 for n_ in slots if n_ < 2)}} if paired else {}),
                              **({"held_back": held_back} if args.select_z > 0 else {}),
                              **({"retest": retest_summary(rt_log, n_rt, len(retest_next))} if args.select_retest else {}),
                              **({"budget": {"focus": [pop[d]["id"] for d in focus], "evaluated": bud_log}} if args.select_budget else {}),
                              **({"thompson": thompson_stats(pool, cands, fit_t, n_fit)}
                                 if args.thompson_share or args.thompson_bonus else {}),
                              **({"margin_w": args.select_margin} if args.select_margin else {}),
                              **({"card": {**{key: {str(i): int(v) for i, v in enumerate(np.atleast_1d(s)) if v}
                                              for key, s in led.items()}, "n_prop": len(prop), "n_acc": len(acc)}}
                                 if args.card_ledger else {})}
                cands, pairs = {}, {}                            # the checkpoint saves them together
                if args.select_retest:
                    retest = retest_next

            # 6. turnover
            turnover, type_sizes = [], None
            if args.turnover_every and (it + 1) % args.turnover_every == 0:
                score = np.array([mean_score(a, 0.5) for a in pop])
                order = np.argsort(score)
                top = order[-max(1, D // 4):]
                old = [d for d in order if it + 1 - pop[d]["born"] >= args.protect]    # --protect: the young stay
                if args.type_cap:                                # --type-cap: an overfull type's worst go first
                    kind_of, sizes = deck_kinds(pool, [a["deck"] for a in pop], score)
                    big = int(np.argmax(sizes))
                    type_sizes = sorted(sizes, reverse=True)[:8]
                    if sizes[big] > args.type_cap * D:
                        first = [d for d in old if kind_of[d] == big][:sizes[big] - int(args.type_cap * D)]
                        old = first + [d for d in old if d not in first]
                        rest = [d for d in order if kind_of[d] != big]
                        if rest:                                 # mutants of the other types' best quarter
                            top = np.array(rest[-max(1, len(rest) // 4):])
                for d in old[:int(round(args.turnover * D))]:
                    if args.turnover_mutant or rng.random() < MUTANT_SHARE:
                        p = int(rng.choice(top))
                        new = {"deck": random_changes(pool, pop[p]["deck"], MUTANT_CHANGES, rng), "parent": pop[p]["id"],
                               "kind": "mutant"}
                    else:
                        new = {"deck": (fresh_wide() if args.turnover_wide else random_deck(pool, rng)), "parent": None,
                               "kind": "wide" if args.turnover_wide else "random"}
                    turnover.append({"out": pop[d]["id"], "score": round(float(score[d]), 4), "in": next_id,
                                     "kind": new["kind"]})
                    pop[d] = {"id": next_id, "born": it + 1, "sum": 0.0, "n": 0, **new}
                    next_id += 1
                for a, sc in zip(pop, score):                    # a fresh window for everyone
                    if a["born"] <= it:
                        a["last"] = round(float(sc), 4)          # the window's result, for rl/evaluate_agents.py
                    a["sum"], a["n"] = 0.0, 0

            shapes = np.array([[s["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"]]
                               for s in (deck_shape(pool, a["deck"]) for a in pop)])
            best = [int(d) for d in np.argsort(-np.nan_to_num(z_iter, nan=-1))[:3]]
            cut = sum(1 for r in games if r["winner"] not in (1, 2))
            row = {"iter": it, "lam": round(lam, 5), "games": len(games), "errors": sum(1 for r in games if r.get("error")),
                   "cut_off": cut, "steps_per_game": round(float(np.mean([r["steps"] for r in games])), 1),
                   "endings": {e: sum(1 for r in games if (r.get("ending") or "none") == e) for e in {r.get("ending") or "none" for r in games}},
                   "recorded": recorded, "ppo": ppo, "draft": draft, "counted": counted,
                   **({"distill": distill} if distill is not None else {}),
                   **({"loop_search": {q: sum((rep.get("loopSearch") or {}).get(q, 0) for rep in replies)        # C138
                                       for q in ("decisions", "searched", "changed", "lines", "lineErrors", "capped")}}
                      if args.loop_search else {}),
                   **({"select": select} if select else {}),
                   **({"types": type_sizes} if type_sizes else {}),
                   **({"practice": {"games": len(practice), "errors": sum(1 for r in practice if r.get("error")),
                                    "steps_per_game": round(float(np.mean([r["steps"] for r in practice])), 1),
                                    **({"from_pop": n_pop} if args.practice_from_pop else {}),
                                    **({"focus": sorted(str(pool.name[c]) for c in p_focus)} if p_focus else {}),
                                    **({"curriculum": tp_used, "tplay": tplay} if args.practice_curriculum else {})}}
                      if practice else {}),
                   "margin_abs": round(float(np.mean([abs(m) for d in range(D) for m in per[d]["margin"]])), 4),
                   "shape_quartiles": {k: np.percentile(shapes[:, i], [25, 50, 75]).tolist()
                                       for i, k in enumerate(("pokemon", "trainer", "energy"))},
                   "z": [None if np.isnan(x) else round(float(x), 3) for x in z_iter],
                   "ids": [a["id"] for a in pop], "shapes": shapes.tolist(),
                   "best": [{"id": pop[d]["id"], "z": round(float(z_iter[d]), 3), "kind": pop[d]["kind"], "born": pop[d]["born"],
                             **deck_shape(pool, pop[d]["deck"]), **drafter.summary(views[d])} for d in best],
                   "turnover": turnover,
                   **({"table_head": table_head_share(views, table_bonus, table_top, np.asarray(pool.allowed, dtype=bool))} if table_bonus is not None else {}),
                   "head_mass": head_mass(views, card_kind, table_bonus),
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

            state = {"net": net.state_dict(), "opt": opt.state_dict(), "drafter": drafter.state(), "config": net.config(),
                     "population": [{**a, "deck": pool.names(a["deck"])} for a in pop], "next_id": next_id,
                     "iter": it, "round": it, "rng": rng.bit_generator.state, "deal_seed": deal_seed,
                     "season": {"cands": cands, "pairs": pairs,
                                **({"retest": {i: {"deck": pool.names(v["deck"]), "n": v["n"]} for i, v in retest.items()}}
                                   if args.select_retest else {}),
                                **({"thompson": thompson_hist} if args.thompson_share or args.thompson_bonus else {}),
                                **({"tplay": tplay} if args.practice_curriculum else {})},
                     "agents": [{"id": a["id"], "deck": pool.names(a["deck"])} for a in pop]}
            tmp = ckpt.with_suffix(".tmp")
            torch.save(state, tmp)
            os.replace(tmp, ckpt)
            if args.save_every and ((it + 1) % args.save_every == 0 or (args.save_first and it == 0)):
                torch.save({k: state[k] for k in ("net", "drafter", "config", "population", "agents", "iter", "round")},
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
