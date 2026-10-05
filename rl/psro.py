"""PSRO with a deck-edit builder (plan items A5.1-A5.3).

Population: decks (archived lists, or random legal decks for a cold start). Each iteration:
  1. measure the matchup rows not yet played, with real games under the play policy
     (env/tools/matrix.js), and solve the meta game (rl/nash.py) -> mixture sigma
  2. refit the matchup model on every game played so far (rl/matchup.py)
  3. train the deck-edit builder against sigma and take its best novel proposals (rl/builder.py)
  4. pilot: fine-tune the play policy on games that include the new decks (rl/train.py)
  5. add the proposals to the population
Logged each iteration: the equilibrium support, each support deck's nearest archived list (by
card overlap) and that list's archetype label, population diversity.

Run (develop on the field's 56 cards, from the archived lists):
  .venv/Scripts/python -m rl.psro --run runs/a5-field --policy runs/a4/model_it00299.pt \
      --pool field --init archived --iterations 10
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import torch

from rl.builder import Builder
from rl.decks import Pool, archived_decks, overlap
from rl.matchup import MatchupModel, fit
from rl.nash import solve
from rl.crossplay import as_spec

ROOT = Path(__file__).resolve().parent.parent


def label_of(name: str) -> str:
    m = re.search(r"\(([^)]*)\)\s*$", name)
    return m.group(1) if m else name


def random_deck(pool: Pool, rng: np.random.Generator) -> np.ndarray:
    """A random legal deck with a plausible shape: 2-4 Pokemon lines, 16-22 basic Energy of
    their types, Trainers for the rest."""
    cards = pool.cards
    by_name = {}
    for c in cards:
        if pool.allowed[c["id"]]:
            by_name.setdefault(c["name"], c)
    basics = [c for c in by_name.values() if c["superType"] == 1 and c["stage"] == 2]
    evolutions = [c for c in by_name.values() if c["superType"] == 1 and c["stage"] in (3, 4)]
    trainers = [c for c in by_name.values() if c["superType"] == 2]
    energies = [c for c in cards if c["superType"] == 3 and c["energyType"] == 0 and pool.allowed[c["id"]]]
    v = np.zeros(pool.n, dtype=np.int32)
    types = set()
    for b in rng.choice(basics, size=rng.integers(2, 5), replace=False):
        v[b["id"]] += rng.integers(2, 5)
        types |= {i for i, x in enumerate(b["types"]) if x}
        evo = [e for e in evolutions if e["evolvesFrom"] == b["name"]]
        if evo and rng.random() < 0.6:
            e = evo[rng.integers(len(evo))]
            v[e["id"]] += rng.integers(1, 4)
    n_energy = int(rng.integers(16, 23))
    typed = [e for e in energies if any(e["provides"][t] for t in types)] or energies
    for _ in range(n_energy):
        v[typed[rng.integers(len(typed))]["id"]] += 1
    while v.sum() < 60:
        t = trainers[rng.integers(len(trainers))]
        if pool.name_counts(np.where(pool.basic_energy, 0, v))[pool.name_of[t["id"]]] < 4:
            v[t["id"]] += 1
    while v.sum() > 60:
        i = rng.choice(np.nonzero(v)[0])
        if not (pool.basic_pokemon[i] and v[pool.basic_pokemon].sum() <= 1):
            v[i] -= 1
    assert pool.legal(v), "random deck not legal"
    return v


class Population:
    def __init__(self, pool: Pool):
        self.pool = pool
        self.decks, self.names, self.origin = [], [], []
        self.wins = np.zeros((0, 0))
        self.games = np.zeros((0, 0))

    def add(self, v, name, origin):
        self.decks.append(v.astype(np.int32))
        self.names.append(name)
        self.origin.append(origin)
        n = len(self.decks)
        for k in ("wins", "games"):
            m = getattr(self, k)
            g = np.zeros((n, n))
            g[:m.shape[0], :m.shape[1]] = m
            setattr(self, k, g)

    def as_json(self):
        return [{"name": n, "cards": self.pool.names(v)} for n, v in zip(self.names, self.decks)]

    def measure(self, run: Path, policy_spec: str, games: int, workers: int, new: int, seed: int):
        """Plays the pairs not measured yet (those involving the last `new` decks, or all)."""
        decks_file = run / "population.json"
        decks_file.write_text(json.dumps(self.as_json()))
        out = run / "matrix_new.json"
        cmd = ["node", str(ROOT / "env/tools/matrix.js"), "--agent", policy_spec, "--decks-file", str(decks_file),
               "--games", str(games), "--workers", str(workers), "--seed", str(seed), "--out", str(out)]
        if new:
            cmd += ["--new", str(new)]
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        m = json.load(open(out))
        W, G = np.array(m["wins"]), np.array(m["games"])
        played = G > 0
        np.fill_diagonal(played, False)
        self.wins[played] = W[played]
        self.games[played] = G[played]
        np.fill_diagonal(self.wins, games / 2)
        np.fill_diagonal(self.games, games)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--policy", required=True, help="play policy checkpoint (.pt) or evaluate.js agent spec")
    ap.add_argument("--pool", choices=["field", "full"], default="field")
    ap.add_argument("--init", default="archived", help="archived | cold:<n> (n random legal decks)")
    ap.add_argument("--iterations", type=int, default=10)
    ap.add_argument("--games", type=int, default=100, help="games per pair")
    ap.add_argument("--new", type=int, default=4, help="decks added per iteration")
    ap.add_argument("--edits", type=int, default=16)
    ap.add_argument("--builder-iters", type=int, default=200)
    ap.add_argument("--pilot-iters", type=int, default=0, help="play-policy fine-tuning iterations per PSRO iteration")
    ap.add_argument("--workers", type=int, default=18)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args(argv)

    run = ROOT / args.run
    run.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    rng = np.random.default_rng(args.seed)
    table = json.load(open(ROOT / "notes/data/cards/pool.json", encoding="utf-8"))["cards"]
    text = np.load(ROOT / "notes/data/cards/text_emb.npy")
    archived = archived_decks(Pool())
    field = sorted({c for _, v in archived for c in Pool().names(v)})
    pool = Pool(restrict=field if args.pool == "field" else None)

    pop = Population(pool)
    if args.init == "archived":
        for name, v in archived:
            pop.add(v, name, "archived")
    else:
        for k in range(int(args.init.split(":")[1])):
            pop.add(random_deck(pool, rng), f"random-{k}", "random")
    policy = args.policy
    spec = as_spec(policy) if policy.endswith(".pt") else policy
    log = open(run / "log.jsonl", "a")

    def nearest(v):
        o = [overlap(v, a) for _, a in archived]
        k = int(np.argmax(o))
        return archived[k][0], label_of(archived[k][0]), round(o[k], 3)

    measured = 0
    for it in range(args.iterations):
        new = len(pop.decks) - measured
        pop.measure(run, spec, args.games, args.workers, new if measured else 0, args.seed * 1000 + it)
        measured = len(pop.decks)
        P = pop.wins / np.maximum(pop.games, 1)
        sigma, value = solve(P)
        support = [(i, float(sigma[i])) for i in np.argsort(-sigma) if sigma[i] > 1e-4]
        row = {"iteration": it, "population": len(pop.decks), "support": [
            {"deck": pop.names[i], "weight": round(w, 4), "origin": pop.origin[i], "nearest": nearest(pop.decks[i])}
            for i, w in support],
            "mean_overlap": float(np.mean([overlap(a, b) for i, a in enumerate(pop.decks) for b in pop.decks[i + 1:]]))}
        print(f"PSRO it {it}: population {len(pop.decks)}, support " + ", ".join(
            f"{pop.names[i][:28]} {w:.2f} [{row['support'][k]['nearest'][1]} {row['support'][k]['nearest'][2]:.2f}]"
            for k, (i, w) in enumerate(support[:8])), flush=True)

        D = np.stack(pop.decks).astype(np.float32)
        model = MatchupModel(table, text)
        row["matchup_fit"] = fit(model, D, pop.wins, pop.games, dev, holdout=0.1, seed=it)
        builder = Builder(pool, table, text, dev, steps=args.edits)
        Dt = torch.from_numpy(D)
        sig = torch.from_numpy(sigma.astype(np.float32))
        mix = 0.5 * sig + 0.5 / len(D)

        def starts(B):
            idx = torch.multinomial(mix, B, replacement=True)
            return Dt[idx].clone()

        blog = builder.train(model, starts, Dt, sig, iterations=args.builder_iters)
        row["builder"] = {"gain_first": blog[0]["gain"], "gain_last": blog[-1]["gain"], "score_last": blog[-1]["final_score"]}
        props = builder.propose(model, Dt[torch.argsort(sig, descending=True)[:8]], Dt, sig, k=args.new,
                                existing=pop.decks)
        for k, (v, score) in enumerate(props):
            pop.add(v, f"psro{it}-{k} ({nearest(v)[1]}-like)", f"builder it {it}, predicted {score:.3f}")
        row["proposals"] = [{"name": pop.names[-len(props) + k], "predicted": s, "nearest": nearest(v)}
                            for k, (v, s) in enumerate(props)]
        log.write(json.dumps(row) + "\n")
        log.flush()
        (run / "population.json").write_text(json.dumps(pop.as_json()))
        np.savez(run / "matrix.npz", wins=pop.wins, games=pop.games, names=np.array(pop.names))
        # Piloting (fine-tuning the play policy on the new decks) is run separately for now:
        # rl.train --init-from <policy> --matchups-file <new vs population>.
    log.close()


if __name__ == "__main__":
    main()
