"""How much does a deck-strength model weight each kind of input, and how few games do its game
statistics need? (logs #38-39)

No opponent context: the target is a deck's win rate against the 24 archived lists. Decks: every
deck of 2000s result #1's three runs plus the archived lists themselves, each playing the archived
field (--games per pair, alternating seats). Alternate pairs of games (both seats) give the target;
the game statistics and the in-play value come from --stat-games of the others, so no input is
computed from the games it predicts. Log #36's Trainer variants (and Graham's list) are held out.
Features: rl/strength.py (shape, goldfish, game_stats, value, uncertainty).

Importance: each group's summed |weight|, and on held-out decks (5 folds) the fit with each group
dropped and alone. The model fitted with --save-stat-games statistics is saved for the search
(rl/search.py StrengthScorer).

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/deck_strength.py --json notes/data/eval/deck_strength.json
"""
import argparse
import json

import numpy as np
import torch

from rl.decks import Pool, archived_decks
from rl.gpu_matrix import GpuMatrix
from rl.strength import GROUPS, NAMES, StrengthModel, deck_features, distance_to_nearest, game_features

RUNS = ["games", "model", "value"]
VARIANT_REAL = [0.499, 0.576, 0.632, 0.681]      # log #36


def fit_logistic(X, w, g, l2=1e-3, steps=600):
    """Binomial logistic regression with an intercept: wins w out of g games."""
    X = torch.tensor(X, dtype=torch.float64)
    w = torch.tensor(w, dtype=torch.float64)
    g = torch.tensor(g, dtype=torch.float64)
    beta = torch.zeros(X.shape[1] + 1, dtype=torch.float64, requires_grad=True)
    opt = torch.optim.LBFGS([beta], max_iter=steps, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        z = X @ beta[1:] + beta[0]
        loss = -(w * torch.nn.functional.logsigmoid(z) + (g - w) * torch.nn.functional.logsigmoid(-z)).sum() / g.sum()
        loss = loss + l2 * (beta[1:] ** 2).sum()
        loss.backward()
        return loss
    opt.step(closure)
    return beta.detach().numpy()


def predict(beta, X):
    return 1 / (1 + np.exp(-(X @ beta[1:] + beta[0])))


def spearman(a, b):
    r = lambda x: np.argsort(np.argsort(x))
    return float(np.corrcoef(r(np.asarray(a)), r(np.asarray(b)))[0, 1])


def swap(cards, out, add):
    cards = list(cards)
    for nm, k in out:
        for _ in range(k):
            cards.remove(nm)
    return cards + [nm for nm, k in add for _ in range(k)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/2000s-result-1/data")
    ap.add_argument("--policy", default="results/2000s-result-1/pilot/model_it00014.pt")
    ap.add_argument("--games", type=int, default=24, help="per pair against each archived list; half target, half statistics")
    ap.add_argument("--stat-games", default="8,16,32,all", help="statistics from this many games per deck")
    ap.add_argument("--save-stat-games", default="16")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--save-model", default="notes/data/eval/strength_model.json")
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    pool = Pool()
    rng = np.random.default_rng(0)
    arch = [{"name": n, "cards": pool.names(v)} for n, v in archived_decks(pool)]
    seen, decks, built = set(), [], None
    for r in RUNS:
        for d in json.load(open(f"{args.results}/{r}/population.json", encoding="utf-8")):
            k = tuple(sorted(d["cards"]))
            if k not in seen:
                seen.add(k); decks.append({"name": f"{r}: {d['name']}", "cards": d["cards"]})
            if d["name"].startswith("value5-0"):
                built = d["cards"]
    graham = [d for d in arch if "Graham" in d["name"]][0]["cards"]
    variants = [built,
                swap(built, [("Lightning Energy BS", 6)], [("PlusPower BS", 3), ("Gust of Wind BS", 2), ("Professor Oak BS", 1)]),
                swap(built, [("Lightning Energy BS", 12)], [("PlusPower BS", 3), ("Gust of Wind BS", 2), ("Scoop Up BS", 2),
                     ("Energy Retrieval BS", 2), ("Professor Oak BS", 1), ("Super Energy Removal BS", 1), ("Scyther JU", 1)]),
                graham]
    train = [d for d in decks if tuple(sorted(d["cards"])) != tuple(sorted(built))] + \
            [{"name": "archived: " + d["name"], "cards": d["cards"]} for d in arch if "Graham" not in d["name"]]
    subjects = train + [{"name": f"variant-{k}", "cards": c} for k, c in enumerate(variants)]
    S, A, T = len(subjects), len(arch), len(train)
    all_decks = subjects + arch
    pairs = [(s, S + a) for s in range(S) for a in range(A) if subjects[s]["cards"] != arch[a]["cards"]]

    gm = GpuMatrix(args.policy, 14)
    try:
        gm.play(all_decks, args.games, 23, pairs=pairs, value_at_turn=5)
        games, speed = gm.results, gm.last
        v0 = gm.values(all_decks, pairs, 8, 31)
        v1 = gm.values(all_decks, [(b, a) for a, b in pairs], 8, 32)
    finally:
        gm.close()
    vstart = np.zeros(S); vcount = np.zeros(S)
    for (s, _), x, y in zip(pairs, v0, v1):
        vstart[s] += (x - y) / 2; vcount[s] += 1
    vstart /= np.maximum(vcount, 1)

    win, n = np.zeros(S), np.zeros(S)
    stat_pool = [[] for _ in range(S)]
    for r in games:
        s = r["i"]
        if (r["seed"] // 2) % 2 == 0:              # pairs of games, so both halves get both seats
            win[s] += 1.0 if r["winner"] == r["iSeat"] else 0.0 if r["winner"] in (1, 2) else 0.5
            n[s] += 1
        else:
            stat_pool[s].append(r)
    y = win / np.maximum(n, 1)
    vecs = [pool.vector(d["cards"]) for d in subjects]
    static = [deck_features(pool, v, rng) for v in vecs]
    dist = [distance_to_nearest(vecs[s], [vecs[t] for t in range(T) if t != s]) for s in range(S)]

    def features(k):
        out = []
        for s in range(S):
            sample = stat_pool[s] if k == "all" else [stat_pool[s][i] for i in rng.permutation(len(stat_pool[s]))[:int(k)]]
            out.append({**static[s], **game_features(sample, s), "value_start": vstart[s], "distance_to_nearest": dist[s]})
        return out

    res = {"train_decks": T, "games": speed, "target_games_per_deck": round(float(n[:T].mean()), 1),
           "target_sd": round(float(y[:T].std()), 3), "by_stat_games": {}}
    for k in args.stat_games.split(","):
        F = features(k)
        X = np.array([[f[c] for c in NAMES] for f in F])
        mu, sd = X[:T].mean(0), X[:T].std(0) + 1e-9
        Z = (X - mu) / sd

        def cv(groups):
            idx = [NAMES.index(f) for g in groups for f in GROUPS[g]]
            p = np.zeros(T)
            for f in np.array_split(np.random.default_rng(1).permutation(T), args.folds):
                tr = np.setdiff1d(np.arange(T), f)
                p[f] = predict(fit_logistic(Z[tr][:, idx], win[tr], n[tr]), Z[f][:, idx])
            return {"mae": round(float(np.abs(p - y[:T]).mean()), 4), "spearman": round(spearman(p, y[:T]), 3)}

        groups = list(GROUPS)
        cvs = {"all": cv(groups), **{f"without {g}": cv([h for h in groups if h != g]) for g in groups},
               **{f"only {g}": cv([g]) for g in groups}}
        beta = fit_logistic(Z[:T], win[:T], n[:T])
        pv = predict(beta, Z[T:])
        weights = {f: round(float(b), 3) for f, b in zip(NAMES, beta[1:])}
        res["by_stat_games"][k] = {
            "cv": cvs, "weights": weights,
            "group_weight": {g: round(float(sum(abs(weights[f]) for f in GROUPS[g])), 3) for g in groups},
            "variants": {"predicted": np.round(pv, 3).tolist(), "real": np.round(y[T:], 3).tolist(),
                         "spearman": round(spearman(pv, y[T:]), 3)}}
        print(f"stat games {k}: all MAE {cvs['all']['mae']:.3f} rank {cvs['all']['spearman']:+.2f} | only game_stats "
              f"{cvs['only game_stats']['mae']:.3f} {cvs['only game_stats']['spearman']:+.2f} | without game_stats "
              f"{cvs['without game_stats']['mae']:.3f} {cvs['without game_stats']['spearman']:+.2f} | variants "
              f"{res['by_stat_games'][k]['variants']['predicted']} rank {res['by_stat_games'][k]['variants']['spearman']:+.2f}", flush=True)
        if k == args.save_stat_games:
            StrengthModel(NAMES, mu, sd, beta).save(args.save_model)
            res["saved_model"] = {"path": args.save_model, "stat_games": k}
    res["constant_mae"] = round(float(np.abs(y[:T].mean() - y[:T]).mean()), 4)
    np.savez("notes/data/eval/deck_strength_data.npz", names=np.array([d["name"] for d in subjects]), win=win, n=n,
             value_start=vstart, distance=np.array(dist))
    print(f"constant MAE {res['constant_mae']}, target sd {res['target_sd']}, {res['target_games_per_deck']} target games per deck")
    if args.json:
        json.dump(res, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
