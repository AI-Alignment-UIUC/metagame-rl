"""Evaluation-only diagnostic: how transitive is a matchup matrix, what does Nash / alpha-Rank keep.

Reads a matrix.js-style JSON (wins[i][j] of deck i against deck j over gamesPerPair games).
Hodge split of the antisymmetric payoff A = P - 1/2 (Balduzzi et al. 2018): r = mean_j A_ij,
transitive part r_i - r_j, cyclic part the rest. Noise: each off-diagonal cell carries
p(1-p)/n binomial variance; its expected energy is reported so the cyclic share can be read
net of noise. Nash by LP (as rl/nash.py), max-entropy Nash by maximising entropy on the
equilibrium set, alpha-Rank (single population, Omidshafiei et al. 2019) by its Markov chain.
"""
import json
import sys

import numpy as np
from scipy.optimize import linprog, minimize


def load(path):
    d = json.load(open(path))
    W = np.array(d["wins"], dtype=float)
    n = d.get("gamesPerPair", 100)
    return d["decks"], W / n, n


def hodge(P, n_games, mask=None):
    A = (P - P.T) / 2.0                                   # antisymmetric part of P - 1/2
    k = len(A)
    off = ~np.eye(k, dtype=bool)
    r = A.mean(1) * k / (k - 1)                           # mean over opponents (diagonal is 0)
    G = r[:, None] - r[None, :]
    # least-squares gradient: r solves min ||A - (r_i - r_j)||, whose solution is r = A.1/k
    r_ls = A.sum(1) / k
    G = r_ls[:, None] - r_ls[None, :]
    C = A - G
    tot, tr, cy = (A[off] ** 2).sum(), (G[off] ** 2).sum(), (C[off] ** 2).sum()
    p = np.clip(P, 1e-3, 1 - 1e-3)
    noise = (p * (1 - p) / n_games)[off].sum()            # expected noise energy in A (both triangles)
    noise_cyc = noise * (1 - (k - 1) / (k * (k - 1) / 2)) # share of i.i.d. noise landing in the cyclic subspace
    return {"total": tot, "transitive_share": tr / tot, "cyclic_share": cy / tot,
            "noise_energy": noise, "cyclic_share_net_of_noise": max(cy - noise_cyc, 0) / max(tot - noise, 1e-9),
            "rating": r_ls}


def nash_lp(P):
    A = P - 0.5
    k = len(A)
    c = np.zeros(k + 1); c[-1] = -1
    A_ub = np.hstack([-A.T, np.ones((k, 1))])
    res = linprog(c, A_ub=A_ub, b_ub=np.zeros(k), A_eq=np.hstack([np.ones((1, k)), np.zeros((1, 1))]),
                  b_eq=[1.0], bounds=[(0, None)] * k + [(None, None)], method="highs")
    x = np.clip(res.x[:k], 0, None)
    return x / x.sum(), res.x[-1]


def nash_maxent(P, v, tol=1e-6):
    A = P - 0.5
    k = len(A)
    cons = [{"type": "eq", "fun": lambda x: x.sum() - 1.0},
            {"type": "ineq", "fun": lambda x: A.T @ x - v + tol}]   # every opponent column at least the value
    f = lambda x: np.sum(x * np.log(np.clip(x, 1e-12, None)))
    x0 = np.full(k, 1.0 / k)
    best = None
    for start in (x0, nash_lp(P)[0] * 0.9 + 0.1 / k):
        res = minimize(f, start, constraints=cons, bounds=[(0, 1)] * k, method="SLSQP", options={"maxiter": 2000, "ftol": 1e-12})
        if res.success and (best is None or res.fun < best.fun):
            best = res
    x = np.clip(best.x, 0, None) if best is not None else nash_lp(P)[0]
    return x / x.sum()


