"""X5 (log #234; runs/probe/X5-filler/record.md): what fills the cut Trainers? (evaluation only)

trainer_value.py's design (each list against a copy of itself with one group of its Trainers replaced, one pilot on both
seats, both seats, the same deals for every copy of a list) with three fillers for each of the search, disrupt and tempo
groups:
  E  the list's commonest basic Energy (trainer_value.py's and C59's filler)
  O  an off-type basic Energy: the lowest-id basic type that no attack of the list's Pokémon costs and no basic Energy of
     the list provides (attack costs from notes/data/cards/pool.json), so it pays only colorless costs and retreat
  D  Clefairy Doll BS (played as a 10 HP Basic with no attacks that can't retreat and gives no Prize; playable since
     #235), as many as the 4-copy limit allows, the rest O (the mix is in the output)
A list that gets nothing from its Trainers scores about 0.5 against its O and D copies; if an extra on-type Energy is what
the pilot overvalues, the list scores far lower against E than against O. The workers (env/tools/probe_filler_worker.js:
env/remote_worker.js plus a count of each deck's Energy attachments and Trainer plays by card) show whether the fillers
and the cut Trainers are played at all. The fillers come from a rule over card types, never a human statistic; nothing
here enters training.

Run: runs/probe/X5-filler/chain.sh
"""
import argparse
import collections
import json
import queue
import subprocess
import threading
from pathlib import Path

import numpy as np
import torch

from rl import limits
from rl.decks import MAX_COPIES, Pool, archived_decks
from rl.gpu_matrix import GpuMatrix, load_policy
from rl.remote import RemotePool
from rl.train import round_turns
from trainer_value import GROUPS, ROOT       # notes/scripts/ is on the path when this file runs

DOLL = "Clefairy Doll BS"
FILLS = ("E", "O", "D")


class FillerPool(RemotePool):
    """RemotePool with its workers on env/tools/probe_filler_worker.js: __init__ is RemotePool's with that path, and
    collect sums each reply's move counts into self.use ({deck name: Counter of "verb|card"})."""

    def __init__(self, n: int):
        self.procs = [subprocess.Popen(["node", str(ROOT / "env/tools/probe_filler_worker.js")], cwd=ROOT,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0) for _ in range(n)]
        self.q, self.mem, self.pace = queue.Queue(), {}, 0.0
        self.use = collections.defaultdict(collections.Counter)
        for i, p in enumerate(self.procs):
            threading.Thread(target=self._reader, args=(i, p), daemon=True).start()

    def collect(self, msgs, models, device):
        replies = super().collect(msgs, models, device)
        for r in replies:
            for deck, c in r.get("use", {}).items():
                self.use[deck].update(c)
        return replies


def off_type(card: dict, basics: dict, cards: list) -> str:
    """The basic Energy of the lowest-id type that no attack of the deck's Pokémon costs and no basic Energy in it gives."""
    used = {t for x in set(cards) if card[x]["superType"] == 1 for a in card[x]["attacks"]
            for t, k in enumerate(a["cost"]) if k and t}
    used |= {card[x]["provides"].index(1) for x in set(cards) if card[x]["superType"] == 3 and card[x]["energyType"] == 0}
    free = [t for t in sorted(basics) if t not in used]
    assert free, "every basic type is in use"
    return basics[free[0]]


def variants(pool: Pool, decks: list, groups: list) -> tuple:
    """[base decks] + each base's E, O and D copies of every group it plays; the pairs (base, variant, group, fill,
    replaced, the cards put in); and each list's E and O cards."""
    card = {c["fullName"]: c for c in pool.cards}
    basics = {c["provides"].index(1): c["fullName"] for c in pool.cards if c["superType"] == 3 and c["energyType"] == 0}
    out, pairs, fill = list(decks), [], {}
    for k, d in enumerate(decks):
        own = collections.Counter(x for x in d["cards"] if card[x]["superType"] == 3 and card[x]["energyType"] == 0)
        e, o = own.most_common(1)[0][0], off_type(card, basics, d["cards"])
        fill[d["name"]] = {"E": e, "O": o}
        dolls = MAX_COPIES - sum(card[x]["name"] == "Clefairy Doll" for x in d["cards"])
        for g in groups:
            hit = [i for i, x in enumerate(d["cards"]) if card[x]["name"] in GROUPS[g]]
            for f in FILLS if hit else ():
                cards = list(d["cards"])
                for n, i in enumerate(hit):
                    cards[i] = e if f == "E" else DOLL if f == "D" and n < dolls else o
                assert pool.legal(pool.vector(cards)), (d["name"], g, f)
                pairs.append({"base": k, "variant": len(out), "group": g, "fill": f, "replaced": len(hit),
                              "put_in": dict(collections.Counter(cards[i] for i in hit))})
                out.append({"name": f"{d['name']}-{f}-{g}", "cards": cards})
    return out, pairs, fill


