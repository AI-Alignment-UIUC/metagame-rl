"""How much does a deck-strength model weight each kind of input? (log #38)

No opponent context: the target is a deck's win rate against the 24 archived lists. Decks: every
deck of 2000s result #1's three runs plus the archived lists themselves, each playing the archived
field (--games per pair, alternating seats). Alternate pairs of games (both seats) give the target;
the others give the game statistics and the in-game value, so no input is computed
from the games it predicts. Log #36's Trainer variants (and Graham's list) are held out.

Input groups (standardized; a logistic model on the win rate, so weights are comparable):
  shape        counts of basic / special Energy, Pokémon, Basics, Trainers, draw cards; Energy fit
  goldfish     the chance a Basic can pay its cheapest attack by turn 2 / 3; Energy in the first 10 cards
  game_stats   turns per game, decisions per game, share of games ending by deck-out / no Pokémon
  value        the pilot's value at the start (both seat orders, 8 deals) and at game turn 5 (in play)
  uncertainty  cards changed from the nearest other deck in the data (how novel the deck is)

Importance: each group's summed |weight|, and on held-out decks (5 folds) the fit with the group
dropped and with the group alone.

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/deck_strength.py --json notes/data/eval/deck_strength.json
"""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import torch

from rl.decks import DECK_SIZE, Pool, archived_decks
from rl.gpu_matrix import GpuMatrix

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("matchup_ablation", HERE / "matchup_ablation.py")
ma = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ma)

GROUPS = {
    "shape": ["basic_energy", "special_energy", "pokemon", "basic_pokemon", "trainers", "draw", "energy_fit"],
    "goldfish": ["attack_by_t2", "attack_by_t3", "energy_in_first_10"],
    "game_stats": ["turns", "decisions", "deck_out_share", "no_pokemon_share"],
    "value": ["value_start", "value_turn5"],
    "uncertainty": ["distance_to_nearest"],
}
NAMES = [f for g in GROUPS.values() for f in g]


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


def deviance(p, w, g):
    p = p.clip(1e-6, 1 - 1e-6)
    return float(-(w * np.log(p) + (g - w) * np.log(1 - p)).sum() / g.sum())


