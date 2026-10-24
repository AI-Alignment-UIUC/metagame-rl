"""Judge fidelity on the human field (log #149, the JF2 check of notes/method.md): does a judge's equilibrium over the 24
STS 2000 lists look like the real field? Evaluation only; the lists never enter training.

Input: matchup matrices of the 24 lists (rl/gpu_matrix.py --decks-file runs/probe/archived.json, the lists in
notes/data/2000-super-trainer-showdown-california/decks.csv order). For each matrix it prints the archetype shares of
the Nash equilibrium (unstable at 32 games a pair, so with a binomial bootstrap) and of the logit equilibrium (QRE) over
a range of temperatures, against the field's shares (Wigglytuff 10, Haymaker 7, Sponge 2, five singles), as a
total-variation distance, plus the pairwise agreement of the judges.

  .venv/Scripts/python -m rl.gpu_matrix --policy runs/pilot-v2/model_it00349.pt --decks-file runs/probe/archived.json \
      --games 32 --workers 6 --out runs/probe/jf2_human24_v2.json
  .venv/Scripts/python notes/scripts/judge_fidelity.py notes/data/eval/matrix_simplebot.json runs/probe/jf2_human24_v2.json
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.nash import solve  # noqa: E402

DECKS = ROOT / "notes/data/2000-super-trainer-showdown-california/decks.csv"


def field():
    labels = [r["label"] for r in csv.DictReader(open(DECKS, encoding="utf-8"))]
    names = sorted(set(labels), key=lambda l: -labels.count(l))
    return labels, names, np.array([labels.count(l) / len(labels) for l in names])


def matrix(path: str):
    """Win rates W[i][j] of list i against list j, made exactly zero-sum (draws and cut games count half, as matrix.js)."""
    m = json.load(open(path))
    wins, games = np.array(m["wins"], float), np.array(m["games"], float)
    W = np.where(games > 0, wins / np.maximum(games, 1), 0.5)
    W = (W + (1 - W.T)) / 2
    np.fill_diagonal(W, 0.5)
    return m, wins, games, W


def qre(W: np.ndarray, lam: float, iters: int = 6000) -> np.ndarray:
    """The logit (quantal response) equilibrium at temperature 1 / lam, by damped iteration."""
    x = np.ones(len(W)) / len(W)
    for _ in range(iters):
        u = (W - 0.5) @ x
        y = np.exp(lam * (u - u.max()))
        x = 0.9 * x + 0.1 * y / y.sum()
    return x


def shares(x, labels, names):
    return np.array([sum(x[i] for i in range(len(labels)) if labels[i] == l) for l in names])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("matrices", nargs="+")
    ap.add_argument("--boot", type=int, default=200, help="bootstrap redraws of each pair's games")
    ap.add_argument("--lams", default="5,10,20,40,80")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    labels, names, real = field()
    rng = np.random.default_rng(a.seed)
    lams = [float(x) for x in a.lams.split(",")]
    Ws = {}
    for path in a.matrices:
        m, wins, games, W = matrix(path)
        assert len(W) == len(labels), "the matrix must hold the 24 lists in decks.csv order"
        Ws[path] = W
        x, _ = solve(W)
        tv = []
        for _ in range(a.boot):
            p = np.clip(wins / np.maximum(games, 1), 0, 1)
            Wb = np.where(games > 0, rng.binomial(games.astype(int), p) / np.maximum(games, 1), 0.5)
            Wb = (Wb + (1 - Wb.T)) / 2
            np.fill_diagonal(Wb, 0.5)
            tv.append(0.5 * np.abs(shares(solve(Wb)[0], labels, names) - real).sum())
        print(f"\n== {m.get('agent', path)} ({path}), {m.get('gamesPerPair')} games a pair")
        print(f"   Nash: TV {0.5 * np.abs(shares(x, labels, names) - real).sum():.3f}; bootstrap median "
              f"{np.median(tv):.3f} [{np.percentile(tv, 5):.3f}, {np.percentile(tv, 95):.3f}]")
        row = []
        for lam in lams:
            s = shares(qre(W, lam), labels, names)
            row.append(f"lam {lam:g}: TV {0.5 * np.abs(s - real).sum():.3f} (top two {s[0] + s[1]:.2f})")
        print("   QRE: " + "; ".join(row))
        s20 = shares(qre(W, 20.0), labels, names)
        for k, l in enumerate(names):
            print(f"   {l[:30]:30s} field {real[k]:.3f}  QRE(20) {s20[k]:.3f}")
    keys = list(Ws)
    iu = np.triu_indices(len(labels), 1)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            r = np.corrcoef(Ws[keys[i]][iu], Ws[keys[j]][iu])[0, 1]
            print(f"pairwise win-rate correlation {keys[i]} vs {keys[j]}: {r:+.3f}")


if __name__ == "__main__":
    main()
