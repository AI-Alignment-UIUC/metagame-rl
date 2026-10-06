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
import sys
import time
from pathlib import Path

import numpy as np
import torch

from rl import limits
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

    def measure(self, run: Path, policy_spec: str, games: int, workers: int, new: int, seed: int, gpu=None):
        """Plays the pairs not measured yet (those involving the last `new` decks, or all), with
        `gpu` (rl/gpu_matrix.GpuMatrix) if given, else with env/tools/matrix.js on CPU workers."""
        decks_file = run / "population.json"
        decks_file.write_text(json.dumps(self.as_json()))
        if gpu is not None:
            W, G, _ = gpu.play(self.as_json(), games, seed, new)
            self._merge(W, G, games)
            return gpu.last
        out = run / "matrix_new.json"
        cmd = ["node", str(ROOT / "env/tools/matrix.js"), "--agent", policy_spec, "--decks-file", str(decks_file),
               "--games", str(games), "--workers", str(workers), "--seed", str(seed), "--out", str(out)]
        if new:
            cmd += ["--new", str(new)]
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        m = json.load(open(out))
        self._merge(np.array(m["wins"]), np.array(m["games"]), games)

    def _merge(self, W, G, games):
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
    ap.add_argument("--builder", choices=["edit", "games", "model", "value", "strength"], default="edit",
                    help="edit: the PPO edit policy (rl/builder.py); games / model / value / strength: restart search "
                         "(rl/search.py) scored by real games, a matchup-model ensemble, the pilot's value, or the deck-strength model (log #39)")
    ap.add_argument("--search-seconds", type=float, default=120, help="wall-clock budget per search (rl/search.py)")
    ap.add_argument("--search-temperature", type=float, default=0.0,
                    help="sample climb steps, finalists and proposals from softmax(score / T) (0: greedy)")
    ap.add_argument("--strength-model", default="notes/data/eval/strength_model.json",
                    help="--builder strength: the deck-strength model (notes/scripts/deck_strength.py)")
    ap.add_argument("--edits", type=int, default=16)
    ap.add_argument("--builder-iters", type=int, default=200)
    ap.add_argument("--pilot-iters", type=int, default=0,
                    help="play-policy fine-tuning (PPO) iterations per PSRO iteration on games with the new decks; "
                         "the whole matrix is then re-measured under the new pilot (log #40)")
    ap.add_argument("--pilot-deckout-win", type=float, default=0.0, help="rl.train --deckout-win for the piloting step")
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--inference", choices=["gpu", "cpu"], default="gpu",
                    help="matrix games with central GPU inference (rl/gpu_matrix.py) or CPU ONNX workers (matrix.js)")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args(argv)

    run = ROOT / args.run
    run.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    limits.apply(dev, args.workers)
    rng = np.random.default_rng(args.seed)
    srng = np.random.default_rng(args.seed + 7)       # the search's own, so every builder starts from the same decks
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
    spec = as_spec(policy) if policy.endswith(".pt") and args.inference == "cpu" else policy
    gpu = None
    if args.inference == "gpu":
        from rl.gpu_matrix import GpuMatrix
        gpu = GpuMatrix(policy, args.workers)
    log = open(run / "log.jsonl", "a")

    def nearest(v):
        o = [overlap(v, a) for _, a in archived]
        k = int(np.argmax(o))
        return archived[k][0], label_of(archived[k][0]), round(o[k], 3)

    if args.builder != "edit" and gpu is None:
        raise SystemExit("--builder games/model/value needs --inference gpu")
    scorer = None
    if args.builder != "edit":
        from rl.search import GamesScorer, ModelScorer, StrengthScorer, ValueScorer
        scorer = {"games": lambda: GamesScorer(gpu), "value": lambda: ValueScorer(gpu),
                  "model": lambda: ModelScorer(table, text, dev),
                  "strength": lambda: StrengthScorer(gpu, str(ROOT / args.strength_model))}[args.builder]()
    pending = []                                   # (deck index, predicted score, sigma at proposal)
    measured = 0

    def pilot(it, new_idx, support):
        """Piloting (A5, "pressure flows down"): fine-tune the play policy on the new decks against
        the support and on the support among itself, then reload the GPU matrix with it. Returns
        the log entry; the caller re-measures the whole matrix under the new pilot."""
        nonlocal policy, gpu
        t0 = time.time()
        d = lambda i: {"name": pop.names[i], "cards": pool.names(pop.decks[i])}
        sup = support[:6]
        matchups = [[d(a), d(b)] for a in new_idx for b in sup] + [[d(b), d(a)] for a in new_idx for b in sup] +                    [[d(a), d(b)] for a in sup for b in sup]
        others = [i for i in range(len(pop.decks)) if i not in new_idx and i not in sup]
        for a, b in rng.choice(others, size=(min(8, len(others) // 2), 2), replace=False).tolist() if len(others) >= 2 else []:
            matchups.append([d(a), d(b)])
        out = f"{args.run}/pilot/it{it:02d}"
        (ROOT / out).mkdir(parents=True, exist_ok=True)
        (ROOT / out / "matchups.json").write_text(json.dumps(matchups))
        gpu.close()                                # the trainer's workers take the CPU budget meanwhile
        torch.cuda.empty_cache()                   # and the card: two processes, one 16 GB GPU
        cmd = [sys.executable, "-m", "rl.train", "--run", out, "--matchups-file", f"{out}/matchups.json",
               "--iterations", str(args.pilot_iters), "--transitions", "4096", "--concurrency", "48",
               "--inference", "gpu", "--model", "tokens", "--micro-batch", "1024", "--amp",
               "--init-from", policy, "--deckout-win", str(args.pilot_deckout_win),
               "--snapshot-every", str(args.pilot_iters), "--seed", str(args.seed * 100 + it)]
        with open(ROOT / out / "train.log", "w") as f:
            subprocess.run(cmd, cwd=ROOT, check=True, stdout=f, stderr=subprocess.STDOUT)
        for f in (ROOT / out).glob("rollout_w*.bin"):
            f.unlink()                             # ~10 MB each, not needed after training
        policy = f"{out}/model_it{args.pilot_iters - 1:05d}.pt"
        from rl.gpu_matrix import GpuMatrix
        gpu = GpuMatrix(policy, args.workers)
        if scorer is not None and hasattr(scorer, "gm"):
            scorer.gm = gpu
        rows = [json.loads(l) for l in open(ROOT / out / "log.jsonl") if '"endings"' in l]
        e = rows[-1]["endings"] if rows else {}
        return {"policy": policy, "matchups": len(matchups), "seconds": round(time.time() - t0, 1),
                "deck_out_share_last": round(e.get("deck-out", 0) / max(sum(e.values()), 1), 3)}

    for it in range(args.iterations + 1):
        new = len(pop.decks) - measured
        t0 = time.time()
        speed = pop.measure(run, spec, args.games, args.workers, new if measured else 0, args.seed * 1000 + it, gpu)
        measured = len(pop.decks)
        t_games = time.time() - t0
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
        # How well each proposal's predicted score matched its real win rate against the mixture it
        # was built for, now that its games are in.
        if pending:
            # predicted: the score it was chosen on (confirmation games for model/value); scorer: the
            # scorer's own estimate (the model's mean, without the optimism bonus)
            row["realized"] = [{"deck": pop.names[i], "predicted": round(p, 4), "scorer": round(o, 4),
                                "real": round(float((P[i, :len(sg)] * sg).sum()), 4)} for i, p, o, sg in pending]
            pending = []
        row["games"] = speed
        row["seconds"] = {"games": round(t_games, 1)}
        if it == args.iterations:                  # the last proposals measured; no new search
            log.write(json.dumps(row) + "\n")
            break
        t0 = time.time()

        if scorer is not None:
            from rl.search import search
            confirm = None if args.builder == "games" else GamesScorer(gpu)
            props, info = search(scorer, pop, sigma, args.new, args.search_seconds, srng,
                                 lambda pl, r: random_deck(pl, r), confirm=confirm,
                                 temperature=args.search_temperature)
            row["search"] = {k: v for k, v in info.items() if k != "runs"}
            row["search_runs"] = info["runs"]
            row["seconds"]["search"] = round(time.time() - t0, 1)
            for k, (v, score, raw) in enumerate(props):
                pop.add(v, f"{args.builder}{it}-{k} ({nearest(v)[1]}-like)", f"{args.builder} it {it}, predicted {score:.3f}")
                own = float(scorer.mean([v])[0]) if args.builder == "model" else raw
                pending.append((len(pop.decks) - 1, score, own, sigma.copy()))
            row["proposals"] = [{"name": pop.names[-len(props) + k], "predicted": round(s, 4), "scorer": round(r, 4),
                                 "energy": int(v[[c["id"] for c in table if c["superType"] == 3]].sum()),
                                 "nearest": nearest(v)} for k, (v, s, r) in enumerate(props)]
            if args.pilot_iters and props:
                row["pilot"] = pilot(it, list(range(len(pop.decks) - len(props), len(pop.decks))), [i for i, _ in support])
                measured = 0                       # the pilot changed: re-measure every pair
                print(f"  pilot: {row['pilot']}", flush=True)
            print(f"  search: {info['searches']} searches, {info['candidates_scored']} candidates, "
                  f"{len(props)} proposals in {info['seconds']} s", flush=True)
            log.write(json.dumps(row) + "\n")
            log.flush()
            (run / "population.json").write_text(json.dumps(pop.as_json()))
            np.savez(run / "matrix.npz", wins=pop.wins, games=pop.games, names=np.array(pop.names))
            continue

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
        row["seconds"]["model_and_builder"] = round(time.time() - t0, 1)
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
    (run / "population.json").write_text(json.dumps(pop.as_json()))
    np.savez(run / "matrix.npz", wins=pop.wins, games=pop.games, names=np.array(pop.names))
    if gpu is not None:
        gpu.close()


if __name__ == "__main__":
    main()