def spearman(a, b):
    r = lambda x: np.argsort(np.argsort(x))
    return float(np.corrcoef(r(np.asarray(a)), r(np.asarray(b)))[0, 1])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/2000s-result-1/data")
    ap.add_argument("--policy", default="results/2000s-result-1/pilot/model_it00014.pt")
    ap.add_argument("--games", type=int, default=40, help="per pair against each archived list; half target, half stats")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    pool = Pool()
    rng = np.random.default_rng(0)
    arch = [{"name": n, "cards": pool.names(v)} for n, v in archived_decks(pool)]
    built = None
    seen, decks = set(), []
    for r in ma.RUNS:
        for d in json.load(open(f"{args.results}/{r}/population.json", encoding="utf-8")):
            k = tuple(sorted(d["cards"]))
            if k not in seen:
                seen.add(k); decks.append({"name": f"{r}: {d['name']}", "cards": d["cards"]})
            if d["name"].startswith("value5-0"):
                built = d["cards"]
    graham = [d for d in arch if "Graham" in d["name"]][0]["cards"]
    variants = [built,
                ma_swap(built, [("Lightning Energy BS", 6)], [("PlusPower BS", 3), ("Gust of Wind BS", 2), ("Professor Oak BS", 1)]),
                ma_swap(built, [("Lightning Energy BS", 12)], [("PlusPower BS", 3), ("Gust of Wind BS", 2), ("Scoop Up BS", 2),
                        ("Energy Retrieval BS", 2), ("Professor Oak BS", 1), ("Super Energy Removal BS", 1), ("Scyther JU", 1)]),
                graham]
    # Training decks: the run decks and the archived lists except Graham's (held out with the variants).
    train = [d for d in decks if tuple(sorted(d["cards"])) != tuple(sorted(built))] + \
            [{"name": "archived: " + d["name"], "cards": d["cards"]} for d in arch if "Graham" not in d["name"]]
    test = [{"name": f"variant-{k}", "cards": c} for k, c in enumerate(variants)]
    subjects = train + test
    S, A = len(subjects), len(arch)
    all_decks = subjects + arch
    pairs = [(s, S + a) for s in range(S) for a in range(A) if subjects[s]["cards"] != arch[a]["cards"]]

    gm = GpuMatrix(args.policy, 14)
    try:
        gm.play(all_decks, args.games, 23, pairs=pairs, value_at_turn=5)
        games = gm.results
        speed = gm.last
        v0 = gm.values(all_decks, pairs, 8, 31)
        v1 = gm.values(all_decks, [(b, a) for a, b in pairs], 8, 32)
    finally:
        gm.close()
    vstart = np.zeros(S); vcount = np.zeros(S)
    for (s, _), x, y in zip(pairs, v0, v1):
        vstart[s] += (x - y) / 2; vcount[s] += 1
    vstart /= np.maximum(vcount, 1)

    # Split each pair's games by seed parity: even -> target, odd -> statistics.
    win = np.zeros(S); n = np.zeros(S)
    st = {k: np.zeros(S) for k in ("turns", "decisions", "deck_out", "no_pokemon", "v5", "v5n", "n")}
    for r in games:
        s = r["i"]
        mine = r["iSeat"]
        if (r["seed"] // 2) % 2 == 0:            # pairs of games, so both halves get both seats
            win[s] += 1.0 if r["winner"] == mine else 0.0 if r["winner"] in (1, 2) else 0.5
            n[s] += 1
        else:
            st["n"][s] += 1
            st["turns"][s] += r.get("turns") or 0
            st["decisions"][s] += r["steps"]
            st["deck_out"][s] += r.get("ending") == "deck-out"
            st["no_pokemon"][s] += r.get("ending") == "no-pokemon"
            va = (r.get("valueAt") or {}).get(str(mine))
            if va is not None:
                st["v5"][s] += va; st["v5n"][s] += 1
    vecs = np.stack([pool.vector(d["cards"]) for d in subjects])
    shape_gold = np.array([ma.deck_features(pool, v, rng) for v in vecs])   # FEATURES order of matchup_ablation
    T = len(train)
    dist = np.array([min(DECK_SIZE - int(np.minimum(vecs[s], vecs[t]).sum()) for t in range(T) if t != s) for s in range(S)])
    cols = {
        **{f: shape_gold[:, ma.FEATURES.index(f)] for f in GROUPS["shape"] + GROUPS["goldfish"]},
        "turns": st["turns"] / np.maximum(st["n"], 1), "decisions": st["decisions"] / np.maximum(st["n"], 1),
        "deck_out_share": st["deck_out"] / np.maximum(st["n"], 1), "no_pokemon_share": st["no_pokemon"] / np.maximum(st["n"], 1),
        "value_start": vstart, "value_turn5": st["v5"] / np.maximum(st["v5n"], 1), "distance_to_nearest": dist.astype(float),
    }
    X = np.stack([cols[f] for f in NAMES], 1)
    mu, sd = X[:T].mean(0), X[:T].std(0) + 1e-9
    Z = (X - mu) / sd
    y = win / np.maximum(n, 1)

    def cols_of(groups):
        return [NAMES.index(f) for g in groups for f in GROUPS[g]]

    def cv(groups):
        idx = cols_of(groups)
        folds = np.array_split(rng.permutation(T), args.folds)
        p = np.zeros(T)
        for f in folds:
            tr = np.setdiff1d(np.arange(T), f)
            beta = fit_logistic(Z[tr][:, idx], win[tr], n[tr])
            p[f] = predict(beta, Z[f][:, idx])
        return {"deviance": round(deviance(p, win[:T], n[:T]), 4), "mae": round(float(np.abs(p - y[:T]).mean()), 4),
                "spearman": round(spearman(p, y[:T]), 3)}

    groups = list(GROUPS)
    out = {"train_decks": T, "games": speed, "games_per_deck_target": round(float(n[:T].mean()), 1),
           "target_spread_sd": round(float(y[:T].std()), 3), "cv": {}, "weights": {}, "group_weight": {}}
    out["cv"]["constant"] = {"deviance": round(deviance(np.full(T, win[:T].sum() / n[:T].sum()), win[:T], n[:T]), 4),
                             "mae": round(float(np.abs(y[:T].mean() - y[:T]).mean()), 4), "spearman": 0.0}
    out["cv"]["all"] = cv(groups)
    for g in groups:
        out["cv"][f"without {g}"] = cv([h for h in groups if h != g])
        out["cv"][f"only {g}"] = cv([g])
    beta = fit_logistic(Z[:T], win[:T], n[:T])
    out["weights"] = {f: round(float(b), 3) for f, b in zip(NAMES, beta[1:])}
    out["group_weight"] = {g: round(float(sum(abs(out["weights"][f]) for f in GROUPS[g])), 3) for g in groups}
    pv = predict(beta, Z[T:])
    out["variants"] = {"predicted": np.round(pv, 3).tolist(), "real_this_run": np.round(y[T:], 3).tolist(),
                       "real_log36": ma.VARIANT_REAL, "spearman": round(spearman(pv, y[T:]), 3),
                       "features": {f: np.round(X[T:, NAMES.index(f)], 3).tolist() for f in NAMES}}
    print(f"train decks {T}, {out['games_per_deck_target']} target games per deck, win-rate sd {out['target_spread_sd']}")
    for k, v in out["cv"].items():
        print(f"  {k:24s} deviance {v['deviance']:.4f}  MAE {v['mae']:.3f}  rank {v['spearman']:+.2f}")
    print("weights (per sd):", out["weights"])
    print("group |weight|:", out["group_weight"])
    print("variants predicted", out["variants"]["predicted"], "real", out["variants"]["real_this_run"], "rank", out["variants"]["spearman"])
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)


def ma_swap(cards, out, add):
    cards = list(cards)
    for nm, k in out:
        for _ in range(k):
            cards.remove(nm)
    return cards + [nm for nm, k in add for _ in range(k)]


if __name__ == "__main__":
    main()
