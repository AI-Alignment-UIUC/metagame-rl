"""What should the matchup model see? (plan item A6, log #37)

Data: every deck and real-game result of 2000s result #1's three runs, merged (the 16 starting
decks are shared). Five models predict P(a beats b), all antisymmetric (P(a, b) = 1 - P(b, a)):

  value        alpha * v(a, b): the pilot's start-of-game value (16 deals), calibrated
  shape        w . (x_a - x_b): deck-shape features (counts, Energy fit, a goldfish proxy)
  value+shape  both
  embed        the matchup model of rl/matchup.py (card embeddings, MLP)
  all          embed + value + shape

Scored on held-out decks (5 folds by deck: trained on pairs among the other decks, tested on the
held-out decks against them), the way the builder meets a new candidate. Then each model, trained
on all of it, ranks log #36's four Trainer variants against the 24 archived lists (never seen):
their real win rates are 0.499, 0.576, 0.632, 0.681.

Game statistics are not an input: a candidate deck has no games yet.

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/matchup_ablation.py --json notes/data/eval/matchup_ablation.json
"""
import argparse
import json

import numpy as np
import torch
import torch.nn as nn

from rl.decks import Pool, archived_decks
from rl.gpu_matrix import GpuMatrix
from rl.matchup import MatchupModel

DRAW = {"Bill", "Professor Oak", "Computer Search", "Item Finder", "Energy Search", "Pokémon Trader",
        "Energy Retrieval", "Pokémon Breeder", "Gambler", "Super Energy Retrieval"}
RUNS = ["games", "model", "value"]
VARIANT_REAL = [0.499, 0.576, 0.632, 0.681]
FEATURES = ["basic_energy", "special_energy", "pokemon", "basic_pokemon", "trainers", "draw",
            "energy_fit", "attack_by_t2", "attack_by_t3", "energy_in_first_10"]


def deck_features(pool, v, rng, sims=300):
    """Counts, the share of basic Energy whose type some attack needs, and a goldfish proxy: the
    chance a Basic in play can pay its cheapest attack by turn 2 / 3 (one matching Energy attached
    per turn, Trainers ignored)."""
    cards = pool.cards
    ids = [i for i in np.nonzero(v)[0] for _ in range(int(v[i]))]
    c = lambda i: cards[i - 1]
    basic_e = [i for i in ids if pool.basic_energy[i]]
    special = [i for i in ids if c(i)["superType"] == 3 and not pool.basic_energy[i]]
    poke = [i for i in ids if c(i)["superType"] == 1]
    basics = [i for i in ids if pool.basic_pokemon[i]]
    need = np.zeros(11)
    for i in poke:
        for a in c(i)["attacks"]:
            need += np.array(a["cost"]) > 0          # index 0 is Colorless, which any Energy pays
    fit = np.mean([need[np.argmax(c(i)["provides"])] > 0 for i in basic_e]) if basic_e else 0.0

    def cheapest(i):
        costs = [np.array(a["cost"]) for a in c(i)["attacks"]]
        return min(costs, key=lambda x: x.sum()) if costs else None

    def can_pay(cost, energy):
        if cost is None:
            return False
        typed = cost.copy(); typed[0] = 0
        have = energy.copy()
        if (have[1:] < typed[1:]).any():
            return False
        return have.sum() >= cost.sum()

    hits = {2: 0, 3: 0}
    e10 = 0
    for _ in range(sims):
        order = rng.permutation(ids)
        e10 += sum(pool.basic_energy[i] or c(i)["superType"] == 3 for i in order[:10])
        if not any(pool.basic_pokemon[i] for i in order[:7]):
            continue
        for t in (2, 3):
            seen = order[:7 + t]
            in_play = [i for i in seen if pool.basic_pokemon[i]]
            energy = np.zeros(11)
            for i in [i for i in seen if c(i)["superType"] == 3][:t]:
                energy += np.array(c(i)["provides"]) * max(1, c(i)["provideAmount"])
            hits[t] += any(can_pay(cheapest(i), energy) for i in in_play)
    return [len(basic_e), len(special), len(poke), len(basics), 60 - len(poke) - len(basic_e) - len(special),
            sum(c(i)["name"] in DRAW for i in ids), fit, hits[2] / sims, hits[3] / sims, e10 / sims]


