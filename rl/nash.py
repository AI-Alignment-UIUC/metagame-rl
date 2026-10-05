"""Nash equilibrium of a symmetric two-player zero-sum meta game (plan items A2, A5.1).

Input: a matchup matrix from env/tools/matrix.js (wins[i][j] of deck i against deck j). The
payoff of picking deck i against deck j is its win rate minus one half; the game is symmetric,
so its value is 0 and the equilibrium mixture x solves
    max_x min_j sum_i x_i (W[i][j] - 1/2)   subject to x >= 0, sum x = 1,
a linear program. Prints the support, and how far each deck is from the equilibrium.

Run: .venv/Scripts/python -m rl.nash notes/data/eval/matrix_simplebot.json [--json out.json]
"""
import argparse
import json

import numpy as np
from scipy.optimize import linprog


def solve(W: np.ndarray):
    n = len(W)
    A = W - 0.5
    # variables: x_1..x_n, v ; maximize v  ->  minimize -v
    c = np.zeros(n + 1)
    c[-1] = -1
    # v - sum_i x_i A[i][j] <= 0 for every j
    A_ub = np.hstack([-A.T, np.ones((n, 1))])
    b_ub = np.zeros(n)
    A_eq = np.hstack([np.ones((1, n)), np.zeros((1, 1))])
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=[1.0],
                  bounds=[(0, None)] * n + [(None, None)], method="highs")
    if not res.success:
        raise RuntimeError(res.message)
    x = np.clip(res.x[:n], 0, None)
    return x / x.sum(), res.x[-1]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("matrix")
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    m = json.load(open(args.matrix))
    W = np.array(m["wins"], dtype=float) / np.array(m["games"], dtype=float)
    x, v = solve(W)
    vs_eq = (W - 0.5) @ x          # each deck's edge against the equilibrium mixture
    order = np.argsort(-x)
    print(f"{m['agent']} matrix, {len(W)} decks, {m['gamesPerPair']} games per pair; game value {v:+.4f}")
    print("equilibrium support:")
    for i in order:
        if x[i] > 1e-6:
            print(f"  {x[i]:6.3f}  {m['decks'][i]}")
    print("edge against the equilibrium (win rate - 0.5), best first:")
    for i in np.argsort(-vs_eq)[:10]:
        print(f"  {vs_eq[i]:+.3f}  {m['decks'][i]}")
    mean = (W - 0.5).mean(axis=1)
    print("mean win rate against the field (uniform), best first:")
    for i in np.argsort(-mean)[:8]:
        print(f"  {0.5 + mean[i]:.3f}  {m['decks'][i]}")
    if args.json:
        json.dump({"decks": m["decks"], "mixture": x.tolist(), "value": v, "edge": vs_eq.tolist()}, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