def play(path: str, decks: list, pairs: list, games: int, seed: int, workers: int, device: str, rounds,
         pool_cls=FillerPool) -> tuple:
    """trainer_value.play_pilot on pool_cls's workers: (the list's score in each pair, the matrix's stats, move counts)."""
    model, _ = load_policy(path, device)
    rp = pool_cls(workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(model, rp, workers, device=device)
        W, G, _ = gm.play(decks, games, seed, pairs=[(p["base"], p["variant"]) for p in pairs],
                          pair_keys=[p["base"] for p in pairs], round_turns=rounds)
    finally:
        rp.close()
    rates = [float(W[p["base"], p["variant"]] / max(G[p["base"], p["variant"]], 1)) for p in pairs]
    return rates, gm.last, {k: dict(v) for k, v in getattr(rp, "use", {}).items()}


def mean_se(x) -> dict:
    x = np.asarray(x, dtype=float)
    se = float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else None
    return {"n": len(x), "mean": round(float(x.mean()), 4), "se": None if se is None else round(se, 4)}


def readout(pool: Pool, decks: list, pairs: list, rates: list, groups: list, fill: dict, games: int, use: dict) -> dict:
    """Scores by group and fill (mean over lists, SE over lists); the primary (per list the mean over its groups, then
    over lists) and its paired differences by list; the D copies' Doll / off-type mix; and, a game, the moves that use
    the fillers and the cut Trainers."""
    s = {(p["base"], p["group"], p["fill"]): r for p, r in zip(pairs, rates)}
    bases = sorted({p["base"] for p in pairs})
    by_group = {g: {f: mean_se([s[b, g, f] for b in bases if (b, g, f) in s]) for f in FILLS}
                for g in groups if any(p["group"] == g for p in pairs)}
    per_list = {f: np.array([np.mean([s[b, g, f] for g in groups if (b, g, f) in s]) for b in bases]) for f in FILLS}
    primary = {f: mean_se(per_list[f]) for f in FILLS}
    diffs = {f"{a}-{b}": mean_se(per_list[a] - per_list[b]) for a, b in (("O", "E"), ("D", "O"), ("D", "E"))}

    name = {c["fullName"]: c["name"] for c in pool.cards}
    n_games = collections.Counter()
    for p in pairs:
        n_games[decks[p["base"]]["name"]] += games
        n_games[decks[p["variant"]]["name"]] += games

    def a_game(deck, test):            # the deck's moves a game that pass test(verb, card)
        return sum(n for k, n in use.get(deck, {}).items() if test(*k.split("|", 1))) / max(n_games[deck], 1)

    avg = lambda xs: round(float(np.mean(xs)), 3)
    base, copy = (lambda p: decks[p["base"]]["name"]), (lambda p: decks[p["variant"]]["name"])
    mix, moves = {}, {}
    for g in by_group:
        gp = {f: [p for p in pairs if p["group"] == g and p["fill"] == f] for f in FILLS}
        dolls = [p["put_in"].get(DOLL, 0) for p in gp["D"]]
        mix[g] = {"replaced": avg([p["replaced"] for p in gp["D"]]), "doll": avg(dolls),
                  "off": avg([p["replaced"] - d for p, d in zip(gp["D"], dolls)])}
        attach = lambda deck, x: a_game(deck, lambda v, c: v == "attach" and c == x)
        moves[g] = {
            "list_plays_group_trainers": avg([a_game(base(p), lambda v, c: v == "trainer" and name.get(c) in GROUPS[g])
                                              for p in gp["E"]]),
            "list_attaches_E": avg([attach(base(p), fill[base(p)]["E"]) for p in gp["E"]]),
            "E_copy_attaches_E": avg([attach(copy(p), fill[base(p)]["E"]) for p in gp["E"]]),
            "O_copy_attaches_O": avg([attach(copy(p), fill[base(p)]["O"]) for p in gp["O"]]),
            "D_copy_attaches_O": avg([attach(copy(p), fill[base(p)]["O"]) for p in gp["D"]]),
            # tip| keys name the card ("tip|Clefairy Doll|A", env/legal.js), trainer| keys its fullName
            "D_copy_plays_doll": avg([a_game(copy(p), lambda v, c: v == "trainer" and name.get(c, c) == "Clefairy Doll")
                                      for p in gp["D"]]),
            "D_copy_discards_doll": avg([a_game(copy(p), lambda v, c: v == "tip" and name.get(c, c) == "Clefairy Doll")
                                         for p in gp["D"]]),
        }
    return {"primary": primary, "diffs": diffs, "by_group": by_group, "mix": mix, "moves_a_game": moves}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--player", default="runs/pilot/C49-sd/model_it00199.pt", help="the pilot on both seats (default X5's)")
    ap.add_argument("--groups", nargs="+", default=["search", "disrupt", "tempo"])
    ap.add_argument("--lists", type=int, default=0, help="the first N archived lists only (smoke tests); 0: all 24")
    ap.add_argument("--games", type=int, default=32, help="games per pair (both seats)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=92)
    ap.add_argument("--round-turns", default="20-45", help='the 2000 round rule, "T" or "A-B" (log #160); "0" off; '
                    'default X5\'s 20-45, unlike trainer_value.py')
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    workers = limits.cap_workers(args.workers)
    limits.apply(device, workers)
    pool = Pool()
    decks = [{"name": n, "cards": pool.names(v)} for n, v in archived_decks(pool)][:args.lists or None]
    alld, pairs, fill = variants(pool, decks, args.groups)
    rates, last, use = play(args.player, alld, pairs, args.games, args.seed, workers, device,
                            round_turns(args.round_turns))
    res = readout(pool, alld, pairs, rates, args.groups, fill, args.games, use)
    print("games", json.dumps(last), flush=True)
    for k in ("primary", "diffs", "by_group", "mix", "moves_a_game"):
        print(k, json.dumps(res[k]), flush=True)
    if args.out:
        Path(ROOT / args.out).write_text(json.dumps({
            "player": args.player, "games": args.games, "seed": args.seed, "round_turns": args.round_turns,
            "workers": workers, "device": device, "stats": last, **res, "fill": fill, "pairs": pairs,
            "per_pair": [round(r, 4) for r in rates], "use": use}, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