class Linear(nn.Module):
    """alpha * v(a, b) and / or w . (x_a - x_b); optionally plus the embedding model's logit."""

    def __init__(self, use_value, use_shape, embed=None, n_feat=len(FEATURES)):
        super().__init__()
        self.use_value, self.use_shape, self.embed = use_value, use_shape, embed
        self.alpha = nn.Parameter(torch.tensor(2.0))
        self.w = nn.Parameter(torch.zeros(n_feat))

    def forward(self, a, b, va, vb, X, V):
        z = torch.zeros(len(a), device=X.device)
        if self.use_value:
            z = z + self.alpha * V
        if self.use_shape:
            z = z + (X[a] - X[b]) @ self.w
        if self.embed is not None:
            z = z + self.embed.logit(self.embed.embed(va), self.embed.embed(vb))
        return torch.sigmoid(z)


def train(model, pairs, W, G, D, X, V, device, epochs=400):
    i = torch.tensor([p[0] for p in pairs], device=device); j = torch.tensor([p[1] for p in pairs], device=device)
    w = torch.tensor([W[p] for p in pairs], dtype=torch.float32, device=device)
    g = torch.tensor([G[p] for p in pairs], dtype=torch.float32, device=device)
    v = torch.tensor([V[p] for p in pairs], dtype=torch.float32, device=device)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4)
    model.to(device).train()
    for _ in range(epochs):
        p = model(i, j, D[i], D[j], X, v).clamp(1e-5, 1 - 1e-5)
        loss = -(w * p.log() + (g - w) * (1 - p).log()).sum() / g.sum()
        opt.zero_grad(); loss.backward(); opt.step()
    return model.eval()