def alpha_rank(P, alpha, m=50):
    """Single-population alpha-Rank for a symmetric 2-player game with payoff M = P (win probability)."""
    M = P
    k = len(M)
    C = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            if i == j:
                continue
            # resident i, mutant j; fitness with l mutants
            s = 0.0
            prod = 1.0
            for l in range(1, m):
                f_mut = ((l - 1) * M[j, j] + (m - l) * M[j, i]) / (m - 1)
                f_res = (l * M[i, j] + (m - l - 1) * M[i, i]) / (m - 1)
                prod *= np.exp(-alpha * (f_mut - f_res))
                s += prod
                if prod > 1e300:
                    break
            rho = 1.0 / (1.0 + s)
            C[i, j] = rho / (k - 1)
        C[i, i] = 1.0 - C[i].sum()
    w, V = np.linalg.eig(C.T)
    pi = np.real(V[:, np.argmin(np.abs(w - 1))])
    pi = np.abs(pi) / np.abs(pi).sum()
    return pi


def sink_components(P, n_games, z=2.0):
    """Response graph with only resolved edges (|p - 1/2| > z SE): i -> j when j beats i. Sink SCCs."""
    k = len(P)
    se = np.sqrt(np.clip(P * (1 - P), 0.01, None) / n_games)
    E = (P.T - 0.5 > z * se)          # E[i, j]: j beats i, resolved
    np.fill_diagonal(E, False)
    # Tarjan-free: reachability by Floyd-Warshall on booleans
    R = E.copy()
    for t in range(k):
        R |= R[:, [t]] & R[[t], :]
    comp = {}
    for i in range(k):
        key = tuple(sorted([i] + [j for j in range(k) if R[i, j] and R[j, i]]))
        comp[key] = True
    sinks = []
    for c in comp:
        out = any(E[i, j] for i in c for j in range(k) if j not in c)
        if not out:
            sinks.append(list(c))
    return sinks, int(E.sum())


def eff(x):
    x = x[x > 1e-9]
    return float(np.exp(-(x * np.log(x)).sum()))


def main(path):
    names, P, n = load(path)
    arche = [s[s.rfind("(") + 1:-1] if "(" in s else s for s in names]
    print(f"{len(names)} decks, {n} games a pair; P + P^T - 1 max |dev| {np.abs(P + P.T - 1)[~np.eye(len(P), dtype=bool)].max():.3f}")
    h = hodge(P, n)
    print(f"Hodge: transitive share {h['transitive_share']:.3f}, cyclic {h['cyclic_share']:.3f}; noise energy "
          f"{h['noise_energy']:.3f} of total {h['total']:.3f}; cyclic share net of noise {h['cyclic_share_net_of_noise']:.3f}")
    x, v = nash_lp(P)
    print("LP Nash support:", [(names[i], round(float(x[i]), 3)) for i in np.argsort(-x) if x[i] > 1e-4], "value", round(v, 4))
    xm = nash_maxent(P, v)
    print("maxent Nash support:", [(names[i], round(float(xm[i]), 3)) for i in np.argsort(-xm) if xm[i] > 1e-3],
          "eff", round(eff(xm), 2))
    for a in (1, 10, 50):
        pi = alpha_rank(P, a)
        top = np.argsort(-pi)[:6]
        print(f"alpha-Rank alpha={a}: eff {eff(pi):.2f};", [(arche[i], round(float(pi[i]), 3)) for i in top])
    sinks, ne = sink_components(P, n)
    print(f"resolved edges (2 SE) {ne} of {len(P)*(len(P)-1)//2}; sink components:", [[names[i] for i in s] for s in sinks])
    # archetype-level matrix
    types = sorted(set(arche))
    T = np.array([[np.mean([P[i, j] for i in range(len(P)) for j in range(len(P)) if arche[i] == a and arche[j] == b and i != j])
                   if not (a == b and arche.count(a) == 1) else 0.5 for b in types] for a in types])
    np.fill_diagonal(T, 0.5)
    ht = hodge(T, n * 4)
    print("archetypes:", types)
    print(f"archetype-level Hodge: transitive share {ht['transitive_share']:.3f}; ratings",
          {t: round(float(r), 3) for t, r in zip(types, ht["rating"])})
    xt, vt = nash_lp(T)
    print("archetype LP Nash:", {types[i]: round(float(xt[i]), 3) for i in np.argsort(-xt) if xt[i] > 1e-4})


if __name__ == "__main__":
    main(sys.argv[1])