def build(kind, table, text):
    embed = MatchupModel(table, text) if kind in ("embed", "all") else None
    return Linear(kind in ("value", "value+shape", "all"), kind in ("shape", "value+shape", "all"), embed)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/2000s-result-1/data")
    ap.add_argument("--policy", default="results/2000s-result-1/pilot/model_it00014.pt")
    ap.add_argument("--openings", type=int, default=16)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    pool = Pool()
    table = json.load(open("notes/data/cards/pool.json", encoding="utf-8"))["cards"]
    text = np.load("notes/data/cards/text_emb.npy")
    rng = np.random.default_rng(0)

    # Merge the runs: one index per distinct deck, games and wins summed.
    key, decks = {}, []
    W, G = {}, {}
    for r in RUNS:
        pop = json.load(open(f"{args.results}/{r}/population.json", encoding="utf-8"))
        m = np.load(f"{args.results}/{r}/matrix.npz")
        idx = []
        for d in pop:
            k = tuple(sorted(d["cards"]))
            if k not in key:
                key[k] = len(decks); decks.append(d)
            idx.append(key[k])
        for a in range(len(pop)):
            for b in range(len(pop)):
                if a != b and m["games"][a, b] > 0:
                    p = (idx[a], idx[b])
                    W[p] = W.get(p, 0) + m["wins"][a, b]; G[p] = G.get(p, 0) + m["games"][a, b]
    n = len(decks)
    pairs = [p for p in G if p[0] < p[1]]
    # The four variants of log #36 and the archived lists, for the out-of-sample ranking check.
    arch = [{"name": nm, "cards": pool.names(v)} for nm, v in archived_decks(pool)]
    built = [d for d in decks if d["name"].startswith("value5-0")][0]["cards"]
    graham = [d for d in arch if "Graham" in d["name"]][0]["cards"]

    def swap(cards, out, add):
        cards = list(cards)
        for nm, k in out:
            for _ in range(k):
                cards.remove(nm)
        return cards + [nm for nm, k in add for _ in range(k)]
    variants = [built, swap(built, [("Lightning Energy BS", 6)], [("PlusPower BS", 3), ("Gust of Wind BS", 2), ("Professor Oak BS", 1)]),
                swap(built, [("Lightning Energy BS", 12)], [("PlusPower BS", 3), ("Gust of Wind BS", 2), ("Scoop Up BS", 2),
                     ("Energy Retrieval BS", 2), ("Professor Oak BS", 1), ("Super Energy Removal BS", 1), ("Scyther JU", 1)]),
                graham]
    all_decks = decks + arch + [{"name": f"variant-{k}", "cards": c} for k, c in enumerate(variants)]
    A0, V0 = n, n + len(arch)
    vecs = np.stack([pool.vector(d["cards"]) for d in all_decks]).astype(np.float32)
    feats = np.array([deck_features(pool, v, rng) for v in vecs])
    mu, sd = feats[:n].mean(0), feats[:n].std(0) + 1e-6
    X = torch.from_numpy(((feats - mu) / sd).astype(np.float32)).to(dev)
    D = torch.from_numpy(vecs).to(dev)

    # The pilot's value for every measured pair, both orders averaged (v(a,b) - v(b,a)) / 2,
    # and for each variant against each archived list.
    want = pairs + [(V0 + k, A0 + j) for k in range(4) for j in range(len(arch))]
    gm = GpuMatrix(args.policy, 14)
    try:
        fw = gm.values(all_decks, want, args.openings, 11)
        bw = gm.values(all_decks, [(b, a) for a, b in want], args.openings, 12)
    finally:
        gm.close()
    V = {}
    for (a, b), x, y in zip(want, fw, bw):
        V[(a, b)] = (x - y) / 2; V[(b, a)] = -(x - y) / 2

    kinds = ["value", "shape", "value+shape", "embed", "all"]
    folds = np.array_split(rng.permutation(n), args.folds)
    out = {"decks": n, "pairs": len(pairs), "games": int(sum(G[p] for p in pairs)), "features": FEATURES,
           "held_out": {}, "variants": {}}
    for kind in kinds:
        nll = mae = right = tot = 0.0
        per_deck = []
        for f in folds:
            test = set(f.tolist())
            tr = [(a, b) for a, b in G if a not in test and b not in test]
            te = [(a, b) for a, b in G if a in test and b not in test]
            if not te:
                continue
            m = train(build(kind, table, text), tr, W, G, D, X, V, dev)
            with torch.no_grad():
                i = torch.tensor([p[0] for p in te], device=dev); j = torch.tensor([p[1] for p in te], device=dev)
                v = torch.tensor([V[p] for p in te], dtype=torch.float32, device=dev)
                p = m(i, j, D[i], D[j], X, v).clamp(1e-5, 1 - 1e-5).cpu().numpy()
            w = np.array([W[q] for q in te]); g = np.array([G[q] for q in te]); y = w / g
            nll += float(-(w * np.log(p) + (g - w) * np.log(1 - p)).sum()); tot += g.sum()
            mae += float((np.abs(p - y) * g).sum()); right += float((((p > .5) == (y > .5)) * g).sum())
            for d in test:
                rows = [k for k, q in enumerate(te) if q[0] == d]
                if rows:
                    per_deck.append((float(np.mean(p[rows])), float(np.mean(y[rows]))))
        pd = np.array(per_deck)
        rank = lambda x: np.argsort(np.argsort(x))
        spear = float(np.corrcoef(rank(pd[:, 0]), rank(pd[:, 1]))[0, 1])
        out["held_out"][kind] = {"nll": round(nll / tot, 4), "mae": round(mae / tot, 4), "direction": round(right / tot, 4),
                                 "deck_rank_spearman": round(spear, 3)}
        # Trained on everything, then the variants against the archived lists.
        m = train(build(kind, table, text), list(G), W, G, D, X, V, dev)
        with torch.no_grad():
            pv = []
            for k in range(4):
                i = torch.full((len(arch),), V0 + k, device=dev); j = torch.arange(A0, A0 + len(arch), device=dev)
                v = torch.tensor([V[(V0 + k, A0 + q)] for q in range(len(arch))], dtype=torch.float32, device=dev)
                pv.append(float(m(i, j, D[i], D[j], X, v).mean()))
        out["variants"][kind] = {"predicted": [round(x, 3) for x in pv],
                                 "spearman_vs_real": round(float(np.corrcoef(rank(np.array(pv)), rank(np.array(VARIANT_REAL)))[0, 1]), 3)}
        if kind in ("shape", "value+shape"):
            out["variants"][kind]["weights"] = dict(zip(FEATURES, np.round(m.w.detach().cpu().numpy(), 3).tolist()))
        if kind in ("value", "value+shape"):
            out["variants"][kind]["alpha"] = round(float(m.alpha), 3)
        h, vv = out["held_out"][kind], out["variants"][kind]
        print(f"{kind:12s} held-out: NLL {h['nll']:.3f} MAE {h['mae']:.3f} direction {h['direction']:.3f} deck rank {h['deck_rank_spearman']:+.2f}"
              f" | variants {vv['predicted']} rank vs real {vv['spearman_vs_real']:+.2f}", flush=True)
    out["variants"]["real"] = VARIANT_REAL
    out["variants"]["value_raw"] = [round(0.5 + 0.5 * float(np.mean([V[(V0 + k, A0 + q)] for q in range(len(arch))])), 3) for k in range(4)]
    print("raw value on the variants:", out["variants"]["value_raw"], "| real", VARIANT_REAL)
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
